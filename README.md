# NoteClaw

NoteClaw 是一个面向个人知识管理的多模态知识库智能助手。它用于把文本、代码、表格、图片、PPTX 等资料沉淀为可检索、可问答、可生成的个人知识库，并通过引用、复核和评测机制提高输出的可追溯性。

本文档提供本地安装、配置、运行、Demo 导入、自有数据接入和常用接口说明。更完整的后端实现细节见 [`docs/BACKEND_TECHNICAL_PIPELINE.md`](docs/BACKEND_TECHNICAL_PIPELINE.md)。

## 1. 项目简介

项目采用前后端分离结构：后端位于 `backend/`，提供 FastAPI 服务和知识处理能力；前端位于 `frontend/`，提供知识库、检索、问答、生成、任务、时间线和知识图谱等工作台页面。运行时数据默认保存到 `storage/`，示例数据位于 `data/demo_subset/`。

## 2. 环境要求

- Python >= 3.11
- Node.js 与 npm
- `uv`
- 可用的 OpenAI-compatible chat 和 embedding 服务
- 可选 Vision/OCR/Image 模型，用于图片理解、OCR 增强和图片生成
- 可选 Tesseract，用于本地 OCR 基线
- 可选 Playwright 浏览器环境，用于 HTML slide 渲染和 PPTX 生成

## 3. 安装与配置

后端依赖：

```bash
cd backend
python -m uv sync
cp .env.example .env
```

Windows PowerShell：

```powershell
cd backend
python -m uv sync
Copy-Item .env.example .env
```

前端依赖：

```bash
cd frontend
npm install
```

编辑 `backend/.env`，至少配置共享模型网关：

```bash
OPENAI_COMPAT_BASE_URL=https://your-openai-compatible-endpoint/v1
OPENAI_COMPAT_API_KEY=sk-...
LLM_MODEL=gpt-4o
EMBEDDING_MODEL=text-embedding-3-small
VISION_MODEL=gpt-4o
IMAGE_MODEL=gpt-image-1

STORAGE_DIR=storage
FAISS_INDEX_PATH=storage/faiss/index.faiss
SQLITE_PATH=storage/noteclaw.db
```

也可以按能力拆分 endpoint：

```bash
OPENAI_COMPAT_CHAT_BASE_URL=
OPENAI_COMPAT_CHAT_API_KEY=
OPENAI_COMPAT_CHAT_MODEL=

OPENAI_COMPAT_EMBEDDING_BASE_URL=
OPENAI_COMPAT_EMBEDDING_API_KEY=
OPENAI_COMPAT_EMBEDDING_MODEL=

OPENAI_COMPAT_VISION_BASE_URL=
OPENAI_COMPAT_VISION_API_KEY=
OPENAI_COMPAT_VISION_MODEL=

OPENAI_COMPAT_OCR_BASE_URL=
OPENAI_COMPAT_OCR_API_KEY=
OPENAI_COMPAT_OCR_MODEL=deepseek-ai/DeepSeek-OCR

OPENAI_COMPAT_IMAGE_BASE_URL=
OPENAI_COMPAT_IMAGE_API_KEY=
OPENAI_COMPAT_IMAGE_MODEL=
```

前端可选配置：

```bash
# frontend/.env.local
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

不配置时，前端默认请求 `/api`。

## 4. 快速开始

本仓库自带一个轻量 demo 数据集 `data/demo_subset/`，可用于从空知识库快速复现“入库、检索、问答、生成、图谱、评测”的完整流程。下面步骤假设已经完成第 3 节的依赖安装和 `.env` 配置。

Step 1 - 启动后端：

```bash
cd backend
python -m uv run noteclaw-backend
```

后端默认地址：

```text
http://127.0.0.1:8000
http://127.0.0.1:8000/api/docs
```

Step 2 - 启动前端：

```bash
cd frontend
npm run dev -- --host 127.0.0.1
```

前端默认地址：

```text
http://127.0.0.1:5173/
```

Step 3 - 检查服务健康状态：

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/api/health
```

预期响应：

```json
{"status":"ok"}
```

