import unittest
from io import BytesIO
from pathlib import Path
import sys

from docx import Document
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.main import app


class PreDeployCheck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_frontend_assets_are_served(self):
        home = self.client.get("/")
        self.assertEqual(home.status_code, 200)
        self.assertIn("SaaS ABNT", home.text)
        self.assertIn("config.js", home.text)
        self.assertIn("agrade", home.text)

        self.assertEqual(self.client.get("/styles.css").status_code, 200)
        self.assertEqual(self.client.get("/app.js").status_code, 200)
        self.assertEqual(self.client.get("/config.js").status_code, 200)

    def test_health_endpoint_is_available(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_text_input_generates_openable_docx(self):
        response = self.client.post(
            "/format",
            data={
                "text": (
                    "TITULO DO TRABALHO\n"
                    "NOME DO AUTOR\n"
                    "INTRODUCAO\n"
                    "Texto de introducao.\n"
                    "CONCLUSAO\n"
                    "Fim."
                )
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("x-compilation-state"), "finalized")
        self.assertGreater(len(response.content), 1000)

        doc = Document(BytesIO(response.content))
        texts = [p.text for p in doc.paragraphs if p.text.strip()]
        self.assertEqual(texts[:10], [
            "TITULO DO TRABALHO",
            "NOME DO AUTOR",
            "FOLHA DE ROSTO",
            "TITULO DO TRABALHO",
            "NOME DO AUTOR",
            "Trabalho acadêmico apresentado para fins de formatação conforme ABNT.",
            "SUMÁRIO",
            "1 INTRODUÇÃO",
            "2 CONCLUSÃO",
            "REFERÊNCIAS",
        ])
        self.assertEqual(texts[10:], [
            "1 INTRODUÇÃO",
            "Texto de introducao.",
            "2 CONCLUSÃO",
            "Fim.",
            "REFERÊNCIAS",
        ])

        section = doc.sections[0]
        self.assertAlmostEqual(section.top_margin.cm, 3.0, places=1)
        self.assertAlmostEqual(section.left_margin.cm, 3.0, places=1)
        self.assertAlmostEqual(section.bottom_margin.cm, 2.0, places=1)
        self.assertAlmostEqual(section.right_margin.cm, 2.0, places=1)

    def test_docx_upload_with_table_preserves_table(self):
        source = Document()
        source.add_paragraph("TITULO DO TRABALHO")
        source.add_paragraph("NOME DO AUTOR")
        source.add_paragraph("INTRODUCAO")
        source.add_paragraph("Texto inicial.")
        table = source.add_table(rows=2, cols=2)
        table.cell(0, 0).text = "Campo"
        table.cell(0, 1).text = "Valor"
        table.cell(1, 0).text = "A"
        table.cell(1, 1).text = "10"
        source.add_paragraph("CONCLUSAO")
        source.add_paragraph("Fim.")

        buffer = BytesIO()
        source.save(buffer)

        response = self.client.post(
            "/format",
            files={
                "file": (
                    "entrada.docx",
                    buffer.getvalue(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )

        self.assertEqual(response.status_code, 200)
        doc = Document(BytesIO(response.content))
        self.assertEqual(len(doc.tables), 1)
        rows = [[cell.text for cell in row.cells] for row in doc.tables[0].rows]
        self.assertEqual(rows, [["Campo", "Valor"], ["A", "10"]])

    def test_reference_like_line_stays_in_references(self):
        response = self.client.post(
            "/format",
            data={
                "text": (
                    "TITULO DO TRABALHO\n"
                    "NOME DO AUTOR\n"
                    "INTRODUCAO\n"
                    "Texto.\n"
                    "REFERENCIAS\n"
                    "SILVA, Joao. Livro bom. Sao Paulo: Editora X, 2020."
                )
            },
        )

        self.assertEqual(response.status_code, 200)
        doc = Document(BytesIO(response.content))
        texts = [p.text for p in doc.paragraphs if p.text.strip()]
        self.assertEqual(texts[-2:], [
            "REFERÊNCIAS",
            "SILVA, Joao. Livro bom. Sao Paulo: Editora X, 2020.",
        ])

    def test_expected_error_responses(self):
        empty = self.client.post("/format", data={})
        self.assertEqual(empty.status_code, 400)
        self.assertEqual(empty.json()["detail"], "No input.")

        broken = self.client.post(
            "/format",
            files={
                "file": (
                    "broken.docx",
                    b"not-a-docx",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        self.assertEqual(broken.status_code, 400)
        self.assertEqual(broken.json()["detail"], "Unable to parse DOCX input.")

    def test_netlify_static_config_exists(self):
        netlify_toml = ROOT / "netlify.toml"
        config_js = ROOT / "frontend" / "config.js"
        app_js = ROOT / "frontend" / "app.js"

        self.assertTrue(netlify_toml.exists())
        self.assertIn('publish = "frontend"', netlify_toml.read_text(encoding="utf-8"))
        self.assertTrue(config_js.exists())
        self.assertIn(
            'apiBaseUrl: "https://saasabnt-api.onrender.com"',
            config_js.read_text(encoding="utf-8"),
        )
        self.assertIn("apiUrl", app_js.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
