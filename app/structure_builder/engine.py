from typing import List
from app.models.document import DocumentBlock, BlockType, ABNTStructure
from app.nlp_engine.engine import SemanticNLPEngine


class StructureBuilder:
    @staticmethod
    def build(blocks: List[DocumentBlock]) -> ABNTStructure:
        structure = ABNTStructure()
        if not blocks:
            return structure

        structure.pre_textual = blocks[:2]
        current_phase = "INTRO"

        for block in blocks[2:]:
            if block.predicted_type in [
                BlockType.CAPA,
                BlockType.FOLHA_ROSTO,
                BlockType.SUMARIO,
                BlockType.SUMARIO_ENTRY,
            ]:
                continue

            text_key = SemanticNLPEngine.canonicalize(block.normalized_text)
            intent = block.features.semantic.semantic_intent

            if block.predicted_type in [BlockType.HEADING, BlockType.CHAPTER]:
                if intent == "INTRODUCAO" or "INTRODUCAO" in text_key:
                    current_phase = "INTRO"
                elif intent == "CONCLUSAO" or "CONCLUSAO" in text_key:
                    current_phase = "CONCLUSION"
                elif intent == "REFERENCIAS" or "REFERENCIAS" in text_key:
                    current_phase = "POST"
                elif block.predicted_type == BlockType.CHAPTER:
                    current_phase = "DEV"

            if current_phase == "INTRO":
                structure.textual_intro.append(block)
            elif current_phase == "DEV":
                structure.textual_dev.append(block)
            elif current_phase == "CONCLUSION":
                structure.textual_conclusion.append(block)
            elif current_phase == "POST":
                structure.post_textual.append(block)

        return structure
