# Frontend to Backend Flow

Base URL in development:

```text
http://127.0.0.1:8000/api
```

## Core UI Areas

Suggested frontend pages:

- `/library`: knowledge card grid, filters, source/type/category/tag search.
- `/ingest`: paste text/code/table or upload image/files.
- `/chat`: knowledge-grounded QA sessions.
- `/generate`: report, note, PPT outline, mind map, image, diagram, video script generation.
- `/tasks`: async task progress and generated artifacts.
- `/settings`: provider keys, model names, storage status.

## Ingestion Flow

```text
User paste/upload
  -> POST /api/ingest
  -> backend creates note + chunks + task
  -> frontend receives note_id and optional task_id
  -> frontend polls GET /api/tasks/{task_id}
  -> when completed, refresh GET /api/knowledge/{note_id}
```

Image-specific behavior:

```text
Upload image
  -> OCR result becomes immediately searchable
  -> vision enrichment runs asynchronously
  -> note status changes from vision_pending to ready
```

## Search Flow

```text
User enters query/filter
  -> POST /api/search
  -> backend returns ranked notes/chunks
  -> frontend shows result list with score, tags, snippets, source
```

Search modes:

- `keyword`: SQLite LIKE/FTS later.
- `semantic`: embedding API + FAISS.
- `hybrid`: merge keyword and semantic results.

## Chat Flow

```text
User opens chat
  -> POST /api/chat/sessions
  -> frontend stores session_id

User asks question
  -> POST /api/chat/sessions/{session_id}/messages
  -> backend retrieves chunks from SQLite/FAISS
  -> backend calls LLM or nanobot reasoning path
  -> backend returns answer + citations + trace
```

MVP can use non-streaming responses. Streaming can be added later with:

```text
GET /api/chat/sessions/{session_id}/stream?message_id=...
```

## Generation Flow

```text
User chooses generation type and scope
  -> POST /api/generate
  -> backend creates generation task
  -> frontend polls GET /api/tasks/{task_id}
  -> completed task includes artifact links or structured content
```

Synchronous shortcut:

```text
POST /api/generate/preview
```

Use this only for small Markdown/PPT-outline previews. PPTX export and image generation should be async.

## Feedback Flow

```text
User clicks helpful/not helpful or edits tags
  -> POST /api/knowledge/{note_id}/feedback
  -> backend stores feedback
  -> future retrieval/summarization/tagging uses feedback signals
```

## Nanobot Harness Flow

Nanobot-backed jobs should be async:

```text
Frontend request
  -> POST /api/harness/jobs
  -> backend creates task
  -> nanobot executes file/search/reasoning operation
  -> frontend polls task status
```

Initial frontend should treat harness jobs like any other task.
