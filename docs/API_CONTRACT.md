# API Contract

All endpoints are prefixed with `/api`.

Response timestamps are ISO 8601 strings. IDs are strings.

## Common Types

```ts
type ContentType = "text" | "code" | "table" | "image" | "document" | "webpage" | "repository";
type TaskStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";
type SearchMode = "keyword" | "semantic" | "hybrid";
type GenerationType =
  | "learning_note"
  | "technical_summary"
  | "report_draft"
  | "ppt_outline"
  | "pptx"
  | "mind_map"
  | "table"
  | "image"
  | "diagram"
  | "video_script";
```

## Health

### `GET /api/health`

Returns:

```json
{ "status": "ok" }
```

## Ingestion

### `POST /api/ingest`

Use JSON for text/code/table/web snippets. Use `POST /api/ingest/files` for files.

Request:

```json
{
  "content_type": "text",
  "content": "Transformer attention notes...",
  "title": "Attention Notes",
  "source": "manual",
  "source_url": null,
  "metadata": {
    "course": "NLP"
  }
}
```

Returns:

```json
{
  "note_id": "note_...",
  "task_id": "task_...",
  "status": "queued",
  "message": "Ingestion accepted"
}
```

### `POST /api/ingest/files`

Multipart form:

- `file`: required.
- `content_type`: optional. If absent, backend infers type.
- `source`: optional.

Returns the same shape as `POST /api/ingest`.

## Knowledge

### `GET /api/knowledge`

Query params:

- `q`: optional keyword.
- `content_type`: optional.
- `tag`: optional, repeatable.
- `category`: optional.
- `limit`: default `20`.
- `offset`: default `0`.

Returns:

```json
{
  "items": [
    {
      "id": "note_...",
      "title": "Attention Notes",
      "content_type": "text",
      "summary": "Explains attention and query-key-value matching.",
      "tags": ["attention", "transformer"],
      "category": "machine_learning",
      "source": "manual",
      "source_url": null,
      "status": "ready",
      "created_at": "2026-07-04T10:00:00Z",
      "updated_at": "2026-07-04T10:00:00Z"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

### `GET /api/knowledge/{note_id}`

Returns:

```json
{
  "id": "note_...",
  "title": "Attention Notes",
  "content_type": "text",
  "content": "Original content...",
  "summary": "Summary...",
  "tags": ["attention"],
  "category": "machine_learning",
  "source": "manual",
  "source_url": null,
  "status": "ready",
  "chunks": [
    {
      "id": "chunk_...",
      "note_id": "note_...",
      "text": "Chunk text...",
      "chunk_index": 0,
      "score": null
    }
  ],
  "created_at": "2026-07-04T10:00:00Z",
  "updated_at": "2026-07-04T10:00:00Z"
}
```

### `PATCH /api/knowledge/{note_id}`

Editable fields:

```json
{
  "title": "New title",
  "summary": "Updated summary",
  "tags": ["tag1", "tag2"],
  "category": "backend"
}
```

### `DELETE /api/knowledge/{note_id}`

Deletes SQLite metadata and removes related vectors from FAISS mapping on next index compaction.

### `POST /api/knowledge/{note_id}/feedback`

Request:

```json
{
  "target": "summary",
  "rating": 1,
  "comment": "The summary missed the code example."
}
```

## Search

### `POST /api/search`

Request:

```json
{
  "query": "Compare FAISS and Chroma",
  "mode": "hybrid",
  "filters": {
    "content_types": ["text", "code"],
    "tags": ["vector database"],
    "category": null,
    "date_from": null,
    "date_to": null
  },
  "limit": 10
}
```

Returns:

```json
{
  "query": "Compare FAISS and Chroma",
  "mode": "hybrid",
  "results": [
    {
      "note_id": "note_...",
      "chunk_id": "chunk_...",
      "title": "Vector DB Notes",
      "snippet": "FAISS is an in-process vector index...",
      "score": 0.84,
      "content_type": "text",
      "tags": ["faiss", "rag"],
      "source": "manual"
    }
  ]
}
```

## Chat

### `POST /api/chat/sessions`

Request:

```json
{
  "title": "RAG design discussion",
  "scope": {
    "note_ids": [],
    "tags": ["rag"],
    "content_types": []
  }
}
```

Returns:

```json
{
  "id": "chat_...",
  "title": "RAG design discussion",
  "created_at": "2026-07-04T10:00:00Z"
}
```

### `POST /api/chat/sessions/{session_id}/messages`

Request:

```json
{
  "message": "结合我的资料，比较 FAISS 和 SQLite 的职责。",
  "retrieval_mode": "hybrid",
  "use_nanobot_reasoning": false,
  "top_k": 8
}
```

Returns:

```json
{
  "message_id": "msg_...",
  "answer": "FAISS should store vector index while SQLite stores metadata...",
  "citations": [
    {
      "note_id": "note_...",
      "chunk_id": "chunk_...",
      "title": "Architecture Notes",
      "snippet": "FAISS is used for semantic retrieval...",
      "score": 0.91
    }
  ],
  "trace": {
    "retrieval_mode": "hybrid",
    "used_nanobot": false,
    "model": "configured-llm-model"
  }
}
```

## Generation

### `POST /api/generate`

Async generation for PPTX, generated images, diagrams, video scripts, reports.

Request:

```json
{
  "generation_type": "pptx",
  "prompt": "生成一个关于个人知识库助手的技术汇报 PPT",
  "scope": {
    "note_ids": ["note_..."],
    "tags": ["rag"],
    "content_types": ["text", "code"]
  },
  "options": {
    "slide_count": 8,
    "theme": "dark_academic",
    "include_generated_images": true,
    "output_format": "pptx"
  }
}
```

Returns:

```json
{
  "task_id": "task_...",
  "status": "queued",
  "message": "Generation accepted"
}
```

### `POST /api/generate/preview`

Synchronous preview for Markdown, Mermaid mind map, PPT outline JSON.

Request:

```json
{
  "generation_type": "ppt_outline",
  "prompt": "基于知识库生成项目介绍 PPT 大纲",
  "scope": {
    "note_ids": [],
    "tags": ["hackathon"],
    "content_types": []
  },
  "options": {
    "slide_count": 6,
    "theme": "dark_academic"
  }
}
```

Returns:

```json
{
  "generation_type": "ppt_outline",
  "content": {
    "title": "NoteClaw",
    "slides": []
  },
  "citations": []
}
```

## Tasks

### `GET /api/tasks/{task_id}`

Returns:

```json
{
  "id": "task_...",
  "type": "generation",
  "status": "running",
  "progress": 0.4,
  "message": "Generating slide images",
  "result": null,
  "error": null,
  "created_at": "2026-07-04T10:00:00Z",
  "updated_at": "2026-07-04T10:01:00Z"
}
```

### `GET /api/tasks`

Query params:

- `status`: optional.
- `limit`: default `20`.

## Harness

### `POST /api/harness/jobs`

Reserved endpoint for nanobot-backed file operations, network search, repository collection, and cross-document reasoning.

Request:

```json
{
  "job_type": "web_research",
  "instruction": "搜索最近的个人知识库 RAG 项目并总结技术路线",
  "inputs": {
    "query": "personal knowledge base RAG assistant"
  }
}
```

Returns:

```json
{
  "task_id": "task_...",
  "status": "queued",
  "message": "Harness job accepted"
}
```
