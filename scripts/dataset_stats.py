"""
dataset_stats.py
Prints summary statistics (image counts, background images, and per-class
image & bounding-box counts) for data/raw and data/processed splits.
"""

import os
from collections import Counter
import yaml

CLASSES_YAML = "config/classes.yaml"
RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"


def summarize_folder(name: str, label_dir: str, class_names: dict):
    if not os.path.isdir(label_dir):
        return

    label_files = [f for f in os.listdir(label_dir) if f.endswith(".txt")]
    box_counts = Counter()
    img_counts = Counter()
    empty_count = 0

    for fname in label_files:
        path = os.path.join(label_dir, fname)
        with open(path, "r", encoding="utf-8", errors="ignore") as fp:
            lines = [l.strip() for l in fp if l.strip()]

        if not lines:
            empty_count += 1
            continue

        seen_in_img = set()
        for line in lines:
            cid = int(line.split()[0])
            box_counts[cid] += 1
            seen_in_img.add(cid)

        for cid in seen_in_img:
            img_counts[cid] += 1

    print(f"\n=== STATS: {name} ===")
    print(f"Label files       : {len(label_files)}")
    print(f"Background (empty): {empty_count}")
    print(f"Total boxes       : {sum(box_counts.values())}")
    print(f"\n{'ID':>3}  {'Class Name':<20}  {'Images':>7}  {'Boxes':>7}")
    print("-" * 44)
    for cid in sorted(class_names):
        cname = class_names[cid]
        print(f"{cid:>3}  {cname:<20}  {img_counts[cid]:>7}  {box_counts[cid]:>7}")


def main():
    with open(CLASSES_YAML, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    class_names = cfg["names"]

    summarize_folder("data/raw", os.path.join(RAW_DIR, "labels"), class_names)

    for split in ["train", "val", "test"]:
        split_lbl = os.path.join(PROCESSED_DIR, split, "labels")
        if os.path.isdir(split_lbl):
            summarize_folder(f"data/processed/{split}", split_lbl, class_names)


if __name__ == "__main__":
    main()