Step 4 - 导入 demo 数据。该脚本会把 `data/demo_subset/text`、`code`、`tables`、`images` 下的文件上传到 `POST /api/ingest/files`：

```bash
python scripts/seed_demo.py \
  --base-url http://127.0.0.1:8000 \
  --root data/demo_subset
```

导入成功后，后端会完成：

```text
文件解析 -> 摘要/标签/分类 -> chunking -> SQLite 入库 -> embedding -> FAISS 索引
```

Step 5 - 打开前端验证结果：

```text
http://127.0.0.1:5173/library    # 查看入库知识
http://127.0.0.1:5173/research   # keyword / semantic / hybrid 检索
http://127.0.0.1:5173/graph      # tag / note / category 知识图谱
http://127.0.0.1:5173/studio     # 笔记、报告、PPT 大纲等生成
```

可尝试的问题：

```text
结合我的资料，比较 FAISS 和 SQLite 的职责。
compare code retrieval examples
spatial transcriptomics feature MAE
基于知识库生成一个 NoteClaw 技术汇报 PPT 大纲
```

Step 6 - 可选：运行 API 评测。若请求中不传 `items`，后端会读取 `data/demo_subset/qa/demo_questions.json`：

```bash
curl -X POST http://127.0.0.1:8000/api/harness/evaluate \
  -H "Content-Type: application/json" \
  -d '{"mode":"hybrid","top_k":5,"generate_answers":true,"judge_answers":true}'
```

常用命令汇总：

| Command | Purpose |
| --- | --- |
| `python -m uv run noteclaw-backend` | 启动 FastAPI 后端 |
| `npm run dev -- --host 127.0.0.1` | 启动 Vite 前端 |
| `python scripts/seed_demo.py --root data/demo_subset` | 批量导入 demo 数据 |
| `curl /api/harness/evaluate` | 运行检索和回答质量评测 |
| `npm run build` | 构建前端生产产物 |

## 5. 使用自有数据

接入自有数据有三种推荐方式：

1. 用前端 Inbox/Library 上传资料，适合交互式使用。
2. 调用 `POST /api/ingest` 或 `POST /api/ingest/files`，适合脚本化上传少量数据。
3. 按 `data/demo_subset` 的目录约定组织文件，然后复用 `scripts/seed_demo.py --root <your_data_dir>` 批量上传。

### 5.1 目录格式

如果希望批量导入，推荐准备如下目录：

```text
data/my_notes/
  text/
    paper_notes.md
    course_summary.txt
  code/
    example.py
    service.ts
  tables/
    experiment_results.csv
  images/
    screenshot.png
    chart.jpg
```

然后运行：

```bash
python scripts/seed_demo.py \
  --base-url http://127.0.0.1:8000 \
  --root data/my_notes
```

当前 `seed_demo.py` 会识别以下子目录：

| Directory | Uploaded source | Typical files |
| --- | --- | --- |
| `text/` | `demo:text` | `.md`, `.txt`, `.html` |
| `code/` | `demo:code` | `.py`, `.js`, `.ts`, `.go`, `.rb`, `.java` |
| `tables/` | `demo:table` | `.csv`, `.tsv` |
| `images/` | `demo:image` | `.png`, `.jpg`, `.jpeg` |

脚本的 source 前缀目前固定为 `demo:*`，如果要改成课程名、项目名或数据集名，可以复制 `scripts/seed_demo.py` 后调整 `KIND_TO_PREFIX`。

### 5.2 单条 JSON 入库

文本、代码、表格或网页片段可直接调用 JSON 接口：

```bash
curl -X POST http://127.0.0.1:8000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "content_type": "text",
    "title": "Attention Notes",
    "content": "Transformer attention notes...",
    "source": "manual",
    "source_url": null,
    "metadata": {
      "course": "NLP",
      "owner": "me"
    }
  }'
```

字段说明：

