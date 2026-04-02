"""
CDMS Image Dataset Evaluation Script
=====================================
Tests the crowd counting model on ShanghaiTech Part B test set.
Generates CSV results and performance metrics.

Author: Aakif Mustafa
Project: Crowd Disaster Management System (CDMS)
Dataset: ShanghaiTech Part B (316 test images)
"""

import os
import sys
import csv
import json
import time
import datetime
import numpy as np
import cv2
import scipy.io as sio
import matplotlib.pyplot as plt

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.crowd_model import load_model, generate_density_map
from backend.detector import detect_people
from backend.model_ensemble import CrowdEnsemble
from backend.density import estimate_density
from backend.calibration import get_smart_scale

# ── Configuration ──────────────────────────────────────
DATASET_PATH  = "model_training/dataset/ShanghaiTech/part_B/test_data"
RESULTS_CSV   = "evaluation/results/image_results.csv"
SUMMARY_JSON  = "evaluation/results/image_summary.json"
CHART_PATH    = "evaluation/visualizations/image_evaluation.png"
MAX_IMAGES    = 316  # Full test set
# ───────────────────────────────────────────────────────


def load_ground_truth(gt_path):
    """Loads ground truth count from .mat file."""
    try:
        gt = sio.loadmat(gt_path)
        points = gt["image_info"][0][0][0][0][0]
        return len(points)
    except Exception as e:
        print(f"Warning: Could not load GT from {gt_path}: {e}")
        return None


def classify_risk(count, warning=50, danger=100):
    """Classifies risk based on person count."""
    if count < warning:
        return "SAFE"
    elif count < danger:
        return "WARNING"
    return "OVERCROWDED"


