# elucidator-skills

我日常把大量信息处理交给 Claude Code，这里是其中实测稳定、别人也用得上的 skill。每个都写了踩过的坑，照着用能少走弯路。

## 安装

```bash
claude plugin marketplace add Elucidator-hky/claude-skills
claude plugin install cn-search@elucidator-skills
claude plugin install cn-transcribe@elucidator-skills
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

### cn-transcribe — 中文视频和录音转逐字稿

两个 skill 共用一个转写脚本：先用阿里云 `paraformer-v2` 分出说话人时间轴，再按段喂 `qwen3-asr-flash` 出文字。中文专有名词准确率明显高于单模型。

- **video-transcript**：给视频链接或「某博主那条讲 XX 的视频」，拿到完整转写稿再回答问题。视频号分享页不给视频地址，skill 会刮作者和标题，去 B 站找同一条（自带 `find_video.py` 匹配），实在没有再引导手机录屏
- **voice-memo-transcript**：iPhone 语音备忘录经 iCloud 同步到 Mac 后，一句「看一下最新的录音」就转成带说话人的逐字稿，并自动校对错别字和专有名词

依赖：`ffmpeg`、`yt-dlp`、`pip install dashscope`，环境变量 `DASHSCOPE_API_KEY`（阿里云百炼）。视频号元数据用 playwright MCP 取，没配的话 skill 会直接问你作者和标题。

## 方法论

[docs/我怎么配置Claude.md](docs/我怎么配置Claude.md)：CLAUDE.md、环境手册、skill、memory 四层怎么分工，以及几个实测有用的小配置。

## License

MIT
