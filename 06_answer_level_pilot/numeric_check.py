# Independent, mechanical numeric cross-check. No judgment, no scoring.
# For each answer: normalize full-width -> half-width, drop thousands commas,
# extract numeric tokens, and test whether each token appears as a standalone
# number in that item's evidence text (not preceded/followed by a digit or dot).
import json, csv, re

INPUTS = "./pilot_inputs.json"
ANSWERS = "pilot_answers.jsonl"
OUT = "pilot_numeric_check.csv"


def normalize(s):
    """Full-width -> half-width (ASCII range + ideographic space), then remove
    thousands commas that sit between digits."""
    out = []
    for ch in s:
        o = ord(ch)
        if 0xFF01 <= o <= 0xFF5E:          # full-width ! .. ~  ->  ASCII
            out.append(chr(o - 0xFEE0))
        elif o == 0x3000:                  # ideographic space -> space
            out.append(" ")
        else:
            out.append(ch)
    s = "".join(out)
    s = re.sub(r"(?<=\d),(?=\d)", "", s)   # 1,234 -> 1234
    return s


TOKEN_RE = re.compile(r"\d+(?:\.\d+)*")    # integer or decimal / dotted numeric run


def tokens(text):
    """Numeric tokens in first-appearance order, de-duplicated."""
    seen, out = set(), []
    for m in TOKEN_RE.finditer(text):
        t = m.group(0)
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def standalone(token, evidence):
    """token occurs in evidence not preceded or followed by a digit or a dot."""
    pat = r"(?<![\d.])" + re.escape(token) + r"(?![\d.])"
    return re.search(pat, evidence) is not None


d = json.load(open(INPUTS, encoding="utf-8"))
ev_norm = {(e["condition"], e["id"]): normalize(e["evidence"]) for e in d["evidence"]}

rows = []
with open(ANSWERS, encoding="utf-8") as fh:
    for line in fh:
        r = json.loads(line)
        ans = normalize(r["answer"])
        for t in tokens(ans):
            if r["condition"] == "NoEvidence":
                verdict = "no evidence"
            else:
                verdict = "true" if standalone(t, ev_norm[(r["condition"], r["id"])]) else "false"
            rows.append({"id": r["id"], "condition": r["condition"],
                         "token": t, "in_evidence": verdict})

with open(OUT, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["id", "condition", "token", "in_evidence"])
    w.writeheader()
    w.writerows(rows)

from collections import Counter
tally = Counter((r["condition"], r["in_evidence"]) for r in rows)
json.dump({f"{k[0]}|{k[1]}": v for k, v in tally.items()},
          open("numeric_tally.json", "w"), indent=1)
print(len(rows), dict(tally))
