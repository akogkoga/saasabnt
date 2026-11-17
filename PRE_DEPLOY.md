# Verificação antes de publicar (Pre-Deploy)

Consulte também o [README.md](README.md) para visão geral e limitações conhecidas.

## 1. Validação local no Linux Mint

No diretório do projeto (`/home/luigikoga/Projetos/saasabnt`), execute em sequência (adequado para máquinas com 4 GB de RAM):

```bash
.venv/bin/python -m pip check
.venv/bin/python tests/predeploy_check.py
PYTHONPATH=. .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
```

Para validar o fluxo completo no navegador:

```bash
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Acesse `http://127.0.0.1:8000` e valide com documentos sintéticos:
- Indicador de status exibe `API online` (`/health`).
- Formatação via texto colado (modo adaptativo e modo automático) gera e baixa o `.docx`.
- Upload de arquivo `.docx` válido (com tabela simples, cabeçalhos e parágrafos) gera e baixa o `.docx`.
- Arquivos inválidos, vazios ou com recursos não suportados (imagens, cabeçalhos/rodapés com conteúdo, negrito parcial, tabelas mescladas) exibem erro claro sem travar a aplicação.

## 2. Checklist de publicação

### Backend API (Render)
- Arquivos utilizados: `render.yaml`, `.python-version` (`3.12`) e `requirements.txt`.
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check: `GET /health` retorna HTTP 200 `{"status": "ok"}`.
- **CORS (`ALLOWED_ORIGINS`)**: substitua `*` em `render.yaml` / painel do Render pela origem real do frontend (ex.: `https://seu-site.netlify.app`).
- **Limites**: o app impõe 5 MiB por requisição (`MAX_REQUEST_BYTES`), 40 MiB descompactado e 1.000 entradas ZIP; configure também rate limiting e proteção no proxy/hospedagem.

### Frontend estático (Netlify)
- Arquivo utilizado: `netlify.toml` (`publish = "frontend"`).
- Revise `frontend/config.js` para garantir que a URL fora de `localhost`/`127.0.0.1`/`[::1]` aponte para a URL pública da API em produção.
- Nota: no plano gratuito do Render, a API hiberna após inatividade; a primeira requisição pode levar cerca de 1 minuto.

## 3. Segurança, privacidade e normas

- Execute auditoria de dependências (`pip-audit -r requirements.txt`, se instalado) antes do deploy.
- Não envie documentos reais ou sigilosos antes de validar política de privacidade e retenção da hospedagem.
- Não apresente o resultado como conformidade ABNT integral sem revisão humana: o motor não comprova aprovação institucional nem preserva recursos complexos de DOCX recusados na validação.
