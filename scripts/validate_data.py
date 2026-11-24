"""
validate_data.py
Validates YOLO annotation files against config/classes.yaml.
Checks:
  1. Exactly 5 values per line: class_id x_center y_center width height
  2. class_id is a valid integer in [0, nc - 1]
  3. Coordinates are floats in [0.0, 1.0] and width/height > 0
  4. Bounding box stays inside image bounds [0.0, 1.0]
"""

import os
import sys
import yaml

CLASSES_YAML = "config/classes.yaml"
LABEL_DIR = "data/raw/labels"


def main():
    label_dir = sys.argv[1] if len(sys.argv) > 1 else LABEL_DIR

    with open(CLASSES_YAML, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    num_classes = cfg["nc"]

    label_files = [f for f in sorted(os.listdir(label_dir)) if f.endswith(".txt")]
    errors = []
    warnings = []
    total_boxes = 0

    for fname in label_files:
        path = os.path.join(label_dir, fname)
        with open(path, "r", encoding="utf-8", errors="ignore") as fp:
            for line_no, raw in enumerate(fp, start=1):
                line = raw.strip()
                if not line:
                    continue

                parts = line.split()
                if len(parts) != 5:
                    errors.append(f"{fname}:{line_no} -> expected 5 values, got {len(parts)}")
                    continue

                try:
                    cid = int(parts[0])
                    x, y, w, h = map(float, parts[1:])
                except ValueError:
                    errors.append(f"{fname}:{line_no} -> non-numeric value: '{line}'")
                    continue

                total_boxes += 1

                if not (0 <= cid < num_classes):
                    errors.append(f"{fname}:{line_no} -> invalid class_id {cid} (expected 0..{num_classes - 1})")

                if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 and 0.0 < w <= 1.0 and 0.0 < h <= 1.0):
                    errors.append(f"{fname}:{line_no} -> out-of-range coords ({x}, {y}, {w}, {h})")

                # Check if box edges extend noticeably outside [0, 1]
                if (x - w / 2) < -0.01 or (x + w / 2) > 1.01 or (y - h / 2) < -0.01 or (y + h / 2) > 1.01:
                    warnings.append(f"{fname}:{line_no} -> box extends outside image bounds")

    print("=== DATA VALIDATION REPORT ===")
    print(f"Folder checked : {label_dir}")
    print(f"Label files    : {len(label_files)}")
    print(f"Total boxes    : {total_boxes}")
    print(f"Errors         : {len(errors)}")
    print(f"Warnings       : {len(warnings)}")

    if errors:
        print("\nFirst 15 errors:")
        for e in errors[:15]:
            print("  [ERROR]", e)
    else:
        print("\nPASS: All label files passed format and range checks.")

    if warnings:
        print("\nFirst 10 warnings:")
        for w in warnings[:10]:
            print("  [WARN]", w)


if __name__ == "__main__":
    main()
