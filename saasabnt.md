# 🗺️ ABNT Formatter Engine — Project Map

## Stack
- Backend: Python 3.10+, FastAPI
- Formatos: python-docx (manipulação física do arquivo DOCX)
- NLP e Texto: difflib nativo (Levenshtein)
- Validação: Pydantic (strict schemas)

## Folder Structure
app/
  models/             → Schemas Pydantic (DocumentBlock, IRDocument, Metadata)
  parser/             → Rich Parsing Híbrido (Extração de texto e metadados visuais)
  normalizer/         → Sanitização de strings e tokens
  feature_engine/     → Vetorização local e estrutural (Lexical, Structural, Semantic)
  global_context/     → Análise de densidade do documento
  nlp_engine/         → Mapeamento de intenção semântica via distâncias
  scoring_engine/     → Softmax Engine probabilística
  classifier/         → Decisão baseada em argmax + Stability Lock
  structure_builder/  → Agrupamento de fases ABNT
  ordering_engine/    → Constraint Solver para sequenciamento hierárquico
  validation_engine/  → Validação estrutural ativa (Gatekeeper)
  correction_engine/  → Ações determinísticas para sanar erros
  convergence_engine/ → Prova de equivalência matemática (IR Hashing)
  recompilation_loop/ → Orquestração do ciclo de feedback e auto-correção
  ir_equality/        → Criptografia e hashes de estado para prova de isomorfismo
  ir_layer/           → Geração de Representação Intermediária (SemanticIR e StyleIR)
  render_validation/  → Validação física reversa do binário gerado
  render_feedback_loop/ → Validação dual (Dual Check) pré-entrega
  docx_generator/     → Consumidor de IR e renderização física de Word
  main.py             → Endpoint FastAPI e orquestração do pipeline V6

## Routes / Endpoints
POST /format          → Pipeline de compilação formal (Upload DOCX/TXT -> DOCX Formatado ABNT)

## Key Files
app/models/document.py         → O coração do State Contract Model (todas as structs)
app/main.py                    → Onde o pipeline é declarado passo a passo
app/ordering_engine/engine.py  → O constraint solver que aplica a numeração e sequência

## Last updated: 2026-05-14 (V6 Ultimate Compiler)
