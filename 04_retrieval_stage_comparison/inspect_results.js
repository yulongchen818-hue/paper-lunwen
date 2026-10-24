'use strict';
const path = require('path');
const r = require(path.join(__dirname, 'results', 'results_full.json'));
const kg = require(path.join(__dirname, '..', '01_frozen_snapshot', 'kg_graph.json'));
const byId = Object.fromEntries(kg.nodes.map(n => [n.id, n]));

const a10 = r.rows.find(x => x.id === 'A10' && x.condition === 'CDC-full');
const trig = a10.retrieval_detail.packageIds.filter(id => {
  const n = byId[id];
  return n && (n.type === 'StructuralComponent' || n.type === 'GirderSegment') && /(z(10|[1-9])|c[1-5])(?![0-9])/i.test(n.name + ' ' + n.id) && !/temppier/i.test(n.id);
});
console.log('A10 trigger nodes:');
for (const id of trig) console.log('  ', id, '|', byId[id].type, '|', byId[id].name, '|', JSON.stringify(byId[id].props).slice(0, 300));

for (const c of ['CDC-full', 'RAG-6', 'RAG-12']) {
  const b02 = r.rows.find(x => x.id === 'B02' && x.condition === c);
  console.log('B02', c, 'missing:', b02.missing, 'anyHits:', b02.anyHits);
}
const b02c = r.rows.find(x => x.id === 'B02' && x.condition === 'CDC-full');
console.log('B02 CDC seeds:', b02c.retrieval_detail.seeds.map(s => s.id + ':' + s.score));

const segs = kg.nodes.filter(n => n.type === 'GirderSegment');
console.log('GirderSegment[0] props:', JSON.stringify(segs[0].props));

const a01 = r.rows.find(x => x.id === 'A01' && x.condition === 'RAG-6');
console.log('A01 RAG-6 chunks:'); for (const c of a01.retrieval_detail.chunks) console.log('  ', c.doc, '/', c.heading, ':', c.score);

const a05 = r.rows.find(x => x.id === 'A05' && x.condition === 'CDC-full');
console.log('A05 CDC seeds:', a05.retrieval_detail.seeds.map(s => s.id));

const b02r = r.rows.find(x => x.id === 'B02' && x.condition === 'RAG-12');
console.log('B02 RAG-12 chunks:'); for (const c of b02r.retrieval_detail.chunks) console.log('  ', c.doc, '/', c.heading, ':', c.score);
