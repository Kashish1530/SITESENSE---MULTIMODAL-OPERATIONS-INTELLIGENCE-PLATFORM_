"""
SiteSense Visual Inspector CLI
Upload or test any image immediately to see:
1. Detected bounding boxes drawn on the image (saved to output/)
2. Detected objects & confidence scores
3. Policy compliance evaluation against SiteSense Safety Policies
"""

import sys
import os
import json
from pathlib import Path
import cv2
import numpy as np

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from vision_service.detector import detector
from agentic.compliance_engine import evaluate_inspection_compliance

CLASS_COLORS = {
    "person": (255, 128, 0),
    "hardhat": (0, 200, 255),
    "no_hardhat": (0, 0, 255),  # Red for missing hardhat
    "safety_vest": (0, 255, 128),
    "no_safety_vest": (0, 0, 255),  # Red for missing vest
    "safety-vest": (0, 255, 128),
    "safety-helmet": (0, 200, 255),
    "crane": (220, 100, 50),
    "excavator": (240, 140, 20),
    "machinery": (150, 50, 150),
    "truck": (180, 100, 50),
    "vehicle/truck": (180, 100, 50),
    "safety_cone": (0, 165, 255),
    "safety-cone": (0, 165, 255),
    "safet--fire-extinguisher": (0, 0, 255),
    "fire-extinguisher": (0, 0, 255),
    "fire-hose": (50, 50, 220),
    "pallets": (200, 150, 50),
    "pallet": (200, 150, 50),
    "fire": (0, 0, 255),
    "spill": (255, 0, 255),
    "safety-signage": (255, 255, 0),
    "exit-sign": (0, 255, 0),
    "empty-shelf": (128, 128, 128),
    "forklift": (0, 140, 255),
    "obstacle": (0, 69, 255),
}


def draw_bounding_boxes(image_path: str, detections: list, output_path: str):
    """
    Renders bounding boxes and label tags onto the image.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image at {image_path}")

    h, w = img.shape[:2]

    for det in detections:
        bbox = det["bbox"]  # [x1, y1, x2, y2]
        cls = det["class_name"]
        conf = det.get("confidence", 0.0)

        x1, y1, x2, y2 = [int(v) for v in bbox]
        color = CLASS_COLORS.get(cls.lower(), (0, 255, 0))

        # Box
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 3)

        # Label background
        label_text = f"{cls} {int(conf * 100)}%"
        (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(img, (x1, max(0, y1 - 25)), (x1 + tw + 10, y1), color, -1)
        cv2.putText(
            img,
            label_text,
            (x1 + 5, max(15, y1 - 7)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 0, 0),
            2,
            cv2.LINE_AA
        )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cv2.imwrite(output_path, img)
    return output_path


def run_visual_inspection(image_path: str):
    print("=" * 70)
    print("           SITESENSE - VISUAL COMPLIANCE INSPECTOR")
    print("=" * 70)

    if not os.path.exists(image_path):
        print(f"Error: File not found: {image_path}")
        return

    print(f"\n[1] Running Object Detection on: {image_path}")
    detections = detector.detect(image_path)
    print(f"    Total Objects Detected: {len(detections)}")

    for i, d in enumerate(detections, 1):
        print(f"    - #{i}: {d['class_name'].upper()} (Confidence: {d['confidence']:.2f}) at bbox {d['bbox']}")

    # Render image with bounding boxes
    out_dir = Path("output")
    out_dir.mkdir(exist_ok=True)
    out_img_path = str(out_dir / f"annotated_{Path(image_path).name}")
    draw_bounding_boxes(image_path, detections, out_img_path)
    print(f"\n[2] Annotated Image Saved: {out_img_path}")

    # Check compliance rules
    print("\n[3] Checking Compliance against Safety Policies...")
    detected_classes = {d["class_name"].lower() for d in detections}
    
    violations = []
    # PPE Hard Hat Check (SITE-PPE-01)
    if "no_hardhat" in detected_classes or ("person" in detected_classes and "hardhat" not in detected_classes and "safety-helmet" not in detected_classes):
        violations.append({
            "rule": "Mandatory PPE - Hard Hat (SITE-PPE-01)",
            "severity": "critical",
            "desc": "Active personnel observed on site without mandatory approved hard hat."
        })

    # PPE Hi-Vis Vest Check (SITE-PPE-02)
    if "no_safety_vest" in detected_classes or ("person" in detected_classes and "safety_vest" not in detected_classes and "safety-vest" not in detected_classes):
        violations.append({
            "rule": "Mandatory PPE - Hi-Vis Vest (SITE-PPE-02)",
            "severity": "major",
            "desc": "Active personnel observed on site without high-visibility safety vest."
        })

    # Heavy Machinery / Construction Equipment Perimeter (SITE-ZONE-01)
    heavy_equipment = detected_classes.intersection({"crane", "excavator", "machinery", "truck"})
    if heavy_equipment and "person" in detected_classes and "safety_cone" not in detected_classes and "safety-cone" not in detected_classes:
        equip_names = ", ".join([e.title() for e in heavy_equipment])
        violations.append({
            "rule": "Heavy Equipment Perimeter Safety (SITE-ZONE-01)",
            "severity": "critical",
            "desc": f"Heavy equipment ({equip_names}) operating near pedestrian personnel without barricades or safety cones."
        })

    # Forklift Pedestrian Separation (WH-FORK-01)
    if "forklift" in detected_classes and "person" in detected_classes:
        violations.append({
            "rule": "Forklift Pedestrian Separation (WH-FORK-01)",
            "severity": "critical",
            "desc": "Forklift operating in close proximity to unsegregated pedestrian."
        })

    # Liquid Spill Containment (WH-ENV-01)
    if "spill" in detected_classes and "safety-cone" not in detected_classes and "safety_cone" not in detected_classes:
        violations.append({
            "rule": "Liquid Spill Containment (WH-ENV-01)",
            "severity": "critical",
            "desc": "Liquid spill detected without mandatory warning cones."
        })

    # Emergency Walkway Obstacle (WH-CLR-01)
    if "obstacle" in detected_classes:
        violations.append({
            "rule": "Emergency Walkway Egress (WH-CLR-01)",
            "severity": "major",
            "desc": "Obstacle obstructing marked aisle or egress path."
        })

    if violations:
        print(f"\n    [!] FLAGGED {len(violations)} SAFETY VIOLATION(S):")
        for v in violations:
            print(f"    * [{v['severity'].upper()}] {v['rule']}")
            print(f"      Detail: {v['desc']}")
            print(f"      Action: PROPOSED Corrective Maintenance Ticket")
    else:
        print("    [✓] ALL COMPLIANCE CHECKS PASSED. No safety violations flagged.")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        img_arg = sys.argv[1]
    else:
        # Use an example image or create a quick test image
        img_arg = "output/test_sample.jpg"
        if not os.path.exists(img_arg):
            os.makedirs("output", exist_ok=True)
            blank = np.full((600, 800, 3), (220, 220, 220), dtype=np.uint8)
            cv2.putText(blank, "Drop your real site image here", (120, 300), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (50, 50, 50), 2)
            cv2.imwrite(img_arg, blank)

    run_visual_inspection(img_arg)
