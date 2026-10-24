# audit_graph.py — the graph-quality audit of Table 4 as a stand-alone script.
# Computes, for each graph version: entity/edge counts, referential integrity (string values beginning
# with "sb:" in entity properties, @id/@type excluded, resolved against instantiated identifiers),
# dangling references by class.property, relation counts, declared vs realized relation types, untyped
# fallback edges (relatedTo), domain/range conformance of depicts and involvesSegment, the edge profile of
# PushRound, and stage-linkage counts. Asserts that v1 and v1.1 reproduce 07_graph_repair/audit_v1_vs_v1_1.json.
# Usage: python audit_graph.py
import json, os
from collections import Counter, OrderedDict
HERE = os.path.dirname(os.path.abspath(__file__))
BASE = r'<EVIDENCE_PACKAGE_ROOT>'
GRAPHS = OrderedDict([('v1', os.path.join(BASE, '01_frozen_snapshot', 'kg_graph.json')),
                      ('v1_1', os.path.join(BASE, '07_graph_repair', 'kg_graph_v1_1.json')),
                      ('v1_2', os.path.join(HERE, '..', 'graph', 'kg_graph_v1_2.json'))])
DECLARED = ['hasComponent', 'belongsTo', 'depicts', 'refersToDrawing', 'appliesTo', 'hasStep', 'usesMethod', 'involvesSegment',
            'launchOrder', 'partOfProject', 'usesMaterial', 'relatedTo']
DECLARED_V12 = DECLARED + ['landsOn']

def refs_of(val, out, cls, key):
    if isinstance(val, list):
        for x in val: refs_of(x, out, cls, key)
    elif isinstance(val, dict):
        for k, v in val.items(): refs_of(v, out, cls, k)
    elif isinstance(val, str) and val.startswith('sb:'):
        out.append((cls, key, val))

def audit(path, declared):
    g = json.load(open(path, encoding='utf-8'))
    nodes = {n['id']: n for n in g['nodes']}; E = g['edges']
    refs = []
    for n in g['nodes']:
        for k, v in n['props'].items():
            if k in ('@id', '@type'): continue
            refs_of(v, refs, n['type'], k)
    dang = [r for r in refs if r[2] not in nodes]
    rc = Counter(e['label_en'] for e in E)
    typ = lambda i: nodes[i]['type']
    pr = Counter()
    for e in E:
        if typ(e['source']) == 'PushRound': pr[f"out:{e['label_en']}->{typ(e['target'])}"] += 1
        if typ(e['target']) == 'PushRound': pr[f"in:{typ(e['source'])}-{e['label_en']}"] += 1
    a = {
        'nodes': len(nodes), 'edges': len(E), 'references': len(refs), 'resolving': len(refs) - len(dang), 'dangling': len(dang),
        'integrity': round((len(refs) - len(dang)) / len(refs) * 100, 1),
        'missingIdentifiers': sorted({r[2] for r in dang}),
        'danglingByProperty': dict(Counter(f'{r[0]}.{r[1]}' for r in dang)),
        'relationCounts': dict(rc), 'declared': len(declared), 'realized': sum(1 for t in declared if rc.get(t)),
        'realizedTypes': [t for t in rc if t in declared],
        'untyped': rc.get('relatedTo', 0), 'typedShare': round((len(E) - rc.get('relatedTo', 0)) / len(E) * 100, 1),
        'depictsAsDeclared': sum(1 for e in E if e['label_en'] == 'depicts' and typ(e['source']) == 'Drawing' and typ(e['target']) == 'StructuralComponent'),
        'involvesSegmentAsDeclared': sum(1 for e in E if e['label_en'] == 'involvesSegment' and typ(e['source']) == 'PushRound' and typ(e['target']) == 'GirderSegment'),
        'pushRoundEdges': dict(pr), 'classes': dict(Counter(n['type'] for n in g['nodes'])),
        # stage linkage (added in this recheck)
        'stage': {
            'roundToTemporaryStructure': sum(1 for e in E if {typ(e['source']), typ(e['target'])} == {'PushRound', 'TemporaryStructure'}),
            'roundToSegment_derived': sum(1 for e in E if e['label_en'] == 'involvesSegment' and typ(e['source']) == 'PushRound' and str(e.get('provenance', '')).startswith('derived')),
            'roundToDrawing': sum(1 for e in E if e['label_en'] == 'refersToDrawing' and typ(e['source']) == 'PushRound'),
            'stepToTemporaryStructure_landsOn': rc.get('landsOn', 0),
            'temporaryStructures': sorted(i for i, n in nodes.items() if n['type'] == 'TemporaryStructure'),
        },
    }
    return a

res = OrderedDict()
for v, p in GRAPHS.items():
    if os.path.exists(p): res[v] = audit(p, DECLARED_V12 if v == 'v1_2' else DECLARED)
arch = json.load(open(os.path.join(BASE, '07_graph_repair', 'audit_v1_vs_v1_1.json'), encoding='utf-8'))
problems = []
for v in ('v1', 'v1_1'):
    for k, val in arch[v].items():
        mine = res[v][k]
        same = (set(mine) == set(val)) if k == 'realizedTypes' else (mine == val)
        if not same: problems.append(f'{v}.{k}: {mine} != {val}')
res['reproduction'] = {'archived': '07_graph_repair/audit_v1_vs_v1_1.json', 'problems': problems, 'reproduced': not problems}
json.dump(res, open(os.path.join(HERE, '..', 'results', 'audit_v1_v1_1_v1_2.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for v in [k for k in res if k != 'reproduction']:
    a = res[v]
    print(f"{v}: {a['nodes']} nodes / {a['edges']} edges; refs {a['resolving']}/{a['references']} ({a['integrity']}%); realized {a['realized']}/{a['declared']}; "
          f"untyped {a['untyped']} ({a['typedShare']}% typed); depicts as declared {a['depictsAsDeclared']}; involvesSegment as declared {a['involvesSegmentAsDeclared']}; stage {a['stage']}")
print('reproduction of archived audit:', 'OK' if not problems else problems)
if problems: raise SystemExit(1)
