"""
postprocessing.py
-----------------
Cleans and filters raw PaddleOCR output before returning it to the caller.

Steps:
  1. Strip leading/trailing whitespace from each recognised text string.
  2. Drop results whose confidence score is below MIN_CONFIDENCE.
  3. Remove exact duplicates (same text + identical bounding box).
  4. Convert raw polygon arrays to plain Python lists for JSON serialisation.
  5. Assemble the structured OCRTextResult list and full_text string.
"""

from __future__ import annotations

import logging
from typing import List

import numpy as np

from ocr_module.config import MIN_CONFIDENCE, STRIP_WHITESPACE
from ocr_module.models import OCRTextResult

logger = logging.getLogger(__name__)


def postprocess(
    rec_texts:  List[str],
    rec_scores: List[float],
    rec_polys:  List[np.ndarray],
    min_confidence: float = MIN_CONFIDENCE,
) -> tuple[List[OCRTextResult], str]:
    """
    Filter and clean raw PaddleOCR results.

    Parameters
    ----------
    rec_texts  : list of recognised text strings
    rec_scores : list of float confidence values (one per text)
    rec_polys  : list of ndarray shape (4, 2) bounding-box polygons
    min_confidence : minimum confidence threshold

    Returns
    -------
    results   : list of OCRTextResult objects
    full_text : all accepted texts joined with spaces
    """
    results: List[OCRTextResult] = []
    seen: set[tuple] = set()   # for duplicate removal

    for text, score, poly in zip(rec_texts, rec_scores, rec_polys):
        # 1. Strip whitespace
        if STRIP_WHITESPACE:
            text = text.strip()

        # 2. Skip empty strings
        if not text:
            logger.debug("Skipping empty text at score=%.4f", score)
            continue

        # 3. Confidence filter
        if score < min_confidence:
            logger.debug("Dropped low-confidence result: '%s' (%.4f < %.4f)",
                         text, score, min_confidence)
            continue

        # 4. Polygon -> plain Python list of [x, y] pairs
        bbox = poly.tolist()   # list of 4 [x, y] points

        # 5. Duplicate removal (same text + same first corner)
        key = (text, tuple(bbox[0]))
        if key in seen:
            logger.debug("Duplicate removed: '%s'", text)
            continue
        seen.add(key)

        results.append(OCRTextResult(
            text=text,
            confidence=round(float(score), 6),
            bounding_box=bbox,
        ))

    full_text = " ".join(r.text for r in results)
    logger.debug("Post-processing: %d results retained, full_text=%r",
                 len(results), full_text[:80])
    return results, full_text
