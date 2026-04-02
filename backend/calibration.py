import cv2
import numpy as np
from backend.database import get_feedback_stats

# Scene type definitions based on visual characteristics
SCENE_TYPES = {
    "sparse_indoor":   {"edge_range": (0.0,  0.08), "texture_range": (0.0,  0.15)},
    "moderate_indoor": {"edge_range": (0.08, 0.15), "texture_range": (0.0,  0.25)},
    "dense_indoor":    {"edge_range": (0.15, 0.25), "texture_range": (0.15, 0.4)},
    "sparse_outdoor":  {"edge_range": (0.0,  0.1),  "texture_range": (0.1,  0.3)},
    "moderate_outdoor":{"edge_range": (0.1,  0.2),  "texture_range": (0.2,  0.5)},
    "dense_outdoor":   {"edge_range": (0.2,  1.0),  "texture_range": (0.3,  1.0)},
}

# Default scale factors per scene type
DEFAULT_SCALES = {
    "sparse_indoor":    1.0,
    "moderate_indoor":  1.0,
    "dense_indoor":     1.5,
    "sparse_outdoor":   1.0,
    "moderate_outdoor": 1.8,
    "dense_outdoor":    4.0,
}


def detect_scene_type(frame):
    """
    Analyzes a frame and detects the scene type.
    Returns scene_type string.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Edge density
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.sum(edges > 0) / (gray.shape[0] * gray.shape[1])

    # Texture variance
    texture_variance = cv2.Laplacian(gray, cv2.CV_64F).var()
    texture_score = min(texture_variance / 2000.0, 1.0)

    # Brightness (outdoor vs indoor)
    brightness = np.mean(gray) / 255.0

    # Match to scene type
    best_match = "moderate_indoor"
    best_score = float('inf')

    for scene_type, ranges in SCENE_TYPES.items():
        e_min, e_max = ranges["edge_range"]
        t_min, t_max = ranges["texture_range"]

        e_dist = max(0, e_min - edge_density) + max(0, edge_density - e_max)
        t_dist = max(0, t_min - texture_score) + max(0, texture_score - t_max)
        score = e_dist + t_dist

        if score < best_score:
            best_score = score
            best_match = scene_type

    return best_match, edge_density, texture_score


def get_calibrated_scale(scene_type):
    """
    Gets the best scale factor for a scene type.
    Uses feedback data if available, otherwise uses defaults.
    """
    feedback_stats = get_feedback_stats()

    if scene_type in feedback_stats:
        stats = feedback_stats[scene_type]
        # Only use feedback if we have enough samples
        if stats["sample_count"] >= 3:
            # Correction ratio tells us how much we over/undercount
            correction = stats["avg_correction_ratio"]
            base_scale = DEFAULT_SCALES.get(scene_type, 1.0)
            # Apply correction to base scale
            calibrated = base_scale * correction
            print(f"📊 Using calibrated scale for {scene_type}: {calibrated:.2f} "
                  f"(from {stats['sample_count']} feedback samples)")
            return round(calibrated, 2)

    return DEFAULT_SCALES.get(scene_type, 1.0)


def get_smart_scale(frame):
    """
    Main function — detects scene and returns calibrated scale.
    """
    scene_type, edge_density, texture_score = detect_scene_type(frame)
    scale = get_calibrated_scale(scene_type)
    return scale, scene_type, edge_density, texture_score

def get_calibrated_scale(scene_type, yolo_count=0):
    """
    Gets calibrated scale. If YOLO count available, uses it
    to further validate the scale makes sense.
    """
    feedback_stats = get_feedback_stats()

    base_scale = DEFAULT_SCALES.get(scene_type, 1.0)

    if scene_type in feedback_stats:
        stats = feedback_stats[scene_type]
        if stats["sample_count"] >= 1:
            correction    = stats["avg_correction_ratio"]
            calibrated    = base_scale * correction
            # Never go below 0.5 or above 5.0
            calibrated    = max(0.5, min(5.0, calibrated))
            return round(calibrated, 2)

    return base_scale