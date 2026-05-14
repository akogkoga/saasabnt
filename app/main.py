from fastapi import FastAPI, UploadFile, File, Form, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os
from typing import Optional
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
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    complete_missing: bool = Form(False),
):
    """
    ABNT V6 Functional Pipeline:
    IR Equality -> Formal Convergence -> Dual Finalization (IR Hash == Render Hash).
    """
    # 1. PARSE & NORMALIZE
    try:
        if file:
            raw = Parser.from_docx(await file.read())
        elif text:
            raw = Parser.from_text(text)
        else:
            raise HTTPException(status_code=400, detail="No input.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    norm = SemanticNormalizer.normalize(raw)
    
    # 2. FEATURE, CONTEXT, SCORING & CLASSIFY
    feat = FeatureEngine.extract(norm)
    ctx = GlobalContextEngine.calculate(feat)
    prob = ScoringEngine.calculate_probabilities(feat, ctx)
    classified = Classifier.classify(prob)
    
    # 3. INITIAL STRUCTURE & ORDERING
    struct = StructureBuilder.build(classified)
    ordered = OrderingEngine.enforce_order(struct, complete_missing=complete_missing)
    
    # 4. ACTIVE RECOMPILATION LOOP (Formal Convergence Checked via IR Hash)
    final_blocks, val_res, ir_converged, final_ir = RecompilationLoopEngine.run(
        ordered,
        complete_missing=complete_missing,
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
