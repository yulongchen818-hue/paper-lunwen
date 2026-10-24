# Fixed-protocol answer generation: 23 questions x 3 conditions = 69 items.
# Route (i): programmatic LM call via host.llm. temperature=0, max_tokens=400,
# one call per item, serial, no retries except transport error (max 1).
import json, os, re, time, datetime, traceback

IN = "./pilot_inputs.json"
OUT = "pilot_answers.jsonl"
LOG = "gen_log.txt"

P_EVID = """你是施工技术资料问答助手。下面给出一个问题和一组证据条目。规则：(1) 只能依据证据作答，不得使用任何外部知识；(2) 回答中出现的每一个数值、编号、材质牌号、日期等具体值，都必须逐字取自证据，并在其后用方括号标注来源条目的标识符（CDC 证据用条目开头的 sb:… 标识符；RAG 证据用【文件 / 标题】标签），标识符必须与证据中出现的一模一样；(3) 不得计算、换算、估算或推断出证据中没有直接出现的数值；(4) 若证据中不包含问题所要求的数值或记录，明确写"证据中未提供该数值/记录"，不得给出任何替代值；(5) 一次作答，不修改。用中文作答，不超过 200 字。

问题：{q}

证据：
{evidence}"""

P_BARE = """你是施工技术资料问答助手。请回答下面关于{PROJECT_DESCRIPTION}的问题。若你不确定或不知道具体数值，请明确说明不知道，不要猜测。用中文作答，不超过 200 字。

问题：{q}"""

WANT = "claude-sonnet-4-6"          # user-selected: accepts temperature=0
_avail = host.list_models()
assert WANT in _avail, f"{WANT} not available; have {_avail}"
MODEL = WANT
MAX_TOKENS = 400
TEMPERATURE = 0

TRANSPORT_PAT = re.compile(
    r"timeout|timed out|connection|connect|network|socket|overloaded|"
    r"rate.?limit|429|5\d\d|temporar|unavailable|broken pipe|reset",
    re.I,
)

d = json.load(open(IN, encoding="utf-8"))
questions = d["questions"]
evmap = {(e["condition"], e["id"]): e for e in d["evidence"]}

# build the 69 items: per question, CDC-full, RAG-12, NoEvidence
items = []
for q in questions:
    for cond in ("CDC-full", "RAG-12", "NoEvidence"):
        if cond == "NoEvidence":
            prompt = P_BARE.replace("{q}", q["q"])
            ev_chars = 0
        else:
            e = evmap[(cond, q["id"])]
            prompt = P_EVID.replace("{q}", q["q"]).replace("{evidence}", e["evidence"])
            ev_chars = e["chars"]
        items.append({"id": q["id"], "condition": cond, "question": q["q"],
                      "prompt": prompt, "evidence_chars": ev_chars})

assert len(items) == 69, len(items)
json.dump({"model": MODEL, "n_items": len(items)}, open("gen_meta.json", "w"))
# keep the exact prompts as sent, for the report + numeric check
json.dump(items, open("prompts_as_sent.json", "w", encoding="utf-8"), ensure_ascii=False)

log = open(LOG, "a", encoding="utf-8", buffering=1)
fh = open(OUT, "w", encoding="utf-8", buffering=1)

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")

for i, it in enumerate(items, 1):
    deviation = ""
    answer = ""
    attempts = 0
    while True:
        attempts += 1
        try:
            r = host.llm({"prompt": it["prompt"], "model": MODEL,
                          "max_tokens": MAX_TOKENS, "temperature": TEMPERATURE,
                          "thinking": {"type": "disabled"}})
        except Exception as exc:
            r = {"error": f"{type(exc).__name__}: {exc}"}
        err = r.get("error") if isinstance(r, dict) else None
        if not err:
            answer = r.get("text", "")
            if r.get("stop_reason") == "max_tokens":
                deviation = (deviation + "; " if deviation else "") + \
                    "output truncated at max_tokens=400"
            break
        # error path
        if attempts == 1 and TRANSPORT_PAT.search(str(err)):
            log.write(f"{now()} {it['id']}/{it['condition']} transport error, retry once: {err}\n")
            deviation = "retry after transport error: " + str(err)[:200]
            time.sleep(5)
            continue
        deviation = (deviation + "; " if deviation else "") + \
            "not generated: " + str(err)[:300]
        answer = ""
        log.write(f"{now()} {it['id']}/{it['condition']} FAILED: {err}\n")
        break

    rec = {"id": it["id"], "condition": it["condition"], "route": "programmatic host.llm",
           "model": MODEL, "question": it["question"], "answer": answer,
           "evidence_chars": it["evidence_chars"], "generated_at": now(),
           "deviation": deviation}
    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    log.write(f"{now()} [{i}/69] {it['id']}/{it['condition']} ev={it['evidence_chars']} "
              f"len={len(answer)} dev={deviation!r}\n")

fh.close()
log.write(f"{now()} DONE\n")
print("done", MODEL)
