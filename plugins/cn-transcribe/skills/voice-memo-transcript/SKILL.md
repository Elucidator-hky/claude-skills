---
name: voice-memo-transcript
description: 把 iPhone 语音备忘录（经 iCloud 同步到 Mac）的录音转成尽可能准确的文字全文（转写后自动校对修错，默认不做总结分析）。用户说"看一下最新的录音 / 我刚录了一段 / 把录音转成文字 / 手机录音里那条XX"时使用。视频链接转写走 video-transcript。
---

# 手机录音 → 文字（自动区分说话人）

## 1. 找录音

```bash
ls ~/Library/Group\ Containers/group.com.apple.VoiceMemos.shared/Recordings/ | grep -E '\.(m4a|qta)$' | sort | tail -5
```

文件名即录音时间 `YYYYMMDD HHMMSS-xxx`。两个坑：

- 新录音是 **`.qta`** 格式，`.m4a` 和 `.qta` 都要搜
- **按文件名排序**，iCloud 会乱改 mtime，`ls -t` 的顺序不可信

终端读这个目录需要「完全磁盘访问权限」，报 `Operation not permitted` 就让用户在系统设置里给终端开权限。

把录音时间报给用户确认。用户说"刚录的"但对不上 = iCloud 没同步：`open -a VoiceMemos`，等 30 秒重查。

次要来源：`~/Library/Mobile Documents/com~apple~CloudDocs/Downloads/`（用户说"存到 iCloud 了"时找这里）。

## 2. 转写

```bash
mkdir -p ~/Documents/录音转写
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/transcribe.py "<录音绝对路径>" \
  -o ~/Documents/录音转写/<YYYYMMDD-HHMMSS>.md \
  --context "<主题/人名/术语，没有就空字符串>" \
  --speakers <人数，不确定就省略这行>
```

- 输出 `**[说话人0]** 00:01:23` 分段的对话稿；26 分钟录音约 1 分钟转完
- `--context` 明显提升专有名词准确率，用户提过主题就带上
- 多人录音带 `--speakers` 聚类更准
- 说话人叫 `说话人0/1/2`，映射真名靠内容判断（谁在提问、谁在自我介绍）

原理：`paraformer-v2` 出说话人时间轴 → 按时间轴切段 → 每段喂 `qwen3-asr-flash` 出准确文字。**两个模型配合使用**：单跑 paraformer 术语错得多，单跑 qwen3-asr 没有说话人。

需要 `ffmpeg`、`pip install dashscope`、环境变量 `DASHSCOPE_API_KEY`（阿里云百炼）。脚本内已强制直连，代理环境下也能跑。

## 3. 校对修错（必做）

读转写 md，逐段修 ASR 错误：同音错别字、专有名词（结合上下文和领域）、断句标点、明显语序混乱。**只修错，说话内容和口语原样保留**。同时根据内容推测说话人身份（谁在提问、谁自我介绍、谁被称呼名字），把「说话人0/1」替换成推测的身份（如「面试官」「候选人」），拿不准就保留编号并注一行推测。修完覆写同一个 md。

**固定场景（例会、常见同事）建一份对照表**：在本 skill 目录下新建 `glossary.md`，记两类内容——

- 人物：称呼、身份、识别线索（说话风格、常讲的话题）
- 稳定错词：ASR 总是错成什么 → 应该是什么（人名、产品名、行业术语）

ASR 对同一批专有名词错得很稳定，有了对照表校对时直接归一，也可以把人名和术语拼进 `--context`。每次校对发现新的稳定错词就追加进去。

**另一类幻觉必须整行删掉**：`qwen3-asr-flash` 在没有人声的片段会把 `--context` 里的提示词原样吐出来，混在正文里像有人在念术语表。删时连同上面那行说话人标注一起删。

## 4. 交付

默认只给「修订后的准确全文」+ 文件绝对路径。用户明确要求了才做总结和分析。
