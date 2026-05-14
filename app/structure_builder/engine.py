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

    @staticmethod
    def build(blocks: List[DocumentBlock]) -> ABNTStructure:
        structure = ABNTStructure()
        if not blocks:
            return structure

        source_blocks = [
            block
            for block in blocks
            if block.predicted_type
            not in [
                BlockType.CAPA,
                BlockType.FOLHA_ROSTO,
                BlockType.SUMARIO,
                BlockType.SUMARIO_ENTRY,
            ]
        ]

        if not source_blocks:
            return structure

        structure.pre_textual = source_blocks[:2]
        current_phase = "INTRO"

        for block in source_blocks[2:]:
            text_key = SemanticNLPEngine.canonicalize(block.normalized_text)
            intent = block.features.semantic.semantic_intent
            is_heading = block.predicted_type in [BlockType.HEADING, BlockType.CHAPTER]

            if is_heading:
                if intent in StructureBuilder.PRE_TEXTUAL_INTENTS:
                    current_phase = "PRE_TEXTUAL"
                elif intent == "INTRODUCAO" or "INTRODUCAO" in text_key:
                    current_phase = "INTRO"
                elif intent == "DESENVOLVIMENTO" or "DESENVOLVIMENTO" in text_key:
                    current_phase = "DEV"
                elif intent == "CONCLUSAO" or "CONCLUSAO" in text_key:
                    current_phase = "CONCLUSION"
                elif intent in StructureBuilder.POST_TEXTUAL_INTENTS or "REFERENCIAS" in text_key:
                    current_phase = "POST"
                elif block.predicted_type == BlockType.CHAPTER:
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
