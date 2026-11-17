# Relatório de Recuperação e Finalização — SaaS ABNT

Data: 17/11/2026  
Branch de trabalho: `fix/mvp-recovery` (derivada do estado local preservado sobre `main` / commit `ec940a7`)

## 1. Diagnóstico Inicial e Problemas Encontrados e Corrigidos

### Prioridade P0 (Bloqueadores Funcionais / Corrupção de Conteúdo / Erros 500)

1. **P0-1 — Parágrafos comuns com citações no texto ou anos eram classificados como `REFERENCE` e arrancados para `REFERÊNCIAS` (e Título/Autor eram perdidos na recompilação):**
   - *Causa raiz*: `SemanticNLPEngine.get_highest_intent` retornava intenções com scores baixos (`0.35–0.65`) por sobreposição parcial de caracteres (`SequenceMatcher`), sem limiar mínimo. `ScoringEngine` penalizava `PARAGRAPH` (`-4.0`) quando `keyword_match > 0` e favorecia `REFERENCE` com posição crescente (`+4.0`). Além disso, `Classifier._looks_like_reference` classificava qualquer frase contendo um ano `\b(19|20)\d{2}\b` (ex.: `"Segundo Silva (2020), ..."`) como referência bibliográfica. Na recompilação, `ValidationEngine` acusava `SECTION_MISPLACEMENT`, `CorrectionEngine` movia o parágrafo para o fim e `StructureBuilder.build` descartava blocos `BlockType.CAPA` (apagando Título e Autor em modo adaptativo).
   - *Correção*:
     - Adicionado limiar `MIN_INTENT_CONFIDENCE = 0.85` e restrições para textos longos (`> 90` caracteres / `> 8` palavras) ou terminados em `.` em `app/nlp_engine/engine.py`.
     - Recalibrados os pesos em `app/scoring_engine/engine.py`.
     - Atualizado `Classifier._looks_like_reference` em `app/classifier/engine.py` para exigir contexto da seção `REFERÊNCIAS` ou padrão explícito de entrada bibliográfica/identificador (`SOBRENOME, Nome` + ano/marcador ou `HTTP`/`DOI`/`ISBN`/`DISPONIVEL EM`), protegendo frases em prosa com citações no texto.
     - Adicionado `is_generated: bool = False` em `DocumentBlock` (`app/models/document.py`), permitindo que `StructureBuilder.build` filtre apenas blocos sintéticos gerados (`not block.is_generated`) e preserve todos os blocos originais do usuário durante o loop de recompilação.

2. **P0-2 — `RESUMO` enviado pelo usuário causava `HTTP 500 (Render violation: Missing Resumo)` quando `complete_missing=true`:**
   - *Causa raiz*: `Classifier` classificava `RESUMO` como `BlockType.HEADING`. `OrderingEngine._build_optional_pre_textual` retornava os blocos sem ajustar o tipo para `BlockType.PRE_TEXTUAL`, mas `ValidationEngine` e `RenderSanityCheckEngine` exigiam `BlockType.PRE_TEXTUAL` para `RESUMO`.
   - *Correção*: `OrderingEngine._build_optional_pre_textual` converte cabeçalhos pré-textuais reconhecidos para `BlockType.PRE_TEXTUAL` mantendo seu conteúdo; `ValidationEngine` e `RenderSanityCheckEngine` aceitam `BlockType.PRE_TEXTUAL` e `BlockType.HEADING` para `RESUMO`.

3. **P0-3 — Textos sem cabeçalho `INTRODUÇÃO` falhavam com `HTTP 500` em `complete_missing=true` ou transformavam parágrafos em `CAPA` em modo adaptativo:**
   - *Causa raiz*: `StructureBuilder.build` consumia até os 2 primeiros blocos do documento como `pre_textual` sem verificar se eram frases em prosa, e `OrderingEngine._build_textual_sequence` não inseria cabeçalho `1 INTRODUÇÃO` quando `textual_intro` tinha parágrafos sem título.
   - *Correção*: `StructureBuilder.build` interrompe a coleta pré-textual ao encontrar frases em prosa (terminadas em `.` com minúsculas), texto longo (`> 150` caracteres), numeração de capítulo, tabelas ou referências. Em `complete_missing=true`, `OrderingEngine._build_textual_sequence` insere o título da seção quando uma fase com conteúdo não possui cabeçalho de nível 1.

