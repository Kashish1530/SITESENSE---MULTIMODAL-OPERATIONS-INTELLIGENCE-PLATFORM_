# SiteSense Object Detection Annotation Guidelines

## 1. Overview

These guidelines define the annotation standards for the **SiteSense** computer vision dataset covering **construction sites** and **warehouses**. Consistent, tight, and unambiguous bounding box annotations are critical for training reliable safety, PPE compliance, hazard detection, and operational monitoring models.

- **Task:** 2D Object Detection (Axis-aligned bounding boxes)
- **Format:** YOLO (`.txt` label files with normalized coordinates)
- **Total Classes:** 16 (`ID 0` – `ID 15`)

---

## 2. Class Taxonomy

| ID | Class Name | Category | Short Description |
|---:|---|---|---|
| `0` | `person` | People & PPE | Any visible human (worker, operator, visitor, supervisor) |
| `1` | `safety_helmet` | People & PPE | Hard hat / protective safety helmet |
| `2` | `safety_vest` | People & PPE | High-visibility reflective safety vest / jacket |
| `3` | `fire_extinguisher` | Fire & Emergency | Portable or wall-mounted fire extinguisher |
| `4` | `fire_hose` | Fire & Emergency | Fire hose (coiled, reel-mounted, or deployed) |
| `5` | `pallet` | Warehouse & Storage | Wooden or plastic shipping pallet (empty or loaded) |
| `6` | `fire` | Hazards | Active visible flames |
| `7` | `spill` | Hazards | Liquid, oil, water, or chemical spill on floor/ground |
| `8` | `safety_signage` | Signage & Traffic | Safety, warning, danger, caution, or PPE requirement signs |
| `9` | `exit_sign` | Signage & Traffic | Emergency / Exit directional signage |
| `10` | `empty_shelf` | Warehouse & Storage | Empty / unoccupied warehouse storage rack bay or shelf slot |
| `11` | `forklift` | Vehicles & Equipment | Warehouse or site forklift |
| `12` | `vehicle` | Vehicles & Equipment | Road/transport vehicles (trucks, vans, pickups, mixer trucks) |
| `13` | `obstacle` | Hazards | Unplanned boxes, debris, or objects obstructing aisles/walkways |
| `14` | `machinery` | Vehicles & Equipment | Heavy construction/industrial machinery (excavators, cranes, loaders) |
| `15` | `safety_cone` | Signage & Traffic | High-visibility orange/reflective safety or traffic cone |

---

## 3. General Bounding Box Rules

1. **Tight Fit:** Draw boxes tightly around the visible edges of the object. Do not include excessive background margin or crop off key parts of the object.
2. **Visibility & Occlusion:**
   - Annotate an object if at least **20–25%** of it is visible and its class is clearly recognizable without guessing.
   - Draw the box **only around the visible portion** — do not extrapolate beyond occluders or outside image boundaries.
3. **Minimum Size:** Skip distant objects smaller than roughly **12 × 12 pixels** unless they are unambiguously identifiable (e.g., a clear helmet on a visible worker).
4. **Individual Labeling:** Label each distinct object instance separately, even when overlapping or stacked (e.g., multiple workers, stacked pallets, adjacent cones).
5. **No Reflections or Media:** Do **not** annotate objects appearing only in mirrors, glass reflections, posters, or monitor screens.
6. **Negative / Background Images:** Images with zero target objects are valid background samples and must retain a corresponding **empty `.txt` file** (0 bytes / 0 lines).

---

## 4. Class-by-Class Annotation Rules

### People & PPE

#### `0` — `person`
- **Include:** All visible people on site or in the warehouse (ground workers, forklift drivers, crane/machine operators, supervisors, pedestrians).
- **Box boundaries:** Cover the full visible body from head (including helmet if worn) to feet.
- **Co-annotation rule:** Always annotate `person` **independently** of `safety_helmet` and `safety_vest`. If a worker wears both a helmet and vest, create **three** boxes (`0`, `1`, `2`).
- **Exclude:** Mannequins, silhouettes/pictograms on safety signs, or blurred crowds where individuals cannot be separated.

