"""
scripts/generate_demo_videos.py
SiteSense Multi-modal Operations Intelligence Platform
Master 5-Minute Video Generator for Demo & Testing
Generates:
  1. Construction Site Safety & Zone Intelligence (5 minutes / 300s)
  2. Warehouse Operations & Emergency Exit Blockage (5 minutes / 300s)
Covers all 16 canonical SiteSense classes, zone tracking, dwell-time alerts,
and emits ground truth bounding boxes.
"""

import os
import sys
import json
import math
import time
import cv2
import numpy as np

# 16 Canonical Classes
CLASS_NAMES = {
    0: "person",
    1: "safety_helmet",
    2: "safety_vest",
    3: "fire_extinguisher",
    4: "fire_hose",
    5: "pallet",
    6: "fire",
    7: "spill",
    8: "safety_signage",
    9: "exit_sign",
    10: "empty_shelf",
    11: "forklift",
    12: "vehicle",
    13: "obstacle",
    14: "machinery",
    15: "safety_cone"
}

# Color palette for classes (BGR)
CLASS_COLORS = {
    0: (255, 128, 0),    # person - orange
    1: (0, 215, 255),    # safety_helmet - yellow
    2: (50, 205, 50),    # safety_vest - lime green
    3: (60, 20, 220),    # fire_extinguisher - red
    4: (34, 34, 178),    # fire_hose - dark red
    5: (45, 82, 160),    # pallet - brown
    6: (0, 69, 255),     # fire - bright red/orange
    7: (255, 191, 0),    # spill - cyan
    8: (0, 215, 255),    # safety_signage - gold/yellow
    9: (50, 205, 50),    # exit_sign - green
    10: (180, 180, 180), # empty_shelf - grey
    11: (0, 215, 255),   # forklift - yellow
    12: (200, 100, 50),  # vehicle - steel blue
    13: (30, 30, 200),   # obstacle - crimson
    14: (0, 165, 255),   # machinery - orange
    15: (0, 140, 255)    # safety_cone - bright orange
}

# ==========================================
# DRAWING HELPERS FOR ALL 16 CLASSES
# ==========================================

def draw_person(img, x, y, w, h, has_helmet=True, has_vest=True, walk_phase=0.0, boxes_list=None):
    """Draws a person (Class 0), helmet (Class 1), vest (Class 2) and records bboxes."""
    x1, y1, x2, y2 = int(x), int(y), int(x + w), int(y + h)
    
    # Proportions
    head_h = int(h * 0.18)
    head_w = int(w * 0.45)
    head_cx = int(x + w / 2)
    head_cy = int(y + head_h / 2)
    
    torso_top = y + head_h
    torso_h = int(h * 0.42)
    torso_bottom = torso_top + torso_h
    
    leg_h = h - (head_h + torso_h)
    
    # 1. Limbs / Legs (animated walk)
    leg_swing = math.sin(walk_phase) * (w * 0.28)
    # Left leg
    pt_hip_l = (int(head_cx - w * 0.15), int(torso_bottom))
    pt_foot_l = (int(head_cx - w * 0.15 - leg_swing), int(y2))
    cv2.line(img, pt_hip_l, pt_foot_l, (70, 50, 40), max(2, int(w * 0.15)))
    # Right leg
    pt_hip_r = (int(head_cx + w * 0.15), int(torso_bottom))
    pt_foot_r = (int(head_cx + w * 0.15 + leg_swing), int(y2))
    cv2.line(img, pt_hip_r, pt_foot_r, (60, 45, 35), max(2, int(w * 0.15)))
    
    # 2. Torso (Base clothing)
    torso_w = int(w * 0.65)
    torso_x1 = int(head_cx - torso_w / 2)
    torso_x2 = int(head_cx + torso_w / 2)
    cv2.rectangle(img, (torso_x1, int(torso_top)), (torso_x2, int(torso_bottom)), (90, 70, 60), -1)
    
    # 3. Arms (animated swing)
    arm_swing = math.sin(walk_phase + math.pi) * (w * 0.25)
    cv2.line(img, (torso_x1, int(torso_top + 5)), (int(torso_x1 - 5 + arm_swing), int(torso_top + torso_h * 0.8)), (80, 60, 50), max(2, int(w * 0.1)))
    cv2.line(img, (torso_x2, int(torso_top + 5)), (int(torso_x2 + 5 - arm_swing), int(torso_top + torso_h * 0.8)), (80, 60, 50), max(2, int(w * 0.1)))
    
    # 4. Vest (Class 2) - High-vis fluorescent yellow-green with reflective stripes
    if has_vest:
        vest_y1 = int(torso_top)
        vest_y2 = int(torso_bottom - 2)
        cv2.rectangle(img, (torso_x1 - 1, vest_y1), (torso_x2 + 1, vest_y2), (40, 230, 80), -1)
        # Silver reflective stripes
        cv2.line(img, (torso_x1, int(vest_y1 + torso_h * 0.35)), (torso_x2, int(vest_y1 + torso_h * 0.35)), (230, 240, 240), 3)
        cv2.line(img, (torso_x1, int(vest_y1 + torso_h * 0.70)), (torso_x2, int(vest_y1 + torso_h * 0.70)), (230, 240, 240), 3)
        # Vertical harness stripes
        cv2.line(img, (int(head_cx - torso_w * 0.25), vest_y1), (int(head_cx - torso_w * 0.25), vest_y2), (230, 240, 240), 2)
        cv2.line(img, (int(head_cx + torso_w * 0.25), vest_y1), (int(head_cx + torso_w * 0.25), vest_y2), (230, 240, 240), 2)
        if boxes_list is not None:
            boxes_list.append([2, torso_x1 - 1, vest_y1, torso_x2 + 1, vest_y2, 0.95])
            
    # 5. Head
    cv2.circle(img, (head_cx, head_cy), int(head_w / 2), (180, 200, 220), -1)
    
    # 6. Safety Helmet (Class 1) - Yellow hard hat
    if has_helmet:
        helm_y1 = int(y)
        helm_y2 = int(y + head_h * 0.8)
        helm_x1 = int(head_cx - head_w * 0.65)
        helm_x2 = int(head_cx + head_w * 0.65)
        # Hard hat dome
        cv2.ellipse(img, (head_cx, int(head_cy - head_h * 0.15)), (int(head_w * 0.65), int(head_h * 0.55)), 0, 180, 360, (0, 215, 255), -1)
        # Hard hat brim
        cv2.line(img, (helm_x1 - 2, int(head_cy)), (helm_x2 + 2, int(head_cy)), (0, 180, 220), 3)
        if boxes_list is not None:
            boxes_list.append([1, helm_x1, helm_y1, helm_x2, helm_y2, 0.94])
            
    # Record person bbox (Class 0)
    if boxes_list is not None:
        boxes_list.append([0, x1, y1, x2, y2, 0.96])