| Field | Required | Description |
| --- | --- | --- |
| `content_type` | yes | `text`, `code`, `table`, `image`, `document`, `webpage`, `repository` |
| `content` | yes | 原始文本内容 |
| `title` | no | 知识条目标题；为空时后端会生成 |
| `source` | no | 来源，如 `manual`, `upload`, `course:dl`, `project:noteclaw` |
| `source_url` | no | 原始 URL |
| `metadata` | no | 任意 JSON 元数据，用于后续过滤和追踪 |

### 5.3 文件上传入库

文件、图片、表格和 PPTX 建议使用 multipart 接口：

```bash
curl -X POST http://127.0.0.1:8000/api/ingest/files \
  -F "file=@/path/to/paper_notes.md" \
  -F "content_type=text" \
  -F "source=course:nlp"
```

常见文件类型：

| Extension | Content type |
| --- | --- |
| `.txt`, `.md`, `.markdown`, `.html`, `.htm` | `text` |
| `.py`, `.js`, `.ts`, `.tsx`, `.go`, `.rb`, `.java`, `.cpp`, `.sql`, `.sh`, `.json`, `.yaml` | `code` |
| `.csv`, `.tsv` | `table` |
| `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`, `.tif`, `.tiff` | `image` |
| `.pptx` | `document` |
| 其他扩展名 | `document` |

图片文件会先走本地 OCR；如果配置了 Vision/OCR API，后端会进一步生成视觉描述或增强 OCR 文本。CSV/TSV 会被转换为 Markdown table 后进入统一的文本检索链路。

### 5.4 导入后检查

导入后可以通过 API 检查知识库：

```bash
curl "http://127.0.0.1:8000/api/knowledge?limit=20"
curl "http://127.0.0.1:8000/api/knowledge/_facets"
```

检索自有数据：

```bash
curl -X POST http://127.0.0.1:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "attention mechanism",
    "mode": "hybrid",
    "filters": {
      "content_types": [],
      "tags": [],
      "category": null,
      "source": null,
      "date_from": null,
      "date_to": null
    },
    "limit": 10
  }'
```

### 5.5 自定义评测数据

如果要评测自有数据，需要准备问题、参考答案和期望来源。可以直接把 `items` 放进请求，也可以参考 `data/demo_subset/qa/demo_questions.json` 建一个 JSON 文件。

单条评测样本格式：

```json
{
  "id": "my_eval_001",
  "question": "FAISS 在我的项目中负责什么？",
  "expected_answer": "FAISS 负责保存 chunk embedding 向量索引，并执行语义相似度检索。",
  "expected_note_ids": [],
  "expected_chunk_ids": [],
  "expected_sources": ["course:nlp"],
  "recommended_files": ["paper_notes.md"],
  "modality": "text"
}
```

直接传入评测：

```bash
curl -X POST http://127.0.0.1:8000/api/harness/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my data eval",
    "mode": "hybrid",
    "top_k": 5,
    "generate_answers": true,
    "judge_answers": false,
    "items": [
      {
        "id": "my_eval_001",
        "question": "FAISS 在我的项目中负责什么？",
        "expected_answer": "FAISS 负责保存 chunk embedding 向量索引，并执行语义相似度检索。",
        "expected_sources": ["course:nlp"],
        "modality": "text"
      }
    ]
  }'
```

评测时，`expected_note_ids`、`expected_chunk_ids` 和 `expected_sources` 至少应提供一种，否则该题不会参与 Hit@K、Recall@K、Precision@K、MRR 的平均。

### 5.6 重复运行与存储

- 导入后的知识库保存在 `storage/noteclaw.db` 和 `storage/faiss/`。
- 重复运行 `scripts/seed_demo.py` 可能继续创建 note；需要干净环境时可先备份或删除 `storage/`。
- 如果更换 embedding 模型，旧 FAISS 索引维度可能不匹配，应使用新的 `STORAGE_DIR` 或重建索引。
- `task_service`、`timeline_service`、`multi_agent_workflow_service` 当前主要是进程内状态，服务重启后任务运行态不会自动恢复。

## 6. 常用 API

