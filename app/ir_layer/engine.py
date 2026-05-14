from typing import List
from app.models.document import DocumentBlock, IRDocument, IRBlock, SemanticIR, StyleIR, BlockType
from app.rules_engine.engine import RuleEngine
from app.nlp_engine.engine import SemanticNLPEngine


class IRLayer:
    @staticmethod
    def generate_passive_ir(ordered_blocks: List[DocumentBlock]) -> IRDocument:
        ir_doc = IRDocument()

        for i, block in enumerate(ordered_blocks):
            block_text = block.normalized_text or block.original_text
            sem = SemanticIR(
                type=block.predicted_type,
                text=block_text,
                level=1 if block.predicted_type in [BlockType.HEADING, BlockType.CHAPTER] else 0,
                table_data=block.table_data,
                image_bytes=block.image_bytes,
            )

            if block.predicted_type == BlockType.TABLE:
                style = StyleIR(font_size=10, is_table_style=True)
            else:
                style = RuleEngine.get_style_for_type(block.predicted_type)

            if i < 2:
                style.alignment = "center"
                style.bold = i == 0
                style.page_break_before = True

            if block.predicted_type in [BlockType.HEADING, BlockType.CHAPTER] and i > 2:
                text_key = SemanticNLPEngine.canonicalize(block.normalized_text)
                if any(k in text_key for k in ["INTRODUCAO", "CONCLUSAO", "REFERENCIAS"]):
                    style.page_break_before = True

            ir_doc.blocks.append(IRBlock(semantic=sem, style=style))

        return ir_doc
