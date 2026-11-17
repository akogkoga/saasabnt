from datetime import datetime
from typing import Dict, List, Optional
import re

from app.models.document import DocumentBlock, BlockType, ABNTStructure, OriginalMetadata
from app.nlp_engine.engine import SemanticNLPEngine
from app.structure_builder.engine import StructureBuilder


class OrderingEngine:
    DISPLAY_LABELS = {
        "INTRODUCAO": "INTRODUÇÃO",
        "DESENVOLVIMENTO": "DESENVOLVIMENTO",
        "CONCLUSAO": "CONCLUSÃO",
        "REFERENCIAS": "REFERÊNCIAS",
        "RESUMO": "RESUMO",
        "ABSTRACT": "ABSTRACT",
    }
    METADATA_KEYS = {
        "INSTITUICAO": "institution",
        "AUTOR": "author",
        "TITULO": "title",
        "SUBTITULO": "subtitle",
        "NATUREZA": "nature",
        "OBJETIVO": "objective",
        "AREA": "area",
        "ORIENTADOR": "advisor",
        "CIDADE": "city",
        "ANO": "year",
    }

    @staticmethod
    def enforce_order(
        structure: ABNTStructure,
        complete_missing: bool = True,
        metadata_overrides: Optional[Dict[str, str]] = None,
    ) -> List[DocumentBlock]:
        """
        Enforces ABNT macro-order:
        pre-textual -> textual -> post-textual.
        """
        metadata = OrderingEngine._extract_metadata(structure.pre_textual, metadata_overrides)
        textual_sequence, summary_entries = OrderingEngine._build_textual_sequence(
            structure,
            complete_missing=complete_missing,
        )

        if not complete_missing:
            final_sequence = OrderingEngine._build_adaptive_pre_textual(structure.pre_textual)
            final_sequence.extend(
                OrderingEngine._build_optional_pre_textual(
                    structure.pre_textual_optional,
                    complete_missing=False,
                )
            )
            final_sequence.extend(textual_sequence)
            final_sequence.extend(OrderingEngine._ordered_post_textual(structure.post_textual, complete_missing=False))
            return final_sequence

        final_sequence = OrderingEngine._build_mandatory_pre_textual(metadata)
        final_sequence.extend(
            OrderingEngine._build_optional_pre_textual(
                structure.pre_textual_optional,
                complete_missing=True,
            )
        )
        final_sequence.extend(OrderingEngine._build_summary(summary_entries))
        final_sequence.extend(textual_sequence)
        final_sequence.extend(OrderingEngine._ordered_post_textual(structure.post_textual, complete_missing=True))
        return final_sequence

    @staticmethod
    def _extract_metadata(
        blocks: List[DocumentBlock],
        metadata_overrides: Optional[Dict[str, str]] = None,
    ) -> dict[str, str]:
        year = str(datetime.now().year)
        metadata = {
            "institution": "INSTITUIÇÃO",
            "author": "NOME DO AUTOR",
            "title": "TÍTULO DO TRABALHO",
            "subtitle": "",
            "nature": "Trabalho acadêmico apresentado para fins de formatação conforme ABNT.",
            "objective": "Objetivo acadêmico não informado.",
            "area": "Área não informada.",
            "advisor": "Orientador não informado.",
            "city": "CIDADE",
            "year": year,
        }
        explicit_keys: set[str] = set()
        unlabeled: List[str] = []

        for block in blocks:
            text = OrderingEngine._block_text(block)
            if not text:
                continue
            if ":" in text:
                raw_label, raw_value = text.split(":", 1)
                label_key = SemanticNLPEngine.canonicalize(raw_label)
                target_field = OrderingEngine.METADATA_KEYS.get(label_key)
                if target_field and raw_value.strip():
                    val = raw_value.strip()
                    if target_field in {"institution", "author", "title", "city"}:
                        val = val.upper()
                    metadata[target_field] = val
                    explicit_keys.add(target_field)
                    continue
            unlabeled.append(text)

        if unlabeled and "title" not in explicit_keys:
            metadata["title"] = unlabeled[0].upper()
        if len(unlabeled) > 1 and "author" not in explicit_keys:
            metadata["author"] = unlabeled[1].upper()

        if metadata_overrides:
            for field, raw_val in metadata_overrides.items():
                if field in metadata and raw_val and raw_val.strip():
                    val = raw_val.strip()
                    if field in {"institution", "author", "title", "city"}:
                        val = val.upper()
                    metadata[field] = val
        return metadata

    @staticmethod
    def _is_subsection_heading(text: str) -> bool:
        return bool(re.match(r"^\d+\.\d+(?:\.\d+)*\s+\S", text.strip()))

    @staticmethod
    def _build_textual_sequence(
        structure: ABNTStructure,
        complete_missing: bool,
    ) -> tuple[List[DocumentBlock], List[str]]:
        textual_sequence: List[DocumentBlock] = []
        summary_entries: List[str] = []
        chapter_counter = 1

        def process_phase(
            blocks: List[DocumentBlock],
            forced_title: str,
            placeholder: str,
        ):
            nonlocal chapter_counter

            if not blocks and not complete_missing:
                return

            if not blocks:
                phase_blocks = [
                    OrderingEngine._locked_block(
                        OrderingEngine.DISPLAY_LABELS[forced_title],
                        BlockType.CHAPTER,
                    ),
                    OrderingEngine._locked_block(placeholder, BlockType.PARAGRAPH),
                ]
            else:
                phase_blocks = list(blocks)
                has_top_heading = any(
                    b.predicted_type in [BlockType.HEADING, BlockType.CHAPTER]
                    and not OrderingEngine._is_subsection_heading(b.normalized_text)
                    for b in phase_blocks
                )
                if complete_missing and not has_top_heading:
                    phase_blocks.insert(
                        0,
                        OrderingEngine._locked_block(
                            OrderingEngine.DISPLAY_LABELS[forced_title],
                            BlockType.CHAPTER,
                        ),
                    )

            for block in phase_blocks:
                is_heading = block.predicted_type in [BlockType.HEADING, BlockType.CHAPTER]
                sub_match = re.match(r"^(\d+)((?:\.\d+)+)\s*[-.)]?\s+(.+)$", block.normalized_text.strip())

                if is_heading and sub_match:
                    parent_num = max(1, chapter_counter - 1)
                    sub_suffix = sub_match.group(2)
                    sub_title = sub_match.group(3).strip()
                    formatted = f"{parent_num}{sub_suffix} {sub_title}"
                    block.original_text = formatted
                    block.normalized_text = formatted
                    block.predicted_type = BlockType.HEADING
                    block.runs = None
                    summary_entries.append(formatted)
                elif is_heading:
                    clean_text = re.sub(r"^\d+(?:\.\d+)*\s*[-.)]?\s*", "", block.normalized_text).strip()
                    clean_key = SemanticNLPEngine.canonicalize(clean_text)
                    if clean_key in OrderingEngine.DISPLAY_LABELS:
                        clean_text = OrderingEngine.DISPLAY_LABELS[clean_key]
                    elif not clean_text:
                        clean_text = OrderingEngine.DISPLAY_LABELS[forced_title]
                    else:
                        clean_text = clean_text.upper()

                    formatted = f"{chapter_counter} {clean_text}"
                    block.original_text = formatted
                    block.normalized_text = formatted
                    block.predicted_type = BlockType.CHAPTER
                    block.runs = None
                    summary_entries.append(formatted)
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
    def _locked_block(
        text: str,
        block_type: BlockType,
        metadata: Optional[OriginalMetadata] = None,
    ) -> DocumentBlock:
        return DocumentBlock(
            original_text=text,
            normalized_text=text,
            predicted_type=block_type,
            is_locked=True,
            is_generated=True,
            metadata=metadata or OriginalMetadata(),
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
        nature_meta = OriginalMetadata(alignment="folha_rosto_natureza")
        title_page = [
            ("FOLHA DE ROSTO", None),
            (metadata["author"], None),
            (metadata["title"], None),
            (metadata["subtitle"], None),
            (metadata["nature"], nature_meta),
            (metadata["objective"], nature_meta),
            (metadata["institution"], None),
            (metadata["area"], nature_meta),
            (metadata["advisor"], nature_meta),
            (metadata["city"], None),
            (metadata["year"], None),
        ]

        return [
            OrderingEngine._locked_block(text, BlockType.CAPA)
            for text in cover
            if text
        ] + [
            OrderingEngine._locked_block(text, BlockType.FOLHA_ROSTO, block_meta)
            for text, block_meta in title_page
            if text
        ]

    @staticmethod
    def _build_adaptive_pre_textual(blocks: List[DocumentBlock]) -> List[DocumentBlock]:
        adaptive = []
        for block in blocks:
            block.predicted_type = BlockType.CAPA
            adaptive.append(block)
        return adaptive

    @staticmethod
    def _build_optional_pre_textual(
        blocks: List[DocumentBlock],
        complete_missing: bool = True,
    ) -> List[DocumentBlock]:
        prepared = list(blocks)
        for block in prepared:
            intent = block.features.semantic.semantic_intent
            text_key = SemanticNLPEngine.canonicalize(block.normalized_text)
            if block.predicted_type in [BlockType.HEADING, BlockType.CHAPTER] and (
                intent in StructureBuilder.PRE_TEXTUAL_INTENTS or text_key == "SUMARIO"
            ):
                block.predicted_type = BlockType.PRE_TEXTUAL

        if not complete_missing:
            return prepared

        if any(SemanticNLPEngine.canonicalize(block.normalized_text) == "RESUMO" for block in prepared):
            return prepared

        return [
            OrderingEngine._locked_block("RESUMO", BlockType.PRE_TEXTUAL),
            OrderingEngine._locked_block(
                "Resumo não identificado no documento de entrada. Informe objetivo, metodologia, resultados e conclusão em 150 a 500 palavras.",
                BlockType.PRE_TEXTUAL,
            ),
        ] + prepared

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
    def _ordered_post_textual(blocks: List[DocumentBlock], complete_missing: bool) -> List[DocumentBlock]:
        ref_heading = None
        references = []
        appendices = []
        annexes = []
        other_post_textual = []

        for block in blocks:
            text_key = SemanticNLPEngine.canonicalize(block.normalized_text)
            intent = block.features.semantic.semantic_intent
            intent_confidence = block.features.semantic.keyword_match
            is_ref_heading = (
                block.predicted_type in [BlockType.HEADING, BlockType.CHAPTER]
                and (
                    "REFERENCIAS" in text_key
                    or (intent == "REFERENCIAS" and intent_confidence >= SemanticNLPEngine.MIN_INTENT_CONFIDENCE)
                )
            )
            if is_ref_heading and ref_heading is None:
                ref_heading = block
                if text_key == "REFERENCIAS":
                    ref_heading.original_text = OrderingEngine.DISPLAY_LABELS["REFERENCIAS"]
                    ref_heading.normalized_text = OrderingEngine.DISPLAY_LABELS["REFERENCIAS"]
                else:
                    upper_heading = block.normalized_text.strip().upper()
                    ref_heading.original_text = upper_heading
                    ref_heading.normalized_text = upper_heading
                ref_heading.runs = None
            elif block.predicted_type == BlockType.REFERENCE:
                references.append(block)
            elif "APENDICE" in text_key:
                appendices.append(block)
            elif "ANEXO" in text_key:
                annexes.append(block)
            else:
                other_post_textual.append(block)

        if ref_heading is None and (complete_missing or references):
            ref_heading = OrderingEngine._locked_block(
                OrderingEngine.DISPLAY_LABELS["REFERENCIAS"],
                BlockType.HEADING,
            )

        ordered = [ref_heading] if ref_heading is not None else []
        ordered.extend(sorted(references, key=lambda block: SemanticNLPEngine.canonicalize(block.normalized_text)))
        ordered.extend(other_post_textual)
        ordered.extend(appendices)
        ordered.extend(annexes)
        return ordered
