from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
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
            DOCXRenderEngine._apply_section_setup(section, ir_doc)

        # 2. Block Rendering
        for idx, ir_block in enumerate(ir_doc.blocks):
            sem = ir_block.semantic
            style = ir_block.style
            
            if style.starts_visible_page_numbering:
                if idx == 0:
                    DOCXRenderEngine._enable_page_numbering(doc.sections[0])
                else:
                    section = doc.add_section(WD_SECTION.NEW_PAGE)
                    DOCXRenderEngine._apply_section_setup(section, ir_doc)
                    DOCXRenderEngine._enable_page_numbering(section)
            elif style.page_break_before and idx > 0:
                doc.add_page_break()
                
            if sem.type == BlockType.TABLE and sem.table_data:
                # Render Table (ABNT/IBGE format: size 10, open lateral borders)
                max_cols = max((len(r) for r in sem.table_data), default=0)
                if max_cols > 0:
                    table = doc.add_table(rows=len(sem.table_data), cols=max_cols)
                    DOCXRenderEngine._apply_ibge_table_borders(table)
                    for r_idx, row in enumerate(sem.table_data):
                        for c_idx, cell_text in enumerate(row):
                            cell = table.cell(r_idx, c_idx)
                            cell_runs = (
                                sem.table_runs[r_idx][c_idx]
                                if sem.table_runs
                                and r_idx < len(sem.table_runs)
                                and c_idx < len(sem.table_runs[r_idx])
                                else None
                            )
                            if cell_runs:
                                p = cell.paragraphs[0]
                                p.clear()
                                for r_ir in cell_runs:
                                    run = p.add_run(r_ir.text)
                                    run.font.size = Pt(10)
                                    run.font.name = style.font_name
                                    run.bold = bool(r_ir.bold)
                                    run.italic = r_ir.italic
                                    run.underline = r_ir.underline
                                    run.font.superscript = r_ir.superscript
                                    run.font.subscript = r_ir.subscript
                            else:
                                cell.text = cell_text
                                for p in cell.paragraphs:
                                    if p.runs:
                                        p.runs[0].font.size = Pt(10)
                                        p.runs[0].font.name = style.font_name
            else:
                # Render Paragraph (preserving inline runs when present)
                if sem.runs:
                    p = doc.add_paragraph()
                    for r_ir in sem.runs:
                        run = p.add_run(r_ir.text)
                        run.font.name = style.font_name
                        run.font.size = Pt(style.font_size)
                        run.bold = style.bold if r_ir.bold is None else r_ir.bold
                        run.italic = r_ir.italic
                        run.underline = r_ir.underline
                        run.font.superscript = r_ir.superscript
                        run.font.subscript = r_ir.subscript
                    DOCXRenderEngine._apply_style(p, style, apply_run_defaults=False)
                else:
                    p = doc.add_paragraph(sem.text)
                    DOCXRenderEngine._apply_style(p, style, apply_run_defaults=True)

                if sem.type == BlockType.SUMARIO:
                    DOCXRenderEngine._append_toc_field(p)

                if sem.type in [BlockType.CHAPTER, BlockType.HEADING] and sem.level in (1, 2):
                    p_pr = p._p.get_or_add_pPr()
                    outline_lvl = OxmlElement("w:outlineLvl")
                    outline_lvl.set(qn("w:val"), str(sem.level - 1))
                    p_pr.append(outline_lvl)

        buffer = io.BytesIO()
        doc.save(buffer)
        return buffer.getvalue()

    @staticmethod
    def _apply_ibge_table_borders(table):
        tbl_pr = table._tbl.tblPr
        borders = tbl_pr.find(qn("w:tblBorders"))
        if borders is not None:
            tbl_pr.remove(borders)
        borders = OxmlElement("w:tblBorders")
        for edge, val in (
            ("top", "single"),
            ("bottom", "single"),
            ("insideH", "single"),
            ("left", "none"),
            ("right", "none"),
            ("insideV", "none"),
        ):
            el = OxmlElement(f"w:{edge}")
            el.set(qn("w:val"), val)
            if val == "single":
                el.set(qn("w:sz"), "4")
                el.set(qn("w:space"), "0")
                el.set(qn("w:color"), "auto")
            borders.append(el)
        tbl_pr.append(borders)

    @staticmethod
    def _append_toc_field(paragraph):
        run = paragraph.add_run()
        begin = OxmlElement("w:fldChar")
        begin.set(qn("w:fldCharType"), "begin")
        begin.set(qn("w:dirty"), "true")

        instr = OxmlElement("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = ' TOC \\o "1-3" \\h \\z \\u '

        separate = OxmlElement("w:fldChar")
        separate.set(qn("w:fldCharType"), "separate")

        end = OxmlElement("w:fldChar")
        end.set(qn("w:fldCharType"), "end")

        run._r.append(begin)
        run._r.append(instr)
        run._r.append(separate)
        run._r.append(end)

    @staticmethod
    def _apply_style(paragraph, style, apply_run_defaults: bool = True):
        fmt = paragraph.paragraph_format
        
        align_map = {"justify": WD_ALIGN_PARAGRAPH.JUSTIFY, "center": WD_ALIGN_PARAGRAPH.CENTER, "left": WD_ALIGN_PARAGRAPH.LEFT}
        paragraph.alignment = align_map.get(style.alignment, WD_ALIGN_PARAGRAPH.JUSTIFY)
        
        fmt.line_spacing = style.line_spacing
        fmt.space_before = Pt(0)
        fmt.space_after = Pt(style.space_after)
        fmt.first_line_indent = Cm(style.first_line_indent) if style.first_line_indent > 0 else 0
        fmt.left_indent = Cm(style.left_indent) if style.left_indent > 0 else 0
            
        if apply_run_defaults and paragraph.runs:
            run = paragraph.runs[0]
            run.font.name = style.font_name
            run.font.size = Pt(style.font_size)
            run.bold = style.bold

    @staticmethod
    def _apply_section_setup(section, ir_doc: IRDocument):
        section.page_width = Cm(21)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(ir_doc.global_margins["top"])
        section.left_margin = Cm(ir_doc.global_margins["left"])
        section.bottom_margin = Cm(ir_doc.global_margins["bottom"])
        section.right_margin = Cm(ir_doc.global_margins["right"])

    @staticmethod
    def _enable_page_numbering(section):
        section.header.is_linked_to_previous = False
        paragraph = section.header.paragraphs[0] if section.header.paragraphs else section.header.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)

        run = paragraph.add_run()
        run.font.name = "Times New Roman"
        run.font.size = Pt(10)

        field_begin = OxmlElement("w:fldChar")
        field_begin.set(qn("w:fldCharType"), "begin")

        instruction = OxmlElement("w:instrText")
        instruction.set(qn("xml:space"), "preserve")
        instruction.text = "PAGE"

        field_end = OxmlElement("w:fldChar")
        field_end.set(qn("w:fldCharType"), "end")

        run._r.append(field_begin)
        run._r.append(instruction)
        run._r.append(field_end)

# Line count: 59
# ⚡ GOLDCODE rules applied — global_rules.md v3.0
