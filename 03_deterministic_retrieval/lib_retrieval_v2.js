'use strict';
/*
 * lib_retrieval_v2.js - verbatim extraction of the retrieval, chunking and scoring code of
 * 08_answer_level_pilot_v2/generation/dump_evidence_v3.js (= run_baseline_v2.js logic), wrapped as a module so
 * that the review-recheck experiments (09_review_recheck) use byte-identical lexical conditions and scoring.
 * Only the module wrapper and the exports were added; no function body was changed.
 */
const fs = require('fs');
const path = require('path');
const BASE = '<EVIDENCE_PACKAGE_ROOT>';
const SNAP = path.join(BASE, '01_frozen_snapshot');
const KG_V1 = path.join(SNAP, 'kg_graph.json');
const KG_V11 = path.join(BASE, '07_graph_repair', 'kg_graph_v1_1.json');
const CORPUS_DIR = path.join(SNAP, 'knowledge_corpus');
const BANK_PATH = path.join(BASE, '02_question_bank', 'question_bank_AB.json');
/* ---------------- text utilities (port of retrieval.py) ---------------- */
function ngrams(text, n = 2) { const t = (text || '').toLowerCase().replace(/\s+/g, ''); if (t.length < n) return t ? [t] : []; const out = []; for (let i = 0; i <= t.length - n; i++) out.push(t.slice(i, i + n)); return out; }
function latinTokens(text) { return ((text || '').toLowerCase().match(/[a-z0-9][a-z0-9\-\.\/]*/g)) || []; }
function terms(query) { const q = (query || '').toLowerCase(); const out = [...latinTokens(q)]; for (const run of q.match(/[一-鿿]+/g) || []) { if (run.length >= 2) out.push(...ngrams(run, 2)); else out.push(run); if (run.length <= 6) out.push(run); } return out.filter(Boolean); }
const NAME_FIELDS = ['sb:name','sb:drawingName','sb:systemName','sb:processName','sb:specName','sb:methodName','sb:roundName','sb:structureName','sb:projectName','sb:segmentNo'];
const TEXT_FIELDS = NAME_FIELDS.concat(['sb:description','sb:category','sb:note','sb:appliedTo','sb:grade','sb:dimension','sb:material','sb:steelGrade','sb:drawingNo','sb:specId','sb:constructionMethod','sb:dangerousReason','sb:girderSection']);
function buildNodeText(props) { const parts = []; for (const f of TEXT_FIELDS) { const v = props[f]; if (typeof v === 'string' || typeof v === 'number') parts.push(String(v)); else if (Array.isArray(v)) for (const x of v) if (typeof x === 'string' || typeof x === 'number') parts.push(String(x)); } return parts.join(' '); }
function flattenProps(props, out) { for (const [k, v] of Object.entries(props)) { if (k === '@id' || k === '@type') continue; if (v === null || v === undefined) continue; if (typeof v === 'object' && !Array.isArray(v)) { flattenProps(v, out); continue; } if (Array.isArray(v)) { for (const x of v) { if (typeof x === 'object' && x !== null) flattenProps(x, out); else out.push(`${k}=${x}`); } } else out.push(`${k}=${v}`); } }

