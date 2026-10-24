// export_for_dense.js — writes the exact chunk strings, the questions and the BM25 rankings used by
// the document-side conditions, so that the dense / hybrid / rerank stage (dense_rank.py) operates on
// byte-identical inputs. Usage: node export_for_dense.js
const fs = require('fs');
const path = require('path');
const L = require('./lib_retrieval_v2.js');
const OUT = path.join(__dirname, '..', 'results', 'dense_inputs.json');
const bank = JSON.parse(fs.readFileSync(L.BANK_PATH, 'utf8'));
const Qs = bank.questions.filter(q => !q.excluded);
// evidence string of a chunk exactly as it appears in a document-side package
const chunkString = c => `【${c.doc} / ${c.heading}】\n${c.text}`;
const bm25 = {};
for (const q of Qs) bm25[q.id] = L.bm25Retrieve(q.q, L.N).chunks.map(c => ({ i: L.chunks.findIndex(x => x.id === c.id), s: c.score }));
const out = {
  meta: { generated: new Date().toISOString(), N: L.N, files: L.corpusFiles.length, avgLen: L.avgLen, bm25: { k1: L.K1, b: L.B } },
  chunks: L.chunks.map((c, i) => ({ i, id: c.id, s: chunkString(c) })),
  questions: Qs.map(q => ({ id: q.id, type: q.type, q: q.q })),
  bm25,
};
fs.mkdirSync(path.dirname(OUT), { recursive: true });
fs.writeFileSync(OUT, JSON.stringify(out), 'utf8');
const lens = out.chunks.map(c => c.s.length);
console.log(`chunks ${L.N}, questions ${Qs.length}, mean chunk-string chars ${Math.round(lens.reduce((a, b) => a + b, 0) / lens.length)}, max ${Math.max(...lens)}, total ${lens.reduce((a, b) => a + b, 0)}`);
console.log('BM25 candidates per question: ' + Qs.map(q => q.id + ':' + bm25[q.id].length).join(' '));
