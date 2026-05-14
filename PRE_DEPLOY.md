# Pre-deploy checklist

## Local validation

Run the automated pre-deploy suite before publishing:

```powershell
.\.venv\Scripts\python.exe tests\predeploy_check.py
```

Expected result:

```text
Ran 6 tests
OK
```

The suite validates:

- Frontend static assets served by FastAPI.
- Text input to DOCX generation.
- DOCX upload with table preservation.
- Bibliographic reference handling.
- Empty input and corrupted DOCX errors.
- Netlify static config and API base URL support.

## Local run

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

## Netlify frontend

Netlify should publish:

```text
frontend
```

The current `netlify.toml` already points to this folder.

## Backend API

The FastAPI backend can be hosted on Render's free Web Service plan. This repo includes:

```text
render.yaml
.python-version
```

Render settings:

```text
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Plan: Free
Health URL: /health
```

Free Render web services spin down after inactivity, so the first request after a quiet period can take about a minute.

After the backend has a public URL, update:

```text
frontend/config.js
```

Example:

```js
window.SAAS_ABNT_CONFIG = {
  apiBaseUrl: "https://your-api.example.com",
};
```

On the backend host, define:

```text
ALLOWED_ORIGINS=https://your-site.netlify.app
```

Use comma-separated origins if needed.
