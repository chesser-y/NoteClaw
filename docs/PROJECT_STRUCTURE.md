# NoteClaw Project Structure

This document defines the working structure for parallel frontend and backend development.

## Repository Layout

```text
NoteClaw/
  README.md
  docs/
    PROJECT_STRUCTURE.md
    API_CONTRACT.md
    FRONTEND_BACKEND_FLOW.md
    BACKEND_INTERNAL_INTERFACES.md
  backend/
    pyproject.toml
    uv.lock
    .env.example
    src/noteclaw_backend/
      main.py
      settings.py
      api/
        router.py
        routes/
          chat.py
          generate.py
          ingest.py
          knowledge.py
          search.py
          tasks.py
      schemas/
        common.py
        chat.py
        generation.py
        ingest.py
        knowledge.py
        search.py
        tasks.py
      services/
        ingestion.py
        retrieval.py
        generation.py
        chat.py
        task_service.py
        nanobot_harness.py
        providers/
          llm.py
          embedding.py
          image.py
          vision.py
      storage/
        sqlite.py
        repositories.py
        faiss_store.py
      domain/
        enums.py
  frontend/
    # Vue 3 + Vite + TailwindCSS, to be initialized by frontend team.
  nanobot/
    # Local source dependency. Backend installs nanobot-ai from ../nanobot.
  REFERENCE/
    # UI reference assets. Not required for backend runtime.
```

## Development Boundaries

Frontend owns:

- Vue pages, components, API client, state management, upload UX.
- Rendering chat sessions, citations, generation task progress, PPT/download results.
- Mapping user actions to the REST API defined in `API_CONTRACT.md`.

Backend owns:

- FastAPI endpoints and OpenAPI contract.
- SQLite metadata persistence.
- FAISS vector index persistence.
- OpenAI-compatible LLM, embedding, vision, and image provider adapters.
- Async task orchestration for OCR, vision enrichment, PPT/image generation, and nanobot harness jobs.

Nanobot integration boundary:

- Nanobot is reserved as a harness for file operations, network search, repository inspection, and multi-document reasoning.
- Current backend exposes stable harness-facing endpoints and service methods but does not assume the final nanobot invocation style.
- Final integration should be implemented behind `services/nanobot_harness.py`.

## MVP Feature Coverage

Required:

- Information input: text, code, table, image.
- Summary and tags: summary, keywords, category.
- Knowledge persistence: original content, summary, tags, source, created time.
- Retrieval: keyword and semantic search.
- Knowledge QA: answer with cited chunks.
- Content generation: learning notes, technical summary, report draft, PPT outline.

Reserved advanced features:

- Multimodal generation: table, image, diagram, video script.
- Personalization: feedback-aware tags, retrieval, summaries.
- Cross-document reasoning: nanobot-assisted multi-document retrieval and reasoning.
- Automatic information collection: nanobot-assisted web/paper/news/repository search.
