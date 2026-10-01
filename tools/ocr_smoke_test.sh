set -x
cd "$(dirname "$0")"
python3 -m venv venv
./venv/bin/pip -q install --upgrade pip
./venv/bin/pip -q install ocrmac pillow 2>&1 | tail -5
./venv/bin/python - <<'PY'
from PIL import Image, ImageDraw, ImageFont
import os
# 造一张中文"处方"测试图，模拟手写体场景（先用印刷体验证链路）
img = Image.new("RGB", (900, 420), "white")
d = ImageDraw.Draw(img)
font = None
for p in ["/System/Library/Fonts/Supplemental/Songti.ttc",
          "/System/Library/Fonts/Hiragino Sans GB.ttc",
          "/System/Library/Fonts/PingFang.ttc"]:
    if os.path.exists(p):
        try:
            font = ImageFont.truetype(p, 30); break
        except Exception: pass
lines = [
 "中医门诊病历",
 "主诉：胃脘胀痛反复发作3月余。",
 "现病史：患者3月前无明显诱因出现胃脘胀痛，餐后加重。",
 "四诊：舌淡红，苔薄白，脉弦细。",
 "中医诊断：胃脘痛（肝胃不和证）",
 "治法：疏肝理气和胃",
 "处方：柴胡10g 白芍15g 枳壳10g 甘草6g",
 "      香附10g 陈皮10g 茯苓15g 白术12g",
 "用法：水煎服，日一剂，分早晚温服。7剂。",
]
y = 20
for ln in lines:
    d.text((25, y), ln, fill="black", font=font); y += 42
img.save("ocr_test_sample.png")
print("image saved")

from ocrmac import ocrmac
res = ocrmac.OCR("ocr_test_sample.png", language_preference=["zh-Hans","en-US"]).recognize()
print("=== macOS Vision OCR 结果 ===")
for text, conf, box in res:
    print(f"[{conf:.3f}] {text}")
PY
