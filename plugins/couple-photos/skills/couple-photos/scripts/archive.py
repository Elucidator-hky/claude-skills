#!/usr/bin/env python3
"""把任意来源的照片/视频复制进统一图库：<图库>/YYYY-MM/YYYY_MM_DD_HH_MM_SS_原名。

拍摄时间优先级：EXIF/视频元数据 → 文件名里的日期或毫秒时间戳 → 文件修改时间。
图库里已有同名同大小的文件就跳过。源文件不动。
用法: python3 archive.py <来源目录> <图库目录> [--photos-db Photos.sqlite] [--apply]
"""
from __future__ import annotations
import argparse, re, shutil, subprocess, json
from collections import Counter
from datetime import datetime
from pathlib import Path

MEDIA = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".mov", ".mp4", ".gif", ".webp"}
VIDEO = {".mov", ".mp4"}


def exif_time(p: Path):
    if p.suffix.lower() in VIDEO:
        r = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_entries",
                            "format_tags=creation_time,com.apple.quicktime.creationdate", str(p)],
                           capture_output=True, text=True)
        tags = json.loads(r.stdout or "{}").get("format", {}).get("tags", {})
        s = tags.get("com.apple.quicktime.creationdate")  # 本地时间带时区
        if s:
            return datetime.fromisoformat(s[:19])
        s = tags.get("creation_time")  # UTC
        return _utc_to_local(s) if s else None
    r = subprocess.run(["sips", "-g", "creation", str(p)], capture_output=True, text=True)
    m = re.search(r"creation: (\d{4}):(\d\d):(\d\d) (\d\d):(\d\d):(\d\d)", r.stdout)
    return datetime(*map(int, m.groups())) if m else None


def _utc_to_local(s: str):
    from datetime import timezone
    dt = datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    return dt.astimezone().replace(tzinfo=None)


def name_time(name: str):
    m = re.search(r"(20\d\d)(\d\d)(\d\d)[_-]?(\d\d)(\d\d)(\d\d)", name)
    if m:
        try:
            return datetime(*map(int, m.groups()))
        except ValueError:
            pass
    m = re.search(r"(1[5-8]\d{11})", name)  # 毫秒时间戳（wx_camera_ / mmexport）
    if m:
        return datetime.fromtimestamp(int(m.group(1)) / 1000)
    return None


PHOTOS_DB = {}  # iPhone Photos.sqlite 里的 文件名 → 入库时间，补没有 EXIF 的图


def load_photos_db(path: str):
    import sqlite3
    con = sqlite3.connect(path)
    for name, t in con.execute("select ZFILENAME, datetime(ZDATECREATED+978307200,'unixepoch','localtime') "
                               "from ZASSET where ZDATECREATED is not null"):
        PHOTOS_DB[name] = datetime.fromisoformat(t)


def shot_time(p: Path):
    return (exif_time(p) or PHOTOS_DB.get(p.name) or name_time(p.name)
            or datetime.fromtimestamp(p.stat().st_mtime))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("lib")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--photos-db", help="从 iPhone 拉下来的 /PhotoData/Photos.sqlite")
    a = ap.parse_args()
    if a.photos_db:
        load_photos_db(a.photos_db)
    src, lib = Path(a.src).expanduser(), Path(a.lib).expanduser()
    stats = Counter()
    for p in sorted(src.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in MEDIA:
            continue
        t = shot_time(p)
        dst = lib / t.strftime("%Y-%m") / (t.strftime("%Y_%m_%d_%H_%M_%S_") + p.name)
        if dst.exists() and dst.stat().st_size == p.stat().st_size:
            stats["已存在跳过"] += 1
            continue
        stats[t.strftime("%Y-%m")] += 1
        if a.apply:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)
    for k, v in sorted(stats.items()):
        print(k, v)
    print("已复制" if a.apply else "（预览，加 --apply 才复制）", sum(v for k, v in stats.items() if k != "已存在跳过"))


if __name__ == "__main__":
    main()
