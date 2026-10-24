"""Stage 3: per-paper field extraction from retrieved full text, with mechanical
verbatim-quote verification. Quotes that cannot be found in the source text are
discarded rather than reported."""
import json, os, re

SCHEMA_KEYS = ["in_domain", "evaluates_llm_qa", "task_domain", "n_items", "eval_type",
               "metrics", "n_human_raters", "rater_independence", "agreement_stat",
               "abstention_included", "hallucination_rate", "quote_agreement",
               "quote_hallucination", "confidence"]

SYS = """You extract evaluation-methodology facts from a research paper's full text for a
systematic survey. You read the whole paper but the facts you need live in the
Methods / Experiments / Evaluation sections, not the abstract.

Return ONE JSON object, no prose, with exactly these keys:

"in_domain": "yes" | "no"  — is the application domain civil / structural / construction
    engineering, construction management, built environment, BIM, bridges, geotechnics or
    transport infrastructure? "no" for general NLP, medicine, law-in-general, geology,
    manufacturing, finance, education-in-general.
"evaluates_llm_qa": "yes" | "no" — does the paper empirically evaluate a large-language-model
    or retrieval-augmented system that answers questions / queries (any evaluation counts:
    automatic metrics, LLM-as-judge, human rating, exam accuracy)?
"task_domain": short phrase, <=15 words, e.g. "building-code QA; Chinese GB standards".
"n_items": the number of questions / test items evaluated, as a number with a short
    qualifier if needed, e.g. "70 inspection questions", "2140 exam questions",
    "150 (50 per type)". "not found" if never stated.
"eval_type": "automatic" | "human" | "both" | "LLM-as-judge" | "automatic + LLM-as-judge"
    | "not found" — what kinds of scoring were actually run.
"metrics": semicolon-separated list of the evaluation metrics actually used, using the
    paper's own names, e.g. "BLEU-4; ROUGE-L; BERTScore; accuracy; RAGAS faithfulness;
    human Likert 1-5; hallucination rate". "not found" if none.
"n_human_raters": number of human raters/annotators/experts who scored SYSTEM OUTPUTS
    (not the number of people who wrote questions), e.g. "3", "1 licensed PE", "not found",
    or "none (no human rating)".
"rater_independence": "authors" | "external practitioners" | "external, blinded" |
    "students" | "mixed" | "not stated" | "no human rating" — and add "blinded" only if the
    paper says raters were blinded.
"agreement_stat": the inter-rater agreement statistic AND its value exactly as reported,
    e.g. "Krippendorff alpha = 0.81", "Cohen kappa = 0.72", "Fleiss kappa not reported",
    "ICC = 0.9", "none reported". Use "none reported" when there is no agreement statistic.
"abstention_included": "yes" | "no" | "not stated" — did the test set deliberately include
    unanswerable / out-of-scope questions, or measure refusal / abstention / "I don't know"
    behaviour? "yes" only if the paper says so.
"hallucination_rate": any reported numeric rate of hallucination, unsupported claims,
    factual error or groundedness failure, with its value and what it measures, e.g.
    "56-64% of closed-book answers judged factually unacceptable"; "hallucination rate 12.5%".
    "not found" if no numeric rate is reported.
"quote_agreement": ONE verbatim sentence or clause copied EXACTLY from the paper, character
    for character, that supports the agreement_stat field (or shows human rating was done
    without an agreement statistic). If nothing in the paper speaks to inter-rater
    agreement or human rating, use exactly "not found".
"quote_hallucination": ONE verbatim sentence or clause copied EXACTLY from the paper that
    supports the hallucination_rate field, or exactly "not found".
"confidence": "explicit" (fields read directly off statements in the text) | "inferred"
    (you had to reason from indirect wording) | "not found" (the paper says almost nothing
    about human evaluation or grounding).

RULES: copy quotes verbatim from the supplied text — never reconstruct, translate,
paraphrase, or fix typos in a quote. Never guess a number. Prefer "not found" or
"not stated" over any inference. Output JSON only."""


def call_extract(host, texts, model, max_chars=170000):
    reqs = []
    for t in texts:
        reqs.append({"prompt": "PAPER FULL TEXT:\n\n" + t[:max_chars],
                     "system": SYS, "model": model, "max_tokens": 1600,
                     "thinking": {"type": "disabled"}})
    return host.llm(reqs, max_concurrency=6)


def parse_json(txt):
    m = re.search(r"\{.*\}", txt or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def squash(s):
    """whitespace-insensitive, quote-insensitive form for quote verification"""
    s = (s or "").replace("\u2019", "'").replace("\u2018", "'")
    s = s.replace("\u201c", '"').replace("\u201d", '"')
    s = s.replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")
    s = re.sub(r"[\s\u00a0]+", " ", s)
    return s.strip().lower()


def verify_quote(quote, source):
    """True if the quote occurs in the source text ignoring whitespace/quote-style.
    Also accepts a de-hyphenated match (PDF line-break hyphenation)."""
    if not quote or quote.strip().lower() in ("not found", "none", ""):
        return None                      # nothing claimed
    q, s = squash(quote), squash(source)
    if q in s:
        return True
    if q.replace("- ", "").replace("-", "") in s.replace("- ", "").replace("-", ""):
        return True
    return False
