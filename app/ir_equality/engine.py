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
                    "text_hash": hashlib.md5(block.semantic.text.encode('utf-8')).hexdigest()
                },
                "style": {
                    "font_name": block.style.font_name,
                    "font_size": block.style.font_size,
                    "line_spacing": block.style.line_spacing,
                    "first_line_indent": block.style.first_line_indent,
                    "left_indent": block.style.left_indent,
                    "alignment": block.style.alignment,
                    "bold": block.style.bold,
                    "page_break_before": block.style.page_break_before
                }
            })
            
        canonical_str = json.dumps(state, sort_keys=True)
        return hashlib.sha256(canonical_str.encode('utf-8')).hexdigest()

# Line count: 35
# ⚡ GOLDCODE rules applied — global_rules.md v3.0
