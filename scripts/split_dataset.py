"""
split_dataset.py
Simple scene-based train / val / test split for YOLO datasets.
- Groups augmented copies (.rf.<hash>, --2-) and nearby video frames into the same scene
  so they never leak across splits.
- Assigns scenes into train (70%), val (15%), test (15%) while balancing rare classes first.
- Copies files into data/processed/{train,val,test}/{images,labels} and writes data/processed/data.yaml.
"""

import hashlib
import os
import re
import random
import shutil
from collections import Counter, defaultdict
import yaml

RAW_IMG_DIR = "data/raw/images"
RAW_LBL_DIR = "data/raw/labels"
OUT_DIR = "data/processed"
CLASSES_YAML = "config/classes.yaml"

SPLIT_RATIOS = {"train": 0.70, "val": 0.15, "test": 0.15}
SEED = 42
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".jfif", ".bmp", ".webp"}


def get_scene_id(filename: str) -> str:
    """Build a simple scene ID from the filename to keep related images together."""
    stem = os.path.splitext(filename)[0]
    # 1. Strip Roboflow augmentation hash and duplicate suffixes
    stem = re.sub(r"\.rf\.[0-9a-fA-F]+$", "", stem)
    stem = re.sub(r"--\d+-?(_jpg|_jpeg|_png)?$", r"\1", stem)

    # 2. Group video frames into short 30-frame windows (e.g., VideoName_mp4-4210 -> VideoName_win140)
    m = re.match(r"^(.+)_mp4-(\d+)", stem, re.IGNORECASE)
    if m:
        video_name, frame_num = m.group(1), int(m.group(2))
        return f"{video_name}_win{frame_num // 30}"

    # 3. Group timestamped video frames into 30-second windows (e.g., 01-frame-0-05-10-00)
    m2 = re.match(r"^(\d+)-frame-(\d+)-(\d+)-(\d+)", stem, re.IGNORECASE)
    if m2:
        vid, hh, mm, ss = m2.group(1), int(m2.group(2)), int(m2.group(3)), int(m2.group(4))
        total_sec = hh * 3600 + mm * 60 + ss
        return f"video{vid}_win{total_sec // 30}"

    return stem


def file_md5(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fp:
        for chunk in iter(lambda: fp.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def read_classes(label_path: str) -> set:
    classes = set()
    with open(label_path, "r", encoding="utf-8", errors="ignore") as fp:
        for line in fp:
            parts = line.strip().split()
            if parts:
                classes.add(int(parts[0]))
    return classes


def main():
    random.seed(SEED)

    # Collect valid image-label pairs
    lbl_stems = {os.path.splitext(f)[0] for f in os.listdir(RAW_LBL_DIR) if f.endswith(".txt")}
    pairs = []
    for f in sorted(os.listdir(RAW_IMG_DIR)):
        stem, ext = os.path.splitext(f)
        if ext.lower() in IMAGE_EXTS and stem in lbl_stems:
            pairs.append((f, stem + ".txt"))

    # Group paired files by scene_id (also merge exact MD5 duplicate images)
    scenes = defaultdict(list)
    scene_classes = defaultdict(Counter)
    total_class_counts = Counter()
    md5_to_scene = {}

    for img_f, lbl_f in pairs:
        img_hash = file_md5(os.path.join(RAW_IMG_DIR, img_f))
        sid = md5_to_scene.get(img_hash, get_scene_id(img_f))
        md5_to_scene[img_hash] = sid

        scenes[sid].append((img_f, lbl_f))
        for cid in read_classes(os.path.join(RAW_LBL_DIR, lbl_f)):
            scene_classes[sid][cid] += 1
            total_class_counts[cid] += 1

    # Order scenes so scenes containing rarer classes are placed first
    scene_ids = list(scenes.keys())
    random.shuffle(scene_ids)
    scene_ids.sort(
        key=lambda sid: min((total_class_counts[c] for c in scene_classes[sid]), default=999999)
    )

    # Assign each scene to the split that needs its rarest class (and total images) the most
    split_names = list(SPLIT_RATIOS.keys())
    split_files = {s: [] for s in split_names}
    split_class_counts = {s: Counter() for s in split_names}
    total_images = len(pairs)

    for sid in scene_ids:
        items = scenes[sid]
        c_counts = scene_classes[sid]

        if c_counts:
            rarest_c = min(c_counts, key=lambda c: total_class_counts[c])
            best_split = min(
                split_names,
                key=lambda s: (
                    split_class_counts[s][rarest_c] / max(total_class_counts[rarest_c] * SPLIT_RATIOS[s], 1e-6),
                    len(split_files[s]) / (total_images * SPLIT_RATIOS[s]),
                ),
            )
        else:
            best_split = min(
                split_names,
                key=lambda s: len(split_files[s]) / (total_images * SPLIT_RATIOS[s]),
            )

        split_files[best_split].extend(items)
        split_class_counts[best_split].update(c_counts)

    # Copy files into data/processed/{train,val,test}/{images,labels}
    for s in split_names:
        split_dir = os.path.join(OUT_DIR, s)
        if os.path.exists(split_dir):
            shutil.rmtree(split_dir)

        img_out = os.path.join(split_dir, "images")
        lbl_out = os.path.join(split_dir, "labels")
        os.makedirs(img_out, exist_ok=True)
        os.makedirs(lbl_out, exist_ok=True)

        for img_f, lbl_f in split_files[s]:
            shutil.copy2(os.path.join(RAW_IMG_DIR, img_f), os.path.join(img_out, img_f))
            shutil.copy2(os.path.join(RAW_LBL_DIR, lbl_f), os.path.join(lbl_out, lbl_f))

    # Write data/processed/data.yaml
    with open(CLASSES_YAML, "r", encoding="utf-8") as f:
        cls_cfg = yaml.safe_load(f)

    processed_yaml = {
        "path": os.path.abspath(OUT_DIR).replace("\\", "/"),
        "train": "train/images",
        "val": "val/images",
        "test": "test/images",
        "nc": cls_cfg["nc"],
        "names": cls_cfg["names"],
    }
    out_yaml_path = os.path.join(OUT_DIR, "data.yaml")
    with open(out_yaml_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(processed_yaml, f, sort_keys=False)

    print("=== SCENE-BASED SPLIT COMPLETE ===")
    print(f"Total paired images : {total_images}")
    print(f"Total scene groups  : {len(scenes)}")
    for s in split_names:
        pct = 100.0 * len(split_files[s]) / total_images
        print(f"  {s:5s}: {len(split_files[s]):4d} images ({pct:5.1f}%)")
    print(f"Saved YAML to       : {out_yaml_path}")


if __name__ == "__main__":
    main()
