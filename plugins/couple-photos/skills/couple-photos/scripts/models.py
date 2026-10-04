"""人脸模型路径：首次使用时从 opencv_zoo 下载到 ~/.cache/couple-photos/models（可用 COUPLE_PHOTOS_MODELS 覆盖）。"""
from __future__ import annotations
import os, urllib.request
from pathlib import Path

BASE = "https://github.com/opencv/opencv_zoo/raw/main/models"
FILES = {
    "face_detection_yunet_2023mar.onnx": f"{BASE}/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "face_recognition_sface_2021dec.onnx": f"{BASE}/face_recognition_sface/face_recognition_sface_2021dec.onnx",
}


def paths() -> tuple[str, str]:
    d = Path(os.environ.get("COUPLE_PHOTOS_MODELS", "~/.cache/couple-photos/models")).expanduser()
    d.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        f = d / name
        if not f.exists() or f.stat().st_size < 100_000:
            print(f"下载模型 {name} ...", flush=True)
            tmp = f.with_suffix(".part")
            urllib.request.urlretrieve(url, tmp)
            tmp.rename(f)
    return str(d / "face_detection_yunet_2023mar.onnx"), str(d / "face_recognition_sface_2021dec.onnx")
