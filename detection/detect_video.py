"""
detect_video.py
SiteSense Unified Video Detection & Spatial Tracking Script.
Integrates Member 1 (YOLO 16-Class Object Detection) with Member 2 (ByteTrack Persistent Tracking & Zone Engine).

Features:
- Runs YOLOv11/v8 detection with automated weights discovery.
- Persistent ByteTrack tracking (prevents counting the same person/forklift repeatedly).
- Configurable spatial zone evaluation (dwell time alerts, restricted zones, directional counting lines).
- Saves annotated video and prints dual summary: Naive Detections vs Unique Entities.

Usage:
    python detection/detect_video.py
    python detection/detect_video.py "data/sample_videos/warehouse1.mp4"
    python detection/detect_video.py "data/sample_videos/warehouse1.mp4" --zones "config/zones_warehouse.json"
    python detection/detect_video.py --no-preview
"""

import os
import sys
import time
import argparse
from collections import Counter
from pathlib import Path

import cv2
import torch
from ultralytics import YOLO

# Resolve workspace root and import Member 2 tracking & zone engines
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR / "src"))
sys.path.append(str(BASE_DIR / "cv_video-zone_tracking" / "src"))

try:
    from tracker import ByteTrackEngine
    from zone_engine import ZoneEngine
    from annotator import VisualAnnotator
    TRACKING_AVAILABLE = True
except ImportError:
    TRACKING_AVAILABLE = False


def get_model_path() -> Path:
    """Discovers ONLY best_3.pt or best_2.pt trained weights."""
    candidates = [
        BASE_DIR / "models" / "best_3.pt",
        BASE_DIR / "models" / "best_2.pt",
    ]
    for p in candidates:
        if p.exists():
            return p
    return BASE_DIR / "models" / "best_3.pt"


def select_video_fallback() -> str:
    """Opens a Tkinter file picker dialog if no CLI path is provided."""
    try:
        from tkinter import Tk, filedialog
        root = Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        file_path = filedialog.askopenfilename(
            title="Select a video for SiteSense detection & tracking",
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.webm *.flv"),
                ("All files", "*.*"),
            ],
        )
        root.destroy()
        return file_path
    except Exception:
        return input("Enter full video path: ").strip().strip('"')


def parse_args():
    parser = argparse.ArgumentParser(description="SiteSense Video Detection & Persistent Tracking")
    parser.add_argument("video", nargs="?", default=None, help="Path to input video file")
    parser.add_argument("--model", default=None, help="Path to YOLO weights (.pt)")
    parser.add_argument("--zones", default=None, help="Path to zone config JSON (e.g. config/zones_warehouse.json)")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold")
    parser.add_argument("--track", action="store_true", default=True, help="Enable ByteTrack persistent tracking")
    parser.add_argument("--no-track", dest="track", action="store_false", help="Disable tracking (raw detections only)")
    parser.add_argument("--no-preview", action="store_true", help="Disable live GUI display window")
    parser.add_argument("--no-open", action="store_true", help="Do not open saved video in player upon completion")
    return parser.parse_args()


