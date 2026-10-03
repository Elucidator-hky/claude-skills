---
name: video-transcript
description: 拿到某条视频的完整文字内容并分析。用户给一个视频链接（微信视频号 weixin.qq.com/sph、B站、抖音、YouTube）或"某某博主那条讲XX的视频"，想知道里面讲了什么、要文案/转写稿/内容摘要时使用。核心是封闭平台（视频号）绕道开放平台取内容。
---

# 视频内容解析

**目标**：一条视频 → 完整转写稿 → 回答用户的问题。一次处理一条视频。

**主线**：能直接下就直接下；下不了（视频号）就**刮元数据去别的平台找同一条**；都找不到才让用户录屏。

## 第 1 步 判断来源

| 来源 | 走哪 |
|---|---|
| B站 / YouTube / 微博 等开放平台 | 跳到第 4 步，直接下 |
| **微信视频号**（`weixin.qq.com/sph/xxx` 或 `channels.weixin.qq.com/finder-preview/pages/sph?id=xxx`） | 第 2 步 |
| 只给了博主名 + 大概讲什么，没有链接 | 跳到第 3 步，直接搜 |

## 第 2 步 刮视频号元数据

**只要作者昵称 + 标题**，拿去第 3 步搜。

最快的办法是直接问用户"这条视频的博主叫什么、标题是什么"——用户在微信里看得见，一句话的事。

要自己刮就用 playwright MCP：

```
playwright: browser_navigate → https://channels.weixin.qq.com/finder-preview/pages/sph?id=<短链ID>
playwright: browser_evaluate → document.body.innerText
```

页面文字里就有作者和标题。要更多字段（`authorInfo.nickname`、`feedInfo.description` 标题+话题标签、`createtime`、`coverUrl`），用 `browser_network_requests(filter="get_feed_info")` 找到请求，再 `browser_network_request(index=N, part="response-body")` 读响应。

### ⚠️ 视频号直接取原片走不通（2026-08 实测）

1. **分享页不给视频地址**。`get_feed_info` 只返回作者、标题、点赞数、**封面图**，`videoUrl`/`decode_key` 一个都没有，页面上写着"可扫码前往微信观看此内容"，连 `<video>` 元素都不存在。
2. **网上流传的 `sph.litao.workers.dev` 解析服务已挂**（Cloudflare error 1042 / HTTP 404）。`ltaoo/wx_channels_download` 的主线其实是**本地 MITM 劫持微信客户端**（装根证书 + 改系统代理），不是这个 Worker。
3. **接口不能纯 curl**。`get_feed_info` 有签名校验，手动 POST 一律 `permission verification failed`，必须真浏览器跑 JS。

硬取视频号原片只剩 MITM 或录屏。**通常直接走第 3 步就够。**

## 第 3 步 跨平台溯源（核心）

博主基本都全网分发，B 站没有任何加密。

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/find_video.py --author "<博主昵称>" --title "<视频标题>"
```

命中打印 bvid + 链接（退出码 0）；没命中退出码 1，并列出最接近的几条**仅供参考**——匹配度低于阈值的当作没找到，去第 5 步。

`--list` 列出该作者在 B 站被搜到的全部视频（用户只记得"他那条讲 XX 的"时用来挑）。

B 站没有时，再试小红书（配了小红书 MCP 的话）、抖音。

## 第 4 步 下载音频

**只要音频**，比视频小一个数量级，转写效果一样。

```bash
cd <工作目录> && unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy && \
yt-dlp --proxy "" --cookies-from-browser chrome \
  -f bestaudio -o "<名字>.%(ext)s" --no-playlist "<视频链接>"
```

三个参数缺一不可：

- `unset` 代理 + `--proxy ""` —— B 站是国内服务，走代理直接 **HTTP 412 风控**
- `--cookies-from-browser chrome` —— 不带 cookie 同样 **412**（用户日常用哪个浏览器登录 B 站就填哪个）
- `-f bestaudio` —— 17 分钟视频只有 12MB，几秒下完

视频站反爬变化快，`yt-dlp` 保持最新版（`brew upgrade yt-dlp` 或 `pip install -U yt-dlp`）。

## 第 5 步 兜底：录屏

前面都没戏时告诉用户：

> 手机上打开视频 → 控制中心「屏幕录制」→ 播完停止 → AirDrop 给 Mac。

**手机录屏默认录的是系统内部声音**（不是麦克风），音质等于原声。加密保护的是文件传输和存储，保护不了已经播放出来的声音——这条路 100% 可行。

录屏在手机上做：macOS 抓系统内录音频要先装 BlackHole 虚拟声卡再配多输出设备，成本高得多。

## 第 6 步 转写

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/transcribe.py <音频文件> --context "<领域背景和专有名词>"
```

`--context` 从第 2 步刮到的标题和话题标签生成，显著提升专名准确率。例如标题带 `#企业AI落地 #FDE`，就写 `"AI行业内容，涉及 FDE（Forward Deployed Engineer）、企业AI落地、Palantir、大模型交付等术语"`。

输出同名 `.md`，带时间戳和说话人分段。需要环境变量 `DASHSCOPE_API_KEY` 和 `ffmpeg`。

## 第 7 步 分析

读转写稿，**回答用户实际问的问题**。用户没具体问就给结构化摘要：核心论点 → 关键论据和数据 → 有信息量的细节（原话金句、具体数字、方法论），口水话略过。

给文件绝对路径，方便用户自己打开核对。
