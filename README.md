# OCR Module — Standalone PaddleOCR Text Extraction

A fully independent OCR pipeline built on **PaddleOCR 3.7.0** (PP-OCRv6)
running on **CPU-only** (Windows 10, Python 3.10).

---

## Project Structure

```
OCR_Module/
├── main.py               # Entry point: batch-processes all input images
├── requirements.txt
├── README.md
│
├── ocr_module/
│   ├── __init__.py
│   ├── config.py         # All tunable parameters live here
│   ├── ocr_engine.py     # Core engine — wraps PaddleOCR, initialised once
│   ├── preprocessing.py  # Image preprocessing pipeline (CLAHE, denoise, sharpen…)
│   ├── postprocessing.py # Confidence filtering, duplicate removal, text cleaning
│   ├── image_utils.py    # Bounding-box drawing + image I/O helpers
│   └── models.py         # Pydantic data models (OCRResponse, OCRTextResult…)
│
├── samples/
│   ├── input/            # ← Place your images here
│   └── output/           # JSON + annotated images are written here
│
├── dataset/
│   └── ocr_data/
│       ├── Train/images/ # 160 synthetic warehouse images (8 categories)
│       └── val/Images/   # 40 validation images
│
└── tests/
    ├── test_ocr.py        # Integration tests (real PaddleOCR inference)
    └── test_preprocessing.py  # Unit tests (no model loading)
```

---

## Quickstart

```powershell
# 1. Activate virtual environment
cd E:\OCR_Module
.\venv\Scripts\activate

# 2. Run OCR on all images (samples/input + dataset/Train)
python main.py

# 3. Run OCR on a custom directory
python main.py --input path\to\images --output path\to\results

# 4. Run OCR on a single image
python main.py --input samples\input\my_label.jpg

# 5. Adjust confidence threshold
python main.py --confidence 0.5

# 6. Skip preprocessing (raw inference)
python main.py --no-preprocess
```

---

## Output Files

For every input image the module writes to `samples/output/`:

| File | Description |
|------|-------------|
| `<stem>.json` | Structured OCR results (see schema below) |
| `<stem>_annotated.jpg` | Image with bounding boxes + text labels |
| `evaluation_report.json` | Dataset-level summary (all images) |

### JSON Schema

```json
{
  "success": true,
  "image_name": "carton_label_001.jpg",
  "extracted_text": [
    {
      "text": "SKU: AC-1024",
      "confidence": 0.997,
      "bounding_box": [[185,299],[434,299],[434,338],[185,338]]
    }
  ],
  "full_text": "carton_label ACME SKU: AC-1024 QTY: 24 PCS",
  "processing_time_ms": 234.5,
  "error": null,
  "preprocessing_meta": {
    "original_shape": [640, 640],
    "final_shape": [640, 640],
    "steps_applied": ["load","resize","denoise","contrast_enhance","sharpen"]
  }
}
```

---

## Running Tests

```powershell
# All tests (unit + integration with real inference)
python -m pytest tests/ -v

# Unit tests only (fast — no model loading)
python -m pytest tests/test_preprocessing.py -v

# Integration tests only
python -m pytest tests/test_ocr.py -v

# With coverage report
python -m pytest tests/ -v --cov=ocr_module --cov-report=term-missing
```

---

## Key Configuration (`ocr_module/config.py`)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `OCR_LANG` | `en` | PaddleOCR language |
| `ENABLE_MKLDNN` | `False` | **Must stay False** on this setup (see note) |
| `MIN_CONFIDENCE` | `0.3` | Drop results below this score |
| `TEXT_DET_THRESH` | `0.3` | Pixel-level detection threshold |
| `TEXT_DET_BOX_THRESH` | `0.6` | Box-level score filter |
| `PREPROCESS.denoise` | `True` | Gaussian noise reduction |
| `PREPROCESS.enhance_contrast` | `True` | CLAHE contrast enhancement |
| `PREPROCESS.sharpen` | `True` | Unsharp-mask sharpening |

> **Note on `ENABLE_MKLDNN=False`**: PaddlePaddle 3.3.1 on Windows CPU with
> oneDNN v3.6.2 triggers a `NotImplementedError` in the PIR (new-IR) executor
> when MKL-DNN is active. Setting `enable_mkldnn=False` forces the pure-paddle
> CPU execution path and resolves the issue.

---

## Image Categories in the Dataset

| Category | Images | Description |
|----------|--------|-------------|
| `barcode` | 25 | 1-D barcode labels with text |
| `carton_label` | 25 | Shipping carton labels (SKU, qty…) |
| `equipment_plate` | 25 | Equipment nameplates |
| `fire_extinguisher_tag` | 25 | Safety inspection tags |
| `pallet_tag` | 25 | Warehouse pallet tags |
| `qr_code` | 25 | QR codes with adjacent text |
| `rack_id` | 25 | Rack location IDs |
| `warehouse_aisle` | 25 | Aisle signage |

---

## Technology Stack

| Component | Version |
|-----------|---------|
| Python | 3.10.4 |
| PaddleOCR | 3.7.0 |
| PaddlePaddle | 3.3.1 (CPU) |
| OpenCV | 5.1.0.95 |
| Pillow | 12.3.0 |
| Pydantic | 2.14.3 |


