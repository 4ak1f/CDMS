FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project
COPY . .

# Create necessary directories
RUN mkdir -p logs/reports uploads models model_training/checkpoints

# Download model from Hugging Face on build
RUN python3 -c "
from huggingface_hub import hf_hub_download
import os
os.makedirs('model_training/checkpoints', exist_ok=True)
hf_hub_download(
    repo_id='4AK1F/CDMS-crowd-counting',
    filename='best_model.pth',
    local_dir='model_training/checkpoints'
)
print('Model downloaded successfully')
"

# Expose port
EXPOSE 7860

# Start server on Hugging Face port
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]