# dense_repro_check.py — re-encodes the 1,321 chunks and 23 questions with BGE-M3 in a fresh process and compares
# against the cached embeddings used for the reported rankings (results/dense_embeddings.npz).
# Reports the maximum absolute embedding difference and whether every per-question top-12/top-k dense ranking is identical.
import json, os, sys
import numpy as np, torch
from sentence_transformers import SentenceTransformer
HERE = os.path.dirname(os.path.abspath(__file__)); RES = os.path.join(HERE, '..', 'results')
torch.manual_seed(0); torch.use_deterministic_algorithms(True)
inp = json.load(open(os.path.join(RES, 'dense_inputs.json'), encoding='utf-8'))
texts = [c['s'] for c in inp['chunks']]; qs = [q['q'] for q in inp['questions']]
z = np.load(os.path.join(RES, 'dense_embeddings.npz'))
enc = SentenceTransformer(r'<MODEL_DIR>\bge-m3', device='cpu'); enc.max_seq_length = 1024
D = enc.encode(texts, batch_size=16, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
Q = enc.encode(qs, batch_size=16, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
def order(Qm, Dm):
    S = Qm @ Dm.T
    return [sorted(range(Dm.shape[0]), key=lambda i: (-float(S[q, i]), i)) for q in range(Qm.shape[0])]
o1, o2 = order(z['Q'], z['D']), order(Q, D)
same = {k: all(a[:k] == b[:k] for a, b in zip(o1, o2)) for k in (6, 12, 50, 100, 200)}
rep = {'max_abs_diff_D': float(np.abs(D - z['D']).max()), 'max_abs_diff_Q': float(np.abs(Q - z['Q']).max()),
       'identical_topk_rankings': same, 'bitwise_identical': bool(np.array_equal(D, z['D']) and np.array_equal(Q, z['Q']))}
json.dump(rep, open(os.path.join(RES, 'dense_repro_check.json'), 'w'), indent=1)
print(json.dumps(rep))
