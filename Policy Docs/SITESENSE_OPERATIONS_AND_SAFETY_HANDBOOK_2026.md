# SITESENSE OPERATIONS & COMPLIANCE POLICY HANDBOOK
**Document ID:** POL-OPS-2026-V1  
**Version:** 2026.Q1  
**Effective Date:** 2026-01-01  
**Scope:** Applicable across all physical operating facilities (Warehouses, Distribution Hubs, Retail Outlets, Logistics Depots, and Site Service Centers).

---

## SECTION 1: SITE ACCESS, IDENTIFICATION & ENTRY PROTOCOLS

### Clause 1.1 — Authorized Visitor & Personnel Entry
All employees, field supervisors, contractors, and visitors must register at the site reception or security checkpoint prior to accessing operational floors. Access credentials (RFID badge or visitor pass) must be displayed visibly on the upper torso at all times.
- **Compliance Standard:** Active ID badge visible.
- **Violation Severity:** Moderate.

### Clause 1.2 — Delivery Gate Logistics Check
All transport vehicles entering the loading dock or depot yard must be logged with vehicle registration number, driver identity, time of arrival, and accompanying consignment documents.
- **Compliance Standard:** Verified vehicle plate and consignment log matching.
- **Violation Severity:** High.

---

## SECTION 2: PERSONAL PROTECTIVE EQUIPMENT (PPE) REQUIREMENTS

### Clause 2.1 — Head Protection (Safety Helmet Mandate)
Every individual entering or working inside an active operational zone, warehouse floor, construction bay, or loading dock must wear an approved, undamaged safety helmet (hard hat conforming to EN 397 / ANSI Z89.1). Helmets must be securely fastened with chin straps where working at heights or near mobile machinery.
- **Governing Rule Type:** `required_object_present`
- **Target Subject:** Person
- **Required Object:** `safety_helmet`
- **Applicable Zones:** `operational_floor`, `loading_bay`, `staging_area`
- **Violation Severity:** Critical. Immediate cessation of work until rectified.

### Clause 2.2 — High-Visibility Clothing
All personnel operating in areas with vehicular or forklift traffic must wear high-visibility vests or jackets meeting EN ISO 20471 Class 2 standards (fluorescent orange or yellow-green with retro-reflective tape).
- **Governing Rule Type:** `required_object_present`
- **Target Subject:** Person
- **Required Object:** `high_vis_vest`
- **Applicable Zones:** `transit_corridor`, `loading_dock`, `yard`
- **Violation Severity:** High.

### Clause 2.3 — Safety Footwear
Steel-toe or composite-toe protective footwear with slip-resistant soles conforming to ASTM F2413 / EN ISO 20345 is mandatory in all storage, fulfillment, and transit zones. Open-toed shoes or soft sneakers are strictly prohibited.
- **Violation Severity:** High.

---

## SECTION 3: FIRE SAFETY, EMERGENCY EQUIPMENT & SIGNAGE

### Clause 3.1 — Fire Extinguisher Accessibility & Inspection Tagging
Portable fire extinguishers must be mounted at designated locations marked by high-visibility red signage. 
1. **Clearance:** A minimum radial clearance of **1.0 meter (3.3 feet)** around each extinguisher must be maintained at all times. No pallets, merchandise, or clutter may obstruct access.
2. **Inspection Tags:** Every extinguisher must bear a valid inspection tag recording monthly inspections and annual servicing. Any extinguisher with an inspection date older than 365 days or with an unreadable tag is considered non-compliant.
- **Governing Rule Type:** `zone_clear` and `ocr_verification`
- **Required Clearance:** 1.0 meter
- **Violation Severity:** Critical.

### Clause 3.2 — Emergency Exit Signage & Illuminated Path Indicators
All emergency exit doors and exit corridors must feature illuminated green/white running-man exit signs conforming to ISO 7010. Signage must remain unobstructed and illuminated 24/7.
- **Governing Rule Type:** `required_object_present`
- **Violation Severity:** Critical.

---

## SECTION 4: WALKWAYS, TRANSIT CORRIDORS & EMERGENCY EXITS

### Clause 4.1 — Primary Walkway Minimum Clearance
All primary transit corridors and pedestrian walkways painted with yellow or high-contrast boundary markings must maintain a continuous minimum unobstructed width of **1.2 meters (4.0 feet)**.
- **Governing Rule Type:** `zone_clear`
- **Forbidden Objects:** `pallet`, `box`, `trolley`, `debris`, `loose_cable`
- **Violation Severity:** High. Requires immediate removal of obstructing items.

