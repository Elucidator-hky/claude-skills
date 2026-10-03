#!/usr/bin/env python3
"""hsearch —— Hacker News 搜索（Algolia API，免费无 key）

Usage:  hsearch <query>              # 按热度（点赞数）排序，默认 10 条
        hsearch -k 20 <query>        # 条数 (1-100)
        hsearch -n <query>           # 按时间排序（找最新讨论）
        hsearch -c <query>           # 搜评论而非帖子（找真实吐槽/踩坑）
        hsearch -p 100 <query>       # 只看 100 分以上的高热帖
        hsearch -j <query>           # 原始 JSON

看海外技术圈对某个工具/公司的真实评价用这个：帖子给出讨论页链接，
点进去是几百条一线开发者的实战反馈，比官方文档和营销稿有用。
中文圈观点用 bsearch，代码实现用 ghsearch，论文用 asearch。
"""
import argparse
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://hn.algolia.com/api/v1"
ITEM_URL = "https://news.ycombinator.com/item?id={}"


def ago(ts):
    """unix 时间戳 → '3 天前' 这种相对时间"""
    if not ts:
        return ""
    delta = datetime.now(timezone.utc) - datetime.fromtimestamp(ts, timezone.utc)
    days = delta.days
    if days >= 365:
        return f"{days // 365} 年前"
    if days >= 30:
        return f"{days // 30} 个月前"
    if days >= 1:
        return f"{days} 天前"
    return f"{delta.seconds // 3600} 小时前"


def clean(text, limit=None):
    """HN 评论正文是 HTML 片段：先去标签，再把 &#x2F; 这类实体还原成字符"""
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = " ".join(html.unescape(text).split())
    if limit and len(text) > limit:
        text = text[: limit - 1] + "…"
    return text


def main():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("-k", "--limit", type=int, default=10)
    p.add_argument("-n", "--newest", action="store_true")
    p.add_argument("-c", "--comments", action="store_true")
    p.add_argument("-p", "--points", type=int, default=0)
    p.add_argument("-j", "--json", action="store_true")
    p.add_argument("-h", "--help", action="store_true")
    p.add_argument("terms", nargs="*")
    args = p.parse_args()

    if args.help or not args.terms:
        print(__doc__.strip())
        return 0 if args.help else 2

    params = {
        "query": " ".join(args.terms),
        "tags": "comment" if args.comments else "story",
        "hitsPerPage": max(1, min(args.limit, 100)),
    }
    if args.points:
        params["numericFilters"] = f"points>={args.points}"
    endpoint = "search_by_date" if args.newest else "search"
    url = f"{API}/{endpoint}?{urllib.parse.urlencode(params)}"

    try:
        data = json.load(urllib.request.urlopen(url, timeout=40))
    except Exception as e:
        print(f"ERROR: HN 请求失败 ({type(e).__name__}: {e})", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0

    hits = data.get("hits", [])
    if not hits:
        print("无结果")
        return 0

    print(f"共 {data.get('nbHits', 0)} 条，显示前 {len(hits)} 条\n")
    for i, h in enumerate(hits, 1):
        discuss = ITEM_URL.format(h.get("story_id") or h.get("objectID"))
        if args.comments:
            print(f"{i}. 【评论】{clean(h.get('story_title'), 90)}")
            print(f"   {h.get('author')} · {ago(h.get('created_at_i'))}")
            print(f"   {clean(h.get('comment_text'), 300)}")
            print(f"   {discuss}\n")
        else:
            meta = f"{h.get('points', 0)} 分 · {h.get('num_comments', 0)} 评论 · {ago(h.get('created_at_i'))}"
            print(f"{i}. {clean(h.get('title'), 110)}")
            print(f"   {meta}")
            if h.get("url"):
                print(f"   原文: {h['url']}")
            print(f"   讨论: {discuss}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
