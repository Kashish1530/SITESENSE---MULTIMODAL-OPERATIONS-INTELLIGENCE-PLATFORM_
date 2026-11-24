"""
main.py
-------
Entry point for the standalone OCR module.

Workflow
--------
1. Collect images from samples/input/ and dataset/ocr_data/Train/images/.
2. Initialise the OCREngine once (model loaded once, reused for all images).
3. Process every image: detect text, extract, save JSON + annotated image.
4. Print a summary table and save a dataset-level evaluation report.

Run
---
  cd E:\OCR_Module
  .\venv\Scripts\activate
  python main.py

Options (edit CONFIG block below or pass as env-vars in future):
  --input   : override input directory
  --output  : override output directory
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Make sure the project root is on sys.path regardless of where Python is run
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # project root
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ocr_module.config import (
    DATASET_TRAIN_DIR,
    MIN_CONFIDENCE,
    SAMPLES_INPUT_DIR,
    SAMPLES_OUTPUT_DIR,
)
from ocr_module.image_utils import collect_images
from ocr_module.ocr_engine import OCREngine

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Standalone PaddleOCR module")
    p.add_argument("--input",  default=None,
                   help="Input image directory (default: samples/input + dataset/Train)")
    p.add_argument("--output", default=None,
                   help="Output directory for JSON + annotated images")
    p.add_argument("--confidence", type=float, default=MIN_CONFIDENCE,
                   help=f"Minimum confidence threshold (default: {MIN_CONFIDENCE})")
    p.add_argument("--no-preprocess", action="store_true",
                   help="Skip image preprocessing")
    p.add_argument("--dataset-only", action="store_true",
                   help="Run only on the dataset Train images, not samples/input")
    return p.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = _parse_args()

    output_dir = Path(args.output) if args.output else SAMPLES_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # ---- Collect input images -------------------------------------------
    image_paths: list[Path] = []

    if args.input:
        # User-supplied directory
        custom = Path(args.input)
        if custom.is_dir():
            image_paths.extend(collect_images(custom))
        elif custom.is_file():
            image_paths.append(custom)
        else:
            logger.error("--input path does not exist: %s", custom)
            sys.exit(1)
    else:
        # 1. samples/input  (user-placed images)
        if SAMPLES_INPUT_DIR.is_dir():
            si = collect_images(SAMPLES_INPUT_DIR)
            if si:
                logger.info("Found %d images in samples/input", len(si))
                image_paths.extend(si)

        if not args.dataset_only:
            pass  # already handled above

        # 2. Dataset Train images (always included unless --input is set)
        if DATASET_TRAIN_DIR.is_dir():
            di = collect_images(DATASET_TRAIN_DIR)
            logger.info("Found %d images in dataset/Train", len(di))
            image_paths.extend(di)

    if not image_paths:
        logger.error(
            "No images found.\n"
            "  Place images in:  %s\n"
            "  or use:           python main.py --input <dir>",
            SAMPLES_INPUT_DIR,
        )
        sys.exit(1)

    logger.info("Total images to process: %d", len(image_paths))

    # ---- Initialise engine once -----------------------------------------
    engine = OCREngine(
        min_confidence=args.confidence,
        enable_preprocessing=not args.no_preprocess,
        output_dir=output_dir,
    )

    # ---- Process all images ---------------------------------------------
    responses = engine.process_batch(image_paths, save_outputs=True)

    # ---- Print summary table --------------------------------------------
    _print_summary(responses)

    # ---- Save evaluation report -----------------------------------------
    report_path = output_dir / "evaluation_report.json"
    _save_report(responses, report_path)
    logger.info("Evaluation report saved: %s", report_path)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _print_summary(responses) -> None:
    sep = "-" * 90
    print("\n" + sep)
    print(f"{'Image':<40}  {'Regions':>7}  {'Avg Conf':>9}  {'Time(ms)':>9}  Status")
    print(sep)
    for r in responses:
        status = "OK" if r.success else f"ERROR: {r.error or ''}"[:20]
        n = len(r.extracted_text)
        avg_conf = (
            sum(t.confidence for t in r.extracted_text) / n
            if n else 0.0
        )
        print(f"{r.image_name:<40}  {n:>7}  {avg_conf:>9.4f}  "
              f"{r.processing_time_ms:>9.1f}  {status}")
    print(sep)
    ok  = sum(1 for r in responses if r.success)
    err = len(responses) - ok
    print(f"\nTotal: {len(responses)}  OK: {ok}  Errors: {err}\n")


def _save_report(responses, path: Path) -> None:
    summary = []
    for r in responses:
        entry = {
            "image_name":        r.image_name,
            "success":           r.success,
            "num_regions":       len(r.extracted_text),
            "full_text":         r.full_text,
            "processing_time_ms": r.processing_time_ms,
            "error":             r.error,
            "avg_confidence": (
                round(
                    sum(t.confidence for t in r.extracted_text) / len(r.extracted_text),
                    4,
                )
                if r.extracted_text else 0.0
            ),
            "results": [
                {
                    "text":         t.text,
                    "confidence":   t.confidence,
                    "bounding_box": t.bounding_box,
                }
                for t in r.extracted_text
            ],
        }
        summary.append(entry)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
