from typing import List
import re

from app.models.document import DocumentBlock, BlockType, ABNTStructure
from app.nlp_engine.engine import SemanticNLPEngine


class OrderingEngine:
    DISPLAY_LABELS = {
        "INTRODUCAO": "INTRODUÇÃO",
        "DESENVOLVIMENTO": "DESENVOLVIMENTO",
        "CONCLUSAO": "CONCLUSÃO",
        "REFERENCIAS": "REFERÊNCIAS",
    }

    @staticmethod
    def enforce_order(structure: ABNTStructure) -> List[DocumentBlock]:
        """
        Enforces ABNT macro-order, inserts mandatory pre-textual elements,
        rewrites chapter numbering, and keeps references at the end.
        """
        title = OrderingEngine._block_text(structure.pre_textual[0]) if structure.pre_textual else "TITULO DO TRABALHO"
        author = OrderingEngine._block_text(structure.pre_textual[1]) if len(structure.pre_textual) > 1 else "NOME DO AUTOR"

        textual_sequence: List[DocumentBlock] = []
        summary_entries: List[str] = []
        chapter_counter = 1

        def process_textual_phase(
            blocks: List[DocumentBlock],
            forced_title: str | None = None,
        ):
            nonlocal chapter_counter

            for block in blocks:
                clean_key = SemanticNLPEngine.canonicalize(block.normalized_text)
                is_forced_heading = bool(
                    forced_title
                    and block.predicted_type in [BlockType.HEADING, BlockType.CHAPTER]
                    and forced_title in clean_key
                )

                if block.predicted_type == BlockType.CHAPTER or is_forced_heading:
                    clean_text = re.sub(r"^\d+(\.\d+)*\s+", "", block.normalized_text).strip()
                    clean_key = SemanticNLPEngine.canonicalize(clean_text)

                    if forced_title and forced_title not in clean_key:
                        clean_text = OrderingEngine.DISPLAY_LABELS.get(forced_title, forced_title)

                    clean_text = clean_text.upper()
                    block.original_text = f"{chapter_counter} {clean_text}"
                    block.normalized_text = f"{chapter_counter} {clean_text}"
                    block.predicted_type = BlockType.CHAPTER
                    summary_entries.append(block.normalized_text)
                    chapter_counter += 1

                textual_sequence.append(block)

        process_textual_phase(structure.textual_intro, forced_title="INTRODUCAO")
        process_textual_phase(structure.textual_dev)
        process_textual_phase(structure.textual_conclusion, forced_title="CONCLUSAO")

        final_sequence = OrderingEngine._build_pre_textual(title, author, summary_entries)
        final_sequence.extend(textual_sequence)
        final_sequence.extend(OrderingEngine._ordered_post_textual(structure.post_textual))
        return final_sequence

    @staticmethod
    def _block_text(block: DocumentBlock) -> str:
        return (block.normalized_text or block.original_text).strip()

    @staticmethod
    def _locked_block(text: str, block_type: BlockType) -> DocumentBlock:
        return DocumentBlock(
            original_text=text,
            normalized_text=text,
            predicted_type=block_type,
            is_locked=True,
        )

    @staticmethod
    def _build_pre_textual(title: str, author: str, chapter_entries: List[str]) -> List[DocumentBlock]:
        entries = chapter_entries or [
            f"1 {OrderingEngine.DISPLAY_LABELS['INTRODUCAO']}",
            f"2 {OrderingEngine.DISPLAY_LABELS['DESENVOLVIMENTO']}",
            f"3 {OrderingEngine.DISPLAY_LABELS['CONCLUSAO']}",
        ]

        return [
            OrderingEngine._locked_block(title.upper(), BlockType.CAPA),
            OrderingEngine._locked_block(author.upper(), BlockType.CAPA),
            OrderingEngine._locked_block("FOLHA DE ROSTO", BlockType.FOLHA_ROSTO),
            OrderingEngine._locked_block(title.upper(), BlockType.FOLHA_ROSTO),
            OrderingEngine._locked_block(author.upper(), BlockType.FOLHA_ROSTO),
            OrderingEngine._locked_block(
                "Trabalho acadêmico apresentado para fins de formatação conforme ABNT.",
                BlockType.FOLHA_ROSTO,
            ),
            OrderingEngine._locked_block("SUMÁRIO", BlockType.SUMARIO),
            *[
                OrderingEngine._locked_block(entry, BlockType.SUMARIO_ENTRY)
                for entry in entries
            ],
            OrderingEngine._locked_block(OrderingEngine.DISPLAY_LABELS["REFERENCIAS"], BlockType.SUMARIO_ENTRY),
        ]

    @staticmethod
    def _ordered_post_textual(blocks: List[DocumentBlock]) -> List[DocumentBlock]:
        ref_heading = None
        references = []
        other_post_textual = []

        for block in blocks:
            text_key = SemanticNLPEngine.canonicalize(block.normalized_text)
            if block.predicted_type == BlockType.HEADING and "REFERENCIAS" in text_key and ref_heading is None:
                ref_heading = block
                ref_heading.original_text = OrderingEngine.DISPLAY_LABELS["REFERENCIAS"]
                ref_heading.normalized_text = OrderingEngine.DISPLAY_LABELS["REFERENCIAS"]
            elif block.predicted_type == BlockType.REFERENCE:
                references.append(block)
            else:
                other_post_textual.append(block)

        if ref_heading is None:
            ref_heading = OrderingEngine._locked_block(
                OrderingEngine.DISPLAY_LABELS["REFERENCIAS"],
                BlockType.HEADING,
            )

        ordered = [ref_heading]
        ordered.extend(sorted(references, key=lambda block: SemanticNLPEngine.canonicalize(block.normalized_text)))
        ordered.extend(other_post_textual)
        return ordered
