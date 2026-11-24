"""
train_strong_aug.py

SiteSense - YOLO11 Custom Object Detection
Experiment 2: Strong Augmentation + Hyperparameter Tuning (Local IDE Version)

Dataset: 16 Classes (data/processed/data.yaml)
Model  : yolo11s.pt

Saves locally in this project:
  1. Complete YOLO training run      -> runs/strong_aug/<RUN_NAME>/
  2. Best & last weights             -> models/<RUN_NAME>_best.pt & _last.pt
  3. Training config & dataset YAML  -> configs/<RUN_NAME>.json & _data.yaml
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

import torch
import yaml
from ultralytics import YOLO


# ============================================================
# 1. PROJECT PATHS (LOCAL)
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_YAML = BASE_DIR / "data" / "processed" / "data.yaml"
MODELS_DIR = BASE_DIR / "models"
RUNS_DIR = BASE_DIR / "runs" / "strong_aug"
CONFIG_DIR = BASE_DIR / "configs"


# ============================================================
# 2. TRAINING SETTINGS
# ============================================================

MODEL_NAME = "yolo11s.pt"
EPOCHS = 125
IMG_SIZE = 640
BATCH_SIZE = 8
WORKERS = 2
PATIENCE = 30
SEED = 42
SAVE_PERIOD = 5
DEVICE = 0 if torch.cuda.is_available() else "cpu"

HYPERPARAMETERS = {
    # Optimizer
    "optimizer": "AdamW",
    "lr0": 0.001,
    "lrf": 0.01,
    "momentum": 0.9,
    "weight_decay": 0.0005,
    "cos_lr": True,

    # Warmup
    "warmup_epochs": 3.0,
    "warmup_momentum": 0.8,

    # Loss weights
    "box": 7.5,
    "cls": 0.5,
    "dfl": 1.5,

    # Color augmentation
    "hsv_h": 0.02,
    "hsv_s": 0.7,
    "hsv_v": 0.4,

    # Geometric augmentation
    "degrees": 5.0,
    "translate": 0.1,
    "scale": 0.5,
    "shear": 2.0,
    "perspective": 0.0005,

    # Flip augmentation
    "fliplr": 0.5,
    "flipud": 0.0,

    # Advanced augmentation
    "mosaic": 1.0,
    "mixup": 0.1,
    "close_mosaic": 15,

    # Multi-scale training
    "multi_scale": 0.1,
}


def validate_dataset(data_yaml: Path) -> dict:
    if not data_yaml.exists():
        raise FileNotFoundError(f"Dataset YAML not found: {data_yaml}")

    with open(data_yaml, "r", encoding="utf-8") as f:
        dataset_config = yaml.safe_load(f)

    if dataset_config.get("nc") != 16:
        raise ValueError(f"Expected 16 classes in data.yaml, got {dataset_config.get('nc')}")

    data_root = Path(dataset_config.get("path", data_yaml.parent))
    if not data_root.is_absolute():
        data_root = data_yaml.parent / data_root

    for split in ["train", "val", "test"]:
        split_path = data_root / dataset_config[split]
        if not split_path.exists():
            raise FileNotFoundError(f"{split} images directory missing: {split_path}")
        print(f"  {split.upper():<5} verified: {split_path}")

    return dataset_config


def main():
    for directory in [MODELS_DIR, RUNS_DIR, CONFIG_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

    run_name = "yolo11s_strong_aug_" + datetime.now().strftime("%Y%m%d_%H%M%S")

    print("\n========== SITESENSE EXPERIMENT 2 (STRONG AUG) ==========")
    print(f"  Experiment : {run_name}")
    print(f"  Model      : {MODEL_NAME}")
    print(f"  Epochs     : {EPOCHS}  |  ImgSz: {IMG_SIZE}  |  Batch: {BATCH_SIZE}")
    print(f"  Device     : {DEVICE}")
    if torch.cuda.is_available():
        gpu_mem = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
        print(f"  GPU        : {torch.cuda.get_device_name(0)} ({gpu_mem:.2f} GB)")
    else:
        print("  GPU        : Not available (running on CPU)")

    # 1. Validate local dataset
    print("\n========== DATASET VALIDATION ==========")
    dataset_config = validate_dataset(DATA_YAML)
    print(f"  Classes ({dataset_config['nc']}): {dataset_config['names']}")

    # 2. Save training config and dataset YAML snapshot
    training_config = {
        "experiment": run_name,
        "model": MODEL_NAME,
        "number_of_classes": dataset_config["nc"],
        "class_names": dataset_config["names"],
        "epochs": EPOCHS,
        "image_size": IMG_SIZE,
        "batch_size": BATCH_SIZE,
        "workers": WORKERS,
        "patience": PATIENCE,
        "seed": SEED,
        "device": str(DEVICE),
        "save_period": SAVE_PERIOD,
        "dataset_yaml": str(DATA_YAML),
        "hyperparameters": HYPERPARAMETERS,
    }

    config_file = CONFIG_DIR / f"{run_name}.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(training_config, f, indent=4)
    shutil.copy2(DATA_YAML, CONFIG_DIR / f"{run_name}_data.yaml")
    print(f"\nSaved training config to: {config_file}")

    # 3. Load pretrained YOLO11s model & train
    print("\n========== STARTING STRONG AUGMENTATION TRAINING ==========")
    model = YOLO(MODEL_NAME)
    results = model.train(
        data=str(DATA_YAML),
        epochs=EPOCHS,
        imgsz=IMG_SIZE,
        batch=BATCH_SIZE,
        workers=WORKERS,
        patience=PATIENCE,
        seed=SEED,
        device=DEVICE,
        amp=torch.cuda.is_available(),
        save=True,
        save_period=SAVE_PERIOD,
        plots=True,
        project=str(RUNS_DIR),
        name=run_name,
        exist_ok=False,
        deterministic=True,
        verbose=True,
        **HYPERPARAMETERS,
    )

    # 4. Copy best.pt & last.pt into models/ without overwriting baseline best.pt
    actual_run_dir = Path(results.save_dir)
    best_model_path = actual_run_dir / "weights" / "best.pt"
    last_model_path = actual_run_dir / "weights" / "last.pt"

    if not best_model_path.exists():
        raise FileNotFoundError(f"best.pt was not generated at {best_model_path}")

    exp_best = MODELS_DIR / f"{run_name}_best.pt"
    exp_last = MODELS_DIR / f"{run_name}_last.pt"
    shutil.copy2(best_model_path, exp_best)
    if last_model_path.exists():
        shutil.copy2(last_model_path, exp_last)

    print("\n========== TRAINING COMPLETED ==========")
    print(f"  Run folder : {actual_run_dir}")
    print(f"  Best model : {exp_best}")
    print(f"  Last model : {exp_last}")
    print("\nNext step -> run evaluation:")
    print("  python training/evaluate_strong_aug.py")


if __name__ == "__main__":
    main()
