# 07_question_bank_format

Documents the format of the frozen question bank and scoring key consumed by `run_baseline.js`,
`lib_retrieval_v2.js` and `score_pilot.js`. Fields:

| Field | Meaning |
|---|---|
| `id` | item identifier (two letters for the domain, two digits) |
| `type` | `answerable`, `boundary` or `excluded_decision` |
| `q` | the question as put to the retriever or the model |
| `key` | the reference answer (human-readable; not used by the scorer) |
| `required_all` | tokens that must all occur as standalone matches in the normalized evidence |
| `required_any`, `min_any` | optional alternative tokens, of which at least `min_any` must occur |
| `request_pattern`, `exposure_keywords` | boundary items: the record that must be absent, and the keywords around which distractor-exposure windows are counted |
| `excluded` | decision items with no retrievable target value, excluded from mechanical scoring |

The scoring rules are stated in `meta.scoring_rules` of the file and implemented verbatim in
`lib_retrieval_v2.js` (`scoreAnswerable`, `scoreBoundary`). `question_bank_example_synthetic.json` holds three
fictional items that document the format; it is not the bank used in the manuscript.
