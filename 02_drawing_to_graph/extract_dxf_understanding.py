# -*- coding: utf-8 -*-
"""
DXF 图纸理解抽取器（低层 tagger，绕过 LibreDWG 产物的结构瑕疵）

从真实图纸 DXF 中抽取：图层、实体统计、文字标注、尺寸数字、桩号、边界框，
归类输出结构化 JSON，用于回灌知识库/问答/建模。

用法：
    python extract_dxf_understanding.py "<dxf路径>" [输出json路径]
"""
from __future__ import annotations
import sys
import re
import json
from collections import Counter
from pathlib import Path

from ezdxf.lldxf.tagger import ascii_tags_loader


def _clean(t: str) -> str:
    # 去除 MTEXT 控制码与格式
    t = re.sub(r"\\[A-Za-z][^;]*;", "", t)
    t = t.replace("{", "").replace("}", "").replace("\\P", " ")
    return t.strip()


def extract(dxf_path: str) -> dict:
    texts: list[str] = []
    types: Counter = Counter()
    xs: list[float] = []
    ys: list[float] = []
    tp = None
    buf = ""

    with open(dxf_path, "r", encoding="utf-8", errors="ignore") as f:
        for tag in ascii_tags_loader(f, skip_comments=True):
            code, val = tag.code, tag.value
            if code == 0:
                if tp in ("TEXT", "MTEXT") and buf.strip():
                    texts.append(_clean(buf))
                tp = val
                buf = ""
                types[val] += 1
            elif tp in ("TEXT", "MTEXT") and code in (1, 3):
                buf += str(val)
            elif code == 10:
                try:
                    xs.append(float(val))
                except (ValueError, TypeError):
                    pass
            elif code == 20:
                try:
                    ys.append(float(val))
                except (ValueError, TypeError):
                    pass
    if tp in ("TEXT", "MTEXT") and buf.strip():
        texts.append(_clean(buf))

    texts = [t for t in texts if t]

    # 归类
    stations = sorted({t for t in texts if re.search(r"K\d\+\d", t)})
    # 纯尺寸数字（含 = 表达式）
    dims = [t for t in texts if re.fullmatch(r"[\d\.\+\-=×xX\s]+", t) and re.search(r"\d{2,}", t)]
    # 中文注记（含汉字、长度>=2）
    notes = [t for t in texts if re.search(r"[\u4e00-\u9fff]", t) and len(t) >= 2]
    # 关键工程术语命中
    key = [t for t in texts if re.search(
        r"提篮|下承|中承|上承|拱肋|主拱|次拱|横撑|主梁|钢箱|吊索|吊杆|预拱|矢高|矢|跨|顶推|"
        r"Q3\d\d|节段|Z\d|C\d|HC|焊缝|支座|承台|桩|护栏|铺装|标高|里程", t)]

    bbox = None
    if xs and ys:
        bbox = {
            "xmin": round(min(xs), 1), "xmax": round(max(xs), 1),
            "ymin": round(min(ys), 1), "ymax": round(max(ys), 1),
            "width": round(max(xs) - min(xs), 1),
            "height": round(max(ys) - min(ys), 1),
        }

    return {
        "file": Path(dxf_path).name,
        "entityTypes": dict(types.most_common()),
        "numTexts": len(texts),
        "boundingBox": bbox,
        "stations": stations,
        "dimensions": dims[:200],
        "keyTerms": key[:200],
        "notes": notes[:300],
    }


def main():
    if len(sys.argv) < 2:
        print("用法: extract_dxf_understanding.py <dxf> [out.json]")
        return
    res = extract(sys.argv[1])
    print(f"文件: {res['file']}")
    print(f"实体统计(前12): {list(res['entityTypes'].items())[:12]}")
    print(f"文字数: {res['numTexts']}  边界框: {res['boundingBox']}")
    print(f"桩号: {res['stations']}")
    print("--- 关键术语文字 ---")
    for t in res["keyTerms"][:40]:
        print("  ", t[:90])
    if len(sys.argv) >= 3:
        Path(sys.argv[2]).write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n已写入 {sys.argv[2]}")


if __name__ == "__main__":
    main()
