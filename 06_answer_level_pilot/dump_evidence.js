/*
 * Retrieval-stage baseline comparison — the case bridge CDC evidence assembly
 * =========================================================================
 * Conditions
 *   CDC-full  : faithful JS port of the deployed deterministic retriever
 *               (01_交付物1_知识图谱服务/retrieval.py + graph_engine.py):
 *               character-bigram/latin-token scoring with name bonus (+3 per
 *               name-hit term, +2*overlap/(|name_grams|+1)), top-6 seed
 *               entities, 1-hop expansion over the union of in/out edges
 *               (the deployed retrieve() default). Evidence = full property
 *               records of every package entity + relation labels.
 *   CDC-seeds : same scoring, evidence restricted to the top-6 seed entities.
 *   RAG-6/12  : sparse vector-space document retrieval over the deployed
 *               knowledge corpus (backend/knowledge/桥梁建筑/*.md, 14 files):
 *               heading-based chunking, character-bigram + latin-token
 *               TF-IDF, cosine similarity, top-6 / top-12 chunks.
 * Scoring: mechanical only, against the preregistered key in
 *   ../02_question_bank/question_bank_AB.json  (frozen before this run).
 * No language model is invoked anywhere in this script.
 */
'use strict';
const fs = require('fs');
const path = require('path');

const HERE = __dirname;
const SNAP = '<EVIDENCE_PACKAGE_ROOT>\\01_frozen_snapshot';
const KG_PATH = path.join(SNAP, 'kg_graph.json');
const CORPUS_DIR = path.join(SNAP, 'knowledge_corpus');
const BANK_PATH = '<EVIDENCE_PACKAGE_ROOT>\\02_question_bank\\question_bank_AB.json';
const OUT_DIR = path.join(HERE, 'results_tmp');
const EVID_DIR = path.join(HERE, 'evidence'); fs.mkdirSync(EVID_DIR, { recursive: true }); const EVID = [];
fs.mkdirSync(OUT_DIR, { recursive: true });

/* ---------------- text utilities (port of retrieval.py) ---------------- */
function ngrams(text, n = 2) {
  const t = (text || '').toLowerCase().replace(/\s+/g, '');
  if (t.length < n) return t ? [t] : [];
  const out = [];
  for (let i = 0; i <= t.length - n; i++) out.push(t.slice(i, i + n));
  return out;
}
function latinTokens(text) {
  return ((text || '').toLowerCase().match(/[a-z0-9][a-z0-9\-\.\/]*/g)) || [];
}
function terms(query) {
  const q = (query || '').toLowerCase();
  const out = [...latinTokens(q)];
  for (const run of q.match(/[一-鿿]+/g) || []) {
    if (run.length >= 2) out.push(...ngrams(run, 2)); else out.push(run);
    if (run.length <= 6) out.push(run);
  }
  return out.filter(Boolean);
}

/* ---------------- KG engine (port of graph_engine.py Node.text) --------- */
const NAME_FIELDS = ['sb:name','sb:drawingName','sb:systemName','sb:processName','sb:specName','sb:methodName','sb:roundName','sb:structureName','sb:projectName','sb:segmentNo'];
const TEXT_FIELDS = NAME_FIELDS.concat(['sb:description','sb:category','sb:note','sb:appliedTo','sb:grade','sb:dimension','sb:material','sb:steelGrade','sb:drawingNo','sb:specId','sb:constructionMethod','sb:dangerousReason','sb:girderSection']);

function buildNodeText(props) {
  const parts = [];
  for (const f of TEXT_FIELDS) {
    const v = props[f];
    if (typeof v === 'string' || typeof v === 'number') parts.push(String(v));
    else if (Array.isArray(v)) for (const x of v) if (typeof x === 'string' || typeof x === 'number') parts.push(String(x));
  }
  return parts.join(' ');
}
function flattenProps(props, out) {
  for (const [k, v] of Object.entries(props)) {
    if (k === '@id' || k === '@type') continue;
    if (v === null || v === undefined) continue;
    if (typeof v === 'object' && !Array.isArray(v)) { flattenProps(v, out); continue; }
    if (Array.isArray(v)) {
      for (const x of v) {
        if (typeof x === 'object' && x !== null) flattenProps(x, out);
        else out.push(`${k}=${x}`);
      }
    } else out.push(`${k}=${v}`);
  }
}

