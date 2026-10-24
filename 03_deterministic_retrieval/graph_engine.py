"""
钢箱梁知识图谱 - 点-边图引擎（Graph Engine）
=================================================
依据课题例会要求，将原有 JSON-LD「实体清单」升级为显式的「点（知识点）+ 边（连接关系）」图结构。

设计要点：
- 不依赖任何外部库（纯标准库），可与现有 FastAPI 服务平滑共存。
- 自动从 JSON-LD 的关系属性（belongsTo / components / relatedComponents / relatedDrawings /
  applicableComponents / sequence / method / flowSegments 等）推导显式边。
- 提供邻居查询、子图抽取、最短路径、按类型/项目过滤。
- 支持导出为 Neo4j Cypher / GraphML / 节点-边 JSON（呼应会议「用 Neo4j 训练 AI」的后续路线）。
"""
from __future__ import annotations

import json
import re
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


# 关系属性 -> (中文边标签, 英文边标签)。值若为指向已存在节点的 @id，则建立一条有向边。
RELATION_PROPS: Dict[str, Tuple[str, str]] = {
    "sb:components": ("包含构件", "hasComponent"),
    "sb:belongsTo": ("属于系统", "belongsTo"),
    "sb:relatedComponents": ("描述构件", "depicts"),
    "sb:relatedDrawings": ("关联图纸", "refersToDrawing"),
    "sb:applicableComponents": ("适用于", "appliesTo"),
    "sb:sequence": ("工序步骤", "hasStep"),
    "sb:method": ("采用工艺", "usesMethod"),
    "sb:flowSegments": ("包含节段", "involvesSegment"),
    "sb:launchSequence": ("顶推顺序", "launchOrder"),
}

# 这些属性的值是「人类可读简码」（如 A1/A4），需映射到节点 @id（sb:Segment_A1）
SEGMENT_CODE_PROPS = {"sb:flowSegments", "sb:launchSequence"}

# 节点类型 -> 该类型的「主名称」候选字段（用于展示与检索）
NAME_FIELDS = [
    "sb:name", "sb:drawingName", "sb:systemName", "sb:processName",
    "sb:specName", "sb:methodName", "sb:roundName", "sb:structureName",
    "sb:projectName", "sb:segmentNo",
]

# 参与文本检索的字段
TEXT_FIELDS = NAME_FIELDS + [
    "sb:description", "sb:category", "sb:note", "sb:appliedTo", "sb:grade",
    "sb:dimension", "sb:material", "sb:steelGrade", "sb:drawingNo", "sb:specId",
    "sb:constructionMethod", "sb:dangerousReason", "sb:girderSection",
]


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


class Node:
    __slots__ = ("id", "type", "raw", "name", "text")

    def __init__(self, raw: Dict[str, Any]):
        self.id: str = raw.get("@id", "")
        self.type: str = (raw.get("@type", "") or "").replace("sb:", "")
        self.raw = raw
        self.name = self._pick_name(raw)
        self.text = self._build_text(raw)

    @staticmethod
    def _pick_name(raw: Dict[str, Any]) -> str:
        for f in NAME_FIELDS:
            if raw.get(f):
                return str(raw[f])
        return raw.get("@id", "")

    @staticmethod
    def _build_text(raw: Dict[str, Any]) -> str:
        parts: List[str] = []
        for f in TEXT_FIELDS:
            v = raw.get(f)
            if isinstance(v, (str, int, float)):
                parts.append(str(v))
            elif isinstance(v, list):
                parts.extend(str(x) for x in v if isinstance(x, (str, int, float)))
        return " ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "type": self.type, "name": self.name, "props": self.raw}


class Edge:
    __slots__ = ("source", "target", "label", "label_en", "prop")

    def __init__(self, source: str, target: str, label: str, label_en: str, prop: str):
        self.source = source
        self.target = target
        self.label = label
        self.label_en = label_en
        self.prop = prop

    def key(self) -> Tuple[str, str, str]:
        return (self.source, self.target, self.label_en)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source, "target": self.target,
            "label": self.label, "label_en": self.label_en, "via": self.prop,
        }


