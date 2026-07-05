# NoteClaw 后端技术 Pipeline 与核心实现

本文档面向答辩/汇报和后端交接，重点说明 NoteClaw 不是简单调用一个 LLM，而是一个围绕个人知识库构建的多模态 RAG 后端系统：多格式解析、知识沉淀、混合检索、证据约束问答、推理/联网/多 Agent、内容生成和自动评测形成闭环。

## 1. 技术路线总览

```text
多模态输入
  -> 文件类型识别与内容解析
  -> LLM/Vision API 生成结构化元数据
  -> 文本切块 chunking
  -> SQLite 保存原文和元信息
  -> Embedding API 生成向量
  -> FAISS 建立向量索引
  -> Keyword / Semantic / Hybrid / Multimodal 检索
  -> RAG 问答、跨文档推理、联网研究、多 Agent、内容生成
  -> Evaluation Harness 量化评测检索和回答质量
```

核心技术点：

- 多模态解析：文本、代码、表格、图片、PPTX 统一转成可检索文本。
- 知识沉淀：SQLite 保存原文、摘要、标签、分类、来源、时间、metadata、chunks。
- 向量索引：Embedding API + FAISS `IndexFlatIP`，向量归一化后近似 cosine similarity。
- 混合检索：关键词字段加权 + 语义相似度 + rank bonus 融合。
- 证据约束生成：回答 prompt 强制基于检索上下文，并使用 `[1] [2]` 引用。
- 自动评测：Hit@K、Recall@K、MRR、Groundedness、Citation Coverage、LLM Judge。

关键代码位置：

```text
backend/src/noteclaw_backend/services/ingestion.py        入库主流程
backend/src/noteclaw_backend/services/document_parser.py  多格式解析
backend/src/noteclaw_backend/services/text_processing.py  摘要/标签/切块
backend/src/noteclaw_backend/storage/repositories.py      SQLite 和关键词检索
backend/src/noteclaw_backend/storage/faiss_store.py       FAISS 向量索引
backend/src/noteclaw_backend/services/retrieval.py        semantic/hybrid 检索
backend/src/noteclaw_backend/services/chat.py             RAG 问答
backend/src/noteclaw_backend/services/evaluation.py       评测指标
backend/src/noteclaw_backend/services/providers/          API provider 抽象
```

## 2. 多模态输入与解析算法

入口接口：

```text
POST /api/ingest
POST /api/ingest/files
POST /api/search/multimodal
```

文件解析由 `parse_file_bytes` 完成。后端先根据扩展名推断 `ContentType`：

```text
.md/.txt/.html        -> text
.py/.js/.go/.rb/...   -> code
.csv/.tsv             -> table
.png/.jpg/.webp/...   -> image
.pptx                 -> document
```

不同类型的处理方式：

- 文本：按编码尝试 `utf-8 / gb18030 / latin-1` 解码。
- 代码：保持源码结构，不做额外清洗，便于代码问答。
- 表格：使用 `csv.Sniffer` 推断分隔符，再转换成 Markdown table。
- 图片：先用 OCR 提取可见文字，再调用 Vision API 生成视觉描述、关键对象、图表信息和检索关键词。
- PPTX：用 `python-pptx` 遍历 slide shapes，提取每页文本。

图片入库的核心思路是：

```text
image bytes
  -> OCR text
  -> Vision API description
  -> "Image OCR text + Image visual description"
  -> 后续和普通文本一样摘要、切块、embedding、检索
```

因此图片不是单独孤立保存，而是被转成可检索的文本语义表示，同时保留原始文件路径和 metadata。

## 3. 知识沉淀与元数据生成

入库主流程在 `IngestionService._ingest_parsed`：

```text
ParsedDocument
  -> enrich_content 生成 title/summary/tags/category
  -> chunk_text 切块
  -> create_note 写 SQLite
  -> embed_texts 生成向量
  -> FAISS.add 写向量索引
  -> vector_mappings 保存 chunk_id -> faiss_row_id
```

### 3.1 LLM 元数据抽取

`enrich_content` 会要求 LLM 返回 JSON：

```json
{
  "title": "...",
  "summary": "...",
  "tags": ["..."],
  "category": "..."
}
```

如果 API 异常或 JSON 不稳定，后端有 fallback：

- title：取正文第一行。
- summary：取前 420 字左右并在句号处截断。
- tags：按词频提取关键词。
- category：根据代码、数据、论文、RAG 等关键词粗分类。

