# API 接口契约

本文档是前后端联调的主要依据。除健康检查外，所有业务接口都以 `/api` 为前缀。

约定：

- 时间字段使用 ISO 8601 字符串。
- ID 使用字符串，后端生成，通常带业务前缀，例如 `note_...`、`task_...`。
- 当前后端实现是 contract-first stub，接口形状已经稳定，SQLite、FAISS、LLM、PPT、nanobot 的真实实现会在对应 service 层补齐。

### 模型适配层说明（内部）

NoteClaw 后端文本、embedding、视觉、图片生成能力暂由 `NoteClawOpenAICompat` 封装。

- 基础配置：
  - `OPENAI_COMPAT_BASE_URL`
  - `OPENAI_COMPAT_API_KEY`
  - `LLM_MODEL`
  - `EMBEDDING_MODEL`
  - `VISION_MODEL`
  - `IMAGE_MODEL`
- 按能力可选覆盖：
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

推荐默认模型：

- 对话：`gpt-4o`
- embedding：`text-embedding-3-small`
- 视觉理解：`gpt-4o`
- 图片生成：`gpt-image-1`

## 通用枚举

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

## 健康检查

### `GET /api/health`

用途：确认后端 API 服务可用。

返回：

```json
{ "status": "ok" }
```

## 信息输入

### `POST /api/ingest`

用途：录入文本、代码、表格、网页片段等 JSON 内容。

说明：

- 文本、代码、表格优先走这个接口。
- 图片、PDF、附件等文件走 `POST /api/ingest/files`。
- 后端最终会完成摘要、标签、分类、切块、embedding、SQLite 入库、FAISS 入索引。

请求：

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

字段说明：

- `content_type`：内容类型，必须是通用枚举中的一种。
- `content`：原始内容。
- `title`：可选标题；为空时后端可自动生成。
- `source`：来源，例如 `manual`、`upload`、`web`、`github`。
- `source_url`：来源链接，可为空。
- `metadata`：扩展元数据，前端可以传课程、项目、作者等信息。

返回：

```json
{
  "note_id": "note_...",
  "task_id": "task_...",
  "status": "queued",
  "message": "Ingestion accepted"
}
```

### `POST /api/ingest/files`

用途：上传图片、截图、PDF、文档、表格文件等。

请求类型：`multipart/form-data`

表单字段：

- `file`：必填，上传文件。
- `content_type`：可选，不传时后端根据文件类型推断。
- `source`：可选，来源描述。

返回：同 `POST /api/ingest`。

图片处理约定：

- 先 OCR，尽快让图片文字进入知识库。
- 再异步调用多模态模型做视觉理解。
- 视觉理解结果作为额外 chunk 追加到同一个 note 下。

## 知识库

### `GET /api/knowledge`

用途：获取知识条目列表，支持基础筛选和分页。

查询参数：

- `q`：可选，关键词。
- `content_type`：可选，内容类型。
- `tag`：可选，可重复传多个标签。
- `category`：可选，分类。
- `limit`：分页大小，默认 `20`。
- `offset`：分页偏移，默认 `0`。

返回：

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

用途：获取单个知识条目的完整内容和 chunks。

返回：

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

用途：更新知识条目的可编辑字段。

请求：

```json
{
  "title": "New title",
  "summary": "Updated summary",
  "tags": ["tag1", "tag2"],
  "category": "backend"
}
```

### `DELETE /api/knowledge/{note_id}`

用途：删除知识条目。

实现约定：

- SQLite 中删除或标记删除 note、chunk。
- FAISS 不直接按向量删除，先在 SQLite 的 `vector_mappings` 中标记 deleted。
- 后续做索引 compaction 时再重建 FAISS。

### `POST /api/knowledge/{note_id}/feedback`

用途：记录用户反馈，为个性化标签、摘要和检索排序预留数据。

请求：

```json
{
  "target": "summary",
  "rating": 1,
  "comment": "摘要漏掉了代码示例。"
}
```

字段说明：

- `target`：反馈目标，例如 `summary`、`tag`、`answer`、`retrieval`。
- `rating`：`1` 表示正反馈，`0` 表示中性，`-1` 表示负反馈。
- `comment`：可选文字说明。

## 搜索

### `POST /api/search`

用途：对知识库做关键词、语义或混合检索。

请求：

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

搜索模式：

- `keyword`：SQLite 关键词检索，后续可升级到 FTS。
- `semantic`：embedding API + FAISS。
- `hybrid`：关键词和语义结果融合排序。

返回：

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

## 知识问答

### `POST /api/chat/sessions`

用途：创建一个问答会话。

请求：

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

返回：

```json
{
  "id": "chat_...",
  "title": "RAG design discussion",
  "created_at": "2026-07-04T10:00:00Z"
}
```

### `POST /api/chat/sessions/{session_id}/messages`

用途：向指定会话发送问题，并获得基于知识库的回答。

请求：

```json
{
  "message": "结合我的资料，比较 FAISS 和 SQLite 的职责。",
  "retrieval_mode": "hybrid",
  "use_nanobot_reasoning": false,
  "top_k": 8
}
```

字段说明：

- `message`：用户问题。
- `retrieval_mode`：检索模式。
- `use_nanobot_reasoning`：是否启用 nanobot 跨文档推理路径。
- `top_k`：最多检索多少个 chunk。

返回：

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

实现约定：

- 普通 RAG：`RetrievalService -> LLMProvider -> answer + citations`。
- 跨文档推理：`RetrievalService broad context -> NanobotHarness -> answer + trace`。

## 内容生成

### `POST /api/generate`

用途：创建异步生成任务。适用于 PPTX、图片、图示、视频脚本、报告等耗时任务。

请求：

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

返回：

```json
{
  "task_id": "task_...",
  "status": "queued",
  "message": "Generation accepted"
}
```

### `POST /api/generate/preview`

用途：同步生成轻量预览。适用于 Markdown、Mermaid 思维导图、PPT 大纲 JSON。

请求：

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

返回：

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

生成类型说明：

- `learning_note`：学习笔记。
- `technical_summary`：技术总结。
- `report_draft`：报告草稿。
- `ppt_outline`：PPT 大纲。
- `pptx`：真实 `.pptx` 文件。
- `mind_map`：Mermaid 思维导图。
- `table`：结构化表格。
- `image`：调用生图 API。
- `diagram`：架构图或流程图。
- `video_script`：视频脚本。

## 任务

### `GET /api/tasks/{task_id}`

用途：查询异步任务状态。

返回：

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

用途：查询任务列表。

查询参数：

- `status`：可选，任务状态。
- `limit`：默认 `20`。
- `offset`：默认 `0`。

## Nanobot Harness

### `POST /api/harness/jobs`

用途：预留 nanobot 执行入口，用于文件操作、网络检索、代码仓库搜集、跨文档推理等。

请求：

```json
{
  "job_type": "web_research",
  "instruction": "搜索最近的个人知识库 RAG 项目并总结技术路线",
  "inputs": {
    "query": "personal knowledge base RAG assistant"
  }
}
```

返回：

```json
{
  "task_id": "task_...",
  "status": "queued",
  "message": "Harness job accepted"
}
```

实现约定：

- 前端把 nanobot job 当普通异步任务处理。
- 后端只通过 `NanobotHarness` service 调用 nanobot。
- 具体 nanobot CLI/API 调用方式后续参考 nanobot 项目再实现，不泄漏到路由层。
