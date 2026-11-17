import io
import unittest
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from fastapi.testclient import TestClient

import app.main as main_module
from app.document_assembler.engine import DocumentAssembler
from app.feature_extractor.engine import FeatureExtractor
from app.main import app
from app.models.document import ABNTStructure, DocumentBlock

ROOT = Path(__file__).resolve().parent.parent


class MVPFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_in_text_citations_with_years_stay_in_sections(self):
        resp = self.client.post(
            "/format",
            data={
                "complete_missing": "false",
                "text": (
                    "TITULO DO TRABALHO\n"
                    "NOME DO AUTOR\n"
                    "INTRODUCAO\n"
                    "Segundo Silva (2020), a formatacao academica exige rigor metodologico.\n"
                    "DESENVOLVIMENTO\n"
                    "Conforme aponta Oliveira (2019), os sistemas automatizados auxiliam estudantes.\n"
                    "CONCLUSAO\n"
                    "Portanto, os dados de 2022 confirmam a hipotese.\n"
                    "REFERENCIAS\n"
                    "SILVA, Joao. Metodologia Cientifica. Sao Paulo: Atlas, 2020."
                ),
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        doc = Document(io.BytesIO(resp.content))
        texts = [p.text for p in doc.paragraphs if p.text.strip()]
        self.assertEqual(
            texts,
            [
                "TITULO DO TRABALHO",
                "NOME DO AUTOR",
                "1 INTRODUÇÃO",
                "Segundo Silva (2020), a formatacao academica exige rigor metodologico.",
                "2 DESENVOLVIMENTO",
                "Conforme aponta Oliveira (2019), os sistemas automatizados auxiliam estudantes.",
                "3 CONCLUSÃO",
                "Portanto, os dados de 2022 confirmam a hipotese.",
                "REFERÊNCIAS",
                "SILVA, Joao. Metodologia Cientifica. Sao Paulo: Atlas, 2020.",
            ],
        )

        body_para = next(
            p for p in doc.paragraphs
            if p.text.startswith("Segundo Silva (2020)")
        )
        self.assertEqual(body_para.runs[0].font.size.pt, 12.0)
        self.assertAlmostEqual(body_para.paragraph_format.first_line_indent.cm, 1.25, places=1)

        ref_para = next(
            p for p in doc.paragraphs
            if p.text.startswith("SILVA, Joao")
        )
        self.assertEqual(ref_para.runs[0].font.size.pt, 10.0)

    def test_user_resumo_in_complete_mode_succeeds(self):
        resp = self.client.post(
            "/format",
            data={
                "complete_missing": "true",
                "text": (
                    "TITULO DO TRABALHO\n"
                    "NOME DO AUTOR\n"
                    "RESUMO\n"
                    "Este e o resumo real do autor.\n"
                    "INTRODUCAO\n"
                    "Texto introdutorio.\n"
                    "DESENVOLVIMENTO\n"
                    "Texto de desenvolvimento.\n"
                    "CONCLUSAO\n"
                    "Texto final.\n"
                    "REFERENCIAS\n"
                    "SILVA, J. Obra. Sao Paulo: Editora, 2020."
                ),
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        doc = Document(io.BytesIO(resp.content))
        texts = [p.text for p in doc.paragraphs if p.text.strip()]
        self.assertIn("RESUMO", texts)
        self.assertIn("Este e o resumo real do autor.", texts)
        self.assertNotIn(
            "Resumo não identificado no documento de entrada. Informe objetivo, metodologia, resultados e conclusão em 150 a 500 palavras.",
            texts,
        )

    def test_multiple_chapters_and_subsections_preserve_titles_and_summary(self):
        resp = self.client.post(
            "/format",
            data={
                "complete_missing": "true",
                "text": (
                    "TITULO DO TRABALHO\n"
                    "NOME DO AUTOR\n"
                    "1 INTRODUCAO\n"
                    "Texto intro.\n"
                    "2 FUNDAMENTACAO TEORICA\n"
                    "Texto fund.\n"
                    "2.1 Conceitos Basicos\n"
                    "Texto conc.\n"
                    "3 METODOLOGIA\n"
                    "Texto met.\n"
                    "4 CONSIDERACOES FINAIS\n"
                    "Texto fim.\n"
                    "REFERENCIAS\n"
                    "SILVA, J. Obra. Sao Paulo: Alfa, 2021."
                ),
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        doc = Document(io.BytesIO(resp.content))
        texts = [p.text for p in doc.paragraphs if p.text.strip()]
        sumario_idx = texts.index("SUMÁRIO")
        intro_heading_idx = texts.index("1 INTRODUÇÃO", sumario_idx + 2)
        summary_entries = texts[sumario_idx + 1:intro_heading_idx]
        self.assertEqual(
            summary_entries,
            [
                "1 INTRODUÇÃO",
                "2 FUNDAMENTACAO TEORICA",
                "2.1 Conceitos Basicos",
                "3 METODOLOGIA",
                "4 CONSIDERACOES FINAIS",
                "REFERÊNCIAS",
            ],
        )

    def test_plain_prose_without_headings_adaptive_and_complete(self):
        plain_text = (
            "Este estudo analisa a producao academica no Brasil sob a otica das normas tecnicas.\n"
            "A metodologia utilizada foi a pesquisa bibliografica e documental.\n"
            "Os resultados demonstram a importancia da padronizacao."
        )
        adaptive = self.client.post(
            "/format",
            data={"complete_missing": "false", "text": plain_text},
        )
        self.assertEqual(adaptive.status_code, 200, adaptive.text)
        doc_adaptive = Document(io.BytesIO(adaptive.content))
        paras = [p for p in doc_adaptive.paragraphs if p.text.strip()]
        self.assertEqual(len(paras), 3)
        for p in paras:
            self.assertFalse(p.runs[0].bold)
            self.assertAlmostEqual(p.paragraph_format.first_line_indent.cm, 1.25, places=1)
            self.assertEqual(p.paragraph_format.line_spacing, 1.5)
            self.assertEqual(p.runs[0].font.size.pt, 12.0)

        complete = self.client.post(
            "/format",
            data={"complete_missing": "true", "text": plain_text},
        )
        self.assertEqual(complete.status_code, 200, complete.text)
        doc_complete = Document(io.BytesIO(complete.content))
        texts = [p.text for p in doc_complete.paragraphs if p.text.strip()]
        self.assertIn("1 INTRODUÇÃO", texts)
        self.assertIn(
            "Este estudo analisa a producao academica no Brasil sob a otica das normas tecnicas.",
            texts,
        )

    def test_docx_with_word_metadata_uniform_bold_heading_long_citation_and_table(self):
        source = Document()
        p_title = source.add_paragraph()
        r = p_title.add_run("TITULO DO TRABALHO")
        r.bold = True
        r.font.name = "Arial"
        r.font.size = Pt(12)
        rPr = r._r.get_or_add_rPr()
        lang = OxmlElement("w:lang")
        lang.set(qn("w:val"), "pt-BR")
        rPr.append(lang)
        p_title._p.append(OxmlElement("w:bookmarkStart"))
        p_title._p.append(OxmlElement("w:bookmarkEnd"))
        p_title._p.append(OxmlElement("w:proofErr"))

        source.add_paragraph("NOME DO AUTOR")
        source.add_paragraph("INTRODUCAO", style="Heading 1")
        source.add_paragraph("Texto inicial do estudo.")

        quote_text = (
            "Esta e uma citacao direta com mais de tres linhas extraida de obra academica "
            "de referencia para validar a preservacao de recuo de 4 centimetros no documento "
            "final formatado pelas normas tecnicas."
        )
        p_quote = source.add_paragraph(quote_text)
        p_quote.paragraph_format.left_indent = Cm(4.0)

        table = source.add_table(rows=2, cols=2)
        table.cell(0, 0).text = "Item"
        table.cell(0, 1).text = "Qtd"
        table.cell(1, 0).text = "Teste"
        table.cell(1, 1).text = "42"

        source.add_paragraph("CONCLUSAO")
        source.add_paragraph("Conclusao do estudo.")

        buf = io.BytesIO()
        source.save(buf)

        resp = self.client.post(
            "/format",
            data={"complete_missing": "true"},
            files={
                "file": (
                    "real.docx",
                    buf.getvalue(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        out = Document(io.BytesIO(resp.content))
        self.assertEqual(len(out.tables), 1)
        self.assertEqual(
            [[c.text for c in row.cells] for row in out.tables[0].rows],
            [["Item", "Qtd"], ["Teste", "42"]],
        )
        quote_para = next(p for p in out.paragraphs if p.text == quote_text)
        self.assertAlmostEqual(quote_para.paragraph_format.left_indent.cm, 4.0, places=1)
        self.assertEqual(quote_para.runs[0].font.size.pt, 10.0)
        self.assertEqual(quote_para.paragraph_format.line_spacing, 1.0)

    def test_labeled_metadata_populates_cover_and_title_page(self):
        resp = self.client.post(
            "/format",
            data={
                "complete_missing": "true",
                "text": (
                    "Instituição: Universidade Teste\n"
                    "Autor: Maria Souza\n"
                    "Título: Arquitetura ABNT\n"
                    "Orientador: Prof. Carlos Lima\n"
                    "Cidade: Curitiba\n"
                    "Ano: 2025\n"
                    "INTRODUCAO\n"
                    "Texto."
                ),
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        doc = Document(io.BytesIO(resp.content))
        texts = [p.text for p in doc.paragraphs if p.text.strip()]
        self.assertEqual(
            texts[:5],
            ["UNIVERSIDADE TESTE", "MARIA SOUZA", "ARQUITETURA ABNT", "CURITIBA", "2025"],
        )
        self.assertIn("Prof. Carlos Lima", texts)

    def test_short_doc_with_majority_references_does_not_fail(self):
        resp = self.client.post(
            "/format",
            data={
                "complete_missing": "false",
                "text": (
                    "TITULO DO TRABALHO\n"
                    "NOME DO AUTOR\n"
                    "INTRODUCAO\n"
                    "Texto.\n"
                    "REFERENCIAS\n"
                    "AUTOR A. Obra 1. 2018.\n"
                    "AUTOR B. Obra 2. 2019.\n"
                    "AUTOR C. Obra 3. 2020.\n"
                    "AUTOR D. Obra 4. 2021.\n"
                    "AUTOR E. Obra 5. 2022.\n"
                    "AUTOR F. Obra 6. 2023."
                ),
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        doc = Document(io.BytesIO(resp.content))
        texts = [p.text for p in doc.paragraphs if p.text.strip()]
        self.assertIn("REFERÊNCIAS", texts)
        self.assertIn("AUTOR F. Obra 6. 2023.", texts)

    def test_empty_docx_and_whitespace_text_return_400(self):
        empty_doc = Document()
        buf = io.BytesIO()
        empty_doc.save(buf)

        docx_resp = self.client.post(
            "/format",
            files={
                "file": (
                    "vazio.docx",
                    buf.getvalue(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        self.assertEqual(docx_resp.status_code, 400)

        text_resp = self.client.post("/format", data={"text": "   \n  \n "})
        self.assertEqual(text_resp.status_code, 400)

    def test_frontend_health_check_and_accessibility_markers(self):
        app_js = (ROOT / "frontend" / "app.js").read_text(encoding="utf-8")
        styles_css = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
        index_html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
        self.assertIn('apiUrl("/health")', app_js)
        self.assertIn("MAX_UPLOAD_BYTES", app_js)
        self.assertIn("humanizeErrorMessage", app_js)
        self.assertIn(":focus-within", styles_css)
        self.assertIn(":focus-visible", styles_css)
        self.assertIn("metadataFields", index_html)
        self.assertIn("metaInstitution", index_html)

    def test_docx_preserves_inline_runs_bold_italic_underline_and_super_sub(self):
        source = Document()
        source.add_paragraph("TITULO DO TRABALHO")
        source.add_paragraph("NOME DO AUTOR")
        source.add_paragraph("INTRODUCAO")

        p = source.add_paragraph()
        r1 = p.add_run("Texto com ")
        r2 = p.add_run("negrito parcial")
        r2.bold = True
        p.add_run(", ")
        r3 = p.add_run("italico")
        r3.italic = True
        p.add_run(", ")
        r4 = p.add_run("sublinhado")
        r4.underline = True
        p.add_run(" e H")
        r5 = p.add_run("2")
        r5.font.subscript = True
        p.add_run("O e 10")
        r6 = p.add_run("2")
        r6.font.superscript = True
        p.add_run(".")

        buf = io.BytesIO()
        source.save(buf)

        resp = self.client.post(
            "/format",
            data={"complete_missing": "false"},
            files={
                "file": (
                    "inline.docx",
                    buf.getvalue(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        out = Document(io.BytesIO(resp.content))
        target = next(para for para in out.paragraphs if "negrito parcial" in para.text)
        run_map = {r.text: r for r in target.runs}
        self.assertTrue(run_map["negrito parcial"].bold)
        self.assertTrue(run_map["italico"].italic)
        self.assertTrue(run_map["sublinhado"].underline)
        self.assertTrue(run_map["2"].font.subscript or any(r.font.subscript for r in target.runs))
        self.assertTrue(any(r.font.superscript for r in target.runs))
        self.assertFalse(bool(run_map["Texto com "].bold))

    def test_abnt_rendering_folha_rosto_indent_references_spacing_ibge_borders_and_outline(self):
        source = Document()
        source.add_paragraph("TITULO DO TRABALHO")
        source.add_paragraph("NOME DO AUTOR")
        source.add_paragraph("INTRODUCAO")
        source.add_paragraph("Texto inicial.")
        table = source.add_table(rows=2, cols=2)
        table.cell(0, 0).text = "Coluna A"
        table.cell(0, 1).text = "Coluna B"
        table.cell(1, 0).text = "1"
        table.cell(1, 1).text = "2"
        source.add_paragraph("CONCLUSAO")
        source.add_paragraph("Conclusao.")
        source.add_paragraph("REFERENCIAS")
        source.add_paragraph("SILVA, Joao. Obra A. Sao Paulo: Editora, 2020.")

        buf = io.BytesIO()
        source.save(buf)

        resp = self.client.post(
            "/format",
            data={"complete_missing": "true"},
            files={
                "file": (
                    "abnt_rules.docx",
                    buf.getvalue(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        out = Document(io.BytesIO(resp.content))

        nature_para = next(
            p for p in out.paragraphs
            if p.text.startswith("Trabalho acadêmico apresentado")
        )
        self.assertAlmostEqual(nature_para.paragraph_format.left_indent.cm, 8.0, places=1)
        self.assertEqual(nature_para.paragraph_format.line_spacing, 1.0)

        ref_para = next(p for p in out.paragraphs if p.text.startswith("SILVA, Joao"))
        self.assertEqual(ref_para.paragraph_format.space_after.pt, 6.0)

        intro_heading = [p for p in out.paragraphs if p.text == "1 INTRODUÇÃO"][-1]
        outline = intro_heading._p.pPr.find(qn("w:outlineLvl"))
        self.assertIsNotNone(outline)
        self.assertEqual(outline.get(qn("w:val")), "0")

        borders = out.tables[0]._tbl.tblPr.find(qn("w:tblBorders"))
        self.assertIsNotNone(borders)
        border_vals = {child.tag.split("}")[-1]: child.get(qn("w:val")) for child in borders}
        self.assertEqual(border_vals.get("top"), "single")
        self.assertEqual(border_vals.get("bottom"), "single")
        self.assertEqual(border_vals.get("insideH"), "single")
        self.assertEqual(border_vals.get("left"), "none")
        self.assertEqual(border_vals.get("right"), "none")
        self.assertEqual(border_vals.get("insideV"), "none")

    def test_metadata_form_overrides_populate_cover_and_title_page(self):
        resp = self.client.post(
            "/format",
            data={
                "complete_missing": "true",
                "institution": "Universidade Exemplo",
                "author": "Carlos Pereira",
                "title": "Compilador ABNT",
                "advisor": "Profa. Dra. Ana Costa",
                "city": "Belo Horizonte",
                "year": "2027",
                "text": "INTRODUCAO\nTexto do estudo.",
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        out = Document(io.BytesIO(resp.content))
        texts = [p.text for p in out.paragraphs if p.text.strip()]
        self.assertEqual(
            texts[:5],
            ["UNIVERSIDADE EXEMPLO", "CARLOS PEREIRA", "COMPILADOR ABNT", "BELO HORIZONTE", "2027"],
        )
        self.assertIn("Profa. Dra. Ana Costa", texts)

    def test_rate_limiter_returns_429_when_limit_exceeded(self):
        orig_limit = main_module.RATE_LIMIT_PER_MINUTE
        main_module.RATE_LIMIT_PER_MINUTE = 2
        main_module._request_log.clear()
        try:
            headers = {"x-forwarded-for": "198.51.100.77"}
            r1 = self.client.post("/format", data={"text": "INTRODUCAO\nA."}, headers=headers)
            r2 = self.client.post("/format", data={"text": "INTRODUCAO\nB."}, headers=headers)
            r3 = self.client.post("/format", data={"text": "INTRODUCAO\nC."}, headers=headers)
            self.assertEqual(r1.status_code, 200)
            self.assertEqual(r2.status_code, 200)
            self.assertEqual(r3.status_code, 429)
        finally:
            main_module.RATE_LIMIT_PER_MINUTE = orig_limit
            main_module._request_log.clear()

    def test_docx_table_preserves_header_bold_and_inline_runs(self):
        source = Document()
        source.add_paragraph("TITULO DO TRABALHO")
        source.add_paragraph("NOME DO AUTOR")
        source.add_paragraph("INTRODUCAO")
        table = source.add_table(rows=2, cols=2)
        table.cell(0, 0).paragraphs[0].add_run("Indicador").bold = True
        table.cell(0, 1).paragraphs[0].add_run("Valor").bold = True
        table.cell(1, 0).paragraphs[0].add_run("Indice ").italic = True
        table.cell(1, 0).paragraphs[0].add_run("geral")
        table.cell(1, 1).paragraphs[0].add_run("95%")

        buf = io.BytesIO()
        source.save(buf)

        resp = self.client.post(
            "/format",
            data={"complete_missing": "false"},
            files={
                "file": (
                    "table_bold.docx",
                    buf.getvalue(),
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        out = Document(io.BytesIO(resp.content))
        self.assertEqual(len(out.tables), 1)
        self.assertTrue(out.tables[0].cell(0, 0).paragraphs[0].runs[0].bold)
        self.assertTrue(out.tables[0].cell(1, 0).paragraphs[0].runs[0].italic)
        self.assertFalse(bool(out.tables[0].cell(1, 0).paragraphs[0].runs[1].italic))

    def test_plain_text_explicit_long_citation_receives_4cm_indent(self):
        quote = (
            "A normatizacao de documentos cientificos requer rigor na organizacao dos "
            "elementos pre-textuais, textuais e pos-textuais para assegurar clareza, "
            "rastreabilidade das fontes consultadas e padronizacao visual uniforme em "
            "trabalhos academicos submetidos a bancas examinadoras (SILVA, 2020, p. 45)."
        )
        resp = self.client.post(
            "/format",
            data={
                "complete_missing": "false",
                "text": f"TITULO DO TRABALHO\nNOME DO AUTOR\nINTRODUCAO\n{quote}",
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        out = Document(io.BytesIO(resp.content))
        quote_para = next(p for p in out.paragraphs if p.text == quote)
        self.assertAlmostEqual(quote_para.paragraph_format.left_indent.cm, 4.0, places=1)
        self.assertEqual(quote_para.runs[0].font.size.pt, 10.0)
        self.assertEqual(quote_para.paragraph_format.line_spacing, 1.0)

    def test_sumario_includes_dynamic_toc_field_instruction(self):
        resp = self.client.post(
            "/format",
            data={
                "complete_missing": "true",
                "text": "TITULO\nAUTOR\nINTRODUCAO\nTexto.\nCONCLUSAO\nFim.",
            },
        )
        self.assertEqual(resp.status_code, 200, resp.text)
        out = Document(io.BytesIO(resp.content))
        sumario_para = next(p for p in out.paragraphs if p.text == "SUMÁRIO")
        instr_nodes = sumario_para._p.xpath(".//w:instrText/text()")
        self.assertTrue(any('TOC \\o "1-3"' in node for node in instr_nodes))

    def test_legacy_modules_are_importable_and_functional(self):
        block = DocumentBlock(original_text="INTRODUCAO", normalized_text="INTRODUCAO")
        extracted = FeatureExtractor.extract([block])
        self.assertEqual(extracted[0].features.semantic.semantic_intent, "INTRODUCAO")

        tree = ABNTStructure(
            textual_intro=[DocumentBlock(original_text="Intro")],
            textual_conclusion=[DocumentBlock(original_text="Fim")],
        )
        assembled = DocumentAssembler.assemble(tree)
        self.assertEqual([b.original_text for b in assembled], ["Intro", "Fim"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
