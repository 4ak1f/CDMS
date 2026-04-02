# CDMS Model Evaluation

## Overview
This directory contains evaluation scripts and results for the 
Crowd Disaster Management System (CDMS) crowd counting model.

## Test 1 — Image Dataset Evaluation

**Dataset:** ShanghaiTech Part B Test Set  
**Images:** 316 crowd images  
**Metric:** MAE, RMSE, Risk Classification Accuracy

### Run
```bash
cd /path/to/CDMS
python3 -m evaluation.test_images
```

### Results
| Metric | Value |
|--------|-------|
| MAE    | 19.64 |
| RMSE   | 32.20 |

## Test 2 — Video Dataset Evaluation

**Dataset:** Free crowd videos (Pexels/Pixabay)  
**Metric:** Frame-by-frame count, FPS, Risk Distribution

### Setup
Add crowd videos to `evaluation/test_videos/` folder.

Free sources:
- https://www.pexels.com/search/videos/crowd/
- https://pixabay.com/videos/search/crowd/

### Run
```bash
python3 -m evaluation.test_videos
```

## Generate PDF Report
```bash
python3 -m evaluation.generate_report
```

## Results Structure
```
evaluation/
├── results/
│   ├── image_results.csv      # Per-image predictions
│   ├── image_summary.json     # Aggregated image metrics
│   ├── video_results.csv      # Per-frame predictions  
│   ├── video_summary.json     # Aggregated video metrics
│   └── CDMS_Evaluation_Report.pdf
└── visualizations/
    ├── image_evaluation.png   # Charts for image test
    └── video_evaluation.png   # Charts for video test
```

## Model Architecture
- **Primary:** Custom VGG16 + Dilated CNN (MAE: 19.64)
- **Fallback:** YOLOv8n-seg (sparse scenes)
- **Dense:** CSRNet-style patch analysis
- **Ensemble:** Automatic scene-aware selection