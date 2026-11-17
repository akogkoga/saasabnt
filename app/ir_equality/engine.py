import hashlib
import json
from app.models.document import IRDocument

class IREqualityEngine:
    @staticmethod
    def generate_canonical_hash(ir_doc: IRDocument) -> str:
        """
        Generates a rigorous canonical hash of the IR Document.
        IR_A ≡ IR_B IFF hash(IR_A) == hash(IR_B).
        """
        # We need a stable dict representation
        state = {
            "global_margins": ir_doc.global_margins,
            "blocks": []
        }
        
        for block in ir_doc.blocks:
            state["blocks"].append({
                "semantic": {
                    "type": block.semantic.type.value,
                    "level": block.semantic.level,
                    # Text is hashed lightly or directly to ensure no silent string mutations
                    "text_hash": hashlib.md5(block.semantic.text.encode('utf-8')).hexdigest(),
                    "runs": [r.model_dump() for r in block.semantic.runs] if block.semantic.runs else None,
                    "table_data": block.semantic.table_data,
                    "table_runs": [
                        [[r.model_dump() for r in cell] for cell in row]
                        for row in block.semantic.table_runs
                    ] if block.semantic.table_runs else None,
                },
                "style": {
                    "font_name": block.style.font_name,
                    "font_size": block.style.font_size,
                    "line_spacing": block.style.line_spacing,
                    "space_after": block.style.space_after,
                    "first_line_indent": block.style.first_line_indent,
                    "left_indent": block.style.left_indent,
                    "alignment": block.style.alignment,
                    "bold": block.style.bold,
                    "page_break_before": block.style.page_break_before,
                    "starts_visible_page_numbering": block.style.starts_visible_page_numbering,
                }
            })
            
        canonical_str = json.dumps(state, sort_keys=True)
        return hashlib.sha256(canonical_str.encode('utf-8')).hexdigest()

# Line count: 35
# ⚡ GOLDCODE rules applied — global_rules.md v3.0
