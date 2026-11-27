"""
detect_image.py
Simple SiteSense image detection script.

Lets you pick an image from your device (file picker popup or command-line path),
runs YOLO detection using models/best.pt, prints detected objects, saves the
annotated image to detection/outputs/, and opens the result.

Usage:
    python detection/detect_image.py
    python detection/detect_image.py "C:/path/to/image.jpg"
"""

import os
import sys
from collections import Counter
from pathlib import Path
from tkinter import Tk, filedialog

import cv2
import torch
from ultralytics import YOLO


# Settings
BASE_DIR = Path(__file__).resolve().parent.parent

def get_model_paths() -> list[Path]:
    """Return ONLY the two best trained models: best_3.pt and best_2.pt."""
    candidates = [
        BASE_DIR / "models" / "best_3.pt",
        BASE_DIR / "models" / "best_2.pt",
    ]
    return [p for p in candidates if p.exists()]


def _calculate_iou(box_a: list[float], box_b: list[float]) -> float:
    """Calculate Intersection over Union for two [x1, y1, x2, y2] boxes."""
    xa = max(box_a[0], box_b[0])
    ya = max(box_a[1], box_b[1])
    xb = min(box_a[2], box_b[2])
    yb = min(box_a[3], box_b[3])
    inter = max(0.0, xb - xa) * max(0.0, yb - ya)
    area_a = max(0.0, box_a[2] - box_a[0]) * max(0.0, box_a[3] - box_a[1])
    area_b = max(0.0, box_b[2] - box_b[0]) * max(0.0, box_b[3] - box_b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _merge_detections_nms(detections: list[dict], iou_thresh: float = 0.50) -> list[dict]:
    """Merge detections from best_3.pt and best_2.pt using NMS."""
    ordered = sorted(detections, key=lambda d: d["confidence"], reverse=True)
    kept: list[dict] = []
    for det in ordered:
        if not any(
            d["class_name"] == det["class_name"] and _calculate_iou(d["bbox"], det["bbox"]) >= iou_thresh
            for d in kept
        ):
            kept.append(det)
    return kept


MODEL_PATHS = get_model_paths()
OUTPUT_DIR = BASE_DIR / "detection" / "outputs"
CONF_THRESHOLD = 0.25
IMG_SIZE = 640
LINE_WIDTH = 2         # Thin bounding box boundary (1-2 px)
FONT_SIZE = 20         # Small label box and text size
DEVICE = 0 if torch.cuda.is_available() else "cpu"
OPEN_RESULT = True   # Automatically open saved image in Windows Photos viewer


def select_image() -> str:
    """Use CLI argument if given, otherwise open a file picker dialog."""
    if len(sys.argv) > 1:
        return sys.argv[1]

    try:
        root = Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        file_path = filedialog.askopenfilename(
            title="Select an image for SiteSense detection",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.jfif *.bmp *.webp"),
                ("All files", "*.*"),
            ],
        )
        root.destroy()
        return file_path
    except Exception:
        # Check for sample test image in dataset if stdin is not interactive
        test_imgs = list((BASE_DIR / "data" / "processed" / "test" / "images").glob("*.jpg"))
        if not sys.stdin.isatty() and test_imgs:
            return str(test_imgs[0])
        return input("Enter full image path: ").strip().strip('"')


def main():
    if not MODEL_PATHS:
        print(f"[ERROR] Neither best_3.pt nor best_2.pt found in: {BASE_DIR / 'models'}")
        return

    image_path = select_image()
    if not image_path:
        print("No image selected. Exiting.")
        return

    image_path = Path(image_path)
    if not image_path.exists():
        print(f"[ERROR] Image file not found: {image_path}")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load primary best_3.pt (fallback to best_2.pt if best_3.pt fails)
    print(f"Running on    : {image_path}")
    all_detections = []
    for mp in MODEL_PATHS:
        try:
            print(f"Loading model : {mp}")
            model = YOLO(str(mp))
            results = model.predict(
                source=str(image_path),
                conf=CONF_THRESHOLD,
                imgsz=IMG_SIZE,
                device=DEVICE,
                verbose=False,
            )
            for box in results[0].boxes:
                cls_id = int(box.cls[0])
                all_detections.append({
                    "class_name": model.names[cls_id],
                    "confidence": float(box.conf[0]),
                    "bbox": [float(v) for v in box.xyxy[0].tolist()],
                    "model": mp.name,
                })
            break  # Primary best_3.pt succeeded; only use best_2.pt on failure
        except Exception as exc:
            print(f"[WARN] Model {mp.name} failed ({exc}); trying fallback...")

    merged = all_detections

    # 2. Print detected objects
    counts = Counter()
    print("\n=== DETECTIONS (best_3.pt + best_2.pt) ===")
    if not merged:
        print("  No objects detected.")
    else:
        for i, det in enumerate(merged, start=1):
            counts[det["class_name"]] += 1
            print(f"  {i:2d}. {det['class_name']:<20} (conf: {det['confidence']:.2f}, model: {det['model']})")

        print("\n=== SUMMARY COUNTS ===")
        for cls_name, cnt in counts.most_common():
            print(f"  {cls_name:<20}: {cnt}")

    # 3. Save annotated image with merged bounding boxes
    annotated_img = cv2.imread(str(image_path))
    for det in merged:
        x1, y1, x2, y2 = [int(round(v)) for v in det["bbox"]]
        label = f"{det['class_name']} {det['confidence']:.2f}"
        cv2.rectangle(annotated_img, (x1, y1), (x2, y2), (16, 185, 129), LINE_WIDTH)
        cv2.putText(
            annotated_img,
            label,
            (x1, max(16, y1 - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (16, 185, 129),
            2,
        )
    output_path = OUTPUT_DIR / f"{image_path.stem}_detected.jpg"
    cv2.imwrite(str(output_path), annotated_img)
    print(f"\nSaved output image to: {output_path}")

    # 4. Open output image on Windows
    if OPEN_RESULT and os.name == "nt":
        os.startfile(str(output_path))


if __name__ == "__main__":
    main()
