# 06_answer_level_pilot

Answer-level pilot with mechanical scoring.

* `dump_evidence.js` writes, per item and condition, the evidence package exactly as the retrieval
  comparison produced it.
* `gen_pilot.py` generates one answer per item and condition with a fixed model at temperature 0, a
  400-token cap, one call per item, no regeneration. It was run inside a sandbox whose `host.llm` call wraps
  the model API; replace that call with your own client. The prompts are in the file; in the no-evidence
  prompt the description of the structure has been replaced by `{PROJECT_DESCRIPTION}`.
* `score_pilot.js` (and the pre-generation version `score_pilot_v0.js`) compute per answer: unsupported
  numeric tokens (numbers not occurring standalone in the item's evidence), answer-level key hit, citation
  resolvability, and lexically detected abstention; boundary items are "safe" when the answer abstains and
  introduces no unsupported number. `numeric_check.py` is an independent re-implementation of the numeric
  check. `results/pilot_scores.md` is the aggregate output; prompts and answers quote project documents and
  are not included.
