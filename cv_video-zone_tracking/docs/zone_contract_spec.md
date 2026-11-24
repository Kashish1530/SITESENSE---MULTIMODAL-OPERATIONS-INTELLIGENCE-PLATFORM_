# SiteSense — Dynamic Zone Configuration Interface Contract
**Owner**: Member 2 (Video Analytics & Spatial Intelligence)  
**Consumers**: Member 6 (Frontend / Admin Zone Editor - Screen 12 - M6.9), Member 3 (GenAI & Agentic AI)

---

## 1. Overview
The **Visual Zone Configuration Editor** enables Site Administrators to define, edit, and persist spatial zones (polygons) and virtual tripwires (counting lines) directly over live or uploaded camera frames.

To ensure stability across all modules:
1. **Member 2** provides:
   - The authoritative JSON schema (`config/zone_config_schema.json`).
   - Geometric and taxonomy validation (`src/zone_validator.py`).
   - REST API endpoints for reference frame capture, schema retrieval, validation, and hot-reload.
   - Reusable `ZoneEngine` that consumes the validated JSON without code modifications.
2. **Member 6 (Frontend)** provides:
   - The interactive canvas/drawing UI for polygon creation and coordinate submission.
3. **Member 3 (GenAI / Agentic AI)** provides:
   - Dynamic policy alignment and reasoning using the zone metadata (`description`, `alert_severity`, `prohibited_classes`).

---

## 2. JSON Schema Specification

```json
{
  "camera_id": "CAM_WH_01",
  "site_id": "SITE_WH_01",
  "site_name": "Main Distribution Warehouse - Bay 4",
  "site_type": "warehouse",
  "resolution": [1280, 720],
  "zones": {
    "emergency_exit": {
      "zone_id": "ZONE_EXIT_01",
      "zone_name": "Emergency Fire Exit Doorway",
      "zone_type": "exclusion",
      "alert_severity": "CRITICAL",
      "coordinates": [[480, 340], [920, 340], [920, 700], [480, 700]],
      "prohibited_classes": [5, 11, 12, 13, 14],
      "blockage_threshold_seconds": 3.0,
      "description": "Evacuation path must have zero obstruction. People moving allowed."
    }
  },
  "counting_lines": {
    "exit_door_counter": {
      "line_id": "LINE_EXIT_DOOR",
      "name": "Exit Doorway Pedestrian Flow",
      "coordinates": [[700, 360], [950, 600]],
      "count_classes": [0],
      "description": "Counts workers entering and exiting through the door"
    }
  }
}
```

### Zone Parameters
| Key | Type | Requirement | Description |
| :--- | :--- | :--- | :--- |
| `zone_id` | String | **Required** | Unique identifier (e.g. `ZONE_EXIT_01`). Must be unique across site. |
| `zone_name` | String | **Required** | Display name used in incident logs and executive reports. |
| `zone_type` | String | Optional | One of `exclusion`, `walkway`, `equipment_clearance`, `machinery_perimeter`, `restricted`. |
| `alert_severity` | String | **Required** | One of `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO`. |
| `coordinates` | Array of `[x, y]` | **Required** | Minimum 3 points. Positive numbers representing pixel locations on the frame. |
| `prohibited_classes`| Array of Int / Str | Optional | Taxonomy class IDs (`0..15`) or canonical names (`pallet`, `forklift`, `person`). |
| `blockage_threshold_seconds` | Float | Optional (Default 3.0s) | Minimum dwell time before generating a spatial violation event. |
| `description` | String | Optional | Human-readable explanation and compliance SOP guidance. |

---

## 3. Class Taxonomy Reference (16 Canonical Classes)
| Class ID | Canonical Name | Typical Restricted Zones |
| :---: | :--- | :--- |
| `0` | `person` | Machinery bays, high-voltage rooms, robot cells |
| `1` | `safety_helmet` | Construction hardhat zones |
| `2` | `safety_vest` | High-visibility zones, roadways |
| `3` | `fire_extinguisher`| Equipment safety perimeters |
| `4` | `fire_hose` | Fire hydrant safety corridors |
| `5` | `pallet` | Emergency exit doors, pedestrian walkways |
| `6` | `fire` | All zones |
| `7` | `spill` | Walkways, storage racks |
| `8` | `safety_signage` | Signage clear zones |
| `9` | `exit_sign` | Doorway overhead clearance |
| `10` | `empty_shelf` | Racking inspection zones |
| `11` | `forklift` | Pedestrian-only walkways, restricted docks |
| `12` | `vehicle` | Pedestrian lanes |
| `13` | `obstacle` | Evacuation routes |
| `14` | `machinery` | Dynamic exclusion zones |
| `15` | `safety_cone` | Traffic demarcation lines |

---

## 4. API Endpoints for Frontend (Member 6)

### `GET /vision/camera/{site_id}/reference-frame`
Returns a JPEG frame snapshot from the specified camera/video feed for the admin to draw polygons over.

### `GET /vision/zones/schema`
Returns the JSON Schema (Draft 2020-12) used to auto-generate frontend forms or validate payloads client-side.

### `POST /vision/zones/validate`
Validates a candidate JSON payload without persisting it. Returns `{ "valid": true, "errors": [] }`.

### `POST /vision/zones/{site_id}`
Validates, persists to `config/zones_{site_id}.json`, and hot-reloads the active `ZoneEngine` in memory. Returns HTTP 200 on success or HTTP 400 with a detailed error array if validation fails.
