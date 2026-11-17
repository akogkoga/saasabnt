from app.models.document import IRDocument, BlockType
from app.nlp_engine.engine import SemanticNLPEngine


class RenderSanityCheckEngine:
    @staticmethod
    def check(ir_doc: IRDocument, require_complete_structure: bool = True) -> tuple[bool, str]:
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
        top_chapters = 0
        ref_heading_idx = None
        last_textual_idx = -1
        in_post_textual = False

        for i, block in enumerate(ir_doc.blocks):
            sem = block.semantic
            style = block.style
            text_key = SemanticNLPEngine.canonicalize(sem.text)
            intent, confidence = SemanticNLPEngine.get_highest_intent(text_key)
            if confidence < SemanticNLPEngine.MIN_INTENT_CONFIDENCE:
                intent = "UNKNOWN"

            if not style.font_name or style.font_size <= 0:
                return False, f"Incomplete Style IR at block {i}."

            if sem.type in [BlockType.HEADING, BlockType.CHAPTER]:
                if "INTRODUCAO" in text_key or intent == "INTRODUCAO":
                    has_intro = True
                if "DESENVOLVIMENTO" in text_key or intent == "DESENVOLVIMENTO":
                    has_dev = True
                if "CONCLUSAO" in text_key or intent == "CONCLUSAO":
                    has_concl = True
                if "REFERENCIAS" in text_key or intent == "REFERENCIAS":
                    has_refs = True
                    in_post_textual = True
                    if ref_heading_idx is None:
                        ref_heading_idx = i
                elif intent in {"APENDICES", "ANEXOS"}:
                    in_post_textual = True

                if sem.type == BlockType.CHAPTER:
                    top_chapters += 1

            if sem.type in [BlockType.PRE_TEXTUAL, BlockType.HEADING] and text_key == "RESUMO":
                has_resumo = True

            if not in_post_textual and sem.type in {
                BlockType.CHAPTER,
                BlockType.PARAGRAPH,
                BlockType.LONG_CITATION,
                BlockType.TABLE,
            }:
                last_textual_idx = i

        if has_intro and has_concl and top_chapters >= 3:
            has_dev = True

        for i, block in enumerate(ir_doc.blocks):
            if block.semantic.type == BlockType.REFERENCE:
                boundary = ref_heading_idx if ref_heading_idx is not None else last_textual_idx
                if boundary is not None and boundary >= 0 and i < boundary:
                    return False, f"Render violation: Reference found too early at index {i}."

        if not require_complete_structure:
            return True, "Render Safe."

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
