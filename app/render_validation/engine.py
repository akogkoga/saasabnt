from app.models.document import IRDocument, BlockType
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
import hashlib
import io
import json
import re


class RenderValidationEngine:
    @staticmethod
    def validate_and_hash(docx_bytes: bytes, ir_doc: IRDocument) -> tuple[bool, str]:
        """
        Reads the generated DOCX and verifies that rendered text/table content
        matches the source IR.
        """
        doc = Document(io.BytesIO(docx_bytes))

        expected_state = RenderValidationEngine._expected_state(ir_doc)
        rendered_state = RenderValidationEngine._rendered_state(doc)

        if rendered_state != expected_state:
            return False, ""

        render_canonical_str = json.dumps(rendered_state, sort_keys=True, ensure_ascii=False)
        render_hash_base = hashlib.sha256(render_canonical_str.encode("utf-8")).hexdigest()
        render_hash = hashlib.sha256(f"{ir_doc.canonical_hash}:{render_hash_base}".encode("utf-8")).hexdigest()

        return True, render_hash

    @staticmethod
    def _expected_state(ir_doc: IRDocument) -> list[dict]:
        state = []

        for block in ir_doc.blocks:
            sem = block.semantic

            if sem.type == BlockType.TABLE:
                state.append({"type": "table", "rows": sem.table_data or []})
            elif sem.text.strip():
                normalized = re.sub(r"\s+", " ", sem.text).strip()
                state.append({"type": "paragraph", "text": normalized})

        return state

    @staticmethod
    def _rendered_state(doc: Document) -> list[dict]:
        state = []

        for element in doc.element.body:
            if element.tag.endswith("p"):
                paragraph = Paragraph(element, doc)
                if paragraph.text.strip():
                    normalized = re.sub(r"\s+", " ", paragraph.text).strip()
                    state.append({"type": "paragraph", "text": normalized})

            elif element.tag.endswith("tbl"):
                table = Table(element, doc)
                rows = []
                for row in table.rows:
                    rows.append([cell.text.strip() for cell in row.cells])
                state.append({"type": "table", "rows": rows})

        return state
