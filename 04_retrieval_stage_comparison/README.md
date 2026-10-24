# 04_retrieval_stage_comparison

Mechanical comparison of the evidence-assembly stage against document retrieval, scored against a key
frozen before the first run. No generative model is invoked and no human rates any output.

| Script | Conditions |
|---|---|
| `run_baseline.js` | CDC-full, CDC-seeds, RAG-6, RAG-12 (vector-space TF-IDF, heading-based chunks) |
| `run_baseline_v2.js` | adds RAG-94 (payload-matched), BM25-6, BM25-12 and the repaired-graph rows |
| `export_for_dense.js`, `dense_rank.py`, `dense_repro_check.py` | Dense (BGE-M3), Hybrid (RRF, k = 60), Rerank (bge-reranker-v2-m3 over the hybrid top 50); CPU, fp32, pinned revisions |
| `run_review_v3.js` | re-scores every condition from archived rankings and writes the summary |
| `coverage_ceiling.js` | what each evidence base contains independent of ranking |
| `inspect_results.js` | locates individual hits and false bases in the audit dump |

Inputs expected under the data root: the graph files, the corpus directory (Markdown files chunked at
headings) and the question bank. `results/summary_all_conditions.md` and `results/coverage_ceiling.md`
are the aggregate outputs as reported in the manuscript and its Supplementary Material S2; the per-question
audit dumps quote project documents and are not included.

The hit rate is recall at k with one required value per item; "item precision" is the share of package
items that contain a token of the key. Dependencies: Node.js >= 20; Python 3.10+, `numpy`, `torch`,
`sentence-transformers` for the dense conditions; model weights are read from `<MODEL_DIR>`.
