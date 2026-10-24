// run_baseline_v2.js — reconstructed stand-alone script for the v2 retrieval-stage comparison
// (07_graph_repair/retrieval_v2/results_v2.json). The original logic lived inside
// 08_answer_level_pilot_v2/generation/dump_evidence_v3.js with its result writers disabled; this file
// re-runs exactly that logic (imported verbatim via lib_retrieval_v2.js) and asserts that every summary
// figure and every per-question row reproduces the archived results_v2.json.
// Usage: node run_baseline_v2.js
const fs = require('fs');
const path = require('path');
const L = require('./lib_retrieval_v2.js');

const OUT_DIR = path.join(__dirname, '..', 'results', 'reproduced_v2');
fs.mkdirSync(OUT_DIR, { recursive: true });
const G1 = L.makeGraph(L.KG_V1), G11 = L.makeGraph(L.KG_V11);
const bank = JSON.parse(fs.readFileSync(L.BANK_PATH, 'utf8'));
const Qs = bank.questions.filter(q => !q.excluded);
const answerable = Qs.filter(q => q.type === 'answerable');
const mkCDC = (G, full) => q => { const r = G.cdcRetrieve(q, 6, full); return { evidence: r.evidenceText, items: r.packageIds.length, pkgIds: r.packageIds, nodesById: G.nodesById }; };
const mkRAG = k => q => { const r = L.ragRetrieve(q, k); return { evidence: r.evidenceText, items: r.chunks.length }; };
const mkBM = k => q => { const r = L.bm25Retrieve(q, k); return { evidence: r.evidenceText, items: r.chunks.length }; };
const cdcFullMean = Math.round(answerable.reduce((s, q) => s + mkCDC(G1, true)(q.q).evidence.length, 0) / answerable.length);
let bestK = 12, bestDiff = Infinity, bestMean = 0;
for (let k = 12; k <= 400; k++) { const m = Math.round(answerable.reduce((s, q) => s + mkRAG(k)(q.q).evidence.length, 0) / answerable.length); const d = Math.abs(m - cdcFullMean); if (d < bestDiff) { bestDiff = d; bestK = k; bestMean = m; } if (m > cdcFullMean * 1.2) break; }
const CONDITIONS = [
  { name: 'CDC-full', run: mkCDC(G1, true) }, { name: 'CDC-seeds', run: mkCDC(G1, false) },
  { name: 'RAG-6', run: mkRAG(6) }, { name: 'RAG-12', run: mkRAG(12) },
  { name: `RAG-${bestK}`, run: mkRAG(bestK), note: `payload-matched to CDC-full (mean ${bestMean} vs ${cdcFullMean} chars)` },
  { name: 'BM25-6', run: mkBM(6) }, { name: 'BM25-12', run: mkBM(12) },
  { name: 'CDC-full@v1.1', run: mkCDC(G11, true) }, { name: 'CDC-seeds@v1.1', run: mkCDC(G11, false) },
];
const rows = [];
for (const q of Qs) for (const cond of CONDITIONS) {
  const r = cond.run(q.q); const text = L.normalize(r.evidence);
  const row = { id: q.id, type: q.type, condition: cond.name, package_items: r.items, package_chars: r.evidence.length };
  if (q.type === 'answerable') Object.assign(row, L.scoreAnswerable(q, text));
  else { row.basis_present = L.basisPresent(q.request_pattern, text, r.pkgIds, r.nodesById || G1.nodesById); row.exposure_count = L.exposureCount(q.exposure_keywords, text); }
  rows.push(row);
}
const summary = {};
for (const c of CONDITIONS) {
  const A = rows.filter(r => r.condition === c.name && r.type === 'answerable'), Bq = rows.filter(r => r.condition === c.name && r.type === 'boundary');
  summary[c.name] = { hits: A.filter(r => r.hit).length, absent: Bq.filter(r => !r.basis_present).length, exposure: Bq.reduce((s, r) => s + r.exposure_count, 0),
    mean_chars: Math.round(A.reduce((s, r) => s + r.package_chars, 0) / A.length), mean_items: Math.round(A.reduce((s, r) => s + r.package_items, 0) / A.length * 10) / 10,
    note: c.note || '', perQuestion: Object.fromEntries(A.map(r => [r.id, r.hit ? 1 : 0])), boundary: Object.fromEntries(Bq.map(r => [r.id, { basis_present: r.basis_present, exposure: r.exposure_count }])) };
}
// ---- reproduction assertions ----
const archived = JSON.parse(fs.readFileSync(path.join(L.BASE, '07_graph_repair', 'retrieval_v2', 'results_v2.json'), 'utf8'));
const problems = [];
if (bestK !== archived.meta.payloadMatchedK) problems.push(`payload-matched k ${bestK} != ${archived.meta.payloadMatchedK}`);
for (const [name, s] of Object.entries(summary)) {
  const a = archived.summary[name]; if (!a) { problems.push('missing condition ' + name); continue; }
  for (const k of ['hits', 'absent', 'exposure', 'mean_chars', 'mean_items']) if (a[k] !== s[k]) problems.push(`${name}.${k}: ${s[k]} != ${a[k]}`);
  if (JSON.stringify(a.perQuestion) !== JSON.stringify(s.perQuestion)) problems.push(`${name}.perQuestion differs`);
  if (JSON.stringify(a.boundary) !== JSON.stringify(s.boundary)) problems.push(`${name}.boundary differs`);
}
const rowKey = r => `${r.id}|${r.condition}`; const archivedRows = new Map(archived.rows.map(r => [rowKey(r), r]));
let rowsChecked = 0;
for (const r of rows) { const a = archivedRows.get(rowKey(r)); rowsChecked++; if (!a || a.package_chars !== r.package_chars || a.package_items !== r.package_items || (r.type === 'answerable' ? a.hit !== r.hit : a.basis_present !== r.basis_present || a.exposure_count !== r.exposure_count)) problems.push('row ' + rowKey(r)); }
const v1 = JSON.parse(fs.readFileSync(path.join(L.BASE, '03_baseline_experiment', 'results', 'results_full.json'), 'utf8'));
for (const c of ['CDC-full', 'CDC-seeds', 'RAG-6', 'RAG-12']) if (summary[c].hits !== v1.summary_answerable[c].hits || summary[c].mean_chars !== v1.summary_answerable[c].mean_chars) problems.push('frozen v1 mismatch ' + c);
const report = { generated: new Date().toISOString(), payloadMatchedK: bestK, cdcFullMeanChars: cdcFullMean, matchedMeanChars: bestMean, rowsChecked, problems, reproduced: problems.length === 0 };
fs.writeFileSync(path.join(OUT_DIR, 'results_v2_reproduced.json'), JSON.stringify({ meta: report, summary, rows }, null, 1), 'utf8');
console.log(JSON.stringify(report, null, 1));
if (problems.length) process.exit(1);
