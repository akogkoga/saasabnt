# 🗺️ ABNT Formatter Engine — Project Map

## Stack
- Backend: Python 3.10+, FastAPI
- Libraries: python-docx, pydantic
- Rules: ABNT NBR 14724 (Deterministic Engine)

## Folder Structure
app/
  models/               → Pydantic schemas and data models
  parser/               → Text and DOCX input extraction logic
  rules_engine/         → Block classification and style assignment
  structure_builder/    → Assembly of the ABNT document tree
  docx_generator/       → Final DOCX file creation using python-docx
  main.py               → API entry point

## Pipeline
1. **INPUT**: Text or DOCX file.
2. **PARSER**: Extracts raw text blocks.
3. **CLASSIFIER**: Identifies block types (Heading, Paragraph, Citation, etc.).
4. **BUILDER**: Organizes blocks into Pre-textual, Textual, and Post-textual.
5. **STYLER**: Applies ABNT specific formatting rules.
6. **GENERATOR**: Produces the .docx file.

## Key Files
app/models/document.py  → Core ABNT data structure
app/rules_engine/engine.py → Deterministic classification logic
app/docx_generator/engine.py → DOCX styling and export logic

## Last updated: 2026-05-14