API JSON 容错也做了增强：模型偶尔返回带非法反斜杠的 JSON 字符串时，会修复非法 escape 后重试解析。

### 3.2 Chunking 算法

`chunk_text` 的默认参数：

```text
chunk_size = 1200 characters
chunk_overlap = 160 characters
```

切块不是简单固定长度截断，而是按结构单元切分：

- Markdown 标题会被识别，并作为后续 chunk 的上下文 header。
- 代码块按照 fenced code block 保持完整。
- Markdown table 按表格行整体处理，避免切断表结构。
- 空行作为段落边界。
- 超长段落再按换行、中文句号、英文句号寻找切点。
- 相邻 chunk 保留 overlap，降低跨 chunk 信息断裂。

这样做的目的：既控制上下文长度，又保留标题、代码、表格等结构信息。

## 4. 存储设计

SQLite 负责业务数据，FAISS 负责向量索引。

### 4.1 SQLite 表

核心表：

```text
notes
  id, title, content_type, content, summary, tags_json, category,
  source, source_url, status, metadata_json, created_at, updated_at

chunks
  id, note_id, chunk_index, text, metadata_json, created_at

vector_mappings
  chunk_id, faiss_row_id, embedding_model, deleted

feedback
  note_id, target, rating, comment
```

也就是说，知识库沉淀不只是保存 embedding，而是完整保存：

```text
原文 + 摘要 + 标签 + 分类 + 来源 + 时间 + metadata + chunk + 向量映射
```

### 4.2 FAISS 向量索引

`FaissVectorStore` 使用归一化向量和内积搜索：

```text
embedding vector
  -> L2 normalize
  -> FAISS IndexFlatIP
  -> inner product ≈ cosine similarity
```

FAISS 只保存向量和内部 row id，不保存原文。检索命中后通过 `chunk_id` 回 SQLite 查标题、摘要、source、tags、原文片段等业务信息。

删除采用 lazy deletion：

```text
SQLite 标记 deleted
FAISS ids.json 记录 deleted chunk_id
后续可重建索引清理
```

## 5. 检索核心算法

入口接口：

```text
POST /api/search
POST /api/search/multimodal
```

支持三种模式：

```text
keyword   关键词检索
semantic  向量语义检索
hybrid    关键词 + 语义融合检索
```

### 5.1 Keyword Search

代码位置：`storage/repositories.py -> keyword_search`

关键词检索不是简单 `LIKE`，而是做了轻量 BM25-like 的字段加权打分。

处理步骤：

```text
query
  -> regex 分词：英文/数字/中文片段
  -> 去停用词：what/the/is/for/from 等
  -> 在 title/text/summary/tags/source/source_url 中匹配
  -> 按字段加权求分
```

当前字段权重：

```text
phrase exact match: 8.0
term in title:      4.0
term in metadata:   3.0   # tags/source/source_url
term in summary:    2.0
term in body text:  min(count, 3) * 1.0
```

设计原因：

- title/source/tags 往往比长正文更能代表文档身份。
- 正文词频做上限，避免长论文靠高频普通词刷分。
- 停用词过滤避免 `what / are / the / in` 把无关长文档排前面。

### 5.2 Semantic Search

代码位置：`services/retrieval.py -> _semantic_search`

流程：

```text
query
  -> Embedding API
  -> query vector normalize
  -> FAISS search top_k * 5 candidates
  -> SQLite get_by_ids 回填业务信息
  -> filters/scope 过滤
  -> 返回 top_k
```

为什么 semantic 慢：

```text
主要延迟 = API embedding(query) 网络调用
FAISS 本地搜索本身是毫秒级
```

因此后端增加了 embedding LRU cache：

```text
相同 query 第一次：调用 API，约 1s 级
相同 query 后续：命中进程内缓存，约 ms 级
```

实际 API 评测复测：

```text
semantic 首次平均约 1140 ms/题
semantic 缓存后约 2.6 ms/题
```

### 5.3 Hybrid Search

代码位置：`services/retrieval.py -> _merge_results`

Hybrid 会同时取 keyword 和 semantic 的候选：

```text
keyword_rows = keyword_search(query, max(top_k * 2, 10))
semantic_rows = semantic_search(query, max(top_k * 2, 10))
```

融合公式可以概括为：

```text
hybrid_score =
  0.45 * normalized_keyword_score
+ 0.55 * semantic_score
+ rank_bonus
```

rank bonus 分两路加入：

```text
keyword rank bonus:  0.15 / (keyword_rank + 1)
semantic rank bonus: 0.15 / (semantic_rank + 1)
```

