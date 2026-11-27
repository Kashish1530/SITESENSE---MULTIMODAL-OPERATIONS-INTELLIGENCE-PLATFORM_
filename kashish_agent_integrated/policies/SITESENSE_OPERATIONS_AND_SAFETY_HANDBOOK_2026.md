# SITESENSE OPERATIONS & COMPLIANCE POLICY HANDBOOK
**Document ID:** POL-OPS-2026-V2  
**Version:** 2026.Q1 (Full 16-Class Operational Specification)  
**Effective Date:** 2026-01-01  
**Scope:** Applicable across all physical operating facilities (Warehouses, Distribution Hubs, Retail Stores, Logistics Depots, Construction Sites, and Service Centers).

---

## SECTION 1: SITE LOGISTICS, TRAFFIC & MOBILE EQUIPMENT

### Clause 1.1 — Vehicle & Truck Logistics Protocol
All transport vehicles and trucks entering loading docks, parking aprons, or depot gates must be logged upon arrival. Heavy trucks must adhere to a maximum yard speed limit of 15 km/h, deploy wheel chocks when docked, and maintain at least 3.0 meters clearance from unassigned personnel.
- **Governing Class:** `vehicle/truck`
- **Applicable Zones:** `loading_dock`, `yard`, `gate_entry`
- **Violation Severity:** High.

### Clause 1.2 — Forklift Operation & Pedestrian Separation
Forklifts must operate strictly within demarcated vehicular lanes. A mandatory **minimum clearance of 2.5 meters** must be maintained between moving forklifts and any pedestrian worker. Forklift operators must sound horns at blind intersections and must never transport passengers unless equipped with an approved auxiliary cabin.
- **Governing Classes:** `forklift`, `person`
- **Applicable Zones:** `operational_floor`, `transit_corridor`, `loading_bay`
- **Rule Type:** `proximity_threshold`
- **Violation Severity:** Critical.

---

## SECTION 2: PERSONAL PROTECTIVE EQUIPMENT (PPE) REQUIREMENTS

### Clause 2.1 — Safety Helmet Mandate (Head Protection)
Every individual (employee, contractor, visitor, or supervisor) entering or present inside an active operational zone, warehouse floor, construction bay, or loading dock must wear an approved, undamaged safety helmet (hard hat conforming to EN 397 / ANSI Z89.1). Helmets must be securely fastened.
- **Governing Classes:** `person`, `safety-helmet`
- **Rule Type:** `required_object_present`
- **Applicable Zones:** `operational_floor`, `loading_bay`, `staging_area`
- **Violation Severity:** Critical (immediate work cessation).

### Clause 2.2 — Safety Vest Requirement (High-Visibility Clothing)
All personnel operating in areas with vehicular, truck, or forklift movement must wear a high-visibility safety vest conforming to EN ISO 20471 Class 2 standards (fluorescent orange or neon yellow with retro-reflective bands).
- **Governing Classes:** `person`, `safety-vest`
- **Rule Type:** `required_object_present`
- **Applicable Zones:** `transit_corridor`, `loading_dock`, `yard`, `warehouse_floor`
- **Violation Severity:** High.

---

## SECTION 3: FIRE SAFETY, SUPPRESSION SYSTEMS & HAZARDS

### Clause 3.1 — Fire Extinguisher Clearance & Readiness
Portable fire extinguishers must be mounted at designated fire points with direct, unhindered visibility. A minimum radial clearance of **1.0 meter (3.3 feet)** around each fire extinguisher must be kept 100% free of obstacles, pallets, boxes, and merchandise. All extinguishers must carry an updated inspection tag dated within the past 365 days.
- **Governing Classes:** `safety- fire extinguisher`, `obstacle`, `pallets`
- **Rule Type:** `zone_clear`
- **Required Clearance:** 1.0 meter
- **Violation Severity:** Critical.

### Clause 3.2 — Fire Hose Reel Station Accessibility
Fire hose reel cabinets and hydrant points must remain unobstructed by pallets, goods, or equipment at all times. A clear perimeter of **1.5 meters** in front of every fire hose reel station must be preserved.
- **Governing Class:** `fire-hose`, `obstacle`
- **Rule Type:** `zone_clear`
- **Violation Severity:** Critical.

### Clause 3.3 — Active Fire Hazard Detection & Emergency Protocol
Any detection of active flame, uncontrolled combustion, or dense smoke represents an immediate Level 1 Life-Safety Emergency. Detection of fire triggers automatic audible alarms, emergency gate unlocking, and immediate evacuation to designated assembly points.
- **Governing Class:** `fire`
- **Rule Type:** `forbidden_object_absent`
- **Violation Severity:** Immediate Emergency (Critical).

---

## SECTION 4: TRANSIT CORRIDORS, EMERGENCY EXITS & OBSTACLES

### Clause 4.1 — Primary Walkway Minimum Clearance
All primary pedestrian walkways and transit aisles marked by yellow boundary lines must maintain a continuous minimum unobstructed clearance width of **1.2 meters (4.0 feet)**. Staging pallets, boxes, or miscellaneous obstacles within these walkways is strictly prohibited.
- **Governing Classes:** `pallets`, `obstacle`, `person`
- **Rule Type:** `zone_clear`
- **Minimum Width:** 1.2 meters
- **Violation Severity:** High.

