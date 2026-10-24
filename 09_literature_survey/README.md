# 09_literature_survey

Open-access literature search on evaluation practice in language-model question answering for civil and
construction engineering (2019-2026), the basis of Supplementary Material S1.

* `lit_search.py`: candidate pool from Crossref, arXiv and PubMed Central.
* `extract.py`: per-paper field extraction from retrieved full text with mechanical quote verification;
  it calls a language model through the sandbox's `host.llm` wrapper, so replace that call with your own
  client to re-run it.
* `grounding_eval_survey.csv`: the 24 included papers with the extracted fields; `grounding_eval_survey_report.md`
  the report; `survey_state.json` the funnel state.