class KnowledgeGraphEngine:
    """点-边知识图谱引擎。"""

    def __init__(self, data_paths: Optional[Iterable[str | Path]] = None):
        if data_paths is None:
            base = Path(__file__).parent / "data"
            data_paths = [
                base / "kg_case_bridge.jsonld",      # 项目图纸/构件/工序（支柱三）
                base / "kg_bridge_knowledge.jsonld",   # 桥梁基础知识/规范知识点（支柱一/二）
            ]
        self.data_paths = [Path(p) for p in data_paths]
        self.context: Dict[str, Any] = {}
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self._out: Dict[str, List[Edge]] = defaultdict(list)
        self._in: Dict[str, List[Edge]] = defaultdict(list)
        self._segment_code_to_id: Dict[str, str] = {}
        self._project_id_to_node: Dict[str, str] = {}
        self._grade_to_material: Dict[str, str] = {}

        self._load()
        self._index_lookups()
        self._build_edges()

    # ---------- 加载 ----------
    def _load(self) -> None:
        for path in self.data_paths:
            if not path.exists():
                continue
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not self.context:
                self.context = data.get("@context", {})
            for raw in data.get("@graph", []):
                nid = raw.get("@id")
                if not nid:
                    continue
                self.nodes[nid] = Node(raw)

    def _index_lookups(self) -> None:
        for node in self.nodes.values():
            raw = node.raw
            if node.type == "GirderSegment" and raw.get("sb:segmentNo"):
                self._segment_code_to_id[str(raw["sb:segmentNo"])] = node.id
            if node.type == "Project" and raw.get("sb:projectId"):
                self._project_id_to_node[str(raw["sb:projectId"])] = node.id
            if node.type == "Material" and raw.get("sb:grade"):
                # grade 可能是 "PES7-73/PES7-85" 这类，拆分登记
                for g in re.split(r"[\/、,，]", str(raw["sb:grade"])):
                    g = g.strip()
                    if g:
                        self._grade_to_material.setdefault(g, node.id)

    # ---------- 建边 ----------
    def _add_edge(self, source: str, target: str, label: str, label_en: str, prop: str) -> None:
        if source not in self.nodes or target not in self.nodes or source == target:
            return
        edge = Edge(source, target, label, label_en, prop)
        self.edges.append(edge)
        self._out[source].append(edge)
        self._in[target].append(edge)

    def _build_edges(self) -> None:
        seen: Set[Tuple[str, str, str]] = set()

        def add_unique(s: str, t: str, lbl: str, lbl_en: str, prop: str) -> None:
            if s not in self.nodes or t not in self.nodes or s == t:
                return
            k = (s, t, lbl_en)
            if k in seen:
                return
            seen.add(k)
            self._add_edge(s, t, lbl, lbl_en, prop)

        for node in self.nodes.values():
            raw = node.raw
            # 1) 显式关系属性
            for prop, (lbl, lbl_en) in RELATION_PROPS.items():
                for val in _as_list(raw.get(prop)):
                    if not isinstance(val, str):
                        continue
                    target = val
                    if prop in SEGMENT_CODE_PROPS and not val.startswith("sb:"):
                        target = self._segment_code_to_id.get(val.strip(), "")
                    if target.startswith("sb:") and target in self.nodes:
                        add_unique(node.id, target, lbl, lbl_en, prop)

            # 2) 任意指向已存在 @id 的字符串值（兜底，保证不漏关系）
            for prop, val in raw.items():
                if prop in RELATION_PROPS or prop in ("@id", "@type"):
                    continue
                for v in _as_list(val):
                    if isinstance(v, str) and v.startswith("sb:") and v in self.nodes:
                        add_unique(node.id, v, "关联", "relatedTo", prop)

            # 3) 构件 -> 材料（按 grade 匹配）
            for mprop in ("sb:material", "sb:steelGrade"):
                mv = raw.get(mprop)
                if isinstance(mv, str):
                    mid = self._grade_to_material.get(mv.strip())
                    if mid:
                        add_unique(node.id, mid, "使用材料", "usesMaterial", mprop)

            # 4) 任意带 projectId 的节点 -> 项目
            pid = raw.get("sb:projectId")
            if isinstance(pid, str):
                proj = self._project_id_to_node.get(pid)
                if proj and proj != node.id:
                    add_unique(node.id, proj, "属于项目", "partOfProject", "sb:projectId")

    # ---------- 查询 ----------
    def get_node(self, node_id: str) -> Optional[Node]:
        return self.nodes.get(node_id)

    def resolve(self, key: str) -> Optional[Node]:
        """按 @id 或名称解析节点。"""
        if key in self.nodes:
            return self.nodes[key]
        key_l = key.strip().lower()
        for node in self.nodes.values():
            if node.name and node.name.lower() == key_l:
                return node
        # 模糊：名称包含
        for node in self.nodes.values():
            if node.name and key_l in node.name.lower():
                return node
        return None

    def neighbors(self, node_id: str, direction: str = "both") -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        if direction in ("out", "both"):
            for e in self._out.get(node_id, []):
                out.append({"edge": e.to_dict(), "node": self.nodes[e.target].to_dict(), "dir": "out"})
        if direction in ("in", "both"):
            for e in self._in.get(node_id, []):
                out.append({"edge": e.to_dict(), "node": self.nodes[e.source].to_dict(), "dir": "in"})
        return out

    def subgraph(self, node_id: str, depth: int = 1) -> Dict[str, Any]:
        if node_id not in self.nodes:
            return {"nodes": [], "edges": []}
        visited: Set[str] = {node_id}
        frontier = deque([(node_id, 0)])
        edge_keys: Set[Tuple[str, str, str]] = set()
        edges_out: List[Dict[str, Any]] = []
        while frontier:
            cur, d = frontier.popleft()
            if d >= depth:
                continue
            for e in self._out.get(cur, []) + self._in.get(cur, []):
                if e.key() not in edge_keys:
                    edge_keys.add(e.key())
                    edges_out.append(e.to_dict())
                for nxt in (e.source, e.target):
                    if nxt not in visited:
                        visited.add(nxt)
                        frontier.append((nxt, d + 1))
        return {
            "center": node_id,
            "depth": depth,
            "nodes": [self.nodes[n].to_dict() for n in visited],
            "edges": edges_out,
        }

    def shortest_path(self, src: str, dst: str) -> List[Dict[str, Any]]:
        if src not in self.nodes or dst not in self.nodes:
            return []
        prev: Dict[str, Tuple[str, Edge]] = {}
        q = deque([src])
        seen = {src}
        while q:
            cur = q.popleft()
            if cur == dst:
                break
            for e in self._out.get(cur, []) + self._in.get(cur, []):
                nxt = e.target if e.source == cur else e.source
                if nxt not in seen:
                    seen.add(nxt)
                    prev[nxt] = (cur, e)
                    q.append(nxt)
        if dst not in prev and src != dst:
            return []
        path: List[Dict[str, Any]] = []
        cur = dst
        while cur != src:
            p, e = prev[cur]
            path.append({"from": p, "to": cur, "edge": e.to_dict()})
            cur = p
        path.reverse()
        return path

    def nodes_by_type(self, type_name: str) -> List[Node]:
        t = type_name.replace("sb:", "")
        return [n for n in self.nodes.values() if n.type == t]

    # ---------- 统计 ----------
    def stats(self) -> Dict[str, Any]:
        type_count: Dict[str, int] = defaultdict(int)
        for n in self.nodes.values():
            type_count[n.type] += 1
        label_count: Dict[str, int] = defaultdict(int)
        for e in self.edges:
            label_count[e.label] += 1
        # 度数排名（最重要的枢纽节点）
        degree: Dict[str, int] = defaultdict(int)
        for e in self.edges:
            degree[e.source] += 1
            degree[e.target] += 1
        top_hubs = sorted(degree.items(), key=lambda kv: kv[1], reverse=True)[:10]
        return {
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "node_types": dict(sorted(type_count.items(), key=lambda kv: -kv[1])),
            "edge_labels": dict(sorted(label_count.items(), key=lambda kv: -kv[1])),
            "top_hubs": [
                {"id": nid, "name": self.nodes[nid].name, "degree": deg}
                for nid, deg in top_hubs
            ],
        }

    # ---------- 导出 ----------
    def export(self, fmt: str = "json") -> str:
        fmt = fmt.lower()
        if fmt == "json":
            return json.dumps(
                {
                    "nodes": [n.to_dict() for n in self.nodes.values()],
                    "edges": [e.to_dict() for e in self.edges],
                },
                ensure_ascii=False, indent=2,
            )
        if fmt == "cypher":
            return self._export_cypher()
        if fmt == "graphml":
            return self._export_graphml()
        raise ValueError(f"不支持的导出格式: {fmt}")

    def _export_cypher(self) -> str:
        lines: List[str] = ["// 钢箱梁知识图谱 - Neo4j Cypher 导入脚本"]
        for n in self.nodes.values():
            label = n.type or "Entity"
            name = n.name.replace("'", "\\'")
            lines.append(
                f"MERGE (n:{label} {{id:'{n.id}'}}) SET n.name='{name}';"
            )
        for e in self.edges:
            rel = re.sub(r"[^A-Za-z]", "", e.label_en) or "REL"
            lines.append(
                f"MATCH (a {{id:'{e.source}'}}),(b {{id:'{e.target}'}}) "
                f"MERGE (a)-[:{rel.upper()}]->(b);"
            )
        return "\n".join(lines)

    def _export_graphml(self) -> str:
        head = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">\n'
            '  <key id="name" for="node" attr.name="name" attr.type="string"/>\n'
            '  <key id="type" for="node" attr.name="type" attr.type="string"/>\n'
            '  <key id="label" for="edge" attr.name="label" attr.type="string"/>\n'
            '  <graph edgedefault="directed">\n'
        )

        def esc(s: str) -> str:
            return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

        body: List[str] = []
        for n in self.nodes.values():
            body.append(
                f'    <node id="{esc(n.id)}"><data key="name">{esc(n.name)}</data>'
                f'<data key="type">{esc(n.type)}</data></node>'
            )
        for i, e in enumerate(self.edges):
            body.append(
                f'    <edge id="e{i}" source="{esc(e.source)}" target="{esc(e.target)}">'
                f'<data key="label">{esc(e.label)}</data></edge>'
            )
        return head + "\n".join(body) + "\n  </graph>\n</graphml>\n"


if __name__ == "__main__":
    eng = KnowledgeGraphEngine()
    s = eng.stats()
    print(f"节点 {s['node_count']} 个，边 {s['edge_count']} 条")
    print("节点类型:", s["node_types"])
    print("边类型:", s["edge_labels"])
    print("枢纽节点 Top:", [(h['name'], h['degree']) for h in s['top_hubs'][:5]])
