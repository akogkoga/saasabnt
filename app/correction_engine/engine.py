from typing import List
from app.models.document import DocumentBlock, ValidationError, ErrorType, BlockType


class CorrectionEngine:
    @staticmethod
    def apply_corrections(blocks: List[DocumentBlock], errors: List[ValidationError]) -> List[DocumentBlock]:
        """
        Applies deterministic corrections based on validation errors.
        """
        corrected_blocks = list(blocks)

        for error in errors:
            if error.type == ErrorType.MISSING_REFERENCES:
                corrected_blocks.append(
                    DocumentBlock(
                        original_text="REFERENCIAS",
                        normalized_text="REFERENCIAS",
                        predicted_type=BlockType.HEADING,
                        is_locked=True,
                        is_generated=True,
                    )
                )

            elif error.type == ErrorType.SECTION_MISPLACEMENT:
                for idx in sorted(error.affected_block_indices, reverse=True):
                    if 0 <= idx < len(corrected_blocks) and corrected_blocks[idx].predicted_type == BlockType.REFERENCE:
                        block = corrected_blocks.pop(idx)
                        corrected_blocks.append(block)

            elif error.type == ErrorType.ORPHAN_BLOCK:
                for idx in error.affected_block_indices:
                    if 0 <= idx < len(corrected_blocks):
                        corrected_blocks[idx].predicted_type = BlockType.CHAPTER

        return corrected_blocks
