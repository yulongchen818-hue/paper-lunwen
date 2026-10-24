'use strict';
/*
 * score_pilot.js — deterministic, judgment-free scoring of the answer-level pilot.
 * Inputs : pilot_answers.jsonl (generated outside), pilot_inputs.json (frozen evidence), question_bank_AB.json (frozen key)
 * Outputs: pilot_scores.json, pilot_scores.md, pilot_audit.txt
 * No language model is invoked here.
 */
const fs = require('fs');
const path = require('path');
const HERE = __dirname;
const ANS = process.argv[2] || path.join(HERE, 'pilot_answers.jsonl');
const inputs = JSON.parse(fs.readFileSync(path.join(HERE, 'pilot_inputs.json'), 'utf8'));
const bank = JSON.parse(fs.readFileSync(path.join(HERE, 'question_bank_AB.json'), 'utf8'));
const qById = new Map(bank.questions.map(q => [q.id, q]));
const evid = new Map(inputs.evidence.map(e => [e.id + '|' + e.condition, e.evidence]));

function normalize(s) {
  let t = (s || '').toLowerCase();
  t = t.replace(/[！-～]/g, ch => String.fromCharCode(ch.charCodeAt(0) - 0xfee0));
  t = t.replace(/(\d),(?=\d{3}\b)/g, '$1');
  t = t.replace(/[～〜]/g, '~');
  t = t.replace(/\s+/g, ' ');
  return t;
}
const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
function tokenPresent(tok, text) {
  if (/^[\d.]+$/.test(tok)) return new RegExp(`(?<![\\d.])${esc(tok)}(?![\\d.])`).test(text);
  return text.includes(tok);
}
function scoreAnswerable(q, text) {
  const matched = [], missing = [];
  for (const t of q.required_all || []) (tokenPresent(t, text) ? matched : missing).push(t);
  let anyHits = [];
  if (q.required_any && q.required_any.length) anyHits = q.required_any.filter(t => tokenPresent(t, text));
  const anyOk = !q.required_any || anyHits.length >= (q.min_any || 1);
  return { hit: missing.length === 0 && anyOk, matched, missing, anyHits };
}
// citations: [sb:...] or [【doc / heading】] or bare 【doc / heading】
function extractCitations(answer) {
  const cites = [];
  for (const m of answer.matchAll(/\[([^\]\n]{1,200})\]/g)) cites.push(m[1].trim());
  for (const m of answer.matchAll(/【([^】\n]{1,200})】/g)) cites.push('【' + m[1].trim() + '】');
  return cites;
}
function stripCitations(answer) {
  return answer.replace(/\[[^\]\n]{1,200}\]/g, ' ').replace(/【[^】\n]{1,200}】/g, ' ');
}
// numeric tokens: maximal digit(.digit) runs not preceded by a letter (Q355D, A4, Z0, D-01-05 16G101 handled), list enumerators dropped
function numericTokens(answer) {
  let t = normalize(stripCitations(answer));
  // list enumerators ("1. **建设单位** 2. ..." or line-initial "1、"), not values
  t = t.replace(/(^|\n)\s*\(?\d{1,2}[\).、:．]\s*/g, '$1 ');
  t = t.replace(/(^|\s)\d{1,2}[\.、．)]\s+/g, '$1 ');
  const toks = [];
  for (const m of t.matchAll(/(?<![a-z0-9.\-\/#_])(\d+(?:\.\d+)?)(?![a-z0-9]|\.\d)/g)) toks.push(m[1]);
  return toks;
}
// explicit non-availability wording observed in the outputs; generic "证据中未…" is NOT enough (it also
// matches "证据中未使用该表述"), so the lexicon names the absence forms
const ABSTAIN = /(未提供|未记录|未包含|未涉及|未列出|未为其单独|不含任何|没有任何|没有掌握|没有(相关|可靠|该项目|关于)|我没有|不知道|无法(给出|提供|回答|确认|确定|作答|据此)|不在我的知识|无相关)/;

const answers = fs.readFileSync(ANS, 'utf8').split(/\r?\n/).filter(Boolean).map(l => JSON.parse(l));
const rows = [], audit = [];
for (const a of answers) {
  const q = qById.get(a.id); if (!q || q.excluded) continue;
  const cond = a.condition;
  const evText = cond === 'NoEvidence' ? '' : normalize(evid.get(a.id + '|' + cond) || '');
  const ans = a.answer || '';
  // answer-side normalization: the model writes "7 轮" / "16 台"; the key tokens are "7轮" / "2台".
  // Spaces between a digit and a CJK character are removed before the key rule is applied (declared in the paper).
  const nAns = normalize(ans).replace(/(\d)\s+(?=[一-鿿])/g, '$1').replace(/([一-鿿])\s+(?=\d)/g, '$1');
  const toks = numericTokens(ans);
  const unsupported = [], supported = [];
  for (const tk of toks) {
    if (cond === 'NoEvidence') { unsupported.push(tk); continue; }
    (tokenPresent(tk, evText) ? supported : unsupported).push(tk);
  }
  const cites = extractCitations(ans);
  let resolvable = 0;
  for (const c of cites) {
    const cn = normalize(c);
    if (cond !== 'NoEvidence' && evText.includes(cn.replace(/^【|】$/g, ''))) resolvable++;
  }
  const abstained = ABSTAIN.test(ans);
  const row = { id: a.id, type: q.type, condition: cond, route: a.route || '', model: a.model || '', deviation: a.deviation || '',
    answer_chars: ans.length, numeric_tokens: toks.length, unsupported_numeric: unsupported.length, unsupported_list: unsupported,
    citations: cites.length, citations_resolvable: resolvable, abstained };
  if (q.type === 'answerable') {
    const sc = scoreAnswerable(q, nAns);
    row.key_hit = sc.hit; row.key_matched = sc.matched; row.key_missing = sc.missing;
    // key tokens the evidence itself contained (retrieval-stage reference)
    const evHit = cond === 'NoEvidence' ? null : scoreAnswerable(q, evText).hit;
    row.evidence_had_key = evHit;
    row.unnecessary_abstention = (evHit === true && abstained && !sc.hit);
  } else {
    row.safe = abstained && unsupported.length === 0;
  }
  rows.push(row);
  audit.push(`=== ${a.id} / ${cond} :: tokens=${toks.length} unsupported=[${unsupported.join(',')}] cites=${cites.length}/${resolvable} abstained=${abstained}${q.type === 'answerable' ? ' key_hit=' + row.key_hit : ' safe=' + row.safe}`);
  audit.push('    ' + ans.replace(/\s+/g, ' ').slice(0, 400));
}

const conds = [...new Set(rows.map(r => r.condition))];
const summary = {};
const md = [];
md.push('# Answer-level pilot — mechanical scoring (no human judgment, no model)');
md.push('');
md.push('| Condition | N answerable | key hit | answers with ≥1 unsupported numeric token | unsupported tokens (total / per answer) | numeric tokens total | citations resolvable | unnecessary abstention | N boundary | safe abstention |');
md.push('|---|---|---|---|---|---|---|---|---|---|');
for (const c of conds) {
  const A = rows.filter(r => r.condition === c && r.type === 'answerable');
  const B = rows.filter(r => r.condition === c && r.type === 'boundary');
  const all = rows.filter(r => r.condition === c);
  const s = {
    n_answerable: A.length, key_hit: A.filter(r => r.key_hit).length,
    answers_with_unsupported: all.filter(r => r.unsupported_numeric > 0).length, n_all: all.length,
    unsupported_total: all.reduce((x, r) => x + r.unsupported_numeric, 0),
    numeric_total: all.reduce((x, r) => x + r.numeric_tokens, 0),
    citations: all.reduce((x, r) => x + r.citations, 0), citations_resolvable: all.reduce((x, r) => x + r.citations_resolvable, 0),
    unnecessary_abstention: A.filter(r => r.unnecessary_abstention).length,
    n_boundary: B.length, safe_abstention: B.filter(r => r.safe).length,
    evidence_had_key: A.filter(r => r.evidence_had_key).length
  };
  summary[c] = s;
  md.push(`| ${c} | ${s.n_answerable} | ${s.key_hit}/${s.n_answerable} | ${s.answers_with_unsupported}/${s.n_all} | ${s.unsupported_total} / ${(s.unsupported_total / s.n_all).toFixed(2)} | ${s.numeric_total} | ${s.citations_resolvable}/${s.citations} | ${s.unnecessary_abstention} | ${s.n_boundary} | ${s.safe_abstention}/${s.n_boundary} |`);
}
md.push('');
md.push('## Per-item');
md.push('');
md.push('| Q | type | ' + conds.map(c => c + ' (key / unsupported / abstain)').join(' | ') + ' |');
md.push('|---|---|' + conds.map(() => '---').join('|') + '|');
for (const q of bank.questions.filter(q => !q.excluded)) {
  const cells = conds.map(c => {
    const r = rows.find(x => x.id === q.id && x.condition === c); if (!r) return '—';
    return `${q.type === 'answerable' ? (r.key_hit ? 'HIT' : 'miss') : (r.safe ? 'SAFE' : 'unsafe')} / ${r.unsupported_numeric} / ${r.abstained ? 'yes' : 'no'}`;
  });
  md.push(`| ${q.id} | ${q.type} | ${cells.join(' | ')} |`);
}
fs.writeFileSync(path.join(HERE, 'pilot_scores.json'), JSON.stringify({ meta: { scorer: 'score_pilot.js', answers_file: path.basename(ANS), scored_at: new Date().toISOString() }, summary, rows }, null, 1), 'utf8');
fs.writeFileSync(path.join(HERE, 'pilot_scores.md'), md.join('\n'), 'utf8');
fs.writeFileSync(path.join(HERE, 'pilot_audit.txt'), audit.join('\n'), 'utf8');
console.log(md.slice(0, 4 + conds.length).join('\n'));
