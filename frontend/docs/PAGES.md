# NoteClaw 页面意义说明

为什么这些页面存在，每个对应什么后端能力，什么时候打开。本文是产品意图快查表，不是 UI 文档。

---

## Inbox — `/`

**为什么存在**：单一入口。粘贴内容、拖入文件、提一个问题，全从这里开始。是「信息进入知识库 + 立刻问起来」的合并面板。

**对应后端**
- `POST /api/ingest`（落库 + 异步理解）
- `POST /api/chat/sessions` / `POST /api/chat/sessions/{id}/messages`（含 `reasoning_mode=agent` 多智能体）
- `GET /api/knowledge?limit=N`、`GET /api/tasks?limit=N`（recent 列表）

**何时打开**：刚捕获一段内容、想基于最近的资料问问题、要看 Agent 模式下的 4 步协同 trace。

**当前状态**：完整实现。粘贴/拖拽 ingest + chat（Normal / Agent）+ recent 列表。

---

## Library — `/library`

**为什么存在**：资料库的目录视图。当 Inbox 像流水、Studio 像「产出」时，Library 是中间的「存量」——所有已经入库的 note 在这里检索、过滤、点开看详情。

**对应后端**
- `GET /api/knowledge`（分页 / 按 tag/category/content_type 过滤 / 全文搜索）
- `GET /api/knowledge/{id}`（单条详情）

**何时打开**：想找某篇资料、过滤某个 tag、检查 OCR/标签质量、给某条 note 关联新会话。

**当前状态**：完整实现。带搜索 + 类型 tabs + 详情抽屉。

---

## Research — `/research`

**为什么存在**：动态信息流。NoteClaw 不只是被搜索引擎——它会持续从你的资料里提炼「研究信号」（新主题、与已有知识的对比、潜在冲突）。Research 是这些信号的 timeline。

**对应后端**（设计意图）
- `GET /api/research/feed`（未来：基于 evidence_anchors 推送高信号片段）
- 复用 `GET /api/agents/workflows` 的 review 输出（risks / verdict）

**何时打开**：日常浏览「有什么新发现」、看哪些资料互相印证或冲突、对一条研究条目反应 / 评论。

**当前状态**：stub。后端 research feed 尚未实现，当前为占位 + 设计草稿。

---

## Tasks — `/tasks`

**为什么存在**：异步工作台。ingest、generation、agent workflow 都是 task；这里给用户看「系统正在做什么 / 失败了什么 / 等我审什么」。

**对应后端**
- `GET /api/tasks`（status / type 过滤）
- `GET /api/tasks/{id}`、`POST /api/tasks/{id}/cancel`
- Work item / Timeline item 关联

**何时打开**：PPT 生成等了好久、批量 ingest 想看进度、Agent workflow 卡住、要看失败任务的错误堆栈。

**当前状态**：完整实现。Kanban 视图 + 详情抽屉。

---

## Timeline — `/timeline`

**为什么存在**：把任务、资料、产出按时间展开。和 Tasks（按状态看）不同，Timeline 按「什么时候发生」看，用来回答「上周我做了什么」「这批资料是哪天 ingest 的」。

**对应后端**（设计意图）
- `GET /api/timeline`（未来：events 流，融合 ingest / task / generation / agent workflow）

**何时打开**：写周报 / 月报、回溯一项工作的演进、检查某段时间的产出。

**当前状态**：stub。后端 timeline 聚合 API 尚未落地。

---

## Map — `/map`

**为什么存在**：项目级「地图」。比 Graph（tag 维度）更粗：以 initiative / project 为节点，看每条项目的健康度、关联资料数、关联任务数。对应 Linear 的 roadmap 视图。

**对应后端**（设计意图）
- `GET /api/initiatives` / `GET /api/initiatives/{id}/health`（未来）

**何时打开**：多项目并行、想看哪条线该投入资源、哪条偏离轨道。

**当前状态**：stub。后端 initiative 模型未实现。

