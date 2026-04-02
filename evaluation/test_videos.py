"""
CDMS Video Dataset Evaluation Script
=====================================
Tests the crowd counting system on video footage.
Uses WorldExpo'10 or any crowd video dataset.
Generates CSV results and performance metrics.

Author: Aakif Mustafa
Project: Crowd Disaster Management System (CDMS)
"""

import os
import sys
import csv
import json
import time
import datetime
import numpy as np
import cv2
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.crowd_model import load_model, generate_density_map
from backend.detector import detect_people
from backend.model_ensemble import CrowdEnsemble
from backend.calibration import detect_scene_type

# ── Configuration ──────────────────────────────────────
VIDEO_DIR    = "evaluation/test_videos/mall_dataset/frames"
IS_FRAMES    = True   # Mall dataset uses frames not video files
FRAME_SKIP   = 20     # Analyze every 20th frame (2000 frames total)
MAX_FRAMES   = 100    # Analyze 100 frames
RESULTS_CSV  = "evaluation/results/video_results.csv"
SUMMARY_JSON = "evaluation/results/video_summary.json"
CHART_PATH   = "evaluation/visualizations/video_evaluation.png"
FRAME_SKIP   = 15   # Analyze every 15th frame
MAX_FRAMES   = 100  # Max frames per video
# ───────────────────────────────────────────────────────


