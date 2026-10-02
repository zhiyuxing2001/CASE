"""OCR 通道 A：macOS Vision 本地识别。

离线、免费、毫秒级，逐行返回文本、置信度与归一化坐标框。
坐标框是"双通道"与"字段溯源"的基础，因此原样保留 Vision 输出。
"""

from __future__ import annotations

from typing import Any

from ocrmac import ocrmac

LANGS = ["zh-Hans", "en-US"]


def run_vision(image_path: str) -> list[dict[str, Any]]:
    """对一张图片执行 macOS Vision 识别。

    返回逐行 ``[{text, confidence, bbox}]``。
    bbox 为 Vision 的归一化坐标 ``[x, y, w, h]``，**原点在左下角**。
    """
    lines = ocrmac.OCR(image_path, language_preference=LANGS).recognize()
    return [
        {
            "text": text,
            "confidence": round(float(confidence), 4),
            "bbox": [round(float(v), 4) for v in box],
        }
        for text, confidence, box in lines
    ]


def lines_to_display(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """把 Vision 的 bbox 转换为屏幕坐标（原点左上角），供前端叠加显示。"""
    result = []
    for line in lines:
        x, y, w, h = line["bbox"]
        result.append({
            "text": line["text"],
            "confidence": line["confidence"],
            # Vision y 自下而上，屏幕 y 自上而下：y_display = 1 - y - h
            "bbox": [round(x, 4), round(1 - y - h, 4), round(w, 4), round(h, 4)],
        })
    return result
