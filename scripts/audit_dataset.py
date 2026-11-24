"""
audit_dataset.py
Simple dataset audit for YOLO images and labels in data/raw.
Checks:
  1. Missing labels (images without a .txt file)
  2. Orphan labels (.txt files without a matching image)
  3. Empty label files (background images)
  4. Corrupted / unreadable images
  5. Repeated base names (e.g., Roboflow .rf.<hash> augmented copies)
"""

import os
import re
from collections import Counter
from PIL import Image

IMAGE_DIR = "data/raw/images"
LABEL_DIR = "data/raw/labels"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".jfif", ".bmp", ".webp"}


def get_base_name(filename: str) -> str:
    """Remove file extension and Roboflow '.rf.<hash>' suffix."""
    stem = os.path.splitext(filename)[0]
    return re.sub(r"\.rf\.[0-9a-fA-F]+$", "", stem)


def main():
    images = [
        f for f in sorted(os.listdir(IMAGE_DIR))
        if os.path.splitext(f)[1].lower() in IMAGE_EXTS
    ]
    labels = [f for f in sorted(os.listdir(LABEL_DIR)) if f.endswith(".txt")]

    img_stems = {os.path.splitext(f)[0]: f for f in images}
    lbl_stems = {os.path.splitext(f)[0]: f for f in labels}

    missing_labels = sorted(set(img_stems) - set(lbl_stems))
    orphan_labels = sorted(set(lbl_stems) - set(img_stems))

    # Check empty label files
    empty_labels = []
    for f in labels:
        path = os.path.join(LABEL_DIR, f)
        with open(path, "r", encoding="utf-8", errors="ignore") as fp:
            if not fp.read().strip():
                empty_labels.append(f)

    # Check corrupted images
    corrupt_images = []
    for f in images:
        path = os.path.join(IMAGE_DIR, f)
        try:
            with Image.open(path) as im:
                im.verify()
        except Exception:
            corrupt_images.append(f)

    # Check repeated base names (augmented copies)
    base_counts = Counter(get_base_name(f) for f in images)
    repeated_bases = {k: v for k, v in base_counts.items() if v > 1}

    print("=== DATASET AUDIT REPORT ===")
    print(f"Total images            : {len(images)}")
    print(f"Total label files       : {len(labels)}")
    print(f"Valid image-label pairs : {len(set(img_stems) & set(lbl_stems))}")
    print(f"Images without labels   : {len(missing_labels)}")
    print(f"Labels without images   : {len(orphan_labels)}")
    print(f"Empty label files       : {len(empty_labels)}")
    print(f"Corrupted images        : {len(corrupt_images)}")
    print(f"Repeated base scenes    : {len(repeated_bases)} ({sum(repeated_bases.values())} images)")

    if missing_labels:
        print("\nImages missing labels (first 10):", missing_labels[:10])
    if orphan_labels:
        print("\nOrphan labels (first 10):", orphan_labels[:10])
    if corrupt_images:
        print("\nCorrupted images (first 10):", corrupt_images[:10])


if __name__ == "__main__":
    main()