4. **P0-4 — Sobrescrita de títulos reais de capítulos e quebra de múltiplos capítulos/subseções:**
   - *Causa raiz*: `OrderingEngine._build_textual_sequence` substituía títulos legítimos como `FUNDAMENTAÇÃO TEÓRICA`, `METODOLOGIA` ou `CONSIDERAÇÕES FINAIS` por `2 DESENVOLVIMENTO` / `CONCLUSÃO` e não numerava múltiplos capítulos nem subseções (`2.1 ...`). `SemanticNormalizer` substituía sinônimos em vez de normalizar apenas acentuação de rótulos padrão.
   - *Correção*: `SemanticNormalizer` normaliza a grafia apenas quando `canonical_text == intent` (ex.: `INTRODUCAO` -> `INTRODUÇÃO`), preservando prefixo numérico e títulos como `CONSIDERAÇÕES FINAIS`. `StructureBuilder` preserva a fase atual em subseções (`1.1`, `2.1`) e encaminha múltiplos capítulos após `INTRODUÇÃO` ao desenvolvimento. `OrderingEngine` preserva os títulos originais em caixa alta, numera capítulos sequencialmente e renumera subseções incluindo-as no `SUMÁRIO`.

5. **P0-5 — `Parser._check_supported` rejeitava documentos DOCX válidos gerados por editores comuns (Word/LibreOffice/`python-docx`):**
   - *Causa raiz*: a verificação `if any(len(rpr) for rpr in body.xpath('.//w:rPr'))` bloqueava qualquer documento com definição de fonte (`w:rFonts`), tamanho (`w:sz`), idioma (`w:lang`) ou títulos inteiros em negrito (`w:b`), além de rejeitar marcadores benignos (`w:bookmarkStart`, `w:bookmarkEnd`, `w:proofErr`, `w:lastRenderedPageBreak`).
   - *Correção*: `app/parser/engine.py` mantém o bloqueio estrito contra perda silenciosa (imagens, cabeçalhos/rodapés com conteúdo, links, campos, notas, comentários, alterações controladas, tabelas mescladas/aninhadas, itálico/sublinhado/destaque/negrito parcial e negrito em tabelas/parágrafos longos), mas passa a aceitar metadados OOXML comuns de fonte/tamanho/idioma, marcadores internos benignos e cabeçalhos curtos uniformemente em negrito fora de tabelas, além de reconhecer citações longas pré-recuadas (`>= 3.0 cm`) e ignorar tabelas totalmente vazias.

### Prioridade P1 (Importantes)

- **P1-1 — Falso positivo de `SECTION_MISPLACEMENT` em documentos curtos com muitas referências:** `ValidationEngine` e `RenderSanityCheckEngine` verificavam `i < len(blocks) * 0.5`. Corrigido para validar se a referência aparece antes do cabeçalho `REFERÊNCIAS` (ou antes do último bloco textual quando não há cabeçalho), eliminando erro 500 quando a lista de referências supera metade dos blocos.
- **P1-2 — `IREqualityEngine` e `StructureBuilder`:** incluídos `table_data` e `starts_visible_page_numbering` no hash canônico de `app/ir_equality/engine.py`.
- **P1-3 — Quebra de página inicial e estilo pré-textual:** `app/ir_layer/engine.py` e `app/docx_generator/engine.py` evitam página em branco inicial quando o primeiro capítulo ocorre no índice `0`, e diferenciam negrito entre títulos pré-textuais curtos (`RESUMO`) e texto placeholder.
- **P1-4 — Módulos legados inconsistentes:** corrigido atributo inexistente `tree.textual_concl` -> `tree.textual_conclusion` em `app/document_assembler/engine.py`; delegado `FeatureExtractor.extract` para `FeatureEngine.extract` em `app/feature_extractor/engine.py`.
- **P1-5 — Metadados de capa/folha de rosto:** `StructureBuilder` e `OrderingEngine` passaram a aceitar linhas iniciais rotuladas (`Instituição:`, `Autor:`, `Título:`, `Subtítulo:`, `Cidade:`, `Ano:`, `Orientador:`, `Área:`, `Objetivo:`, `Natureza:`).

