import re
from typing import List

from app.models.document import DocumentBlock, BlockType, ABNTStructure
from app.nlp_engine.engine import SemanticNLPEngine


class StructureBuilder:
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
    }
    POST_TEXTUAL_INTENTS = {"REFERENCIAS", "APENDICES", "ANEXOS"}
    METADATA_PREFIXES = (
        "INSTITUICAO:",
        "AUTOR:",
        "TITULO:",
        "SUBTITULO:",
        "CIDADE:",
        "ANO:",
        "ORIENTADOR:",
        "COORIENTADOR:",
        "OBJETIVO:",
        "AREA:",
        "NATUREZA:",
    )

    @staticmethod
    def _has_metadata_label(text: str) -> bool:
        if ":" not in text:
            return False
        prefix = SemanticNLPEngine.canonicalize(text.split(":", 1)[0])
        return f"{prefix}:" in StructureBuilder.METADATA_PREFIXES

    @staticmethod
    def build(blocks: List[DocumentBlock]) -> ABNTStructure:
        structure = ABNTStructure()
        if not blocks:
            return structure

        source_blocks = [
            block
            for block in blocks
            if not block.is_generated
        ]

        if not source_blocks:
            return structure

        content_start = 0
        unlabeled_pre_textual = 0
        for i, block in enumerate(source_blocks):
            if block.predicted_type in {BlockType.TABLE, BlockType.REFERENCE, BlockType.LONG_CITATION}:
                break

            text = (block.normalized_text or block.original_text).strip()
            intent = block.features.semantic.semantic_intent
            intent_confidence = block.features.semantic.keyword_match
            text_key = SemanticNLPEngine.canonicalize(text)
            is_labeled_meta = StructureBuilder._has_metadata_label(text)

            if (
                (intent in StructureBuilder.PRE_TEXTUAL_INTENTS and intent_confidence >= SemanticNLPEngine.MIN_INTENT_CONFIDENCE)
                or (intent in {"INTRODUCAO", "DESENVOLVIMENTO", "CONCLUSAO"} and intent_confidence >= SemanticNLPEngine.MIN_INTENT_CONFIDENCE)
                or (intent in StructureBuilder.POST_TEXTUAL_INTENTS and intent_confidence >= SemanticNLPEngine.MIN_INTENT_CONFIDENCE)
                or text_key == "SUMARIO"
                or re.match(r"^\d+(?:\.\d+)*\s+\S", text)
            ):
                break

            if not is_labeled_meta:
                is_prose_sentence = text.endswith(".") and any(c.islower() for c in text)
                if unlabeled_pre_textual >= 2 or len(text) > 150 or is_prose_sentence:
                    break
                unlabeled_pre_textual += 1

            structure.pre_textual.append(block)
            content_start = i + 1

        current_phase = "INTRO"
        intro_has_heading = False

        for block in source_blocks[content_start:]:
            if block.predicted_type == BlockType.REFERENCE:
                structure.post_textual.append(block)
                continue

            text_key = SemanticNLPEngine.canonicalize(block.normalized_text)
            intent = block.features.semantic.semantic_intent
            intent_confidence = block.features.semantic.keyword_match
            is_heading = block.predicted_type in [BlockType.HEADING, BlockType.CHAPTER]
            is_subsection = bool(re.match(r"^\d+\.\d+(?:\.\d+)*\s+\S", block.normalized_text))

            if is_heading:
                if intent in StructureBuilder.PRE_TEXTUAL_INTENTS and intent_confidence >= SemanticNLPEngine.MIN_INTENT_CONFIDENCE:
                    current_phase = "PRE_TEXTUAL"
                elif text_key == "SUMARIO":
                    current_phase = "PRE_TEXTUAL"
                elif intent == "INTRODUCAO" and intent_confidence >= SemanticNLPEngine.MIN_INTENT_CONFIDENCE:
                    current_phase = "INTRO"
                    intro_has_heading = True
                elif intent == "DESENVOLVIMENTO" and intent_confidence >= SemanticNLPEngine.MIN_INTENT_CONFIDENCE:
                    current_phase = "DEV"
                elif intent == "CONCLUSAO" and intent_confidence >= SemanticNLPEngine.MIN_INTENT_CONFIDENCE:
                    current_phase = "CONCLUSION"
                elif intent in StructureBuilder.POST_TEXTUAL_INTENTS and intent_confidence >= SemanticNLPEngine.MIN_INTENT_CONFIDENCE:
                    current_phase = "POST"
                elif is_subsection:
                    pass
                elif current_phase == "INTRO" and intro_has_heading:
                    current_phase = "DEV"
                elif block.predicted_type == BlockType.CHAPTER and current_phase not in {"CONCLUSION", "POST"}:
                    current_phase = "DEV"

            if current_phase == "PRE_TEXTUAL":
                structure.pre_textual_optional.append(block)
            elif current_phase == "INTRO":
                structure.textual_intro.append(block)
            elif current_phase == "DEV":
                structure.textual_dev.append(block)
            elif current_phase == "CONCLUSION":
                structure.textual_conclusion.append(block)
            elif current_phase == "POST":
                structure.post_textual.append(block)

        return structure
