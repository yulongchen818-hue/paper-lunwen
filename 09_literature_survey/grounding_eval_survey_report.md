> **Erratum (added by the manuscript authors after the run, 2026-09-03).** The run's own reviewer flagged that the S1 paragraph below states "21/24 papers score answers with automatic metrics and/or an LLM judge and no human rating" while also reporting 7/24 with human rating (21 + 7 > 24). Recomputed from `grounding_eval_survey.csv`: **17/24** papers have no human rating of outputs and **7/24** do; the agent's closing message used the corrected 17/24. All other counts used in the manuscript (0/24 chance-corrected agreement statistic, 7/24 human raters, 3/24 unanswerable items included) were re-derived from the CSV and are unchanged. The report text below is otherwise as generated.
# LLM / RAG question-answering evaluation in civil, structural and construction engineering
## How grounding, hallucination and inter-rater agreement are measured — survey of 24 papers (2019–2026)

Built as external anchors for an evaluation protocol using **Krippendorff alpha >= 0.67**,
**statement-level grounding**, and **safe abstention on unanswerable items**.

## Method

Candidate pool from **Crossref** (10 queries), **arXiv** (9 queries) and **PubMed Central**
(6 queries), 2019–2026, run against the public REST APIs. The built-in OpenAlex connector was
not used. No web or literature-chat tool was used for any factual field: every field in the CSV
was extracted from a full text actually retrieved and stored in this session.

Pipeline: mechanical prefilter (language-model signal AND domain signal AND year >= 2019 AND not
clinical) -> title/abstract relevance triage -> full-text retrieval -> Methods-level extraction
with an identical fixed prompt for all 35 retrieved papers (`extract.py`, `SYS`),
model `claude-sonnet-5` -> mechanical verbatim-quote verification -> inclusion screening on two
extracted fields (`in_domain` = yes AND `evaluates_llm_qa` = yes).

| funnel stage | n |
|---|---|
| raw hits (25 queries, three databases) | 1268 |
| after de-duplication (DOI / arXiv id / normalized title) | 1026 |
| after mechanical prefilter | 288 |
| after title/abstract relevance triage | 106 |
| full-text fetch attempts (budget was 60) | 47 |
| full texts obtained | 35 |
| **included after Methods-level screening** | **24** |

Full texts obtained: 19 arXiv, 4 PMC (Scientific Reports / iScience), 1 engrXiv, out of
35 retrieved (11 retrieved papers were dropped at Methods level:
7 in-domain but not question answering, 4 question answering but out of domain).
Twelve journal DOIs were attempted and **none** yielded legal full text (ASCE, Elsevier,
Emerald, MDPI, SSRN, Research Square) — they are excluded, not guessed at.

**Verification.** Every identifier in the CSV was re-resolved after extraction:
6 DOIs via the Crossref API and 18 arXiv ids via the arXiv API, all 24 resolving with
matching titles (`id_verification` column). Both quote fields were checked mechanically against
the paper's own retrieved text, whitespace-, quote-style- and soft-hyphen-insensitive
(`quote_verification` column): 9 quote slots were claimed and verified verbatim, 2 failed
verification and were **discarded** — for those two the corresponding data field reads
"not found (unverifiable)" rather than a repaired quote. The remaining slots were reported as
"not found" by the extractor.

## The 24 included papers

