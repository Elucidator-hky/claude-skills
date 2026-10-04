#!/usr/bin/env python3
"""用参考照片（两人都在、清楚的几张，如婚纱照）的簇，在图库的簇里找出这两个人最可能是第几组。

用法: python3 match.py <图库scan工作目录> <参考照scan工作目录> [--top 5]
参考照 scan 后取最大的两个簇当 A、B；对图库前 30 个簇算与 A、B 中心的相似度，各列出最高的几个。
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np


def centers(work: Path, n: int):
    d = np.load(work / "faces.npz")
    feats, labels = np.nan_to_num(d["feats"]), d["labels"]
    out = []
    for c in range(min(n, int(labels.max()) + 1)):
        m = feats[labels == c]
        v = m.mean(0)
        out.append((c, len(m), v / np.linalg.norm(v)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lib_work")
    ap.add_argument("ref_work")
    ap.add_argument("--top", type=int, default=5)
    a = ap.parse_args()
    ref = centers(Path(a.ref_work).expanduser(), 2)
    lib = centers(Path(a.lib_work).expanduser(), 30)
    for name, (rc, rn, rv) in zip("AB", ref):
        ranked = sorted(lib, key=lambda x: -float(x[2] @ rv))[: a.top]
        print(f"参考 {name}（参考照第 {rc} 组，{rn} 张脸）最像的图库簇：")
        for c, n, v in ranked:
            print(f"  第 {c} 组  相似度 {float(v @ rv):.3f}  {n} 张脸")
    print("相似度 ≥ 0.42 的簇基本是同一个人；同一人被拆成几组时一起传给 sort.py，如 --her 0,8")


if __name__ == "__main__":
    main()
