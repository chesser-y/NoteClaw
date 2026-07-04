## NoteClaw Backend

FastAPI backend managed by uv.

### Setup

```powershell
python -m uv sync
Copy-Item .env.example .env
```

Fill `.env` with OpenAI-compatible provider settings.

`nanobot-ai` is installed from the local source tree at `../nanobot` via uv:

```toml
[tool.uv.sources]
nanobot-ai = { path = "../nanobot" }
```

### Run

```powershell
python -m uv run noteclaw-backend
```

Health checks:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/api/health`
- `http://127.0.0.1:8000/api/docs`

API modules are currently contract-first stubs. They expose stable request and
response schemas for frontend integration while SQLite, FAISS, LLM provider,
PPT generation, and nanobot harness implementations are filled in.

### Dependency Scope

- `fastapi`, `uvicorn`: API server
- `openai`: OpenAI-compatible LLM, embedding, vision, image APIs
- `faiss-cpu`, `numpy`: vector indexing and search
- `python-pptx`: real `.pptx` generation
- `pillow`, `pytesseract`: image handling and OCR baseline
- `pydantic-settings`: environment-based configuration
- `nanobot-ai`: local source-built harness/agent runtime
