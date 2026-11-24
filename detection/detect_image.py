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
MODEL_PATH = BASE_DIR / "models" / "best_2.pt"
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
        return input("Enter full image path: ").strip().strip('"')


def main():
    if not MODEL_PATH.exists():
        print(f"[ERROR] Model not found: {MODEL_PATH}")
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

    # 1. Load model and run detection
    print(f"Loading model : {MODEL_PATH}")
    print(f"Running on    : {image_path}")
    model = YOLO(str(MODEL_PATH))

    results = model.predict(
        source=str(image_path),
        conf=CONF_THRESHOLD,
        imgsz=IMG_SIZE,
        device=DEVICE,
        verbose=False,
    )
    result = results[0]

    # 2. Print detected objects
    counts = Counter()
    print("\n=== DETECTIONS ===")
    if len(result.boxes) == 0:
        print("  No objects detected.")
    else:
        for i, box in enumerate(result.boxes, start=1):
            cls_id = int(box.cls[0])
            cls_name = model.names[cls_id]
            conf = float(box.conf[0])
            counts[cls_name] += 1
            print(f"  {i:2d}. {cls_name:<20} (conf: {conf:.2f})")

        print("\n=== SUMMARY COUNTS ===")
        for cls_name, cnt in counts.most_common():
            print(f"  {cls_name:<20}: {cnt}")

    # 3. Save annotated image with thin boundary and small label boxes
    annotated_img = result.plot(line_width=LINE_WIDTH, font_size=FONT_SIZE)
    output_path = OUTPUT_DIR / f"{image_path.stem}_detected.jpg"
    cv2.imwrite(str(output_path), annotated_img)
    print(f"\nSaved output image to: {output_path}")

    # 4. Open output image on Windows
    if OPEN_RESULT and os.name == "nt":
        os.startfile(str(output_path))


if __name__ == "__main__":
    main()
