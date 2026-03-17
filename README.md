---
title: CDMS - Crowd Disaster Management System
emoji: 🚨
colorFrom: red
colorTo: blue
sdk: docker
pinned: true
---
# Crowd Disaster Management System (CDMS)

An AI-powered crowd monitoring system that detects dangerous crowd density levels in real-time using Computer Vision and Deep Learning.

## 🏆 Model Performance
- **MAE: 13.77** on ShanghaiTech Part B dataset
- **RMSE: 23.48**
- Trained custom VGG16-based crowd counting model

## ✨ Features
- Real-time person detection using YOLOv8
- Custom-trained crowd density estimation model (MAE: 13.77)
- Risk level classification (Safe / Warning / Danger)
- Automatic alert generation and logging
- Live monitoring dashboard

## 🧠 Pretrained Model
Download the trained model from Hugging Face:
👉 https://huggingface.co/4AK1F/CDMS-crowd-counting

## 🛠️ Tech Stack
- Python, FastAPI, OpenCV
- PyTorch (custom VGG16-based model)
- YOLOv8 (Ultralytics)
- SQLite, HTML/CSS/JS

## 🚀 Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Download model from Hugging Face and place in:
```
model_training/checkpoints/best_model.pth
```

Run the system:
```bash
uvicorn backend.main:app --reload
```

## 📊 Dataset
Trained on the ShanghaiTech Crowd Counting Dataset (Part B).

## 👤 Author
Aakif Mustafa — Final Year CS Project