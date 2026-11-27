"""
video_reader.py
SiteSense Feature 2.3 — Video Reader & Stream Handler Module

Responsibilities:
- Robust video stream / file opening with validation.
- Frame-by-frame decoding with persistent frame sequence indexing.
- Precise timestamp extraction (PTS / POS_MSEC) resilient to dropped frames.
- Frame drop detection and missing frame sequence accounting.
- Graceful End-of-Stream (EOS) detection without memory leaks or infinite loops.
- Metadata extraction (FPS, resolution, duration, frame count) and CSV/JSON export.
"""

import cv2
import os
import csv
import json
from typing import Generator, Tuple, Dict, Any, Optional

class VideoReader:
    def __init__(self, video_path: str, max_frames: Optional[int] = None):
        """
        Initializes the VideoReader with path validation and stream inspection.
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found at: {video_path}")

        self.video_path = video_path
        self.max_frames = max_frames
        self.cap = cv2.VideoCapture(video_path)

        if not self.cap.isOpened():
            raise RuntimeError(f"Failed to open video source: {video_path}")

        # Core stream properties
        self.fps = float(self.cap.get(cv2.CAP_PROP_FPS) or 25.0)
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration_seconds = (self.total_frames / self.fps) if self.fps > 0 else 0.0

        # State tracking
        self.current_frame_idx = 0
        self.dropped_frames_count = 0
        self.last_pos_msec = 0.0
        self.is_eos = False
        self._released = False

    def get_metadata(self) -> Dict[str, Any]:
        """Returns standard metadata dictionary for logging and CSV export."""
        return {
            "video_name": os.path.basename(self.video_path),
            "video_path": os.path.abspath(self.video_path),
            "fps": round(self.fps, 2),
            "width": self.width,
            "height": self.height,
            "total_frames": self.total_frames,
            "duration_seconds": round(self.duration_seconds, 2),
            "dropped_frames": self.dropped_frames_count,
            "end_of_stream": self.is_eos
        }

    def export_metadata_csv(self, output_csv_path: str):
        """Exports video stream metadata to CSV format."""
        os.makedirs(os.path.dirname(os.path.abspath(output_csv_path)), exist_ok=True)
        meta = self.get_metadata()
        with open(output_csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(meta.keys()))
            writer.writeheader()
            writer.writerow(meta)

    def frames(self) -> Generator[Tuple[int, float, Any], None, None]:
        """
        Generator yielding (frame_index, timestamp_seconds, frame_ndarray).
        Handles dropped frames, calculates timestamp accurately, and terminates gracefully on EOS.
        """
        try:
            expected_interval_ms = (1000.0 / self.fps) if self.fps > 0 else 40.0

            while self.cap.isOpened():
                if self.max_frames and self.current_frame_idx >= self.max_frames:
                    break

                ret, frame = self.cap.read()
                if not ret or frame is None:
                    # End of Stream reached
                    self.is_eos = True
                    break

                # Accurate timestamp extraction (using PTS if available)
                pos_msec = self.cap.get(cv2.CAP_PROP_POS_MSEC)
                if pos_msec and pos_msec > 0:
                    timestamp = pos_msec / 1000.0
                    # Detect dropped frames if delta between timestamps is unexpectedly large
                    if self.current_frame_idx > 0 and (pos_msec - self.last_pos_msec) > (expected_interval_ms * 1.8):
                        estimated_dropped = int((pos_msec - self.last_pos_msec) / expected_interval_ms) - 1
                        if estimated_dropped > 0:
                            self.dropped_frames_count += estimated_dropped
                    self.last_pos_msec = pos_msec
                else:
                    timestamp = self.current_frame_idx / self.fps

                yield self.current_frame_idx, timestamp, frame
                self.current_frame_idx += 1

        finally:
            self.release()

    def release(self):
        """Ensures OpenCV VideoCapture handle is released cleanly."""
        if not self._released:
            if self.cap is not None and self.cap.isOpened():
                self.cap.release()
            self._released = True
