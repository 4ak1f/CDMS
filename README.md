# Crowd Disaster Management System (CDMS)

An AI-powered crowd monitoring system that detects dangerous crowd density levels in real-time using Computer Vision and Deep Learning.

## Features
- Real-time person detection using YOLOv8
- Custom-trained crowd density estimation model
- Risk level classification (Safe / Warning / Danger)
- Automatic alert generation and logging
- Live monitoring dashboard

## Tech Stack
- Python, FastAPI, OpenCV
- YOLOv8 (Ultralytics)
- PyTorch (custom model)
- SQLite, HTML/CSS/JS

## Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

## Dataset
Trained on the ShanghaiTech Crowd Counting Dataset.
