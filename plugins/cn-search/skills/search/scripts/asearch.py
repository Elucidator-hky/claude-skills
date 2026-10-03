#!/usr/bin/env python3
"""asearch —— arXiv 论文搜索（免费无 key，官方 API）

Usage:  asearch <query>                 # 按相关度，默认 10 条
        asearch -k 20 <query>           # 条数 (1-100)
        asearch -n <query>              # 按最新提交排序
        asearch -c cs.AI <query>        # 限分类
        asearch -e <query>              # 精确短语（默认是各词 AND）
        asearch -j <query>              # 原始 XML

比赛选型、AI 方法调研用这个；找代码实现用 ghsearch，找中文解读用 bsearch。
"""
import argparse
import os
import re
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

# 必须 https：解析返回用的是 stdlib ElementTree，明文传输会给中间人留注入 XML 的口子
API = "https://export.arxiv.org/api/query"
NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def build_query(terms, category, exact):
    words = " ".join(terms).strip()
    if exact:
        q = f'all:"{words}"'
    else:
        q = " AND ".join(f"all:{w}" for w in words.split())
    if category:
        q = f"({q}) AND cat:{category}"
    return q


def clean(text, limit=None):
    text = " ".join((text or "").split())
    if limit and len(text) > limit:
        text = text[: limit - 1] + "…"
    return text


MIN_INTERVAL = 3.0  # arXiv 官方要求：单连接、每 3 秒最多一次
STAMP = os.path.join(tempfile.gettempdir(), "arxiv-search-last-call")


def throttle():
    """跨进程节流：连着敲几次 asearch 会被 arXiv 按 IP 封几十分钟，这里主动补足间隔"""
    try:
        gap = time.time() - os.path.getmtime(STAMP)
        if 0 <= gap < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - gap)
    except OSError:
        pass
    try:
        with open(STAMP, "w"):
            pass
    except OSError:
        pass


def main():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("-k", "--limit", type=int, default=10)
    p.add_argument("-n", "--newest", action="store_true")
    p.add_argument("-c", "--category", default="")
    p.add_argument("-e", "--exact", action="store_true")
    p.add_argument("-j", "--json", action="store_true", help="原始 XML")
    p.add_argument("-h", "--help", action="store_true")
    p.add_argument("terms", nargs="*")
    args = p.parse_args()

    if args.help or not args.terms:
        print(__doc__.strip())
        return 0 if args.help else 2

    params = {
        "search_query": build_query(args.terms, args.category, args.exact),
        "start": 0,
        "max_results": max(1, min(args.limit, 100)),
        "sortBy": "submittedDate" if args.newest else "relevance",
        "sortOrder": "descending",
    }
    url = f"{API}?{urllib.parse.urlencode(params)}"
    throttle()
    try:
        raw = urllib.request.urlopen(url, timeout=40).read().decode("utf-8")
    except Exception as e:
        # arXiv 官方要求「单连接、3 秒一次」，连打十几次会被按 IP 掐断，
        # 表现就是所有查询（含刚才成功过的）一律 30 秒后 RemoteDisconnected
        print(f"ERROR: arXiv 请求失败 ({type(e).__name__}: {e})", file=sys.stderr)
        print("       连续查多次会被 arXiv 限流，隔几分钟再试；急用改走 gsearch -a", file=sys.stderr)
        return 1

    if args.json:
        print(raw)
        return 0

    entries = ET.fromstring(raw).findall("a:entry", NS)
    if not entries:
        print("无结果")
        return 0

    for i, e in enumerate(entries, 1):
        title = clean(e.findtext("a:title", "", NS))
        authors = [clean(a.findtext("a:name", "", NS)) for a in e.findall("a:author", NS)]
        who = ", ".join(authors[:3]) + (" 等" if len(authors) > 3 else "")
        date = e.findtext("a:published", "", NS)[:10]
        cat = e.find("arxiv:primary_category", NS)
        cat = cat.get("term") if cat is not None else ""
        abs_url = e.findtext("a:id", "", NS)
        arxiv_id = re.sub(r"^.*/abs/", "", abs_url)

        print(f"{i}. {title}")
        print(f"   {' · '.join(x for x in (cat, date, who) if x)}")
        print(f"   {clean(e.findtext('a:summary', '', NS), 220)}")
        print(f"   {abs_url}  |  PDF: https://arxiv.org/pdf/{arxiv_id}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
