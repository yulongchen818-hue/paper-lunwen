# Cite-Don't-Compute: drawing-derived knowledge graph with LLM-free evidence retrieval

Code and non-project material accompanying the manuscript *Cite-Don't-Compute: A Drawing-Derived Knowledge
Graph with LLM-Free Evidence Retrieval for Auditable Decision Support in Steel Box-Girder Construction*
(submitted to *Buildings*). The repository is released for academic exchange.

Cite-Don't-Compute (CDC) is a constraint on system organization: the entities, relations and recorded
values that appear in an answer are produced by components that contain no language model, and the model
only narrates them. This repository holds those components and the scripts that measured them.

## Contents

| Folder | What it holds |
|---|---|
| `01_ontology` | the 18-class, 12-relation lightweight schema and the graph file format |
| `02_drawing_to_graph` | rule-based DXF traversal and graph construction |
| `03_deterministic_retrieval` | the deployed retriever and graph engine, the JavaScript port used in the experiments, and the post hoc improved graph retriever |
| `04_retrieval_stage_comparison` | scripts and aggregate results of the mechanical retrieval-stage comparison (vector-space, BM25, dense, hybrid, reranked, payload-matched) |
| `05_graph_audit` | the graph-quality audit (referential integrity, relation completeness, domain/range conformance, stage linkage) |
| `06_answer_level_pilot` | generation and scoring scripts of the answer-level pilot and its aggregate scores |
| `07_question_bank_format` | the question-bank and scoring-key format, with a synthetic example |
| `08_public_data_protocol` | the public datasets of the ingestion protocol that may be redistributed |
| `09_literature_survey` | the open-access literature search behind Supplementary Material S1 |

## What is not here, and why

The case project's drawings, method statements and records are covered by a data-use agreement with the
project parties. Everything derived from them is withheld for the same reason, because it quotes their
values: the populated graph snapshots (v1, v1.1, v1.2) and their changelogs, the knowledge corpus, the
frozen question bank and key, the per-question evidence dumps, and the prompts and answers of the pilot.
Identifying details of the project have been removed from code comments and default paths; placeholders
such as `<EVIDENCE_PACKAGE_ROOT>`, `<DRAWING_ROOT>`, `<MODEL_DIR>` and `{PROJECT_DESCRIPTION}` mark where
your own paths and text go. The aggregate results in `04_.../results` and `06_.../results` are the numbers
reported in the manuscript and its Supplementary Material S2.

## Running the code on your own data

1. Build a graph in the JSON format of `01_ontology/ontology_schema.md`, either from JSON-LD files through
   `02_drawing_to_graph/build_kg.py` or by any other means.
2. Put the documents of the comparison corpus in one directory as Markdown files (chunked at headings by
   the scripts) and write a question bank in the format of `07_question_bank_format`.
3. Set the data root in `03_deterministic_retrieval/lib_retrieval_v2.js` and the `GRAPHS` paths in
   `05_graph_audit/audit_graph.py`, then run the scripts in the order given in
   `04_retrieval_stage_comparison/README.md`. Every lexical condition is deterministic and reproduces byte
   for byte; the dense conditions need the two model checkpoints named in `dense_rank.py`.

Requirements: Node.js >= 20; Python 3.10+ with the packages in `requirements.txt` (`ezdxf` for the
pipeline; `numpy`, `torch`, `sentence-transformers` for the dense conditions only).

## Licence

Code: MIT (see `LICENSE`). Public datasets keep their own licences, listed in `08_public_data_protocol/README.md`.