const kg = JSON.parse(fs.readFileSync(KG_PATH, 'utf8'));
const nodesById = new Map();
for (const n of kg.nodes) {
  const text = buildNodeText(n.props || {});
  nodesById.set(n.id, { ...n, text });
}
const adj = new Map(); // id -> [{other, label, label_en, dir}]
for (const e of kg.edges) {
  if (!adj.has(e.source)) adj.set(e.source, []);
  if (!adj.has(e.target)) adj.set(e.target, []);
  adj.get(e.source).push({ other: e.target, label: e.label, label_en: e.label_en, dir: 'out' });
  adj.get(e.target).push({ other: e.source, label: e.label, label_en: e.label_en, dir: 'in' });
}

/* per-node gram index, exactly as _build_index() */
const nodeGrams = new Map(), nameGrams = new Map();
for (const [nid, node] of nodesById) {
  const grams = new Map();
  for (const g of ngrams(node.text, 2)) grams.set(g, (grams.get(g) || 0) + 1);
  for (const w of latinTokens(node.text)) grams.set(w, (grams.get(w) || 0) + 1);
  nodeGrams.set(nid, grams);
  nameGrams.set(nid, new Set([...ngrams(node.name, 2), ...latinTokens(node.name)]));
}

function searchEntities(query, topK = 6) {
  const tset = new Set(terms(query));
  const scored = [];
  for (const [nid] of nodesById) {
    const grams = nodeGrams.get(nid), ng = nameGrams.get(nid);
    let score = 0;
    for (const t of tset) {
      if (grams.has(t)) {
        score += grams.get(t);
        if (ng.has(t)) score += 3.0;
      }
    }
    if (score > 0) {
      let overlap = 0;
      for (const g of ng) if (tset.has(g)) overlap++;
      score += 2.0 * (overlap / (ng.size + 1));
      scored.push([score, nid]);
    }
  }
  scored.sort((a, b) => b[0] - a[0] || (a[1] < b[1] ? -1 : 1));
  return scored.slice(0, topK).map(([score, nid]) => ({ id: nid, score: Math.round(score * 100) / 100 }));
}

function cdcRetrieve(query, topK = 6, expand = true) {
  const seeds = searchEntities(query, topK);
  const pkg = new Map();
  const relLabels = new Set();
  for (const s of seeds) pkg.set(s.id, nodesById.get(s.id));
  if (expand) {
    for (const s of seeds) {
      for (const nb of adj.get(s.id) || []) {
        relLabels.add(nb.label_en);
        if (!pkg.has(nb.other)) pkg.set(nb.other, nodesById.get(nb.other));
      }
    }
  }
  const lines = [];
  for (const n of pkg.values()) {
    const flat = [];
    flattenProps(n.props || {}, flat);
    lines.push(`[${n.type}] ${n.name} (${n.id}) :: ${flat.join(' | ')}`);
  }
  if (relLabels.size) lines.push('relations: ' + [...relLabels].join(', '));
  return { seeds, packageIds: [...pkg.keys()], evidenceText: lines.join('\n') };
}

