---
name: couple-photos
description: 从本机图库里把「我」和另一半（或任意两个人）的照片和视频挑出来，复制到 合照 / 只有我 / 只有她 / 待确认 四个文件夹；也负责把 iPhone、外接盘的照片按拍摄时间统一归档进一个本地图库。用户说「把我和老婆/女朋友的照片整理出来」「找出我们俩的合照」「做视频要我们的照片」「把手机照片导到电脑」「照片统一放一个地方」时使用。全程本地人脸识别（OpenCV YuNet + SFace），照片不上传。
---

# couple-photos

## 开工前问清楚

| 项 | 说明 |
|---|---|
| 图库目录 `<图库>` | 照片按 `YYYY-MM/YYYY_MM_DD_HH_MM_SS_原名` 存放（流程一产出的就是这个结构） |
| 输出目录 `<输出>` | 下面会建 `合照/只有我/只有她/待确认/视频` |
| 参考照目录 `<参考照>` | 几张两人都在、脸清楚的照片（婚纱照、合影最好） |
| 起始月份 | 可选，如两人认识的月份，用于 `--since YYYY-MM` |

脚本在 `${CLAUDE_SKILL_DIR}/scripts/`，工作目录 `<work>` 放 scratchpad。人脸模型首次运行时自动下载到 `~/.cache/couple-photos/models`。

## 流程一：新照片归档进图库

1. **iPhone**（`idevice_id -l` 能看到设备即可，`brew install libimobiledevice`）：afcclient 的子命令要从标准输入喂，命令行参数里的 `-r` 会被它自己吃掉。
   ```bash
   printf 'get -r /DCIM/105APPLE 105APPLE\nexit\n' | afcclient          # 每个 1xxAPPLE 一行
   printf 'get /PhotoData/Photos.sqlite Photos.sqlite\nget /PhotoData/Photos.sqlite-wal Photos.sqlite-wal\nget /PhotoData/Photos.sqlite-shm Photos.sqlite-shm\nexit\n' | afcclient
   ```
   先拉到图库**外**的临时目录，并一起拉 `Photos.sqlite`：微信保存图、截图等没有 EXIF，要靠它拿到真实时间。
2. 预览再复制：
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/archive.py <来源> <图库> --photos-db Photos.sqlite          # 预览
   python3 ${CLAUDE_SKILL_DIR}/scripts/archive.py <来源> <图库> --photos-db Photos.sqlite --apply
   ```
   预览里当前月份数量异常偏多，说明有文件退回到了文件修改时间，先查清楚再 apply。同名同大小自动跳过，可以重复跑。

## 流程二：挑出两人的照片

1. 扫描（约 15 分钟 / 6500 张），生成 `clusters.html` 认人页：
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/scan.py <图库> <work> --since YYYY-MM
   python3 ${CLAUDE_SKILL_DIR}/scripts/scan.py <参考照> <work_ref>
   ```
2. 用参考照的两个簇去比对图库的簇，列出候选：
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/match.py <work> <work_ref>
   ```
   打开 `<work>/clusters.html` 和 `<work_ref>/clusters.html` 给用户看。**谁是谁由用户指认**，Claude 只报簇号和数量。
3. 预览再复制（同一人被拆成几组就用逗号连起来）：
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/sort.py <work> <输出> --me <簇> --her <簇>          # 预览
   python3 ${CLAUDE_SKILL_DIR}/scripts/sort.py <work> <输出> --me <簇> --her <簇> --apply
   ```
   阈值：相似度 ≥ 0.42 算本人，0.33–0.42 进待确认。原图不动，只复制。
4. 视频：每个视频均匀抽 8 帧比对，跳过 Live Photo 附带的同名 .MOV，输出到 `<输出>/视频/`：
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/videos.py <图库> <work> <输出> --me <簇> --her <簇> --since YYYY-MM --apply
   ```

## 流程三：备份

外接盘是 exFAT 时用 `-rt`：
```bash
rsync -rt --modify-window=2 --exclude='.DS_Store' <图库>/ /Volumes/<外接盘>/Pictures/
```

## 环境

macOS，python3 + `pip install opencv-python numpy`（OpenCV ≥ 4.8）；HEIC 用系统自带 `sips` 转 jpg 缓存；视频时间用 `ffprobe`（`brew install ffmpeg`）。
