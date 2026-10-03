#!/usr/bin/env python3
"""音频 → 带说话人分离的高精度转写（融合方案）

paraformer-v2 出说话人时间轴（扔掉它的文字）
  → 按时间轴切段 → qwen3-asr-flash + context 逐段转写（高准确率）
  → 拼回带说话人标注的 markdown

用法:
  transcribe.py <音视频> [-o 输出.md] [--context "背景/术语"] [--speakers N] [--jobs 8]
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from concurrent.futures import ThreadPoolExecutor

for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
    os.environ.pop(k, None)
os.environ["NO_PROXY"] = os.environ["no_proxy"] = "*"

import dashscope  # noqa: E402
from dashscope.audio.asr import Transcription  # noqa: E402
from dashscope.utils.oss_utils import OssUtils  # noqa: E402

MIN_SEG_MS = 1200  # 短于此的块不值得单独调 ASR，直接用 paraformer 的文字


def load_key() -> str:
    key = os.environ.get("DASHSCOPE_API_KEY")
    if key:
        return key
    sys.exit("找不到环境变量 DASHSCOPE_API_KEY（阿里云百炼控制台申请）")


def fmt_ts(ms: int) -> str:
    s = ms // 1000
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def get_diarization(mp3: str, key: str, speakers: int) -> list:
    """跑 paraformer-v2，返回 sentences（含 speaker_id / begin_time / end_time）。"""
    ret = OssUtils.upload(model="paraformer-v2", file_path=mp3, api_key=key)
    url = ret[0] if isinstance(ret, tuple) else ret
    kw = {"speaker_count": speakers} if speakers else {}
    task = Transcription.async_call(
        model="paraformer-v2", file_urls=[url], language_hints=["zh"],
        diarization_enabled=True,
        headers={"X-DashScope-OssResourceResolve": "enable"}, **kw,
    )
    resp = Transcription.wait(task=task.output.task_id)
    results = resp.output.get("results", [])
    if not results or not results[0].get("transcription_url"):
        sys.exit(f"说话人分离失败: {json.dumps(resp.output, ensure_ascii=False)[:400]}")
    data = json.loads(urllib.request.urlopen(results[0]["transcription_url"]).read())
    return [s for tr in data.get("transcripts", []) for s in tr.get("sentences", [])]


def asr_segment(job, key: str, context: str, retries: int = 3) -> str:
    """切出一段音频调 qwen3-asr-flash。job = (idx, wav_path, fallback_text)"""
    idx, path, fallback = job
    for attempt in range(retries):
        try:
            resp = dashscope.MultiModalConversation.call(
                api_key=key, model="qwen3-asr-flash",
                messages=[{"role": "system", "content": [{"text": context}]},
                          {"role": "user", "content": [{"audio": f"file://{path}"}]}],
                result_format="message",
                asr_options={"language": "zh", "enable_itn": True},
            )
            content = resp.output.choices[0].message.content
            text = content[0].get("text", "") if content else ""
            return text.strip() or fallback
        except Exception:
            if attempt == retries - 1:
                return fallback
    return fallback


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("-o", "--output")
    ap.add_argument("--context", default="", help="背景/术语提示，显著提升专有名词准确率")
    ap.add_argument("--speakers", type=int, default=0, help="已知人数则填（2-100）")
    ap.add_argument("--jobs", type=int, default=8)
    args = ap.parse_args()

    src = os.path.abspath(args.input)
    if not os.path.exists(src):
        sys.exit(f"文件不存在: {src}")
    out = args.output or os.path.splitext(src)[0] + ".md"
    key = load_key()
    dashscope.api_key = key

    with tempfile.TemporaryDirectory(prefix="transcribe_") as wd:
        mp3 = os.path.join(wd, "full.mp3")
        print("转码中…", file=sys.stderr)
        subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vn", "-ac", "1",
                        "-ar", "16000", "-b:a", "64k", mp3], check=True)

        print("① 说话人分离（paraformer-v2）…", file=sys.stderr)
        sents = get_diarization(mp3, key, args.speakers)

        # 合并连续的同一说话人 → 发言块
        blocks = []
        for s in sents:
            spk = s.get("speaker_id")
            if blocks and blocks[-1]["spk"] == spk:
                blocks[-1]["end"] = s["end_time"]
                blocks[-1]["fallback"] += s["text"]
            else:
                blocks.append({"spk": spk, "begin": s["begin_time"],
                               "end": s["end_time"], "fallback": s["text"]})
        n_spk = len({b["spk"] for b in blocks})
        print(f"   → {n_spk} 个说话人，{len(blocks)} 轮发言", file=sys.stderr)

        # 切段
        jobs, short = [], 0
        for i, b in enumerate(blocks):
            dur = b["end"] - b["begin"]
            if dur < MIN_SEG_MS:
                short += 1
                continue
            seg = os.path.join(wd, f"seg_{i:04d}.mp3")
            subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{b['begin']/1000:.2f}",
                            "-to", f"{b['end']/1000:.2f}", "-i", mp3, "-c", "copy", seg],
                           check=True)
            jobs.append((i, seg, b["fallback"]))

        print(f"② 逐段高精度转写（qwen3-asr-flash）{len(jobs)} 段，"
              f"{short} 段过短沿用原文…", file=sys.stderr)
        with ThreadPoolExecutor(max_workers=args.jobs) as ex:
            texts = list(ex.map(lambda j: asr_segment(j, key, args.context), jobs))
        for (i, _, _), t in zip(jobs, texts):
            blocks[i]["text"] = t

    lines = [f"# 转写: {os.path.basename(src)}", "",
             f"> {n_spk} 个说话人，{len(blocks)} 轮发言"
             f"（说话人时间轴 paraformer-v2 + 文字 qwen3-asr-flash）", ""]
    for b in blocks:
        text = b.get("text") or b["fallback"]
        if not text.strip():
            continue
        lines.append(f"**[说话人{b['spk']}]** `{fmt_ts(b['begin'])}`")
        lines.append(text)
        lines.append("")

    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(out)


if __name__ == "__main__":
    main()
