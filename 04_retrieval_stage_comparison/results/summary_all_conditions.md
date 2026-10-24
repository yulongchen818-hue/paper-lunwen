# Retrieval-stage comparison — first-round revision recheck (v3)

Corpus 14 files -> 1321 chunks. Graphs (nodes/edges): v1 162/329; v1.1 193/487; v1.2 204/528. CDC-full mean payload 17372 chars. Dense payload-matched k = 67 (mean 17463 chars).

Reproduction of all v2 conditions: exact.

| Condition | Family | Hits/18 | Basis absent/5 | Exposure | Mean chars | Mean items | Item precision | Note |
|---|---|---|---|---|---|---|---|---|
| CDC-full | deployed graph retriever | 13/18 | 4/5 | 88 | 17,372 | 49.4 | 0.13 | graph v1, as delivered |
| CDC-seeds | deployed graph retriever | 10/18 | 5/5 | 25 | 2,167 | 5.3 | 0.30 | graph v1, seeds only |
| CDC-full@v1.1 | deployed graph retriever | 13/18 | 4/5 | 180 | 21,451 | 57.9 | 0.14 |  |
| CDC-seeds@v1.1 | deployed graph retriever | 10/18 | 5/5 | 25 | 2,148 | 5.3 | 0.30 |  |
| RAG-6 | lexical document | 13/18 | 5/5 | 39 | 1,166 | 6 | 0.25 |  |
| RAG-12 | lexical document | 14/18 | 5/5 | 72 | 2,395 | 12 | 0.16 |  |
| RAG-94 | lexical document | 16/18 | 5/5 | 183 | 17,426 | 86.6 | 0.07 | payload-matched to CDC-full |
| BM25-6 | lexical document | 12/18 | 5/5 | 33 | 1,289 | 6 | 0.25 |  |
| BM25-12 | lexical document | 15/18 | 4/5 | 83 | 2,651 | 12 | 0.19 |  |
| CDC-full@v1.2 | deployed graph retriever | 13/18 | 4/5 | 180 | 20,679 | 51.1 | 0.15 |  |
| CDC-seeds@v1.2 | deployed graph retriever | 9/18 | 5/5 | 25 | 2,588 | 5.3 | 0.32 |  |
| Dense-6 | dense / hybrid document | 12/18 | 5/5 | 46 | 1,736 | 6 | 0.28 | BGE-M3 |
| Dense-12 | dense / hybrid document | 13/18 | 5/5 | 68 | 3,394 | 12 | 0.21 | BGE-M3 |
| Dense-67 | dense / hybrid document | 14/18 | 4/5 | 128 | 17,463 | 67 | 0.08 | BGE-M3, payload-matched to CDC-full (mean 17463 vs 17372 chars) |
| Hybrid-6 | dense / hybrid document | 13/18 | 5/5 | 52 | 1,729 | 6 | 0.32 | BM25 + BGE-M3, RRF k=60 |
| Hybrid-12 | dense / hybrid document | 14/18 | 5/5 | 71 | 3,459 | 12 | 0.24 | BM25 + BGE-M3, RRF k=60 |
| Rerank-6 | dense / hybrid document | 16/18 | 5/5 | 49 | 1,867 | 6 | 0.37 | hybrid top-50 reranked by bge-reranker-v2-m3 |
| Rerank-12 | dense / hybrid document | 16/18 | 5/5 | 88 | 3,664 | 12 | 0.26 | hybrid top-50 reranked by bge-reranker-v2-m3 |
| CDC-v2-6@v1 | improved graph retriever (post hoc) | 13/18 | 4/5 | 37 | 2,435 | 6 | 0.32 | seeds only |
| CDC-v2-12@v1 | improved graph retriever (post hoc) | 14/18 | 4/5 | 58 | 5,405 | 12 | 0.24 | record budget 12 |
| CDC-v2-24@v1 | improved graph retriever (post hoc) | 14/18 | 4/5 | 81 | 9,651 | 24 | 0.15 | record budget 24 |
| CDC-v2-6@v1.1 | improved graph retriever (post hoc) | 13/18 | 5/5 | 22 | 2,391 | 6 | 0.32 | seeds only |
| CDC-v2-12@v1.1 | improved graph retriever (post hoc) | 14/18 | 5/5 | 55 | 5,504 | 12 | 0.24 | record budget 12 |
| CDC-v2-24@v1.1 | improved graph retriever (post hoc) | 14/18 | 5/5 | 74 | 9,822 | 24 | 0.18 | record budget 24 |
| CDC-v2-6@v1.2 | improved graph retriever (post hoc) | 11/18 | 5/5 | 22 | 2,514 | 6 | 0.31 | seeds only |
| CDC-v2-12@v1.2 | improved graph retriever (post hoc) | 14/18 | 5/5 | 55 | 5,967 | 12 | 0.24 | record budget 12 |
| CDC-v2-24@v1.2 | improved graph retriever (post hoc) | 14/18 | 5/5 | 74 | 10,758 | 24 | 0.17 | record budget 24 |

