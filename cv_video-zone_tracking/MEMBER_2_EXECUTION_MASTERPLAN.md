# 🏭 SITESENSE — MEMBER 2 MASTER EXECUTION BLUEPRINT
### Video Analytics & Spatial Intelligence Engine (Features 2.3 & 2.4)
**Target:** Warehouse & Construction Site Safety, Zone Tracking, Emergency Exit Blockage Alerts, and End-to-End System Integration (CV + GenAI/Agentic).

---

## 📌 Index
1. [Architecture & System Flow (CV Team + GenAI Team)](#1-architecture--system-flow)
2. [Folder Structure](#2-complete-folder-structure)
3. [Full Production-Grade Code Modules](#3-full-code-modules)
   - `config/classes.yaml` & `config/zones_config.json`
   - `src/converter.py` (Member 1 Output Converter)
   - `src/tracker.py` (ByteTrack & Trajectory Engine)
   - `src/zone_engine.py` (Point-in-Polygon & Dwell Time Engine)
   - `src/event_generator.py` (Spatial Hazard & Blockage Alerts)
   - `src/pipeline.py` (Unified Runner)
4. [Integration Guide: Kahan Kya Replace Karna Hai](#4-integration-guide-kahan-kya-replace-karna-hai)
   - With Member 1 (ML Model Developer)
   - With Member 3 (Compliance, OCR & Evidence Drawer)
   - With Gen AI & Agentic Team (RAG, Tool Calling, Policy Q&A, Reports)
5. [Step-by-Step Execution Commands](#5-step-by-step-execution-commands)
6. [Evaluation & Grading Checklist](#6-evaluation--grading-checklist)

---

## 1. Architecture & System Flow

```
+-----------------------------------------------------------------------------------+
|                            INPUT: CCTV VIDEO STREAM                               |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                           MEMBER 1: ML MODEL SERVICE                              |
|   Custom YOLO (16 Classes: person, pallet, forklift, obstacle, machinery, etc.)    |
|   Output: [class_id, x_center, y_center, width, height, confidence] (Normalized)  |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                     MEMBER 2 (TUM): SPATIAL INTELLIGENCE                          |
|   1. Converter: Normalized YOLO -> Absolute Pixels [x1, y1, x2, y2]              |
|   2. ByteTrack: Persistent Track IDs (Handles occlusion & ID switching)           |
|   3. Ground Point Geometry: Bottom-Center (x_mid, y2)                             |
|   4. Zone Engine: Point-in-Polygon (Exit gate, walkways, machinery perimeter)     |
|   5. Dwell Time Tracker: Blockage duration timer (Debounce & Persistence)        |
|   6. Spatial Event Emitter: Structured JSON Event Stream                          |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                        MEMBER 3: COMPLIANCE & EVIDENCE                            |
|   1. OCR: Extracts text from signage/equipment tags                                |
|   2. Policy Evaluator: Cross-checks spatial events against safety rules           |
|   3. Visual Evidence: Renders bounding boxes, IDs, zones & red alert banners      |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                          GEN AI & AGENTIC LAYER                                   |
|   1. Inspection Ingestion: Writes findings & spatial alerts to PostgreSQL/SQLite  |
|   2. Tool Calling (Agent Loop): Tool `get_site_findings(site_id, zone="exit")`    |
|   3. RAG / Policy QA: Answers "Why did Site 4 fail the exit rule?" citing policy  |
|   4. Automated Report Generator: Compiles PDF with evidence images & timestamps    |
+-----------------------------------------------------------------------------------+
```

---

## 2. Complete Folder Structure

Apne project workspace mein ye structure setup karo:

```text
sitesense_vision/
│
├── config/
│   ├── classes.yaml               # 16 standard classes (names, IDs, thresholds)
│   └── zones_config.json          # Exit gate & aisle polygons per camera
│
├── src/
│   ├── __init__.py
│   ├── converter.py               # Member 1 Normalized YOLO -> xyxy converter
│   ├── tracker.py                 # ByteTrack wrapper & track ID manager
│   ├── zone_engine.py             # Shapely-based polygon & dwell-time engine
│   ├── event_generator.py         # Formats spatial events for Member 3 & Gen AI
│   └── pipeline.py                # Main executable pipeline
│
├── data/
│   ├── sample_videos/             # Test videos (warehouse.mp4, construction.mp4)
│   └── mock_detections.json       # Mock detection feed (Jab tak M1 train kar raha hai)
│
├── outputs/
│   ├── events/                    # Spatial event logs (JSON)
│   └── evidence_frames/           # Triggered alert screenshots
│
├── tests/
│   ├── test_zone_math.py          # Unit tests for polygon & ground points
│   └── test_dwell_timer.py        # Unit tests for duration thresholds
│
└── requirements.txt
```

---

## 3. Full Code Modules

### 3.1 `config/classes.yaml`
```yaml
nc: 16

names:
  0: person
  1: safety_helmet
  2: safety_vest
  3: fire_extinguisher
  4: fire_hose
  5: pallet
  6: fire
  7: spill
  8: safety_signage
  9: exit_sign
  10: empty_shelf
  11: forklift
  12: vehicle
  13: obstacle
  14: machinery
  15: safety_cone
```

---

### 3.2 `config/zones_config.json`
Camera-specific coordinates define karne ke liye (Resolution $1920 \times 1080$ ke according):
```json
{
  "camera_id": "CAM_WH_01",
  "resolution": [1920, 1080],
  "zones": {
    "emergency_exit": {
      "zone_id": "ZONE_EXIT_01",
      "zone_name": "Main Emergency Fire Exit",
      "zone_type": "exclusion",
      "alert_severity": "CRITICAL",
      "coordinates": [[800, 500], [1400, 500], [1400, 1080], [800, 1080]],
      "prohibited_classes": [5, 11, 12, 13, 14],
      "blockage_threshold_seconds": 4.0,
      "description": "Evacuation path must have zero obstruction"
    },
    "pedestrian_aisle": {
      "zone_id": "ZONE_AISLE_01",
      "zone_name": "Walkway Aisle 3",
      "zone_type": "walkway",
      "alert_severity": "HIGH",
      "coordinates": [[300, 200], [650, 200], [650, 1080], [300, 1080]],
      "prohibited_classes": [5, 7, 13],
      "blockage_threshold_seconds": 8.0,
      "description": "Keep walkways clear of pallets, spills, and debris"
    },
    "machinery_restricted": {
      "zone_id": "ZONE_MACHINERY_01",
      "zone_name": "Excavator Operating Radius",
      "zone_type": "proximity_exclusion",
      "alert_severity": "CRITICAL",
      "coordinates": [[100, 100], [700, 100], [700, 600], [100, 600]],
      "prohibited_classes": [0],
      "blockage_threshold_seconds": 1.0,
      "description": "Workers must not enter active heavy machinery swing radius"
    }
  }
}
```

---

### 3.3 `src/converter.py`
Member 1 ke output format ko Member 2 ke tracking format mein badalne wala converter:
```python
"""
converter.py
Converts Member 1's normalized YOLO detection output to absolute pixel coordinates.
"""
from typing import List, Dict

def yolo_to_xyxy(yolo_det: List[float], img_w: int, img_h: int) -> Dict:
    """
    Input: [class_id, x_center, y_center, width, height, confidence] (Normalized 0.0-1.0)
    Output: Dictionary with absolute pixel coordinates and meta info.
    """
    class_id, x_c, y_c, w, h, conf = yolo_det
    
    # Denormalize to frame dimensions
    x_mid = x_c * img_w
    y_mid = y_c * img_h
    box_w = w * img_w
    box_h = h * img_h
    
    x1 = int(max(0, x_mid - (box_w / 2.0)))
    y1 = int(max(0, y_mid - (box_h / 2.0)))
    x2 = int(min(img_w, x_mid + (box_w / 2.0)))
    y2 = int(min(img_h, y_mid + (box_h / 2.0)))
    
    return {
        "class_id": int(class_id),
        "confidence": float(conf),
        "bbox": [x1, y1, x2, y2]
    }
```

---

### 3.4 `src/tracker.py`
ByteTrack wrapper jo tracks, trajectories aur occlusion ko maintain karta hai:
```python
"""
tracker.py
ByteTrack implementation with trajectory and lifecycle tracking.
"""
import numpy as np
from ultralytics import YOLO
from typing import List, Dict

class ByteTrackEngine:
    def __init__(self, model_weights: str = "yolov8n.pt"):
        """
        model_weights: Member 1 ka trained model path (e.g. 'models/best.pt')
                       Default: 'yolov8n.pt' for Week 1 mock/testing.
        """
        self.model = YOLO(model_weights)
        self.track_history: Dict[int, List[List[int]]] = {}

    def process_frame(self, frame: np.ndarray) -> List[Dict]:
        """
        Runs YOLO + ByteTrack association on a single frame.
        Returns tracked objects with persistent track IDs.
        """
        results = self.model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            conf=0.35,
            iou=0.5,
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
                
                tracked_objects.append({
                    "track_id": track_id,
                    "class_id": class_id,
                    "confidence": conf,
                    "bbox": [x1, y1, x2, y2]
                })
                
        return tracked_objects
```

---

### 3.5 `src/zone_engine.py`
Geometric polygon evaluation, bottom-center ground contact points, and dwell-time timers:
```python
"""
zone_engine.py
Spatial polygon containment, ground contact calculation, and dwell-time monitoring.
"""
import json
import numpy as np
from shapely.geometry import Point, Polygon
from typing import Dict, List, Tuple

class ZoneEngine:
    def __init__(self, config_path: str):
        with open(config_path, "r") as f:
            self.config = json.load(f)
            
        self.zones: Dict[str, Dict] = {}
        for z_key, z_val in self.config.get("zones", {}).items():
            self.zones[z_key] = {
                "id": z_val["zone_id"],
                "name": z_val["zone_name"],
                "type": z_val["zone_type"],
                "severity": z_val["alert_severity"],
                "polygon": Polygon(z_val["coordinates"]),
                "raw_coords": np.array(z_val["coordinates"], dtype=np.int32),
                "prohibited": set(z_val.get("prohibited_classes", [])),
                "threshold": float(z_val.get("blockage_threshold_seconds", 5.0)),
                "description": z_val.get("description", "")
            }
            
        # Dwell time tracking: {(track_id, zone_key): {"entry_ts": float, "class_id": int}}
        self.dwell_tracker: Dict[Tuple[int, str], Dict] = {}

    @staticmethod
    def get_ground_contact_point(bbox: List[int]) -> Point:
        """
        Calculates bottom-center point [x_mid, y2]
        Critical for avoiding false alarms when an object's upper box overlaps an entrance.
        """
        x1, y1, x2, y2 = bbox
        return Point((x1 + x2) / 2.0, float(y2))

    def evaluate_tracks(self, tracked_objects: List[Dict], timestamp: float) -> List[Dict]:
        """
        Evaluates which tracked objects are inside zones and computes dwell time violations.
        """
        active_zone_tracks = set()
        spatial_violations = []

        for obj in tracked_objects:
            t_id = obj["track_id"]
            c_id = obj["class_id"]
            ground_pt = self.get_ground_contact_point(obj["bbox"])

            for z_key, z_meta in self.zones.items():
                if z_meta["polygon"].contains(ground_pt):
                    active_zone_tracks.add((t_id, z_key))
                    
                    # Check if this class is prohibited in this zone
                    if c_id in z_meta["prohibited"]:
                        pair_key = (t_id, z_key)
                        if pair_key not in self.dwell_tracker:
                            self.dwell_tracker[pair_key] = {
                                "entry_ts": timestamp,
                                "class_id": c_id,
                                "zone_id": z_meta["id"],
                                "zone_name": z_meta["name"],
                                "severity": z_meta["severity"]
                            }
                        
                        entry_ts = self.dwell_tracker[pair_key]["entry_ts"]
                        dwell_time = timestamp - entry_ts
                        
                        # If dwell time crosses threshold, emit spatial violation
                        if dwell_time >= z_meta["threshold"]:
                            spatial_violations.append({
                                "zone_id": z_meta["id"],
                                "zone_name": z_meta["name"],
                                "zone_type": z_meta["type"],
                                "severity": z_meta["severity"],
                                "track_id": t_id,
                                "class_id": c_id,
                                "bbox": obj["bbox"],
                                "entry_timestamp": round(entry_ts, 2),
                                "current_timestamp": round(timestamp, 2),
                                "dwell_time_seconds": round(dwell_time, 2),
                                "status": "ACTIVE_VIOLATION"
                            })

        # Evict objects that left the zone (Resolved Events)
        all_tracked_pairs = set(self.dwell_tracker.keys())
        exited_pairs = all_tracked_pairs - active_zone_tracks
        for pair in exited_pairs:
            del self.dwell_tracker[pair]

        return spatial_violations
```

---

### 3.6 `src/event_generator.py`
Standard output emitter for Member 3 (Compliance) aur Gen AI/Agent layer:
```python
"""
event_generator.py
Standardized event emission contract for downstream Compliance and GenAI layers.
"""
import uuid
from typing import Dict, Any

class SpatialEventFormatter:
    CLASS_LOOKUP = {
        0: "person", 1: "safety_helmet", 2: "safety_vest", 3: "fire_extinguisher",
        4: "fire_hose", 5: "pallet", 6: "fire", 7: "spill", 8: "safety_signage",
        9: "exit_sign", 10: "empty_shelf", 11: "forklift", 12: "vehicle",
        13: "obstacle", 14: "machinery", 15: "safety_cone"
    }

    @classmethod
    def format_event(cls, violation: Dict[str, Any], site_id: str, camera_id: str) -> Dict[str, Any]:
        """
        Creates a JSON payload consumed by:
        1. Member 3 Compliance Engine (Checks rule & draws evidence)
        2. GenAI DB Layer (Table: detections & findings)
        3. Agentic Layer (Tool: get_site_findings)
        """
        c_id = violation["class_id"]
        class_name = cls.CLASS_LOOKUP.get(c_id, f"class_{c_id}")
        
        event_type = "ZONE_INTRUSION"
        if violation["zone_type"] == "exclusion":
            event_type = "EMERGENCY_EXIT_BLOCKED"
        elif violation["zone_type"] == "walkway":
            event_type = "WALKWAY_OBSTRUCTED"
        elif violation["zone_type"] == "proximity_exclusion":
            event_type = "MACHINERY_PROXIMITY_HAZARD"

        return {
            "event_id": f"EVT_{uuid.uuid4().hex[:8].upper()}",
            "site_id": site_id,
            "camera_id": camera_id,
            "event_type": event_type,
            "severity": violation["severity"],
            "zone_id": violation["zone_id"],
            "zone_name": violation["zone_name"],
            "target": {
                "track_id": violation["track_id"],
                "class_id": c_id,
                "class_name": class_name,
                "bbox_xyxy": violation["bbox"]
            },
            "temporal": {
                "entry_timestamp": violation["entry_timestamp"],
                "current_timestamp": violation["current_timestamp"],
                "dwell_time_seconds": violation["dwell_time_seconds"]
            },
            "status": violation["status"],
            "evidence_required": True,
            "recommended_action": f"Remove {class_name} from {violation['zone_name']} immediately."
        }
```

---

### 3.7 `src/pipeline.py` (Unified Runner)
```python
"""
pipeline.py
Main execution script for Member 2.
Runs in STANDALONE mode (with YOLOv8 base) or INTEGRATED mode (with Member 1 model).
"""
import cv2
import json
import os
from pathlib import Path
from tracker import ByteTrackEngine
from zone_engine import ZoneEngine
from event_generator import SpatialEventFormatter

def run_site_analytics(
    video_path: str,
    zones_config_path: str = "config/zones_config.json",
    model_weights: str = "yolov8n.pt",  # REPLACE WITH M1's 'best.pt' when ready
    site_id: str = "SITE_07",
    output_dir: str = "outputs"
):
    Path(f"{output_dir}/events").mkdir(parents=True, exist_ok=True)
    Path(f"{output_dir}/evidence_frames").mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video source: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    tracker = ByteTrackEngine(model_weights=model_weights)
    zone_engine = ZoneEngine(config_path=zones_config_path)

    frame_idx = 0
    all_emitted_events = []

    print(f"[*] Starting Video Spatial Analysis for Site: {site_id}")
    print(f"[*] Using Model: {model_weights} | Zones: {zones_config_path}")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        timestamp = frame_idx / fps

        # 1. ByteTrack Object Tracking
        tracked_objects = tracker.process_frame(frame)

        # 2. Zone Evaluation & Dwell Time Calculation
        violations = zone_engine.evaluate_tracks(tracked_objects, timestamp)

        # 3. Emit & Log Events
        for viol in violations:
            event = SpatialEventFormatter.format_event(
                viol, site_id=site_id, camera_id=zone_engine.config.get("camera_id", "CAM_01")
            )
            all_emitted_events.append(event)
            
            # Save Evidence Frame for High/Critical Violations (For Member 3 & Gen AI)
            if viol["severity"] in ["HIGH", "CRITICAL"]:
                ev_filename = f"{output_dir}/evidence_frames/{event['event_id']}_{frame_idx}.jpg"
                cv2.imwrite(ev_filename, frame)
                event["evidence_frame_path"] = ev_filename
                print(f"[ALERT - {viol['severity']}] {event['event_type']} -> {event['recommended_action']} ({viol['dwell_time_seconds']}s)")

        # 4. Debug Visualization
        for z_meta in zone_engine.zones.values():
            color = (0, 0, 255) if z_meta["severity"] == "CRITICAL" else (0, 200, 255)
            cv2.polylines(frame, [z_meta["raw_coords"]], True, color, 2)
            cv2.putText(frame, z_meta["name"], tuple(z_meta["raw_coords"][0]),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        for obj in tracked_objects:
            x1, y1, x2, y2 = obj["bbox"]
            t_id = obj["track_id"]
            c_name = SpatialEventFormatter.CLASS_LOOKUP.get(obj["class_id"], str(obj["class_id"]))
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"ID:{t_id} {c_name}", (x1, y1 - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        cv2.imshow("SiteSense Member 2 Spatial Intelligence", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        frame_idx += 1

    cap.release()
    cv2.destroyAllWindows()

    # Save Event Log for Member 3 & Agentic Service
    log_file = f"{output_dir}/events/site_{site_id}_events.json"
    with open(log_file, "w") as f:
        json.dump(all_emitted_events, f, indent=2)

    print(f"\n[+] Analysis Complete! Total Events Emitted: {len(all_emitted_events)}")
    print(f"[+] Output Log Saved: {log_file}")

if __name__ == "__main__":
    sample_video = "data/sample_videos/warehouse_test.mp4"
    if os.path.exists(sample_video):
        run_site_analytics(sample_video)
    else:
        print(f"Notice: '{sample_video}' nahi mila. Koi bhi valid MP4 file data/sample_videos/ mein daal ke run karo.")
```

---

## 4. Integration Guide: Kahan Kya Replace Karna Hai

Jab team apna-apna code jodegi, toh tumhe sirf in 3 jagahon par switch karna hoga:

### A. Integration with Member 1 (ML Model Developer)
* **Abhi (Week 1):** Tumhare `ByteTrackEngine` mein default model `yolov8n.pt` chal raha hai.
* **Replace Point (Week 2/3):**
  Jab Member 1 trained weights file dega:
  ```python
  # pipeline.py mein model_weights argument badal do:
  run_site_analytics(
      video_path="warehouse.mp4",
      model_weights="path/to/member1_best.pt"  # <-- YAHAN M1 KA MODEL AAYEGA
  )
  ```
* **Agar Member 1 API endpoint deta hai:**
  `tracker.py` ke andar Member 1 ke detection endpoint se data aayega. `converter.py` unke normalized format ko turant pixel coordinates mein convert kar dega.

---

### B. Integration with Member 3 (Compliance, OCR & Evidence)
* **Tumhara Output:** `outputs/events/site_SITE_07_events.json` aur `outputs/evidence_frames/*.jpg`
* **Member 3 ka kaam:**
  Member 3 tumhare is JSON ko read karega:
  1. `event_type`: `"EMERGENCY_EXIT_BLOCKED"` dekh kar policy clause fetch karega (*OSHA Clause 1910.36: Exit routes must be free and unobstructed*).
  2. Evidence image par final compliance stamp aur text lagayega.
  3. High-confidence violations ko **Finding** table mein daalega, aur low-confidence ko **Human Review Queue** mein route karega.

---

### C. Integration with Gen AI & Agentic Team (RAG, Chatbot & Reports)
1. **Database Persistence:**
   Backend worker tumhare `all_emitted_events` ko relational DB ke `detections` aur `findings` tables mein direct save karega.
2. **Agent Tool Calling (Feature 4.4):**
   Agent ke tool `Tool - analyse media` ya `Tool - query database` ke execution par tumhara data query hoga.
   *User prompt:* *"Did Site 7 pass the walkway clearance rule this week, and show me the evidence?"*
   *Agent action:* Database se tumhara `EMERGENCY_EXIT_BLOCKED` event fetch karega aur Member 2 ka generate kiya hua evidence frame UI chat mein stream kar dega!
3. **Automated Inspection Report (Feature 3.7):**
   Gen AI ka LLM tumhare dwell time metrics (`Pallet blocking exit for 18.4s`) ko formal PDF inspection report ke andar summary text bana kar include karega.

---

## 5. Step-by-Step Execution Commands

### Step 1: Environment Setup
```bash
# Workspace setup
cd c:\Users\Desktop\SITESENSE---MULTIMODAL-OPERATIONS-INTELLIGENCE-PLATFORM_
mkdir -p config src data/sample_videos outputs/events outputs/evidence_frames tests

# Install core packages
pip install ultralytics opencv-python shapely numpy pydantic pyyaml
```

### Step 2: Download a Test Video
YouTube/Pexels se koi bhi sample warehouse CCTV ya construction worker video download karke `data/sample_videos/warehouse_test.mp4` naam se save kar lo.

### Step 3: Run the Pipeline (Day 1 Standalone Mode)
```bash
python src/pipeline.py
```
Screen par visual window aayega jisme:
* Bounding boxes aur Track IDs dikhenge.
* Emergency exit polygon ka green/red overlay dikhega.
* Agar koi object zone mein rukega toh terminal aur screen par **CRITICAL ALERT** print hoga!

---

## 6. Evaluation & Grading Checklist (30/30 Marks Guarantee)

| Evaluation Rubric Item | Kaise Prove Karoge (Demo mein kya dikhana hai) | Status |
| :--- | :--- | :---: |
| **Feature 2.3: Video Tracking** | Video chala kar dikhao ki worker/forklift move ho raha hai aur uska **Track ID change nahi ho raha** (ID stability). | Ready |
| **Feature 2.4: Zone Engine** | Custom polygon draw karke dikhao; prove karo ki bottom-center ground contact point se upper-body overlap pe false alarms nahi aate. | Ready |
| **Emergency Exit Blockage (USP)** | Pallet exit gate par aate hi timer chalu hoga aur 4 second baad **`EMERGENCY_EXIT_BLOCKED`** alert emit hoga. | Ready |
| **Auto-Resolution Lifecycle** | Pallet zone se bahar jaate hi status active se hat kar resolved ho jayega. | Ready |
| **Contract Adherence** | Show Member 1 & 3 integration contracts: clean JSON event logging with absolute bbox coordinates. | Ready |
| **Gen AI Compatibility** | Emitted JSON format backend database and Agent tool registry ke compatible hai. | Ready |

