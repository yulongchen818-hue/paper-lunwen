// run_review_v3.js — retrieval-stage comparison for the first-round revision recheck.
// Same 1,321 chunks, same 23 scored questions (B12 excluded), same verbatim scoring as v1/v2.
// Adds: contemporary document-side baselines (BGE-M3 dense, BM25+dense RRF hybrid, cross-encoder rerank;
// rankings from dense_rank.py), the deployed retriever on graph v1.2, and the improved CDC-v2 retriever
// (cdc_v2.js) on v1, v1.1 and v1.2. Also reports item-level precision (share of package items that contain
// at least one scoring token), which is a payload-efficiency measure, not an answer-quality measure.
// Asserts that every condition already in results_v2.json reproduces exactly.  Usage: node run_review_v3.js
const fs = require('fs');
const path = require('path');
const L = require('./lib_retrieval_v2.js');
const { makeGraphV2, recordLine } = require('./cdc_v2.js');
const RES = path.join(__dirname, '..', 'results');
const KG_V12 = path.join(__dirname, '..', 'graph', 'kg_graph_v1_2.json');
const G = { v1: L.makeGraph(L.KG_V1), 'v1.1': L.makeGraph(L.KG_V11), 'v1.2': L.makeGraph(KG_V12) };
const G2 = { v1: makeGraphV2(L.KG_V1), 'v1.1': makeGraphV2(L.KG_V11), 'v1.2': makeGraphV2(KG_V12) };
const bank = JSON.parse(fs.readFileSync(L.BANK_PATH, 'utf8'));
const Qs = bank.questions.filter(q => !q.excluded);
const answerable = Qs.filter(q => q.type === 'answerable');
const chunkString = c => `【${c.doc} / ${c.heading}】\n${c.text}`;
const chunkById = new Map(L.chunks.map(c => [c.id, c]));
const dense = fs.existsSync(path.join(RES, 'dense_rankings.json')) ? JSON.parse(fs.readFileSync(path.join(RES, 'dense_rankings.json'), 'utf8')) : null;

const mkCDC = (g, full) => q => { const r = g.cdcRetrieve(q.q, 6, full); return { evidence: r.evidenceText, items: r.packageIds.length, pkgIds: r.packageIds, nodesById: g.nodesById, itemTexts: r.packageIds.map(id => recordLine(g.nodesById.get(id))) }; };
const mkV2 = (g, budget) => q => { const r = g.retrieve(q.q, budget); return { evidence: r.evidenceText, items: r.packageIds.length, pkgIds: r.packageIds, nodesById: g.nodesById, itemTexts: r.itemTexts }; };
const fromChunks = cs => ({ evidence: cs.map(chunkString).join('\n\n'), items: cs.length, itemTexts: cs.map(chunkString) });
const mkRAG = k => q => fromChunks(L.ragRetrieve(q.q, k).chunks.map(c => chunkById.get(c.id)));
const mkBM = k => q => fromChunks(L.bm25Retrieve(q.q, k).chunks.map(c => chunkById.get(c.id)));
const mkRank = (list, k) => q => fromChunks(dense.rankings[q.id][list].slice(0, k).map(([i]) => L.chunks[i]));
const meanChars = run => Math.round(answerable.reduce((s, q) => s + run(q).evidence.length, 0) / answerable.length);
function matchK(mk, target) { let best = [12, Infinity, 0]; for (let k = 12; k <= 400; k++) { const m = meanChars(mk(k)); const d = Math.abs(m - target); if (d < best[1]) best = [k, d, m]; if (m > target * 1.2) break; } return best; }
const cdcFullMean = meanChars(mkCDC(G.v1, true));

