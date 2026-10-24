"""
钢箱梁知识图谱 - 三维展示窗口问答联动（3D Linkage）
=======================================================
依据课题例会要求：实现「问答 ↔ 三维模型变更的实时联动」（右侧三维展示窗口）。

本模块提供两个方向的联动契约（与三维查看器解耦，按构件 id/名称/类型对齐）：

A. 问答 -> 三维：根据查询返回需要在三维窗口中【高亮】的构件目标 + 结构化答案。
   返回的 highlight 列表含 {id, name, system, keywords}，三维端可按 id 或名称/关键词高亮 mesh。

B. 三维 -> 问答：用户在三维窗口点选某构件后，返回该构件的知识子图
   （描述它的图纸、适用规范、相关工序、所属系统、所用材料、相关知识点）。

不依赖 LLM；答案由检索+模板生成。
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from graph_engine import KnowledgeGraphEngine
from retrieval import DualLevelRetriever

# 可高亮的「三维构件」节点类型（其余如规范/工序作为知识附着，不直接高亮）
HIGHLIGHTABLE = {"ComponentSystem", "StructuralComponent", "GirderSegment", "TemporaryStructure"}

# 邻居节点类型 -> 联动面板分组名（按目标节点类型归并，更清晰）
TYPE_GROUP = {
    "Drawing": "related_drawings",
    "TechnicalSpecification": "applicable_specs",
    "ConstructionProcess": "processes",
    "ConstructionMethod": "construction_method",
    "Material": "materials",
    "KnowledgePoint": "knowledge_points",
    "ComponentSystem": "related_components",
    "StructuralComponent": "related_components",
    "GirderSegment": "related_components",
    "TemporaryStructure": "related_components",
    "PushRound": "push_rounds",
    "Quantity": "quantities",
}


class Linkage3D:
    def __init__(self, engine: Optional[KnowledgeGraphEngine] = None,
                 retriever: Optional[DualLevelRetriever] = None):
        self.engine = engine or KnowledgeGraphEngine()
        self.retriever = retriever or DualLevelRetriever(self.engine)

    # ---------- A. 问答 -> 三维高亮 ----------
    def query_to_highlight(self, query: str, top_k: int = 8) -> Dict[str, Any]:
        ans = self.retriever.answer(query, top_k=top_k)
        highlights: List[Dict[str, Any]] = []
        seen = set()

        def add_highlight(nid: str, role: str) -> None:
            if nid in seen or nid not in self.engine.nodes:
                return
            node = self.engine.nodes[nid]
            if node.type not in HIGHLIGHTABLE:
                return
            seen.add(nid)
            highlights.append({
                "id": nid,
                "name": node.name,
                "type": node.type,
                "system": node.raw.get("sb:belongsTo", node.id if node.type == "ComponentSystem" else ""),
                "keywords": _keywords(node.name),
                "role": role,
            })

        # 命中实体本身可高亮的直接加入
        for e in ans["entities"]:
            add_highlight(e["id"], "matched")
        # 命中实体的邻居里，把「可高亮构件」也带出（如知识点->构件系统）
        for e in ans["entities"]:
            for item in self.engine.neighbors(e["id"], "both"):
                add_highlight(item["node"]["id"], "related")

        return {
            "query": query,
            "answer": ans["answer"],
            "highlight": highlights,
            "entities": ans["entities"],
            "context_subgraph": ans["context_subgraph"],
            "linkage": "query->3d",
        }

    # ---------- B. 三维点选 -> 知识子图 ----------
    def component_to_knowledge(self, key: str, depth: int = 1) -> Dict[str, Any]:
        node = self.engine.resolve(key)
        if not node:
            return {"found": False, "key": key, "message": "未找到对应构件"}

        groups: Dict[str, List[Dict[str, str]]] = defaultdict(list)
        for item in self.engine.neighbors(node.id, "both"):
            label = item["edge"]["label"]
            nb = item["node"]
            group = TYPE_GROUP.get(nb["type"], "related")
            groups[group].append({
                "id": nb["id"], "name": nb["name"], "type": nb["type"],
                "relation": label, "dir": item["dir"],
            })

        panel = self._build_panel(node, groups)
        return {
            "found": True,
            "component": {
                "id": node.id, "name": node.name, "type": node.type,
                "props": node.raw,
            },
            "knowledge": dict(groups),
            "panel_text": panel,
            "subgraph": self.engine.subgraph(node.id, depth=depth),
            "linkage": "3d->query",
        }

    def _build_panel(self, node, groups: Dict[str, List[Dict[str, str]]]) -> str:
        lines = [f"【{node.name}】（{node.type}）"]
        desc = node.raw.get("sb:description") or node.raw.get("sb:note")
        if desc:
            lines.append(str(desc))
        order = [
            ("related_components", "关联构件"),
            ("related_drawings", "相关图纸"), ("applicable_specs", "适用规范"),
            ("construction_method", "施工工艺"), ("processes", "相关工序"),
            ("push_rounds", "顶推轮次"), ("materials", "使用材料"),
            ("knowledge_points", "相关知识点"), ("quantities", "工程数量"),
            ("related", "其他关联"),
        ]
        for gkey, gname in order:
            items = groups.get(gkey)
            if items:
                names = "、".join(dict.fromkeys(i["name"] for i in items))
                lines.append(f"· {gname}：{names}")
        return "\n".join(lines)


def _keywords(name: str) -> List[str]:
    """从构件名提炼可供三维端模糊匹配 mesh 的关键词。"""
    import re
    kws = re.findall(r"[A-Za-z]+\d*|[0-9]+#?|[\u4e00-\u9fff]{2,}", name or "")
    return list(dict.fromkeys(kws))


if __name__ == "__main__":
    link = Linkage3D()
    print("== 问答->三维：拱肋安装 ==")
    r = link.query_to_highlight("拱肋怎么安装")
    print(r["answer"])
    print("高亮:", [(h["name"], h["role"]) for h in r["highlight"]])
    print("\n== 三维->问答：点选 拱肋结构系统 ==")
    k = link.component_to_knowledge("拱肋结构系统")
    print(k["panel_text"])
