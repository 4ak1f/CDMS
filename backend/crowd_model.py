import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
import numpy as np
import cv2
import os
from huggingface_hub import hf_hub_download
from backend.calibration import get_smart_scale
CHECKPOINT_PATH = "model_training/checkpoints/best_model.pth"
REPO_ID = "4AK1F/CDMS-crowd-counting"


class CrowdCountingModel(nn.Module):
    """
    VGG16-based crowd density estimation model.
    Primary analysis engine for CDMS.
    """

    def __init__(self):
        super(CrowdCountingModel, self).__init__()
        vgg = models.vgg16(weights=None)
        features = list(vgg.features.children())
        self.frontend = nn.Sequential(*features[:23])
        self.backend = nn.Sequential(
            nn.Conv2d(512, 256, kernel_size=3, dilation=2, padding=2),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 128, kernel_size=3, dilation=2, padding=2),
            nn.ReLU(inplace=True),
            nn.Conv2d(128, 64, kernel_size=3, dilation=2, padding=2),
            nn.ReLU(inplace=True),
            nn.Conv2d(64, 32, kernel_size=3, dilation=2, padding=2),
            nn.ReLU(inplace=True),
        )
        self.output_layer = nn.Conv2d(32, 1, kernel_size=1)

    def forward(self, x):
        x = self.frontend(x)
        x = self.backend(x)
        x = self.output_layer(x)
        return x


def load_model():
    """
    Loads trained model from local checkpoint.
    If not found locally, downloads from Hugging Face automatically.
    """
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

    if not os.path.exists(CHECKPOINT_PATH):
        print("📥 Model not found locally. Downloading from Hugging Face...")
        os.makedirs("model_training/checkpoints", exist_ok=True)
        downloaded = hf_hub_download(
            repo_id=REPO_ID,
            filename="best_model.pth",
            local_dir="model_training/checkpoints"
        )
        print(f"✅ Model downloaded to {downloaded}")

    model = CrowdCountingModel().to(device)
    checkpoint = torch.load(CHECKPOINT_PATH, map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    print(f"✅ Crowd counting model loaded (Best MAE: {checkpoint['best_mae']:.2f})")
    return model, device


def preprocess_frame(frame):
    """
    Preprocesses frame for better model accuracy.
    Applies contrast enhancement and noise reduction.
    """
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    enhanced = cv2.merge([l, a, b])
    enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
    enhanced = cv2.bilateralFilter(enhanced, 5, 75, 75)
    return enhanced


def generate_density_map(model, device, frame):
    """
    Runs the trained model on a frame with preprocessing.
    Uses multi-scale prediction and dynamic scaling for better accuracy.
    Returns:
        - density map (numpy array)
        - estimated crowd count
        - confidence range (min, max)
    """
    # Preprocess frame
    frame = preprocess_frame(frame)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Calculate edge density ONCE before the loop
    from backend.calibration import get_smart_scale
    scale, scene_type, edge_density, texture_score = get_smart_scale(frame)
# Cap scale — never multiply by more than 3x to avoid wild overcounting
    scale = min(scale, 3.0)
    print(f"🎬 Scene: {scene_type} | Scale: {scale} | Edge: {edge_density:.3f}")

    counts = []
    density_maps = []

    for size in [(512, 512), (640, 640), (384, 384)]:
        t = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize(size),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])
        input_tensor = t(rgb_frame).unsqueeze(0).to(device)
        with torch.no_grad():
            out = model(input_tensor)
        density_np = out.squeeze().cpu().numpy()
        density_np = np.maximum(density_np, 0) * scale
        counts.append(float(density_np.sum()))
        density_maps.append(density_np)

    avg_count = float(np.mean(counts))
    std_count = float(np.std(counts))
    conf_min  = max(0, avg_count - std_count)
    conf_max  = avg_count + std_count

    return density_maps[0], avg_count, (round(conf_min), round(conf_max))


def generate_heatmap(density_map, frame_shape):
    """
    Converts density map into a colour heatmap overlay.
    Red = high density, Green = low density.
    """
    h, w = frame_shape[:2]
    density_resized = cv2.resize(density_map, (w, h))

    if density_resized.max() > 0:
        density_normalized = (density_resized / density_resized.max() * 255).astype(np.uint8)
    else:
        density_normalized = np.zeros((h, w), dtype=np.uint8)

    heatmap = cv2.applyColorMap(density_normalized, cv2.COLORMAP_JET)
    return heatmap


def overlay_heatmap(frame, heatmap, alpha=0.4):
    """
    Blends heatmap onto original frame.
    """
    return cv2.addWeighted(frame, 1 - alpha, heatmap, alpha, 0)


def analyze_zones(density_map, frame_shape, grid_rows=3, grid_cols=3):
    """
    Divides frame into zones and analyzes density per zone.
    Fixed calibration for accurate zone risk assessment.
    """
    h, w = frame_shape[:2]
    density_resized = cv2.resize(density_map, (w, h))
    density_resized = np.maximum(density_resized, 0)

    cell_h = h // grid_rows
    cell_w = w // grid_cols
    zones  = []

    for r in range(grid_rows):
        for c in range(grid_cols):
            cell = density_resized[
                r * cell_h:(r + 1) * cell_h,
                c * cell_w:(c + 1) * cell_w
            ]
            zone_count = max(0.0, float(cell.sum()))
            cell_area    = cell_h * cell_w
            zone_density = (zone_count / cell_area) * 10000

            if zone_density < 1.0:
                risk  = "SAFE"
                color = (0, 255, 0)
            elif zone_density < 3.0:
                risk  = "WARNING"
                color = (0, 165, 255)
            else:
                risk  = "OVERCROWDED"
                color = (0, 0, 255)

            zones.append({
                "zone":    f"Zone {r * grid_cols + c + 1}",
                "row":     r,
                "col":     c,
                "count":   round(zone_count, 1),
                "density": round(zone_density, 3),
                "risk":    risk,
                "color":   color,
                "x1":      c * cell_w,
                "y1":      r * cell_h,
                "x2":      (c + 1) * cell_w,
                "y2":      (r + 1) * cell_h
            })

    return zones


def draw_zones(frame, zones):
    """
    Draws zone grid with risk colours and labels on frame.
    """
    annotated = frame.copy()

    for zone in zones:
        color = zone["color"]
        x1, y1, x2, y2 = zone["x1"], zone["y1"], zone["x2"], zone["y2"]

        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

        overlay = annotated.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
        cv2.addWeighted(overlay, 0.15, annotated, 0.85, 0, annotated)

        label       = f"{zone['zone']}: {zone['risk']}"
        count_label = f"~{zone['count']:.0f} people"
        cv2.putText(annotated, label, (x1 + 5, y1 + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)
        cv2.putText(annotated, count_label, (x1 + 5, y1 + 38),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

    return annotated