import torch
import numpy as np
import cv2
import matplotlib.pyplot as plt
import os
from model_training.model import CrowdCountingModel
from model_training.dataset_loader import get_dataloaders

CHECKPOINT   = "model_training/checkpoints/best_model.pth"
DATASET_PATH = "model_training/dataset/ShanghaiTech"


def evaluate():
    """Evaluates the trained model and shows sample predictions."""

    if not os.path.exists(CHECKPOINT):
        print("❌ No trained model found. Run train.py first.")
        return

    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

    model = CrowdCountingModel().to(device)
    checkpoint = torch.load(CHECKPOINT, map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()

    print(f"✅ Loaded model from epoch {checkpoint['epoch']} (Best MAE: {checkpoint['best_mae']:.2f})")

    _, test_loader = get_dataloaders(DATASET_PATH, part="B", batch_size=1)

    mae_list, mse_list = [], []
    sample_results = []

    with torch.no_grad():
        for i, (images, density_maps, true_counts) in enumerate(test_loader):
            images = images.to(device)
            predictions = model(images)
            pred_count = predictions.sum().item()
            true_count = true_counts[0].item()

            mae_list.append(abs(pred_count - true_count))
            mse_list.append((pred_count - true_count) ** 2)

            if i < 5:
                sample_results.append({
                    "true": true_count,
                    "predicted": round(pred_count, 1),
                    "error": round(abs(pred_count - true_count), 1)
                })

    mae  = np.mean(mae_list)
    rmse = np.sqrt(np.mean(mse_list))

    print(f"\n{'='*40}")
    print(f"  Final Evaluation Results")
    print(f"{'='*40}")
    print(f"  MAE  (Mean Absolute Error) : {mae:.2f}")
    print(f"  RMSE (Root Mean Sq Error)  : {rmse:.2f}")
    print(f"\n  Sample Predictions:")
    print(f"  {'True':>8} | {'Predicted':>10} | {'Error':>8}")
    print(f"  {'-'*35}")
    for r in sample_results:
        print(f"  {r['true']:>8.0f} | {r['predicted']:>10.1f} | {r['error']:>8.1f}")

    print(f"\n✅ Evaluation complete.")
    print(f"   For your dissertation: MAE = {mae:.2f}, RMSE = {rmse:.2f}")


if __name__ == "__main__":
    evaluate()