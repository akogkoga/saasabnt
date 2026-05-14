from typing import List
from app.models.document import DocumentBlock, ValidationResult, ValidationError, ErrorType, BlockType, DocumentState
from app.nlp_engine.engine import SemanticNLPEngine


class ValidationEngine:
    @staticmethod
    def validate(ordered_blocks: List[DocumentBlock]) -> ValidationResult:
        res = ValidationResult(state=DocumentState.VALIDATED)
        if not ordered_blocks:
            res.is_valid = False
            res.errors.append(ValidationError(type=ErrorType.LOW_CONFIDENCE_STRUCTURE, message="Document is empty."))
            return res

        has_intro = False
        has_refs = False

        for i, block in enumerate(ordered_blocks):
            block_type = block.predicted_type
            text_key = SemanticNLPEngine.canonicalize(block.normalized_text)

            if block_type in [BlockType.HEADING, BlockType.CHAPTER]:
                if "INTRODUCAO" in text_key:
                    has_intro = True
                if "REFERENCIAS" in text_key:
                    has_refs = True

            if block_type == BlockType.REFERENCE and i < len(ordered_blocks) * 0.5:
                res.errors.append(
                    ValidationError(
                        type=ErrorType.SECTION_MISPLACEMENT,
                        message=f"Reference at index {i} is too early",
                        affected_block_indices=[i],
                    )
                )
                res.is_valid = False

        if not has_refs:
            res.errors.append(ValidationError(type=ErrorType.MISSING_REFERENCES, message="References section missing."))
            res.is_valid = False

        res.audit_log.append(f"Validation completed. Valid: {res.is_valid}")
        return res