def draw_pallet(img, x, y, w, h, loaded=True, boxes_list=None):
    """Draws a wooden pallet (Class 5) with optional loaded cargo."""
    x1, y1, x2, y2 = int(x), int(y), int(x + w), int(y + h)
    
    # Pallet base (bottom 25% of height)
    pallet_base_h = max(10, int(h * 0.3 if loaded else h))
    base_y1 = y2 - pallet_base_h
    base_y2 = y2
    
    # Wood color
    wood_col = (50, 95, 155)
    wood_dark = (35, 70, 115)
    
    # Draw cargo on top if loaded
    if loaded:
        cargo_y1 = y1
        cargo_y2 = base_y1
        cv2.rectangle(img, (x1 + 4, cargo_y1), (x2 - 4, cargo_y2), (140, 175, 210), -1)
        cv2.rectangle(img, (x1 + 4, cargo_y1), (x2 - 4, cargo_y2), (80, 110, 140), 2)
        # Strapping tape
        cv2.line(img, (int(x + w * 0.35), cargo_y1), (int(x + w * 0.35), cargo_y2), (30, 30, 30), 2)
        cv2.line(img, (int(x + w * 0.70), cargo_y1), (int(x + w * 0.70), cargo_y2), (30, 30, 30), 2)
        cv2.putText(img, "CARGO", (int(x + 10), int(cargo_y1 + (cargo_y2 - cargo_y1) / 2 + 5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (40, 60, 80), 1)

    # Base deck boards
    cv2.rectangle(img, (x1, base_y1), (x2, base_y2), wood_col, -1)
    cv2.rectangle(img, (x1, base_y1), (x2, base_y2), wood_dark, 2)
    
    # Forklift entry holes
    hole_w = int(w * 0.28)
    hole_h = int(pallet_base_h * 0.55)
    hole_y = int(base_y1 + (pallet_base_h - hole_h) / 2)
    # Left entry pocket
    cv2.rectangle(img, (int(x + w * 0.15), hole_y), (int(x + w * 0.15 + hole_w), hole_y + hole_h), (20, 20, 20), -1)
    # Right entry pocket
    cv2.rectangle(img, (int(x + w * 0.57), hole_y), (int(x + w * 0.57 + hole_w), hole_y + hole_h), (20, 20, 20), -1)
    
    if boxes_list is not None:
        boxes_list.append([5, x1, y1, x2, y2, 0.93])

def draw_obstacle(img, x, y, w, h, label="DEBRIS", boxes_list=None):
    """Draws obstacle / debris / misplaced boxes (Class 13)."""
    x1, y1, x2, y2 = int(x), int(y), int(x + w), int(y + h)
    cv2.rectangle(img, (x1, y1), (x2, y2), (70, 90, 130), -1)
    cv2.rectangle(img, (x1, y1), (x2, y2), (40, 50, 80), 2)
    
    # Hazard diagonal stripes on obstacle
    for offset in range(-int(w), int(w + h), 16):
        pt1 = (max(x1, x1 + offset), y1)
        pt2 = (min(x2, x1 + offset + int(h)), y2)
        if pt1[0] < x2 and pt2[0] > x1:
            cv2.line(img, pt1, pt2, (0, 215, 255), 2)
            
    cv2.putText(img, label, (x1 + 6, int(y1 + h / 2 + 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
    if boxes_list is not None:
        boxes_list.append([13, x1, y1, x2, y2, 0.91])

def draw_spill(img, cx, cy, rx, ry, color=(60, 160, 230), boxes_list=None):
    """Draws liquid / oil puddle spill on floor (Class 7)."""
    cx, cy, rx, ry = int(cx), int(cy), int(rx), int(ry)
    x1 = cx - rx
    y1 = cy - ry
    x2 = cx + rx
    y2 = cy + ry
    
    # Glossy puddle
    overlay = img.copy()
    cv2.ellipse(overlay, (cx, cy), (rx, ry), 0, 0, 360, color, -1)
    # Specular shine
    cv2.ellipse(overlay, (int(cx - rx * 0.3), int(cy - ry * 0.2)), (int(rx * 0.4), int(ry * 0.25)), -20, 0, 360, (255, 255, 255), -1)
    cv2.addWeighted(overlay, 0.75, img, 0.25, 0, img)
    cv2.ellipse(img, (cx, cy), (rx, ry), 0, 0, 360, (int(color[0]*0.7), int(color[1]*0.7), int(color[2]*0.7)), 2)
    
    if boxes_list is not None:
        boxes_list.append([7, x1, y1, x2, y2, 0.90])

def draw_fire(img, cx, cy, w, h, t=0, boxes_list=None):
    """Draws active flame / fire (Class 6) with flickers."""
    cx, cy, w, h = int(cx), int(cy), int(w), int(h)
    x1 = cx - w // 2
    y1 = cy - h
    x2 = cx + w // 2
    y2 = cy
    
    # Flame outer layer (Red)
    flicker = int(math.sin(t * 15.0) * 8)
    flame_pts_outer = np.array([
        [cx - w // 2, cy],
        [cx - w // 3, cy - int(h * 0.6) + flicker],
        [cx, cy - h - flicker],
        [cx + w // 3, cy - int(h * 0.7) - flicker],
        [cx + w // 2, cy]
    ], np.int32)
    cv2.fillPoly(img, [flame_pts_outer], (0, 69, 255))
    
    # Flame mid layer (Orange)
    flame_pts_mid = np.array([
        [cx - w // 3, cy],
        [cx - w // 5, cy - int(h * 0.5) - flicker],
        [cx, cy - int(h * 0.8) + flicker],
        [cx + w // 5, cy - int(h * 0.5) + flicker],
        [cx + w // 3, cy]
    ], np.int32)
    cv2.fillPoly(img, [flame_pts_mid], (0, 165, 255))
    
    # Flame core (Yellow-white)
    cv2.ellipse(img, (cx, int(cy - h * 0.25)), (int(w * 0.2), int(h * 0.25)), 0, 0, 360, (180, 255, 255), -1)
    
    if boxes_list is not None:
        boxes_list.append([6, x1, y1 - 10, x2, y2, 0.94])

def draw_safety_cone(img, x, y, w, h, boxes_list=None):
    """Draws orange traffic / safety cone (Class 15)."""
    x1, y1, x2, y2 = int(x), int(y), int(x + w), int(y + h)
    cx = (x1 + x2) // 2
    
    # Base
    base_h = max(4, int(h * 0.15))
    cv2.rectangle(img, (x1, y2 - base_h), (x2, y2), (20, 20, 20), -1)
    
    # Cone body
    cone_pts = np.array([
        [cx, y1],
        [x1 + 3, y2 - base_h],
        [x2 - 3, y2 - base_h]
    ], np.int32)
    cv2.fillPoly(img, [cone_pts], (0, 140, 255))
    
    # White reflective band
    band_y1 = int(y1 + h * 0.45)
    band_y2 = int(y1 + h * 0.65)
    pts_band = np.array([
        [int(cx - w * 0.22), band_y1],
        [int(cx + w * 0.22), band_y1],
        [int(cx + w * 0.35), band_y2],
        [int(cx - w * 0.35), band_y2]
    ], np.int32)
    cv2.fillPoly(img, [pts_band], (240, 240, 240))
    
    if boxes_list is not None:
        boxes_list.append([15, x1, y1, x2, y2, 0.92])

def draw_fire_extinguisher(img, x, y, w, h, boxes_list=None):
    """Draws red fire extinguisher (Class 3)."""
    x1, y1, x2, y2 = int(x), int(y), int(x + w), int(y + h)
    cx = (x1 + x2) // 2
    
    # Cylinder
    cyl_y1 = int(y1 + h * 0.25)
    cv2.rectangle(img, (x1, cyl_y1), (x2, y2), (20, 20, 210), -1)
    cv2.rectangle(img, (x1, cyl_y1), (x2, y2), (10, 10, 140), 2)
    # White label
    cv2.rectangle(img, (x1 + 2, int(cyl_y1 + h * 0.2)), (x2 - 2, int(cyl_y1 + h * 0.5)), (240, 240, 240), -1)
    cv2.putText(img, "FIRE", (x1 + 3, int(cyl_y1 + h * 0.38)), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (20, 20, 200), 1)
    # Valve & handle
    cv2.rectangle(img, (int(cx - w * 0.25), y1 + 5), (int(cx + w * 0.25), cyl_y1), (50, 50, 50), -1)
    cv2.line(img, (cx, y1 + 5), (cx + int(w * 0.4), y1), (40, 40, 40), 3)
    # Hose
    cv2.line(img, (int(cx + w * 0.25), cyl_y1), (x2 + 3, int(cyl_y1 + h * 0.4)), (20, 20, 20), 2)
    
    if boxes_list is not None:
        boxes_list.append([3, x1, y1, x2 + 4, y2, 0.95])

def draw_fire_hose(img, x, y, w, h, boxes_list=None):
    """Draws fire hose reel and cabinet (Class 4)."""
    x1, y1, x2, y2 = int(x), int(y), int(x + w), int(y + h)
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    
    # Cabinet
    cv2.rectangle(img, (x1, y1), (x2, y2), (25, 25, 180), -1)
    cv2.rectangle(img, (x1, y1), (x2, y2), (230, 230, 230), 2)
    # Reel circle
    cv2.circle(img, (cx, cy), int(min(w, h) * 0.38), (15, 15, 120), -1)
    # Coiled red hose
    cv2.circle(img, (cx, cy), int(min(w, h) * 0.30), (30, 30, 220), 4)
    cv2.circle(img, (cx, cy), int(min(w, h) * 0.18), (30, 30, 220), 4)
    # Brass nozzle
    cv2.rectangle(img, (cx - 3, cy - 3), (cx + 3, cy + 3), (0, 215, 255), -1)
    
    if boxes_list is not None:
        boxes_list.append([4, x1, y1, x2, y2, 0.94])

def draw_exit_sign(img, x, y, w, h, boxes_list=None):
    """Draws green illuminated EMERGENCY EXIT sign (Class 9)."""
    x1, y1, x2, y2 = int(x), int(y), int(x + w), int(y + h)
    # Green backlit panel
    cv2.rectangle(img, (x1, y1), (x2, y2), (40, 180, 50), -1)
    cv2.rectangle(img, (x1, y1), (x2, y2), (240, 255, 240), 2)
    # White "EXIT" text & arrow
    font_scale = max(0.4, w / 140.0)
    cv2.putText(img, "EMERGENCY EXIT ->", (x1 + 8, int(y1 + h * 0.68)), cv2.FONT_HERSHEY_DUPLEX, font_scale, (255, 255, 255), 2)
    
    if boxes_list is not None:
        boxes_list.append([9, x1, y1, x2, y2, 0.98])

def draw_safety_signage(img, x, y, w, h, text="DANGER", boxes_list=None):
    """Draws warning/safety placard (Class 8)."""
    x1, y1, x2, y2 = int(x), int(y), int(x + w), int(y + h)
    # Yellow sign with black border
    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 220, 255), -1)
    cv2.rectangle(img, (x1, y1), (x2, y2), (20, 20, 20), 3)
    # Header black box
    header_h = int(h * 0.38)
    cv2.rectangle(img, (x1, y1), (x2, y1 + header_h), (20, 20, 20), -1)
    cv2.putText(img, text, (x1 + 6, int(y1 + header_h * 0.75)), cv2.FONT_HERSHEY_SIMPLEX, max(0.35, w / 160.0), (0, 220, 255), 2)
    # Bottom text
    cv2.putText(img, "AUTHORIZED ONLY", (x1 + 6, int(y1 + h * 0.8)), cv2.FONT_HERSHEY_SIMPLEX, max(0.3, w / 220.0), (20, 20, 20), 1)
    
    if boxes_list is not None:
        boxes_list.append([8, x1, y1, x2, y2, 0.95])

def draw_empty_shelf(img, x, y, w, h, bay_label="BAY-E1", boxes_list=None):
    """Draws unoccupied warehouse storage shelf bay (Class 10)."""
    x1, y1, x2, y2 = int(x), int(y), int(x + w), int(y + h)
    # Dark open bay interior
    cv2.rectangle(img, (x1, y1), (x2, y2), (40, 45, 50), -1)
    # Wire decking mesh lines
    for yy in range(y1 + 15, y2, 18):
        cv2.line(img, (x1, yy), (x2, yy), (70, 75, 80), 1)
    for xx in range(x1 + 20, x2, 25):
        cv2.line(img, (xx, y1), (xx, y2), (70, 75, 80), 1)
    # Structural orange load beams
    cv2.rectangle(img, (x1, y1), (x2, y1 + 8), (0, 110, 230), -1)
    cv2.rectangle(img, (x1, y2 - 8), (x2, y2), (0, 110, 230), -1)
    # Blue upright posts
    cv2.rectangle(img, (x1, y1), (x1 + 10, y2), (180, 70, 30), -1)
    cv2.rectangle(img, (x2 - 10, y1), (x2, y2), (180, 70, 30), -1)
    # Bay slot ID
    cv2.putText(img, bay_label, (x1 + 15, y1 + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)
    
    if boxes_list is not None:
        boxes_list.append([10, x1, y1, x2, y2, 0.92])

def draw_forklift(img, x, y, w, h, facing="right", carrying_pallet=True, boxes_list=None):
    """Draws warehouse forklift (Class 11)."""
    x1, y1, x2, y2 = int(x), int(y), int(x + w), int(y + h)
    # Main body
    body_col = (0, 200, 245) # Industrial yellow
    dark_metal = (35, 35, 35)
    
    # Chassis base
    chassis_y1 = int(y1 + h * 0.45)
    cv2.rectangle(img, (x1, chassis_y1), (x2, y2 - 15), body_col, -1)
    cv2.rectangle(img, (x1, chassis_y1), (x2, y2 - 15), (20, 20, 20), 2)
    
    # Counterweight (rear)
    cw_w = int(w * 0.28)
    if facing == "right":
        cv2.rectangle(img, (x1, chassis_y1), (x1 + cw_w, y2 - 15), (0, 160, 210), -1)
        # Overhead safety cage
        cv2.rectangle(img, (int(x1 + w * 0.25), y1), (int(x1 + w * 0.75), chassis_y1), dark_metal, 3)
        # Vertical mast (front)
        mast_x1 = int(x2 - w * 0.15)
        mast_x2 = int(x2 - w * 0.05)
        cv2.rectangle(img, (mast_x1, y1 - 10), (mast_x2, y2 - 5), dark_metal, -1)
        # Steel forks
        fork_y = y2 - 12
        cv2.line(img, (mast_x2, fork_y), (x2 + 25, fork_y), (80, 80, 80), 4)
        # Wheels
        cv2.circle(img, (int(x1 + w * 0.22), y2 - 8), 12, dark_metal, -1)
        cv2.circle(img, (int(x1 + w * 0.78), y2 - 8), 12, dark_metal, -1)
        # Operator silhouette
        cv2.circle(img, (int(x1 + w * 0.5), int(y1 + h * 0.25)), 10, (0, 215, 255), -1) # Hardhat
        cv2.rectangle(img, (int(x1 + w * 0.42), int(y1 + h * 0.35)), (int(x1 + w * 0.58), chassis_y1), (50, 205, 50), -1) # Vest
        
        # Pallet on forks
        if carrying_pallet:
            draw_pallet(img, x2 + 5, fork_y - 35, 60, 35, loaded=True, boxes_list=boxes_list)
    else:
        cv2.rectangle(img, (x2 - cw_w, chassis_y1), (x2, y2 - 15), (0, 160, 210), -1)
        cv2.rectangle(img, (int(x1 + w * 0.25), y1), (int(x1 + w * 0.75), chassis_y1), dark_metal, 3)
        mast_x1 = int(x1 + w * 0.05)
        mast_x2 = int(x1 + w * 0.15)
        cv2.rectangle(img, (mast_x1, y1 - 10), (mast_x2, y2 - 5), dark_metal, -1)
        fork_y = y2 - 12
        cv2.line(img, (mast_x1, fork_y), (x1 - 25, fork_y), (80, 80, 80), 4)
        cv2.circle(img, (int(x1 + w * 0.22), y2 - 8), 12, dark_metal, -1)
        cv2.circle(img, (int(x1 + w * 0.78), y2 - 8), 12, dark_metal, -1)
        cv2.circle(img, (int(x1 + w * 0.5), int(y1 + h * 0.25)), 10, (0, 215, 255), -1)
        cv2.rectangle(img, (int(x1 + w * 0.42), int(y1 + h * 0.35)), (int(x1 + w * 0.58), chassis_y1), (50, 205, 50), -1)
        if carrying_pallet:
            draw_pallet(img, x1 - 65, fork_y - 35, 60, 35, loaded=True, boxes_list=boxes_list)

    if boxes_list is not None:
        boxes_list.append([11, x1, y1 - 10, x2 + (25 if facing == "right" else 0), y2, 0.96])

def draw_vehicle(img, x, y, w, h, facing="left", boxes_list=None):
    """Draws transport dump truck / delivery vehicle (Class 12)."""
    x1, y1, x2, y2 = int(x), int(y), int(x + w), int(y + h)
    
    cab_w = int(w * 0.35)
    bed_w = w - cab_w
    wheel_r = int(h * 0.16)
    wheel_y = y2 - wheel_r
    
    if facing == "left":
        # Cab (front left)
        cv2.rectangle(img, (x1, int(y1 + h * 0.25)), (x1 + cab_w, wheel_y), (180, 80, 40), -1)
        # Windshield
        cv2.rectangle(img, (x1 + 5, int(y1 + h * 0.3)), (x1 + cab_w - 10, int(y1 + h * 0.55)), (220, 220, 240), -1)
        # Cargo bed
        cv2.rectangle(img, (x1 + cab_w, y1), (x2, wheel_y), (100, 110, 120), -1)
        cv2.rectangle(img, (x1 + cab_w, y1), (x2, wheel_y), (50, 55, 60), 2)
        # Headlight
        cv2.rectangle(img, (x1, int(wheel_y - 20)), (x1 + 6, int(wheel_y - 8)), (0, 240, 255), -1)
        # Wheels
        cv2.circle(img, (int(x1 + cab_w * 0.45), wheel_y), wheel_r, (25, 25, 25), -1)
        cv2.circle(img, (int(x1 + cab_w + bed_w * 0.4), wheel_y), wheel_r, (25, 25, 25), -1)
        cv2.circle(img, (int(x1 + cab_w + bed_w * 0.8), wheel_y), wheel_r, (25, 25, 25), -1)
    else:
        cv2.rectangle(img, (x2 - cab_w, int(y1 + h * 0.25)), (x2, wheel_y), (180, 80, 40), -1)
        cv2.rectangle(img, (x2 - cab_w + 10, int(y1 + h * 0.3)), (x2 - 5, int(y1 + h * 0.55)), (220, 220, 240), -1)
        cv2.rectangle(img, (x1, y1), (x2 - cab_w, wheel_y), (100, 110, 120), -1)
        cv2.rectangle(img, (x1, y1), (x2 - cab_w, wheel_y), (50, 55, 60), 2)
        cv2.rectangle(img, (x2 - 6, int(wheel_y - 20)), (x2, int(wheel_y - 8)), (0, 240, 255), -1)
        cv2.circle(img, (int(x2 - cab_w * 0.45), wheel_y), wheel_r, (25, 25, 25), -1)
        cv2.circle(img, (int(x1 + bed_w * 0.3), wheel_y), wheel_r, (25, 25, 25), -1)
        cv2.circle(img, (int(x1 + bed_w * 0.7), wheel_y), wheel_r, (25, 25, 25), -1)
        
    if boxes_list is not None:
        boxes_list.append([12, x1, y1, x2, y2, 0.96])

def draw_machinery(img, x, y, w, h, boom_angle=0.0, boxes_list=None):
    """Draws heavy construction hydraulic excavator (Class 14)."""
    x1, y1, x2, y2 = int(x), int(y), int(x + w), int(y + h)
    
    # Crawler tracks (bottom)
    track_h = int(h * 0.22)
    track_y1 = y2 - track_h
    cv2.rectangle(img, (x1, track_y1), (int(x1 + w * 0.65), y2), (30, 30, 30), -1)
    cv2.rectangle(img, (x1, track_y1), (int(x1 + w * 0.65), y2), (60, 60, 60), 2)
    for roller_x in range(x1 + 15, int(x1 + w * 0.65), 30):
        cv2.circle(img, (roller_x, int(track_y1 + track_h / 2)), int(track_h * 0.35), (70, 70, 70), 2)
        
    # Revolving cab & engine body
    cab_x1 = x1 + 10
    cab_x2 = int(x1 + w * 0.55)
    cab_y1 = int(y1 + h * 0.35)
    cv2.rectangle(img, (cab_x1, cab_y1), (cab_x2, track_y1), (0, 180, 235), -1)
    cv2.rectangle(img, (cab_x1, cab_y1), (cab_x2, track_y1), (20, 20, 20), 2)
    # Cab window
    cv2.rectangle(img, (cab_x1 + 10, cab_y1 + 10), (int(cab_x1 + (cab_x2 - cab_x1) * 0.5), cab_y1 + int(h * 0.25)), (220, 230, 240), -1)
    # Operator silhouette inside
    cv2.circle(img, (cab_x1 + 25, cab_y1 + 25), 8, (0, 215, 255), -1) # Hardhat
    
    # Articulated Boom, Arm and Bucket
    boom_base = (int(cab_x2 - 10), int(track_y1 - 15))
    boom_elbow = (int(cab_x2 + w * 0.25), int(y1 + h * 0.15 + math.sin(boom_angle) * 20))
    bucket_pin = (int(x2 - 30), int(y1 + h * 0.55 + math.cos(boom_angle) * 30))
    
    # Heavy boom beams
    cv2.line(img, boom_base, boom_elbow, (0, 180, 235), 14)
    cv2.line(img, boom_base, boom_elbow, (20, 20, 20), 2)
    cv2.line(img, boom_elbow, bucket_pin, (0, 180, 235), 10)
    cv2.line(img, boom_elbow, bucket_pin, (20, 20, 20), 2)
    
    # Hydraulic cylinder
    cv2.line(img, (boom_base[0] - 15, boom_base[1] - 15), (boom_elbow[0] - 10, boom_elbow[1] + 15), (180, 180, 180), 4)
    
    # Bucket
    bucket_pts = np.array([
        bucket_pin,
        [bucket_pin[0] + 25, bucket_pin[1] + 15],
        [bucket_pin[0] + 15, bucket_pin[1] + 35],
        [bucket_pin[0] - 10, bucket_pin[1] + 25]
    ], np.int32)
    cv2.fillPoly(img, [bucket_pts], (40, 40, 40))
    cv2.polylines(img, [bucket_pts], True, (10, 10, 10), 2)
    
    if boxes_list is not None:
        boxes_list.append([14, x1, y1, x2, y2, 0.97])

# ==========================================
# CCTV HUD OVERLAY HELPER
# ==========================================

def render_cctv_hud(frame, cam_id, site_name, elapsed_sec, active_alert_msg=None, severity="NORMAL"):
    """Renders professional surveillance CCTV On-Screen Display."""
    h, w = frame.shape[:2]
    
    # Top HUD Bar
    cv2.rectangle(frame, (0, 0), (w, 48), (15, 15, 15), -1)
    cv2.line(frame, (0, 48), (w, 48), (60, 60, 60), 1)
    
    # Camera ID & Site
    cv2.putText(frame, f"[ {cam_id} ] - {site_name}", (25, 32), cv2.FONT_HERSHEY_DUPLEX, 0.75, (240, 240, 240), 2)
    
    # Live ISO Timestamp: 2026-11-18 10:00:00 + elapsed
    total_sec = int(elapsed_sec)
    mm = total_sec // 60
    ss = total_sec % 60
    ms = int((elapsed_sec - total_sec) * 100)
    time_str = f"2026-11-18 10:{mm:02d}:{ss:02d}.{ms:02d} (T={total_sec:03d}s / 300s)"
    cv2.putText(frame, time_str, (w - 620, 32), cv2.FONT_HERSHEY_DUPLEX, 0.70, (200, 220, 220), 2)
    
    # Blinking REC dot
    if (int(elapsed_sec * 2) % 2) == 0:
        cv2.circle(frame, (w - 45, 25), 8, (0, 0, 240), -1)
    cv2.putText(frame, "REC", (w - 100, 32), cv2.FONT_HERSHEY_DUPLEX, 0.65, (0, 0, 240), 2)
    
    # Bottom Alert Status Banner
    if active_alert_msg:
        banner_col = (0, 0, 180) if severity == "CRITICAL" else (0, 140, 220)
        cv2.rectangle(frame, (0, h - 55), (w, h), banner_col, -1)
        cv2.line(frame, (0, h - 55), (w, h - 55), (255, 255, 255), 2)
        alert_icon = "🚨 [CRITICAL ALERT]" if severity == "CRITICAL" else "⚠️ [WARNING]"
        cv2.putText(frame, f"{alert_icon} {active_alert_msg}", (30, h - 18), cv2.FONT_HERSHEY_DUPLEX, 0.75, (255, 255, 255), 2)
    else:
        cv2.rectangle(frame, (0, h - 35), (w, h), (20, 20, 20), -1)
        cv2.putText(frame, "STATUS: ALL ZONES NORMAL | PERIMETER ACTIVE | DWELL TIMERS CLEAR", (30, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 120), 1)


# ==========================================
# 1. CONSTRUCTION SITE VIDEO GENERATOR (5 MIN)
# ==========================================

def generate_construction_site_video(output_mp4, mock_detections_json, duration_sec=300, fps=10):
    """
    Generates 5-minute Construction Site Safety & Zone Intelligence Video.
    Includes:
      - ZONE_CONST_EXIT_01: Emergency Evacuation Gate (Right)
      - ZONE_CONST_MACHINERY_01: Excavator Swing Radius (Left)
      - ZONE_CONST_WALKWAY_01: Safe Pedestrian Walkway (Center)
    Events across 5 minutes:
      - 0-60s: Normal baseline operations, compliant workers, active excavator
      - 60-120s: Delivery vehicle drops pallet & debris blocking exit gate -> CRITICAL EXIT BLOCKAGE ALERT
      - 120-180s: Worker walks into excavator swing radius -> CRITICAL PROXIMITY VIOLATION
      - 180-240s: Worker without helmet & vest enters -> PPE VIOLATION; Oil spill on walkway -> OBSTRUCTION
      - 240-300s: Fire flare-up -> FIRE ALERT, worker uses extinguisher, personnel evacuate through gate
    """
    print(f"\n=======================================================")
    print(f"[*] Generating Construction Site Video: {output_mp4}")
    print(f"[*] Duration: {duration_sec}s ({duration_sec//60} mins) | FPS: {fps} | Total Frames: {duration_sec * fps}")
    print(f"=======================================================")
    
    w, h = 1920, 1080
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_mp4, fourcc, fps, (w, h))
    
    total_frames = duration_sec * fps
    mock_detections = {}
    start_t = time.time()
    
    # Define Construction Zones
    zone_exit = np.array([[1350, 450], [1850, 450], [1850, 1020], [1350, 1020]], np.int32)
    zone_machinery = np.array([[80, 200], [680, 200], [680, 800], [80, 800]], np.int32)
    zone_walkway = np.array([[720, 220], [980, 220], [980, 1020], [720, 1020]], np.int32)
    
    for frame_idx in range(total_frames):
        t_sec = frame_idx / float(fps)
        boxes = []
        
        # 1. Base Construction Site Background
        # Graded gravel ground (earthy brownish-grey)
        frame = np.full((h, w, 3), (110, 125, 140), dtype=np.uint8)
        # Horizon sky
        cv2.rectangle(frame, (0, 0), (w, 200), (210, 190, 170), -1)
        # Background building frame / scaffolding
        for bx in range(200, 1800, 160):
            cv2.rectangle(frame, (bx, 60), (bx + 80, 200), (90, 95, 100), -1)
            cv2.line(frame, (bx, 60), (bx + 80, 200), (60, 65, 70), 2)
            cv2.line(frame, (bx + 80, 60), (bx, 200), (60, 65, 70), 2)
        cv2.line(frame, (0, 200), (w, 200), (70, 75, 80), 3) # Ground line
        
        # 2. Draw Zone Outlines on Ground
        # Zone Walkway (Green safety lane)
        overlay = frame.copy()
        cv2.fillPoly(overlay, [zone_walkway], (80, 150, 80))
        cv2.fillPoly(overlay, [zone_exit], (80, 80, 180)) # Red evacuation exit
        cv2.fillPoly(overlay, [zone_machinery], (60, 140, 180)) # Yellow danger radius
        cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)
        
        # Zone borders & labels
        cv2.polylines(frame, [zone_walkway], True, (50, 200, 50), 2)
        cv2.putText(frame, "ZONE_CONST_WALKWAY_01 (Safe Corridor)", (730, 250), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (50, 230, 50), 2)
        
        cv2.polylines(frame, [zone_exit], True, (0, 0, 230), 3)
        cv2.putText(frame, "ZONE_CONST_EXIT_01 (Emergency Evacuation Path)", (1360, 485), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 0, 240), 2)
        
        cv2.polylines(frame, [zone_machinery], True, (0, 215, 255), 2)
        cv2.putText(frame, "ZONE_CONST_MACHINERY_01 (Excavator Swing Radius)", (90, 235), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 215, 255), 2)

        # 3. Permanent Safety Infrastructure
        # Emergency Gate Structure at right
        cv2.rectangle(frame, (1550, 300), (1850, 500), (50, 60, 60), -1)
        draw_exit_sign(frame, 1580, 320, 240, 55, boxes) # Class 9
        draw_safety_signage(frame, 1580, 390, 240, 90, "EMERGENCY EXIT", boxes) # Class 8
        
        # Fire Safety Station on construction post
        cv2.rectangle(frame, (1020, 350), (1040, 750), (70, 70, 70), -1) # Post
        draw_safety_signage(frame, 1005, 300, 160, 60, "FIRE POINT", boxes) # Class 8
        draw_fire_extinguisher(frame, 1050, 420, 35, 75, boxes) # Class 3
        draw_fire_hose(frame, 1050, 520, 75, 75, boxes) # Class 4
        
        # Safety Cones marking machinery edge
        draw_safety_cone(frame, 660, 300, 25, 40, boxes) # Class 15
        draw_safety_cone(frame, 660, 550, 25, 40, boxes) # Class 15
        draw_safety_cone(frame, 660, 760, 25, 40, boxes) # Class 15

        # 4. Heavy Machinery (Class 14) - Excavator in Zone 1
        boom_osc = math.sin(t_sec * 0.8)
        draw_machinery(frame, 120, 340, 480, 360, boom_angle=boom_osc, boxes_list=boxes)
        
        # 5. Dynamic Actors & Scenarios across 5 minutes (0 - 300s)
        alert_msg = None
        alert_sev = "NORMAL"

        # --- SCENARIO TIMELINE ---

        # (A) Minute 0 (0-60s): Compliant Normal Operations
        # Worker 1 walking down walkway with helmet & vest
        w1_phase = t_sec * 4.0
        w1_y = 280 + int((t_sec % 30) * 22)
        draw_person(frame, 820, w1_y, 45, 115, has_helmet=True, has_vest=True, walk_phase=w1_phase, boxes_list=boxes)
        
        # Worker 2 supervising near fire point
        draw_person(frame, 1150, 500, 45, 115, has_helmet=True, has_vest=True, walk_phase=0.0, boxes_list=boxes)

        # (B) Minute 1 (60-120s): EMERGENCY EXIT BLOCKAGE EVENT (Core Target)
        if 55 <= t_sec <= 125:
            # Construction Dump Truck / Delivery Vehicle enters and drops pallet & debris in exit
            if 55 <= t_sec <= 80:
                truck_x = int(1920 - (t_sec - 55) * 25)
                draw_vehicle(frame, truck_x, 720, 240, 130, facing="left", boxes_list=boxes)
            elif 80 < t_sec <= 125:
                # Truck departing
                truck_x = int(1300 + (t_sec - 80) * 35)
                if truck_x < 1920:
                    draw_vehicle(frame, truck_x, 720, 240, 130, facing="right", boxes_list=boxes)

            # Blockage objects dwelling inside ZONE_CONST_EXIT_01 at (1460, 680)
            if 65 <= t_sec <= 118:
                # Class 5: Pallet
                draw_pallet(frame, 1460, 680, 130, 80, loaded=True, boxes_list=boxes)
                # Class 13: Obstacle crate
                draw_obstacle(frame, 1610, 690, 95, 75, label="DEBRIS", boxes_list=boxes)
                
                dwell = t_sec - 65.0
                if dwell >= 4.0:
                    alert_msg = f"EMERGENCY EXIT OBSTRUCTED: Pallet & Debris in Evacuation Gate! (Dwell: {dwell:.1f}s >= 4.0s)"
                    alert_sev = "CRITICAL"
                    
            if 110 <= t_sec <= 125:
                # Site safety worker arrives and clears blockage
                clearer_x = int(1350 + (t_sec - 110) * 15)
                draw_person(frame, min(clearer_x, 1450), 660, 45, 115, has_helmet=True, has_vest=True, walk_phase=t_sec*4, boxes_list=boxes)

        # (C) Minute 2 (120-180s): MACHINERY ZONE PROXIMITY VIOLATION
        if 125 <= t_sec <= 185:
            # Worker walks across site and steps directly into excavator swing radius
            if 130 <= t_sec <= 170:
                intruder_x = int(760 - (t_sec - 130) * 12) if t_sec < 145 else int(580 + (t_sec - 145) * 12)
                intruder_y = 520
                draw_person(frame, intruder_x, intruder_y, 45, 115, has_helmet=True, has_vest=True, walk_phase=t_sec*4, boxes_list=boxes)
                
                # Ground contact in zone_machinery? intruder_x < 680
                if intruder_x < 680:
                    dwell_mach = t_sec - 137.0
                    if dwell_mach >= 1.0:
                        alert_msg = f"MACHINERY PROXIMITY HAZARD: Worker inside Active Excavator Swing Radius! (Dwell: {dwell_mach:.1f}s >= 1.0s)"
                        alert_sev = "CRITICAL"

        # (D) Minute 3 (180-240s): PPE VIOLATION + GROUND HAZARD (Spill & Cones)
        if 180 <= t_sec <= 245:
            # Unauthorized person walking without helmet (1) and without vest (2)
            if 185 <= t_sec <= 225:
                non_compliant_y = 300 + int((t_sec - 185) * 14)
                draw_person(frame, 780, non_compliant_y, 45, 115, has_helmet=False, has_vest=False, walk_phase=t_sec*3.5, boxes_list=boxes)
                alert_msg = "PPE COMPLIANCE VIOLATION: Worker detected WITHOUT Safety Helmet & High-Vis Vest!"
                alert_sev = "WARNING"
                
            # Spill event at walkway entrance
            if 200 <= t_sec <= 245:
                draw_spill(frame, 850, 780, 65, 35, color=(30, 80, 160), boxes_list=boxes) # Class 7: Oil spill
                draw_safety_cone(frame, 760, 760, 25, 40, boxes) # Class 15
                draw_safety_cone(frame, 930, 760, 25, 40, boxes) # Class 15
                if 208 <= t_sec <= 235:
                    alert_msg = "GROUND HAZARD: Oil Spill obstructing Safe Walkway Corridor! Safety cones deployed."
                    alert_sev = "WARNING"

        # (E) Minute 4 (240-300s): FIRE INCIDENT & EVACUATION
        if 245 <= t_sec <= 300:
            # Active flame near equipment
            draw_fire(frame, 560, 680, 70, 95, t=t_sec, boxes_list=boxes) # Class 6: Fire
            if t_sec < 280:
                alert_msg = "CRITICAL HAZARD DETECTED: Active Fire Outbreak! Emergency Suppression & Evacuation Triggered."
                alert_sev = "CRITICAL"
            else:
                alert_msg = "FIRE SUPPRESSED: Personnel successfully evacuated through unblocked Emergency Exit."
                alert_sev = "NORMAL"

            # Worker responds with extinguisher
            if 255 <= t_sec <= 285:
                firefighter_x = int(1050 - (t_sec - 255) * 16)
                draw_person(frame, max(650, firefighter_x), 640, 45, 115, has_helmet=True, has_vest=True, walk_phase=t_sec*4.5, boxes_list=boxes)
            # Workers evacuating towards emergency gate (right)
            evac_x1 = int(850 + (t_sec - 250) * 30)
            evac_x2 = int(920 + (t_sec - 252) * 28)
            if evac_x1 < 1800:
                draw_person(frame, evac_x1, 620, 45, 115, has_helmet=True, has_vest=True, walk_phase=t_sec*5, boxes_list=boxes)
            if evac_x2 < 1800:
                draw_person(frame, evac_x2, 700, 45, 115, has_helmet=True, has_vest=True, walk_phase=t_sec*5, boxes_list=boxes)

        # 6. Render CCTV OSD HUD
        render_cctv_hud(frame, "CAM_CONST_01", "West Perimeter Heavy Construction & Loading Bay", t_sec, alert_msg, alert_sev)
        
        # Write Frame
        writer.write(frame)
        
        # Record Mock Detections (every frame or sample keyframes)
        if frame_idx % 5 == 0: # 2 fps sample for lightweight JSON
            mock_detections[frame_idx] = {
                "timestamp": round(t_sec, 2),
                "camera_id": "CAM_CONST_01",
                "detections": boxes
            }
            
        if (frame_idx + 1) % 300 == 0:
            pct = ((frame_idx + 1) / total_frames) * 100
            elapsed = time.time() - start_t
            fps_actual = (frame_idx + 1) / elapsed
            print(f"  -> Progress: {frame_idx + 1}/{total_frames} frames ({pct:.0f}%) | Time: {elapsed:.1f}s | Speed: {fps_actual:.1f} fps")
            
    writer.release()
    print(f"[+] Construction Site Video generated successfully: {output_mp4}")
    
    with open(mock_detections_json, "w") as f:
        json.dump(mock_detections, f)
    print(f"[+] Mock Ground Truth Detections saved: {mock_detections_json}")


# ==========================================
# 2. WAREHOUSE VIDEO GENERATOR (5 MIN)
# ==========================================

def generate_warehouse_video(output_mp4, mock_detections_json, duration_sec=300, fps=10):
    """
    Generates 5-minute Warehouse Operations & Emergency Exit Blockage Intelligence Video.
    Includes:
      - ZONE_EXIT_01: Main Emergency Fire Exit ([800, 500] to [1400, 1080]) - EXACT MATCH WITH zones_config.json!
      - ZONE_AISLE_01: Walkway Aisle 3 ([300, 200] to [650, 1080]) - EXACT MATCH WITH zones_config.json!
      - Racking Bays with empty shelves (Class 10) and loaded pallets (Class 5)
    Events across 5 minutes:
      - 0-60s: Normal forklift transport, compliant workers walking in Aisle 3, Exit clear
      - 60-120s: Forklift drops pallets & obstacle box in ZONE_EXIT_01 -> CRITICAL EMERGENCY EXIT BLOCKED ALERT (>4.0s dwell)
      - 120-180s: Chemical spill & fallen carton in Walkway Aisle 3 -> HIGH WALKWAY OBSTRUCTION ALERT (>8.0s dwell)
      - 180-240s: Transport vehicle arrives at loading portal; worker enters forklift zone without PPE -> PROXIMITY & PPE ALERT
      - 240-300s: Fire flare-up at rack wiring -> CRITICAL FIRE ALERT, extinguisher deployment, personnel evacuate via Exit
    """
    print(f"\n=======================================================")
    print(f"[*] Generating Warehouse Operations Video: {output_mp4}")
    print(f"[*] Duration: {duration_sec}s ({duration_sec//60} mins) | FPS: {fps} | Total Frames: {duration_sec * fps}")
    print(f"=======================================================")
    
    w, h = 1920, 1080
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_mp4, fourcc, fps, (w, h))
    
    total_frames = duration_sec * fps
    mock_detections = {}
    start_t = time.time()
    
    # Exact Zones from zones_config.json
    zone_exit = np.array([[800, 500], [1400, 500], [1400, 1080], [800, 1080]], np.int32)
    zone_aisle = np.array([[300, 200], [650, 200], [650, 1080], [300, 1080]], np.int32)
    
    for frame_idx in range(total_frames):
        t_sec = frame_idx / float(fps)
        boxes = []
        
        # 1. Base Warehouse Interior (Polished concrete floor & industrial walls)
        frame = np.full((h, w, 3), (180, 185, 190), dtype=np.uint8)
        # Concrete floor perspective lines
        for floor_x in range(0, w, 150):
            cv2.line(frame, (floor_x, 480), (int(floor_x * 1.3 - 200), h), (160, 165, 170), 1)
        # Ceiling & high rafters
        cv2.rectangle(frame, (0, 0), (w, 180), (80, 85, 90), -1)
        for rafter_x in range(100, w, 220):
            cv2.line(frame, (rafter_x, 0), (rafter_x + 60, 180), (60, 65, 70), 3)
            # High-bay LED pendant lights
            cv2.circle(frame, (rafter_x + 30, 175), 12, (240, 245, 255), -1)
            
        # 2. Zone Overlays on Floor
        overlay = frame.copy()
        cv2.fillPoly(overlay, [zone_exit], (60, 60, 210)) # Red Emergency Exit exclusion box
        cv2.fillPoly(overlay, [zone_aisle], (60, 170, 70)) # Green Pedestrian Walkway
        cv2.addWeighted(overlay, 0.22, frame, 0.78, 0, frame)
        
        # Yellow hazard border lines for zones
        cv2.polylines(frame, [zone_aisle], True, (0, 220, 255), 3)
        cv2.putText(frame, "ZONE_AISLE_01: Walkway Aisle 3 (Pedestrian Lane)", (310, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 220, 255), 2)
        
        # Emergency exit hatching / box
        cv2.polylines(frame, [zone_exit], True, (0, 0, 240), 3)
        cv2.putText(frame, "ZONE_EXIT_01: Main Emergency Fire Exit (Zero Obstruction)", (810, 530), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 0, 240), 2)
        # Red diagonal hash marks inside exit box
        for hx in range(800, 1400, 60):
            cv2.line(frame, (hx, 500), (min(1400, hx + 100), 600), (100, 100, 220), 1)

        # 3. Permanent Warehouse Infrastructure
        # Main Emergency Fire Exit Doors in background wall (800 to 1400 at y=320-500)
        cv2.rectangle(frame, (860, 310), (1340, 500), (45, 50, 55), -1) # Door frame
        cv2.rectangle(frame, (880, 330), (1090, 500), (35, 40, 45), -1) # Left Door
        cv2.rectangle(frame, (1110, 330), (1320, 500), (35, 40, 45), -1) # Right Door
        # Panic push-bars
        cv2.line(frame, (900, 420), (1070, 420), (0, 215, 255), 4)
        cv2.line(frame, (1130, 420), (1300, 420), (0, 215, 255), 4)
        # Class 9: Illuminated Exit Sign above doors
        draw_exit_sign(frame, 960, 250, 280, 55, boxes)
        
        # Fire Safety Station on right wall pillar
        cv2.rectangle(frame, (1420, 250), (1450, 750), (100, 105, 110), -1)
        draw_safety_signage(frame, 1470, 260, 180, 65, "FIRE POINT", boxes) # Class 8
        draw_fire_extinguisher(frame, 1470, 340, 40, 85, boxes) # Class 3
        draw_fire_hose(frame, 1470, 450, 85, 85, boxes) # Class 4

        # Warehouse Pallet Storage Racking on Left (x=10 to 280) and Right (x=1580 to 1910)
        # Class 10: Empty Shelves + Class 5: Stored Pallets
        # Left Racks
        draw_pallet(frame, 20, 200, 120, 70, loaded=True, boxes_list=boxes)
        draw_pallet(frame, 150, 200, 120, 70, loaded=True, boxes_list=boxes)
        draw_empty_shelf(frame, 20, 280, 125, 80, bay_label="BAY-A1", boxes_list=boxes) # Class 10
        draw_pallet(frame, 150, 280, 120, 75, loaded=True, boxes_list=boxes)
        draw_empty_shelf(frame, 20, 370, 125, 80, bay_label="BAY-A2", boxes_list=boxes) # Class 10
        draw_pallet(frame, 150, 370, 120, 75, loaded=True, boxes_list=boxes)
        
        # Right Racks
        draw_pallet(frame, 1600, 200, 135, 75, loaded=True, boxes_list=boxes)
        draw_empty_shelf(frame, 1750, 200, 135, 75, bay_label="BAY-C1", boxes_list=boxes) # Class 10
        draw_empty_shelf(frame, 1600, 285, 135, 80, bay_label="BAY-C2", boxes_list=boxes) # Class 10
        draw_pallet(frame, 1750, 285, 135, 80, loaded=True, boxes_list=boxes)
        draw_pallet(frame, 1600, 375, 135, 80, loaded=True, boxes_list=boxes)
        draw_pallet(frame, 1750, 375, 135, 80, loaded=True, boxes_list=boxes)

        # 4. Dynamic Actors & Scenarios across 5 minutes (0 - 300s)
        alert_msg = None
        alert_sev = "NORMAL"

        # --- SCENARIO TIMELINE ---

        # (A) Minute 0 (0-60s): Compliant Baseline
        # Compliant Worker walking inside Walkway Aisle 3
        w_y = 250 + int((t_sec % 25) * 30)
        draw_person(frame, 450, w_y, 48, 120, has_helmet=True, has_vest=True, walk_phase=t_sec*4, boxes_list=boxes)
        
        # Forklift driving in travel corridor carrying loaded pallet
        if 0 <= t_sec <= 55:
            fl_x = 700 + int((t_sec % 30) * 18)
            draw_forklift(frame, fl_x, 700, 160, 110, facing="right", carrying_pallet=True, boxes_list=boxes)

        # (B) Minute 1 (60-120s): EMERGENCY EXIT BLOCKAGE ALERT (CORE TARGET)
        if 55 <= t_sec <= 130:
            # Forklift drives up to Emergency Exit door and dumps pallets directly inside ZONE_EXIT_01!
            if 55 <= t_sec <= 72:
                # Forklift approaching exit
                fl_x = int(1450 - (t_sec - 55) * 25)
                draw_forklift(frame, fl_x, 620, 160, 110, facing="left", carrying_pallet=(t_sec < 68), boxes_list=boxes)
            elif 72 < t_sec <= 105:
                # Forklift drives away, leaving pallets stranded
                fl_x = int(1025 + (t_sec - 72) * 20)
                if fl_x < 1920:
                    draw_forklift(frame, fl_x, 750, 160, 110, facing="right", carrying_pallet=False, boxes_list=boxes)

            # Blockage Pallet and Obstacle sitting stationary inside ZONE_EXIT_01 (800-1400)
            if 68 <= t_sec <= 118:
                # Pallet dropped right in evacuation threshold
                draw_pallet(frame, 950, 640, 150, 95, loaded=True, boxes_list=boxes)
                # Obstacle box dropped next to it
                draw_obstacle(frame, 1120, 660, 90, 80, label="BLOCKAGE", boxes_list=boxes)
                
                dwell = t_sec - 68.0
                if dwell >= 4.0: # 4.0s threshold defined in zones_config.json!
                    alert_msg = f"EMERGENCY EXIT BLOCKED: Pallet & Obstacle obstructing Zone EXIT_01! (Dwell: {dwell:.1f}s >= 4.0s threshold)"
                    alert_sev = "CRITICAL"

            # Operator returns with forklift to clear the exit
            if 105 <= t_sec <= 126:
                fl_clear_x = int(1500 - (t_sec - 105) * 35)
                draw_forklift(frame, max(fl_clear_x, 920), 620, 160, 110, facing="left", carrying_pallet=(t_sec > 118), boxes_list=boxes)

        # (C) Minute 2 (120-180s): WALKWAY AISLE 3 OBSTRUCTION & CHEMICAL SPILL
        if 125 <= t_sec <= 185:
            # Worker accidentally drops canister at t=128s, causing spill in Aisle 3
            if 128 <= t_sec <= 180:
                # Spill inside ZONE_AISLE_01 ([300, 200] to [650, 1080]) at x=460, y=650
                draw_spill(frame, 460, 650, 80, 45, color=(240, 160, 40), boxes_list=boxes) # Class 7: Spill
                # Obstacle box
                draw_obstacle(frame, 380, 610, 85, 75, label="FALLEN BOX", boxes_list=boxes) # Class 13: Obstacle
                
                dwell_aisle = t_sec - 128.0
                if dwell_aisle >= 8.0: # 8.0s threshold from zones_config.json!
                    alert_msg = f"WALKWAY OBSTRUCTED: Chemical Spill & Hazard Box in Aisle 3! (Dwell: {dwell_aisle:.1f}s >= 8.0s)"
                    alert_sev = "WARNING"
                    
            if 150 <= t_sec <= 185:
                # Deploy safety cones around spill
                draw_safety_cone(frame, 340, 630, 30, 48, boxes) # Class 15
                draw_safety_cone(frame, 560, 630, 30, 48, boxes) # Class 15
                draw_safety_cone(frame, 460, 720, 30, 48, boxes) # Class 15

        # (D) Minute 3 (180-240s): VEHICLE ARRIVAL & WORKER WITHOUT PPE IN FORKLIFT LANE
        if 180 <= t_sec <= 245:
            # Transport / Delivery vehicle enters loading portal at right
            if 185 <= t_sec <= 235:
                veh_x = int(1920 - min(420, (t_sec - 185) * 20))
                draw_vehicle(frame, veh_x, 700, 260, 140, facing="left", boxes_list=boxes) # Class 12: Vehicle

            # Pedestrian enters without vest (2) and without helmet (1) right into active forklift travel path
            if 195 <= t_sec <= 230:
                unauth_x = int(720 + (t_sec - 195) * 15)
                draw_person(frame, min(unauth_x, 1100), 720, 48, 120, has_helmet=False, has_vest=False, walk_phase=t_sec*4, boxes_list=boxes)
                alert_msg = "SAFETY VIOLATION: Pedestrian without PPE entering Active Heavy Vehicle & Forklift Lane!"
                alert_sev = "WARNING"

        # (E) Minute 4 (240-300s): FIRE EMERGENCY & EVACUATION THROUGH EMERGENCY EXIT
        if 245 <= t_sec <= 300:
            # Active fire ignites near electrical rack base
            draw_fire(frame, 1580, 520, 75, 105, t=t_sec, boxes_list=boxes) # Class 6: Fire
            if t_sec < 282:
                alert_msg = "CRITICAL EMERGENCY: Fire Incident detected near Bay C! Evacuate via Emergency Exit 01."
                alert_sev = "CRITICAL"
            else:
                alert_msg = "INCIDENT CONTROLLED: Emergency Exit path held clear throughout evacuation."
                alert_sev = "NORMAL"

            # Worker grabs fire extinguisher and suppresses fire
            if 250 <= t_sec <= 285:
                responder_x = int(1470 - (t_sec - 250) * 8)
                draw_person(frame, max(1490, responder_x), 490, 48, 120, has_helmet=True, has_vest=True, walk_phase=t_sec*4, boxes_list=boxes)
                
            # Personnel evacuating through ZONE_EXIT_01 doors
            evac_y1 = int(750 - (t_sec - 248) * 16)
            evac_y2 = int(820 - (t_sec - 250) * 15)
            if evac_y1 > 420:
                draw_person(frame, 980, evac_y1, 46, 115, has_helmet=True, has_vest=True, walk_phase=t_sec*5, boxes_list=boxes)
            if evac_y2 > 420:
                draw_person(frame, 1140, evac_y2, 46, 115, has_helmet=True, has_vest=True, walk_phase=t_sec*5, boxes_list=boxes)

        # 5. Render CCTV OSD HUD
        render_cctv_hud(frame, "CAM_WH_01", "Distribution Center Sector 4 - Main Fire Exit & Racks", t_sec, alert_msg, alert_sev)
        
        # Write Frame
        writer.write(frame)
        
        # Record Mock Ground Truth
        if frame_idx % 5 == 0:
            mock_detections[frame_idx] = {
                "timestamp": round(t_sec, 2),
                "camera_id": "CAM_WH_01",
                "detections": boxes
            }
            
        if (frame_idx + 1) % 300 == 0:
            pct = ((frame_idx + 1) / total_frames) * 100
            elapsed = time.time() - start_t
            fps_actual = (frame_idx + 1) / elapsed
            print(f"  -> Progress: {frame_idx + 1}/{total_frames} frames ({pct:.0f}%) | Time: {elapsed:.1f}s | Speed: {fps_actual:.1f} fps")
            
    writer.release()
    print(f"[+] Warehouse Video generated successfully: {output_mp4}")
    
    with open(mock_detections_json, "w") as f:
        json.dump(mock_detections, f)
    print(f"[+] Mock Ground Truth Detections saved: {mock_detections_json}")


if __name__ == "__main__":
    os.makedirs("data/sample_videos", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    # Generate Construction Site Video (5 mins = 300s, 10 fps = 3000 frames)
    const_video_path = "data/sample_videos/construction_site_5min.mp4"
    const_meta_path = "data/mock_detections_construction.json"
    generate_construction_site_video(const_video_path, const_meta_path, duration_sec=300, fps=10)
    
    # Generate Warehouse Video (5 mins = 300s, 10 fps = 3000 frames)
    wh_video_path = "data/sample_videos/warehouse_5min.mp4"
    wh_meta_path = "data/mock_detections_warehouse.json"
    generate_warehouse_video(wh_video_path, wh_meta_path, duration_sec=300, fps=10)
    
    print("\n[SUCCESS] Both 5-minute video streams and ground truth datasets created!")

