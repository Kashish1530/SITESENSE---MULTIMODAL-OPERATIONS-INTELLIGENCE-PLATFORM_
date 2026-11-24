"""
scripts/benchmark_unique_count.py
SiteSense Task 2.3 Acceptance Benchmark & Verification
Demonstrates and validates:
1. Video frame-by-frame processing with persistent ByteTrack track IDs.
2. Prevention of duplicate counting: Compares naive per-frame detection count
   (which reports hundreds of people) against persistent unique person tracking.
3. Acceptance verification: Asserts unique person count against manual ground truth.
"""

import sys
import os
import argparse
import cv2
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from tracker import ByteTrackEngine

def run_unique_tracking_benchmark(video_path: str = "data/sample_videos/warehouse1.mp4", manual_ground_truth: int = 7, max_frames: int = None):
    print("=" * 75)
    print("🎯 SITESENSE — TASK 2.3 VIDEO TRACKING & UNIQUE PERSON BENCHMARK")
    print("=" * 75)

    if not os.path.exists(video_path):
        print(f"[!] Error: Video not found at '{video_path}'")
        return False

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[!] Error: Could not open video '{video_path}'")
        return False

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = total_frames / fps

    print(f"[*] Input Video Source: {video_path}")
    print(f"[*] Video Specs: {total_frames} frames @ {fps:.1f} FPS ({duration_sec:.1f}s)")
    print(f"[*] Manual Ground Truth Unique Person Count: {manual_ground_truth}")

    model_weights = "models/best_3.pt" if os.path.exists("models/best_3.pt") else "models/best.pt"
    tracker = ByteTrackEngine(model_weights=model_weights)

    frame_idx = 0
    naive_person_detections = 0

    print("[*] Processing frames with ByteTrack persistent tracker...")
    while cap.isOpened():
        if max_frames and frame_idx >= max_frames:
            break

        ret, frame = cap.read()
        if not ret:
            break

        tracked_objects = tracker.process_frame(frame)

        # Count naive detections for Class 0 (person)
        for obj in tracked_objects:
            if obj["class_id"] == 0:
                naive_person_detections += 1

        frame_idx += 1

    cap.release()

    unique_person_count = tracker.get_unique_person_count()
    unique_counts_by_class = tracker.get_unique_counts_by_class()
    total_unique_tracked = tracker.get_total_unique_objects()

    # Calculate error against manual count
    count_error = abs(unique_person_count - manual_ground_truth)
    error_percent = (count_error / max(1, manual_ground_truth)) * 100.0

    print("-" * 75)
    print(f"[*] Frames Analyzed:                         {frame_idx}")
    print(f"[*] Naive Non-Tracked Person Detections:     {naive_person_detections}")
    print(f"[*] ByteTrack Persistent Unique Persons:     {unique_person_count}")
    print(f"[*] Manual Ground-Truth Person Count:        {manual_ground_truth}")
    print(f"[*] Total Tracked Objects Across Taxonomy:   {total_unique_tracked}")
    print(f"[*] Class Breakdown:                         {unique_counts_by_class}")
    print(f"[*] Count Discrepancy Error:                 {count_error} ({error_percent:.1f}%)")
    print("-" * 75)

    # Acceptance check (within stated error of manual count, <= 15%)
    passed = error_percent <= 15.0
    if passed:
        print(f"✅ ACCEPTANCE CRITERIA PASSED: Error {error_percent:.1f}% is within acceptable error margin (<= 15%).")
        print(f"   Persistent tracking successfully avoided false duplicate counts ({naive_person_detections} -> {unique_person_count}).")
    else:
        print(f"⚠️ Notice: Stated error {error_percent:.1f}% exceeds benchmark margin.")

    print("=" * 75)
    return passed

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SiteSense Task 2.3 Benchmark")
    parser.add_argument("--video", default="data/sample_videos/warehouse1.mp4", help="Path to video clip")
    parser.add_argument("--ground_truth", type=int, default=7, help="Manual count of unique persons")
    parser.add_argument("--max_frames", type=int, default=100, help="Max frames to test")
    args = parser.parse_args()

    success = run_unique_tracking_benchmark(
        video_path=args.video,
        manual_ground_truth=args.ground_truth,
        max_frames=args.max_frames
    )
    sys.exit(0 if success else 1)
