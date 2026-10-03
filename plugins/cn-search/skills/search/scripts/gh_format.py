#!/usr/bin/env python3
"""把 gh search 的 JSON 输出格式化成人读的短列表。用法: gh_format.py <mode>"""
import json
import sys


def trunc(text, n):
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


def day(ts):
    return (ts or "")[:10]


def fmt_repos(rows):
    for i, r in enumerate(rows, 1):
        stars = r.get("stargazersCount", 0)
        star = f"{stars/1000:.1f}k" if stars >= 1000 else str(stars)
        meta = " · ".join(x for x in (f"★{star}", r.get("language"), day(r.get("updatedAt"))) if x)
        flag = " [已归档]" if r.get("isArchived") else ""
        print(f"{i}. {r.get('fullName')}{flag}")
        print(f"   {meta}")
        if r.get("description"):
            print(f"   {trunc(r['description'], 150)}")
        print(f"   {r.get('url')}\n")


def fmt_code(rows):
    for i, r in enumerate(rows, 1):
        repo = (r.get("repository") or {}).get("nameWithOwner", "")
        print(f"{i}. {repo} — {r.get('path')}")
        for m in (r.get("textMatches") or [])[:2]:
            frag = trunc(m.get("fragment", ""), 160)
            if frag:
                print(f"   | {frag}")
        print(f"   {r.get('url')}\n")


def fmt_issues(rows):
    for i, r in enumerate(rows, 1):
        repo = (r.get("repository") or {}).get("nameWithOwner", "")
        labels = ",".join(l.get("name", "") for l in (r.get("labels") or [])[:3])
        meta = " · ".join(x for x in (r.get("state"), day(r.get("createdAt")), labels) if x)
        print(f"{i}. [{meta}] {repo}#{r.get('number')}")
        print(f"   {trunc(r.get('title'), 150)}")
        print(f"   {r.get('url')}\n")


FORMATTERS = {"repos": fmt_repos, "code": fmt_code, "issues": fmt_issues, "prs": fmt_issues}

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "repos"
    try:
        rows = json.load(sys.stdin)
    except json.JSONDecodeError:
        print("解析失败（gh 可能返回了错误信息）", file=sys.stderr)
        sys.exit(1)
    if not rows:
        print("无结果")
        sys.exit(0)
    FORMATTERS.get(mode, fmt_repos)(rows)
