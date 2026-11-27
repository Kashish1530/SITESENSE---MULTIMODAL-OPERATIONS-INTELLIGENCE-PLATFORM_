"""
config.py
Central configuration for the OCR module.
"""

from pathlib import Path
import os

# Project paths
PROJECT_ROOT      = Path(__file__).resolve().parent.parent
SAMPLES_INPUT_DIR = PROJECT_ROOT / "samples" / "input"
DATASET_TRAIN_DIR = PROJECT_ROOT / "dataset" / "ocr_data" / "Train" / "images"
DATASET_VAL_DIR   = PROJECT_ROOT / "dataset" / "ocr_data" / "val" / "Images"


def _resolve_output_dir() -> Path:
    """Pick the first writable candidate from the preferred list."""
    candidates = [
        Path("E:/Temp/ocr_outputs"),
        PROJECT_ROOT / "samples" / "output",
        PROJECT_ROOT / "outputs",
        Path(os.environ.get("TEMP", "C:/Temp")) / "ocr_outputs",
        Path.home() / "ocr_outputs",
    ]
    for c in candidates:
        try:
            c.mkdir(parents=True, exist_ok=True)
            probe = c / ".write_test"
            probe.write_text("x")
            probe.unlink()
            return c
        except (OSError, PermissionError):
            continue
    import tempfile
    return Path(tempfile.mkdtemp(prefix="ocr_outputs_"))


SAMPLES_OUTPUT_DIR = _resolve_output_dir()

# Supported image extensions
SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}

# PaddleOCR engine settings (PaddleOCR 3.7.0 / PP-OCRv6)
OCR_LANG    = "en"
OCR_VERSION = "PP-OCRv6"

# Pipeline switches - keep False for a lean CPU-only pipeline
USE_DOC_ORIENTATION_CLASSIFY = False
USE_DOC_UNWARPING            = False
USE_TEXTLINE_ORIENTATION     = False

# CRITICAL FIX: disable MKL-DNN / oneDNN so the pure-paddle CPU path is used.
ENABLE_MKLDNN = False

# Detection thresholds
TEXT_DET_THRESH         = 0.3
TEXT_DET_BOX_THRESH     = 0.6
TEXT_DET_UNCLIP_RATIO   = 1.5
TEXT_DET_LIMIT_SIDE_LEN = 64
TEXT_DET_LIMIT_TYPE     = "min"

# Recognition score threshold (0 = keep all; post-processing filters)
TEXT_REC_SCORE_THRESH = 0.0

# Post-processing
MIN_CONFIDENCE   = 0.3
STRIP_WHITESPACE = True


# Preprocessing
class PreprocessConfig:
    """Toggle individual preprocessing steps."""
    max_dimension: int     = 2048
    min_dimension: int     = 64
    denoise: bool          = True
    enhance_contrast: bool = True
    sharpen: bool          = True
    to_grayscale: bool     = False
    threshold: bool        = False


PREPROCESS = PreprocessConfig()

# Visualisation
BBOX_COLOR      = (0, 255, 0)   # green  (B, G, R)
BBOX_THICKNESS  = 2
TEXT_COLOR      = (0, 0, 255)   # red    (B, G, R)
TEXT_FONT_SCALE = 0.5
TEXT_FONT_THICK = 1

# Output filenames
ANNOTATED_IMAGE_SUFFIX = "_annotated.jpg"
JSON_SUFFIX            = ".json"
