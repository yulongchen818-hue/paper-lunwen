# dense_rank.py — contemporary document-side baselines on the identical 1,321 chunk strings.
#   Dense:   BAAI/bge-m3 dense embeddings (CLS, L2-normalised), cosine ranking  [Chen et al. 2024]
#   Hybrid:  reciprocal rank fusion of the BM25 ranking (exported by export_for_dense.js) and the
#            dense ranking, k = 60                                                [Cormack et al. 2009]
#   Rerank:  BAAI/bge-reranker-v2-m3 cross-encoder over the top-50 hybrid candidates
# All settings are library / paper defaults fixed before the run; nothing is tuned on the bank.
# Usage: python dense_rank.py [--encode-only] [--reencode]   (models are read from <MODEL_DIR>, see download_meta.json)
import json, os, sys, time, platform
import numpy as np
import torch
import sentence_transformers
from sentence_transformers import SentenceTransformer, CrossEncoder

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, '..', 'results')
MODELS = r'<MODEL_DIR>'
RRF_K, RERANK_DEPTH, KEEP = 60, 50, 400
torch.manual_seed(0)
torch.use_deterministic_algorithms(True)

inp = json.load(open(os.path.join(RES, 'dense_inputs.json'), encoding='utf-8'))
texts = [c['s'] for c in inp['chunks']]
qs = inp['questions']

# Stage 1: dense encoding, cached in results/dense_embeddings.npz (rerun with --reencode to recompute)
CACHE = os.path.join(RES, 'dense_embeddings.npz')
if os.path.exists(CACHE) and '--reencode' not in sys.argv:
    z = np.load(CACHE); D, Q, t_enc = z['D'], z['Q'], float(z['t_enc'])
else:
    t0 = time.time()
    enc = SentenceTransformer(os.path.join(MODELS, 'bge-m3'), device='cpu')
    enc.max_seq_length = 1024  # longest chunk string is 973 characters, so nothing is truncated
    D = enc.encode(texts, batch_size=16, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
    Q = enc.encode([q['q'] for q in qs], batch_size=16, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
    t_enc = time.time() - t0
    np.savez(CACHE, D=D, Q=Q, t_enc=t_enc)
    print('encoded', D.shape, Q.shape, round(t_enc, 1), 's', flush=True)
if '--encode-only' in sys.argv: sys.exit(0)
dl = json.load(open(os.path.join(MODELS, 'download_meta.json'), encoding='utf-8'))
S = Q @ D.T

ce = CrossEncoder(os.path.join(MODELS, 'bge-reranker-v2-m3'), device='cpu', max_length=1024)
out = {}
t1 = time.time()
for qi, q in enumerate(qs):
    s = S[qi]
    dense_order = sorted(range(len(texts)), key=lambda i: (-float(s[i]), i))
    dense_rank = {i: r + 1 for r, i in enumerate(dense_order)}
    bm = inp['bm25'][q['id']]
    bm_rank = {c['i']: r + 1 for r, c in enumerate(bm)}
    rrf = {}
    for i in range(len(texts)):
        v = 1.0 / (RRF_K + dense_rank[i])
        if i in bm_rank: v += 1.0 / (RRF_K + bm_rank[i])
        rrf[i] = v
    hyb_order = sorted(rrf, key=lambda i: (-rrf[i], dense_rank[i]))
    cand = hyb_order[:RERANK_DEPTH]
    cs = ce.predict([(q['q'], texts[i]) for i in cand], batch_size=16, show_progress_bar=False)
    rr = sorted(zip(cand, [float(x) for x in cs]), key=lambda t: (-t[1], hyb_order.index(t[0])))
    out[q['id']] = {
        'dense': [[i, round(float(s[i]), 6)] for i in dense_order[:KEEP]],
        'hybrid': [[i, round(rrf[i], 8)] for i in hyb_order[:KEEP]],
        'rerank': [[i, round(v, 6)] for i, v in rr],
    }
t_rr = time.time() - t1
meta = {
    'generated': time.strftime('%Y-%m-%dT%H:%M:%S'),
    'dense_model': 'BAAI/bge-m3', 'dense_revision': dl['BAAI/bge-m3']['revision'],
    'reranker_model': 'BAAI/bge-reranker-v2-m3', 'reranker_revision': dl['BAAI/bge-reranker-v2-m3']['revision'],
    'settings': {'pooling': 'CLS (model default)', 'normalize': True, 'max_seq_length': 1024, 'rrf_k': RRF_K, 'rerank_depth': RERANK_DEPTH,
                 'reranker_max_length': 1024, 'device': 'cpu', 'dtype': 'float32'},
    'versions': {'python': platform.python_version(), 'torch': torch.__version__, 'sentence_transformers': sentence_transformers.__version__, 'numpy': np.__version__},
    'seconds': {'encode': round(t_enc, 1), 'fuse_and_rerank': round(t_rr, 1)},
    'chunks': len(texts), 'questions': len(qs),
}
json.dump({'meta': meta, 'rankings': out}, open(os.path.join(RES, 'dense_rankings.json'), 'w', encoding='utf-8'), ensure_ascii=False)
print(json.dumps(meta, ensure_ascii=False, indent=1))
