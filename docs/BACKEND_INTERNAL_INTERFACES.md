# 后端内部接口边界

本文档用于后端并行开发，明确 SQLite、FAISS、模型 provider、业务 service 和 nanobot harness 的职责边界。

## SQLite 职责

SQLite 存所有业务元数据，不直接承担向量计算。

需要存储：

- notes：知识条目。
- chunks：切分后的文本块。
- vector_mappings：chunk 和 FAISS row id 的映射。
- chat_sessions：问答会话。
- chat_messages：问答消息。
- tasks：异步任务。
- artifacts：生成产物，例如 pptx、图片、报告。
- feedback：用户反馈。
- source_jobs：自动信息搜集任务。

建议基础表：

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

## FAISS 职责

FAISS 只存向量索引和内部 row id，不存业务内容。

接口：

```python
class VectorStore:
    def add(self, vectors: list[list[float]], chunk_ids: list[str]) -> None: ...
    def search(self, vector: list[float], limit: int) -> list[VectorHit]: ...
    def mark_deleted(self, chunk_ids: list[str]) -> None: ...
    def save(self) -> None: ...
    def load(self) -> None: ...
```

实现建议：

- embedding 向量先归一化。
- 使用 `IndexFlatIP`，实现类 cosine similarity 的效果。
- `chunk_id -> faiss_row_id` 存 SQLite。
- 删除采用 lazy deletion：SQLite 标记 deleted，后续重建索引时清理。
- FAISS 文件路径使用 `settings.faiss_index_path`。

## Provider 职责

所有模型供应商都隐藏在 provider adapter 后面，业务 service 不直接依赖具体 API。

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

模型配置来自 `.env`：

- `OPENAI_COMPAT_BASE_URL`
- `OPENAI_COMPAT_API_KEY`
- `LLM_MODEL`
- `EMBEDDING_MODEL`
- `VISION_MODEL`
- `IMAGE_MODEL`
- 按能力可选覆盖（推荐在成本敏感场景使用）：
  - `OPENAI_COMPAT_CHAT_API_KEY`
  - `OPENAI_COMPAT_CHAT_BASE_URL`
  - `OPENAI_COMPAT_CHAT_MODEL`
  - `OPENAI_COMPAT_EMBEDDING_API_KEY`
  - `OPENAI_COMPAT_EMBEDDING_BASE_URL`
  - `OPENAI_COMPAT_EMBEDDING_MODEL`
  - `OPENAI_COMPAT_VISION_API_KEY`
  - `OPENAI_COMPAT_VISION_BASE_URL`
  - `OPENAI_COMPAT_VISION_MODEL`
  - `OPENAI_COMPAT_IMAGE_API_KEY`
  - `OPENAI_COMPAT_IMAGE_BASE_URL`
  - `OPENAI_COMPAT_IMAGE_MODEL`

实现建议：

- 缺省只配置主网关与全局 key。
- 按能力覆盖时，仅对目标能力覆盖 `api_key`、`base_url`、`model`。
- 默认值：对话 `gpt-4o`，embedding `text-embedding-3-small`，视觉 `gpt-4o`，图像 `gpt-image-1`。

## IngestionService

职责：

- 推断内容类型。
- 图片先 OCR。
- 内容切块。
- 调 LLM 生成摘要、标签、分类。
- 原文、摘要、标签、来源写入 SQLite。
- 调 embedding provider。
- 向 FAISS 添加向量。
- 图片多模态理解异步补充。

接口：

```python
class IngestionService:
    async def ingest_text(request: IngestRequest) -> IngestResponse: ...
    async def ingest_file(file: UploadFile, content_type: str | None) -> IngestResponse: ...
```

## RetrievalService

职责：

- SQLite 关键词检索。
- embedding + FAISS 语义检索。
- hybrid 融合排序。
- 返回 chunks 和 note metadata。

接口：

```python
class RetrievalService:
    async def search(request: SearchRequest) -> SearchResponse: ...
    async def retrieve_for_question(query: str, top_k: int, scope: dict) -> list[Citation]: ...
```

## ChatService

职责：

- 创建和管理问答会话。
- 为问题检索相关 chunks。
- 普通 RAG 路径调用 LLM。
- 跨文档推理路径调用 nanobot harness。
- 返回 answer、citations、trace。

普通问答路径：

```text
question -> RetrievalService -> LLMProvider -> answer + citations
```

跨文档推理路径：

```text
question -> RetrievalService broad context -> NanobotHarness -> answer + trace
```

## GenerationService

职责：

- 根据 scope 检索知识库上下文。
- 生成 Markdown、JSON、Mermaid、PPT outline。
- PPTX 任务中先生成 PPT JSON，再生成部分配图，最后用 python-pptx 渲染真实 `.pptx`。
- 保存 artifact 和 task result。

PPT JSON 结构约定：

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

建议首批支持 layout：

- `cover`
- `section`
- `text_image`
- `comparison`
- `quote`
- `summary`

## NanobotHarness

nanobot 作为执行 harness，不直接暴露给前端。

预留接口：

```python
class NanobotHarness:
    async def run_job(self, job_type: str, instruction: str, inputs: dict) -> dict: ...
    async def web_research(self, query: str, constraints: dict | None = None) -> dict: ...
    async def repository_research(self, repo_url: str, instruction: str) -> dict: ...
    async def cross_document_reasoning(self, instruction: str, documents: list[dict]) -> dict: ...
    async def file_operation(self, instruction: str, workspace: str, inputs: dict) -> dict: ...
```

用途：

- 文件编辑和文件读取。
- 网络检索。
- 论文、新闻、代码仓库搜集。
- 多文档综合推理。
- 复杂任务的工具调用链。

实现要求：

- 路由层只调用 `NanobotHarness`。
- `NanobotHarness` 内部再决定使用 CLI、Python API 或 OpenAI-compatible server。
- 所有 harness 任务都应该落到 `tasks` 表，前端通过 task 轮询。
- 文件操作必须限制 workspace，避免越权修改。