#### `1` — `safety_helmet`
- **Include:** Industrial hard hats and safety helmets worn by a person or clearly placed on a surface/rack.
- **Box boundaries:** Tightly enclose the helmet shell and brim (do not include the person's face or neck).
- **Exclude:** Regular baseball caps, beanies, hoods, or bare heads. *(Missing-helmet violations are determined downstream by checking `person` boxes without an overlapping `safety_helmet`.)*

#### `2` — `safety_vest`
- **Include:** High-visibility safety vests (fluorescent yellow/lime, orange, or reflective-striped safety vests/harnesses worn over torso).
- **Box boundaries:** Enclose the visible torso area covered by the vest.
- **Exclude:** Ordinary shirts, jackets, or coveralls that do not have high-visibility coloring or reflective safety strips.

---

### Fire & Emergency Equipment

#### `3` — `fire_extinguisher`
- **Include:** Red/metallic portable, wheeled, or wall-mounted fire extinguishers (foam, CO2, dry powder, water).
- **Box boundaries:** Include the full cylinder body, handle/valve, pressure gauge, and attached hose/nozzle.
- **Exclude:** Fire extinguisher wall signs (label those as `8: safety_signage`), gas cylinders, or propane tanks.

#### `4` — `fire_hose`
- **Include:** Coiled fire hoses, hose reels, wall-cabinet hoses (when the hose itself is visible), and deployed/unrolled fire hoses.
- **Box boundaries:** Tightly enclose the visible hose coil/reel or deployed hose body (including nozzle/coupling).
- **Exclude:** Standard garden hoses, electrical cables, air compressor hoses, or closed fire-hose cabinets where the hose is hidden.

---

### Hazards

#### `6` — `fire`
- **Include:** Active, visible flames (open fires, equipment fires, structural or material fires).
- **Box boundaries:** Tightly enclose the active luminous flame region.
- **Exclude:** Pure smoke plumes without visible flames, welding sparks alone, orange lights/reflections, or flame icons on warning signs.

#### `7` — `spill`
- **Include:** Visible pools, puddles, or streaks of liquid, oil, coolant, water, or chemicals on floors, concrete, or walkways.
- **Box boundaries:** Tightly enclose the entire contiguous wet/stained spill footprint on the floor.
- **Co-annotation rule:** If a tipped drum/bucket/box caused the spill and blocks the walkway, label the spill as `7: spill` and the container itself as `13: obstacle`.
- **Exclude:** Shadows, dry tire marks without liquid, or normal surface texture variations.

#### `13` — `obstacle`
- **Include:** Unplanned or misplaced items obstructing warehouse aisles, walkways, exits, or active work paths — such as scattered cardboard boxes, fallen items, loose debris, stray tool cases, or improperly placed containers on the floor.
- **Box boundaries:** Enclose the single obstructing object, or a tightly grouped pile of scattered debris that forms one continuous floor hazard.
- **Exclude:**
  - Neatly stored pallets or cargo properly placed inside rack bays (use `5: pallet` where applicable).
  - Properly placed `15: safety_cone` markers.
  - Liquid spills (use `7: spill`).

---

### Warehouse & Storage

#### `5` — `pallet`
- **Include:** Wooden or plastic flat shipping pallets — whether empty, stacked, on the floor, on forklift forks, or stored on warehouse racks.
- **Box boundaries:** Enclose the pallet structure itself. When a pallet carries tightly bound goods and the pallet base is clearly visible, tightly box the pallet base (or keep consistent with the existing dataset convention if the pallet stack is boxed as a unit).
- **Exclude:** Loose cardboard boxes without a pallet underneath (if blocking an aisle, use `13: obstacle`).

#### `10` — `empty_shelf`
- **Include:** Unoccupied storage rack bays / empty warehouse shelf slots (wire decking, metal beam bays, or open shelf levels with no pallets/inventory stored in that slot).
- **Box boundaries:** Tightly frame the empty shelf bay / deck opening bounded by the rack beams/uprights.
- **Exclude:** Occupied shelves containing boxes or pallets, or non-storage structures like scaffolding.

---

### Signage & Traffic Control

#### `8` — `safety_signage`
- **Include:** Construction and warehouse safety signs — `DANGER`, `WARNING`, `CAUTION`, `NOTICE`, mandatory PPE signs, electrical hazard triangles, restricted-area signs, and emergency alarm/horn instruction signs.
- **Box boundaries:** Tightly enclose the sign board/placard border.
- **Exclude:**
  - `EXIT` signs (always use `9: exit_sign`).
  - General commercial billboards, company logos, or warehouse aisle number labels without safety content.

#### `9` — `exit_sign`
- **Include:** Dedicated `EXIT` / `EMERGENCY EXIT` signs (illuminated wall/ceiling signs, glow-in-the-dark plaques, or printed directional exit signs).
- **Box boundaries:** Tightly enclose the sign housing/panel.
- **Disambiguation:** Always label exit signs exclusively as `9: exit_sign` — do **not** double-label them as `8: safety_signage`.

#### `15` — `safety_cone`
- **Include:** High-visibility orange, red, or reflective traffic/safety cones used to mark work zones, hazards, or restricted paths.
- **Box boundaries:** Enclose the full cone from tip to square base.
- **Exclude:** Bollards, barrels/drums, or barricades.

---

### Vehicles & Heavy Equipment

> **Critical Disambiguation (`11` vs `12` vs `14`):** Assign every motorized machine/vehicle to **exactly one** of these three classes based on its primary role:

| Class | Use For | Do NOT Use For |
|---|---|---|
| `11: forklift` | Counterbalance forklifts, reach trucks, warehouse lift trucks, site forklifts | Road trucks (`12`), excavators/cranes (`14`) |
| `12: vehicle` | Road & transport vehicles: dump trucks, flatbeds, pickups, delivery vans, cargo trucks, concrete mixer trucks, passenger cars on site | Forklifts (`11`), non-road construction machinery (`14`) |
| `14: machinery` | Heavy construction & industrial equipment: excavators, tower cranes, mobile/crawler cranes, bulldozers, wheel loaders, backhoes, road rollers, concrete boom pumps, scissor/boom lifts | Forklifts (`11`), standard transport/dump trucks (`12`) |

#### `11` — `forklift`
- **Include:** The full forklift body, overhead guard/cab, mast, and forks.
- **Co-annotation rule:** If a driver is visible inside the cab, also annotate the driver as `0: person` (and their PPE `1`/`2` if visible).

#### `12` — `vehicle`
- **Include:** Full visible body of transport vehicles on construction sites or warehouse loading docks (cab, chassis, cargo bed/trailer, wheels).
- **Exclude:** Stationary shipping containers without a truck/chassis.

#### `14` — `machinery`
- **Include:** Full visible extent of heavy equipment including booms, arms, buckets, or crane jibs when part of the machine.
- **Note on auditing:** Ensure dump trucks are consistently labeled `12: vehicle` and excavators/cranes are consistently labeled `14: machinery` during dataset QA.

---

## 5. YOLO Label Format & File Conventions

Each image must have a matching `.txt` label file with the **exact same filename stem**:

```text
images/site_0001.jpg  <-->  labels/site_0001.txt
```

Each line in the `.txt` file represents one bounding box:

```text
<class_id> <x_center> <y_center> <width> <height>
```

- `class_id`: Integer from `0` to `15`.
- `x_center`, `y_center`: Normalized box center coordinates in `[0.0, 1.0]`.
- `width`, `height`: Normalized box dimensions in `(0.0, 1.0]`.

Example:
```text
0 0.452100 0.518400 0.142000 0.481000
1 0.449500 0.295000 0.054000 0.048000
2 0.453000 0.460000 0.118000 0.195000
```

---

## 6. Quality Assurance (QA) Checklist

Before approving a batch for training, verify:

- [ ] Every `class_id` is an integer in `0`–`15` matching `config/classes.yaml`.
- [ ] All coordinates are strictly within `[0.0, 1.0]` with `width > 0` and `height > 0`.
- [ ] Every image in `images/` has a matching `.txt` in `labels/`, and there are no orphan `.txt` files without images.
- [ ] Co-annotations are complete (`person` + `safety_helmet` + `safety_vest` labeled separately).
- [ ] Mutually exclusive classes are not double-labeled (`exit_sign` vs `safety_signage`; `forklift` vs `vehicle` vs `machinery`).
- [ ] No duplicate overlapping boxes of the same class on the same object.
