import re
from typing import List
from app.models.document import DocumentBlock, IRDocument, IRBlock, SemanticIR, StyleIR, BlockType
from app.rules_engine.engine import RuleEngine
from app.nlp_engine.engine import SemanticNLPEngine


class IRLayer:
    @staticmethod
    def generate_passive_ir(ordered_blocks: List[DocumentBlock]) -> IRDocument:
        ir_doc = IRDocument()
        started_page_numbering = False

        for i, block in enumerate(ordered_blocks):
            block_text = block.normalized_text or block.original_text
            is_subsection = bool(re.match(r"^\d+\.\d+(?:\.\d+)*\s+\S", block_text.strip()))
            level = 2 if is_subsection else (1 if block.predicted_type in [BlockType.HEADING, BlockType.CHAPTER] else 0)

            sem = SemanticIR(
                type=block.predicted_type,
                text=block_text,
                level=level,
                runs=block.runs,
                table_data=block.table_data,
                table_runs=block.table_runs,
                image_bytes=block.image_bytes,
            )

            if block.predicted_type == BlockType.TABLE:
                style = StyleIR(font_size=10, is_table_style=True)
            else:
                style = RuleEngine.get_style_for_type(block.predicted_type)

            text_key = SemanticNLPEngine.canonicalize(block_text)
            intent, confidence = SemanticNLPEngine.get_highest_intent(text_key)
            if confidence < SemanticNLPEngine.MIN_INTENT_CONFIDENCE:
                intent = "UNKNOWN"

            if block.predicted_type == BlockType.FOLHA_ROSTO:
                if text_key == "FOLHA DE ROSTO":
                    style.page_break_before = i > 0
                    style.bold = True
                elif block.metadata.alignment == "folha_rosto_natureza":
                    style.left_indent = 8.0
                    style.alignment = "justify"
                    style.line_spacing = 1.0
                    style.font_size = 10
                    style.first_line_indent = 0.0
                    style.bold = False

            if block.predicted_type == BlockType.PRE_TEXTUAL:
                if len(block_text) <= 40 and not block_text.strip().endswith("."):
                    style.bold = True
                else:
                    style.bold = False
                    style.alignment = "justify"
                if text_key in ["RESUMO", "ABSTRACT", "AGRADECIMENTOS", "DEDICATORIA", "EPIGRAFE"]:
                    style.page_break_before = i > 0

            if block.predicted_type == BlockType.SUMARIO:
                style.page_break_before = i > 0

            if block.predicted_type in [BlockType.HEADING, BlockType.CHAPTER]:
                if block.predicted_type == BlockType.CHAPTER and not started_page_numbering:
                    style.starts_visible_page_numbering = True
                    style.page_break_before = i > 0
                    started_page_numbering = True
                elif not is_subsection and (
                    block.predicted_type == BlockType.CHAPTER
                    or "REFERENCIAS" in text_key
                    or intent in {"DESENVOLVIMENTO", "CONCLUSAO", "REFERENCIAS", "APENDICES", "ANEXOS"}
                ):
                    style.page_break_before = i > 0

            ir_doc.blocks.append(IRBlock(semantic=sem, style=style))

        return ir_doc
