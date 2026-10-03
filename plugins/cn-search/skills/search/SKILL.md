---
name: search
description: 要联网查任何信息时按这个流程走。① 内置 WebSearch 打底，总是跑；② 同时按需并发这些免费通道——zhihu 国内亲历经验和行业观点 · ghsearch 找开源实现 · asearch 追最新论文 · hsearch 某工具值不值得用 · context7 库框架文档 · WebFetch 读已知网址；③ 还缺中国信息才补 osearch（中国全网搜索，付费），不够再 bsearch。读正文拿各命令的 flag 和踩过的坑。
---

# 各通道用法和坑

流程见上面的 description。所有命令的 **flag 必须写在 query 前面**。

下文的命令都是本 skill 自带脚本，调用时写全路径：

| 命令 | 实际调用 | 需要 |
|---|---|---|
| `osearch` | `${CLAUDE_SKILL_DIR}/scripts/osearch.sh` | `ALIYUN_OPENSEARCH_API_KEY` + `ALIYUN_OPENSEARCH_ENDPOINT` |
| `bsearch` | `${CLAUDE_SKILL_DIR}/scripts/bsearch.sh` | `BOCHA_API_KEY` |
| `gsearch` | `${CLAUDE_SKILL_DIR}/scripts/gsearch.sh` | `SERPER_API_KEY`，国内网络加 `SEARCH_PROXY` |
| `ghsearch` | `${CLAUDE_SKILL_DIR}/scripts/ghsearch.sh` | 已登录的 `gh` |
| `asearch` | `${CLAUDE_SKILL_DIR}/scripts/asearch.py` | 无 |
| `hsearch` | `${CLAUDE_SKILL_DIR}/scripts/hsearch.py` | 无 |

`zhihu` 是知乎官方 CLI，另行安装；`context7`、`github` 是 MCP，另行配置。缺哪个就跳过哪个通道。

## 内置 WebSearch

US-only，抓不到国内站。但方法论共通——"外贸怎么开发客户"这类先内置就够，国内通道只是补实操差异。**提问是中文也照样先跑它。** 限定域名用 `allowed_domains` 参数，等价于 `site:`。

## zhihu —— 官方 CLI，免费 5000 次/天

```bash
zhihu search zhihu --query "..." --count 3   # 知乎站内，返回全文
zhihu search global --query "..."            # 全网，可按站点和时间筛
zhihu hot                                    # 热榜
zhihu quota                                  # 查剩余额度
```

**返回完整正文不是摘要**，一条就可能上千 token，`--count` 给 3~5 足够。返回 JSON 字段名**大写开头**（`Data`/`Items`/`Title`/`Url`/`ContentText`），写解析脚本时按大写取。

`osearch`/`bsearch` 都索引不到知乎，要知乎内容只能走这里。`zhihu auth status --verify` 查登录状态。

## ghsearch + github MCP —— 接力，不是二选一

```bash
ghsearch -c -l go "xxx"     # 搜代码，给匹配片段 + 文件行链接（最有价值的模式）
ghsearch -i "报错原文"       # 搜 issue，词太窄会 0 结果，放宽再试
ghsearch -s -k 20 "..."     # 按 star 排序
```

**`ghsearch` 扫候选**（输出压缩成三行一条，扫二十个仓库也不涨多少 context）→ **`github` MCP 读实现**（`get_file_contents` 直接拿文件，不用拼 `gh api` 再解 base64）。初筛用 `ghsearch`，MCP 拉 schema 有开销，留给读实现；手里只有链接时也用 MCP 读，GitHub 页面用 `WebFetch` 抓效果差。

⚠️ **查"某个工具/产品是否存在"先用内置或 osearch**：GitHub 只有社区实现，看不见官方产品。实测查"知乎有没有 CLI"，`ghsearch` 只找到 16 star 的第三方平替，而 `osearch` 和内置都直接命中知乎官方 CLI。**先确认官方有没有做，再去 GitHub 找替代品。**

## asearch —— arXiv，免费

```bash
asearch -n -c cs.CL -k 5 "..."   # -n 按最新 · -c 限分类 · -e 精确短语
```

要**按发表时间取最新**只能用它，内置排不了序。想了解一个方向的全貌用内置，它给综述。

⚠️ **每 3 秒最多一次**，连打会被 arXiv 按 IP 封几十分钟（届时所有查询一律 429，包括刚成功过的）。脚本自带节流，单次调用即可，循环里调用会触发封禁。

## hsearch —— Hacker News，免费

```bash
hsearch -p 200 "..."    # 只看 200 分以上高热帖
hsearch -c "..."        # 搜评论找真实吐槽，词太窄会 0 结果
```

## WebFetch —— 分界是要不要登录，不是国内外

能读 `gov.cn`／CSDN／博客园／腾讯云／百家号／企业官网；知乎 403 走 `zhihu` CLI，大众点评和小红书要登录、读不到。

搜索结果里 `m.` 开头的手机版会 301，**直接换桌面版 URL**，省一次往返。

目标站上了 Cloudflare（`Just a moment...`）才用 playwright MCP，慢，最后才用。

## osearch / bsearch —— 付费，中国全网

```bash
osearch -k 10 "..."              # -s 大模型摘要（慢但整理过）· -j 原始 JSON
bsearch -k 20 -f oneWeek "..."   # 时间过滤 noLimit/oneYear/oneMonth/oneWeek/oneDay
```

**`bsearch` 只当补漏**：五组同题对照，近两年内容占比 `osearch` 95% / `bsearch` 61%；查社保 `osearch` 给 `gov.cn`，`bsearch` 给二手解读站。它的价值是站点池不同（命中过 BOSS 直聘、1688、慧博研报）。

⚠️ **英文关键词用内置或 gsearch**：中文引擎搜英文公司名会返回完全无关的结果（搜印度农机经销商返回过 NVIDIA 显卡）。

⚠️ **付费 key 会静默失效**：`bsearch` 403 = 博查余额用完（open.bochaai.com 买资源包）。怀疑哪个通道死了，逐个跑 `-k 1 "测试"` 探活。

## gsearch —— 备用

能力内置全覆盖，只在内置报错时顶上。`-m` 查海外商户（店名/地址/评分/电话），`-a` 查 Google Scholar（带被引数，覆盖非 arXiv 期刊）。

## 通用

- **LLM 综合用真实结果喂**：先用上面通道拿到真实结果再让模型总结。千问的 `enable_search` 会编造 URL。
- **验证代理用真实命令**：curl 的代理变量规则和别的工具不一样，拿它验会给假阳性。
