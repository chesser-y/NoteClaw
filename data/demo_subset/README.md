# NoteClaw Demo Subset

This directory is a small, non-destructive subset extracted from the raw datasets in `NoteClaw/data`.
It is intended for fast MVP demos and lightweight backend evaluation: upload a handful of ordinary files, then show summary/tags/category, knowledge search, QA, retrieval metrics, multimodal retrieval, and content generation.

## What is included

- `text/`: Chinese retrieval notes from T2Retrieval, Open-RAGBench arxiv QA notes, and small personal neuroscience notes.
- `code/`: real CodeSearchNet snippets in Python, JavaScript, Go, and Ruby.
- `tables/`: a compact CSV converted from an Open-RAGBench paper table.
- `images/`: PNG images extracted from Vidore parquet, plus metadata sidecar markdown files.
- `qa/demo_questions.json`: 12 suggested questions for validating search, knowledge QA, and retrieval benchmark metrics.
- `cross_modal_pairs/`: positive text-query to document-section plus linked-image pairs for cross-modal retrieval demos.

## Suggested upload order

1. Upload 3-5 files from `text/`, including the neuroscience notes if you want tag/category graph variety.
2. Upload 2-4 files from `code/`.
3. Upload `tables/spatial_transcriptomics_feature_mae.csv`.
4. Upload 2-4 image samples from `images/`; optionally also upload their `.md` sidecars for OCR/vision-free retrieval baselines.
5. Upload files from `cross_modal_pairs/` to demonstrate a text query retrieving a document section with linked image evidence.
6. Run `/api/harness/evaluate` with `qa/demo_questions.json` and compare `keyword`, `semantic`, and `hybrid` retrieval.
7. Ask questions from `qa/demo_questions.json` and generate a learning note or report draft.

## Evaluation endpoint

Use `POST /api/harness/evaluate` to run a lightweight benchmark over `qa/demo_questions.json` or over custom items passed in the request body.

Example request:

```json
{
  "name": "demo-subset hybrid benchmark",
  "mode": "hybrid",
  "top_k": 5,
  "generate_answers": true,
  "judge_answers": false
}
```

Set `mode` to `keyword`, `semantic`, or `hybrid` to compare retrieval strategies. Set `judge_answers` to `true` only when API-based LLM judging is needed.

Main metrics:

- Retrieval: `hit_rate_at_k`, `recall_at_k`, `precision_at_k`, `mrr`, `avg_latency_ms`.
- Answer quality: `answer_overlap`, `completeness_score`, `groundedness_score`, `citation_coverage`, `relevance_score`, `hallucination_risk`.
- Optional LLM judge: `judge_relevance`, `judge_groundedness`, `judge_completeness`, `judge_clarity`, `judge_hallucination_risk`.
- `breakdown` reports the same metrics by modality, such as text, code, table, image_table, image_chart, image_infographic, and personal_note.

The raw multi-GB datasets are intentionally left untouched.
