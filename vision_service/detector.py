"""
SITESENSE - Multi-Model Detection Inference Service (Feature 2.2)
Supports:
1. Primary 16-Class Warehouse & Operational Site Model (best_16class.pt / best.pt)
2. Construction Site PPE & Heavy Machinery Model (best_construction.pt)
3. Dynamic Model Ensemble: Runs both models and merges detections with Non-Maximum Suppression (NMS)
4. Extensible registry: Automatically detects newly dropped .pt weights in models/
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Union, Optional
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "models"

# Class name normalization mapping
CLASS_SYNONYMS = {
    "hardhat": "safety_helmet",
    "safety-helmet": "safety_helmet",
    "safety-vest": "safety_vest",
    "safet--fire-extinguisher": "fire_extinguisher",
    "fire-extinguisher": "fire_extinguisher",
    "fire-hose": "fire_hose",
    "pallets": "pallet",
    "safety-signage": "safety_signage",
    "exit-sign": "exit_sign",
    "empty-shelf": "empty_shelf",
    "truck": "vehicle",
    "vehicle/truck": "vehicle",
    "safety-cone": "safety_cone"
}


def calculate_iou(boxA, boxB):
    """Calculates Intersection over Union for two [x1, y1, x2, y2] boxes."""
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    unionArea = float(boxAArea + boxBArea - interArea)

    if unionArea <= 0:
        return 0.0
    return interArea / unionArea


class MultiModelDetectionService:
    def __init__(self, confidence_threshold: float = 0.25):
        self.confidence_threshold = confidence_threshold
        self.models: Dict[str, Any] = {}
        self._load_available_models()

    def _load_model(self):
        """Backwards compatible alias for loading models."""
        self._load_available_models()

    def _load_available_models(self):
        """Discovers and loads all trained models present in the models/ directory."""
        """Discovers and loads all trained models present in the models/ directory."""
        from ultralytics import YOLO

        MODELS_DIR.mkdir(exist_ok=True)
        discovered_files = list(MODELS_DIR.glob("*.pt"))

        # Dedicated aliases
        model_candidates = {
            "16class": MODELS_DIR / "best_16class.pt",
            "construction": MODELS_DIR / "best_construction.pt",
            "primary": MODELS_DIR / "best.pt"
        }

        for alias, path in model_candidates.items():
            if path.exists() and alias not in self.models:
                try:
                    print(f"[DetectionService] Loading model '{alias}' from {path.name}...")
                    self.models[alias] = YOLO(str(path))
                except Exception as e:
                    print(f"[DetectionService Warning] Failed to load {alias}: {e}")

        # Load any other custom models uploaded by the user
        for model_file in discovered_files:
            stem = model_file.stem
            if stem not in self.models and stem not in ["best_3"]:
                try:
                    print(f"[DetectionService] Registering dynamic model '{stem}' from {model_file.name}...")
                    self.models[stem] = YOLO(str(model_file))
                except Exception as e:
                    pass

        # Fallback if no custom models exist
        if not self.models:
            print("[DetectionService] No custom models found. Using yolov8n.pt as baseline.")
            self.models["baseline"] = YOLO("yolov8n.pt")

    def detect(
        self,
        image_input: Union[str, Image.Image],
        zone: str = None,
        model_name: Optional[str] = "ensemble"
    ) -> List[Dict[str, Any]]:
        """
        Runs object detection and outputs standard SiteSense contract shape:
        [{'bbox': [x1, y1, x2, y2], 'class_name': str, 'confidence': float, 'zone': Optional[str], 'source_model': str}]
        """
        if not self.models:
            self._load_available_models()

        # If specific single model requested
        if model_name in self.models:
            return self._run_single_model(self.models[model_name], image_input, zone, model_name)

        # Default: Ensemble mode across available models
        raw_detections = []
        # Run primary / 16class
        if "16class" in self.models:
            raw_detections.extend(self._run_single_model(self.models["16class"], image_input, zone, "16class"))
        elif "primary" in self.models:
            raw_detections.extend(self._run_single_model(self.models["primary"], image_input, zone, "primary"))

        # Run construction model if present
        if "construction" in self.models:
            raw_detections.extend(self._run_single_model(self.models["construction"], image_input, zone, "construction"))

        # If neither loaded, run whatever is loaded
        if not raw_detections and self.models:
            first_model_name = next(iter(self.models))
            raw_detections.extend(self._run_single_model(self.models[first_model_name], image_input, zone, first_model_name))

        # Merge overlapping detections via NMS
        merged = self._non_max_suppression(raw_detections, iou_thresh=0.55)
        return merged

    def _run_single_model(self, yolo_model, image_input, zone, model_tag) -> List[Dict[str, Any]]:
        results = yolo_model(image_input, conf=self.confidence_threshold, verbose=False)
        detections = []

        for r in results:
            boxes = r.boxes
            for box in boxes:
                xyxy = [round(float(coord), 1) for coord in box.xyxy[0].tolist()]
                conf = round(float(box.conf[0]), 4)
                cls_id = int(box.cls[0])
                raw_cls = r.names.get(cls_id, f"class_{cls_id}")
                norm_cls = CLASS_SYNONYMS.get(raw_cls.lower(), raw_cls.lower())

                detections.append({
                    "class_name": norm_cls,
                    "raw_class": raw_cls,
                    "bbox": xyxy,
                    "confidence": conf,
                    "zone": zone,
                    "source_model": model_tag
                })
        return detections

    def _non_max_suppression(self, detections: List[Dict[str, Any]], iou_thresh: float = 0.55) -> List[Dict[str, Any]]:
        """Deduplicates overlapping bounding boxes across ensemble models."""
        if not detections:
            return []

        # Sort by confidence descending
        sorted_dets = sorted(detections, key=lambda d: d["confidence"], reverse=True)
        selected = []

        while sorted_dets:
            best = sorted_dets.pop(0)
            selected.append(best)

            # Filter out overlapping detections of the same or compatible class
            remaining = []
            for det in sorted_dets:
                iou = calculate_iou(best["bbox"], det["bbox"])
                same_class = (best["class_name"] == det["class_name"])
                # If high IoU and same class, discard the lower confidence one
                if iou > iou_thresh and same_class:
                    continue
                remaining.append(det)
            sorted_dets = remaining

        return selected

    def list_loaded_models(self) -> Dict[str, List[str]]:
        """Returns loaded model names and their respective class lists."""
        info = {}
        for name, m in self.models.items():
            info[name] = list(m.names.values())
        return info


# Global singleton instance
detector = MultiModelDetectionService()
