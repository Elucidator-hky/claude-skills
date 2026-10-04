#!/usr/bin/env python3
"""扫描照片目录：检测人脸、提取特征、聚类，生成 clusters.html 供用户认人。

用法: python3 scan.py <照片目录> <工作目录> [--since YYYY-MM] [--limit N]
产出: <工作目录>/faces.npz（所有人脸特征）、clusters.json、clusters.html、crops/
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys, hashlib, html
from pathlib import Path
import cv2
import numpy as np
import models

EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif"}
MAX_SIDE = 1600      # 检测前缩放到这个长边
MIN_FACE = 60        # 原图缩放后人脸最小边长（px），太小的路人脸不要
SIM_TH = 0.40        # 聚类余弦相似度阈值（SFace 官方同人阈值 0.363）


def load(path: Path, cache: Path):
    """读图；HEIC 先用 sips 转 jpg 缓存。返回 BGR 图或 None。"""
    if path.suffix.lower() in {".heic", ".heif"}:
        out = cache / (hashlib.md5(str(path).encode()).hexdigest() + ".jpg")
        if not out.exists():
            subprocess.run(["sips", "-s", "format", "jpeg", "-Z", str(MAX_SIDE), str(path), "--out", str(out)],
                           capture_output=True)
        path = out
    img = cv2.imread(str(path))
    if img is None:
        return None
    h, w = img.shape[:2]
    s = MAX_SIDE / max(h, w)
    if s < 1:
        img = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    return img


def iter_photos(root: Path, since: str | None):
    for p in sorted(root.rglob("*")):
        if p.suffix.lower() not in EXTS or not p.is_file():
            continue
        if since:
            month = p.relative_to(root).parts[0]
            if month[:7].replace("-", "").isdigit() and month[:7] < since:
                continue
        yield p


def cluster(feats: np.ndarray):
    """贪心增量聚类：每张脸并入最相似的簇中心，否则开新簇。按簇大小降序返回标签。"""
    centers, members = [], []
    for i, f in enumerate(feats):
        if centers:
            sims = np.array(centers) @ f
            j = int(sims.argmax())
            if sims[j] >= SIM_TH:
                members[j].append(i)
                c = feats[members[j]].mean(0)
                centers[j] = c / np.linalg.norm(c)
                continue
        centers.append(f.copy())
        members.append([i])
    order = sorted(range(len(members)), key=lambda k: -len(members[k]))
    labels = np.full(len(feats), -1)
    for new, k in enumerate(order):
        labels[members[k]] = new
    return labels, [np.array(centers[k]) for k in order]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("photos")
    ap.add_argument("work")
    ap.add_argument("--since", help="只扫 YYYY-MM 及之后的月份文件夹")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    root, work = Path(a.photos).expanduser(), Path(a.work).expanduser()
    (work / "crops").mkdir(parents=True, exist_ok=True)
    (work / "heic_cache").mkdir(exist_ok=True)

    DET, REC = models.paths()
    det = cv2.FaceDetectorYN.create(DET, "", (320, 320), 0.8)
    rec = cv2.FaceRecognizerSF.create(REC, "")

    photos = list(iter_photos(root, a.since))
    if a.limit:
        photos = photos[: a.limit]
    feats, meta = [], []
    for n, p in enumerate(photos, 1):
        img = load(p, work / "heic_cache")
        if img is None:
            continue
        h, w = img.shape[:2]
        det.setInputSize((w, h))
        _, faces = det.detect(img)
        for k, face in enumerate(faces if faces is not None else []):
            if min(face[2], face[3]) < MIN_FACE:
                continue
            aligned = rec.alignCrop(img, face)
            f = rec.feature(aligned).flatten()
            feats.append(f / np.linalg.norm(f))
            crop = f"crops/{len(meta)}.jpg"
            cv2.imwrite(str(work / crop), aligned)
            meta.append({"photo": str(p), "crop": crop})
        if n % 100 == 0:
            print(f"{n}/{len(photos)} 张，已得 {len(meta)} 张脸", flush=True)

    feats = np.array(feats, dtype=np.float32)
    labels, centers = cluster(feats)
    for m, l in zip(meta, labels):
        m["cluster"] = int(l)
    np.savez(work / "faces.npz", feats=feats, labels=labels)
    json.dump({"photos": len(photos), "faces": meta}, open(work / "clusters.json", "w"), ensure_ascii=False)

    # 生成认人网页：前 30 个大簇，每簇展示 12 张脸
    rows = []
    for c in range(min(30, len(centers))):
        idx = [i for i, l in enumerate(labels) if l == c]
        imgs = "".join(f'<img src="{html.escape(meta[i]["crop"])}">' for i in idx[:12])
        rows.append(f"<div class=c><h3>第 {c} 组 · {len(idx)} 张脸</h3>{imgs}</div>")
    page = ("<meta charset=utf-8><title>认人</title><style>body{font-family:sans-serif;margin:20px}"
            "img{width:96px;height:112px;object-fit:cover;margin:2px;border-radius:6px}"
            ".c{margin-bottom:18px;border-bottom:1px solid #ddd}</style>"
            "<h2>找出「我」和「老婆」分别是第几组（同一个人分成几组也没关系，都告诉我）</h2>" + "".join(rows))
    (work / "clusters.html").write_text(page)
    print(f"完成：{len(photos)} 张照片，{len(meta)} 张脸，{len(centers)} 个簇")
    print("簇大小前 10：", [int((labels == c).sum()) for c in range(min(10, len(centers)))])


if __name__ == "__main__":
    main()