这样做的原因：

- keyword 对专有名词、代码函数名、文件名非常强。
- semantic 对自然语言问题、同义表达、多模态描述更强。
- rank bonus 保留两个检索器自己的排序信心。
- 去重后按融合分排序，避免同一个 chunk 重复出现。

### 5.4 前端 score 的含义

检索返回的 `score` 不是准确率，而是单条结果的相关度分数。

现在后端把它归一化到 `0-1`：

```text
score = relevance score / 匹配度 / 相关度
```

前端可以显示为：

```text
相关度 92%
```

但不要叫“准确率”。准确率是评测指标，例如 Hit@5、Recall@5、MRR。

## 6. 多模态检索算法

多模态检索入口：

```text
POST /api/search/multimodal
```

核心思路：把非文本输入先转为可检索语义，再走统一检索链路。

```text
用户文本 query + 可选图片/文件
  -> 解析文件
  -> 图片 OCR + Vision API description
  -> 合成 expanded query
  -> keyword / semantic / hybrid 检索
  -> 返回 chunk + note metadata + score
```

图片检索本质上依赖两个方向：

- 入库时图片已经被 OCR/Vision 转成文本描述并 embedding。
- 查询时图片也被 OCR/Vision 转成文本描述，和用户 query 合并后检索。

因此可以实现“输入图片或图片相关文字，返回对应原文档/图片 sidecar/图表说明”的效果。

## 7. RAG 问答 Pipeline

入口：

```text
POST /api/chat/sessions
POST /api/chat/sessions/{session_id}/messages
```

流程：

```text
question
  -> RetrievalService.retrieve_chunks_for_question
  -> 得到 top-k chunks
  -> 构造 Source [1], Source [2] 上下文
  -> LLM complete_text
  -> 返回 answer + citations + trace
```

上下文格式包含：

```text
Source [n]
title
source
relevance score
summary
chunk text
```

Prompt 约束：

```text
只能基于给定 context 回答
关键事实必须引用 [1] [2]
优先高相关度 source
证据不足要说明不确定，而不是猜
```

这使回答更像严格 RAG，而不是普通聊天。

## 8. 跨文档推理、联网搜索与多 Agent

### 8.1 多步推理

`ReasoningService` 会把复杂问题拆成多个 reasoning steps：

```text
原问题
  -> 生成多个子问题/推理步骤
  -> 每一步单独检索证据
  -> 汇总所有 citations
  -> LLM 综合回答并说明不确定性
```

适合：

- 多篇 PDF 方法对比。
- 多文档总结。
- 从多个 note 中抽取证据再推结论。

### 8.2 Nanobot 联网研究

Nanobot 是可选的高级路径，不是默认每次启动。

典型流程：

```text
用户打开联网/深度思考开关
  -> 本地知识库先检索
  -> Web search / fetch 补充外部资料
  -> 本地证据 + Web 证据合并
  -> LLM 生成带 Local/Web citation 的回答
```

适合：

- 当前知识库不足的问题。
- 需要最新资料的研究任务。
- 自动资料搜集。

### 8.3 多 Agent 工作流

多 Agent 不是“多个 API key”，而是角色化分工：

```text
Researcher：找资料、抽证据
Reasoner：跨文档综合推理
Reviewer：检查引用、完整性、风险
Coordinator：组织任务状态和最终输出
```

它比普通 RAG 多了“任务分解、证据审查、结果复核”的环节，所以更适合复杂任务，但速度会更慢，因此作为可选模式。

## 9. 内容生成 Pipeline

入口：

```text
POST /api/generate
```

生成流程：

```text
用户选择生成类型和范围
  -> 检索相关 chunks
  -> 构造带 citations 的上下文
  -> LLM 生成结构化内容
  -> 可选渲染 artifact
  -> 返回 result/artifact/citations
```

支持：

```text
学习笔记
技术总结
报告草稿
PPT 大纲
PPTX 文件
表格
思维导图
图片
图示
视频脚本
```

PPTX 不是前端假展示，而是后端生成真实 `.pptx` artifact：

```text
LLM 生成 slide JSON
  -> python-pptx 创建 Presentation
  -> 写标题、要点、备注、引用
  -> 保存到 storage/generated
```

## 10. Tasks / Timeline / Knowledge Graph

这些模块是把底层能力包装成可展示的工作流。

### Tasks

把复杂任务抽象成 work item：

```text
queued -> in_progress -> need_review -> done
```

