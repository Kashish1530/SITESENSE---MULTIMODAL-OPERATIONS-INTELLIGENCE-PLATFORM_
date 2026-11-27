"""
app.py
------
FastAPI Web UI for the Standalone PaddleOCR Module.
Enhanced with:
1. High-Performance Barcode & QR Code Reader (using zxing-cpp + OpenCV fallback)
2. Optical Character Recognition (PaddleOCR PP-OCRv6 CPU)
3. Multilingual Translation to English (automatic language detection & translation)
4. Clean side-by-side human-understandable visual interface
"""

import io
import os
import sys
import base64
import time
import json
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional, List, Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # project root
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
# Add src directory to import ocr_module package
src_path = PROJECT_ROOT / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

import cv2
import numpy as np
import uvicorn
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

try:
    import zxingcpp
    HAS_ZXING = True
except ImportError:
    HAS_ZXING = False

from ocr_module.ocr_engine import OCREngine
from ocr_module.config import SAMPLES_OUTPUT_DIR

app = FastAPI(title="PaddleOCR + Code Reader & Translation Console")

# Global engine cache
engine: Optional[OCREngine] = None
qr_detector = None
barcode_detector = None


@app.on_event("startup")
def load_engine():
    global engine, qr_detector, barcode_detector
    print("Initializing OCREngine for Web UI...")
    engine = OCREngine(min_confidence=0.25, output_dir=SAMPLES_OUTPUT_DIR)
    qr_detector = cv2.QRCodeDetector()
    try:
        barcode_detector = cv2.barcode.BarcodeDetector()
    except Exception:
        barcode_detector = None
    print(f"OCREngine ready (zxing-cpp available: {HAS_ZXING}).")


def translate_to_english(text: str) -> Dict[str, Any]:
    """Translate non-English text to English."""
    if not text or not text.strip():
        return {"detected_lang": "en", "translated_text": text, "is_translated": False}
    
    clean_strip = text.strip()
    if clean_strip.replace("-", "").replace("_", "").replace(".", "").isalnum() and len(clean_strip) <= 6:
        return {"detected_lang": "en", "translated_text": text, "is_translated": False}

    url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=en&dt=t&q=" + urllib.parse.quote(text)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=4) as response:
            data = json.loads(response.read().decode("utf-8"))
            translated_pieces = [sentence[0] for sentence in data[0] if sentence[0]]
            translated = "".join(translated_pieces)
            src_lang = data[2] if len(data) > 2 else "auto"
            
            is_trans = (
                src_lang.lower() not in ["en", "und"] and 
                translated.strip().lower() != text.strip().lower()
            )
            return {
                "detected_lang": src_lang,
                "translated_text": translated if is_trans else text,
                "is_translated": is_trans
            }
    except Exception:
        return {"detected_lang": "auto", "translated_text": text, "is_translated": False}


