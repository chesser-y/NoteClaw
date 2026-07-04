# NoteClaw

Personal knowledge base assistant for the hackathon project.

## Confirmed Technical Route

- Frontend: Vue 3 + Vite + TailwindCSS, visually inspired by the provided dark academic SaaS reference.
- Backend: FastAPI.
- Python dependency management: uv.
- Metadata storage: SQLite.
- Vector retrieval: embedding API + FAISS.
- LLM provider: OpenAI-compatible API.
- Multimodal ingestion: OCR first, async vision-model enrichment.
- Content generation: Markdown reports, Mermaid mind maps, and real `.pptx` export with theme templates and generated images.

Backend lives in `backend/`.

## Development Docs

- `docs/PROJECT_STRUCTURE.md`: project layout and development boundaries.
- `docs/API_CONTRACT.md`: frontend/backend REST contract.
- `docs/FRONTEND_BACKEND_FLOW.md`: UI-to-API call flows.
- `docs/FRONTEND_API_CLIENT.md`: suggested TypeScript API client and chat session logic.
- `docs/BACKEND_INTERNAL_INTERFACES.md`: SQLite, FAISS, provider, and nanobot harness boundaries.