/* ---------------- document-chunk TF-IDF retriever ----------------------- */
function chunkDocument(fileName, content) {
  const lines = content.split(/\r?\n/);
  const chunks = [];
  let buf = [], heading = '(preamble)';
  const flush = () => {
    const text = buf.join('\n').trim();
    if (text) {
      // hard-split overlong chunks
      for (let i = 0; i < text.length; i += 1400) {
        chunks.push({ doc: fileName, heading, text: text.slice(i, i + 1600) });
        if (i + 1600 >= text.length) break;
      }
    }
    buf = [];
  };
  for (const ln of lines) {
    if (/^#{2,3}\s/.test(ln)) { flush(); heading = ln.replace(/^#+\s*/, ''); }
    buf.push(ln);
    if (buf.join('\n').length > 900 && /^\s*$/.test(ln)) flush();
  }
  flush();
  return chunks;
}

const corpusFiles = fs.readdirSync(CORPUS_DIR).filter(f => f.endsWith('.md')).sort();
const chunks = [];
for (const f of corpusFiles) chunks.push(...chunkDocument(f, fs.readFileSync(path.join(CORPUS_DIR, f), 'utf8')));
chunks.forEach((c, i) => { c.id = `${c.doc}#${i}`; });

function chunkTerms(text) {
  const out = [];
  out.push(...latinTokens(text));
  for (const run of text.toLowerCase().match(/[一-鿿]+/g) || []) {
    if (run.length >= 2) out.push(...ngrams(run, 2)); else out.push(run);
  }
  return out;
}
const df = new Map();
const chunkVecs = chunks.map(c => {
  const tf = new Map();
  for (const t of chunkTerms(c.text)) tf.set(t, (tf.get(t) || 0) + 1);
  for (const t of tf.keys()) df.set(t, (df.get(t) || 0) + 1);
  return tf;
});
const N = chunks.length;
const idf = t => Math.log(1 + N / (df.get(t) || 1));
const chunkNorm = chunkVecs.map(tf => {
  let s = 0;
  for (const [t, f] of tf) s += (f * idf(t)) ** 2;
  return Math.sqrt(s) || 1;
});

function ragRetrieve(query, topK) {
  const qtf = new Map();
  for (const t of terms(query)) qtf.set(t, (qtf.get(t) || 0) + 1);
  let qn = 0;
  for (const [t, f] of qtf) qn += (f * idf(t)) ** 2;
  qn = Math.sqrt(qn) || 1;
  const scored = chunks.map((c, i) => {
    let dot = 0;
    for (const [t, f] of qtf) {
      const cf = chunkVecs[i].get(t);
      if (cf) dot += f * idf(t) * cf * idf(t);
    }
    return [dot / (qn * chunkNorm[i]), i];
  }).filter(([s]) => s > 0).sort((a, b) => b[0] - a[0]);
  const top = scored.slice(0, topK);
  return {
    chunks: top.map(([s, i]) => ({ id: chunks[i].id, doc: chunks[i].doc, heading: chunks[i].heading, score: Math.round(s * 1000) / 1000 })),
    evidenceText: top.map(([, i]) => `【${chunks[i].doc} / ${chunks[i].heading}】\n${chunks[i].text}`).join('\n\n')
  };
}

/* ---------------- normalization + mechanical scoring -------------------- */
function normalize(s) {
  let t = (s || '').toLowerCase();
  t = t.replace(/[！-～]/g, ch => String.fromCharCode(ch.charCodeAt(0) - 0xfee0)); // full->half width
  t = t.replace(/(\d),(?=\d{3}\b)/g, '$1');   // thousands commas
  t = t.replace(/[～〜]/g, '~');
  t = t.replace(/\s+/g, ' ');
  return t;
}
const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
function tokenPresent(tok, text) {
  if (/^[\d.]+$/.test(tok)) {
    return new RegExp(`(?<![\\d.])${esc(tok)}(?![\\d.])`).test(text);
  }
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
function basisPresent(pattern, text, pkgNodes) {
  switch (pattern) {
    case 'arch_segment_record':
      return (pkgNodes || []).some(id => {
        const n = nodesById.get(id);
        return n && (n.type === 'StructuralComponent' || n.type === 'GirderSegment') && /(z(10|[1-9])|c[1-5])(?![0-9])/i.test(n.name + ' ' + n.id) && !/temppier/i.test(n.id);
      });
    case 'coordinate_triple':
      return /(实测|竣工).{0,20}坐标/.test(text) || /坐标[^。\n]{0,40}\d+\.\d+[^。\n]{0,20}\d+\.\d+/.test(text);
    case 'ndt_pass_rate':
      return /合格率.{0,10}\d/.test(text) || /\d{1,3}(\.\d+)?%.{0,6}合格/.test(text);
    case 'measured_oil_pressure':
      return /\d+(\.\d+)?\s*mpa/.test(text) || /油压.{0,15}\d/.test(text);
    case 'measured_deviation':
      return /(偏差|纠偏).{0,12}\d+(\.\d+)?\s*mm/.test(text);
    default: return false;
  }
}
function exposureCount(keywords, text) {
  let count = 0; const windows = [];
  for (const k of keywords || []) {
    const re = new RegExp(esc(k.toLowerCase()), 'g');
    let m;
    while ((m = re.exec(text)) !== null) {
      const w = text.slice(Math.max(0, m.index - 40), m.index + k.length + 40);
      if (/\d/.test(w)) { count++; windows.push(`${k} :: …${w.replace(/\n/g, ' ')}…`); }
    }
  }
  return { count, windows: windows.slice(0, 6) };
}

/* ---------------- run ---------------------------------------------------- */
const bank = JSON.parse(fs.readFileSync(BANK_PATH, 'utf8'));
const CONDITIONS = [
  { name: 'CDC-full',  run: q => { const r = cdcRetrieve(q, 6, true);  return { evidence: r.evidenceText, items: r.packageIds.length, detail: { seeds: r.seeds, packageIds: r.packageIds } }; } },
  { name: 'CDC-seeds', run: q => { const r = cdcRetrieve(q, 6, false); return { evidence: r.evidenceText, items: r.packageIds.length, detail: { seeds: r.seeds, packageIds: r.packageIds } }; } },
  { name: 'RAG-6',     run: q => { const r = ragRetrieve(q, 6);  return { evidence: r.evidenceText, items: r.chunks.length, detail: { chunks: r.chunks } }; } },
  { name: 'RAG-12',    run: q => { const r = ragRetrieve(q, 12); return { evidence: r.evidenceText, items: r.chunks.length, detail: { chunks: r.chunks } }; } },
];

const rows = [], audit = [];
for (const q of bank.questions) {
  if (q.excluded) { rows.push({ id: q.id, type: q.type, note: 'excluded from mechanical scoring (decision question)' }); continue; }
  for (const cond of CONDITIONS) {
    const r = cond.run(q.q);
    fs.writeFileSync(path.join(EVID_DIR, q.id + '__' + cond.name + '.txt'), r.evidence, 'utf8');
    EVID.push({ id: q.id, type: q.type, condition: cond.name, question: q.q, chars: r.evidence.length, items: r.items, evidence: r.evidence });
    const text = normalize(r.evidence);
    const row = { id: q.id, type: q.type, condition: cond.name, package_items: r.items, package_chars: r.evidence.length };
    if (q.type === 'answerable') {
      Object.assign(row, scoreAnswerable(q, text));
      audit.push(`=== ${q.id} / ${cond.name} :: hit=${row.hit} matched=[${row.matched}] missing=[${row.missing}] any=[${row.anyHits}]`);
      for (const t of [...(q.required_all || []), ...(q.required_any || [])]) {
        if (tokenPresent(t, text)) {
          const i = text.indexOf(t.toLowerCase());
          audit.push(`    "${t}" @ …${text.slice(Math.max(0, i - 45), i + t.length + 45)}…`);
        }
      }
    } else {
      row.basis_present = basisPresent(q.request_pattern, text, r.detail.packageIds);
      const ex = exposureCount(q.exposure_keywords, text);
      row.exposure_count = ex.count;
      audit.push(`=== ${q.id} / ${cond.name} :: basis_present=${row.basis_present} exposure=${ex.count}`);
      for (const w of ex.windows) audit.push('    ' + w);
    }
    row.retrieval_detail = r.detail;
    rows.push(row);
  }
}

/* ---------------- summarize --------------------------------------------- */
function summarize() {
  const conds = CONDITIONS.map(c => c.name);
  const lines = [];
  lines.push('# Mechanical retrieval-stage comparison — summary');
  lines.push('');
  lines.push(`Corpus: ${corpusFiles.length} documents -> ${N} chunks. KG: ${kg.nodes.length} entities / ${kg.edges.length} edges.`);
  lines.push('');
  lines.push('## Answerable questions (18): evidence hit rate');
  lines.push('');
  lines.push('| Condition | Hits/18 | Rate | mean pkg chars | mean pkg items |');
  lines.push('|---|---|---|---|---|');
  const summary = {};
  for (const c of conds) {
    const rs = rows.filter(r => r.condition === c && r.type === 'answerable');
    const hits = rs.filter(r => r.hit).length;
    const mc = Math.round(rs.reduce((s, r) => s + r.package_chars, 0) / rs.length);
    const mi = Math.round(rs.reduce((s, r) => s + r.package_items, 0) / rs.length * 10) / 10;
    lines.push(`| ${c} | ${hits}/18 | ${(hits / 18 * 100).toFixed(1)}% | ${mc} | ${mi} |`);
    summary[c] = { hits, rate: hits / 18, mean_chars: mc, mean_items: mi };
  }
  lines.push('');
  lines.push('## Per-question hits (answerable)');
  lines.push('');
  lines.push('| Q | ' + conds.join(' | ') + ' |');
  lines.push('|---|' + conds.map(() => '---').join('|') + '|');
  for (const q of bank.questions.filter(x => x.type === 'answerable')) {
    const cells = conds.map(c => { const r = rows.find(x => x.id === q.id && x.condition === c); return r.hit ? 'HIT' : 'miss'; });
    lines.push(`| ${q.id} | ${cells.join(' | ')} |`);
  }
  lines.push('');
  lines.push('## Boundary questions (5 scorable): request-value basis and distractor exposure');
  lines.push('');
  lines.push('| Q | ' + conds.map(c => `${c} basis / exposure`).join(' | ') + ' |');
  lines.push('|---|' + conds.map(() => '---').join('|') + '|');
  for (const q of bank.questions.filter(x => x.type === 'boundary')) {
    const cells = conds.map(c => { const r = rows.find(x => x.id === q.id && x.condition === c); return `${r.basis_present ? 'PRESENT' : 'absent'} / ${r.exposure_count}`; });
    lines.push(`| ${q.id} | ${cells.join(' | ')} |`);
  }
  const bSummary = {};
  for (const c of conds) {
    const rs = rows.filter(r => r.condition === c && r.type === 'boundary');
    bSummary[c] = { basis_absent: rs.filter(r => !r.basis_present).length, of: rs.length, total_exposure: rs.reduce((s, r) => s + r.exposure_count, 0) };
  }
  lines.push('');
  lines.push('| Condition | basis absent (correct) | total exposure windows |');
  lines.push('|---|---|---|');
  for (const c of conds) lines.push(`| ${c} | ${bSummary[c].basis_absent}/${bSummary[c].of} | ${bSummary[c].total_exposure} |`);
  return { md: lines.join('\n'), summary, bSummary };
}

const { md, summary, bSummary } = summarize();
fs.writeFileSync(path.join(OUT_DIR, 'results_full.json'), JSON.stringify({ meta: { generated_by: 'run_baseline.js', kg: path.basename(KG_PATH), corpus_files: corpusFiles, chunks: N, conditions: CONDITIONS.map(c => c.name) }, summary_answerable: summary, summary_boundary: bSummary, rows }, null, 2), 'utf8');
fs.writeFileSync(path.join(OUT_DIR, 'summary.md'), md, 'utf8');
fs.writeFileSync(path.join(OUT_DIR, 'audit_contexts.txt'), audit.join('\n'), 'utf8');
console.log(md);

/* ---------------- pilot inputs (added for the answer-level pilot) -------- */
const pilot = {
  meta: { source: 'dump_evidence.js = run_baseline.js + evidence dump; retrieval logic unchanged', generated: new Date().toISOString(),
          conditions: ['CDC-full', 'CDC-seeds', 'RAG-12'], note: 'B12 excluded (decision question, not mechanically scorable)' },
  questions: bank.questions.filter(q => !q.excluded).map(q => ({ id: q.id, type: q.type, q: q.q })),
  evidence: EVID.filter(e => ['CDC-full', 'CDC-seeds', 'RAG-12'].includes(e.condition)).map(e => ({ id: e.id, condition: e.condition, chars: e.chars, items: e.items, evidence: e.evidence }))
};
fs.writeFileSync(path.join(HERE, 'pilot_inputs.json'), JSON.stringify(pilot, null, 1), 'utf8');
console.log('pilot_inputs.json written: ' + pilot.evidence.length + ' evidence packages for ' + pilot.questions.length + ' questions');