/* ---------------- graph retriever factory (port of graph_engine.py) ---------------- */
function makeGraph(kgPath) {
  const kg = JSON.parse(fs.readFileSync(kgPath, 'utf8'));
  const nodesById = new Map();
  for (const n of kg.nodes) nodesById.set(n.id, { ...n, text: buildNodeText(n.props || {}) });
  const adj = new Map();
  for (const e of kg.edges) { if (!adj.has(e.source)) adj.set(e.source, []); if (!adj.has(e.target)) adj.set(e.target, []); adj.get(e.source).push({ other: e.target, label_en: e.label_en }); adj.get(e.target).push({ other: e.source, label_en: e.label_en }); }
  const nodeGrams = new Map(), nameGrams = new Map();
  for (const [nid, node] of nodesById) { const grams = new Map(); for (const g of ngrams(node.text, 2)) grams.set(g, (grams.get(g) || 0) + 1); for (const w of latinTokens(node.text)) grams.set(w, (grams.get(w) || 0) + 1); nodeGrams.set(nid, grams); nameGrams.set(nid, new Set([...ngrams(node.name, 2), ...latinTokens(node.name)])); }
  function searchEntities(query, topK = 6) {
    const tset = new Set(terms(query)); const scored = [];
    for (const [nid] of nodesById) { const grams = nodeGrams.get(nid), ng = nameGrams.get(nid); let score = 0; for (const t of tset) { if (grams.has(t)) { score += grams.get(t); if (ng.has(t)) score += 3.0; } } if (score > 0) { let overlap = 0; for (const g of ng) if (tset.has(g)) overlap++; score += 2.0 * (overlap / (ng.size + 1)); scored.push([score, nid]); } }
    scored.sort((a, b) => b[0] - a[0] || (a[1] < b[1] ? -1 : 1));
    return scored.slice(0, topK).map(([score, nid]) => ({ id: nid, score: Math.round(score * 100) / 100 }));
  }
  function cdcRetrieve(query, topK = 6, expand = true) {
    const seeds = searchEntities(query, topK); const pkg = new Map(); const relLabels = new Set();
    for (const s of seeds) pkg.set(s.id, nodesById.get(s.id));
    if (expand) for (const s of seeds) for (const nb of adj.get(s.id) || []) { relLabels.add(nb.label_en); if (!pkg.has(nb.other)) pkg.set(nb.other, nodesById.get(nb.other)); }
    const lines = []; for (const n of pkg.values()) { const flat = []; flattenProps(n.props || {}, flat); lines.push(`[${n.type}] ${n.name} (${n.id}) :: ${flat.join(' | ')}`); }
    if (relLabels.size) lines.push('relations: ' + [...relLabels].join(', '));
    return { seeds, packageIds: [...pkg.keys()], evidenceText: lines.join('\n') };
  }
  return { kg, nodesById, cdcRetrieve };
}
/* ---------------- document chunks ---------------- */
function chunkDocument(fileName, content) { const lines = content.split(/\r?\n/); const chunks = []; let buf = [], heading = '(preamble)'; const flush = () => { const text = buf.join('\n').trim(); if (text) { for (let i = 0; i < text.length; i += 1400) { chunks.push({ doc: fileName, heading, text: text.slice(i, i + 1600) }); if (i + 1600 >= text.length) break; } } buf = []; }; for (const ln of lines) { if (/^#{2,3}\s/.test(ln)) { flush(); heading = ln.replace(/^#+\s*/, ''); } buf.push(ln); if (buf.join('\n').length > 900 && /^\s*$/.test(ln)) flush(); } flush(); return chunks; }
const corpusFiles = fs.readdirSync(CORPUS_DIR).filter(f => f.endsWith('.md')).sort();
const chunks = []; for (const f of corpusFiles) chunks.push(...chunkDocument(f, fs.readFileSync(path.join(CORPUS_DIR, f), 'utf8')));
chunks.forEach((c, i) => { c.id = `${c.doc}#${i}`; });
function chunkTerms(text) { const out = []; out.push(...latinTokens(text)); for (const run of text.toLowerCase().match(/[一-鿿]+/g) || []) { if (run.length >= 2) out.push(...ngrams(run, 2)); else out.push(run); } return out; }
const df = new Map();
const chunkVecs = chunks.map(c => { const tf = new Map(); for (const t of chunkTerms(c.text)) tf.set(t, (tf.get(t) || 0) + 1); for (const t of tf.keys()) df.set(t, (df.get(t) || 0) + 1); return tf; });
const N = chunks.length;
const idf = t => Math.log(1 + N / (df.get(t) || 1));
const chunkNorm = chunkVecs.map(tf => { let s = 0; for (const [t, f] of tf) s += (f * idf(t)) ** 2; return Math.sqrt(s) || 1; });
const chunkLen = chunkVecs.map(tf => { let s = 0; for (const f of tf.values()) s += f; return s; });
const avgLen = chunkLen.reduce((a, b) => a + b, 0) / N;
function ragRetrieve(query, topK) {
  const qtf = new Map(); for (const t of terms(query)) qtf.set(t, (qtf.get(t) || 0) + 1);
  let qn = 0; for (const [t, f] of qtf) qn += (f * idf(t)) ** 2; qn = Math.sqrt(qn) || 1;
  const scored = chunks.map((c, i) => { let dot = 0; for (const [t, f] of qtf) { const cf = chunkVecs[i].get(t); if (cf) dot += f * idf(t) * cf * idf(t); } return [dot / (qn * chunkNorm[i]), i]; }).filter(([s]) => s > 0).sort((a, b) => b[0] - a[0]);
  const top = scored.slice(0, topK);
  return { chunks: top.map(([s, i]) => ({ id: chunks[i].id, score: Math.round(s * 1000) / 1000 })), evidenceText: top.map(([, i]) => `【${chunks[i].doc} / ${chunks[i].heading}】\n${chunks[i].text}`).join('\n\n') };
}
/* BM25 (Robertson/Okapi), k1 = 1.2, b = 0.75, same terms and chunks */
const K1 = 1.2, B = 0.75;
const bm25idf = t => Math.log(1 + (N - (df.get(t) || 0) + 0.5) / ((df.get(t) || 0) + 0.5));
function bm25Retrieve(query, topK) {
  const qterms = [...new Set(terms(query))];
  const scored = chunks.map((c, i) => { let s = 0; for (const t of qterms) { const f = chunkVecs[i].get(t); if (!f) continue; s += bm25idf(t) * (f * (K1 + 1)) / (f + K1 * (1 - B + B * chunkLen[i] / avgLen)); } return [s, i]; }).filter(([s]) => s > 0).sort((a, b) => b[0] - a[0]);
  const top = scored.slice(0, topK);
  return { chunks: top.map(([s, i]) => ({ id: chunks[i].id, score: Math.round(s * 1000) / 1000 })), evidenceText: top.map(([, i]) => `【${chunks[i].doc} / ${chunks[i].heading}】\n${chunks[i].text}`).join('\n\n') };
}

/* ---------------- scoring (verbatim from run_baseline.js) ---------------- */
function normalize(s) { let t = (s || '').toLowerCase(); t = t.replace(/[！-～]/g, ch => String.fromCharCode(ch.charCodeAt(0) - 0xfee0)); t = t.replace(/(\d),(?=\d{3}\b)/g, '$1'); t = t.replace(/[～〜]/g, '~'); t = t.replace(/\s+/g, ' '); return t; }
const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
function tokenPresent(tok, text) { if (/^[\d.]+$/.test(tok)) return new RegExp(`(?<![\\d.])${esc(tok)}(?![\\d.])`).test(text); return text.includes(tok); }
function scoreAnswerable(q, text) { const matched = [], missing = []; for (const t of q.required_all || []) (tokenPresent(t, text) ? matched : missing).push(t); let anyHits = []; if (q.required_any && q.required_any.length) anyHits = q.required_any.filter(t => tokenPresent(t, text)); const anyOk = !q.required_any || anyHits.length >= (q.min_any || 1); return { hit: missing.length === 0 && anyOk, matched, missing, anyHits }; }
function basisPresent(pattern, text, pkgNodes, nodesById) {
  switch (pattern) {
    case 'arch_segment_record': return (pkgNodes || []).some(id => { const n = nodesById.get(id); return n && (n.type === 'StructuralComponent' || n.type === 'GirderSegment') && /(z(10|[1-9])|c[1-5])(?![0-9])/i.test(n.name + ' ' + n.id) && !/temppier/i.test(n.id); });
    case 'coordinate_triple': return /(实测|竣工).{0,20}坐标/.test(text) || /坐标[^。\n]{0,40}\d+\.\d+[^。\n]{0,20}\d+\.\d+/.test(text);
    case 'ndt_pass_rate': return /合格率.{0,10}\d/.test(text) || /\d{1,3}(\.\d+)?%.{0,6}合格/.test(text);
    case 'measured_oil_pressure': return /\d+(\.\d+)?\s*mpa/.test(text) || /油压.{0,15}\d/.test(text);
    case 'measured_deviation': return /(偏差|纠偏).{0,12}\d+(\.\d+)?\s*mm/.test(text);
    default: return false;
  }
}
function exposureCount(keywords, text) { let count = 0; for (const k of keywords || []) { const re = new RegExp(esc(k.toLowerCase()), 'g'); let m; while ((m = re.exec(text)) !== null) { const w = text.slice(Math.max(0, m.index - 40), m.index + k.length + 40); if (/\d/.test(w)) count++; } } return count; }


module.exports = { BASE, SNAP, KG_V1, KG_V11, CORPUS_DIR, BANK_PATH, ngrams, latinTokens, terms, NAME_FIELDS, TEXT_FIELDS, buildNodeText, flattenProps, makeGraph,
  chunkDocument, corpusFiles, chunks, chunkTerms, df, chunkVecs, N, idf, chunkNorm, chunkLen, avgLen, ragRetrieve, K1, B, bm25idf, bm25Retrieve,
  normalize, esc, tokenPresent, scoreAnswerable, basisPresent, exposureCount };