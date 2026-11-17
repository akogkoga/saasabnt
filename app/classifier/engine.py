from typing import List
from app.models.document import DocumentBlock, BlockType
from app.nlp_engine.engine import SemanticNLPEngine
import re

class Classifier:
    PRE_TEXTUAL_INTENTS = {
        "RESUMO",
        "ABSTRACT",
        "FOLHA_APROVACAO",
        "DEDICATORIA",
        "AGRADECIMENTOS",
        "EPIGRAFE",
        "LISTA_ILUSTRACOES",
        "LISTA_TABELAS",
        "LISTA_ABREVIATURAS",
        "LISTA_SIMBOLOS",
        "SUMARIO",
    }

    @staticmethod
    def _looks_like_reference(text: str, in_references_section: bool = False) -> bool:
        stripped = (text or "").strip()
        canonical = SemanticNLPEngine.canonicalize(stripped)
        if not canonical:
            return False

        strong_markers = [
            "HTTP",
            "WWW",
            "DISPONIVEL EM",
            "ACESSO EM",
            "DOI",
            "ISBN",
            "ISSN",
            "EDITORA",
            "JOURNAL",
        ]
        has_strong_marker = any(marker in canonical for marker in strong_markers)
        has_year = bool(re.search(r"\b(19|20)\d{2}\b", canonical))
        has_author_prefix = bool(
            re.match(r"^[A-ZÀ-Ý]{2,}(?:\s+[A-ZÀ-Ý]{2,})*,\s+\S", stripped)
            or re.match(r"^[A-Z]{3,}(?: [A-Z]{2,})*[.,]", canonical)
        )

        if in_references_section:
            return has_strong_marker or has_year or has_author_prefix

        if any(
            marker in canonical
            for marker in ("HTTP", "WWW", "DISPONIVEL EM", "ACESSO EM", "DOI", "ISBN", "ISSN")
        ):
            return True

        return has_author_prefix and (has_year or has_strong_marker)

    @staticmethod
    def classify(blocks: List[DocumentBlock]) -> List[DocumentBlock]:
        in_references_section = False

        for block in blocks:
            canonical = SemanticNLPEngine.canonicalize(block.normalized_text)
            intent = block.features.semantic.semantic_intent
            intent_confidence = block.features.semantic.keyword_match

            # V5.1: Stability Lock Check
            if block.is_locked:
                if intent == "REFERENCIAS" and intent_confidence >= SemanticNLPEngine.MIN_INTENT_CONFIDENCE:
                    in_references_section = True
                elif intent in {"APENDICES", "ANEXOS"} and intent_confidence >= SemanticNLPEngine.MIN_INTENT_CONFIDENCE:
                    in_references_section = False
                continue

            # Sort probabilities descending
            sorted_probs = sorted(block.probabilities.items(), key=lambda x: x[1], reverse=True)

            top_type_str, top_prob = sorted_probs[0]
            second_prob = sorted_probs[1][1] if len(sorted_probs) > 1 else 0

            block.predicted_type = BlockType(top_type_str)
            block.confidence = top_prob

            if intent == "REFERENCIAS" and intent_confidence >= SemanticNLPEngine.MIN_INTENT_CONFIDENCE:
                block.predicted_type = BlockType.HEADING
                in_references_section = True
            elif intent in {"APENDICES", "ANEXOS"} and intent_confidence >= SemanticNLPEngine.MIN_INTENT_CONFIDENCE:
                block.predicted_type = BlockType.HEADING
                in_references_section = False
            elif intent in Classifier.PRE_TEXTUAL_INTENTS and intent_confidence >= SemanticNLPEngine.MIN_INTENT_CONFIDENCE:
                block.predicted_type = BlockType.HEADING
                in_references_section = False
            elif intent in {"INTRODUCAO", "DESENVOLVIMENTO", "CONCLUSAO"} and intent_confidence >= SemanticNLPEngine.MIN_INTENT_CONFIDENCE:
                block.predicted_type = BlockType.HEADING
                in_references_section = False
            elif canonical.startswith("FIGURA "):
                block.predicted_type = BlockType.FIGURE_CAPTION
            elif canonical.startswith("TABELA "):
                block.predicted_type = BlockType.TABLE_CAPTION
            elif canonical.startswith("FONTE "):
                block.predicted_type = BlockType.SOURCE
            elif in_references_section and Classifier._looks_like_reference(
                block.normalized_text,
                in_references_section=True,
            ):
                block.predicted_type = BlockType.REFERENCE
            elif block.predicted_type == BlockType.REFERENCE and not Classifier._looks_like_reference(
                block.normalized_text,
                in_references_section=False,
            ):
                block.predicted_type = BlockType.PARAGRAPH

            # Guard against prose sentences being misclassified as headings/chapters.
            if (
                block.predicted_type in [BlockType.HEADING, BlockType.CHAPTER]
                and intent_confidence < SemanticNLPEngine.MIN_INTENT_CONFIDENCE
                and (block.normalized_text.strip().endswith(".") or len(block.normalized_text) > 120)
                and block.features.semantic.chapter_pattern < 0.5
            ):
                block.predicted_type = BlockType.PARAGRAPH

            # Promote obvious short uppercase headings outside references when scored as paragraph.
            if (
                block.predicted_type == BlockType.PARAGRAPH
                and not in_references_section
                and len(block.normalized_text) <= 90
                and block.features.lexical.casing_ratio > 0.75
                and not block.normalized_text.strip().endswith(".")
                and not Classifier._looks_like_reference(block.normalized_text, in_references_section=False)
            ):
                block.predicted_type = (
                    BlockType.CHAPTER
                    if block.features.semantic.chapter_pattern >= 0.5
                    else BlockType.HEADING
                )

            # Detect explicit long direct citations in plain text (>240 chars ending with (AUTHOR, YEAR, p. N)).
            if (
                block.predicted_type == BlockType.PARAGRAPH
                and len(block.normalized_text) > 240
                and re.search(
                    r"\([A-ZÀ-Ý][^)]*,\s*(?:19|20)\d{2}\s*,\s*p\.\s*\d+(?:[-–]\d+)?\)\.?\s*$",
                    block.normalized_text,
                )
            ):
                block.predicted_type = BlockType.LONG_CITATION

            # --- V5.1: Stability Lock ---
            if top_prob > 0.85:
                block.is_locked = True

            # --- Ambiguity Check ---
            if (top_prob - second_prob) < 0.08:
                block.is_ambiguous = True
                block.ambiguity_details = f"Top diff: {top_prob - second_prob:.4f}. Candidates: {top_type_str}, {sorted_probs[1][0]}"

                # Fallback rules
                if block.features.structural.position_norm > 0.9 and "reference" in [top_type_str, sorted_probs[1][0]]:
                    if Classifier._looks_like_reference(
                        block.normalized_text,
                        in_references_section=in_references_section,
                    ):
                        block.predicted_type = BlockType.REFERENCE
                elif (
                    block.features.lexical.length_norm < 0.2
                    and block.features.lexical.casing_ratio > 0.8
                    and not block.normalized_text.strip().endswith(".")
                    and not Classifier._looks_like_reference(
                        block.normalized_text,
                        in_references_section=in_references_section,
                    )
                ):
                    block.predicted_type = BlockType.HEADING

        return blocks

# Line count: 35
# ⚡ GOLDCODE rules applied — global_rules.md v3.0
