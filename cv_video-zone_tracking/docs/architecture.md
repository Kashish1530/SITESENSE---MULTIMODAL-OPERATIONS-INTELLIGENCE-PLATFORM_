# 🏭 SiteSense — Video Analytics & Spatial Intelligence Architecture
## Member 2 Deliverables: Feature 2.3 (Video Tracking) & Feature 2.4 (Zone Engine)

---

## 1. High-Level System Flow

```
+-----------------------------------------------------------------------------------------+
|                                    CCTV Video Feed                                      |
+-----------------------------------------------------------------------------------------+
                                             |
                                             v
+-----------------------------------------------------------------------------------------+
|                        DELIVERABLE 1: VIDEO READER (video_reader.py)                    |
| - OpenCV frame generator with accurate PTS/POS_MSEC timestamp synchronization           |
| - Missing sequence / dropped frame counter for variable framerate streams                |
| - Clean End-of-Stream (EOS) resource deallocation without memory leaks                  |
+-----------------------------------------------------------------------------------------+
                                             | (Frame, Timestamp)
                                             v
+-----------------------------------------------------------------------------------------+
|                       MEMBER 1: OBJECT DETECTIONS (classes.yaml)                        |
| - 16 Canonical Classes: person, safety_helmet, safety_vest, pallet, forklift, etc.      |
+-----------------------------------------------------------------------------------------+
                                             | Detections [class_id, bbox, conf]
                                             v
+-----------------------------------------------------------------------------------------+
|                    DELIVERABLE 2: PERSISTENT TRACKER (tracker.py)                       |
| - ByteTrack two-stage Kalman filter & high/low confidence IoU association               |
| - Persistent Track IDs (prevents duplicate counting: 200 frame detections -> 9 persons) |
| - Trajectory history buffer & persistent unique count registry                          |
+-----------------------------------------------------------------------------------------+
                                             | Tracked Objects [track_id, class_id, bbox]
                                             v
+-----------------------------------------------------------------------------------------+
|                  DELIVERABLE 3: SPATIAL ZONE ENGINE (zone_engine.py)                    |
| - Camera-agnostic JSON polygon loaders (CAM_001, CAM_002, CAM_003_UNSEEN)               |
| - Bottom-center ground contact point math (x_mid, y2) to eliminate upper-body false alarms |
| - Dwell time duration timer with debounce threshold per restricted zone                |
| - Directional virtual counting lines (Vector cross-product: ENTERED vs EXITED)          |
+-----------------------------------------------------------------------------------------+
                                             |
                                             v
+-----------------------------------------------------------------------------------------+
|                  DOWNSTREAM HANDOFF (tracking_metrics.py / pipeline.py)                 |
| -> Output A: outputs/tracking/tracking_results.csv (Per-frame track coordinates)        |
| -> Output B: outputs/zone_events/zone_events.csv (Spatial violations & dwell durations) |
| -> Output C: outputs/reports/zone_summary.json (Executive counts & line flow)          |
| -> Central SQLite Violation DB & FastAPI Microservice (/vision/analyze-video)           |
+-----------------------------------------------------------------------------------------+
```

---

## 2. Mathematical Formulations

### 2.1 Ground Contact Foot-Point Geometry
To prevent leaning or tall objects from triggering false zone alarms, the contact point is strictly bottom-center:
$$x_{\text{foot}} = \frac{x_1 + x_2}{2.0}, \quad y_{\text{foot}} = y_2$$

### 2.2 Point-in-Polygon Containment
Evaluated using Shapely winding number / ray-casting algorithm:
$$\text{Inside}(P, \text{Zone}) = \text{Polygon}(\text{coords}).\text{contains}(\text{Point}(x_{\text{foot}}, y_{\text{foot}}))$$

### 2.3 Virtual Counting Line Directional Crossing
Virtual line defined by $P_1$ and $P_2$. The signed side of a point $P$ is given by the 2D cross product:
$$\text{side}(P) = (x_2 - x_1)(y - y_1) - (y_2 - y_1)(x - x_1)$$
Crossing occurs when consecutive frames switch signs:
$$\text{side}(P_{\text{prev}}) \cdot \text{side}(P_{\text{curr}}) < 0$$
* If $\text{side}(P_{\text{curr}}) > 0 \implies \textbf{ENTERED}$
* If $\text{side}(P_{\text{curr}}) < 0 \implies \textbf{EXITED}$

### 2.4 Dwell Time Calculation
$$\text{DwellTime} = t_{\text{current}} - t_{\text{entry}}$$
An active violation is emitted only when:
$$\text{DwellTime} \ge \text{Threshold}_{\text{zone}}$$
When an object exits the polygon, its active dwell record is evicted to prevent stale timers.