### Prioridade P2 (Melhorias de Interface e Documentação)

- **P2-1 — Frontend (`frontend/app.js` e `frontend/styles.css`):**
  - Verificação de disponibilidade da API alterada de `/openapi.json` para `/health`.
  - Validação preventiva no cliente para tamanho máximo (`5 MB`) e extensão `.docx`.
  - Tradução amigável de mensagens técnicas retornadas pelo backend (`"No input."`, `"Unable to parse DOCX input."`).
  - Adicionado destaque visual de foco por teclado (`:focus-within` na área de upload e `:focus-visible` nos controles).
- **P2-2 — Documentação:** atualizado `PRE_DEPLOY.md` com passos objetivos de validação no Linux Mint e checklist de publicação.

### Evolução V1 (Implementada na sequência para uso com documentos reais)

- **Preservação de formatação inline (`runs`) em parágrafos e tabelas simples DOCX:** criado `TextRun` em `app/models/document.py` (`bold`, `italic`, `underline`, `superscript`, `subscript`) e `table_runs` para células de tabela, com suporte completo no `Parser`, `IRLayer`, `IREqualityEngine`, `DOCXRenderEngine` e `RenderValidationEngine` (normalizando espaços internos). Arquivos DOCX reais com *itálico*, **negrito parcial**, sublinhado, sobrescrito, subscrito e cabeçalhos de tabela em negrito são aceitos e preservados sem perda, mantendo a recusa para riscado/realce (`strike`/`highlight`) e tabelas mescladas/aninhadas.
- **Ajustes normativos ABNT adicionais na renderização DOCX:**
  - Folha de Rosto (`OrderingEngine` + `IRLayer`): nota de natureza, objetivo, área e orientador recuados a `8,0 cm` à esquerda, justificados, fonte `10 pt` e espaçamento simples (`1,0`), conforme NBR 14724.
  - Referências (`RuleEngine` + `DOCXRenderEngine`): adicionado `space_after = 6 pt` entre entradas de referências bibliográficas.
  - Tabelas (`DOCXRenderEngine._apply_ibge_table_borders`): bordas verticais abertas (`left`, `right`, `insideV` = `none`) e horizontais visíveis (`top`, `bottom`, `insideH` = `single`), no padrão IBGE.
  - Hierarquia de seções (`w:outlineLvl`) e campo `TOC` dinâmico: capítulos (`0`) e subseções (`1`) recebem nível de tópico OOXML, e o bloco `SUMÁRIO` inclui instrução `TOC \o "1-3" \h \z \u` (`w:dirty="true"`) para atualização automática de páginas no Word/LibreOffice, mantendo a lista estática como fallback visível.
- **Detecção explícita de citação longa em texto puro:** `Classifier.classify` identifica parágrafos com mais de `240` caracteres terminados explicitamente com referência e página no padrão `(AUTOR, ANO, p. X)` como `BlockType.LONG_CITATION` (recuo `4,0 cm`, fonte `10 pt`, espaçamento `1,0`), preservando parágrafos longos comuns sem citação.
- **Campos opcionais de metadados no Frontend e Backend:** `POST /format` aceita `institution`, `author`, `title`, `advisor`, `city` e `year` (via `metadata_overrides` em `OrderingEngine` e `RecompilationLoopEngine`); `frontend/index.html`, `frontend/app.js` e `frontend/styles.css` exibem o bloco `#metadataFields` quando `Completar estrutura ABNT automaticamente` está marcado.
- **Rate limiting em memória por IP:** `app/main.py` aplica janela deslizante de 60s em `/format` (`RATE_LIMIT_PER_MINUTE`, padrão `60`, retornando HTTP `429` quando excedido).

---

## 2. Arquivos Modificados e Criados

