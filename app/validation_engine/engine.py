from typing import List
from app.models.document import DocumentBlock, ValidationResult, ValidationError, ErrorType, BlockType, DocumentState
from app.nlp_engine.engine import SemanticNLPEngine


class ValidationEngine:
    @staticmethod
    def validate(ordered_blocks: List[DocumentBlock], require_complete_structure: bool = True) -> ValidationResult:
        res = ValidationResult(state=DocumentState.VALIDATED)
        if not ordered_blocks:
            res.is_valid = False
            res.errors.append(ValidationError(type=ErrorType.LOW_CONFIDENCE_STRUCTURE, message="Document is empty."))
            return res

        has_intro = False
        has_dev = False
        has_concl = False
        has_refs = False
        has_resumo = False
        top_chapters = 0
        ref_heading_idx = None
        last_textual_idx = -1
        in_post_textual = False

        for i, block in enumerate(ordered_blocks):
            block_type = block.predicted_type
            text_key = SemanticNLPEngine.canonicalize(block.normalized_text)
            intent, confidence = SemanticNLPEngine.get_highest_intent(text_key)
            if confidence < SemanticNLPEngine.MIN_INTENT_CONFIDENCE:
                intent = "UNKNOWN"

            if block_type in [BlockType.HEADING, BlockType.CHAPTER]:
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

                if block_type == BlockType.CHAPTER:
                    top_chapters += 1

            if block_type in [BlockType.PRE_TEXTUAL, BlockType.HEADING] and text_key == "RESUMO":
                has_resumo = True

            if not in_post_textual and block_type in {
                BlockType.CHAPTER,
                BlockType.PARAGRAPH,
                BlockType.LONG_CITATION,
                BlockType.TABLE,
            }:
                last_textual_idx = i

        if has_intro and has_concl and top_chapters >= 3:
            has_dev = True

        for i, block in enumerate(ordered_blocks):
            if block.predicted_type == BlockType.REFERENCE:
                boundary = ref_heading_idx if ref_heading_idx is not None else last_textual_idx
                if boundary is not None and boundary >= 0 and i < boundary:
                    res.errors.append(
                        ValidationError(
                            type=ErrorType.SECTION_MISPLACEMENT,
                            message=f"Reference at index {i} is too early",
                            affected_block_indices=[i],
                        )
                    )
                    res.is_valid = False

        if require_complete_structure and (not has_intro or not has_dev or not has_concl):
            res.errors.append(
                ValidationError(
                    type=ErrorType.LOW_CONFIDENCE_STRUCTURE,
                    message="Mandatory textual structure missing.",
                )
            )
            res.is_valid = False

        if require_complete_structure and not has_resumo:
            res.warnings.append("Resumo section missing; placeholder will be emitted.")

        if require_complete_structure and not has_refs:
            res.errors.append(ValidationError(type=ErrorType.MISSING_REFERENCES, message="References section missing."))
            res.is_valid = False

        res.audit_log.append(f"Validation completed. Valid: {res.is_valid}")
        return res