const C = [];
const add = (name, family, run, note = '') => C.push({ name, family, run, note });
// reproduced v2 conditions
add('CDC-full', 'deployed graph retriever', mkCDC(G.v1, true), 'graph v1, as delivered');
add('CDC-seeds', 'deployed graph retriever', mkCDC(G.v1, false), 'graph v1, seeds only');
add('CDC-full@v1.1', 'deployed graph retriever', mkCDC(G['v1.1'], true));
add('CDC-seeds@v1.1', 'deployed graph retriever', mkCDC(G['v1.1'], false));
add('RAG-6', 'lexical document', mkRAG(6)); add('RAG-12', 'lexical document', mkRAG(12));
add('RAG-94', 'lexical document', mkRAG(94), 'payload-matched to CDC-full');
add('BM25-6', 'lexical document', mkBM(6)); add('BM25-12', 'lexical document', mkBM(12));
// new: deployed retriever on v1.2
add('CDC-full@v1.2', 'deployed graph retriever', mkCDC(G['v1.2'], true));
add('CDC-seeds@v1.2', 'deployed graph retriever', mkCDC(G['v1.2'], false));
// new: contemporary document-side baselines
let denseK = null;
if (dense) {
  add('Dense-6', 'dense / hybrid document', mkRank('dense', 6), 'BGE-M3'); add('Dense-12', 'dense / hybrid document', mkRank('dense', 12), 'BGE-M3');
  denseK = matchK(k => mkRank('dense', k), cdcFullMean);
  add(`Dense-${denseK[0]}`, 'dense / hybrid document', mkRank('dense', denseK[0]), `BGE-M3, payload-matched to CDC-full (mean ${denseK[2]} vs ${cdcFullMean} chars)`);
  add('Hybrid-6', 'dense / hybrid document', mkRank('hybrid', 6), 'BM25 + BGE-M3, RRF k=60'); add('Hybrid-12', 'dense / hybrid document', mkRank('hybrid', 12), 'BM25 + BGE-M3, RRF k=60');
  add('Rerank-6', 'dense / hybrid document', mkRank('rerank', 6), 'hybrid top-50 reranked by bge-reranker-v2-m3'); add('Rerank-12', 'dense / hybrid document', mkRank('rerank', 12), 'hybrid top-50 reranked by bge-reranker-v2-m3');
}
// new: improved graph retriever
for (const v of ['v1', 'v1.1', 'v1.2']) for (const b of [6, 12, 24]) add(`CDC-v2-${b}@${v}`, 'improved graph retriever (post hoc)', mkV2(G2[v], b), b === 6 ? 'seeds only' : `record budget ${b}`);

const scoringTokens = q => [...(q.required_all || []), ...(q.required_any || [])];
const rows = [], audit = [], evidence = [];
for (const q of Qs) for (const c of C) {
  const r = c.run(q); const text = L.normalize(r.evidence);
  const row = { id: q.id, type: q.type, condition: c.name, package_items: r.items, package_chars: r.evidence.length };
  if (q.type === 'answerable') {
    Object.assign(row, L.scoreAnswerable(q, text));
    const toks = scoringTokens(q); const rel = r.itemTexts.filter(t => { const n = L.normalize(t); return toks.some(k => L.tokenPresent(k, n)); }).length;
    row.relevant_items = rel; row.item_precision = r.items ? rel / r.items : 0;
    audit.push(`=== ${q.id} / ${c.name} :: hit=${row.hit} matched=[${row.matched}] missing=[${row.missing}] any=[${row.anyHits}] items=${r.items} relevant=${rel}`);
  } else { row.basis_present = L.basisPresent(q.request_pattern, text, r.pkgIds, r.nodesById || G.v1.nodesById); row.exposure_count = L.exposureCount(q.exposure_keywords, text); audit.push(`=== ${q.id} / ${c.name} :: basis_present=${row.basis_present} exposure=${row.exposure_count}`); }
  rows.push(row);
  if (/^(CDC-v2-12|Rerank-12|Dense-12|Hybrid-12|CDC-full@v1\.2)/.test(c.name)) evidence.push({ id: q.id, condition: c.name, chars: r.evidence.length, items: r.items, evidence: r.evidence });
}
const summary = {};
for (const c of C) {
  const A = rows.filter(r => r.condition === c.name && r.type === 'answerable'), Bq = rows.filter(r => r.condition === c.name && r.type === 'boundary');
  summary[c.name] = { family: c.family, note: c.note, hits: A.filter(r => r.hit).length, absent: Bq.filter(r => !r.basis_present).length, exposure: Bq.reduce((s, r) => s + r.exposure_count, 0),
    mean_chars: Math.round(A.reduce((s, r) => s + r.package_chars, 0) / A.length), mean_items: Math.round(A.reduce((s, r) => s + r.package_items, 0) / A.length * 10) / 10,
    item_precision: Math.round(A.reduce((s, r) => s + r.item_precision, 0) / A.length * 1000) / 1000,
    perQuestion: Object.fromEntries(A.map(r => [r.id, r.hit ? 1 : 0])), boundary: Object.fromEntries(Bq.map(r => [r.id, { basis_present: r.basis_present, exposure: r.exposure_count }])) };
}
// reproduction assertion against results_v2.json
const v2 = JSON.parse(fs.readFileSync(path.join(L.BASE, '07_graph_repair', 'retrieval_v2', 'results_v2.json'), 'utf8'));
const problems = [];
for (const [name, a] of Object.entries(v2.summary)) { const s = summary[name]; if (!s) { problems.push('missing ' + name); continue; } for (const k of ['hits', 'absent', 'exposure', 'mean_chars', 'mean_items']) if (a[k] !== s[k]) problems.push(`${name}.${k} ${s[k]} != ${a[k]}`); if (JSON.stringify(a.perQuestion) !== JSON.stringify(s.perQuestion)) problems.push(name + '.perQuestion'); if (JSON.stringify(a.boundary) !== JSON.stringify(s.boundary)) problems.push(name + '.boundary'); }
// bootstrap-free paired comparison: discordant pairs vs CDC-full and vs RAG-12 (exact two-sided sign test)
function signTest(a, b) { let ab = 0, ba = 0; for (const q of answerable) { const x = summary[a].perQuestion[q.id], y = summary[b].perQuestion[q.id]; if (x && !y) ab++; if (!x && y) ba++; } const n = ab + ba; let p = 0; const k = Math.min(ab, ba); const C2 = (n, r) => { let v = 1; for (let i = 1; i <= r; i++) v = v * (n - r + i) / i; return v; }; for (let i = 0; i <= k; i++) p += C2(n, i); p = Math.min(1, 2 * p / 2 ** n); return { [a + '_only']: ab, [b + '_only']: ba, p: n ? Math.round(p * 1000) / 1000 : 1 }; }
const paired = {};
for (const c of C) for (const ref of ['CDC-full', 'RAG-12', 'BM25-12']) if (c.name !== ref) paired[`${c.name} vs ${ref}`] = signTest(c.name, ref);
const meta = { generated: new Date().toISOString(), chunks: L.N, graphs: Object.fromEntries(Object.entries(G).map(([k, g]) => [k, `${g.kg.nodes.length}/${g.kg.edges.length}`])), cdcFullMeanChars: cdcFullMean,
  denseMatchedK: denseK ? { k: denseK[0], meanChars: denseK[2] } : null, dense: dense ? dense.meta : null, reproductionOfV2: { problems, reproduced: problems.length === 0 } };
