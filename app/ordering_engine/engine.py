from typing import List
from app.models.document import DocumentBlock, BlockType, ABNTStructure
from app.nlp_engine.engine import SemanticNLPEngine
import re


class OrderingEngine:
    DISPLAY_LABELS = {
        "INTRODUCAO": "INTRODUÇÃO",
        "CONCLUSAO": "CONCLUSÃO",
    }

    @staticmethod
    def enforce_order(structure: ABNTStructure) -> List[DocumentBlock]:
        """
        Enforces ABNT macro-order and rewrites chapter numbering sequentially.
        """
        final_sequence = []
        final_sequence.extend(structure.pre_textual)

        chapter_counter = 1

        def process_textual_phase(
            blocks: List[DocumentBlock],
            forced_title: str | None = None,
        ):
            nonlocal chapter_counter

            for block in blocks:
                if block.predicted_type == BlockType.CHAPTER:
                    clean_text = re.sub(r"^\d+(\.\d+)*\s+", "", block.normalized_text).strip()
                    clean_key = SemanticNLPEngine.canonicalize(clean_text)

                    if forced_title and forced_title not in clean_key:
                        clean_text = OrderingEngine.DISPLAY_LABELS.get(forced_title, forced_title)

                    block.original_text = f"{chapter_counter}. {clean_text}"
                    block.normalized_text = f"{chapter_counter}. {clean_text}"
                    chapter_counter += 1

                final_sequence.append(block)

        process_textual_phase(structure.textual_intro, forced_title="INTRODUCAO")
        process_textual_phase(structure.textual_dev)
        process_textual_phase(structure.textual_conclusion, forced_title="CONCLUSAO")

        has_ref_anchor = False
        for block in structure.post_textual:
            text_key = SemanticNLPEngine.canonicalize(block.normalized_text)
            if block.predicted_type == BlockType.HEADING and "REFERENCIAS" in text_key:
                has_ref_anchor = True

        if not has_ref_anchor:
            final_sequence.append(
                DocumentBlock(
                    original_text="REFERENCIAS",
                    normalized_text="REFERENCIAS",
                    predicted_type=BlockType.HEADING,
                    is_locked=True,
                )
            )

        final_sequence.extend(structure.post_textual)
        return final_sequence
