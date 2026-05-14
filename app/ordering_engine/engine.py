from datetime import datetime
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
        "RESUMO": "RESUMO",
        "ABSTRACT": "ABSTRACT",
    }

    @staticmethod
    def enforce_order(structure: ABNTStructure) -> List[DocumentBlock]:
        """
        Enforces ABNT macro-order:
        pre-textual -> textual -> post-textual.
        """
        metadata = OrderingEngine._extract_metadata(structure.pre_textual)
        textual_sequence, summary_entries = OrderingEngine._build_textual_sequence(structure)

        final_sequence = OrderingEngine._build_mandatory_pre_textual(metadata)
        final_sequence.extend(OrderingEngine._build_optional_pre_textual(structure.pre_textual_optional))
        final_sequence.extend(OrderingEngine._build_summary(summary_entries))
        final_sequence.extend(textual_sequence)
        final_sequence.extend(OrderingEngine._ordered_post_textual(structure.post_textual))
        return final_sequence

    @staticmethod
    def _extract_metadata(blocks: List[DocumentBlock]) -> dict[str, str]:
        year = str(datetime.now().year)
        return {
            "institution": "INSTITUIÇÃO",
            "author": OrderingEngine._block_text(blocks[1]).upper() if len(blocks) > 1 else "NOME DO AUTOR",
            "title": OrderingEngine._block_text(blocks[0]).upper() if blocks else "TÍTULO DO TRABALHO",
            "subtitle": "",
            "nature": "Trabalho acadêmico apresentado para fins de formatação conforme ABNT.",
            "objective": "Objetivo acadêmico não informado.",
            "area": "Área não informada.",
            "advisor": "Orientador não informado.",
            "city": "CIDADE",
            "year": year,
        }

    @staticmethod
    def _build_textual_sequence(structure: ABNTStructure) -> tuple[List[DocumentBlock], List[str]]:
        textual_sequence: List[DocumentBlock] = []
        summary_entries: List[str] = []
        chapter_counter = 1

        def process_phase(
            blocks: List[DocumentBlock],
            forced_title: str,
            placeholder: str,
        ):
            nonlocal chapter_counter

            phase_blocks = blocks or [
                OrderingEngine._locked_block(
                    OrderingEngine.DISPLAY_LABELS[forced_title],
                    BlockType.CHAPTER,
                ),
                OrderingEngine._locked_block(placeholder, BlockType.PARAGRAPH),
            ]

            has_heading = False
            for block in phase_blocks:
                text_key = SemanticNLPEngine.canonicalize(block.normalized_text)
                is_heading = block.predicted_type in [BlockType.HEADING, BlockType.CHAPTER]
                is_forced_heading = is_heading and forced_title in text_key

                if (not has_heading and is_heading) or is_forced_heading:
                    clean_text = re.sub(r"^\d+(\.\d+)*\s+", "", block.normalized_text).strip()
                    clean_key = SemanticNLPEngine.canonicalize(clean_text)
                    if forced_title not in clean_key:
                        clean_text = OrderingEngine.DISPLAY_LABELS[forced_title]

                    clean_text = clean_text.upper()
                    block.original_text = f"{chapter_counter} {clean_text}"
                    block.normalized_text = f"{chapter_counter} {clean_text}"
                    block.predicted_type = BlockType.CHAPTER
                    summary_entries.append(block.normalized_text)
                    has_heading = True
                    chapter_counter += 1

                textual_sequence.append(block)

        process_phase(
            structure.textual_intro,
            "INTRODUCAO",
            "Introdução não identificada no documento de entrada.",
        )
        process_phase(
            structure.textual_dev,
            "DESENVOLVIMENTO",
            "Desenvolvimento não identificado no documento de entrada.",
        )
        process_phase(
            structure.textual_conclusion,
            "CONCLUSAO",
            "Conclusão não identificada no documento de entrada.",
        )

        return textual_sequence, summary_entries

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
    def _build_mandatory_pre_textual(metadata: dict[str, str]) -> List[DocumentBlock]:
        cover = [
            metadata["institution"],
            metadata["author"],
            metadata["title"],
            metadata["subtitle"],
            metadata["city"],
            metadata["year"],
        ]
        title_page = [
            "FOLHA DE ROSTO",
            metadata["author"],
            metadata["title"],
            metadata["subtitle"],
            metadata["nature"],
            metadata["objective"],
            metadata["institution"],
            metadata["area"],
            metadata["advisor"],
            metadata["city"],
            metadata["year"],
        ]

        return [
            OrderingEngine._locked_block(text, BlockType.CAPA)
            for text in cover
            if text
        ] + [
            OrderingEngine._locked_block(text, BlockType.FOLHA_ROSTO)
            for text in title_page
            if text
        ]

    @staticmethod
    def _build_optional_pre_textual(blocks: List[DocumentBlock]) -> List[DocumentBlock]:
        if any(SemanticNLPEngine.canonicalize(block.normalized_text) == "RESUMO" for block in blocks):
            return blocks

        return [
            OrderingEngine._locked_block("RESUMO", BlockType.PRE_TEXTUAL),
            OrderingEngine._locked_block(
                "Resumo não identificado no documento de entrada. Informe objetivo, metodologia, resultados e conclusão em 150 a 500 palavras.",
                BlockType.PRE_TEXTUAL,
            ),
        ] + blocks

    @staticmethod
    def _build_summary(chapter_entries: List[str]) -> List[DocumentBlock]:
        entries = chapter_entries + [OrderingEngine.DISPLAY_LABELS["REFERENCIAS"]]
        return [
            OrderingEngine._locked_block("SUMÁRIO", BlockType.SUMARIO),
            *[
                OrderingEngine._locked_block(entry, BlockType.SUMARIO_ENTRY)
                for entry in entries
            ],
        ]

    @staticmethod
    def _ordered_post_textual(blocks: List[DocumentBlock]) -> List[DocumentBlock]:
        ref_heading = None
        references = []
        appendices = []
        annexes = []
        other_post_textual = []

        for block in blocks:
            text_key = SemanticNLPEngine.canonicalize(block.normalized_text)
            if block.predicted_type == BlockType.HEADING and "REFERENCIAS" in text_key and ref_heading is None:
                ref_heading = block
                ref_heading.original_text = OrderingEngine.DISPLAY_LABELS["REFERENCIAS"]
                ref_heading.normalized_text = OrderingEngine.DISPLAY_LABELS["REFERENCIAS"]
            elif block.predicted_type == BlockType.REFERENCE:
                references.append(block)
            elif "APENDICE" in text_key:
                appendices.append(block)
            elif "ANEXO" in text_key:
                annexes.append(block)
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
        ordered.extend(appendices)
        ordered.extend(annexes)
        return ordered
