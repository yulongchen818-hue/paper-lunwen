// coverage_ceiling.js — what each evidence base CONTAINS, independent of ranking.
// For every answerable item, the scoring function of every other condition is applied to (a) each single
// record / chunk and (b) the union of all records / chunks of the evidence base. (a) is the ceiling of any
// retriever that returns the right single item; (b) is a loose upper bound (tokens may be spread over items).
// Usage: node coverage_ceiling.js  -> results/coverage_ceiling.{json,md}
const fs = require('fs'), path = require('path');
const L = require('./lib_retrieval_v2.js');
const { recordLine } = require('./cdc_v2.js');
const RES = path.join(__dirname, '..', 'results');
const KG = { v1: L.KG_V1, 'v1.1': L.KG_V11, 'v1.2': path.join(__dirname, '..', 'graph', 'kg_graph_v1_2.json') };
const bank = JSON.parse(fs.readFileSync(L.BANK_PATH, 'utf8'));
const A = bank.questions.filter(q => !q.excluded && q.type === 'answerable');
const bases = {};
for (const [v, p] of Object.entries(KG)) bases['graph ' + v] = JSON.parse(fs.readFileSync(p, 'utf8')).nodes.map(n => L.normalize(recordLine(n)));
bases['documents (1,321 chunks)'] = L.chunks.map(c => L.normalize(`【${c.doc} / ${c.heading}】\n${c.text}`));
const out = {}; const md = ['# Coverage ceiling (independent of ranking)', '', '| Evidence base | single item | union of items | items not covered (union) |', '|---|---|---|---|'];
for (const [b, items] of Object.entries(bases)) {
  const all = items.join('\n'); const single = {}, union = {};
  for (const q of A) { union[q.id] = !!L.scoreAnswerable(q, all).hit; single[q.id] = items.some(t => L.scoreAnswerable(q, t).hit); }
  out[b] = { single, union, single_n: Object.values(single).filter(Boolean).length, union_n: Object.values(union).filter(Boolean).length };
  md.push(`| ${b} | ${out[b].single_n}/18 | ${out[b].union_n}/18 | ${A.filter(q => !union[q.id]).map(q => q.id).join(', ')} |`);
}
fs.writeFileSync(path.join(RES, 'coverage_ceiling.json'), JSON.stringify(out, null, 1));
fs.writeFileSync(path.join(RES, 'coverage_ceiling.md'), md.join('\n'));
console.log(md.join('\n'));
