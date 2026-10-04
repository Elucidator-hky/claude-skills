#!/usr/bin/env python3
"""视频版筛选：每个视频均匀抽帧做人脸比对，复制到 <输出>/视频/{合照,只有我,只有她,待确认}。

跳过 Live Photo 附带的短视频（同目录有同名图片的 .MOV）。
「我」「她」的特征中心取自 scan.py 的工作目录 + 用户指认的簇号。
用法: python3 videos.py <图库> <scan工作目录> <输出目录> --me 2 --her 0,8 [--since YYYY-MM] [--apply]
"""
from __future__ import annotations
import argparse, shutil
from collections import defaultdict
from pathlib import Path
import cv2
import numpy as np
import models

VIDEO = {".mov", ".mp4"}
IMAGE = {".jpg", ".jpeg", ".heic", ".png"}
FRAMES = 8         # 每个视频抽几帧
MIN_FACE = 50
SURE, MAYBE = 0.42, 0.33   # 与 sort.py 一致


def center(feats, labels, ids):
    c = feats[np.isin(labels, ids)].mean(0)
    return c / np.linalg.norm(c)


def is_live(p: Path):
    stem = p.name.split(".")[0]
    return any((p.parent / (stem + e)).exists() or (p.parent / (stem + e.upper())).exists() for e in IMAGE)


def best_sims(p: Path, det, rec, me, her):
    cap = cv2.VideoCapture(str(p))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    sm = sh = 0.0
    for idx in np.linspace(0, max(n - 1, 0), FRAMES).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ok, img = cap.read()
        if not ok:
            continue
        h, w = img.shape[:2]
        det.setInputSize((w, h))
        _, faces = det.detect(img)
        for face in faces if faces is not None else []:
            if min(face[2], face[3]) < MIN_FACE:
                continue
            f = rec.feature(rec.alignCrop(img, face)).flatten()
            f = np.nan_to_num(f / np.linalg.norm(f))
            sm, sh = max(sm, float(f @ me)), max(sh, float(f @ her))
    cap.release()
    return sm, sh


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lib")
    ap.add_argument("work")
    ap.add_argument("out")
    ap.add_argument("--me", required=True)
    ap.add_argument("--her", required=True)
    ap.add_argument("--since", default="0000", help="只看 YYYY-MM 及之后的月份文件夹")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    lib, out = Path(a.lib).expanduser(), Path(a.out).expanduser() / "视频"
    d = np.load(Path(a.work).expanduser() / "faces.npz")
    feats, labels = np.nan_to_num(d["feats"]), d["labels"]
    me = center(feats, labels, [int(x) for x in a.me.split(",")])
    her = center(feats, labels, [int(x) for x in a.her.split(",")])
    DET, REC = models.paths()
    det = cv2.FaceDetectorYN.create(DET, "", (320, 320), 0.8)
    rec = cv2.FaceRecognizerSF.create(REC, "")

    vids = [p for p in sorted(lib.rglob("*")) if p.suffix.lower() in VIDEO and p.is_file()
            and p.relative_to(lib).parts[0][:7] >= a.since and not is_live(p)]
    print(f"待处理视频 {len(vids)} 个（已跳过 Live Photo）", flush=True)
    plan = defaultdict(list)
    for n, p in enumerate(vids, 1):
        sm, sh = best_sims(p, det, rec, me, her)
        hm, hh = sm >= SURE, sh >= SURE
        if hm and hh:
            k = "合照"
        elif hm:
            k = "待确认" if sh >= MAYBE else "只有我"
        elif hh:
            k = "待确认" if sm >= MAYBE else "只有她"
        elif max(sm, sh) >= MAYBE:
            k = "待确认"
        else:
            continue
        plan[k].append(p)
        if n % 100 == 0:
            print(f"{n}/{len(vids)}", flush=True)
    for k in ["合照", "只有我", "只有她", "待确认"]:
        print(f"{k}: {len(plan[k])} 个")
    if not a.apply:
        print("（预览，加 --apply 才复制）")
        return
    for k, ps in plan.items():
        (out / k).mkdir(parents=True, exist_ok=True)
        for p in ps:
            dst = out / k / p.name
            if not dst.exists():
                shutil.copy2(p, dst)
    print(f"已复制到 {out}")


if __name__ == "__main__":
    main()
