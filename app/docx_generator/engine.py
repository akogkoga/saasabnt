from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from app.models.document import IRDocument, BlockType
import io

class DOCXRenderEngine:
    @staticmethod
    def render(ir_doc: IRDocument) -> bytes:
        """
        Passive Rendering Engine V6: Supports Rich Blocks (Tables)
        """
        doc = Document()
        
        # 1. Global Page Setup
        for section in doc.sections:
            section.top_margin = Cm(ir_doc.global_margins["top"])
            section.left_margin = Cm(ir_doc.global_margins["left"])
            section.bottom_margin = Cm(ir_doc.global_margins["bottom"])
            section.right_margin = Cm(ir_doc.global_margins["right"])

        # 2. Block Rendering
        for ir_block in ir_doc.blocks:
            sem = ir_block.semantic
            style = ir_block.style
            
            if style.page_break_before:
                doc.add_page_break()
                
            if sem.type == BlockType.TABLE and sem.table_data:
                # Render Table (ABNT format: size 10)
                table = doc.add_table(rows=len(sem.table_data), cols=len(sem.table_data[0]))
                table.style = 'Table Grid' # Basic style, could be customized for open borders
                for r_idx, row in enumerate(sem.table_data):
                    for c_idx, cell_text in enumerate(row):
                        cell = table.cell(r_idx, c_idx)
                        cell.text = cell_text
                        for p in cell.paragraphs:
                            if p.runs:
                                p.runs[0].font.size = Pt(10)
                                p.runs[0].font.name = style.font_name
            else:
                # Render Paragraph
                p = doc.add_paragraph(sem.text)
                DOCXRenderEngine._apply_style(p, style)

        buffer = io.BytesIO()
        doc.save(buffer)
        return buffer.getvalue()

    @staticmethod
    def _apply_style(paragraph, style):
        fmt = paragraph.paragraph_format
        
        align_map = {"justify": WD_ALIGN_PARAGRAPH.JUSTIFY, "center": WD_ALIGN_PARAGRAPH.CENTER, "left": WD_ALIGN_PARAGRAPH.LEFT}
        paragraph.alignment = align_map.get(style.alignment, WD_ALIGN_PARAGRAPH.JUSTIFY)
        
        fmt.line_spacing = style.line_spacing
        fmt.first_line_indent = Cm(style.first_line_indent) if style.first_line_indent > 0 else 0
        fmt.left_indent = Cm(style.left_indent) if style.left_indent > 0 else 0
            
        if paragraph.runs:
            run = paragraph.runs[0]
            run.font.name = style.font_name
            run.font.size = Pt(style.font_size)
            run.bold = style.bold

# Line count: 59
# ⚡ GOLDCODE rules applied — global_rules.md v3.0
