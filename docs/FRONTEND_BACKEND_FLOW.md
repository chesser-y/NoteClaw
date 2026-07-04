# 前后端调用流程

开发环境后端基础地址：

```text
http://127.0.0.1:8000/api
```

## 建议前端页面

- `/library`：知识库卡片列表、筛选、标签、分类、来源。
- `/ingest`：文本、代码、表格粘贴；图片和文件上传。
- `/chat`：基于知识库的问答会话。
- `/generate`：学习笔记、技术总结、报告、PPT 大纲、PPTX、思维导图、图片、图示、视频脚本生成。
- `/tasks`：异步任务进度和生成产物。
- `/settings`：模型配置、API key、存储状态。

## 信息输入流程

```text
用户粘贴文本/代码/表格或上传文件
  -> POST /api/ingest 或 POST /api/ingest/files
  -> 后端创建 note、chunks、task
  -> 前端拿到 note_id 和 task_id
  -> 前端轮询 GET /api/tasks/{task_id}
  -> 任务完成后刷新 GET /api/knowledge/{note_id}
```

图片输入流程：

```text
上传图片
  -> 后端先 OCR
  -> OCR 文本立即参与摘要、标签和检索
  -> 多模态理解异步执行
  -> note 状态从 vision_pending 变为 ready
  -> 视觉理解结果追加为新的 chunk
```

## 搜索流程

```text
用户输入查询词和筛选条件
  -> POST /api/search
  -> 后端按 keyword / semantic / hybrid 检索
  -> 返回排序后的 chunks 和 note metadata
  -> 前端展示标题、摘要、snippet、score、标签、来源
```

搜索模式：

- `keyword`：SQLite 关键词检索，后续可升级 FTS。
- `semantic`：embedding API + FAISS。
- `hybrid`：关键词结果和语义结果融合。

## 问答会话流程

```text
用户打开问答页
  -> POST /api/chat/sessions
  -> 前端保存 session_id

用户发送问题
  -> POST /api/chat/sessions/{session_id}/messages
  -> 后端检索相关 chunks
  -> 后端调用 LLM 或 nanobot 推理路径
  -> 返回 answer + citations + trace
```

MVP 阶段先使用非流式响应。后续如果要做流式输出，可以新增：

```text
GET /api/chat/sessions/{session_id}/stream?message_id=...
```

## 内容生成流程

```text
用户选择生成类型和知识范围
  -> POST /api/generate
  -> 后端创建异步任务
  -> 前端轮询 GET /api/tasks/{task_id}
  -> 任务成功后展示 result 或 artifact 下载链接
```

轻量预览可以使用同步接口：

```text
POST /api/generate/preview
```

适合同步预览的内容：

- Markdown 学习笔记。
- 技术总结。
- PPT 大纲 JSON。
- Mermaid 思维导图。

必须异步的内容：

- PPTX 导出。
- 生图 API。
- 图示生成。
- 视频脚本生成。
- nanobot 网络检索或跨文档推理。

## 反馈流程

```text
用户点击有用/无用，或编辑标签、摘要
  -> POST /api/knowledge/{note_id}/feedback
  -> 后端保存反馈
  -> 后续用于优化标签、检索排序、摘要风格
```

## Nanobot Harness 流程

nanobot 用作执行 harness，负责文件操作、网络检索、代码仓库分析、跨文档推理等。

```text
前端发起高级任务
  -> POST /api/harness/jobs
  -> 后端创建 task
  -> NanobotHarness 调用 nanobot
  -> 前端通过 GET /api/tasks/{task_id} 轮询状态
```

前端不需要知道 nanobot 的具体调用方式，只需要把 harness job 当异步任务处理。