### Clause 4.2 — Emergency Fire Exit Zero-Tolerance Clearance
Designated emergency exit doors, push-bars, and immediate escape routes leading directly outdoors must remain **100% unobstructed at all times**. Storing, staging, or momentarily parking any pallet, cardboard carton, waste container, or vehicle within 2.0 meters of an exit door constitutes an immediate regulatory breach.
- **Governing Rule Type:** `forbidden_object_absent`
- **Forbidden Objects:** Any object except human pedestrians
- **Applicable Zones:** `emergency_exit_zone`, `fire_escape_door`
- **Violation Severity:** Critical. Triggers automatic high-priority remediation ticket.

---

## SECTION 5: PALLET STACKING, STORAGE & RACKING INTEGRITY

### Clause 5.1 — Pallet Stacking Height Limits
Freestanding pallet stacks on warehouse or depot floors must not exceed a maximum height of **2.4 meters (8.0 feet)** or three stacked unit loads, whichever is lower. All stacked items must be uniformly shrink-wrapped with no leaning exceeding 5 degrees from the vertical.
- **Governing Rule Type:** `count_threshold` and `height_limit`
- **Max Height:** 2.4 meters
- **Violation Severity:** High.

### Clause 5.2 — Racking Upright Protection & Overhang
Merchandise stored in heavy-duty pallet racking must not overhang into transit aisles by more than **50 mm (2 inches)**. Pallet beam loads must not exceed the certified safe working load (SWL) indicated on load plaques.
- **Violation Severity:** High.

---

## SECTION 6: SPILL CONTROL, LIQUID HAZARDS & HOUSEKEEPING

### Clause 6.1 — Immediate Spill Containment
Any liquid spill (chemical, oil, water, or product breakage) exceeding 0.5 liters must be cordoned off immediately with caution cones or barricade tape within **15 minutes** of occurrence. Neutralization and clean-up using the facility spill kit must be initiated promptly.
- **Governing Rule Type:** `dwell_time_exceeded` / `hazard_present`
- **Target Object:** `spill`
- **Violation Severity:** Critical (slip and fall hazard).

### Clause 6.2 — Waste & Packaging Accumulation
Empty wooden pallets, shrink-wrap rolls, and torn corrugated cardboard boxes must be discarded into designated recycling skips at the end of each work shift. Staging loose rubbish in operational walkways is prohibited.
- **Violation Severity:** Moderate.

---

## SECTION 7: DELIVERY DOCUMENTATION, PERMITS & INGESTION COMPLIANCE

### Clause 7.1 — Consignment Delivery Note Matching
Every inbound and outbound shipment must be accompanied by an official physical or digital Delivery Note (or Consignment Note).
1. **Mandatory Fields:** Delivery Notes must contain:
   - Vendor / Supplier Name
   - Consignment / Delivery Note Number
   - Date of Dispatch and Delivery
   - Itemized Description of Goods and Quantities
   - Purchase Order (PO) Reference
   - Authorized Receiver Signature
2. **Discrepancy Threshold:** If physical detected pallet/carton count differs from delivery note quantities by more than **0% on serial-tracked goods** or **2% on bulk goods**, a documentation discrepancy finding must be logged.
- **Governing Rule Type:** `structured_extraction_match`
- **Confidence Threshold:** Any extraction confidence below 0.85 must be routed to the Human Review Queue.
- **Violation Severity:** High.

### Clause 7.2 — Hot Work & Height Permits
Any maintenance involving welding, cutting, or elevated platform work above 2.0 meters requires an active signed Permit to Work (PTW). The permit must be posted visibly at the job location.
- **Violation Severity:** Critical.

---

## SECTION 8: AUTOMATED COMPLIANCE TICKETING & HUMAN APPROVAL GATE

### Clause 8.1 — Remediation Ticket Generation
When the SiteSense automated inspection engine detects a rule failure rated High or Critical, the agent proposes a remediation ticket. 
- **Approval Gate:** The ticket remains in `proposed` status until reviewed and explicitly approved by an authorized Site Manager or Compliance Administrator in the UI. 
- **Action SLA:** Approved critical tickets must be rectified within 4 hours; high-priority tickets within 24 hours.

