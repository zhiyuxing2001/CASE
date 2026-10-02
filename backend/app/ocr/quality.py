"""图片质量闸门：模糊检测。

用拉普拉斯边缘方差的均值估计清晰度，低于阈值判定为模糊并提示重拍。
这是流水线最便宜的一道闸——在 OCR 之前拦住废图。
"""

from __future__ import annotations

from PIL import Image, ImageFilter, ImageStat

#: 边缘方差均值低于该值判为模糊（经验阈值，可在评测阶段校准）
BLUR_THRESHOLD = 45.0


def check_quality(image_path: str) -> dict:
    with Image.open(image_path) as img:
        gray = img.convert("L")
        edges = gray.filter(ImageFilter.FIND_EDGES)
        stat = ImageStat.Stat(edges)
        # stat.var 是每个通道的方差列表；灰度图单通道
        sharpness = round(float(stat.var[0]), 2)
        return {
            "width": img.width,
            "height": img.height,
            "sharpness": sharpness,
            "blurry": sharpness < BLUR_THRESHOLD,
        }
