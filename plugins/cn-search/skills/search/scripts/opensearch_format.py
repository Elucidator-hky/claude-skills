#!/usr/bin/env python3
"""格式化 OpenSearch 返回的 JSON 为 Markdown — stdin 读 JSON，stdout 输出格式化结果"""
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

    code = d.get("code") or d.get("Code")
    if code and str(code).lower() not in ("success", "0"):
        print(f"API error code={code}", file=sys.stderr)
        print(json.dumps(d, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1

    results = (d.get("result") or {}).get("search_result") or []
    if not results:
        print("（无结果）")
        print(json.dumps(d, ensure_ascii=False, indent=2)[:500], file=sys.stderr)
        return 0

    for i, r in enumerate(results, 1):
        title = r.get("title") or "(无标题)"
        link = r.get("link") or r.get("url") or ""
        snip = r.get("snippet") or r.get("content") or ""
        snip = re.sub(r"\s+", " ", snip).strip()[:400]
        pub = (r.get("meta_info") or {}).get("publishedTime") or ""
        pub_tag = f"  · {pub[:10]}" if pub else ""
        print(f"### {i}. {title}{pub_tag}")
        print(link)
        print()
        print(snip)
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
