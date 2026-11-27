"""
image_utils.py
--------------
Utility functions for drawing OCR results onto images and saving outputs.

Public API
----------
draw_ocr_results(img, results)  -> annotated BGR ndarray
save_annotated_image(img, path) -> None
collect_images(directory)       -> list of Path objects
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

import cv2
import numpy as np

from ocr_module.config import (
    BBOX_COLOR, BBOX_THICKNESS,
    TEXT_COLOR, TEXT_FONT_SCALE, TEXT_FONT_THICK,
    SUPPORTED_EXTENSIONS,
)
from ocr_module.models import OCRTextResult

logger = logging.getLogger(__name__)


def draw_ocr_results(
    img: np.ndarray,
    results: List[OCRTextResult],
) -> np.ndarray:
    """
    Draw bounding boxes and text labels on a copy of *img*.

    Parameters
    ----------
    img     : BGR uint8 ndarray (the preprocessed or original image)
    results : list of OCRTextResult objects

    Returns
    -------
    annotated : new BGR ndarray with boxes and labels drawn
    """
    annotated = img.copy()

    for res in results:
        pts = np.array(res.bounding_box, dtype=np.int32).reshape((-1, 1, 2))

        # Draw polygon outline
        cv2.polylines(annotated, [pts], isClosed=True,
                      color=BBOX_COLOR, thickness=BBOX_THICKNESS)

        # Place label above the top-left corner
        x, y = res.bounding_box[0]
        label = f"{res.text}  ({res.confidence:.2f})"
        font  = cv2.FONT_HERSHEY_SIMPLEX

        # Dark background rectangle for readability
        (tw, th), baseline = cv2.getTextSize(label, font, TEXT_FONT_SCALE, TEXT_FONT_THICK)
        y_text = max(y - 4, th + 2)
        cv2.rectangle(
            annotated,
            (x, y_text - th - baseline - 2),
            (x + tw, y_text + baseline),
            (0, 0, 0), cv2.FILLED
        )
        cv2.putText(annotated, label, (x, y_text),
                    font, TEXT_FONT_SCALE, TEXT_COLOR, TEXT_FONT_THICK,
                    lineType=cv2.LINE_AA)

    return annotated


def save_annotated_image(img: np.ndarray, output_path: str | Path) -> None:
    """Write the annotated image to *output_path* (JPEG)."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    success = cv2.imwrite(str(output_path), img)
    if not success:
        raise IOError(f"cv2.imwrite failed for: {output_path}")
    logger.info("Annotated image saved: %s", output_path)


def collect_images(directory: str | Path) -> List[Path]:
    """
    Return a sorted list of all supported image files in *directory*.
    Does not recurse into subdirectories.
    """
    directory = Path(directory)
    if not directory.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    images = sorted(
        p for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    logger.info("Found %d images in %s", len(images), directory)
    return images