## Per-question hits (answerable items)

| Q | CDC-full | CDC-seeds | CDC-full@v1.1 | CDC-seeds@v1.1 | RAG-6 | RAG-12 | RAG-94 | BM25-6 | BM25-12 | CDC-full@v1.2 | CDC-seeds@v1.2 | Dense-6 | Dense-12 | Dense-67 | Hybrid-6 | Hybrid-12 | Rerank-6 | Rerank-12 | CDC-v2-6@v1 | CDC-v2-12@v1 | CDC-v2-24@v1 | CDC-v2-6@v1.1 | CDC-v2-12@v1.1 | CDC-v2-24@v1.1 | CDC-v2-6@v1.2 | CDC-v2-12@v1.2 | CDC-v2-24@v1.2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A01 | HIT | HIT | HIT | HIT | - | - | HIT | - | - | HIT | HIT | HIT | HIT | HIT | - | - | HIT | HIT | - | HIT | HIT | - | HIT | HIT | - | HIT | HIT |
| A02 | HIT | - | HIT | - | HIT | HIT | HIT | HIT | HIT | HIT | - | - | - | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT |
| A03 | HIT | - | HIT | - | HIT | HIT | HIT | HIT | HIT | HIT | - | - | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT |
| A04 | HIT | - | HIT | - | HIT | HIT | HIT | HIT | HIT | HIT | - | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT |
| A05 | - | - | - | - | HIT | HIT | HIT | HIT | HIT | - | - | HIT | HIT | HIT | HIT | HIT | HIT | HIT | - | - | - | - | - | - | - | - | - |
| A06 | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | - | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | - | HIT | HIT |
| A07 | - | - | - | - | - | HIT | HIT | - | HIT | - | - | - | - | - | - | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT |
| A08 | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| A09 | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - |
| B01 | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT |
| B02 | - | - | - | - | - | - | HIT | - | HIT | - | - | - | - | - | - | - | HIT | HIT | - | - | - | - | - | - | - | - | - |
| B03 | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT |
| B04 | HIT | HIT | HIT | HIT | HIT | HIT | HIT | - | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT |
| B05 | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT |
| B06 | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | - | HIT | HIT |
| B07 | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT |
| B08 | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT |
| B09 | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT | HIT |

## Boundary items (basis present? / exposure)

