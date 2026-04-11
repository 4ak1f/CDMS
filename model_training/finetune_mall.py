"""
Fine-tunes the CDMS crowd-counting model on the Mall dataset.

Strategy:
  - Freeze VGG16 frontend (backbone) — preserve low-level features
  - Train only the backend dilated-conv layers at a very low LR
  - Cosine-annealing LR schedule over 30 epochs
  - Early stopping with 8-epoch patience; restores best checkpoint
    automatically if no improvement was seen

Usage:
    python -m model_training.finetune_mall
"""

import os
import shutil
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim

from model_training.model import CrowdCountingModel
from model_training.dataset_loader import get_finetune_dataloaders, download_mall_dataset

# ── Configuration ──────────────────────────────────────────────────────────────
MALL_PATH      = "model_training/dataset/mall_dataset"
CHECKPOINT_IN  = "model_training/checkpoints/best_model.pth"
CHECKPOINT_OUT = "model_training/checkpoints/best_model.pth"          # overwrite in-place
CHECKPOINT_BAK = "model_training/checkpoints/best_model_pre_mall.pth" # safety backup

EPOCHS     = 30
BATCH_SIZE = 4
LR         = 5e-6
IMAGE_SIZE = (512, 512)
PATIENCE   = 8   # early-stop if no improvement for this many epochs
# ───────────────────────────────────────────────────────────────────────────────


def evaluate(model, loader, device):
    """
    Evaluates the model on a DataLoader.
    Returns (mae, rmse) matching train.py's validation pattern.
    """
    model.eval()
    mae_list, mse_list = [], []

    with torch.no_grad():
        for images, density_maps, true_counts in loader:
            images      = images.to(device)
            predictions = model(images)
            pred_count  = predictions.sum().item()
            true_count  = true_counts[0].item()

            mae_list.append(abs(pred_count - true_count))
            mse_list.append((pred_count - true_count) ** 2)

    mae  = np.mean(mae_list)
    rmse = np.sqrt(np.mean(mse_list))
    return mae, rmse


def finetune():
    # ── Device ─────────────────────────────────────────────────────────────────
    if torch.backends.mps.is_available():
        device = torch.device("mps")
        print("✅ Using Apple Silicon GPU (MPS)")
    elif torch.cuda.is_available():
        device = torch.device("cuda")
        print("✅ Using NVIDIA GPU (CUDA)")
    else:
        device = torch.device("cpu")
        print("⚠️  Using CPU — fine-tuning will be slower")

    print("\n" + "=" * 55)
    print("  CDMS — Mall Dataset Fine-Tuning")
    print("=" * 55 + "\n")

    # ── Dataset ────────────────────────────────────────────────────────────────
    download_mall_dataset(MALL_PATH)
    train_loader, val_loader = get_finetune_dataloaders(
        MALL_PATH, batch_size=BATCH_SIZE, image_size=IMAGE_SIZE
    )

    # ── Model ──────────────────────────────────────────────────────────────────
    model = CrowdCountingModel().to(device)

    if not os.path.exists(CHECKPOINT_IN):
        raise FileNotFoundError(
            f"Base checkpoint not found at {CHECKPOINT_IN}. "
            "Train the base model first with model_training/train.py"
        )

    checkpoint = torch.load(CHECKPOINT_IN, map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["model_state"])
    base_mae = checkpoint.get("best_mae", float("inf"))
    print(f"📦 Base checkpoint loaded — pre-finetune MAE: {base_mae:.2f}\n")

    # Back up the current best model before we touch it
    os.makedirs(os.path.dirname(CHECKPOINT_BAK), exist_ok=True)
    shutil.copy2(CHECKPOINT_IN, CHECKPOINT_BAK)
    print(f"💾 Safety backup saved → {CHECKPOINT_BAK}\n")

    # ── Freeze VGG frontend ────────────────────────────────────────────────────
    for param in model.frontend.parameters():
        param.requires_grad = False

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total     = sum(p.numel() for p in model.parameters())
    print(f"🔒 Frontend frozen — training {trainable:,} / {total:,} parameters\n")

    # ── Optimizer & scheduler ──────────────────────────────────────────────────
    criterion = nn.MSELoss()
    optimizer = optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=LR, weight_decay=1e-4
    )
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS, eta_min=1e-8)

    # ── Training loop ──────────────────────────────────────────────────────────
    best_mae      = float("inf")
    no_improve    = 0
    best_state    = None

    for epoch in range(1, EPOCHS + 1):
        model.train()
        train_loss = 0.0

        for batch_idx, (images, density_maps, counts) in enumerate(train_loader):
            images       = images.to(device)
            density_maps = density_maps.to(device)

            optimizer.zero_grad()
            predictions = model(images)
            loss = criterion(predictions, density_maps)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()

            if (batch_idx + 1) % 10 == 0:
                print(f"  Epoch {epoch}/{EPOCHS} | Batch {batch_idx+1}/"
                      f"{len(train_loader)} | Loss: {loss.item():.4f}")

        avg_loss       = train_loss / len(train_loader)
        val_mae, val_rmse = evaluate(model, val_loader, device)

        print(f"\n📊 Epoch {epoch}/{EPOCHS} Summary:")
        print(f"   Train Loss : {avg_loss:.4f}")
        print(f"   Val MAE    : {val_mae:.2f}  (avg error in person count)")
        print(f"   Val RMSE   : {val_rmse:.2f}")

        scheduler.step()

        if val_mae < best_mae:
            best_mae   = val_mae
            no_improve = 0
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            torch.save({
                "epoch":       epoch,
                "model_state": model.state_dict(),
                "optimizer":   optimizer.state_dict(),
                "best_mae":    best_mae,
            }, CHECKPOINT_OUT)
            print(f"   ✅ New best MAE: {best_mae:.2f} — checkpoint saved")
        else:
            no_improve += 1
            print(f"   ⏳ No improvement for {no_improve}/{PATIENCE} epochs")

        print()

        if no_improve >= PATIENCE:
            print(f"⏹  Early stopping triggered after {epoch} epochs "
                  f"(no improvement for {PATIENCE} epochs)")
            break

    # ── Outcome ────────────────────────────────────────────────────────────────
    if best_mae >= base_mae:
        print(f"\n⚠️  Fine-tuning did not improve MAE "
              f"({best_mae:.2f} vs base {base_mae:.2f})")
        print(f"   Restoring pre-fine-tune checkpoint from {CHECKPOINT_BAK}")
        shutil.copy2(CHECKPOINT_BAK, CHECKPOINT_OUT)
        print("   ✅ Original checkpoint restored — no harm done")
    else:
        improvement = base_mae - best_mae
        print(f"\n🎉 Fine-tuning complete!")
        print(f"   Base MAE : {base_mae:.2f}")
        print(f"   Best MAE : {best_mae:.2f}  (↓ {improvement:.2f} improvement)")
        print(f"   Model saved → {CHECKPOINT_OUT}")


if __name__ == "__main__":
    finetune()