### Clause 4.2 — Emergency Fire Exit Zero-Tolerance Obstruction
Designated emergency exit doors and escape routes leading directly outdoors must remain **100% unobstructed at all times**. Storing, stacking, or temporarily parking pallets, carts, waste, or any physical obstacle within 2.0 meters of an emergency exit door constitutes a zero-tolerance regulatory breach.
- **Governing Classes:** `exit-sign`, `obstacle`, `pallets`
- **Rule Type:** `forbidden_object_absent`
- **Violation Severity:** Critical (automatic urgent remediation ticket).

---

## SECTION 5: HOUSEKEEPING, SPILLS & SAFETY DEMARCATION

### Clause 5.1 — Immediate Spill Containment & Cleanup
Any liquid spill (water, chemical, detergent, oil, or product breakage) exceeding 0.5 liters must be addressed immediately. Within **15 minutes** of occurrence, the hazard area must be cordoned off with high-visibility safety cones and cleaned using spill response kits.
- **Governing Classes:** `spill`, `safety-cone`
- **Rule Type:** `hazard_present` / `dwell_time_exceeded`
- **Max Response Time:** 15 minutes
- **Violation Severity:** Critical (slip and fall hazard).

### Clause 5.2 — Mandatory Safety Cone Deployment for Floor Hazards
Whenever a floor hazard (wet floor, temporary repair, uneven surface, or pending spill cleanup) exists, at least **two safety cones** must be deployed around the perimeter to alert workers and pedestrians.
- **Governing Classes:** `safety-cone`, `spill`, `obstacle`
- **Rule Type:** `required_object_present`
- **Violation Severity:** High.

---

## SECTION 6: FACILITY SIGNAGE & DIRECTIONAL INDICATORS

### Clause 6.1 — Exit Sign Visibility & Illumination
Illuminated green/white exit signs conforming to ISO 7010 must be mounted over every emergency exit door and directional escape junction. Signage must remain unobstructed by high pallet stacks or hanging banners and must be fully illuminated 24/7.
- **Governing Class:** `exit-sign`
- **Rule Type:** `required_object_present`
- **Violation Severity:** Critical.

### Clause 6.2 — Safety & Warning Signage Display
Mandatory safety warning signage (e.g., Forklift Traffic Warning, Eye Protection Required, No Smoking, High Voltage) must be clearly displayed at zone boundaries. Signage must remain undamaged, clean, and legible from a distance of at least 5 meters.
- **Governing Class:** `safety-signage`
- **Rule Type:** `required_object_present`
- **Violation Severity:** Moderate.

---

## SECTION 7: INVENTORY, SHELF COMPLIANCE & PALLET STORAGE

### Clause 7.1 — Retail & Warehouse Shelf Stocking (Empty Shelf Protocol)
In retail customer zones and high-velocity warehouse pick bays, empty shelf space must not exceed **15% of the total shelf module area** during operational hours. Facing gaps must be replenished or consolidated within 2 hours of detection.
- **Governing Class:** `empty-shelf`
- **Rule Type:** `threshold_limit`
- **Max Empty Shelf Area:** 15%
- **Violation Severity:** Moderate.

### Clause 7.2 — Pallet Stacking Height & Unit Integrity
Freestanding pallet stacks on warehouse or depot floors must not exceed a maximum height of **2.4 meters (8.0 feet)** or three stacked unit loads. Pallets must be uniformly shrink-wrapped with no leaning exceeding 5 degrees from the vertical.
- **Governing Class:** `pallets`
- **Rule Type:** `count_threshold` / `height_limit`
- **Max Height:** 2.4 meters
- **Violation Severity:** High.

---

## SECTION 8: INDUSTRIAL MACHINERY & HAZARDOUS OPERATIONS

### Clause 8.1 — Machinery Safety Perimeter & Guarding
All heavy fixed machinery (conveyors, balers, sorters, packaging machines) must be equipped with physical guards and emergency stop buttons. Personnel must maintain a clear safety buffer and must not bypass safety light curtains or barriers without a Lockout/Tagout (LOTO) permit.
- **Governing Classes:** `machinery`, `person`
- **Rule Type:** `zone_boundary_check`
- **Violation Severity:** Critical.

---

## SECTION 9: DOCUMENTATION & DELIVERY COMPLIANCE

### Clause 9.1 — Consignment Delivery Note Matching
Every inbound delivery must be verified against its official delivery note (vendor name, PO number, line items, and receiver signature). Physical pallet count discrepancies exceeding 2% require an investigation finding. Extractions below 0.85 confidence must route to human review.
- **Violation Severity:** High.

---

## SECTION 10: AUTOMATED TICKETING & APPROVAL GATE

### Clause 10.1 — Remediation Ticket Approval Gate
When automated inspection identifies a Critical or High rule failure, the agent proposes a remediation ticket. The ticket remains in `proposed` status and requires explicit approval by a Site Manager in the UI prior to ticket creation.
- **Violation Severity:** High.
