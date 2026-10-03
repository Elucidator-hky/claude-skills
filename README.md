# elucidator-skills

我日常把大量信息处理交给 Claude Code，这里是其中实测稳定、别人也用得上的 skill。每个都写了踩过的坑，照着用能少走弯路。

## 安装

```bash
claude plugin marketplace add Elucidator-hky/claude-skills
claude plugin install cn-search@elucidator-skills
```

也可以把 `plugins/<插件>/skills/<skill>/` 整个目录拷进 `~/.claude/skills/` 直接用。

## 插件

### cn-search — 中英文多通道联网搜索

Claude 内置 WebSearch 只覆盖美国索引，国内站基本搜不到。这个 skill 规定了什么问题走哪个通道、哪些并发、哪些只当补漏，并附带 6 个命令行搜索脚本：

| 命令 | 来源 | 费用 |
|---|---|---|
| `ghsearch` | GitHub 仓库 / 代码 / issue（走 `gh` CLI） | 免费 |
| `asearch` | arXiv 论文 | 免费 |
| `hsearch` | Hacker News 帖子和评论 | 免费 |
| `osearch` | 阿里云 OpenSearch 联网搜索，中文首选 | 付费 |
| `bsearch` | 博查，中文补漏 | 付费 |
| `gsearch` | Serper（Google 网页 / 地图商户 / 学术） | 有免费额度 |

另外会用到知乎官方 CLI `zhihu`、`context7` 和 `github` MCP。没配的通道 skill 会跳过，只配免费的三个也能用。

**环境变量**（放进 `~/.zshrc` 或 `~/.claude/settings.json` 的 `env`）：

```bash
export ALIYUN_OPENSEARCH_API_KEY=...
export ALIYUN_OPENSEARCH_ENDPOINT=https://xxx.platform-cn-shanghai.opensearch.aliyuncs.com
export BOCHA_API_KEY=...
export SERPER_API_KEY=...
export SEARCH_PROXY=http://127.0.0.1:7890   # 国内网络访问 serper.dev 用
```

脚本需要 `zsh`、`python3`、`curl`，macOS 自带。

## License

MIT
