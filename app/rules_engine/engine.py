from app.models.document import BlockType, StyleIR

class RuleEngine:
    @staticmethod
    def get_style_for_type(block_type: BlockType) -> StyleIR:
        """Returns strict ABNT styling rules based on the block type."""
        # Default global ABNT rules
        style = StyleIR(
            font_name="Times New Roman",
            font_size=12,
            alignment="justify",
            line_spacing=1.5,
            first_line_indent=1.25,
            left_indent=0.0,
            bold=False
        )

        if block_type in [BlockType.HEADING, BlockType.CHAPTER, BlockType.TITLE]:
            style.bold = True
            style.first_line_indent = 0.0
            style.alignment = "left"
        elif block_type in [BlockType.CAPA, BlockType.FOLHA_ROSTO, BlockType.PRE_TEXTUAL]:
            style.bold = block_type == BlockType.CAPA
            style.first_line_indent = 0.0
            style.alignment = "center"
        elif block_type == BlockType.SUMARIO:
            style.bold = True
            style.first_line_indent = 0.0
            style.alignment = "center"
        elif block_type == BlockType.SUMARIO_ENTRY:
            style.first_line_indent = 0.0
            style.alignment = "left"
        elif block_type in [BlockType.FIGURE_CAPTION, BlockType.TABLE_CAPTION, BlockType.SOURCE]:
            style.font_size = 10
            style.line_spacing = 1.0
            style.first_line_indent = 0.0
            style.alignment = "center"
        elif block_type == BlockType.LONG_CITATION:
            style.font_size = 10
            style.line_spacing = 1.0
            style.left_indent = 4.0
            style.first_line_indent = 0.0
        elif block_type == BlockType.REFERENCE:
            style.font_size = 10
            style.line_spacing = 1.0
            style.space_after = 6
            style.alignment = "left"
            style.first_line_indent = 0.0
        elif block_type == BlockType.SHORT_CITATION:
            style.first_line_indent = 0.0
        elif block_type == BlockType.FOOTNOTE:
            style.font_size = 10
            style.line_spacing = 1.0
            style.first_line_indent = 0.0
        
        return style

# Line count: 35
# ⚡ GOLDCODE rules applied — global_rules.md v3.0
