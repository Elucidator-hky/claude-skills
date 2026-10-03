#!/usr/bin/env python3
"""格式化博查 Bocha web-search 返回的 JSON 为 Markdown — stdin 读 JSON，stdout 输出。"""
import json
import re
import sys


def main() -> int:
    raw = sys.stdin.read()
    try:
        d = json.loads(raw, strict=False)
    except Exception as exc:
        print(f"JSON parse error: {exc}", file=sys.stderr)
        print(raw[:500], file=sys.stderr)
        return 1

    code = d.get("code")
    if code is not None and str(code) != "200":
        print(f"Bocha API error code={code}: {d.get('msg') or d.get('message') or ''}", file=sys.stderr)
        print(json.dumps(d, ensure_ascii=False)[:500], file=sys.stderr)
        return 1

    pages = ((d.get("data") or {}).get("webPages") or {}).get("value") or []
    if not pages:
        print("（无结果）")
        print(json.dumps(d, ensure_ascii=False)[:500], file=sys.stderr)
        return 0

    for i, it in enumerate(pages, 1):
        title = it.get("name") or "(无标题)"
        url = it.get("url") or ""
        summ = it.get("summary") or it.get("snippet") or ""
        summ = re.sub(r"\s+", " ", summ).strip()[:400]
        pub = (it.get("datePublished") or it.get("dateLastCrawled") or "")[:10]
        site = it.get("siteName") or ""
        tag = "  ·  ".join(x for x in [pub, site] if x)
        print(f"### {i}. {title}" + (f"  ·  {tag}" if tag else ""))
        print(url)
        print()
        print(summ)
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
