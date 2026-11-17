from collections import defaultdict
from fastapi import FastAPI, UploadFile, File, Form, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse
from pathlib import Path
import os
import threading
import time
from typing import Dict, Optional
from app.parser.engine import Parser
from app.normalizer.engine import SemanticNormalizer
from app.feature_engine.engine import FeatureEngine
from app.global_context.engine import GlobalContextEngine
from app.scoring_engine.engine import ScoringEngine
from app.classifier.engine import Classifier
from app.structure_builder.engine import StructureBuilder
from app.ordering_engine.engine import OrderingEngine
from app.recompilation_loop.engine import RecompilationLoopEngine
from app.ir_layer.versioning import IRVersioningEngine
from app.render_sanity_check.engine import RenderSanityCheckEngine
from app.render_feedback_loop.engine import RenderFeedbackLoopEngine
from app.models.document import DocumentState

app = FastAPI(title="ABNT Formatter Engine V6 - Functional Compiler")
MAX_REQUEST_BYTES = 5 * 1024 * 1024
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
RATE_LIMIT_WINDOW_SECONDS = 60.0
_request_log: Dict[str, list[float]] = defaultdict(list)
_rate_limit_lock = threading.Lock()


def _enforce_rate_limit(client_ip: str) -> None:
    if RATE_LIMIT_PER_MINUTE <= 0:
        return
    now = time.monotonic()
    cutoff = now - RATE_LIMIT_WINDOW_SECONDS
    with _rate_limit_lock:
        timestamps = [ts for ts in _request_log[client_ip] if ts > cutoff]
        if len(timestamps) >= RATE_LIMIT_PER_MINUTE:
            _request_log[client_ip] = timestamps
            raise HTTPException(
                status_code=429,
                detail="Muitas requisições em pouco tempo. Aguarde um minuto e tente novamente.",
            )
        timestamps.append(now)
        _request_log[client_ip] = timestamps


class RequestSizeLimit:
    """Limit the entire incoming request before multipart parsing, including chunked uploads."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['path'] != '/format':
            return await self.app(scope, receive, send)
        parts = []
        total = 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            chunk = message.get('body', b'')
            total += len(chunk)
            if total > MAX_REQUEST_BYTES:
                return await JSONResponse({'detail': 'A entrada excede o limite de 5 MB.'}, status_code=413)(scope, receive, send)
            parts.append(chunk)
            if not message.get('more_body', False):
                break
        body = b''.join(parts)
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': body, 'more_body': False}
            return await receive()

        return await self.app(scope, replay, send)


app.add_middleware(RequestSizeLimit)
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

if ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_methods=["POST", "GET"],
        allow_headers=["*"],
        expose_headers=[
            "Content-Disposition",
            "X-Compilation-State",
            "X-IR-Canonical-Hash",
            "X-Render-Verification-Hash",
        ],
    )

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/format")
async def format_document(
    request: Request,
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    complete_missing: bool = Form(False),
    institution: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    advisor: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    year: Optional[str] = Form(None),
):
    """
    ABNT V6 Functional Pipeline:
    IR Equality -> Formal Convergence -> Dual Finalization (IR Hash == Render Hash).
    """
    forwarded_for = request.headers.get("x-forwarded-for", "")
    client_ip = (
        forwarded_for.split(",")[0].strip()
        if forwarded_for
        else (request.client.host if request.client else "unknown")
    )
    _enforce_rate_limit(client_ip)

    metadata_overrides = {
        key: value.strip()
        for key, value in {
            "institution": institution,
            "author": author,
            "title": title,
            "advisor": advisor,
            "city": city,
            "year": year,
        }.items()
        if value and value.strip()
    }

    # 1. PARSE & NORMALIZE
    try:
        if file and text and text.strip():
            raise HTTPException(status_code=400, detail="Envie um arquivo ou texto, não ambos.")
        if file:
            raw = await run_in_threadpool(Parser.from_docx, await file.read())
        elif text and text.strip():
            raw = Parser.from_text(text)
        else:
            raise HTTPException(status_code=400, detail="No input.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not raw:
        raise HTTPException(status_code=400, detail="O documento não contém texto ou tabelas suportadas.")

    norm = SemanticNormalizer.normalize(raw)
    
    # 2. FEATURE, CONTEXT, SCORING & CLASSIFY
    feat = FeatureEngine.extract(norm)
    ctx = GlobalContextEngine.calculate(feat)
    prob = ScoringEngine.calculate_probabilities(feat, ctx)
    classified = Classifier.classify(prob)
    
    # 3. INITIAL STRUCTURE & ORDERING
    struct = StructureBuilder.build(classified)
    ordered = OrderingEngine.enforce_order(
        struct,
        complete_missing=complete_missing,
        metadata_overrides=metadata_overrides,
    )
    
    # 4. ACTIVE RECOMPILATION LOOP (Formal Convergence Checked via IR Hash)
    final_blocks, val_res, ir_converged, final_ir = RecompilationLoopEngine.run(
        ordered,
        complete_missing=complete_missing,
        metadata_overrides=metadata_overrides,
    )
    
    if not ir_converged:
        raise HTTPException(status_code=500, detail="Compiler failed to converge structurally (IR Equality check failed).")
        
    final_ir.state = DocumentState.VALIDATED
    snapshot = IRVersioningEngine.create_snapshot("6.0", final_ir.blocks, val_res)
    final_ir.snapshots["6.0"] = snapshot
    
    # 5. RENDER SANITY CHECK ENGINE
    is_render_safe, sanity_msg = RenderSanityCheckEngine.check(
        final_ir,
        require_complete_structure=complete_missing,
    )
    if not is_render_safe:
        raise HTTPException(status_code=500, detail=f"Render Sanity Check Failed: {sanity_msg}")
        
    # 6. RENDER FEEDBACK LOOP ENGINE (V5.2)
    docx_bytes, render_converged, render_hash = RenderFeedbackLoopEngine.render_and_verify(final_ir)
    
    if not render_converged:
         raise HTTPException(status_code=500, detail="Render Feedback Loop Failed. Divergence between IR and DOCX binary.")
         
    # 7. DUAL FINALIZATION CHECK (V5.2)
    # The ultimate proof of compilation consistency
    if ir_converged and render_converged and render_hash != "":
        final_ir.state = DocumentState.FINALIZED
    else:
        raise HTTPException(status_code=500, detail="Dual Finalization Lock Failed.")
    
    # 8. OUTPUT
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": "attachment; filename=documento_abnt_v6.docx",
            "X-Compilation-State": final_ir.state.value,
            "X-IR-Canonical-Hash": final_ir.canonical_hash,
            "X-Render-Verification-Hash": render_hash
        }
    )

if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Line count: 75
# ⚡ GOLDCODE rules applied — global_rules.md v3.0