def run_video_evaluation():
    print("=" * 60)
    print("  CDMS — Video Dataset Evaluation")
    print(f"  Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Load model
    print("\n📦 Loading models...")
    crowd_model, device = load_model()
    ensemble = CrowdEnsemble(crowd_model, device)
    print("✅ Models loaded\n")

    os.makedirs(VIDEO_DIR,                   exist_ok=True)
    os.makedirs("evaluation/results",        exist_ok=True)
    os.makedirs("evaluation/visualizations", exist_ok=True)

   # Support both video files and frame sequences
    if IS_FRAMES:
        frames_list = sorted([
            f for f in os.listdir(VIDEO_DIR)
            if f.endswith(('.jpg', '.jpeg', '.png'))
        ])
        print(f"📂 Found {len(frames_list)} frames in Mall Dataset\n")
        run_frames_evaluation(frames_list, ensemble, crowd_model, device)
        return

    videos = [f for f in os.listdir(VIDEO_DIR)
            if f.endswith(('.mp4', '.avi', '.mov', '.mkv'))]
    if not videos:
        print(f"⚠️  No videos found in {VIDEO_DIR}")
        print("Please add crowd videos to that folder and run again.")
        print("\nSuggested free sources:")
        print("  - https://www.pexels.com/search/videos/crowd/")
        print("  - https://pixabay.com/videos/search/crowd/")
        print("  - Any crowd video from YouTube (use yt-dlp)")
        return

    print(f"📂 Found {len(videos)} videos\n")

    all_results = []
    video_summaries = []

    # CSV header
    with open(RESULTS_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Video", "Frame_Number", "Timestamp_s",
            "Predicted_Count", "Risk_Level",
            "Detection_Method", "Scene_Type",
            "Processing_Time_s", "FPS_Equivalent"
        ])

    for vid_file in videos:
        vid_path = os.path.join(VIDEO_DIR, vid_file)
        cap      = cv2.VideoCapture(vid_path)

        if not cap.isOpened():
            print(f"❌ Could not open {vid_file}")
            continue

        fps        = cap.get(cv2.CAP_PROP_FPS) or 25
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration   = total_frames / fps

        print(f"\n🎬 Processing: {vid_file}")
        print(f"   Duration: {duration:.1f}s | FPS: {fps:.1f} | Frames: {total_frames}")

        frame_results = []
        frame_num     = 0
        analyzed      = 0

        while cap.isOpened() and analyzed < MAX_FRAMES:
            ret, frame = cap.read()
            if not ret:
                break
            frame_num += 1
            if frame_num % FRAME_SKIP != 0:
                continue

            # Resize for faster processing
            frame = cv2.resize(frame, (640, 360))

            start = time.time()
            try:
                density_map, model_count, confidence = generate_density_map(
                    crowd_model, device, frame
                )
                _, yolo_count, _ = detect_people(frame)
                result = ensemble.predict(
                    frame, yolo_count, model_count, confidence, "auto"
                )
                count  = result["count"]
                method = result["method"]
            except Exception as e:
                continue

            proc_time  = time.time() - start
            fps_equiv  = round(1 / proc_time, 1) if proc_time > 0 else 0
            timestamp  = round(frame_num / fps, 2)
            scene_type, _, _ = detect_scene_type(frame)
            risk = "SAFE" if count < 50 else "WARNING" if count < 100 else "OVERCROWDED"

            row = [
                vid_file, frame_num, timestamp,
                round(count, 1), risk,
                method, scene_type,
                round(proc_time, 3), fps_equiv
            ]
            frame_results.append(row)
            all_results.append(row)
            analyzed += 1

            with open(RESULTS_CSV, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(row)

        cap.release()

        if frame_results:
            counts    = [r[3] for r in frame_results]
            vid_summary = {
                "video":        vid_file,
                "frames_analyzed": len(frame_results),
                "avg_count":    round(np.mean(counts), 1),
                "max_count":    round(max(counts), 1),
                "min_count":    round(min(counts), 1),
                "std_count":    round(np.std(counts), 2),
                "risk_dist": {
                    "SAFE":        sum(1 for r in frame_results if r[4] == "SAFE"),
                    "WARNING":     sum(1 for r in frame_results if r[4] == "WARNING"),
                    "OVERCROWDED": sum(1 for r in frame_results if r[4] == "OVERCROWDED"),
                },
                "avg_fps": round(np.mean([r[8] for r in frame_results]), 1)
            }
            video_summaries.append(vid_summary)
            print(f"   ✅ Analyzed {len(frame_results)} frames")
            print(f"   Avg Count: {vid_summary['avg_count']} | "
                  f"Peak: {vid_summary['max_count']} | "
                  f"Avg FPS: {vid_summary['avg_fps']}")

    # Overall summary
    if all_results:
        all_counts = [r[3] for r in all_results]
        summary = {
            "total_videos":      len(video_summaries),
            "total_frames":      len(all_results),
            "overall_avg_count": round(np.mean(all_counts), 1),
            "overall_max_count": round(max(all_counts), 1),
            "avg_processing_fps": round(np.mean([r[8] for r in all_results]), 1),
            "video_summaries":   video_summaries,
            "timestamp":         datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        with open(SUMMARY_JSON, "w") as f:
            json.dump(summary, f, indent=2)

        print("\n" + "=" * 60)
        print("  VIDEO EVALUATION SUMMARY")
        print("=" * 60)
        print(f"  Videos Tested    : {summary['total_videos']}")
        print(f"  Frames Analyzed  : {summary['total_frames']}")
        print(f"  Avg Crowd Count  : {summary['overall_avg_count']}")
        print(f"  Peak Count       : {summary['overall_max_count']}")
        print(f"  Avg Processing   : {summary['avg_processing_fps']} FPS")
        print(f"\n  Results: {RESULTS_CSV}")
        print("=" * 60)

        generate_video_charts(all_results, video_summaries)
        print(f"📊 Charts saved to: {CHART_PATH}")

    return summary if all_results else None


def generate_video_charts(all_results, summaries):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("CDMS — Video Evaluation Results",
                 fontsize=14, fontweight='bold')

    # 1. Count over time for each video
    ax1 = axes[0, 0]
    colors = plt.cm.tab10(np.linspace(0, 1, len(summaries)))
    for i, summary in enumerate(summaries):
        vid_results = [r for r in all_results if r[0] == summary['video']]
        timestamps  = [r[2] for r in vid_results]
        counts      = [r[3] for r in vid_results]
        ax1.plot(timestamps, counts, label=summary['video'][:20],
                 color=colors[i], linewidth=1.5)
    ax1.set_xlabel("Time (seconds)")
    ax1.set_ylabel("Crowd Count")
    ax1.set_title("Crowd Count Over Time")
    ax1.legend(fontsize=7)
    ax1.grid(True, alpha=0.3)

    # 2. Risk distribution across all frames
    ax2 = axes[0, 1]
    risk_counts = {
        "SAFE":        sum(1 for r in all_results if r[4] == "SAFE"),
        "WARNING":     sum(1 for r in all_results if r[4] == "WARNING"),
        "OVERCROWDED": sum(1 for r in all_results if r[4] == "OVERCROWDED"),
    }
    colors_r = ['#2ecc71', '#f39c12', '#e74c3c']
    ax2.pie(risk_counts.values(), labels=risk_counts.keys(),
            colors=colors_r, autopct='%1.1f%%', startangle=90)
    ax2.set_title("Risk Level Distribution")

    # 3. Processing FPS per video
    ax3 = axes[1, 0]
    vid_names = [s['video'][:15] for s in summaries]
    fps_vals  = [s['avg_fps'] for s in summaries]
    ax3.bar(vid_names, fps_vals, color='steelblue', edgecolor='white')
    ax3.set_xlabel("Video")
    ax3.set_ylabel("Avg FPS")
    ax3.set_title("Processing Speed per Video")
    ax3.grid(True, alpha=0.3, axis='y')
    plt.sca(ax3)
    plt.xticks(rotation=15, ha='right')

    # 4. Count distribution histogram
    ax4 = axes[1, 1]
    all_counts = [r[3] for r in all_results]
    ax4.hist(all_counts, bins=25, color='steelblue',
             edgecolor='white', alpha=0.8)
    ax4.set_xlabel("Crowd Count")
    ax4.set_ylabel("Frequency")
    ax4.set_title("Count Distribution Across All Frames")
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(CHART_PATH, dpi=150, bbox_inches='tight')
    plt.close()

def run_frames_evaluation(frames_list, ensemble, crowd_model, device):
    """Handles frame-based datasets like Mall Dataset."""
    
    os.makedirs("evaluation/results",        exist_ok=True)
    os.makedirs("evaluation/visualizations", exist_ok=True)

    # Write CSV header
    with open(RESULTS_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Frame", "Frame_Number", "Predicted_Count",
            "Risk_Level", "Detection_Method",
            "Scene_Type", "Processing_Time_s", "FPS_Equivalent"
        ])

    results    = []
    selected   = frames_list[::FRAME_SKIP][:MAX_FRAMES]

    print(f"{'Frame':<25} {'Count':>7} {'Risk':<15} {'Method':<25} {'FPS':>6}")
    print("-" * 80)

    for i, frame_file in enumerate(selected):
        frame_path = os.path.join(VIDEO_DIR, frame_file)
        frame      = cv2.imread(frame_path)
        if frame is None:
            continue

        frame = cv2.resize(frame, (640, 360))
        start = time.time()

        try:
            density_map, model_count, confidence = generate_density_map(
                crowd_model, device, frame
            )
            _, yolo_count, _ = detect_people(frame)
            result = ensemble.predict(
                frame, yolo_count, model_count, confidence, "auto"
            )
            count  = result["count"]
            method = result["method"]
        except Exception as e:
            print(f"Error on {frame_file}: {e}")
            continue

        proc_time  = time.time() - start
        fps_equiv  = round(1 / proc_time, 1) if proc_time > 0 else 0
        scene_type, _, _ = detect_scene_type(frame)
        risk = "SAFE" if count < 50 else "WARNING" if count < 100 else "OVERCROWDED"

        row = [
            frame_file, i+1, round(count, 1),
            risk, method, scene_type,
            round(proc_time, 3), fps_equiv
        ]
        results.append(row)

        with open(RESULTS_CSV, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(row)

        if (i+1) % 10 == 0 or i == 0:
            print(f"{frame_file:<25} {round(count):>7} {risk:<15} "
                  f"{method:<25} {fps_equiv:>6}")

    # Summary
    if results:
        counts = [r[2] for r in results]
        summary = {
            "dataset":           "Mall Dataset (CUHK)",
            "total_frames":      len(results),
            "avg_count":         round(np.mean(counts), 1),
            "max_count":         round(max(counts), 1),
            "min_count":         round(min(counts), 1),
            "std_count":         round(np.std(counts), 2),
            "avg_fps":           round(np.mean([r[7] for r in results]), 1),
            "risk_distribution": {
                "SAFE":        sum(1 for r in results if r[3] == "SAFE"),
                "WARNING":     sum(1 for r in results if r[3] == "WARNING"),
                "OVERCROWDED": sum(1 for r in results if r[3] == "OVERCROWDED"),
            },
            "method_distribution": {},
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        # Method distribution
        for r in results:
            m = r[4].split("[")[0].strip()
            summary["method_distribution"][m] = \
                summary["method_distribution"].get(m, 0) + 1

        with open(SUMMARY_JSON, "w") as f:
            json.dump(summary, f, indent=2)

        print("\n" + "=" * 60)
        print("  MALL DATASET EVALUATION SUMMARY")
        print("=" * 60)
        print(f"  Frames Analyzed  : {summary['total_frames']}")
        print(f"  Avg Count        : {summary['avg_count']}")
        print(f"  Peak Count       : {summary['max_count']}")
        print(f"  Min Count        : {summary['min_count']}")
        print(f"  Avg FPS          : {summary['avg_fps']}")
        print(f"\n  Risk Distribution:")
        for k, v in summary['risk_distribution'].items():
            pct = round(v / len(results) * 100)
            print(f"    {k:<15}: {v} frames ({pct}%)")
        print(f"\n  Methods Used:")
        for k, v in summary['method_distribution'].items():
            print(f"    {k:<15}: {v} frames")
        print("=" * 60)

        generate_frames_chart(results, summary)
        print(f"\n📊 Charts: {CHART_PATH}")
        print(f"📋 CSV:    {RESULTS_CSV}")


def generate_frames_chart(results, summary):
    """Generates charts for frame-based evaluation."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(
        f"CDMS — Mall Dataset Evaluation\n"
        f"Avg Count: {summary['avg_count']} | "
        f"Peak: {summary['max_count']} | "
        f"Avg FPS: {summary['avg_fps']}",
        fontsize=13, fontweight='bold'
    )

    counts      = [r[2] for r in results]
    frame_nums  = [r[1] for r in results]

    # 1. Count over frames
    ax1 = axes[0, 0]
    ax1.plot(frame_nums, counts, color='steelblue', linewidth=1.5)
    ax1.axhline(np.mean(counts), color='red', linestyle='--',
                label=f"Avg={summary['avg_count']}")
    ax1.fill_between(frame_nums, counts, alpha=0.2, color='steelblue')
    ax1.set_xlabel("Frame Number")
    ax1.set_ylabel("Crowd Count")
    ax1.set_title("Crowd Count Over Time")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. Risk distribution pie
    ax2 = axes[0, 1]
    rd = summary['risk_distribution']
    non_zero = {k: v for k, v in rd.items() if v > 0}
    color_map = {'SAFE': '#2ecc71', 'WARNING': '#f39c12', 'OVERCROWDED': '#e74c3c'}
    ax2.pie(
        non_zero.values(),
        labels=non_zero.keys(),
        colors=[color_map[k] for k in non_zero],
        autopct='%1.1f%%',
        startangle=90
    )
    ax2.set_title("Risk Level Distribution")

    # 3. Count histogram
    ax3 = axes[1, 0]
    ax3.hist(counts, bins=20, color='steelblue', edgecolor='white', alpha=0.8)
    ax3.axvline(np.mean(counts), color='red', linestyle='--',
                label=f"Mean={summary['avg_count']}")
    ax3.set_xlabel("Crowd Count")
    ax3.set_ylabel("Frequency")
    ax3.set_title("Count Distribution")
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # 4. Processing FPS over frames
    ax4 = axes[1, 1]
    fps_vals = [r[7] for r in results]
    ax4.plot(frame_nums, fps_vals, color='#2ecc71', linewidth=1.5)
    ax4.axhline(np.mean(fps_vals), color='red', linestyle='--',
                label=f"Avg={summary['avg_fps']} FPS")
    ax4.set_xlabel("Frame Number")
    ax4.set_ylabel("FPS")
    ax4.set_title("Processing Speed")
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(CHART_PATH, dpi=150, bbox_inches='tight')
    plt.close()
if __name__ == "__main__":
    run_video_evaluation()