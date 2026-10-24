// cdc_v2.js — improved cite-don't-compute retriever (revision round 1 recheck; post hoc, disclosed as such).
// Three changes to the deployed retriever, each taken from the literature with its published default and
// none tuned on the question bank:
//  (1) index what you cite: every record is indexed by exactly the text it contributes to the evidence
//      package (all property values, as printed by the deployed formatter), not by a hand-picked field list;
//  (2) seed scoring by Okapi BM25 over those record texts (k1 = 1.2, b = 0.75; Robertson & Zaragoza 2009),
//      with the same tokenisation (Latin tokens + Chinese character bigrams) as every other condition;
//  (3) relevance-gated expansion by personalized PageRank from the seeds (damping 0.5 as in HippoRAG,
//      Gutierrez et al. 2024) over the undirected relation graph, keeping a fixed record budget, instead
//      of adding every one-hop neighbour of every seed (which pulls in the 146-edge project hub).
// The evidence format, the identifiers and the scoring code are unchanged.
const L = require('./lib_retrieval_v2.js');
const fs = require('fs');

function recordLine(n) { const flat = []; L.flattenProps(n.props || {}, flat); return `[${n.type}] ${n.name} (${n.id}) :: ${flat.join(' | ')}`; }

function makeGraphV2(kgPath, opts = {}) {
  const { seeds: SEEDS = 6, damping: D = 0.5, iters: IT = 100, k1: K1 = 1.2, b: B = 0.75 } = opts;
  const kg = JSON.parse(fs.readFileSync(kgPath, 'utf8'));
  const nodes = kg.nodes.map(n => ({ ...n, line: recordLine(n) }));
  const byId = new Map(nodes.map(n => [n.id, n]));
  const idx = new Map(nodes.map((n, i) => [n.id, i]));
  // BM25 statistics over record lines
  const tfs = nodes.map(n => { const tf = new Map(); for (const t of L.chunkTerms(n.line)) tf.set(t, (tf.get(t) || 0) + 1); return tf; });
  const df = new Map(); for (const tf of tfs) for (const t of tf.keys()) df.set(t, (df.get(t) || 0) + 1);
  const lens = tfs.map(tf => { let s = 0; for (const f of tf.values()) s += f; return s; });
  const avg = lens.reduce((a, b) => a + b, 0) / lens.length, N = nodes.length;
  const idf = t => Math.log(1 + (N - (df.get(t) || 0) + 0.5) / ((df.get(t) || 0) + 0.5));
  // undirected neighbour sets (parallel edges collapsed) and edge labels per pair
  const nb = nodes.map(() => new Set()); const pairLabels = new Map();
  for (const e of kg.edges) { const a = idx.get(e.source), c = idx.get(e.target); if (a === undefined || c === undefined || a === c) continue; nb[a].add(c); nb[c].add(a); const k = a < c ? `${a}|${c}` : `${c}|${a}`; if (!pairLabels.has(k)) pairLabels.set(k, new Set()); pairLabels.get(k).add(e.label_en); }
  const nbl = nb.map(s => [...s].sort((x, y) => x - y));

  function scoreAll(query) {
    const q = [...new Set(L.terms(query))];
    return tfs.map((tf, i) => { let s = 0; for (const t of q) { const f = tf.get(t); if (!f) continue; s += idf(t) * (f * (K1 + 1)) / (f + K1 * (1 - B + B * lens[i] / avg)); } return s; });
  }
  function ppr(seedIdx, seedScore) {
    const p = new Float64Array(N); const tot = seedScore.reduce((a, b) => a + b, 0);
    seedIdx.forEach((i, j) => { p[i] = seedScore[j] / tot; });
    let r = Float64Array.from(p);
    for (let it = 0; it < IT; it++) {
      const nx = new Float64Array(N);
      for (let u = 0; u < N; u++) { if (!r[u]) continue; const d = nbl[u].length; if (!d) { nx[u] += D * r[u]; continue; } const share = D * r[u] / d; for (const v of nbl[u]) nx[v] += share; }
      for (let u = 0; u < N; u++) nx[u] += (1 - D) * p[u];
      r = nx;
    }
    return r;
  }
  function retrieve(query, budget = 12) {
    const sc = scoreAll(query);
    const ranked = sc.map((s, i) => [s, i]).filter(([s]) => s > 0).sort((a, b) => b[0] - a[0] || (nodes[a[1]].id < nodes[b[1]].id ? -1 : 1));
    const seed = ranked.slice(0, SEEDS);
    const pkg = seed.map(([, i]) => i);
    if (budget > pkg.length && seed.length) {
      const r = ppr(seed.map(([, i]) => i), seed.map(([s]) => s));
      const inPkg = new Set(pkg);
      const rest = [...r.keys()].filter(i => !inPkg.has(i) && r[i] > 0).sort((a, b) => r[b] - r[a] || (nodes[a].id < nodes[b].id ? -1 : 1));
      for (const i of rest) { if (pkg.length >= budget) break; pkg.push(i); }
    }
    const rels = new Set(); const set = new Set(pkg);
    for (const a of pkg) for (const c of nbl[a]) if (set.has(c)) for (const l of pairLabels.get(a < c ? `${a}|${c}` : `${c}|${a}`)) rels.add(l);
    const lines = pkg.map(i => nodes[i].line);
    if (rels.size) lines.push('relations: ' + [...rels].sort().join(', '));
    return { seeds: seed.map(([s, i]) => ({ id: nodes[i].id, score: Math.round(s * 100) / 100 })), packageIds: pkg.map(i => nodes[i].id), itemTexts: pkg.map(i => nodes[i].line), evidenceText: lines.join('\n') };
  }
  return { kg, nodesById: byId, retrieve, recordLine };
}
module.exports = { makeGraphV2, recordLine };
