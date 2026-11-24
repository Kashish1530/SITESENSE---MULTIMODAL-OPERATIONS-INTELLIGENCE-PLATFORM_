"""
detect_video.py
Simple SiteSense video detection script.

Lets you pick a video from your device (file picker popup or command-line path),
runs YOLO detection frame-by-frame, displays live detection, saves the annotated
video to detection/outputs/, and opens the saved result.

Usage:
    python detection/detect_video.py
    python detection/detect_video.py "C:/path/to/video.mp4"
"""

import os
import sys
import time
from collections import Counter
from pathlib import Path
from tkinter import Tk, filedialog

import cv2
import torch
from ultralytics import YOLO


# ============================================================
# SETTINGS
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent

# Automatically use best_2.pt if available, else best_1.pt or best.pt
def get_model_path() -> Path:
    for name in ["best_3.pt", "best_2.pt", "best_1.pt"]:
        p = BASE_DIR / "models" / name
        if p.exists():
            return p
    return BASE_DIR / "models" / "best_1.pt"


MODEL_PATH = get_model_path()
OUTPUT_DIR = BASE_DIR / "detection" / "outputs"
CONF_THRESHOLD = 0.25
IMG_SIZE = 640
LINE_WIDTH = 2         # Thin bounding box boundary (1-2 px)
FONT_SIZE = 20         # Small label box and text size
DEVICE = 0 if torch.cuda.is_available() else "cpu"

SHOW_PREVIEW = True    # Show live detection window while processing (press 'q' to stop)
OPEN_RESULT = True     # Automatically open the saved video when done


def select_video() -> str:
    """Use CLI argument if given, otherwise open a file picker dialog."""
    if len(sys.argv) > 1:
        return sys.argv[1]

    try:
        root = Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        file_path = filedialog.askopenfilename(
            title="Select a video for SiteSense detection",
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.webm *.flv"),
                ("All files", "*.*"),
            ],
        )
        root.destroy()
        return file_path
    except Exception:
        return input("Enter full video path: ").strip().strip('"')


def main():
    if not MODEL_PATH.exists():
        print(f"[ERROR] Model weights not found: {MODEL_PATH}")
        return

    video_path = select_video()
    if not video_path:
        print("No video selected. Exiting.")
        return

    video_path = Path(video_path)
    if not video_path.exists():
        print(f"[ERROR] Video file not found: {video_path}")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{video_path.stem}_detected.mp4"

    # 1. Load YOLO model
    print(f"\nLoading model : {MODEL_PATH}")
    print(f"Input video   : {video_path}")
    print(f"Device        : {DEVICE}")
    model = YOLO(str(MODEL_PATH))

    # 2. Open input video
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"[ERROR] Could not open video: {video_path}")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"Resolution    : {width}x{height} @ {fps:.1f} FPS")
    print(f"Total frames  : {total_frames if total_frames > 0 else 'Unknown'}")
    if SHOW_PREVIEW:
        print("Live preview  : ON (press 'q' in preview window to stop early)")

    # 3. Setup video writer
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    frame_idx = 0
    total_detections = Counter()
    start_time = time.time()
    show_window = SHOW_PREVIEW

    print("\n=== PROCESSING VIDEO ===")

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1

            # Run detection on current frame
            results = model.predict(
                frame,
                conf=CONF_THRESHOLD,
                imgsz=IMG_SIZE,
                device=DEVICE,
                verbose=False,
            )
            result = results[0]

            # Count detected classes
            for box in result.boxes:
                cls_id = int(box.cls[0])
                cls_name = model.names[cls_id]
                total_detections[cls_name] += 1

            # Draw bounding boxes on frame with thin lines and small label boxes
            annotated_frame = result.plot(line_width=LINE_WIDTH, font_size=FONT_SIZE)

            # Write annotated frame to output video
            out.write(annotated_frame)

            # Show live preview
            if show_window:
                try:
                    cv2.imshow("SiteSense Video Detection (Press 'q' to stop)", annotated_frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        print("\n[INFO] Stopped early by user.")
                        break
                except Exception:
                    show_window = False

            # Progress log every 30 frames
            if frame_idx % 30 == 0 or frame_idx == total_frames:
                pct = (frame_idx / total_frames * 100) if total_frames > 0 else 0
                elapsed = time.time() - start_time
                fps_proc = frame_idx / elapsed if elapsed > 0 else 0
                print(f"  Frame {frame_idx}/{total_frames} ({pct:5.1f}%) | Speed: {fps_proc:4.1f} FPS")

    finally:
        cap.release()
        out.release()
        cv2.destroyAllWindows()

    elapsed = time.time() - start_time
    print("\n=== DETECTION SUMMARY ===")
    print(f"  Frames processed : {frame_idx}")
    print(f"  Time elapsed     : {elapsed:.1f} s (avg {frame_idx / elapsed if elapsed > 0 else 0:.1f} FPS)")
    print("\nObjects detected across video:")
    if total_detections:
        for name, count in total_detections.most_common():
            print(f"  {name:<20}: {count} occurrences")
    else:
        print("  No objects detected.")

    print(f"\nSaved annotated video to: {output_path}")

    # 4. Automatically open saved video in Windows default media player
    if OPEN_RESULT and os.name == "nt" and output_path.exists():
        try:
            os.startfile(str(output_path))
        except Exception:
            pass


if __name__ == "__main__":
    main()
