"""
preprocessing.py
----------------
Image preprocessing pipeline executed before PaddleOCR inference.

Stages (each can be toggled via PreprocessConfig in config.py):
  1. Validate path (file exists, correct extension).
  2. Load image with OpenCV.
  3. Resize: cap long edge to max_dimension; ensure short edge >= min_dimension.
  4. Denoise: light Gaussian blur to suppress sensor noise.
  5. Contrast enhance: CLAHE on the L channel (LAB colour space).
  6. Sharpen: unsharp-mask to improve text edge definition.
  7. Grayscale (optional – off by default for colour labels).
  8. Threshold: Otsu binarisation (optional – off by default).

Returns a uint8 NumPy BGR array ready for PaddleOCR.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Tuple

import cv2
import numpy as np

from ocr_module.config import PREPROCESS, SUPPORTED_EXTENSIONS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def preprocess_image(
    image_path: str | Path,
    cfg=None,
) -> Tuple[np.ndarray, dict]:
    """
    Load and preprocess an image file.

    Parameters
    ----------
    image_path : path to the image file
    cfg        : PreprocessConfig instance (defaults to config.PREPROCESS)

    Returns
    -------
    img  : preprocessed BGR uint8 ndarray
    meta : dict with original shape, final shape, and applied steps
    """
    if cfg is None:
        cfg = PREPROCESS

    path = Path(image_path)
    _validate_path(path)

    img = _load_image(path)
    original_shape = img.shape[:2]  # (H, W)
    applied: list[str] = ["load"]

    img = _resize(img, cfg.max_dimension, cfg.min_dimension)
    applied.append("resize")

    if cfg.denoise:
        img = _denoise(img)
        applied.append("denoise")

    if cfg.enhance_contrast:
        img = _enhance_contrast(img)
        applied.append("contrast_enhance")

    if cfg.sharpen:
        img = _sharpen(img)
        applied.append("sharpen")

    if cfg.to_grayscale:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        applied.append("grayscale")

    if cfg.threshold:
        img = _threshold(img)
        applied.append("threshold")

    final_shape = img.shape[:2]
    meta = {
        "original_shape": original_shape,
        "final_shape":    final_shape,
        "steps_applied":  applied,
    }
    logger.debug("Preprocessing done: %s", meta)
    return img, meta


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _validate_path(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    if not path.is_file():
        raise ValueError(f"Path is not a file: {path}")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported extension '{path.suffix}'. "
            f"Supported: {sorted(SUPPORTED_EXTENSIONS)}"
        )


def _load_image(path: Path) -> np.ndarray:
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise IOError(
            f"OpenCV could not read the file: {path}. "
            "The file may be corrupt or not a valid image."
        )
    return img


# ---------------------------------------------------------------------------
# Processing steps
# ---------------------------------------------------------------------------

def _resize(img: np.ndarray, max_dim: int, min_dim: int) -> np.ndarray:
    h, w = img.shape[:2]
    long_edge  = max(h, w)
    short_edge = min(h, w)

    scale = 1.0
    if long_edge > max_dim:
        scale = max_dim / long_edge
    elif short_edge < min_dim and short_edge > 0:
        scale = min_dim / short_edge

    if scale != 1.0:
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))
        interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_LINEAR
        img = cv2.resize(img, (new_w, new_h), interpolation=interp)
        logger.debug("Resized (%d,%d) -> (%d,%d) scale=%.3f", h, w, new_h, new_w, scale)

    return img


def _denoise(img: np.ndarray) -> np.ndarray:
    """Light Gaussian blur to reduce high-frequency sensor noise."""
    return cv2.GaussianBlur(img, (3, 3), sigmaX=0.5)


def _enhance_contrast(img: np.ndarray) -> np.ndarray:
    """CLAHE on the L channel in LAB colour space (preserves hue)."""
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def _sharpen(img: np.ndarray) -> np.ndarray:
    """Unsharp-mask: original + (original - blurred) * amount."""
    blurred = cv2.GaussianBlur(img, (5, 5), sigmaX=1.0)
    return cv2.addWeighted(img, 1.5, blurred, -0.5, 0)


def _threshold(img: np.ndarray) -> np.ndarray:
    """Otsu binarisation; output stays 3-channel for pipeline compatibility."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