| 模块 | 接口 | 用途 |
| --- | --- | --- |
| Health | `GET /health`, `GET /api/health` | 服务健康检查 |
| Ingest | `POST /api/ingest` | JSON 内容入库 |
| Ingest | `POST /api/ingest/files` | 文件上传入库 |
| Knowledge | `GET /api/knowledge` | note 列表、筛选、分页 |
| Knowledge | `GET /api/knowledge/{note_id}` | note 详情和 chunks |
| Knowledge | `GET /api/knowledge/_facets` | tags、sources、categories、content_types |
| Knowledge | `GET /api/knowledge/graph` | 知识图谱 |
| Search | `POST /api/search` | keyword、semantic、hybrid 检索 |
| Search | `POST /api/search/multimodal` | 多模态查询 |
| Chat | `POST /api/chat/sessions` | 创建问答会话 |
| Chat | `POST /api/chat/sessions/{id}/messages` | 非流式问答 |
| Chat | `POST /api/chat/sessions/{id}/messages/stream` | SSE 流式问答 |
| Generate | `POST /api/generate` | 创建生成任务 |
| Generate | `POST /api/generate/preview` | 同步生成预览 |
| Tasks | `GET /api/tasks`, `GET /api/tasks/{task_id}` | 任务列表和详情 |
| Timeline | `GET /api/timeline`, `GET /api/timeline/board` | 时间线数据 |
| Harness | `POST /api/harness/evaluate` | 自动评测 |
| Nanobot | `POST /api/nanobot/research` | 本地知识 + Web research |
| Agents | `POST /api/agents/workflows` | 多 Agent 工作流 |
| Review | `GET /api/review/items` | 复核项列表 |

## 7. 评测指标

自动评测入口：

```bash
curl -X POST http://127.0.0.1:8000/api/harness/evaluate \
  -H "Content-Type: application/json" \
  -d '{"mode":"hybrid","top_k":5,"generate_answers":true,"judge_answers":true}'
```

如果请求中不传 `items`，后端会读取：

```text
data/demo_subset/qa/demo_questions.json
```

评测指标包括：

- `hit_rate_at_k`
- `recall_at_k`
- `precision_at_k`
- `mrr`
- `answer_overlap`
- `groundedness_score`
- `citation_coverage`
- `relevance_score`
- `hallucination_risk`
- `judge_relevance`
- `judge_groundedness`
- `judge_completeness`
- `judge_clarity`

当前仓库已有一次 API 评测输出位于：

```text
backend/storage_api_eval/api_eval_20260705_083202
```

## 8. 当前实现边界

- SQLite、FAISS、上传文件和生成文件会持久化到 `storage/`。
- `task_service`、`timeline_service`、`multi_agent_workflow_service` 当前主要使用进程内存注册表，服务重启后运行态不会自动恢复。
- FAISS 删除采用 lazy deletion，后续可通过重建索引清理。
- `scripts/seed_demo.py` 不是严格幂等，重复运行可能继续创建 note。
- 语义检索主要延迟来自 embedding API 网络调用，FAISS 本地检索本身通常是毫秒级。
- 图片处理优先走本地 OCR；Vision/OCR/Image 能力依赖 `.env` 中配置的模型服务。

## 9. 文档索引

- [`docs/BACKEND_TECHNICAL_PIPELINE.md`](docs/BACKEND_TECHNICAL_PIPELINE.md)：后端 pipeline、算法和评测结果。
- [`docs/PROJECT_STRUCTURE.md`](docs/PROJECT_STRUCTURE.md)：项目目录与开发边界。
- [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md)：前后端 REST 契约。
- [`docs/FRONTEND_BACKEND_FLOW.md`](docs/FRONTEND_BACKEND_FLOW.md)：前后端调用流程。
- [`docs/FRONTEND_API_CLIENT.md`](docs/FRONTEND_API_CLIENT.md)：前端 API client 约定。
- [`docs/BACKEND_INTERNAL_INTERFACES.md`](docs/BACKEND_INTERNAL_INTERFACES.md)：SQLite、FAISS、provider、service 边界。
- [`backend/README.md`](backend/README.md)：后端运行说明。
- [`frontend/README.md`](frontend/README.md)：前端 Vite 说明。