def scan_barcodes_and_qrs(img: np.ndarray) -> List[Dict[str, Any]]:
    """
    Robust scanning using zxing-cpp (industry standard) with multi-scale/rotation passes,
    falling back to OpenCV.
    """
    findings = []
    seen_data = set()

    # Pass 1: zxing-cpp (highest accuracy for 1D Barcodes & 2D QR Codes)
    if HAS_ZXING:
        # Multi-scale & multi-filter attempts for blurry, low-res or compressed barcodes
        attempts = [
            img,
            cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img,
        ]
        h, w = img.shape[:2]
        if min(h, w) < 300:
            scale = 300 / min(h, w)
            attempts.append(cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC))

        for target in attempts:
            try:
                results = zxingcpp.read_barcodes(target)
                for r in results:
                    val = r.text.strip() if r.text else ""
                    if val and val not in seen_data:
                        seen_data.add(val)
                        pts = []
                        if hasattr(r, 'position') and r.position:
                            pts = [[int(p.x), int(p.y)] for p in [r.position.top_left, r.position.top_right, r.position.bottom_right, r.position.bottom_left]]
                        findings.append({
                            "type": r.format.name,
                            "data": val,
                            "points": pts
                        })
                if findings:
                    break
            except Exception:
                pass

    # Pass 2: OpenCV Fallback if zxing found nothing
    if not findings:
        # 1. OpenCV QR detector
        if qr_detector is not None:
            try:
                val, pts, _ = qr_detector.detectAndDecode(img)
                if val and val.strip() and val.strip() not in seen_data:
                    seen_data.add(val.strip())
                    findings.append({
                        "type": "QR Code",
                        "data": val.strip(),
                        "points": pts.astype(int).tolist() if pts is not None else []
                    })
            except Exception:
                pass

        # 2. OpenCV Barcode detector
        if barcode_detector is not None:
            try:
                res = barcode_detector.detectAndDecode(img)
                if len(res) == 3:
                    decoded_info, decoded_type, points = res
                    if decoded_info and isinstance(decoded_info, str) and decoded_info.strip():
                        val = decoded_info.strip()
                        if val not in seen_data:
                            findings.append({
                                "type": f"Barcode ({decoded_type})" if decoded_type else "1D Barcode",
                                "data": val,
                                "points": points.astype(int).tolist() if points is not None else []
                            })
            except Exception:
                pass

    return findings


HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>OCR + Barcode & QR Reader + Translator Console</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0b1120;
      --card-bg: #1e293b;
      --card-border: #334155;
      --primary: #38bdf8;
      --primary-hover: #0ea5e9;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --accent: #10b981;
      --accent-badge: rgba(16, 185, 129, 0.15);
      --badge-border: rgba(16, 185, 129, 0.3);
      --purple: #c084fc;
      --purple-bg: rgba(192, 132, 252, 0.15);
      --font-mono: 'JetBrains Mono', monospace;
      --font-sans: 'Inter', sans-serif;
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg);
      color: var(--text-main);
      font-family: var(--font-sans);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      padding: 20px 24px;
    }

    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--card-border);
      margin-bottom: 20px;
    }

    .title-group h1 {
      font-size: 1.5rem;
      font-weight: 700;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .title-group h1 span {
      background: linear-gradient(135deg, #38bdf8, #818cf8);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .title-group p {
      color: var(--text-muted);
      font-size: 0.85rem;
      margin-top: 4px;
    }

    .badge-bar {
      display: flex;
      gap: 8px;
    }

    .feature-pill {
      font-size: 0.75rem;
      background: rgba(56, 189, 248, 0.1);
      border: 1px solid rgba(56, 189, 248, 0.3);
      color: var(--primary);
      padding: 5px 12px;
      border-radius: 9999px;
      font-weight: 600;
    }

    .main-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
      flex: 1;
    }

    @media (max-width: 1080px) {
      .main-grid { grid-template-columns: 1fr; }
    }

    .panel {
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
    }

    .panel-header {
      font-size: 1rem;
      font-weight: 600;
      margin-bottom: 14px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      color: #e2e8f0;
    }

    .upload-zone {
      border: 2px dashed #475569;
      border-radius: 10px;
      padding: 24px 16px;
      text-align: center;
      cursor: pointer;
      transition: all 0.2s ease;
      background: rgba(15, 23, 42, 0.4);
      margin-bottom: 16px;
    }

    .upload-zone:hover, .upload-zone.dragover {
      border-color: var(--primary);
      background: rgba(56, 189, 248, 0.05);
    }

    .upload-btn {
      background: var(--primary);
      color: #0f172a;
      font-weight: 600;
      border: none;
      padding: 8px 18px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.9rem;
      margin-top: 8px;
      transition: background 0.2s;
    }

    .upload-btn:hover { background: var(--primary-hover); }

    .image-preview-container {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #060911;
      border-radius: 10px;
      border: 1px solid var(--card-border);
      overflow: hidden;
      min-height: 380px;
      position: relative;
    }

    .image-preview-container img {
      max-width: 100%;
      max-height: 520px;
      object-fit: contain;
      display: none;
    }

    .placeholder-text {
      color: var(--text-muted);
      font-size: 0.85rem;
      text-align: center;
      padding: 20px;
    }

    /* Right Column Stats & Cards */
    .stats-bar {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
      margin-bottom: 16px;
    }

    .stat-card {
      background: #090d16;
      border: 1px solid var(--card-border);
      padding: 10px 8px;
      border-radius: 8px;
      text-align: center;
    }

    .stat-label {
      font-size: 0.7rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .stat-value {
      font-size: 1.2rem;
      font-weight: 700;
      color: var(--primary);
      margin-top: 2px;
      font-family: var(--font-mono);
    }

    /* Code Reader Box (Barcodes & QR Codes) */
    .codes-card {
      background: rgba(192, 132, 252, 0.08);
      border: 1px solid rgba(192, 132, 252, 0.3);
      border-radius: 10px;
      padding: 14px;
      margin-bottom: 14px;
      display: none;
    }

    .codes-title {
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      font-weight: 700;
      color: var(--purple);
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .code-item {
      background: rgba(15, 23, 42, 0.7);
      border: 1px solid rgba(192, 132, 252, 0.2);
      border-radius: 6px;
      padding: 8px 12px;
      margin-top: 6px;
      font-family: var(--font-mono);
      font-size: 0.95rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .code-type-pill {
      font-size: 0.7rem;
      background: var(--purple-bg);
      color: var(--purple);
      padding: 2px 8px;
      border-radius: 4px;
      font-weight: 600;
    }

    /* Summary Card (Extracted Text) */
    .summary-card {
      background: rgba(56, 189, 248, 0.07);
      border: 1px solid rgba(56, 189, 248, 0.22);
      border-radius: 10px;
      padding: 14px;
      margin-bottom: 14px;
    }

    .summary-title {
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      font-weight: 700;
      color: var(--primary);
      margin-bottom: 6px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .summary-text {
      font-size: 1rem;
      line-height: 1.5;
      color: #f1f5f9;
      font-weight: 500;
      word-break: break-word;
    }

    /* Translation Card */
    .translation-card {
      background: rgba(16, 185, 129, 0.08);
      border: 1px solid rgba(16, 185, 129, 0.3);
      border-radius: 10px;
      padding: 14px;
      margin-bottom: 14px;
      display: none;
    }

    .translation-title {
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      font-weight: 700;
      color: var(--accent);
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .translation-text {
      font-size: 1rem;
      line-height: 1.5;
      color: #ecfdf5;
      font-weight: 500;
    }

    /* Helpful tips note for partially cropped images */
    .tip-box {
      font-size: 0.75rem;
      color: #94a3b8;
      background: rgba(15, 23, 42, 0.5);
      border-left: 3px solid #64748b;
      padding: 8px 12px;
      border-radius: 0 6px 6px 0;
      margin-top: 10px;
    }

    /* Line-by-Line Breakdown */
    .section-title {
      font-size: 0.85rem;
      font-weight: 600;
      color: #cbd5e1;
      margin-bottom: 8px;
    }

    .regions-list {
      flex: 1;
      overflow-y: auto;
      max-height: 250px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding-right: 4px;
    }

    .regions-list::-webkit-scrollbar { width: 5px; }
    .regions-list::-webkit-scrollbar-thumb {
      background: #334155;
      border-radius: 4px;
    }

    .region-row {
      background: #090d16;
      border: 1px solid var(--card-border);
      border-radius: 8px;
      padding: 10px 14px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .region-left {
      display: flex;
      align-items: center;
      gap: 10px;
      overflow: hidden;
    }

    .region-idx {
      background: #334155;
      color: #94a3b8;
      font-family: var(--font-mono);
      font-size: 0.7rem;
      width: 22px;
      height: 22px;
      border-radius: 5px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 600;
      flex-shrink: 0;
    }

    .region-text {
      font-size: 0.9rem;
      color: #f8fafc;
      font-weight: 500;
      font-family: var(--font-mono);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .confidence-badge {
      font-size: 0.75rem;
      font-family: var(--font-mono);
      font-weight: 600;
      padding: 3px 8px;
      border-radius: 5px;
      flex-shrink: 0;
    }

    .conf-high {
      background: rgba(16, 185, 129, 0.15);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .conf-mid {
      background: rgba(245, 158, 11, 0.15);
      color: #fbbf24;
      border: 1px solid rgba(245, 158, 11, 0.3);
    }

    .spinner {
      display: none;
      width: 36px;
      height: 36px;
      border: 3px solid rgba(255, 255, 255, 0.1);
      border-top-color: var(--primary);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }

    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>

  <header>
    <div class="title-group">
      <h1><span>PaddleOCR</span> Multi-Modal Vision Console</h1>
      <p>OCR Text Extraction + Barcode & QR Code Reader (zxing-cpp) + Multilingual Translation</p>
    </div>
    <div class="badge-bar">
      <span class="feature-pill">PP-OCRv6 CPU</span>
      <span class="feature-pill" style="color: var(--purple); border-color: rgba(192, 132, 252, 0.3); background: rgba(192, 132, 252, 0.1);">ZXing Code Engine</span>
      <span class="feature-pill" style="color: var(--accent); border-color: rgba(16, 185, 129, 0.3); background: rgba(16, 185, 129, 0.1);">Auto Translation</span>
    </div>
  </header>

  <div class="main-grid">
    <div class="panel">
      <div class="panel-header">
        <span>Image & Annotated Output</span>
        <span style="font-size: 0.8rem; color: var(--text-muted);" id="imgMeta">—</span>
      </div>

      <div class="upload-zone" id="dropZone" onclick="document.getElementById('fileInput').click()">
        <span style="font-size: 2rem; display: block; margin-bottom: 6px;">📷</span>
        <div style="font-weight: 600; font-size: 0.95rem; color: #f1f5f9;">Drag & drop image here</div>
        <div style="color: var(--text-muted); font-size: 0.8rem; margin-top: 3px;">Supports full labels, barcodes, QR codes and printed text</div>
        <button type="button" class="upload-btn">Browse File</button>
        <input type="file" id="fileInput" accept="image/png, image/jpeg, image/jpg, image/bmp" style="display: none;">
      </div>

      <div class="image-preview-container" id="previewContainer">
        <div class="spinner" id="spinner"></div>
        <div class="placeholder-text" id="placeholder">Upload an image to see detection bounding boxes, codes & translation</div>
        <img id="annotatedImage" alt="OCR Annotated Output">
      </div>

      <div class="tip-box">
        💡 <b>Pro Tip:</b> Barcodes require full width (left/right start & stop guard bars + quiet zones) to decode. If scanning printed labels, ensure the barcode is fully within the frame.
      </div>
    </div>

    <div class="panel">
      <div class="panel-header">
        <span>Structured Intelligence Output</span>
        <span id="timingBadge" style="font-size: 0.8rem; color: var(--text-muted);">Ready</span>
      </div>

      <div class="stats-bar">
        <div class="stat-card">
          <div class="stat-label">OCR Regions</div>
          <div class="stat-value" id="valRegions">0</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Codes Read</div>
          <div class="stat-value" id="valCodes">0</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Confidence</div>
          <div class="stat-value" id="valConf">0%</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Latency</div>
          <div class="stat-value" id="valTime">0ms</div>
        </div>
      </div>

      <div class="codes-card" id="codesCard">
        <div class="codes-title">
          <span>🏷️ Decoded Barcode & QR Code</span>
        </div>
        <div id="codesList"></div>
      </div>

      <div class="summary-card">
        <div class="summary-title">
          <span>Recognized Printed Text</span>
          <span id="langBadge" style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase;"></span>
        </div>
        <div class="summary-text" id="fullText">No image processed yet. Upload an image on the left.</div>
      </div>

      <div class="translation-card" id="transCard">
        <div class="translation-title">
          <span>🌐 English Translation</span>
          <span id="transFrom" style="font-size: 0.7rem; opacity: 0.8;"></span>
        </div>
        <div class="translation-text" id="transText"></div>
      </div>

      <div class="section-title">
        <span>Detected Text Segments</span>
      </div>

      <div class="regions-list" id="regionsList"></div>
    </div>
  </div>

  <script>
    const fileInput = document.getElementById('fileInput');
    const dropZone = document.getElementById('dropZone');
    const spinner = document.getElementById('spinner');
    const placeholder = document.getElementById('placeholder');
    const annotatedImage = document.getElementById('annotatedImage');
    const fullText = document.getElementById('fullText');
    const valRegions = document.getElementById('valRegions');
    const valCodes = document.getElementById('valCodes');
    const valConf = document.getElementById('valConf');
    const valTime = document.getElementById('valTime');
    const timingBadge = document.getElementById('timingBadge');
    const regionsList = document.getElementById('regionsList');
    const imgMeta = document.getElementById('imgMeta');
    const codesCard = document.getElementById('codesCard');
    const codesList = document.getElementById('codesList');
    const transCard = document.getElementById('transCard');
    const transText = document.getElementById('transText');
    const transFrom = document.getElementById('transFrom');
    const langBadge = document.getElementById('langBadge');

    ['dragenter', 'dragover'].forEach(name => {
      dropZone.addEventListener(name, (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
      });
    });

    ['dragleave', 'drop'].forEach(name => {
      dropZone.addEventListener(name, (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
      });
    });

    dropZone.addEventListener('drop', (e) => {
      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        processFile(e.dataTransfer.files[0]);
      }
    });

    fileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files[0]) {
        processFile(e.target.files[0]);
      }
    });

    async function processFile(file) {
      if (!file) return;

      placeholder.style.display = 'none';
      annotatedImage.style.display = 'none';
      spinner.style.display = 'block';
      codesCard.style.display = 'none';
      transCard.style.display = 'none';
      fullText.innerText = "Analyzing image: reading text, scanning barcodes/QR & detecting language...";
      timingBadge.innerText = "Processing...";
      regionsList.innerHTML = "";
      codesList.innerHTML = "";
      langBadge.innerText = "";
      imgMeta.innerText = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;

      const formData = new FormData();
      formData.append('file', file);

      try {
        const response = await fetch('/api/ocr', {
          method: 'POST',
          body: formData
        });

        const data = await response.json();
        spinner.style.display = 'none';

        if (!data.success) {
          fullText.innerText = "Error: " + (data.error || "Unable to process image");
          timingBadge.innerText = "Failed";
          return;
        }

        annotatedImage.src = "data:image/jpeg;base64," + data.annotated_image_base64;
        annotatedImage.style.display = 'block';

        valRegions.innerText = data.extracted_text.length;
        valCodes.innerText = (data.codes || []).length;
        const avgScore = data.extracted_text.length > 0 
          ? (data.extracted_text.reduce((sum, item) => sum + item.confidence, 0) / data.extracted_text.length * 100).toFixed(1)
          : 0;
        valConf.innerText = avgScore + "%";
        valTime.innerText = Math.round(data.processing_time_ms) + "ms";
        timingBadge.innerText = `Completed in ${Math.round(data.processing_time_ms)}ms`;

        if (data.codes && data.codes.length > 0) {
          codesCard.style.display = 'block';
          codesList.innerHTML = data.codes.map(c => `
            <div class="code-item">
              <span style="font-weight: 600; color: #fff;">${escapeHtml(c.data)}</span>
              <span class="code-type-pill">${escapeHtml(c.type)}</span>
            </div>
          `).join('');
        }

        fullText.innerText = data.full_text || "(No readable printed text detected)";

        if (data.translation && data.translation.is_translated) {
          transCard.style.display = 'block';
          transText.innerText = data.translation.translated_text;
          transFrom.innerText = `(Translated from: ${data.translation.detected_lang.toUpperCase()})`;
          langBadge.innerText = `[${data.translation.detected_lang.toUpperCase()}]`;
        }

        if (data.extracted_text.length === 0) {
          regionsList.innerHTML = `<div style="color: var(--text-muted); padding: 8px; font-size: 0.85rem;">No text bounding boxes found.</div>`;
        } else {
          data.extracted_text.forEach((item, index) => {
            const confPercent = (item.confidence * 100).toFixed(1);
            const badgeClass = item.confidence >= 0.85 ? 'conf-high' : 'conf-mid';

            const row = document.createElement('div');
            row.className = 'region-row';
            row.innerHTML = `
              <div class="region-left">
                <div class="region-idx">${index + 1}</div>
                <div class="region-text" title="${escapeHtml(item.text)}">${escapeHtml(item.text)}</div>
              </div>
              <div class="confidence-badge ${badgeClass}">${confPercent}%</div>
            `;
            regionsList.appendChild(row);
          });
        }

      } catch (err) {
        spinner.style.display = 'none';
        fullText.innerText = "Error: " + err.message;
        timingBadge.innerText = "Error";
      }
    }

    function escapeHtml(text) {
      const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
      return text.replace(/[&<>"']/g, m => map[m]);
    }
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    return HTMLResponse(content=HTML_PAGE)


@app.post("/api/ocr")
async def run_ocr_api(file: UploadFile = File(...)):
    global engine
    if engine is None:
        return JSONResponse(status_code=500, content={"success": False, "error": "Engine not initialized"})

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "Could not decode uploaded file as an image."}
        )

    t0 = time.perf_counter()

    # 1. Barcode & QR Code Scanning (zxing-cpp + OpenCV multi-engine)
    detected_codes = scan_barcodes_and_qrs(img)

    # 2. Preprocess for OCR
    from ocr_module.preprocessing import _denoise, _enhance_contrast, _sharpen
    from ocr_module.config import PREPROCESS
    
    proc_img = img.copy()
    if PREPROCESS.denoise:
        proc_img = _denoise(proc_img)
    if PREPROCESS.enhance_contrast:
        proc_img = _enhance_contrast(proc_img)
    if PREPROCESS.sharpen:
        proc_img = _sharpen(proc_img)

    # 3. PaddleOCR inference
    raw = engine._run_inference(proc_img)

    # 4. Post-processing
    from ocr_module.postprocessing import postprocess
    from ocr_module.image_utils import draw_ocr_results

    results, full_text = postprocess(
        raw["rec_texts"],
        raw["rec_scores"],
        raw["rec_polys"],
        min_confidence=engine.min_confidence,
    )

    # 5. Multilingual Translation
    translation_info = translate_to_english(full_text)

    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    # 6. Annotation overlay
    annotated = draw_ocr_results(proc_img, results)
    
    # Draw boxes for barcodes and QR codes
    for code in detected_codes:
        pts = code.get("points")
        if pts and len(pts) >= 4:
            pts_np = np.array(pts, dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(annotated, [pts_np], isClosed=True, color=(252, 132, 192), thickness=2)
            cv2.putText(
                annotated,
                code["type"],
                (pts[0][0], max(pts[0][1] - 6, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (252, 132, 192),
                1,
                lineType=cv2.LINE_AA,
            )

    _, buffer = cv2.imencode(".jpg", annotated)
    b64_img = base64.b64encode(buffer).decode("utf-8")

    return {
        "success": True,
        "image_name": file.filename,
        "extracted_text": [r.model_dump() for r in results],
        "full_text": full_text,
        "codes": detected_codes,
        "translation": translation_info,
        "processing_time_ms": round(elapsed_ms, 2),
        "annotated_image_base64": b64_img,
    }


def start():
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    start()
