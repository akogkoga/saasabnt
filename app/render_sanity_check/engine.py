from app.models.document import IRDocument, BlockType
from app.nlp_engine.engine import SemanticNLPEngine


class RenderSanityCheckEngine:
    @staticmethod
    def check(ir_doc: IRDocument) -> tuple[bool, str]:
        """
        Pre-render validation to ensure the IR is safe to render.
        """
        if not ir_doc.blocks:
            return False, "IR Document is empty."

        has_intro = False
        has_dev = False
        has_concl = False
        has_refs = False
        has_resumo = False

        for i, block in enumerate(ir_doc.blocks):
            sem = block.semantic
            style = block.style
            text_key = SemanticNLPEngine.canonicalize(sem.text)

            if not style.font_name or style.font_size <= 0:
                return False, f"Incomplete Style IR at block {i}."

            if sem.type in [BlockType.HEADING, BlockType.CHAPTER]:
                if "INTRODUCAO" in text_key:
                    has_intro = True
                if "DESENVOLVIMENTO" in text_key:
                    has_dev = True
                if "CONCLUSAO" in text_key:
                    has_concl = True
                if "REFERENCIAS" in text_key:
                    has_refs = True

            if sem.type == BlockType.PRE_TEXTUAL and text_key == "RESUMO":
                has_resumo = True

            if sem.type == BlockType.REFERENCE and i < len(ir_doc.blocks) * 0.5:
                return False, f"Render violation: Reference found too early at index {i}."

        if not has_resumo:
            return False, "Render violation: Missing Resumo."
        if not has_intro:
            return False, "Render violation: Missing Introduction."
        if not has_dev:
            return False, "Render violation: Missing Development."
        if not has_concl:
            return False, "Render violation: Missing Conclusion."
        if not has_refs:
            return False, "Render violation: Missing References."

        return True, "Render Safe."