---

## Graph — `/graph`（新增）

**为什么存在**：tag 维度的知识图谱。每篇 note 入库时 LLM 自动总结 tag，Graph 把这些 tag 用共现关系连起来。Obsidian-style：拖拽、缩放、hover 高亮深度 ≤ 2 的邻居。

**对应后端**
- `GET /api/knowledge/graph`（focus_tag / min_tag_count / min_edge_weight 调节）
- 节点：tag / note / category / content_type
- 边：has_tag / tag_cooccurs / category_tag / content_type_tag

**何时打开**：想发现「这个 tag 还和哪些一起出现」、找资料间隐性关联、给某主题聚焦（focus_tag）看 1-2 跳邻域。

**当前状态**：完整实现（d3-force + 高亮 + focus_tag 重渲染）。

---

## Studio — `/studio`

**为什么存在**：从知识库生成新内容。PPT、笔记、报告、表格、图示、视频脚本。模板是入口，自然语言隐式决定 generation_type。

**对应后端**
- `POST /api/generate/preview`（同步预览）
- `POST /api/generate`（异步任务，写入 /generated）
- PPTX 流水线：outline → Layout Agent → HTML 模板 → Playwright 截 PNG → python-pptx 全屏嵌入

**何时打开**：要交付一份 PPT、把多条资料压成学习笔记、生成视频脚本草稿。

**当前状态**：完整实现（含 HTML→PPT 新流水线）。需要 `playwright install chromium` 才能出图，否则 fallback 到朴素 PPTX。

---

## Review — `/review`

**为什么存在**：质量审阅队列。系统检测到的「重复 tag」「低 OCR」「标签冲突」「待确认的 generated 内容」汇集到这里，让人决策。

**对应后端**（设计意图）
- `GET /api/review/queue`（未来）
- 复用 Agent workflow 的 `review.verdict` 与 `review.risks`

**何时打开**：定期清理资料库、确认是否要保留某条低置信度 note、看 Agent 输出的 risks。

**当前状态**：stub（UI 框架已就位，等后端 review queue API）。

---

## Settings — `/settings`

**为什么存在**：用户偏好（主题 / 语言 / 检索默认）+ 前端配置查看 + 入口到高级（Quality 评测、Retrieval 调优、Storage 索引）。

**对应后端**
- 主题 / 语言：localStorage，纯前端
- API Base：仅展示
- 高级：跳 `/settings/quality`

**何时打开**：切换深浅色 / 中英文、查 API 配置、进入质量评测页。

**当前状态**：完整实现。

---

## Quality — `/settings/quality`

**为什么存在**：RAG 系统的「质量门」。Recall@K / MRR / Citation hit rate / Faithfulness / Latency 这些指标决定系统是否可用。把这些独立成 sub-route，避免污染 Settings 主面板。

**对应后端**
- `POST /api/evaluation/run`（运行一组 eval set）
- `GET /api/evaluation/results`（拉历史指标）

**何时打开**：改了检索阈值 / 重排权重之后跑评测、对外汇报 RAG 质量、上线前回归。

**当前状态**：stub（后端 evaluation 已实现，前端展示未接入）。

---

## 总结

| 页面 | 角色 | 状态 |
| --- | --- | --- |
| Inbox | 入口 + 对话 | ✅ |
| Library | 资料库目录 | ✅ |
| Research | 信号 feed | stub |
| Tasks | 异步工作台 | ✅ |
| Timeline | 时间轴 | stub |
| Map | 项目地图 | stub |
| Graph | tag 知识图谱 | ✅ |
| Studio | 内容生成 | ✅ |
| Review | 质量审阅 | stub |
| Settings | 偏好 + 配置 | ✅ |
| Quality | RAG 评测 | stub |

stub 的页面是设计上的「未来位置」，等后端能力落地后接入。Graph / Studio / Inbox 是当前的三条主线，分别对应「理解资料 → 关联知识 → 生成新内容」。
