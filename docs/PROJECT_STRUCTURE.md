# 项目目录与开发边界

本文档用于团队并行开发，明确目录结构、前后端边界、后端模块边界和 MVP 功能覆盖范围。

## 仓库结构

```text
NoteClaw/
  README.md
  docs/
    PROJECT_STRUCTURE.md
    API_CONTRACT.md
    FRONTEND_BACKEND_FLOW.md
    FRONTEND_API_CLIENT.md
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
          harness.py
          ingest.py
          knowledge.py
          search.py
          tasks.py
      schemas/
        common.py
        chat.py
        generation.py
        harness.py
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
    # 前端后续初始化：Vue 3 + Vite + TailwindCSS
  nanobot/
    # 本地源码依赖。backend 通过 ../nanobot 安装 nanobot-ai
  REFERENCE/
    # UI 参考素材，不属于后端运行依赖
```

## 前端职责

前端负责：

- Vue 页面、组件、路由、状态管理。
- 知识库卡片、上传页、问答页、生成页、任务页。
- API client 封装。
- 展示 citations、任务进度、生成产物下载链接。
- 根据 `docs/API_CONTRACT.md` 对接后端。

建议页面：

- `/library`
- `/ingest`
- `/chat`
- `/generate`
- `/tasks`
- `/settings`

## 后端职责

后端负责：

- FastAPI 路由和 OpenAPI。
- SQLite 元数据存储。
- FAISS 向量索引。
- OpenAI-compatible LLM、embedding、vision、image provider。
- OCR、图片理解、摘要标签、检索、问答、内容生成。
- 异步任务管理。
- nanobot harness 预留和后续集成。

## Nanobot 集成边界

nanobot 用作执行 harness，负责：

- 文件操作。
- 网络检索。
- 代码仓库分析。
- 多文档推理。
- 自动信息搜集。

当前只预留：

- `POST /api/harness/jobs`
- `services/nanobot_harness.py`

后续在研究 nanobot 的 CLI/API 使用方式后，把具体调用封装进 `NanobotHarness`，不要泄漏到前端和路由层。

## MVP 必须覆盖的功能

- 信息输入：文本、代码、表格、图片。
- 摘要与标签：摘要、关键词标签、基础分类。
- 知识库沉淀：原文、摘要、标签、时间、来源。
- 检索：关键词检索、语义检索、混合检索。
- 知识问答：自然语言提问，基于已存储内容回答，并返回引用。
- 内容生成：学习笔记、技术总结、报告草稿、PPT 大纲至少一种。

## 计划实现的进阶功能

- 多模态生成：表格、图片、图示、视频脚本。
- 个性化学习：根据反馈优化标签、摘要和检索排序。
- 跨文档推理：由 nanobot 执行多文档检索和推理。
- 自动信息搜集：由 nanobot 从网页、论文、新闻、代码仓库搜集资料。

## 并行开发建议

前端可以先按 OpenAPI 和文档写页面：

- 先接 stub 接口。
- 任务页统一按 `task_id` 轮询。
- 问答页先做非流式。
- 生成页先做 preview，再接异步任务。

后端可以分工实现：

- SQLite repository。
- FAISS vector store。
- OpenAI-compatible providers。
- ingestion pipeline。
- retrieval pipeline。
- chat RAG。
- generation pipeline。
- nanobot harness。
