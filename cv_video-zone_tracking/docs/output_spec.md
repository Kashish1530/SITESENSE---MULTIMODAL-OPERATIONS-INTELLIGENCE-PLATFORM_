# 📋 Member 3 & Agentic AI Output Specification
## Standardized Data Formats Emitted by Video Analytics Engine (Member 2)

Member 2 automatically exports three standardized outputs after processing every video stream.

---

### Output A: `outputs/tracking/tracking_results.csv`
Used by Member 3 for trajectory reconstruction and forensic replay.

| Column | Type | Example | Description |
|---|---|---|---|
| `frame` | `int` | `120` | Frame sequence index |
| `timestamp` | `float` | `4.80` | Video timestamp in seconds (PTS-synchronized) |
| `track_id` | `int` | `12` | Persistent ByteTrack entity identifier |
| `class_id` | `int` | `0` | Taxonomy class ID (0–15) |
| `class_name` | `string` | `"person"` | Human-readable object label |
| `confidence` | `float` | `0.925` | Model detection confidence score |
| `bbox_x1` | `int` | `450` | Bounding box top-left X coordinate |
| `bbox_y1` | `int` | `250` | Bounding box top-left Y coordinate |
| `bbox_x2` | `int` | `498` | Bounding box bottom-right X coordinate |
| `bbox_y2` | `int` | `370` | Bounding box bottom-right Y coordinate |

---

### Output B: `outputs/zone_events/zone_events.csv`
Directly consumed by Member 3 Rules Engine and Human Review Queue.

| Column | Type | Example | Description |
|---|---|---|---|
| `track_id` | `int` | `101` | Entity violating spatial boundary |
| `zone_id` | `string` | `"ZONE_EXIT_01"` | Canonical zone identifier from config |
| `zone_name` | `string` | `"Emergency Fire Exit Doorway"` | Friendly name of zone |
| `event` | `string` | `"ACTIVE_VIOLATION"` | Spatial event state |
| `timestamp` | `float` | `14.50` | Event timestamp in seconds |
| `dwell_time` | `float` | `4.50` | Total seconds target has continuously blocked zone |
| `severity` | `string` | `"CRITICAL"` | Alert severity: `CRITICAL` or `HIGH` |

---

### Output C: `outputs/reports/zone_summary.json`
Directly consumed by Manager Workspace Dashboard and Agentic AI `get_site_findings` tool.

```json
{
  "site_id": "SITE_WH_01",
  "camera_id": "CAM_001",
  "unique_person_count": 9,
  "total_entries": 4,
  "total_exits": 2,
  "counting_lines": {
    "aisle_entry_counter": {
      "entries": 4,
      "exits": 2
    }
  },
  "zones": [
    {
      "zone_id": "ZONE_EXIT_01",
      "zone_name": "Main Emergency Fire Exit Doorway",
      "zone_type": "exclusion",
      "alert_severity": "CRITICAL",
      "current_occupancy": 1,
      "blockage_threshold_seconds": 4.0
    },
    {
      "zone_id": "ZONE_AISLE_01",
      "zone_name": "Walkway Aisle 3",
      "zone_type": "walkway",
      "alert_severity": "HIGH",
      "current_occupancy": 0,
      "blockage_threshold_seconds": 4.0
    }
  ]
}
```
