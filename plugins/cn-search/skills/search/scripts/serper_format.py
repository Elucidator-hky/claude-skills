#!/usr/bin/env python3
"""格式化 Serper API 返回：网页结果 / 地图商户 / 新闻 / 学术"""
import json
import sys


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "search"
    # news 端点会无视小 num 一律回 10 条，这里按用户要的条数统一截断
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit("返回内容不是 JSON（多半是 key 无效或网络不通）")

    if "message" in data and not any(k in data for k in ("organic", "places", "news")):
        sys.exit(f"API 报错: {data['message']}")

    if mode == "news":
        items = data.get("news", [])[:limit]
        if not items:
            print("无新闻结果")
            return
        for i, n in enumerate(items, 1):
            meta = "  ·  ".join(x for x in (n.get("source"), n.get("date")) if x)
            print(f"### {i}. {n.get('title', '?')}")
            if meta:
                print(f"  {meta}")
            print(n.get("link", ""))
            if n.get("snippet"):
                print(f"\n{n['snippet']}")
            print()
        return

    if mode == "scholar":
        items = data.get("organic", [])[:limit]
        if not items:
            print("无学术结果")
            return
        for i, p in enumerate(items, 1):
            print(f"### {i}. {p.get('title', '?')}")
            bits = []
            if p.get("year"):
                bits.append(str(p["year"]))
            if p.get("citedBy"):
                bits.append(f"被引 {p['citedBy']}")
            if bits:
                print("  " + "  ·  ".join(bits))
            if p.get("publicationInfo"):
                print(f"  {p['publicationInfo']}")
            print(p.get("link", ""))
            if p.get("pdfUrl"):
                print(f"  PDF: {p['pdfUrl']}")
            if p.get("snippet"):
                print(f"\n{p['snippet']}")
            print()
        return

    if mode == "places":
        places = data.get("places", [])[:limit]
        if not places:
            print("无商户结果 —— 该公司在 Google 地图上查不到实体店")
            return
        for i, p in enumerate(places, 1):
            print(f"### {i}. {p.get('title', '?')}")
            bits = []
            if p.get("category"):
                bits.append(p["category"])
            if p.get("rating"):
                bits.append(f"{p['rating']}★ ({p.get('ratingCount', 0)} 条评价)")
            if bits:
                print("  " + "  ·  ".join(bits))
            for label, key in [("地址", "address"), ("电话", "phoneNumber"), ("官网", "website")]:
                if p.get(key):
                    print(f"  {label}: {p[key]}")
            if not p.get("website"):
                print("  官网: 未登记")
            print()
        return

    # 网页搜索
    if data.get("answerBox", {}).get("answer"):
        print(f"【直接答案】{data['answerBox']['answer']}\n")
    kg = data.get("knowledgeGraph")
    if kg:
        print(f"【知识图谱】{kg.get('title', '')} — {kg.get('type', '')}")
        for k, v in (kg.get("attributes") or {}).items():
            print(f"  {k}: {v}")
        if kg.get("website"):
            print(f"  官网: {kg['website']}")
        print()

    results = data.get("organic", [])[:limit]
    if not results:
        print("无结果")
        return
    for i, r in enumerate(results, 1):
        head = f"### {i}. {r.get('title', '?')}"
        if r.get("date"):
            head += f"  ·  {r['date']}"
        print(head)
        print(r.get("link", ""))
        if r.get("snippet"):
            print(f"\n{r['snippet']}")
        print()


if __name__ == "__main__":
    main()
