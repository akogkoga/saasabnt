# SaaS ABNT — formatador de documentos

Aplicação FastAPI com interface web para gerar um DOCX a partir de texto ou de um DOCX simples. A formatação é automática e precisa de revisão: o projeto não comprova conformidade integral com normas ABNT ou regras de uma instituição.

## Executar no Linux

Requisitos: Python 3.12, pip e venv. No diretório do projeto:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Acesse `http://127.0.0.1:8000`. O frontend usa a API local quando acessado por `localhost` ou `127.0.0.1`; em outros endereços usa a URL de `frontend/config.js`. Para finalizar, pressione Ctrl+C. A entrada é limitada a 5 MiB por requisição; DOCX descompactado, a 40 MiB.

## Testes

```bash
.venv/bin/python tests/predeploy_check.py
PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
```

Os testes usam documentos sintéticos. Não envie documentos pessoais para serviços que não tenham sido avaliados quanto à privacidade.

## Limitações importantes

- O processamento reconstrói o DOCX: trechos de parágrafos e tabelas simples com negrito, itálico, sublinhado, sobrescrito e subscrito são preservados, mas há verificação para recusar recursos que o renderizador não preserva, como imagens, cabeçalhos, rodapés com conteúdo, links, campos, riscado/realce e tabelas mescladas/aninhadas. Ela não prova detecção de todos os recursos possíveis de DOCX. Revise o resultado e preserve o original.
- Tabelas simples têm seu texto e destaques básicos reconstruídos com bordas laterais abertas (estilo IBGE simplificado); larguras de coluna e cores originais não são preservadas. A estrutura e a ordem podem ser alteradas. Texto colado perde formatação original.
- No modo automático, campos opcionais da interface permitem preencher Instituição, Autor, Título, Orientador, Cidade e Ano; campos não informados usam placeholders genéricos para revisão. O sumário gerado inclui lista de seções e campo `TOC` para atualização de páginas no Word/LibreOffice. Citações longas em texto puro só são identificadas automaticamente quando terminam com `(AUTOR, ANO, p. X)`; revise-as manualmente.
- O endpoint `/format` conta com limite de taxa em memória por IP (`RATE_LIMIT_PER_MINUTE`, padrão 60/min), além dos limites de tamanho (`5 MiB` / `40 MiB` descompactado). Isso não substitui autenticação, proxies reversos ou política de privacidade/retenção para produção.

## Implantação

`render.yaml` inicia a API; `netlify.toml` publica o frontend. Configure `ALLOWED_ORIGINS` com as origens reais do frontend antes da publicação e revise a URL da API em `frontend/config.js`. As configurações declaradas não demonstram que um serviço está publicado ou seguro. Deploy exige validação e autorização separadas.
