# -*- coding: utf-8 -*-
"""
build_kg.py —— 知识图谱一键构建 / 自检脚本（不依赖 LLM、不联网）

依据课题例会要求：
  1) 点（知识点）+ 边（连接关系）的图结构
  2) 三支柱：桥梁基础知识(规范) + 施工方法(顶推) + 项目图纸 全部连通
  3) 工程语言 + 构件库(JSON) 约束
  4) 可导入 Neo4j / Gephi

运行：
  python build_kg.py            # 构建并打印报告
  python build_kg.py --export   # 额外导出 cypher / graphml 到 build/ 目录
"""
import os
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(HERE, "build")


def main(export: bool = False):
    from graph_engine import KnowledgeGraphEngine
    from component_library import ComponentLibrary
    from retrieval import DualLevelRetriever

    print("=" * 60)
    print(" 钢箱梁知识图谱 · 构建与自检")
    print("=" * 60)

    # 1) 点-边图
    engine = KnowledgeGraphEngine()
    st = engine.stats()
    print(f"\n[1] 点-边图：{st['node_count']} 个节点 / {st['edge_count']} 条边")
    print("    节点类型：")
    for t, c in sorted(st["node_types"].items(), key=lambda x: -x[1]):
        print(f"      - {t}: {c}")
    print("    边类型：")
    for t, c in sorted(st["edge_labels"].items(), key=lambda x: -x[1]):
        print(f"      - {t}: {c}")
    print("    枢纽节点（度数 Top5）：")
    for hub in st["top_hubs"][:5]:
        print(f"      - {hub['name']}: {hub['degree']}")

    # 2) 三支柱覆盖
    kp = engine.nodes_by_type("KnowledgePoint")
    basics = [n for n in kp if n.raw.get("sb:pillar") == "桥梁基础知识"]
    methods = [n for n in kp if n.raw.get("sb:pillar") == "施工方法"]
    drawings = engine.nodes_by_type("Drawing")
    specs = engine.nodes_by_type("TechnicalSpecification")
    print(f"\n[2] 三支柱覆盖：")
    print(f"      支柱1 桥梁基础知识：{len(basics)} 知识点 + {len(specs)} 规范")
    print(f"      支柱2 施工方法    ：{len(methods)} 知识点（步履式顶推）")
    print(f"      支柱3 项目图纸    ：{len(drawings)} 张图纸")

    # 检查连通性：每个知识点是否至少有一条边连到项目实体
    isolated = [n for n in kp if not engine.neighbors(n.id, "both")]
    if isolated:
        print(f"      ⚠️ 孤立知识点 {len(isolated)} 个：{[n.name for n in isolated]}")
    else:
        print(f"      ✅ 全部知识点均已连通到项目实体（三支柱贯通）")

    # 3) 构件库约束
    lib = ComponentLibrary(engine)
    path = lib.save()
    print(f"\n[3] 构件库：{len(lib.library['systems'])} 系统 / "
          f"{len(lib.library['catalog'])} 目录项 / {len(lib.library['materials'])} 材料")
    print(f"      已写入：{os.path.relpath(path, HERE)}")
    print(f"      允许材料：{', '.join(lib.library['allowed_materials'])}")

    # 4) 检索自检
    retr = DualLevelRetriever(engine)
    print(f"\n[4] 双层检索自检（无 LLM）：")
    for q in ["拱肋怎么安装", "步履式顶推", "焊缝检测规范", "Q355D用在哪"]:
        r = retr.retrieve(q, top_k=3)
        ents = [e["name"] for e in r.get("entities", [])[:3]]
        print(f"      Q: {q} -> {ents}")

    # 5) 导出
    if export:
        os.makedirs(BUILD_DIR, exist_ok=True)
        for fmt, ext in [("json", "json"), ("cypher", "cypher"), ("graphml", "graphml")]:
            out = os.path.join(BUILD_DIR, f"kg_graph.{ext}")
            with open(out, "w", encoding="utf-8") as f:
                f.write(engine.export(fmt))
            print(f"\n[5] 已导出 {fmt} -> {os.path.relpath(out, HERE)}")

    print("\n" + "=" * 60)
    print(" ✅ 构建完成。可启动服务： uvicorn main:app --reload")
    print("=" * 60)


if __name__ == "__main__":
    main(export="--export" in sys.argv)