def run_evaluation():
    print("=" * 60)
    print("  CDMS — Image Dataset Evaluation")
    print("  Dataset: ShanghaiTech Part B Test Set")
    print(f"  Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Load model
    print("\n📦 Loading models...")
    crowd_model, device = load_model()
    ensemble = CrowdEnsemble(crowd_model, device)
    print("✅ Models loaded\n")

    # Setup paths
    img_dir = os.path.join(DATASET_PATH, "images")
    gt_dir  = os.path.join(DATASET_PATH, "ground-truth")

    if not os.path.exists(img_dir):
        print(f"❌ Dataset not found at {img_dir}")
        return

    images = sorted([f for f in os.listdir(img_dir) if f.endswith(".jpg")])[:MAX_IMAGES]
    print(f"📂 Found {len(images)} test images\n")

    # Results storage
    results     = []
    mae_list    = []
    mse_list    = []
    errors      = []

    os.makedirs("evaluation/results",        exist_ok=True)
    os.makedirs("evaluation/visualizations", exist_ok=True)

    # Write CSV header
    with open(RESULTS_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Image", "Ground_Truth", "Predicted",
            "Absolute_Error", "Relative_Error_%",
            "Risk_Level", "Detection_Method",
            "Scene_Type", "Processing_Time_s"
        ])

    print(f"{'Image':<25} {'GT':>6} {'Pred':>6} {'Error':>7} {'Method':<20}")
    print("-" * 70)

    for i, img_file in enumerate(images):
        img_path = os.path.join(img_dir, img_file)
        img_id   = os.path.splitext(img_file)[0]
        gt_path  = os.path.join(gt_dir, f"GT_{img_id}.mat")

        # Load image
        frame = cv2.imread(img_path)
        if frame is None:
            continue

        h, w = frame.shape[:2]

        # Get ground truth
        gt_count = load_ground_truth(gt_path)
        if gt_count is None:
            continue

        # Run inference
        start_time = time.time()
        try:
            density_map, model_count, confidence = generate_density_map(
                crowd_model, device, frame
            )
            _, yolo_count, _ = detect_people(frame)
            ensemble_result  = ensemble.predict(
                frame, yolo_count, model_count, confidence, "auto"
            )
            final_count = ensemble_result["count"]
            method      = ensemble_result["method"]
        except Exception as e:
            print(f"Error processing {img_file}: {e}")
            continue

        proc_time = time.time() - start_time

        # Metrics
        abs_error = abs(final_count - gt_count)
        rel_error = (abs_error / max(gt_count, 1)) * 100
        risk      = classify_risk(int(final_count))
        scene, _, _ = get_smart_scale(frame)[1:] if hasattr(get_smart_scale(frame), '__iter__') else ("unknown", 0, 0)

        mae_list.append(abs_error)
        mse_list.append((final_count - gt_count) ** 2)

        # Get scene type
        from backend.calibration import detect_scene_type
        scene_type, _, _ = detect_scene_type(frame)

        row = [
            img_file,
            gt_count,
            round(final_count, 1),
            round(abs_error, 1),
            round(rel_error, 1),
            risk,
            method,
            scene_type,
            round(proc_time, 3)
        ]
        results.append(row)
        errors.append(abs_error)

        # Append to CSV
        with open(RESULTS_CSV, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(row)

        # Progress
        if (i + 1) % 10 == 0 or i == 0:
            current_mae = np.mean(mae_list)
            print(f"{img_file:<25} {gt_count:>6} {round(final_count):>6} "
                  f"{round(abs_error):>7} {method:<20} | MAE so far: {current_mae:.2f}")

    # Final metrics
    mae  = np.mean(mae_list)
    rmse = np.sqrt(np.mean(mse_list))
    mean_rel_error = np.mean([r[4] for r in results])

    # Risk distribution
    risk_dist = {"SAFE": 0, "WARNING": 0, "OVERCROWDED": 0}
    for r in results:
        risk_dist[r[5]] = risk_dist.get(r[5], 0) + 1

    # Method distribution
    method_dist = {}
    for r in results:
        m = r[6].split("[")[0].strip()
        method_dist[m] = method_dist.get(m, 0) + 1

    summary = {
        "dataset":          "ShanghaiTech Part B Test Set",
        "total_images":     len(results),
        "mae":              round(mae, 2),
        "rmse":             round(rmse, 2),
        "mean_rel_error":   round(mean_rel_error, 1),
        "min_error":        round(min(mae_list), 2),
        "max_error":        round(max(mae_list), 2),
        "risk_distribution": risk_dist,
        "method_distribution": method_dist,
        "timestamp":        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    with open(SUMMARY_JSON, "w") as f:
        json.dump(summary, f, indent=2)

    # Print summary
    print("\n" + "=" * 60)
    print("  EVALUATION RESULTS")
    print("=" * 60)
    print(f"  Total Images Tested : {len(results)}")
    print(f"  MAE                 : {mae:.2f}")
    print(f"  RMSE                : {rmse:.2f}")
    print(f"  Mean Relative Error : {mean_rel_error:.1f}%")
    print(f"  Min Error           : {min(mae_list):.2f}")
    print(f"  Max Error           : {max(mae_list):.2f}")
    print(f"\n  Risk Distribution:")
    for k, v in risk_dist.items():
        print(f"    {k:<15}: {v} images ({round(v/len(results)*100)}%)")
    print(f"\n  Detection Methods Used:")
    for k, v in method_dist.items():
        print(f"    {k:<15}: {v} images")
    print(f"\n  Results saved to: {RESULTS_CSV}")
    print("=" * 60)

    # Generate charts
    generate_charts(results, mae_list, summary)
    print(f"📊 Charts saved to: {CHART_PATH}")

    return summary


def generate_charts(results, errors, summary):
    """Generates evaluation visualization charts."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("CDMS — Image Evaluation Results\nShanghaiTech Part B Test Set",
                 fontsize=14, fontweight='bold')

    # 1. Predicted vs Ground Truth scatter
    ax1 = axes[0, 0]
    gt_vals   = [r[1] for r in results]
    pred_vals = [r[2] for r in results]
    ax1.scatter(gt_vals, pred_vals, alpha=0.5, color='steelblue', s=20)
    max_val = max(max(gt_vals), max(pred_vals))
    ax1.plot([0, max_val], [0, max_val], 'r--', label='Perfect prediction')
    ax1.set_xlabel("Ground Truth Count")
    ax1.set_ylabel("Predicted Count")
    ax1.set_title(f"Predicted vs Ground Truth\nMAE={summary['mae']:.2f}")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. Error distribution histogram
    ax2 = axes[0, 1]
    ax2.hist(errors, bins=30, color='steelblue', edgecolor='white', alpha=0.8)
    ax2.axvline(summary['mae'], color='red', linestyle='--',
                label=f"MAE={summary['mae']:.2f}")
    ax2.set_xlabel("Absolute Error")
    ax2.set_ylabel("Frequency")
    ax2.set_title("Error Distribution")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 3. Risk distribution pie
    ax3 = axes[1, 0]
    risk_data   = summary['risk_distribution']
    colors_risk = ['#2ecc71', '#f39c12', '#e74c3c']
    ax3.pie(
        risk_data.values(),
        labels=risk_data.keys(),
        colors=colors_risk,
        autopct='%1.1f%%',
        startangle=90
    )
    ax3.set_title("Risk Level Distribution")

    # 4. Method distribution bar
    ax4 = axes[1, 1]
    methods = list(summary['method_distribution'].keys())
    counts  = list(summary['method_distribution'].values())
    bars = ax4.bar(methods, counts, color='steelblue', edgecolor='white')
    ax4.set_xlabel("Detection Method")
    ax4.set_ylabel("Number of Images")
    ax4.set_title("Detection Method Usage")
    for bar, count in zip(bars, counts):
        ax4.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.5,
                 str(count), ha='center', va='bottom', fontsize=9)
    ax4.grid(True, alpha=0.3, axis='y')
    plt.xticks(rotation=15, ha='right')

    plt.tight_layout()
    plt.savefig(CHART_PATH, dpi=150, bbox_inches='tight')
    plt.close()


if __name__ == "__main__":
    run_evaluation()