# Backend Internal Interfaces

This document defines boundaries for backend parallel work.

## SQLite Responsibility

SQLite stores all business metadata:

- notes
- chunks
- chat sessions and messages
- generation tasks
- artifacts
- feedback
- source collection jobs

Suggested tables:

```sql
notes(
  id text primary key,
  title text not null,
  content_type text not null,
  content text not null,
  summary text,
  tags_json text not null,
  category text,
  source text,
  source_url text,
  status text not null,
  metadata_json text not null,
  created_at text not null,
  updated_at text not null
);

chunks(
  id text primary key,
  note_id text not null,
  chunk_index integer not null,
  text text not null,
  metadata_json text not null,
  created_at text not null
);

vector_mappings(
  chunk_id text primary key,
  faiss_row_id integer not null,
  embedding_model text not null,
  deleted integer not null default 0
);

tasks(
  id text primary key,
  type text not null,
  status text not null,
  progress real not null,
  message text,
  payload_json text not null,
  result_json text,
  error text,
  created_at text not null,
  updated_at text not null
);
```

## FAISS Responsibility

FAISS stores only normalized embedding vectors and integer row IDs.

Interface:

```python
class VectorStore:
    def add(self, vectors: list[list[float]], chunk_ids: list[str]) -> None: ...
    def search(self, vector: list[float], limit: int) -> list[VectorHit]: ...
    def mark_deleted(self, chunk_ids: list[str]) -> None: ...
    def save(self) -> None: ...
    def load(self) -> None: ...
```

FAISS index recommendation:

- Normalize embeddings.
- Use `IndexFlatIP` for cosine-like similarity.
- Store `chunk_id -> faiss_row_id` in SQLite.
- Use lazy deletion in SQLite mapping and compact later.

## Provider Responsibility

All model vendors must be hidden behind provider adapters.

```python
class LLMProvider:
    async def complete_json(self, messages: list[dict], schema: dict | None = None) -> dict: ...
    async def complete_text(self, messages: list[dict]) -> str: ...

class EmbeddingProvider:
    async def embed_texts(self, texts: list[str]) -> list[list[float]]: ...

class VisionProvider:
    async def understand_image(self, image_path: str, ocr_text: str | None = None) -> dict: ...

class ImageProvider:
    async def generate_image(self, prompt: str, size: str = "1024x1024") -> str: ...
```

## Ingestion Service

Responsibilities:

- infer content type
- OCR image first
- chunk content
- call summary/tag/category prompt
- store note/chunks in SQLite
- call embedding provider
- add vectors to FAISS
- enqueue async vision enrichment for images

Contract:

```python
class IngestionService:
    async def ingest_text(request: IngestRequest) -> IngestResponse: ...
    async def ingest_file(file: UploadFile, content_type: str | None) -> IngestResponse: ...
```

## Retrieval Service

Responsibilities:

- keyword search via SQLite
- semantic search via embedding + FAISS
- hybrid rank merge
- return chunks with note metadata

Contract:

```python
class RetrievalService:
    async def search(request: SearchRequest) -> SearchResponse: ...
    async def retrieve_for_question(query: str, top_k: int, scope: dict) -> list[Citation]: ...
```

## Chat Service

Responsibilities:

- manage chat sessions
- retrieve relevant context
- call LLM for normal RAG
- optionally delegate cross-document reasoning to nanobot harness
- return answer with citations

Normal QA path:

```text
question -> RetrievalService -> LLMProvider -> answer + citations
```

Nanobot reasoning path:

```text
question -> RetrievalService broad context -> NanobotHarness -> synthesized answer + trace
```

## Generation Service

Responsibilities:

- collect scope context through retrieval
- create structured Markdown / JSON / Mermaid / PPT outline
- for PPTX: generate PPT JSON, generate selected images, render with python-pptx
- store artifacts and task results

PPT contract:

```json
{
  "title": "Deck title",
  "theme": "dark_academic",
  "slides": [
    {
      "layout": "cover",
      "title": "NoteClaw",
      "subtitle": "Personal knowledge assistant",
      "image_prompt": "dark academic knowledge graph interface"
    }
  ]
}
```

## Nanobot Harness Service

Reserved backend boundary:

```python
class NanobotHarness:
    async def run_job(self, job_type: str, instruction: str, inputs: dict) -> dict: ...
    async def web_research(self, query: str, constraints: dict | None = None) -> dict: ...
    async def repository_research(self, repo_url: str, instruction: str) -> dict: ...
    async def cross_document_reasoning(self, instruction: str, documents: list[dict]) -> dict: ...
    async def file_operation(self, instruction: str, workspace: str, inputs: dict) -> dict: ...
```

Initial implementation may return `501 Not Implemented` or queued task placeholders.

Final implementation should be developed after studying nanobot's native CLI/API usage and safety model.
