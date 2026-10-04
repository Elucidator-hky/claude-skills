#!/usr/bin/env python3
"""按用户指认的簇，把照片复制到 合照 / 只有我 / 只有她 / 待确认。原图不动。

用法: python3 sort.py <工作目录> <输出目录> --me 0,3 --her 1 [--apply]
不加 --apply 只打印统计；加了才复制。
"""
from __future__ import annotations
import argparse, json, shutil
from collections import defaultdict
from pathlib import Path
import numpy as np

SURE = 0.42    # 与本人中心相似度 ≥ 此值算确认
MAYBE = 0.33   # 介于 MAYBE 与 SURE 之间进「待确认」


def center(feats, labels, ids):
    c = feats[np.isin(labels, ids)].mean(0)
    return c / np.linalg.norm(c)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("work")
    ap.add_argument("out")
    ap.add_argument("--me", required=True)
    ap.add_argument("--her", required=True)
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    work, out = Path(a.work).expanduser(), Path(a.out).expanduser()
    d = np.load(work / "faces.npz")
    feats, labels = np.nan_to_num(d["feats"]), d["labels"]
    meta = json.load(open(work / "clusters.json"))["faces"]
    me = center(feats, labels, [int(x) for x in a.me.split(",")])
    her = center(feats, labels, [int(x) for x in a.her.split(",")])

    # 每张照片取「我」「她」各自最高相似度
    best = defaultdict(lambda: [0.0, 0.0])
    for f, m in zip(feats, meta):
        b = best[m["photo"]]
        b[0], b[1] = max(b[0], float(f @ me)), max(b[1], float(f @ her))

    plan = defaultdict(list)
    for photo, (sm, sh) in best.items():
        hm, hh = sm >= SURE, sh >= SURE
        if hm and hh:
            plan["合照"].append(photo)
        elif hm:
            plan["待确认" if sh >= MAYBE else "只有我"].append(photo)
        elif hh:
            plan["待确认" if sm >= MAYBE else "只有她"].append(photo)
        elif max(sm, sh) >= MAYBE:
            plan["待确认"].append(photo)

    for k in ["合照", "只有我", "只有她", "待确认"]:
        print(f"{k}: {len(plan[k])} 张")
    if not a.apply:
        print("（预览，加 --apply 才复制）")
        return
    for k, photos in plan.items():
        (out / k).mkdir(parents=True, exist_ok=True)
        for p in photos:
            src = Path(p)
            dst = out / k / f"{src.parent.name}_{src.name}"
            if not dst.exists():
                shutil.copy2(src, dst)
    print(f"已复制到 {out}")


if __name__ == "__main__":
    main()
