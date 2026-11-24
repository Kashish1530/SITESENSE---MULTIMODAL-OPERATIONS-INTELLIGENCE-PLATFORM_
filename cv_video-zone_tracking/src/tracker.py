import numpy as np
from ultralytics import YOLO
from typing import List, Dict, Set, Optional

class ByteTrackEngine:
    def __init__(self, model_weights: str = "models/best.pt"):
        """
        model_weights: Trained YOLO model path (e.g. 'models/best.pt')
        """
        self.model = YOLO(model_weights)
        self.track_history: Dict[int, List[List[int]]] = {}
        # Persistent unique track registry across entire video session (Feature 2.3)
        self.unique_tracks_by_class: Dict[int, Set[int]] = {}
        self.all_unique_tracks: Set[int] = set()

    def process_frame(self, frame: np.ndarray) -> List[Dict]:
        """
        Runs YOLO + ByteTrack association on a single frame.
        Returns tracked objects with persistent track IDs.
        Uses exact 16-class taxonomy directly from trained model.
        """
        results = self.model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            conf=0.25,
            iou=0.45,
            verbose=False
        )
        
        tracked_objects = []
        if results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes
            for i in range(len(boxes)):
                track_id = int(boxes.id[i].item())
                class_id = int(boxes.cls[i].item())
                conf = float(boxes.conf[i].item())
                x1, y1, x2, y2 = [int(v) for v in boxes.xyxy[i].tolist()]
                
                # Maintain trajectory
                if track_id not in self.track_history:
                    self.track_history[track_id] = []
                self.track_history[track_id].append([(x1 + x2) // 2, y2])
                
                # Register unique entities (avoids duplicate counting across 3+ minute videos)
                self.all_unique_tracks.add(track_id)
                if class_id not in self.unique_tracks_by_class:
                    self.unique_tracks_by_class[class_id] = set()
                self.unique_tracks_by_class[class_id].add(track_id)

                tracked_objects.append({
                    "track_id": track_id,
                    "class_id": class_id,
                    "confidence": conf,
                    "bbox": [x1, y1, x2, y2]
                })
                
        return tracked_objects

    def get_unique_person_count(self) -> int:
        """Returns the distinct number of unique individuals tracked (class_id=0)."""
        return len(self.unique_tracks_by_class.get(0, set()))

    def get_unique_counts_by_class(self) -> Dict[int, int]:
        """Returns unique track count for each detected class ID."""
        return {cls_id: len(tracks) for cls_id, tracks in self.unique_tracks_by_class.items()}

    def get_total_unique_objects(self) -> int:
        """Returns total distinct track IDs observed across the session."""
        return len(self.all_unique_tracks)

    def reset(self):
        """Resets tracking state for a new video feed."""
        self.track_history.clear()
        self.unique_tracks_by_class.clear()
        self.all_unique_tracks.clear()

