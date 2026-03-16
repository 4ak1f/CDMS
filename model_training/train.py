import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import os
import json
import matplotlib.pyplot as plt
from model_training.model import CrowdCountingModel
from model_training.dataset_loader import get_dataloaders

# ── Configuration ──────────────────────────────────────────────
DATASET_PATH = "model_training/dataset/ShanghaiTech"
PART         = "B"          # Part B = moderate crowds, more achievable
BATCH_SIZE   = 4
EPOCHS       = 50
LR           = 1e-5         # Lower LR works better with pretrained weights
IMAGE_SIZE   = (512, 512)
CHECKPOINT   = "model_training/checkpoints/best_model.pth"
RESULTS_FILE = "model_training/outputs/training_results.json"
# ───────────────────────────────────────────────────────────────

def train():
    # Detect best available device (MPS = Apple Silicon GPU)
    if torch.backends.mps.is_available():
        device = torch.device("mps")
        print("✅ Using Apple Silicon GPU (MPS) — training will be fast!")
    elif torch.cuda.is_available():
        device = torch.device("cuda")
        print("✅ Using NVIDIA GPU (CUDA)")
    else:
        device = torch.device("cpu")
        print("⚠️  Using CPU — training will be slower but will work")

    print(f"\n{'='*50}")
    print("  CDMS — Custom Crowd Counting Model Training")
    print(f"{'='*50}\n")

    # Load data
    print("📂 Loading ShanghaiTech dataset...")
    train_loader, test_loader = get_dataloaders(
        DATASET_PATH, part=PART,
        batch_size=BATCH_SIZE,
        image_size=IMAGE_SIZE
    )

    # Initialize model
    model = CrowdCountingModel().to(device)
    total_params = sum(p.numel() for p in model.parameters())
    print(f"🧠 Model initialized — {total_params:,} parameters\n")

    # Loss and optimizer
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)

    best_mae  = float("inf")
    history   = {"train_loss": [], "val_mae": [], "val_mse": []}

    os.makedirs("model_training/checkpoints", exist_ok=True)
    os.makedirs("model_training/outputs",     exist_ok=True)

    for epoch in range(1, EPOCHS + 1):
        # ── Training phase ──
        model.train()
        train_loss = 0.0

        for batch_idx, (images, density_maps, counts) in enumerate(train_loader):
            images      = images.to(device)
            density_maps = density_maps.to(device)

            optimizer.zero_grad()
            predictions = model(images)
            loss = criterion(predictions, density_maps)
            loss.backward()
            optimizer.step()

            train_loss += loss.item()

            if (batch_idx + 1) % 10 == 0:
                print(f"  Epoch {epoch}/{EPOCHS} | Batch {batch_idx+1}/{len(train_loader)} "
                      f"| Loss: {loss.item():.4f}")

        avg_train_loss = train_loss / len(train_loader)

        # ── Validation phase ──
        model.eval()
        mae_list, mse_list = [], []

        with torch.no_grad():
            for images, density_maps, true_counts in test_loader:
                images = images.to(device)
                predictions = model(images)
                pred_count  = predictions.sum().item()
                true_count  = true_counts[0].item()

                mae_list.append(abs(pred_count - true_count))
                mse_list.append((pred_count - true_count) ** 2)

        mae = np.mean(mae_list)
        mse = np.sqrt(np.mean(mse_list))

        history["train_loss"].append(avg_train_loss)
        history["val_mae"].append(mae)
        history["val_mse"].append(mse)

        print(f"\n📊 Epoch {epoch}/{EPOCHS} Summary:")
        print(f"   Train Loss : {avg_train_loss:.4f}")
        print(f"   Val MAE    : {mae:.2f}  (avg error in person count)")
        print(f"   Val RMSE   : {mse:.2f}")

        # Save best model
        if mae < best_mae:
            best_mae = mae
            torch.save({
                "epoch":       epoch,
                "model_state": model.state_dict(),
                "optimizer":   optimizer.state_dict(),
                "best_mae":    best_mae,
            }, CHECKPOINT)
            print(f"   ✅ New best model saved! MAE: {best_mae:.2f}")

        scheduler.step()
        print()

    # ── Save results & plot ──
    with open(RESULTS_FILE, "w") as f:
        json.dump(history, f, indent=2)

    plot_training(history)
    print(f"\n🎉 Training complete! Best MAE: {best_mae:.2f}")
    print(f"   Model saved to: {CHECKPOINT}")


def plot_training(history):
    """Saves a training curve graph to outputs folder."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

    ax1.plot(history["train_loss"], color="#64ffda", linewidth=2)
    ax1.set_title("Training Loss")
    ax1.set_xlabel("Epoch")
    ax1.set_ylabel("MSE Loss")
    ax1.grid(True, alpha=0.3)

    ax2.plot(history["val_mae"], color="#f39c12", linewidth=2, label="MAE")
    ax2.plot(history["val_mse"], color="#e74c3c", linewidth=2, label="RMSE")
    ax2.set_title("Validation Metrics")
    ax2.set_xlabel("Epoch")
    ax2.set_ylabel("Error (people)")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("model_training/outputs/training_curves.png", dpi=150, bbox_inches="tight")
    print("📈 Training curves saved to model_training/outputs/training_curves.png")


if __name__ == "__main__":
    train()