fs.writeFileSync(path.join(RES, 'results_v3.json'), JSON.stringify({ meta, summary, paired, rows }, null, 1), 'utf8');
fs.writeFileSync(path.join(RES, 'audit_v3.txt'), audit.join('\n'), 'utf8');
fs.writeFileSync(path.join(RES, 'evidence_v3_selected.json'), JSON.stringify(evidence, null, 1), 'utf8');
// markdown summary
const md = ['# Retrieval-stage comparison — first-round revision recheck (v3)', '', `Corpus ${L.corpusFiles.length} files -> ${L.N} chunks. Graphs (nodes/edges): ${Object.entries(meta.graphs).map(([k, v]) => k + ' ' + v).join('; ')}. CDC-full mean payload ${cdcFullMean} chars.` + (denseK ? ` Dense payload-matched k = ${denseK[0]} (mean ${denseK[2]} chars).` : ''), '', `Reproduction of all v2 conditions: ${problems.length ? 'MISMATCH ' + problems.join('; ') : 'exact'}.`, '',
  '| Condition | Family | Hits/18 | Basis absent/5 | Exposure | Mean chars | Mean items | Item precision | Note |', '|---|---|---|---|---|---|---|---|---|'];
for (const c of C) { const s = summary[c.name]; md.push(`| ${c.name} | ${c.family} | ${s.hits}/18 | ${s.absent}/5 | ${s.exposure} | ${s.mean_chars.toLocaleString('en-US')} | ${s.mean_items} | ${s.item_precision.toFixed(2)} | ${c.note} |`); }
md.push('', '## Per-question hits (answerable items)', '', '| Q | ' + C.map(c => c.name).join(' | ') + ' |', '|---|' + C.map(() => '---').join('|') + '|');
for (const q of answerable) md.push(`| ${q.id} | ` + C.map(c => summary[c.name].perQuestion[q.id] ? 'HIT' : '-').join(' | ') + ' |');
md.push('', '## Boundary items (basis present? / exposure)', '', '| Q | ' + C.map(c => c.name).join(' | ') + ' |', '|---|' + C.map(() => '---').join('|') + '|');
for (const q of Qs.filter(q => q.type === 'boundary')) md.push(`| ${q.id} | ` + C.map(c => { const b = summary[c.name].boundary[q.id]; return (b.basis_present ? 'PRESENT' : 'absent') + '/' + b.exposure; }).join(' | ') + ' |');
md.push('', '## Paired comparisons on the 18 answerable items (exact two-sided sign test on discordant items)', '', '| Comparison | first only | second only | p |', '|---|---|---|---|');
for (const [k, v] of Object.entries(paired)) if (/^(CDC-v2-12|Rerank-12|Dense-12|Hybrid-12|CDC-full@v1\.2)/.test(k)) { const vals = Object.values(v); md.push(`| ${k} | ${vals[0]} | ${vals[1]} | ${v.p} |`); }
fs.writeFileSync(path.join(RES, 'summary_v3.md'), md.join('\n'), 'utf8');
console.log(md.slice(0, C.length + 8).join('\n'));
if (problems.length) process.exit(1);