| # | title | yr | venue | items | evaluation type | human raters | agreement statistic | abstention |
|---|---|---|---|---|---|---|---|---|
| 1 | ARIA: Adaptive Retrieval Intelligence Assistant -- A Multim… | 2026 | arXiv preprint | 80 (20 relevant + 60 … | both | not found | none reported | yes |
| 2 | BEST-KAG: Enhancing Question Answering of Building Engineer… | 2026 | arXiv preprint | 140 question-answer p… | automatic + LLM-as-judge | 10 | none reported | no |
| 3 | Chronological Knowledge Retrieval: A Retrieval-Augmented Ge… | 2026 | arXiv preprint | 8 retrieval benchmark… | automatic | not found | none reported | no |
| 4 | Edge-Based Agentic Retrieval-Augmented Generation for Auton… | 2026 | arXiv preprint | 20 retrieval benchmar… | automatic | none (no human … | none reported | not stated |
| 5 | Grounding Large Language Models (LLMs) in Agency Standards:… | 2026 | engrXiv preprint | 70 inspection questio… | automatic + LLM-as-judge | 1 licensed prof… | Spearman rank correlation o… | not stated |
| 6 | Knowledge graph-large language model fusion approach for em… | 2026 | Scientific repo… | 50 case-based QA pairs | automatic + LLM-as-judge | 10 | none reported | not stated |
| 7 | Knowledge-driven automated prefabricated bridge modeling fr… | 2026 | Scientific repo… | 2 instructions (Instr… | automatic + LLM-as-judge | 3 | none reported | not stated |
| 8 | MMArch: Benchmarking Multimodal Reasoning Grounded in Archi… | 2026 | arXiv preprint | 1212 short-answer ite… | automatic | not found | none reported | no |
| 9 | Qwen-BIM: developing large language model for BIM-based des… | 2026 | arXiv preprint | 3300 BIM-QA data pair… | automatic + LLM-as-judge | not found | none reported | no |
| 10 | Seed-Anchored Budget-Bounded Graph Rendering for Question A… | 2026 | arXiv preprint | 50 per network (25 S1… | automatic + LLM-as-judge | none (no human … | not found (unverifiable) | yes |
| 11 | Suppressing Domain-Specific Hallucination in Construction L… | 2026 | arXiv preprint | 100 test questions (8… | LLM-as-judge | none (no human … | none reported | no |
| 12 | Two stage AI framework for strength prediction and generati… | 2026 | Scientific repo… | not found | automatic | none (no human … | none reported | not stated |
| 13 | A Large Language Model-Empowered Agent for Reliable and Rob… | 2025 | arXiv preprint | 8 benchmark beam prob… | automatic | none (no human … | none reported | no |
| 14 | An Embodied AR Navigation Agent: Integrating BIM with Retri… | 2025 | arXiv preprint | not found | both | 20 | none reported | not stated |
| 15 | Automatic Building Code Review: A Case Study | 2025 | arXiv preprint | not found | automatic | none (no human … | none reported | not stated |
| 16 | Bridging Dual Knowledge Graphs for Multi-Hop Question Answe… | 2025 | arXiv preprint | 93 multi-hop questions | automatic | none (no human … | none reported | not stated |
| 17 | Domain-Specific Fine-Tuning and Prompt-Based Learning: A Co… | 2025 | arXiv preprint | 1740 annotated querie… | automatic | not found | none reported | not stated |
| 18 | DrafterBench: Benchmarking Large Language Models for Tasks … | 2025 | arXiv preprint | 1920 drawing revision… | automatic | not found | none reported | yes |
| 19 | Investigating the Potential of Large Language Model-Based R… | 2025 | arXiv preprint | 27 test cases (15 sha… | automatic | not found | none reported | not stated |
| 20 | Multi-Agent GraphRAG: A Text-to-Cypher Framework for Labele… | 2025 | arXiv preprint | 150 questions per Cyp… | LLM-as-judge | none (no human … | none reported | not stated |
| 21 | Performance evaluation of GPT-4o on South Korean national e… | 2025 | Scientific repo… | 180 (100 EEM + 80 EAC… | automatic | none (no human … | none reported | no |
| 22 | Integrating Large Language Models with Multimodal Virtual R… | 2024 | arXiv preprint | 55 intentionally inco… | both | 12 construction… | none reported | not stated |
| 23 | Question answering system of bridge design specification ba… | 2024 | arXiv preprint | 226 samples (200 trai… | automatic | none (no human … | none reported | not stated |
| 24 | Automating construction contract review using knowledge gra… | 2023 | arXiv preprint | 18 risk clauses | automatic + LLM-as-judge | 5 domain experts | none reported | not stated |

## Distributions

**Evaluation type** (n = 24): automatic metrics only **12**;
automatic + LLM-as-judge **7**; LLM-as-judge only
**2**; human rating alongside automatic metrics **3**.
Human rating of system outputs occurs in **7/24** papers.

**Rater independence** (n = 24): no human rating **13**;
not stated **5**; external practitioners **3**;
external practitioners, blinded **2**; mixed **1**.
Nobody reports authors-as-raters explicitly; the 5 "not stated" papers rate outputs without
saying who rated them.

**Agreement reporting**: **1/24** papers report any agreement or
concordance statistic. **Krippendorff alpha: 0 papers. Cohen kappa: 0. Fleiss kappa: 0. ICC: 0.**
The single case is:

- **Grounding Large Language Models (LLMs) in Agency Stan…** — Spearman rank correlation of 0.77
  > "Agreement between the expert and the judge was strong: Spearman rank correlation of 0.77 (p < 0.001), Pearson correlation of 0.80, mean absolute difference of 0.60 points, and 82.7 percent of items within one point, with the judge averaging 0.41 points stricter than the expert, a conservative direc…"

Note what that one case is: a correlation between an **LLM judge and one blinded human expert**,
i.e. judge validation, not agreement among independent human raters.

**Abstention / unanswerable items**: yes **3**, no **7**,
not stated **14**. The three that include them:

- **ARIA: Adaptive Retrieval Intelligence Assistant -- A …** — engineering-education QA; Statics and Mechanics of Material…
- **Seed-Anchored Budget-Bounded Graph Rendering for Ques…** — QA over CIM/CGMES power-grid models; ENTSO-E conformity tes…
- **DrafterBench: Benchmarking Large Language Models for …** — civil engineering drawing revision task automation via LLM …

**Numeric hallucination / unsupported-claim rate**: **2/24** papers report one.

- **Grounding Large Language Models (LLMs) in Agency Stan…** — 56 to 64 percent of closed-book answers were judged factually unacceptable
  > "while 56 to 64 percent of closed-book answers were judged factually unacceptable."
- **Suppressing Domain-Specific Hallucination in Construc…** — 28% low-quality (score 0-1) responses for Case A; 13% for Case C; 0% for Case B
  > "The Score-3 rate rises from 60% (A) to 77% (C) to 92% (B), while Score-2 responses remain at 8% for Case B with no score-0 or score-1— a zero low-quality rate versus 28% for Case A and 13% for Case C."

**Grounding granularity** (mechanical vocabulary presence in the 24 full texts, a
keyword presence test — not a judgment of what the papers did):
claim/statement-level grounding vocabulary **0/24**;
sentence-level **3/24**;
citation / attribution / traceability **14/24**;
faithfulness or groundedness metric (RAGAS-style) **2/24**;
refusal / abstention vocabulary **3/24**.

**Extraction confidence**: explicit 20,
inferred 2,
not found 2.

## The three statements

### S1 — "Most LLM/RAG evaluations in construction engineering rely on automatic text-similarity metrics or author self-assessment rather than independent blinded human rating."

**Verdict: SUPPORTED, with one correction to the wording.**
21/24
papers score answers with automatic metrics and/or an LLM judge and no human rating of outputs;
7/24 rate outputs with humans; only
**2/24** use external raters described as
blinded. The correction: the non-human alternative is no longer only *text-similarity* metrics —
9/24 papers use an
**LLM-as-judge**, which your framing should name explicitly or a reviewer will call the claim
dated. "Author self-assessment" is also not what the corpus shows: nobody says the authors rated
the outputs; 5 papers simply never say who rated.

Suggested wording: "In 24 retrieved open-access evaluations of LLM/RAG question
answering in civil and construction engineering (2019–2026), 12 scored answers
with automatic metrics alone and a further
9 added or substituted an
LLM-as-judge; 7 rated outputs with human raters, and only
2 reported blinded external raters."

### S2 — "Inter-rater agreement statistics are rarely reported."

**Verdict: SUPPORTED — more strongly than the statement claims.**
1/24 papers report any agreement or concordance statistic, and **none**
reports Krippendorff alpha, Cohen kappa, Fleiss kappa or ICC. Even restricting to the
7 papers that do use human raters, 6 report no
agreement statistic of any kind, and the one that does reports LLM-judge-to-expert correlation
rather than human-to-human agreement.

Suggested wording: "None of the 24 retrieved evaluations reports a chance-corrected
inter-rater agreement statistic (Krippendorff alpha, Cohen or Fleiss kappa, ICC); one reports a
Spearman correlation between an LLM judge and a single blinded professional engineer. A
preregistered alpha threshold therefore has no precedent to be compared against in this
literature."

### S3 — "Unanswerable or abstention items are rarely included."

**Verdict: SUPPORTED as a reporting claim, PARTLY SUPPORTED as a design claim.**
3/24 papers deliberately include unanswerable / out-of-scope items or
measure refusal behaviour; 7 explicitly do not; 14 never address
it. The mechanical vocabulary test agrees: refusal/abstention wording appears in only
3/24 full texts. The honest limit on this
verdict is the 14 silent papers — absence of a statement is not proof of
absence of such items, so claim under-reporting, not certain absence.

Suggested wording: "3 of 24 retrieved evaluations state that their test
set includes unanswerable or out-of-scope questions or that abstention was measured;
14 do not mention the issue at all."

**Does the field already do these things routinely?** No. On the evidence retrieved here, none of
the three practices your protocol fixes — chance-corrected agreement, statement-level grounding,
deliberate unanswerable items — is routine in this literature. Claim-level grounding vocabulary
is absent from all 24 papers; the dominant grounding check is an
answer-level citation or traceability claim (14/24)
usually asserted rather than measured. The framing that would NOT survive review is
"nobody evaluates grounding at all": 2 papers report a numeric
unsupported-answer rate and 2 use a
faithfulness-style metric, so position the contribution as *granularity and rater discipline*,
not as first-to-measure.

## Limitations

1. **Open-access-only corpus, and the bias runs against S1 and S2.** 24 of the included
   papers are open access: 19 arXiv preprints,
   4 PMC journal articles,
   1 engrXiv preprint. Twelve paywalled or
   bot-protected journal papers — including *Automation in Construction*, *Advanced Engineering
   Informatics*, *Expert Systems with Applications*, ASCE's *Journal of Construction Engineering
   and Management*, *Engineering, Construction and Architectural Management* and MDPI *Buildings*
   — were dropped for lack of legal full text. Construction-management journals are exactly where
   expert-panel evaluation and questionnaire methodology are most likely to appear, so the true
   rate of human rating and of agreement reporting is plausibly **higher** than
   7/24 and 1/24. Treat these as
   preprint-heavy lower bounds, and say so in the paper.
2. **arXiv-heavy corpus skews toward computer-science reporting conventions**, which favour
   automatic metrics and LLM-judges over expert panels — a second reason S1's count is a lower
   bound on human evaluation.
3. **No cross-checking of what the papers claim.** Fields were extracted from the papers' own
   Methods text; where a paper is silent the cell reads "not found" / "not stated". Two quote
   slots failed verbatim verification and were discarded with their data fields.
4. **Single-pass extraction, no second extractor**, so field-level extraction error is not
   quantified. The three fields carrying the verdicts (agreement, abstention, human raters) were
   additionally audited mechanically by keyword: three "none reported" agreement values were
   flagged and inspected by hand, and all three were confirmed false positives (a kappa math
   symbol, model-fit "agreement", and a reference list).
5. **Search-driven pool, not a registered systematic review**: 25 queries, three databases, no
   backward or forward citation chasing, so recall is not characterised. Two 2026 papers found
   only as SSRN records could not be read at all.
6. Numbers here describe the retrieved corpus only; they are not population estimates.

## Files

- `grounding_eval_survey.csv` — one row per included paper, 22 columns, including both
  verbatim quote fields, per-row identifier verification and quote-verification status.
- `grounding_eval_survey_report.md` — this document.
- `survey_state.json` — funnel counts, keyword tallies and the post-full-text exclusion list.

## Included papers with verified identifiers

1. ARIA: Adaptive Retrieval Intelligence Assistant -- A Multimodal RAG Framework for Domain-Specific Engineering Education. *arXiv preprint* (2026). arXiv:2604.06179v1 — resolves (arXiv API) [arXiv preprint, no journal DOI]
2. BEST-KAG: Enhancing Question Answering of Building Engineering Standards with Multimodal Knowledge Graph Modeling and Large Language Model. *arXiv preprint* (2026). arXiv:2608.11244v1 — resolves (arXiv API) [arXiv preprint, no journal DOI]
3. Chronological Knowledge Retrieval: A Retrieval-Augmented Generation Approach to Construction Project Documentation. *arXiv preprint* (2026). arXiv:2604.14169v1 — resolves (arXiv API) [arXiv preprint, no journal DOI]
4. Edge-Based Agentic Retrieval-Augmented Generation for Autonomous FHWA Bridge Inspection Compliance. *arXiv preprint* (2026). arXiv:2608.20372v1 — resolves (arXiv API) [arXiv preprint, no journal DOI]
5. Grounding Large Language Models (LLMs) in Agency Standards: A Controlled Comparison of Closed-Book, Retrieval-Augmented, and Full-Document Question Answering for Construction Inspection. *engrXiv preprint* (2026). DOI 10.31224/7545 — resolves (Crossref)
6. Knowledge graph-large language model fusion approach for emergency knowledge recommendation in gas tunnels.. *Scientific reports* (2026). DOI 10.1038/s41598-026-39204-0 — resolves (Crossref)
7. Knowledge-driven automated prefabricated bridge modeling from natural language using LLM and RAG.. *Scientific reports* (2026). DOI 10.1038/s41598-026-53765-0 — resolves (Crossref)
8. MMArch: Benchmarking Multimodal Reasoning Grounded in Architectural Evidence. *arXiv preprint* (2026). arXiv:2608.09281v1 — resolves (arXiv API) [arXiv preprint, no journal DOI]
9. Qwen-BIM: developing large language model for BIM-based design with domain-specific benchmark and dataset. *arXiv preprint* (2026). arXiv:2602.20812v1 — resolves (arXiv API) [arXiv preprint, no journal DOI]
10. Seed-Anchored Budget-Bounded Graph Rendering for Question Answering on Industry-Standard Power-Grid Information and Exchange Models. *arXiv preprint* (2026). arXiv:2609.02011v1 — resolves (arXiv API) [arXiv preprint, no journal DOI]
11. Suppressing Domain-Specific Hallucination in Construction LLMs: A Knowledge Graph Foundation for GraphRAG and QLoRA on River and Sediment Control Technical Standards. *arXiv preprint* (2026). arXiv:2603.13307v1 — resolves (arXiv API) [arXiv preprint, no journal DOI]
12. Two stage AI framework for strength prediction and generative LLM for geopolymer concrete.. *Scientific reports* (2026). DOI 10.1038/s41598-026-49329-x — resolves (Crossref)
13. A Large Language Model-Empowered Agent for Reliable and Robust Structural Analysis. *arXiv preprint* (2025). arXiv:2507.02938v1 — resolves (arXiv API) [arXiv preprint, no journal DOI]
14. An Embodied AR Navigation Agent: Integrating BIM with Retrieval-Augmented Generation for Language Guidance. *arXiv preprint* (2025). arXiv:2508.16602v1 — resolves (arXiv API) [arXiv preprint, no journal DOI]
15. Automatic Building Code Review: A Case Study. *arXiv preprint* (2025). arXiv:2510.02634v1 — resolves (arXiv API) [arXiv preprint, no journal DOI]
16. Bridging Dual Knowledge Graphs for Multi-Hop Question Answering in Construction Safety. *arXiv preprint* (2025). DOI 10.1016/j.autcon.2026.106794 — resolves (Crossref)
17. Domain-Specific Fine-Tuning and Prompt-Based Learning: A Comparative Study for developing Natural Language-Based BIM Information Retrieval Systems. *arXiv preprint* (2025). arXiv:2508.05676v1 — resolves (arXiv API) [arXiv preprint, no journal DOI]
18. DrafterBench: Benchmarking Large Language Models for Tasks Automation in Civil Engineering. *arXiv preprint* (2025). arXiv:2507.11527v1 — resolves (arXiv API) [arXiv preprint, no journal DOI]
19. Investigating the Potential of Large Language Model-Based Router Multi-Agent Architectures for Foundation Design Automation: A Task Classification and Expert Selection Study. *arXiv preprint* (2025). arXiv:2506.13811v1 — resolves (arXiv API) [arXiv preprint, no journal DOI]
20. Multi-Agent GraphRAG: A Text-to-Cypher Framework for Labeled Property Graphs. *arXiv preprint* (2025). arXiv:2511.08274v1 — resolves (arXiv API) [arXiv preprint, no journal DOI]
21. Performance evaluation of GPT-4o on South Korean national exams for building mechanical equipment maintenance.. *Scientific reports* (2025). DOI 10.1038/s41598-025-16118-x — resolves (Crossref)
22. Integrating Large Language Models with Multimodal Virtual Reality Interfaces to Support Collaborative Human-Robot Construction Work. *arXiv preprint* (2024). arXiv:2404.03498v1 — resolves (arXiv API) [arXiv preprint, no journal DOI]
23. Question answering system of bridge design specification based on large language model. *arXiv preprint* (2024). arXiv:2408.13282v1 — resolves (arXiv API) [arXiv preprint, no journal DOI]
24. Automating construction contract review using knowledge graph-enhanced large language models. *arXiv preprint* (2023). arXiv:2309.12132v2 — resolves (arXiv API) [arXiv preprint, no journal DOI]
