"""
tests/test_video_reader.py
Unit tests for VideoReader module (Feature 2.3: Video Reader & Stream Handler).
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
from video_reader import VideoReader

SAMPLE_VIDEO = "data/sample_videos/warehouse1.mp4"

def test_video_reader_metadata():
    reader = VideoReader(SAMPLE_VIDEO)
    meta = reader.get_metadata()
    
    assert meta["video_name"] == "warehouse1.mp4"
    assert meta["fps"] > 0
    assert meta["width"] > 0
    assert meta["height"] > 0
    assert meta["total_frames"] > 0
    assert meta["duration_seconds"] > 0
    assert meta["end_of_stream"] is False
    reader.release()

def test_video_reader_frames_generator_and_eos():
    max_frames = 15
    reader = VideoReader(SAMPLE_VIDEO, max_frames=max_frames)
    
    frames_read = 0
    for idx, ts, frame in reader.frames():
        assert idx == frames_read
        assert ts >= 0.0
        assert frame is not None
        assert frame.shape[0] == reader.height
        assert frame.shape[1] == reader.width
        frames_read += 1

    assert frames_read == max_frames
    reader.release()

def test_video_reader_invalid_file():
    with pytest.raises(FileNotFoundError):
        VideoReader("non_existent_video_file.mp4")

def test_metadata_csv_export(tmp_path):
    csv_file = str(tmp_path / "metadata_test.csv")
    reader = VideoReader(SAMPLE_VIDEO, max_frames=5)
    # Drain generator
    list(reader.frames())
    reader.export_metadata_csv(csv_file)
    
    assert os.path.exists(csv_file)
    with open(csv_file, "r") as f:
        content = f.read()
        assert "warehouse1.mp4" in content
        assert "total_frames" in content
