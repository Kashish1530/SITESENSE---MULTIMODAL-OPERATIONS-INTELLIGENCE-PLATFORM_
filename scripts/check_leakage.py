"""
check_leakage.py
Checks train / val / test splits under data/processed for data leakage:
  1. Exact filename overlap
  2. Scene / base-name overlap (e.g., same image with different .rf.<hash> augmentations)
  3. Exact image content overlap (MD5 file hash)
"""

import hashlib
import os
import re
from itertools import combinations

PROCESSED_DIR = "data/processed"
SPLITS = ["train", "val", "test"]
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".jfif", ".bmp", ".webp"}


def get_base_name(filename: str) -> str:
    stem = os.path.splitext(filename)[0]
    stem = re.sub(r"\.rf\.[0-9a-fA-F]+$", "", stem)
    stem = re.sub(r"--\d+-?(_jpg|_jpeg|_png)?$", r"\1", stem)
    return stem


def file_md5(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fp:
        for chunk in iter(lambda: fp.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    filenames = {}
    base_names = {}
    hashes = {}

    for split in SPLITS:
        img_dir = os.path.join(PROCESSED_DIR, split, "images")
        if not os.path.isdir(img_dir):
            print(f"[ERROR] Missing directory: {img_dir}. Run split_dataset.py first.")
            return

        files = [
            f for f in os.listdir(img_dir)
            if os.path.splitext(f)[1].lower() in IMAGE_EXTS
        ]
        filenames[split] = set(files)
        base_names[split] = {get_base_name(f) for f in files}
        hashes[split] = {file_md5(os.path.join(img_dir, f)) for f in files}

    print("=== SPLIT LEAKAGE CHECK ===")
    total_leaks = 0

    for a, b in combinations(SPLITS, 2):
        fname_leak = filenames[a] & filenames[b]
        base_leak = base_names[a] & base_names[b]
        hash_leak = hashes[a] & hashes[b]

        total_leaks += len(fname_leak) + len(base_leak) + len(hash_leak)
        print(f"\n{a} vs {b}:")
        print(f"  Exact filename overlap : {len(fname_leak)}")
        print(f"  Base-scene overlap     : {len(base_leak)}")
        print(f"  MD5 content overlap    : {len(hash_leak)}")

        if base_leak:
            print("  Sample leaked scenes   :", sorted(base_leak)[:5])

    if total_leaks == 0:
        print("\nPASS: No leakage detected across train / val / test splits.")
    else:
        print(f"\nFAIL: Found {total_leaks} total overlap(s) across splits.")


if __name__ == "__main__":
    main()
