"""
train_baseline.py
Simple YOLO baseline training script for SiteSense.
"""

import os
import torch
from ultralytics import YOLO

# Training settings
DATA_YAML = os.path.abspath("data/processed/data.yaml")
MODEL_NAME = "yolo11n.pt"
EPOCHS = 50
IMG_SIZE = 640
BATCH_SIZE = 16
WORKERS = 2
PATIENCE = 20
SEED = 42
DEVICE = 0 if torch.cuda.is_available() else "cpu"


def main():
    # 1. Load pretrained YOLO model
    model = YOLO(MODEL_NAME)

    # 2. Train baseline model
    results = model.train(
        data=DATA_YAML,
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        batch=BATCH_SIZE,
        workers=WORKERS,
        patience=PATIENCE,
        seed=SEED,
        device=DEVICE,
        project=os.path.abspath("runs/baseline"),
        name="sitesense_yolo11n",
    )

    # 3. Evaluate best model on the test split
    best_model = YOLO(os.path.join(str(results.save_dir), "weights", "best.pt"))
    metrics = best_model.val(data=DATA_YAML, split="test", device=DEVICE)

    print(f"Precision : {metrics.box.mp:.4f}")
    print(f"Recall    : {metrics.box.mr:.4f}")
    print(f"mAP@50    : {metrics.box.map50:.4f}")
    print(f"mAP@50-95 : {metrics.box.map:.4f}")


if __name__ == "__main__":
    main()
