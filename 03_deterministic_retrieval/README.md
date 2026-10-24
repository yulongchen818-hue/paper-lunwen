# 03_deterministic_retrieval

The LLM-free evidence-assembly path.

* `graph_engine.py` loads JSON-LD data files into a node/edge graph, holds the property-to-edge mapping
  that realizes the relation types, and provides adjacency, breadth-first relation paths and bounded
  evidence-subgraph extraction (capped at three hops). Default data file names are placeholders.
* `retrieval.py` is the deployed retriever: query and entity text reduced to character bigrams (Chinese)
  and alphanumeric tokens (Latin); each entity scored by the count of query grams in its indexed text, plus
  3 per query term found in the entity name and 2 x overlap / (|name grams| + 1); the six highest-scoring
  entities are seeds; one-hop expansion over incoming and outgoing edges. No inverse document frequency and
  no length normalization, so scores are relative to one query.
* `linkage.py` maps retrieved entities to highlight targets and knowledge-panel groups (table-driven).
* `lib_retrieval_v2.js` is the byte-faithful JavaScript port of the scoring, chunking and retrieval code
  used by every experiment script, plus the frozen scoring functions. Set `BASE` to your data root.
* `cdc_v2.js` is the improved graph retriever designed after the outcomes were known (post hoc): BM25-scored
  seeds and personalized PageRank over the same records, filling a fixed record budget.
