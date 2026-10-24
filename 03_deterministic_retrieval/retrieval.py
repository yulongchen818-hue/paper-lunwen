"""
钢箱梁知识图谱 - 双层检索（Dual-Level Retrieval）
====================================================
借鉴 LightRAG / GraphRAG 的「双层检索」思想，但**不依赖任何 LLM / 向量模型**，
纯标准库实现，可离线运行（符合本轮「先做不依赖 LLM 的增强」目标）：

- 低层（Local / 实体级）：把查询匹配到最相关的「点（知识点/实体）」。
- 高层（Global / 关系级）：沿这些实体的「边」扩展，召回相关的关系、邻居与主题，
  形成可解释的上下文子图（之后可直接喂给 LLM 做问答）。

中文友好的词法打分：字符二元组(bigram) + 关键词字段加权，无需分词器与外部依赖。
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from graph_engine import KnowledgeGraphEngine, Node


def _ngrams(text: str, n: int = 2) -> List[str]:
    text = re.sub(r"\s+", "", (text or "").lower())
    if len(text) < n:
        return [text] if text else []
    return [text[i:i + n] for i in range(len(text) - n + 1)]


def _terms(query: str) -> List[str]:
    """提取查询词：连续的字母/数字串 + 中文字符二元组。"""
    q = (query or "").lower()
    out: List[str] = []
    # 字母数字 token（图号/规范号/英文）
    out += re.findall(r"[a-z0-9][a-z0-9\-\./]*", q)
    # 中文 bigram
    for han_run in re.findall(r"[\u4e00-\u9fff]+", q):
        out += _ngrams(han_run, 2) if len(han_run) >= 2 else [han_run]
        # 同时保留整词，提升精确匹配
        if len(han_run) <= 6:
            out.append(han_run)
    return [t for t in out if t]


class DualLevelRetriever:
    def __init__(self, engine: Optional[KnowledgeGraphEngine] = None):
        self.engine = engine or KnowledgeGraphEngine()
        self._node_grams: Dict[str, Dict[str, int]] = {}
        self._name_grams: Dict[str, set] = {}
        self._build_index()

    def _build_index(self) -> None:
        for nid, node in self.engine.nodes.items():
            grams: Dict[str, int] = defaultdict(int)
            for g in _ngrams(node.text, 2):
                grams[g] += 1
            for w in re.findall(r"[a-z0-9][a-z0-9\-\./]*", node.text.lower()):
                grams[w] += 1
            self._node_grams[nid] = grams
            self._name_grams[nid] = set(_ngrams(node.name, 2)) | set(
                re.findall(r"[a-z0-9][a-z0-9\-\./]*", node.name.lower())
            )

    # ---------- 低层：实体级检索 ----------
    def search_entities(self, query: str, top_k: int = 8, type_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        terms = _terms(query)
        if not terms:
            return []
        tset = set(terms)
        tf = type_filter.replace("sb:", "") if type_filter else None
        scored: List[Tuple[float, str]] = []
        for nid, node in self.engine.nodes.items():
            if tf and node.type != tf:
                continue
            grams = self._node_grams[nid]
            name_grams = self._name_grams[nid]
            score = 0.0
            for t in tset:
                if t in grams:
                    score += grams[t]
                    if t in name_grams:      # 命中名称额外加权
                        score += 3.0
            if score > 0:
                # 名称整体相似度加成
                score += 2.0 * (len(name_grams & tset) / (len(name_grams) + 1))
                scored.append((score, nid))
        scored.sort(reverse=True)
        results = []
        for score, nid in scored[:top_k]:
            node = self.engine.nodes[nid]
            results.append({
                "id": nid, "name": node.name, "type": node.type,
                "score": round(score, 2),
                "snippet": (node.raw.get("sb:description") or node.raw.get("sb:definition") or node.text)[:120],
            })
        return results

    # ---------- 高层：关系级扩展 ----------
    def retrieve(self, query: str, top_k: int = 6, hops: int = 1) -> Dict[str, Any]:
        """双层检索：返回匹配实体 + 关系上下文子图 + 可解释证据。"""
        entities = self.search_entities(query, top_k=top_k)
        seed_ids = [e["id"] for e in entities]

        # 关系级：聚合种子实体的边，统计关系类型并召回邻居
        relation_count: Dict[str, int] = defaultdict(int)
        context_nodes: Dict[str, Node] = {}
        context_edges: List[Dict[str, Any]] = []
        edge_seen = set()
        for sid in seed_ids:
            context_nodes[sid] = self.engine.nodes[sid]
            for item in self.engine.neighbors(sid, "both"):
                e = item["edge"]
                relation_count[e["label"]] += 1
                k = (e["source"], e["target"], e["label_en"])
                if k not in edge_seen:
                    edge_seen.add(k)
                    context_edges.append(e)
                nb = item["node"]
                context_nodes.setdefault(nb["id"], self.engine.nodes[nb["id"]])

        # 证据：把命中实体按类型归并，便于问答模板化使用
        by_type: Dict[str, List[Dict[str, str]]] = defaultdict(list)
        for e in entities:
            by_type[e["type"]].append({"id": e["id"], "name": e["name"]})

        return {
            "query": query,
            "entities": entities,
            "relations": dict(sorted(relation_count.items(), key=lambda kv: -kv[1])),
            "evidence_by_type": dict(by_type),
            "context_subgraph": {
                "nodes": [n.to_dict() for n in context_nodes.values()],
                "edges": context_edges,
            },
            "note": "未启用 LLM；context_subgraph 可直接作为大模型问答的检索上下文。",
        }

    # ---------- 无 LLM 的模板化「回答」 ----------
    def answer(self, query: str, top_k: int = 6) -> Dict[str, Any]:
        """基于检索结果，用模板拼装一段可读的结构化回答（不调用 LLM）。"""
        res = self.retrieve(query, top_k=top_k)
        ents = res["entities"]
        if not ents:
            return {"query": query, "answer": "未在知识图谱中检索到相关内容。", "entities": [], "context_subgraph": res["context_subgraph"]}

        lines: List[str] = [f"针对「{query}」，知识图谱命中以下相关内容："]
        for e in ents[:5]:
            type_cn = {
                "KnowledgePoint": "知识点", "Drawing": "图纸", "ConstructionProcess": "工序",
                "ConstructionMethod": "施工工艺", "ComponentSystem": "构件系统",
                "StructuralComponent": "构件", "TechnicalSpecification": "规范",
                "PushRound": "顶推轮次", "Material": "材料", "GirderSegment": "梁段",
            }.get(e["type"], e["type"])
            lines.append(f"- [{type_cn}] {e['name']}：{e['snippet']}")
        if res["relations"]:
            rel_str = "、".join(f"{k}({v})" for k, v in list(res["relations"].items())[:6])
            lines.append(f"相关联系：{rel_str}")
        return {
            "query": query,
            "answer": "\n".join(lines),
            "entities": ents,
            "relations": res["relations"],
            "context_subgraph": res["context_subgraph"],
        }


if __name__ == "__main__":
    r = DualLevelRetriever()
    for q in ["拱肋怎么安装", "步履式顶推", "焊缝检测规范", "Q355D 用在哪"]:
        a = r.answer(q)
        print("\n====", q, "====")
        print(a["answer"])
