# NoteClaw Demo Subset

This directory is a small, non-destructive subset extracted from the raw datasets in `NoteClaw/data`.
It is intended for fast MVP demos: upload a handful of ordinary files, then show summary/tags/category, knowledge search, QA, and content generation.

## What is included

- `text/`: Chinese retrieval notes from T2Retrieval and one Open-RAGBench arxiv QA note.
- `code/`: real CodeSearchNet snippets in Python, JavaScript, Go, and Ruby.
- `tables/`: a compact CSV converted from an Open-RAGBench paper table.
- `images/`: PNG images extracted from Vidore parquet, plus metadata sidecar markdown files.
- `qa/demo_questions.json`: suggested questions for validating search and knowledge QA.
- `cross_modal_pairs/`: positive text-query to document-section plus linked-image pairs for cross-modal retrieval demos.

## Suggested upload order

1. Upload 2-3 files from `text/`.
2. Upload 1-2 files from `code/`.
3. Upload `tables/spatial_transcriptomics_feature_mae.csv`.
4. Upload `images/document_question_page.png` and `images/financial_table_image.png`; optionally also upload their `.md` sidecars.
5. Upload files from `cross_modal_pairs/` to demonstrate a text query retrieving a document section with linked image evidence.
6. Ask questions from `qa/demo_questions.json` and generate a learning note or report draft.

The raw 5.1GB dataset is intentionally left untouched.