def main():
    args = parse_args()

    # 1. Resolve video source
    video_path_str = args.video
    if not video_path_str:
        # Check if default sample video exists
        def_sample = BASE_DIR / "data" / "sample_videos" / "warehouse1.mp4"
        if not sys.stdin.isatty() and def_sample.exists():
            video_path_str = str(def_sample)
        else:
            video_path_str = select_video_fallback()

    if not video_path_str:
        print("No video selected. Exiting.")
        return

    video_path = Path(video_path_str)
    if not video_path.exists():
        print(f"[ERROR] Video file not found: {video_path}")
        return

    # 2. Resolve Model Weights
    model_path = Path(args.model) if args.model else get_model_path()
    if not model_path.exists():
        print(f"[ERROR] Model weights not found: {model_path}")
        return

    output_dir = BASE_DIR / "detection" / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{video_path.stem}_detected.mp4"

    device = 0 if torch.cuda.is_available() else "cpu"

    print("\n" + "=" * 60)
    print("🎯 SITESENSE — UNIFIED DETECTION & SPATIAL TRACKING PIPELINE")
    print("=" * 60)
    print(f"[*] Input Video     : {video_path}")
    print(f"[*] Model Weights   : {model_path}")
    print(f"[*] Compute Device  : {device}")
    print(f"[*] Tracking Mode   : {'ByteTrack Persistent IDs (Active)' if (args.track and TRACKING_AVAILABLE) else 'Off (Naive Detections)'}")

    # 3. Initialize Tracking & Zone Engine if requested
    tracker = None
    if args.track and TRACKING_AVAILABLE:
        try:
            tracker = ByteTrackEngine(model_weights=str(model_path))
        except Exception as e:
            print(f"[!] Tracking initialization fallback: {e}")
            tracker = None

    zone_engine = None
    if args.zones and TRACKING_AVAILABLE:
        if os.path.exists(args.zones):
            zone_engine = ZoneEngine(args.zones)
            print(f"[*] Zone Engine     : Active ({len(zone_engine.zones)} zones from {args.zones})")
        else:
            print(f"[!] Zone config not found at: {args.zones}")
    elif TRACKING_AVAILABLE:
        # Check for auto-discovered zone config matching video name
        auto_cfg = BASE_DIR / "config" / ("zones_warehouse.json" if "warehouse" in str(video_path).lower() else "zones_construction.json")
        if auto_cfg.exists():
            zone_engine = ZoneEngine(str(auto_cfg))
            print(f"[*] Zone Engine     : Auto-loaded ({len(zone_engine.zones)} zones from {auto_cfg.name})")

    # 4. Open video
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"[ERROR] Could not open video: {video_path}")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"[*] Video Specs     : {width}x{height} @ {fps:.1f} FPS ({total_frames} frames)")
    show_preview = not args.no_preview

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    # Standard model loader (used if tracker is off)
    model = YOLO(str(model_path)) if tracker is None else None

    frame_idx = 0
    naive_counts = Counter()
    total_zone_violations = 0
    total_line_crossings = 0
    start_time = time.time()

    print("\n=== PROCESSING VIDEO ===")

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            frame_idx += 1
            timestamp = frame_idx / fps

            annotated_frame = frame.copy()

            if tracker is not None:
                # Member 2 ByteTrack Tracking
                tracked_objects = tracker.update(frame)
                
                # Draw zone polygons if active
                if zone_engine is not None:
                    violations, crossings = zone_engine.evaluate_tracks(tracked_objects, timestamp)
                    total_zone_violations += len(violations)
                    total_line_crossings += len(crossings)
                    active_viols = {v["zone_id"] for v in violations}
                    annotated_frame = VisualAnnotator.draw_zones(annotated_frame, zone_engine.zones, active_viols)
                    annotated_frame = VisualAnnotator.draw_counting_lines(annotated_frame, zone_engine.counting_lines)
                    annotated_frame = VisualAnnotator.draw_dynamic_danger_zones(
                        annotated_frame,
                        zone_engine.last_dynamic_danger_circles,
                        zone_engine.last_proximity_alerts
                    )

                # Draw tracked bounding boxes with persistent IDs
                for obj in tracked_objects:
                    cls_name = obj.get("class_name", "object")
                    track_id = obj["track_id"]
                    conf = obj.get("confidence", 0.0)
                    bbox = obj["bbox"]
                    naive_counts[cls_name] += 1

                    # Draw box and track label
                    x1, y1, x2, y2 = [int(v) for v in bbox]
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 200, 255), 2)
                    label = f"#{track_id} {cls_name} {conf:.2f}"
                    cv2.putText(annotated_frame, label, (x1, max(15, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 2)

                # Add Tracking & Zone HUD banner
                unique_p = tracker.get_unique_person_count()
                cv2.rectangle(annotated_frame, (10, 10), (450, 45), (20, 20, 25), -1)
                hud_txt = f"ByteTrack: {len(tracked_objects)} Active | Unique Persons: {unique_p}"
                cv2.putText(annotated_frame, hud_txt, (20, 33), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 180), 2)

            else:
                # Raw YOLO frame detection (Member 1 baseline)
                results = model.predict(frame, conf=args.conf, imgsz=640, device=device, verbose=False)[0]
                for box in results.boxes:
                    cls_id = int(box.cls[0])
                    cls_name = model.names[cls_id]
                    naive_counts[cls_name] += 1
                annotated_frame = results.plot(line_width=2, font_size=14)

            out.write(annotated_frame)

            if show_preview:
                try:
                    cv2.imshow("SiteSense Detection & Tracking (Press 'q' to stop)", annotated_frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        print("\n[INFO] Stopped early by user.")
                        break
                except Exception:
                    show_preview = False

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
    print("\n" + "=" * 60)
    print("📊 DETECTION & TRACKING SUMMARY")
    print("=" * 60)
    print(f"  Frames processed : {frame_idx}")
    print(f"  Time elapsed     : {elapsed:.1f} s (avg {frame_idx / elapsed if elapsed > 0 else 0:.1f} FPS)")

    print("\n[1] Naive Frame-Level Detections (Raw Over-Count):")
    if naive_counts:
        for name, count in naive_counts.most_common():
            print(f"  {name:<20}: {count} occurrences")
    else:
        print("  No objects detected.")

    if tracker is not None:
        print("\n[2] ByteTrack Persistent Unique Objects (Double-Count Free):")
        class_breakdown = tracker.get_unique_counts_by_class()
        unique_persons = tracker.get_unique_person_count()
        total_unique = tracker.get_total_unique_objects()
        print(f"  Unique Persons   : {unique_persons} (Avoided {naive_counts.get('person', 0) - unique_persons} duplicate counts)")
        print(f"  Total Unique IDs : {total_unique}")

    if zone_engine is not None:
        print("\n[3] Spatial Zone Intelligence:")
        print(f"  Zone Violations  : {total_zone_violations}")
        print(f"  Line Crossings   : {total_line_crossings}")

    print(f"\nSaved annotated video to: {output_path}")

    if not args.no_open and os.name == "nt" and output_path.exists():
        try:
            os.startfile(str(output_path))
        except Exception:
            pass


if __name__ == "__main__":
    main()