任务卡片可以承载：

- 多文档总结。
- 报告生成。
- PPT 大纲生成。
- 联网资料搜集。
- 代码库分析。
- 跨文档推理。

### Timeline

Timeline 用于展示知识工作过程，而不是项目排期：

```text
资料搜集 -> 证据抽取 -> 对比分析 -> 报告草稿 -> PPT 大纲 -> 最终版本
```

### Knowledge Graph

知识图谱基于 notes、tags、category 构图：

```text
节点：note / tag / category / source
边：note-has-tag / note-in-category / note-from-source / tag-co-occurs
```

它体现的是“知识之间的组织关系”，不是简单列表。

## 11. 自动评测 Pipeline

入口：

```text
POST /api/harness/evaluate
```

评测数据：

```text
data/demo_subset/qa/demo_questions.json
```

每条评测样本包含：

```json
{
  "id": "...",
  "question": "...",
  "expected_answer": "...",
  "recommended_files": ["..."],
  "modality": "text/code/table/image/..."
}
```

### 11.1 检索指标

设 `expected_refs` 是标准答案对应的 note/chunk/source，`retrieved_refs@k` 是 Top-K 检索结果。

```text
Hit@K = Top-K 中是否至少命中一个 expected ref
Recall@K = 命中的 expected refs 数 / expected refs 总数
Precision@K = Top-K 中相关结果数 / K
MRR = 1 / 第一个相关结果排名
Latency = 单题检索耗时
```

### 11.2 回答质量指标

```text
answer_overlap
  回答和 expected_answer 的关键词覆盖程度

completeness_score
  当前等同于 answer_overlap，衡量标准答案要点覆盖

groundedness_score
  回答词项有多少能在检索上下文中找到支持

citation_coverage
  根据回答 claim 数估计需要的引用数量，再计算有效引用覆盖

relevance_score
  回答与 question + expected_answer 的词项重合程度

hallucination_risk
  1 - groundedness_score
```

中文场景下 `answer_overlap` 会偏保守，因为目前没有专门中文分词；因此最终更建议结合 LLM judge 看回答质量。

### 11.3 API Judge

当 `judge_answers=true` 时，后端会调用 LLM judge 返回：

```text
judge_relevance
judge_groundedness
judge_completeness
judge_clarity
judge_hallucination_risk
judge_comment
```

这相当于用另一次模型调用做主观质量评估，适合比赛展示。

## 12. 当前 API 评测结果

API 全链路评测库：

```text
backend/storage_api_eval/api_eval_20260705_083202
```

数据规模：

```text
notes: 21
chunks: 62
vector_mappings: 62
```

检索 Top-5 指标：

| Mode | Hit@5 | Recall@5 | Precision@5 | MRR | Avg Latency |
|---|---:|---:|---:|---:|---:|
| keyword | 1.0000 | 0.9583 | 0.4500 | 0.9583 | 4.31 ms |
| semantic | 1.0000 | 1.0000 | 0.4000 | 0.9583 | 1179.05 ms |
| hybrid | 1.0000 | 1.0000 | 0.4000 | 0.9583 | 1102.52 ms |

API Judge 回答质量：

```text
judge_relevance: 0.9625
judge_groundedness: 0.9125
judge_completeness: 0.9292
judge_clarity: 0.9417
judge_hallucination_risk: 0.1167
```

可以汇报为：

```text
在覆盖文本、中文、代码、表格、图片表格、图表、个人笔记的 12 条 demo benchmark 上，
API embedding 的 semantic/hybrid 检索达到 Hit@5 100%、Recall@5 100%、MRR 95.83%。
生成回答经 API judge 评估，相关性 0.9625，证据支撑度 0.9125，完整性 0.9292。
```

## 13. 技术亮点总结

- 不是简单 LLM wrapper，而是完整 RAG 后端：解析、沉淀、索引、检索、生成、评测。
- 多模态统一文本化：图片 OCR/Vision 后进入同一知识库检索链路。
- Hybrid 检索融合了关键词精确命中和 embedding 语义召回。
- SQLite + FAISS 分层设计，业务元信息和向量索引解耦。
- Provider adapter 统一模型调用，支持不同 API endpoint 和 fallback。
- Embedding 缓存显著降低重复语义检索延迟。
- 回答 prompt 强制引用证据，降低幻觉风险。
- Evaluation Harness 把效果量化，不只靠主观展示。
- Tasks、Timeline、Knowledge Graph 把底层能力包装成可展示的知识工作流。
