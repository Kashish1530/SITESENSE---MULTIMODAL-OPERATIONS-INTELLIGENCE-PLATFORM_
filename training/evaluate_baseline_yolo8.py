"""
evaluate_baseline_yolo8.py

SiteSense - Evaluation Script for YOLOv8 Baseline
Evaluates trained YOLOv8s models on the local dataset (test or val split)
and saves reports, plots, per-class AP metrics, and experiment summary.

Handles multiple runs in runs/baseline_yolo8/ automatically:
  - Defaults to the latest/best run
  - Allows choosing a specific run via CLI: python training/evaluate_baseline_yolo8.py --run 1
  - Or evaluate all runs for comparison:   python training/evaluate_baseline_yolo8.py --all

Usage:
    python training/evaluate_baseline_yolo8.py
    python training/evaluate_baseline_yolo8.py --run 1
    python training/evaluate_baseline_yolo8.py --all
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import torch
import yaml
from ultralytics import YOLO


# ============================================================
# 1. PROJECT PATHS & EVALUATION SETTINGS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_YAML = BASE_DIR / "data" / "processed" / "data.yaml"
MODELS_DIR = BASE_DIR / "models"
RUNS_DIR = BASE_DIR / "runs" / "baseline_yolo8"
REPORTS_DIR = BASE_DIR / "reports"
CONFIG_DIR = BASE_DIR / "configs"

# Optional manual override: set to a specific Path or str, or leave as None to auto-detect
MODEL_PATH = None

SPLIT = "test"          # "val" or "test"
IMG_SIZE = 640
BATCH_SIZE = 8 if torch.cuda.is_available() else 4
CONF_THRESHOLD = 0.25
IOU_THRESHOLD = 0.60
DEVICE = 0 if torch.cuda.is_available() else "cpu"


# ============================================================
# 2. DISCOVER YOLOv8 RUNS
# ============================================================

def list_yolo8_runs() -> list[tuple[Path, str]]:
    """Scan runs/baseline_yolo8/ and models/ for YOLOv8 runs with best.pt."""
    candidates = []
    if RUNS_DIR.exists():
        for run_dir in sorted(RUNS_DIR.iterdir()):
            if run_dir.is_dir():
                best_pt = run_dir / "weights" / "best.pt"
                if best_pt.exists():
                    candidates.append((best_pt, run_dir.name))

    # Also check models/ if runs/ has no runs or extra weights exist
    if MODELS_DIR.exists():
        for m in sorted(MODELS_DIR.glob("*yolo8*best*.pt")):
            if not any(c[0] == m for c in candidates):
                candidates.append((m, m.stem))
        for m in sorted(MODELS_DIR.glob("*yolov8*best*.pt")):
            if not any(c[0] == m for c in candidates):
                candidates.append((m, m.stem))

    return candidates


def select_model(run_arg: str | None = None) -> list[tuple[Path, str]]:
    """Select which model(s) to evaluate based on settings or CLI arguments."""
    if MODEL_PATH is not None:
        p = Path(MODEL_PATH)
        if not p.is_absolute():
            p = BASE_DIR / p
        run_name = p.parent.parent.name if p.parent.name == "weights" else p.stem.replace("_best", "")
        return [(p, run_name)]

    runs = list_yolo8_runs()
    if not runs:
        raise FileNotFoundError(
            f"No trained YOLOv8 models found in {RUNS_DIR} or {MODELS_DIR}.\n"
            "Train a model first using `python training/train_baseline_yolo8.py`."
        )

    # If --all is passed, return every available run
    if run_arg and run_arg.lower() == "all":
        return runs

    # If --run <num> is passed (e.g. --run 1 or --run 2)
    if run_arg:
        if run_arg.isdigit():
            idx = int(run_arg) - 1
            if 0 <= idx < len(runs):
                return [runs[idx]]
            print(f"[WARN] Invalid run number {run_arg}. Available: 1 to {len(runs)}.")
        else:
            # Match by folder name or keyword
            for pt_path, rname in runs:
                if run_arg.lower() in rname.lower():
                    return [(pt_path, rname)]
            print(f"[WARN] Run matching '{run_arg}' not found.")

    # Default: pick the latest run (most recent modification time)
    latest = max(runs, key=lambda x: x[0].stat().st_mtime)
    return [latest]


def calc_f1(precision: float, recall: float) -> float:
    if (precision + recall) == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


# ============================================================
# 3. EVALUATION FUNCTION FOR A SINGLE MODEL
# ============================================================

def evaluate_single_model(best_model_path: Path, run_name: str, dataset_config: dict, split: str = "test") -> dict:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    eval_project = RUNS_DIR / run_name / "evaluation"

    print("\n" + "=" * 68)
    print(f"  EVALUATING YOLOv8 RUN     : {run_name}")
    print(f"  Model Weights             : {best_model_path}")
    print(f"  Dataset                   : {DATA_YAML}")
    print(f"  Split                     : {split}")
    print(f"  Device                    : {DEVICE}")
    print("=" * 68)

    # 1. Run YOLO validation
    model = YOLO(str(best_model_path))
    metrics = model.val(
        data=str(DATA_YAML),
        split=split,
        imgsz=IMG_SIZE,
        batch=BATCH_SIZE,
        conf=CONF_THRESHOLD,
        iou=IOU_THRESHOLD,
        device=DEVICE,
        plots=True,
        save_json=True,
        project=str(eval_project),
        name=split,
        exist_ok=True,
    )

    # 2. Collect overall metrics
    precision = float(metrics.box.mp)
    recall = float(metrics.box.mr)
    f1 = calc_f1(precision, recall)
    map50 = float(metrics.box.map50)
    map75 = float(metrics.box.map75)
    map50_95 = float(metrics.box.map)

    speed = metrics.speed
    total_ms = speed["preprocess"] + speed["inference"] + speed["postprocess"]
    fps = 1000.0 / total_ms if total_ms > 0 else 0.0

    # 3. Collect per-class metrics
    raw_names = dataset_config["names"]
    class_names = (
        {int(k): v for k, v in raw_names.items()}
        if isinstance(raw_names, dict)
        else {i: name for i, name in enumerate(raw_names)}
    )

    per_class_metrics = []
    for idx, cid in enumerate(metrics.box.ap_class_index):
        cid = int(cid)
        p, r, ap50, ap = metrics.box.class_result(idx)
        cf1 = calc_f1(float(p), float(r))
        per_class_metrics.append({
            "class_id": cid,
            "class_name": class_names.get(cid, str(cid)),
            "precision": round(float(p), 4),
            "recall": round(float(r), 4),
            "f1": round(cf1, 4),
            "AP50": round(float(ap50), 4),
            "AP50_95": round(float(ap), 4),
        })

    evaluation_report = {
        "experiment": run_name,
        "model_path": str(best_model_path),
        "dataset": str(DATA_YAML),
        "split": split,
        "imgsz": IMG_SIZE,
        "conf_threshold": CONF_THRESHOLD,
        "iou_threshold": IOU_THRESHOLD,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "mAP50": round(map50, 4),
        "mAP75": round(map75, 4),
        "mAP50_95": round(map50_95, 4),
        "speed_ms": {
            "preprocess": round(speed["preprocess"], 2),
            "inference": round(speed["inference"], 2),
            "postprocess": round(speed["postprocess"], 2),
            "total": round(total_ms, 2),
            "fps": round(fps, 1),
        },
        "per_class_metrics": per_class_metrics,
    }

    # 4. Save evaluation JSON & TXT reports
    report_json = REPORTS_DIR / f"{run_name}_evaluation.json"
    report_txt = REPORTS_DIR / f"{run_name}_evaluation.txt"
    summary_json = REPORTS_DIR / f"{run_name}_summary.json"

    with open(report_json, "w", encoding="utf-8") as f:
        json.dump(evaluation_report, f, indent=4)

    with open(report_txt, "w", encoding="utf-8") as f:
        f.write("SITESENSE - YOLOv8 BASELINE EVALUATION REPORT\n")
        f.write("=" * 68 + "\n\n")
        f.write(f"Experiment : {run_name}\n")
        f.write(f"Model      : {best_model_path}\n")
        f.write(f"Split      : {split}\n")
        f.write(f"Precision  : {precision:.4f}\n")
        f.write(f"Recall     : {recall:.4f}\n")
        f.write(f"F1-Score   : {f1:.4f}\n")
        f.write(f"mAP@50     : {map50:.4f}\n")
        f.write(f"mAP@75     : {map75:.4f}\n")
        f.write(f"mAP@50-95  : {map50_95:.4f}\n")
        f.write(f"Speed      : {total_ms:.2f} ms/img ({fps:.1f} FPS)\n\n")
        f.write("PER-CLASS METRICS\n")
        f.write("-" * 68 + "\n")
        f.write(f"{'ID':>3}  {'Class Name':<20}  {'Prec':>6}  {'Rec':>6}  {'F1':>6}  {'AP50':>6}  {'AP50-95':>7}\n")
        f.write("-" * 68 + "\n")
        for item in per_class_metrics:
            f.write(
                f"{item['class_id']:>3}  {item['class_name']:<20}  "
                f"{item['precision']:>6.3f}  {item['recall']:>6.3f}  {item['f1']:>6.3f}  "
                f"{item['AP50']:>6.3f}  {item['AP50_95']:>7.3f}\n"
            )

    # 5. Save complete experiment summary
    config_file = CONFIG_DIR / f"{run_name}.json"
    training_config = {}
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            training_config = json.load(f)

    summary = {
        "training_configuration": training_config,
        "evaluation_results": evaluation_report,
        "evaluation_plots_dir": str(metrics.save_dir),
        "best_model": str(best_model_path),
        "evaluation_json": str(report_json),
        "evaluation_txt": str(report_txt),
    }
    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4)

    # 6. Print formatted console table
    print("\n" + "=" * 68)
    print(f"       TEST EVALUATION RESULTS : {run_name}")
    print("=" * 68)
    print(f"  Precision : {precision:.4f}")
    print(f"  Recall    : {recall:.4f}")
    print(f"  F1-Score  : {f1:.4f}")
    print(f"  mAP@50    : {map50:.4f}")
    print(f"  mAP@75    : {map75:.4f}")
    print(f"  mAP@50-95 : {map50_95:.4f}")
    print(f"  Speed     : {total_ms:.2f} ms/img ({fps:.1f} FPS)")
    print("=" * 68)

    print(f"\n{'ID':>3}  {'Class Name':<20}  {'Prec':>6}  {'Rec':>6}  {'F1':>6}  {'AP50':>6}  {'AP50-95':>7}")
    print("-" * 68)
    for item in per_class_metrics:
        print(
            f"{item['class_id']:>3}  {item['class_name']:<20}  "
            f"{item['precision']:>6.3f}  {item['recall']:>6.3f}  {item['f1']:>6.3f}  "
            f"{item['AP50']:>6.3f}  {item['AP50_95']:>7.3f}"
        )

    print("\n========== SAVED OUTPUTS ==========")
    print(f"  Plots / CM   : {metrics.save_dir}")
    print(f"  Report JSON  : {report_json}")
    print(f"  Report TXT   : {report_txt}")
    print(f"  Summary JSON : {summary_json}")

    return evaluation_report


# ============================================================
# 4. MAIN ENTRYPOINT
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="SiteSense YOLOv8 Baseline Evaluation")
    parser.add_argument("--run", type=str, default=None, help="Run number (1, 2) or run folder name, or 'all'")
    parser.add_argument("--all", action="store_true", help="Evaluate all available YOLOv8 runs")
    parser.add_argument("--split", type=str, default=SPLIT, help="Dataset split: 'test' or 'val'")
    args = parser.parse_args()

    split_target = args.split

    if not DATA_YAML.exists():
        raise FileNotFoundError(f"Dataset YAML not found: {DATA_YAML}")

    with open(DATA_YAML, "r", encoding="utf-8") as f:
        dataset_config = yaml.safe_load(f)

    # Show available runs
    all_runs = list_yolo8_runs()
    print("\n========== SITESENSE YOLOv8 RUNS DETECTED ==========")
    for i, (pt_path, rname) in enumerate(all_runs, start=1):
        mtime = datetime.fromtimestamp(pt_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        is_latest = (pt_path == max(all_runs, key=lambda x: x[0].stat().st_mtime)[0])
        tag = " (LATEST / RECOMMENDED)" if is_latest else ""
        print(f"  [{i}] {rname:<40} {mtime}{tag}")

    run_choice = "all" if args.all else args.run

    # If multiple runs exist and no CLI flag was passed, give a quick interactive choice
    if run_choice is None and len(all_runs) > 1:
        latest_idx = len(all_runs)
        for i, (pt, _) in enumerate(all_runs, start=1):
            if pt == max(all_runs, key=lambda x: x[0].stat().st_mtime)[0]:
                latest_idx = i
                break
        try:
            user_input = input(f"\nEnter choice [1-{len(all_runs)}, 'all', or press Enter for latest ({latest_idx})]: ").strip()
            if user_input:
                run_choice = user_input
        except (EOFError, KeyboardInterrupt):
            pass

    selected = select_model(run_choice)

    results_summary = []
    for best_pt, rname in selected:
        report = evaluate_single_model(best_pt, rname, dataset_config, split=split_target)
        results_summary.append(report)

    # If multiple runs evaluated, print side-by-side comparison
    if len(results_summary) > 1:
        print("\n" + "=" * 68)
        print("                 YOLOv8 RUNS COMPARISON")
        print("=" * 68)
        print(f"{'Run Name':<38}  {'Prec':>6}  {'Rec':>6}  {'mAP50':>6}  {'mAP50-95':>8}")
        print("-" * 68)
        for r in results_summary:
            print(
                f"{r['experiment']:<38}  "
                f"{r['precision']:>6.4f}  "
                f"{r['recall']:>6.4f}  "
                f"{r['mAP50']:>6.4f}  "
                f"{r['mAP50_95']:>8.4f}"
            )
        print("=" * 68)


if __name__ == "__main__":
    main()
