import base64
import io
import unittest
from zipfile import ZIP_DEFLATED, ZipFile

from docx import Document
from fastapi.testclient import TestClient

from app.main import app, MAX_REQUEST_BYTES


class ProtectionTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def submit(self, doc):
        buffer = io.BytesIO()
        doc.save(buffer)
        return self.client.post('/format', files={'file': ('teste.docx', buffer.getvalue())})

    def base_doc(self):
        doc = Document()
        doc.add_paragraph('TITULO DO TRABALHO')
        doc.add_paragraph('NOME DO AUTOR')
        doc.add_paragraph('INTRODUCAO')
        return doc

    def assert_rejected(self, response):
        self.assertEqual(response.status_code, 400, response.text)
        self.assertIn('não podem ser preservados', response.json()['detail'])

    def test_image_is_not_silently_removed(self):
        doc = self.base_doc()
        image = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/a9sAAAAASUVORK5CYII=')
        doc.add_picture(io.BytesIO(image))
        self.assert_rejected(self.submit(doc))

    def test_header_and_partial_bold_are_not_silently_removed(self):
        doc = self.base_doc()
        doc.sections[0].header.paragraphs[0].text = 'Cabeçalho sintético'
        self.assert_rejected(self.submit(doc))

        # Unsupported inline strike formatting is rejected instead of silently dropped.
        doc = self.base_doc()
        p = doc.add_paragraph()
        p.add_run('Riscado').font.strike = True
        p.add_run(' normal')
        self.assert_rejected(self.submit(doc))

    def test_complex_table_is_rejected(self):
        doc = self.base_doc()
        table = doc.add_table(rows=2, cols=2)
        table.cell(0, 0).merge(table.cell(0, 1)).text = 'Mesclada'
        self.assert_rejected(self.submit(doc))

    def test_file_and_text_together_are_rejected(self):
        doc = self.base_doc()
        buffer = io.BytesIO()
        doc.save(buffer)
        response = self.client.post('/format', data={'text': 'Texto'}, files={'file': ('teste.docx', buffer.getvalue())})
        self.assertEqual(response.status_code, 400)

    def test_long_paragraph_is_not_automatically_a_quote(self):
        text = ('Este é um parágrafo sintético. ' * 12).strip()
        response = self.client.post('/format', data={'text': f'TITULO\nAUTOR\nINTRODUCAO\n{text}'})
        self.assertEqual(response.status_code, 200, response.text)
        doc = Document(io.BytesIO(response.content))
        paragraph = next(p for p in doc.paragraphs if p.text == text)
        self.assertNotEqual(paragraph.paragraph_format.left_indent.cm if paragraph.paragraph_format.left_indent else 0, 4.0)

    def test_request_size_limit(self):
        response = self.client.post('/format', content=b'x' * (MAX_REQUEST_BYTES + 1))
        self.assertEqual(response.status_code, 413)

    def test_streamed_request_size_limit(self):
        def chunks():
            for _ in range(6):
                yield b'x' * (1024 * 1024)
        response = self.client.post('/format', content=chunks())
        self.assertEqual(response.status_code, 413)

    def test_uncompressed_size_limit(self):
        buffer = io.BytesIO()
        with ZipFile(buffer, 'w', compression=ZIP_DEFLATED) as archive:
            archive.writestr('oversized', b'0' * (40 * 1024 * 1024 + 1))
        response = self.client.post('/format', files={'file': ('teste.docx', buffer.getvalue())})
        self.assertEqual(response.status_code, 400)
        self.assertIn('descompactado', response.json()['detail'])

if __name__ == '__main__':
    unittest.main()
