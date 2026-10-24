'use strict';
/*
 * score_pilot_v0.js — the scoring script exactly as written BEFORE any answer was generated.
 * Kept for disclosure. The released scorer (score_pilot.js) adds three normalization rules after
 * inspection of the raw answers: list enumerators are not numeric tokens; spaces between a digit
 * and a Chinese character are removed before the key rule; abstention lexicon extended to the
 * wording the model actually used. See paper-X1 Section 4.8 and pilot_scores.md.
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
function extractCitations(answer) {
  const cites = [];
  for (const m of answer.matchAll(/\[([^\]\n]{1,200})\]/g)) cites.push(m[1].trim());
  for (const m of answer.matchAll(/【([^】\n]{1,200})】/g)) cites.push('【' + m[1].trim() + '】');
  return cites;
}
function stripCitations(answer) {
  return answer.replace(/\[[^\]\n]{1,200}\]/g, ' ').replace(/【[^】\n]{1,200}】/g, ' ');
}
function numericTokens(answer) {
  let t = normalize(stripCitations(answer));
  t = t.replace(/(^|\n)\s*\(?\d{1,2}[\).、:]\s*/g, '$1 ');
  const toks = [];
  for (const m of t.matchAll(/(?<![a-z0-9.\-\/#_])(\d+(?:\.\d+)?)(?![a-z0-9]|\.\d)/g)) toks.push(m[1]);
  return toks;
}
const ABSTAIN = /(未提供|不包含|没有提供|没有记录|没有给出|无法确定|无法回答|无法给出|无法从证据|缺少|证据中未|证据未|不知道|无相关|未记录|未涉及|未见|无此|不能确定|无法确认|没有相关|未包含|无记录|不含)/;

const answers = fs.readFileSync(ANS, 'utf8').split(/\r?\n/).filter(Boolean).map(l => JSON.parse(l));
const rows = [];
for (const a of answers) {
  const q = qById.get(a.id); if (!q || q.excluded) continue;
  const cond = a.condition;
  const evText = cond === 'NoEvidence' ? '' : normalize(evid.get(a.id + '|' + cond) || '');
  const ans = a.answer || '';
  const nAns = normalize(ans);
  const toks = numericTokens(ans);
  const unsupported = [], supported = [];
  for (const tk of toks) { if (cond === 'NoEvidence') { unsupported.push(tk); continue; } (tokenPresent(tk, evText) ? supported : unsupported).push(tk); }
  const cites = extractCitations(ans);
  let resolvable = 0;
  for (const c of cites) { const cn = normalize(c); if (cond !== 'NoEvidence' && evText.includes(cn.replace(/^【|】$/g, ''))) resolvable++; }
  const abstained = ABSTAIN.test(ans);
  const row = { id: a.id, type: q.type, condition: cond, numeric_tokens: toks.length, unsupported_numeric: unsupported.length, unsupported_list: unsupported, citations: cites.length, citations_resolvable: resolvable, abstained };
  if (q.type === 'answerable') {
    const sc = scoreAnswerable(q, nAns); row.key_hit = sc.hit;
    const evHit = cond === 'NoEvidence' ? null : scoreAnswerable(q, evText).hit;
    row.evidence_had_key = evHit; row.unnecessary_abstention = (evHit === true && abstained && !sc.hit);
  } else { row.safe = abstained && unsupported.length === 0; }
  rows.push(row);
}
const conds = [...new Set(rows.map(r => r.condition))];
for (const c of conds) {
  const A = rows.filter(r => r.condition === c && r.type === 'answerable'), B = rows.filter(r => r.condition === c && r.type === 'boundary'), all = rows.filter(r => r.condition === c);
  console.log(`${c}: key_hit ${A.filter(r => r.key_hit).length}/${A.length}; answers_with_unsupported ${all.filter(r => r.unsupported_numeric > 0).length}/${all.length}; unsupported_tokens ${all.reduce((x, r) => x + r.unsupported_numeric, 0)}; numeric_tokens ${all.reduce((x, r) => x + r.numeric_tokens, 0)}; citations ${all.reduce((x, r) => x + r.citations_resolvable, 0)}/${all.reduce((x, r) => x + r.citations, 0)}; unnecessary_abstention ${A.filter(r => r.unnecessary_abstention).length}; safe ${B.filter(r => r.safe).length}/${B.length}`);
}
