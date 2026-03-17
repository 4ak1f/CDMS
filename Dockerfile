FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p logs/reports uploads models model_training/checkpoints

RUN python3 -c "from huggingface_hub import hf_hub_download; import os; os.makedirs('model_training/checkpoints', exist_ok=True); hf_hub_download(repo_id='4AK1F/CDMS-crowd-counting', filename='best_model.pth', local_dir='model_training/checkpoints')"

EXPOSE 7860

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]