| Q | CDC-full | CDC-seeds | CDC-full@v1.1 | CDC-seeds@v1.1 | RAG-6 | RAG-12 | RAG-94 | BM25-6 | BM25-12 | CDC-full@v1.2 | CDC-seeds@v1.2 | Dense-6 | Dense-12 | Dense-67 | Hybrid-6 | Hybrid-12 | Rerank-6 | Rerank-12 | CDC-v2-6@v1 | CDC-v2-12@v1 | CDC-v2-24@v1 | CDC-v2-6@v1.1 | CDC-v2-12@v1.1 | CDC-v2-24@v1.1 | CDC-v2-6@v1.2 | CDC-v2-12@v1.2 | CDC-v2-24@v1.2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A10 | PRESENT/75 | absent/14 | PRESENT/167 | absent/14 | absent/28 | absent/49 | absent/101 | absent/24 | absent/61 | PRESENT/167 | absent/14 | absent/31 | absent/49 | absent/94 | absent/36 | absent/55 | absent/31 | absent/64 | PRESENT/22 | PRESENT/41 | PRESENT/62 | absent/5 | absent/36 | absent/55 | absent/5 | absent/36 | absent/55 |
| A11 | absent/8 | absent/8 | absent/8 | absent/8 | absent/9 | absent/12 | absent/33 | absent/3 | PRESENT/12 | absent/8 | absent/8 | absent/9 | absent/9 | absent/10 | absent/9 | absent/9 | absent/10 | absent/10 | absent/8 | absent/8 | absent/8 | absent/8 | absent/8 | absent/8 | absent/8 | absent/8 | absent/8 |
| A12 | absent/1 | absent/1 | absent/1 | absent/1 | absent/2 | absent/4 | absent/4 | absent/5 | absent/5 | absent/1 | absent/1 | absent/2 | absent/2 | absent/4 | absent/3 | absent/3 | absent/3 | absent/5 | absent/1 | absent/1 | absent/1 | absent/1 | absent/1 | absent/1 | absent/1 | absent/1 | absent/1 |
| B10 | absent/2 | absent/2 | absent/2 | absent/2 | absent/0 | absent/0 | absent/2 | absent/0 | absent/0 | absent/2 | absent/2 | absent/0 | absent/4 | PRESENT/15 | absent/0 | absent/0 | absent/0 | absent/4 | absent/2 | absent/4 | absent/4 | absent/2 | absent/4 | absent/4 | absent/2 | absent/4 | absent/4 |
| B11 | absent/2 | absent/0 | absent/2 | absent/0 | absent/0 | absent/7 | absent/43 | absent/1 | absent/5 | absent/2 | absent/0 | absent/4 | absent/4 | absent/5 | absent/4 | absent/4 | absent/5 | absent/5 | absent/4 | absent/4 | absent/6 | absent/6 | absent/6 | absent/6 | absent/6 | absent/6 | absent/6 |

## Paired comparisons on the 18 answerable items (exact two-sided sign test on discordant items)

| Comparison | first only | second only | p |
|---|---|---|---|
| CDC-full@v1.2 vs CDC-full | 0 | 0 | 1 |
| CDC-full@v1.2 vs RAG-12 | 1 | 2 | 1 |
| CDC-full@v1.2 vs BM25-12 | 1 | 3 | 0.625 |
| Dense-12 vs CDC-full | 1 | 1 | 1 |
| Dense-12 vs RAG-12 | 1 | 2 | 1 |
| Dense-12 vs BM25-12 | 1 | 3 | 0.625 |
| Hybrid-12 vs CDC-full | 2 | 1 | 1 |
| Hybrid-12 vs RAG-12 | 0 | 0 | 1 |
| Hybrid-12 vs BM25-12 | 0 | 1 | 1 |
| Rerank-12 vs CDC-full | 3 | 0 | 0.25 |
| Rerank-12 vs RAG-12 | 2 | 0 | 0.5 |
| Rerank-12 vs BM25-12 | 1 | 0 | 1 |
| CDC-v2-12@v1 vs CDC-full | 1 | 0 | 1 |
| CDC-v2-12@v1 vs RAG-12 | 1 | 1 | 1 |
| CDC-v2-12@v1 vs BM25-12 | 1 | 2 | 1 |
| CDC-v2-12@v1.1 vs CDC-full | 1 | 0 | 1 |
| CDC-v2-12@v1.1 vs RAG-12 | 1 | 1 | 1 |
| CDC-v2-12@v1.1 vs BM25-12 | 1 | 2 | 1 |
| CDC-v2-12@v1.2 vs CDC-full | 1 | 0 | 1 |
| CDC-v2-12@v1.2 vs RAG-12 | 1 | 1 | 1 |
| CDC-v2-12@v1.2 vs BM25-12 | 1 | 2 | 1 |