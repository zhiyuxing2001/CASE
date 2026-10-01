#!/usr/bin/env python3
"""Extract scanned pages from a PDF and OCR them with macOS Vision.

Most clinical case PDFs in this project are pure scans without a text
layer. Rather than rendering the PDF, we pull the embedded page images
directly, which is faster and lossless.

For each page the largest embedded image is kept (small images are
usually header logos), then OCR'd via macOS Vision through `ocrmac`,
which returns per-line text, confidence and bounding boxes.

Usage:
    python tools/pdf_ocr_extract.py INPUT.pdf OUTPUT_DIR

Outputs, all under OUTPUT_DIR:
    pages/<pdf-stem>-p01.png ...   extracted page images
    <pdf-stem>.txt                 plain OCR text with page markers
    <pdf-stem>.jsonl               one JSON record per OCR line
    <pdf-stem>.vision.json         full Vision payload incl. bboxes
"""

from __future__ import annotations

import json
import pathlib
import sys

from pypdf import PdfReader
from ocrmac import ocrmac

MIN_PIXELS = 200_000  # ignore anything smaller; those are logos/rules
LANGS = ["zh-Hans", "en-US"]


def extract_pages(pdf_path: pathlib.Path, out_dir: pathlib.Path) -> list[pathlib.Path]:
    """Save the largest embedded image of every page as a PNG."""
    reader = PdfReader(str(pdf_path))
    pages_dir = out_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    saved: list[pathlib.Path] = []
    for index, page in enumerate(reader.pages, start=1):
        best = None
        for image in page.images:
            pil = image.image
            if pil.width * pil.height < MIN_PIXELS:
                continue
            if best is None or pil.width * pil.height > best.width * best.height:
                best = pil
        if best is None:
            print(f"  page {index}: no usable image, skipped", file=sys.stderr)
            continue
        target = pages_dir / f"{pdf_path.stem}-p{index:02d}.png"
        if best.mode not in ("RGB", "L"):
            best = best.convert("RGB")
        best.save(target)
        saved.append(target)
        print(f"  page {index}: {best.width}x{best.height} -> {target.name}")
    return saved


def ocr_pages(pages: list[pathlib.Path]) -> list[dict]:
    """Run macOS Vision on every page image."""
    results = []
    for page in pages:
        lines = ocrmac.OCR(str(page), language_preference=LANGS).recognize()
        records = [
            {
                "page": page.name,
                "text": text,
                "confidence": round(float(confidence), 4),
                # Vision bbox is normalised, origin bottom-left
                "bbox": [round(float(v), 4) for v in box],
            }
            for text, confidence, box in lines
        ]
        results.append({"page": page.name, "lines": records})
        print(f"  OCR {page.name}: {len(records)} lines")
    return results


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2

    pdf_path = pathlib.Path(sys.argv[1]).expanduser().resolve()
    out_dir = pathlib.Path(sys.argv[2]).expanduser().resolve()
    if not pdf_path.is_file():
        print(f"error: no such file: {pdf_path}", file=sys.stderr)
        return 1
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"PDF : {pdf_path.name}")
    print(f"OUT : {out_dir}")
    pages = extract_pages(pdf_path, out_dir)
    if not pages:
        print("error: no page images extracted", file=sys.stderr)
        return 1

    results = ocr_pages(pages)

    stem = pdf_path.stem
    (out_dir / f"{stem}.vision.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    with (out_dir / f"{stem}.jsonl").open("w", encoding="utf-8") as fh:
        for page in results:
            for line in page["lines"]:
                fh.write(json.dumps(line, ensure_ascii=False) + "\n")

    with (out_dir / f"{stem}.txt").open("w", encoding="utf-8") as fh:
        for page in results:
            fh.write(f"\n{'=' * 70}\n### {page['page']}\n{'=' * 70}\n")
            for line in page["lines"]:
                fh.write(f"[{line['confidence']:.2f}] {line['text']}\n")

    print(f"\nwritten: {stem}.txt / .jsonl / .vision.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