### Modificados nesta entrega (sobre as alterações locais preservadas)
- [app/models/document.py](file:///home/luigikoga/Projetos/saasabnt/app/models/document.py)
- [app/main.py](file:///home/luigikoga/Projetos/saasabnt/app/main.py)
- [app/nlp_engine/engine.py](file:///home/luigikoga/Projetos/saasabnt/app/nlp_engine/engine.py)
- [app/normalizer/engine.py](file:///home/luigikoga/Projetos/saasabnt/app/normalizer/engine.py)
- [app/parser/engine.py](file:///home/luigikoga/Projetos/saasabnt/app/parser/engine.py)
- [app/feature_engine/engine.py](file:///home/luigikoga/Projetos/saasabnt/app/feature_engine/engine.py)
- [app/feature_extractor/engine.py](file:///home/luigikoga/Projetos/saasabnt/app/feature_extractor/engine.py)
- [app/scoring_engine/engine.py](file:///home/luigikoga/Projetos/saasabnt/app/scoring_engine/engine.py)
- [app/classifier/engine.py](file:///home/luigikoga/Projetos/saasabnt/app/classifier/engine.py)
- [app/structure_builder/engine.py](file:///home/luigikoga/Projetos/saasabnt/app/structure_builder/engine.py)
- [app/ordering_engine/engine.py](file:///home/luigikoga/Projetos/saasabnt/app/ordering_engine/engine.py)
- [app/recompilation_loop/engine.py](file:///home/luigikoga/Projetos/saasabnt/app/recompilation_loop/engine.py)
- [app/correction_engine/engine.py](file:///home/luigikoga/Projetos/saasabnt/app/correction_engine/engine.py)
- [app/validation_engine/engine.py](file:///home/luigikoga/Projetos/saasabnt/app/validation_engine/engine.py)
- [app/render_sanity_check/engine.py](file:///home/luigikoga/Projetos/saasabnt/app/render_sanity_check/engine.py)
- [app/ir_layer/engine.py](file:///home/luigikoga/Projetos/saasabnt/app/ir_layer/engine.py)
- [app/ir_equality/engine.py](file:///home/luigikoga/Projetos/saasabnt/app/ir_equality/engine.py)
- [app/rules_engine/engine.py](file:///home/luigikoga/Projetos/saasabnt/app/rules_engine/engine.py)
- [app/docx_generator/engine.py](file:///home/luigikoga/Projetos/saasabnt/app/docx_generator/engine.py)
- [app/render_validation/engine.py](file:///home/luigikoga/Projetos/saasabnt/app/render_validation/engine.py)
- [app/document_assembler/engine.py](file:///home/luigikoga/Projetos/saasabnt/app/document_assembler/engine.py)
- [frontend/index.html](file:///home/luigikoga/Projetos/saasabnt/frontend/index.html)
- [frontend/app.js](file:///home/luigikoga/Projetos/saasabnt/frontend/app.js)
- [frontend/styles.css](file:///home/luigikoga/Projetos/saasabnt/frontend/styles.css)
- [README.md](file:///home/luigikoga/Projetos/saasabnt/README.md)
- [PRE_DEPLOY.md](file:///home/luigikoga/Projetos/saasabnt/PRE_DEPLOY.md)
- [docs/CORRECOES.md](file:///home/luigikoga/Projetos/saasabnt/docs/CORRECOES.md)
- [tests/test_protection.py](file:///home/luigikoga/Projetos/saasabnt/tests/test_protection.py)

### Alterações locais prévias preservadas na árvore
- [frontend/config.js](file:///home/luigikoga/Projetos/saasabnt/frontend/config.js)
- [requirements.txt](file:///home/luigikoga/Projetos/saasabnt/requirements.txt)
- [tests/predeploy_check.py](file:///home/luigikoga/Projetos/saasabnt/tests/predeploy_check.py)
- [docs/AUDITORIA_TECNICA.md](file:///home/luigikoga/Projetos/saasabnt/docs/AUDITORIA_TECNICA.md)

### Criados
- [tests/test_mvp_flow.py](file:///home/luigikoga/Projetos/saasabnt/tests/test_mvp_flow.py)
- [RELATORIO_FINALIZACAO.md](file:///home/luigikoga/Projetos/saasabnt/RELATORIO_FINALIZACAO.md)

---

## 3. Testes Executados e Resultados

Todos os comandos abaixo foram executados sequencialmente no ambiente local após as edições de código:

| Verificação | Comando | Resultado |
|---|---|---|
| Integridade de pacotes | `.venv/bin/python -m pip check` | `No broken requirements found.` (exit code 0) |
| Suíte pre-deploy | `.venv/bin/python tests/predeploy_check.py` | **8 testes passaram** (`OK`) |
| Suíte estendida (`unittest discover`) | `PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` | **25 testes passaram** (`OK`: 17 em `test_mvp_flow.py` + 8 em `test_protection.py`) |
| Fluxo HTTP ao vivo (Uvicorn `127.0.0.1:8767`) | `GET /health`, `GET /`, `POST /format` (texto `complete_missing=true` com overrides), `POST /format` (DOCX com itálico/negrito e tabela `complete_missing=false`), `POST /format` (DOCX inválido) | `GET /health` HTTP 200 `{"status": "ok"}`; `GET /` HTTP 200 (6.245 bytes); `POST /format` texto HTTP 200 `finalized` (37.982 bytes, 29 parágrafos); `POST /format` DOCX HTTP 200 (37.724 bytes, cabeçalho em negrito preservado); `POST /format` inválido HTTP 400 |

---

## 4. Funcionalidades Concluídas no MVP

- Interface web estática servida pelo próprio FastAPI (`/`, `/styles.css`, `/app.js`, `/config.js`) com verificação de saúde (`/health`), seleção clara entre upload `.docx` (arrastar/clicar) ou texto colado, controle explícito do modo `Completar estrutura ABNT automaticamente` (`complete_missing`) e download direto do arquivo `.docx` gerado.
- Validação de entrada com limite de requisição de `5 MiB`, limite de `40 MiB` descompactado e `1.000` entradas ZIP no `.docx`, rejeitando arquivos corrompidos, vazios, protegidos por senha, com entradas duplicadas ou com envio simultâneo de arquivo e texto.
- Proteção contra perda silenciosa de conteúdo em `.docx` (recusando imagens, cabeçalhos/rodapés com conteúdo, hyperlinks, campos, notas, comentários, track changes, tabelas mescladas/aninhadas e formatação inline parcial não suportada), aceitando ao mesmo tempo documentos reais com metadados de fonte/tamanho/idioma, marcadores internos e cabeçalhos uniformemente em negrito.
- Classificação e ordenação com preservação de títulos originais de capítulos, subseções numeradas, sumário automático no modo completo, citações no texto mantidas nos parágrafos originais, citações longas (>3 linhas pré-recuadas) mantidas com recuo de 4 cm / fonte 10 / espaçamento simples, ordenação alfabética de referências e preservação de tabelas simples.
- Geração e verificação dual (`IR` + leitura reversa do binário `.docx` via `RenderValidationEngine`) com resposta HTTP pronta para download.

---

## 5. Normas ABNT Consideradas, Limitações e Pendências

### Normas ABNT consideradas como referência na implementação
As regras implementadas apoiam-se parcialmente em convenções das normas:
- **ABNT NBR 14724:2011** (Trabalhos acadêmicos — apresentação): página A4 (`21,0 x 29,7 cm`), margens superior/esquerda `3,0 cm` e inferior/direita `2,0 cm`, fonte Times New Roman `12 pt` no corpo e `10 pt` em citações longas/notas/legendas/tabelas, espaçamento `1,5` no texto e `1,0` em citações longas/referências/legendas, recuo de `1,25 cm` na primeira linha dos parágrafos, ordenação macro (pré-textuais, textuais e pós-textuais) e habilitação de numeração de páginas a partir da seção textual.
- **ABNT NBR 6024:2012** (Numeração progressiva das seções): numeração sequencial de capítulos primários e preservação de subseções (`2.1`, etc.).
- **ABNT NBR 6027:2012** (Sumário): geração da lista de seções no modo completo.
- **ABNT NBR 6028:2021** (Resumo): bloco pré-textual `RESUMO` (preservado quando enviado ou sinalizado por placeholder no modo completo).
- **ABNT NBR 10520:2023** (Citações): recuo esquerdo `4,0 cm`, fonte `10 pt`, espaçamento simples (`1,0`) para citações longas identificadas.
- **ABNT NBR 6023:2018** (Referências): seção `REFERÊNCIAS` ordenada alfabeticamente, fonte `10 pt` / alinhamento à esquerda / espaçamento simples (nota: a formatação padrão de fonte `10 pt` nas referências aplicada por `RuleEngine` pode diferir de regras institucionais ou interpretações que adotem `12 pt` com espaçamento simples — revise conforme o manual da instituição).

> **Aviso de conformidade:** A aprovação dos testes automatizados **não** comprova conformidade integral com todas as normas ABNT nem com regras específicas de cada instituição de ensino.

### Limitações técnicas conhecidas e pendências
1. **Reconstrução do DOCX e recusa preventiva:** o motor cria um novo DOCX a partir da representação intermediária (IR). Trechos de parágrafos e tabelas simples com negrito, itálico, sublinhado, sobrescrito e subscrito são preservados, mas imagens, cabeçalhos/rodapés com conteúdo, notas de rodapé/fim, links, campos automáticos, tabelas mescladas/aninhadas, riscado/realce e listas numeradas do Word são recusados explicitamente para evitar perda silenciosa.
2. **Sumário com campo `TOC` e lista estática:** os capítulos e subseções recebem `w:outlineLvl` e o `SUMÁRIO` inclui campo `TOC \o "1-3" \h \z \u` (`w:dirty="true"`), exigindo atualização de campos no Word/LibreOffice para preencher os números exatos de página; a lista estática abaixo serve como fallback.
3. **Tabelas simples:** o conteúdo textual e destaques básicos das células são preservados com bordas laterais abertas (padrão IBGE simplificado), sem manter larguras de coluna ou cores de preenchimento originais.
4. **Identificação heurística:** citações longas em texto puro só são identificadas automaticamente quando superam `240` caracteres e terminam com `(AUTOR, ANO, p. X)`; casos fora desse padrão exigem recuo prévio em DOCX ou revisão manual. Classificação e separação de metadados não rotulados assumem título e autor nos dois primeiros blocos curtos quando não há rótulos explícitos (`Título:`, `Autor:`, etc.) ou valores no formulário.
5. **Produção e segurança externa:** ainda não há autenticação, rate limiting na aplicação nem política de privacidade/retenção validada no repositório; testes de navegador via Playwright não foram reexecutados nesta sessão (a verificação de interface nesta rodada foi feita por inspeção estática e entrega HTTP via Uvicorn).

---

## 6. Instruções Reproduzíveis no Linux Mint (4 GB de RAM)

Execute os comandos sequencialmente (evitando processos paralelos pesados):

```bash
cd /home/luigikoga/Projetos/saasabnt

# 1. Validar ambiente virtual e dependências (caso recrie o venv, use python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt)
.venv/bin/python -m pip check

# 2. Executar testes leves em sequência
.venv/bin/python tests/predeploy_check.py
PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v

# 3. Iniciar a aplicação localmente
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Abra `http://127.0.0.1:8000` no navegador. Ao finalizar, pressione `Ctrl+C` no terminal.

---

## 7. Checklist de Publicação (Sem Deploy Automático Executado)

- [x] `GET /health` e `POST /format` validados localmente.
- [x] Todos os testes automatizados (`tests/predeploy_check.py`, `tests/test_protection.py`, `tests/test_mvp_flow.py`) aprovados após as correções finais.
- [x] Limites de payload (`5 MiB` HTTP, `40 MiB` descompactado, `1.000` entradas ZIP) ativos.
- [ ] Revisar e restringir `ALLOWED_ORIGINS` em `render.yaml` / painel do Render para o domínio final do frontend (substituindo `*`).
- [ ] Confirmar a URL pública final da API em `frontend/config.js` antes de publicar o frontend no Netlify (`netlify.toml`).
- [ ] Rodar auditoria de vulnerabilidades (`pip-audit -r requirements.txt`) e configurar rate limiting / política de privacidade no ambiente de hospedagem antes de abrir para usuários finais.
- [ ] Efetuar `push` da branch `main` local após revisar e autorizar o deploy.
