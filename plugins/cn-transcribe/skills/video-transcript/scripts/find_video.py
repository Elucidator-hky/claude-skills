#!/usr/bin/env python3
"""跨平台溯源：拿作者名 + 标题去 B 站找同一条视频。

用法:
  find_video.py --author "UP主昵称" --title "视频标题"
  find_video.py --title "关键词"                    # 只有标题时
  find_video.py --author "UP主昵称" --list          # 列出该作者被搜到的全部视频

输出: 命中的 bvid + 链接，按匹配度排序。没命中返回码 1。
"""
import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from difflib import SequenceMatcher

# B 站是国内服务，走代理反而会被风控挡（412）
for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
    os.environ.pop(k, None)

SEARCH_API = "https://api.bilibili.com/x/web-interface/wbi/search/type"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


def search(keyword: str) -> list[dict]:
    url = f"{SEARCH_API}?search_type=video&keyword={urllib.parse.quote(keyword)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://www.bilibili.com"})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=25) as resp:
            data = json.load(resp)
    except Exception as e:
        print(f"搜索失败: {e}", file=sys.stderr)
        return []
    if data.get("code") != 0:
        print(f"B站返回 code={data.get('code')} {data.get('message')}", file=sys.stderr)
        return []
    out = []
    for r in (data.get("data") or {}).get("result") or []:
        out.append({
            "title": re.sub(r"<[^>]+>", "", r.get("title", "")),
            "author": r.get("author", ""),
            "bvid": r.get("bvid", ""),
            "mid": r.get("mid"),
            "duration": r.get("duration", ""),
        })
    return out


def similarity(a: str, b: str) -> float:
    norm = lambda s: re.sub(r"[\s#，,。.！!？?、：:—\-_]+", "", s)
    return SequenceMatcher(None, norm(a), norm(b)).ratio()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--author", default="", help="作者/UP主昵称")
    ap.add_argument("--title", default="", help="视频标题")
    ap.add_argument("--list", action="store_true", help="列出该作者的全部命中结果")
    args = ap.parse_args()
    if not args.author and not args.title:
        sys.exit("至少要给 --author 或 --title")

    # 两路搜索取并集：标题命中率高，作者名用来兜住标题被改过的情况
    seen, pool = set(), []
    for kw in filter(None, [args.title, args.author]):
        for item in search(kw):
            if item["bvid"] not in seen:
                seen.add(item["bvid"])
                pool.append(item)

    scored = []
    for item in pool:
        score = 0.0
        if args.author and item["author"] == args.author:
            score += 1.0                                    # 作者精确命中，权重最高
        if args.title:
            score += similarity(args.title, item["title"])
        scored.append((score, item))
    scored.sort(key=lambda x: -x[0])

    if args.list and args.author:
        hits = [i for s, i in scored if i["author"] == args.author]
        for i in hits:
            print(f"{i['bvid']} | {i['duration']} | {i['title']}")
        sys.exit(0 if hits else 1)

    # 作者对上 + 标题像，或纯标题极像，才算命中
    strong = [(s, i) for s, i in scored if s >= 1.6 or (not args.author and s >= 0.85)]
    if not strong:
        print("未在 B 站找到同款视频", file=sys.stderr)
        if scored[:3]:
            print("最接近的几条（仅供参考，不要当成命中）:", file=sys.stderr)
            for s, i in scored[:3]:
                print(f"  {s:.2f} | {i['author']} | {i['title']} | {i['bvid']}", file=sys.stderr)
        sys.exit(1)

    for s, i in strong[:5]:
        print(f"匹配度 {s:.2f} | UP: {i['author']} | 时长 {i['duration']}")
        print(f"  {i['title']}")
        print(f"  https://www.bilibili.com/video/{i['bvid']}")


if __name__ == "__main__":
    main()
