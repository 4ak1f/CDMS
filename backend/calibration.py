import cv2
import numpy as np
import json
import os
from backend.database import get_feedback_stats
# Set to True when running evaluations — disables all scaling
BENCHMARK_MODE = False
# Scene type definitions based on visual characteristics
SCENE_TYPES = {
    "sparse_indoor":   {"edge_range": (0.0,  0.08), "texture_range": (0.0,  0.15)},
    "moderate_indoor": {"edge_range": (0.08, 0.15), "texture_range": (0.0,  0.25)},
    "dense_indoor":    {"edge_range": (0.15, 0.25), "texture_range": (0.15, 0.4)},
    "sparse_outdoor":  {"edge_range": (0.0,  0.1),  "texture_range": (0.1,  0.3)},
    "moderate_outdoor":{"edge_range": (0.1,  0.2),  "texture_range": (0.2,  0.5)},
    "dense_outdoor":   {"edge_range": (0.2,  1.0),  "texture_range": (0.3,  1.0)},
    "mega_outdoor":    {"edge_range": (0.25, 1.0),  "texture_range": (0.4,  1.0)},
}

# Default scale factors per scene type
DEFAULT_SCALES = {
    "sparse_indoor":    0.8,
    "moderate_indoor":  1.0,
    "dense_indoor":     1.5,
    "sparse_outdoor":   0.8,
    "moderate_outdoor": 1.2,
    "dense_outdoor":    1.8,
    "mega_outdoor":     3.0,
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


# ── Scene fingerprinting & parameter memory ──────────────────────────────────

def get_scene_fingerprint(frame):
    """
    Creates a fingerprint for a scene based on visual characteristics.
    Similar scenes get similar fingerprints so we can recall
    the right parameters for each scene type.
    """
    import cv2
    import numpy as np

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Visual characteristics
    brightness    = round(np.mean(gray) / 255.0, 1)
    edges         = cv2.Canny(gray, 50, 150)
    edge_density  = round(np.sum(edges > 0) / (gray.shape[0] * gray.shape[1]), 2)
    texture_var   = round(min(cv2.Laplacian(gray, cv2.CV_64F).var() / 1000.0, 5.0), 1)

    # Bucket into discrete categories for stable fingerprinting
    brightness_bucket = "dark" if brightness < 0.3 else "medium" if brightness < 0.6 else "bright"
    edge_bucket       = "sparse" if edge_density < 0.05 else "moderate" if edge_density < 0.15 else "dense"
    texture_bucket    = "smooth" if texture_var < 0.5 else "normal" if texture_var < 2.0 else "complex"

    return f"{brightness_bucket}_{edge_bucket}_{texture_bucket}"


SCENE_PARAMS_PATH = "logs/scene_params.json"


def load_scene_params():
    """Load all scene-specific learned parameters."""
    try:
        with open(SCENE_PARAMS_PATH) as f:
            return json.load(f)
    except:
        return {}


def save_scene_params(params):
    """Save scene-specific parameters to disk."""
    os.makedirs("logs", exist_ok=True)
    with open(SCENE_PARAMS_PATH, "w") as f:
        json.dump(params, f, indent=2)


def get_params_for_scene(fingerprint):
    """
    Get the best known parameters for this scene.
    If we have seen this scene before and been corrected,
    return those learned parameters.
    If not, return defaults.
    """
    scene_params = load_scene_params()
    if fingerprint in scene_params:
        p = scene_params[fingerprint]
        print(f"🎯 Scene '{fingerprint}' recognised — loading learned params: "
              f"conf={p['conf']:.2f}, iou={p['iou']:.2f}, "
              f"scale={p['scale']:.2f} ({p['corrections']} corrections)")
        return p["conf"], p["iou"], p["scale"]
    return 0.30, 0.30, 1.0  # defaults


def update_params_for_scene(fingerprint, predicted, actual):
    """
    Update stored parameters for this specific scene based on correction.
    This is called when user submits feedback.
    The system learns what parameters work for this exact scene.
    """
    scene_params = load_scene_params()

    if fingerprint not in scene_params:
        scene_params[fingerprint] = {
            "conf":        0.30,
            "iou":         0.30,
            "scale":       1.0,
            "corrections": 0,
            "history":     []
        }

    p     = scene_params[fingerprint]
    ratio = actual / max(predicted, 1)
    # Clamp ratio to prevent wild swings from single bad feedback
    ratio = max(0.1, min(10.0, ratio))

    p["history"].append({"predicted": predicted, "actual": actual, "ratio": ratio})
    if len(p["history"]) > 20:
        p["history"] = p["history"][-20:]
    p["corrections"] += 1

    # Calculate average ratio from recent history for this scene
    recent_ratios = [h["ratio"] for h in p["history"][-3:]]
    avg_ratio     = sum(recent_ratios) / len(recent_ratios)

    # Be more conservative with fewer corrections — require stronger signal
    correction_confidence = min(1.0, p["corrections"] / 5.0)

    if avg_ratio < 0.85 and correction_confidence > 0.3:
        # Consistently overcounting in this scene
        # Raise confidence threshold (reject weak detections)
        p["conf"]  = min(0.70, p["conf"] + 0.04)
        # Lower IOU (merge overlapping boxes more aggressively)
        p["iou"]   = max(0.10, p["iou"]  - 0.04)
        # Reduce density model scale
        p["scale"] = max(0.2, p["scale"] * avg_ratio)
        print(f"📉 Scale reduced to {p['scale']:.2f} for scene '{fingerprint}'")

    elif avg_ratio > 1.15 and correction_confidence > 0.3:
        # Consistently undercounting in this scene
        # Lower confidence (accept more detections)
        p["conf"]  = max(0.10, p["conf"] - 0.03)
        # Raise IOU (allow more separate detections)
        p["iou"]   = min(0.60, p["iou"]  + 0.03)
        # Increase density model scale
        p["scale"] = min(12.0, p["scale"] * avg_ratio)
        print(f"📈 Scale increased to {p['scale']:.2f} for scene '{fingerprint}'")

    elif 0.85 <= avg_ratio <= 1.15:
        # Within 15 percent accuracy - params are working well
        print(f"✅ Scene '{fingerprint}' parameters converged after "
              f"{p['corrections']} corrections")

    scene_params[fingerprint] = p
    save_scene_params(scene_params)

    print(f"💾 Scene '{fingerprint}' params updated: "
          f"conf={p['conf']:.2f}, iou={p['iou']:.2f}, "
          f"scale={p['scale']:.2f}")
    return p


def get_smart_scale(frame):
    """
    Main function — detects scene and returns calibrated scale.
    In benchmark mode, always returns 1.0 (no scaling).
    """
    if BENCHMARK_MODE:
        scene_type, edge_density, texture_score = detect_scene_type(frame)
        return 1.0, scene_type, edge_density, texture_score

    scene_type, edge_density, texture_score = detect_scene_type(frame)
    scale = get_calibrated_scale(scene_type)
    return scale, scene_type, edge_density, texture_score


def get_full_scene_params(frame):
    """
    Single entry point for all scene calibration.
    Returns everything process_frame needs: conf, iou, scale, scene_type, fingerprint.
    Fingerprint-based params (specific) take priority over scene-type params (general).
    Falls back gracefully if no learned data exists.
    """
    if BENCHMARK_MODE:
        scene_type, edge_density, texture_score = detect_scene_type(frame)
        fingerprint = get_scene_fingerprint(frame)
        return {
            "conf":          0.30,
            "iou":           0.30,
            "scale":         1.0,
            "scene_type":    scene_type,
            "fingerprint":   fingerprint,
            "edge_density":  edge_density,
            "texture_score": texture_score,
            "source":        "benchmark"
        }

    scene_type, edge_density, texture_score = detect_scene_type(frame)
    fingerprint = get_scene_fingerprint(frame)

    # Try fingerprint-specific learned params first (most accurate)
    scene_params = load_scene_params()
    if fingerprint in scene_params and scene_params[fingerprint]["corrections"] >= 2:
        p = scene_params[fingerprint]
        print(f"🎯 Using learned params for '{fingerprint}': "
              f"conf={p['conf']:.2f}, iou={p['iou']:.2f}, scale={p['scale']:.2f}")
        return {
            "conf":          p["conf"],
            "iou":           p["iou"],
            "scale":         p["scale"],
            "scene_type":    scene_type,
            "fingerprint":   fingerprint,
            "edge_density":  edge_density,
            "texture_score": texture_score,
            "source":        "learned"
        }

    # Fall back to scene-type calibration from feedback stats
    scale = get_calibrated_scale(scene_type)
    print(f"📊 Using scene-type scale for '{scene_type}': {scale:.2f}")
    return {
        "conf":          0.30,
        "iou":           0.30,
        "scale":         scale,
        "scene_type":    scene_type,
        "fingerprint":   fingerprint,
        "edge_density":  edge_density,
        "texture_score": texture_score,
        "source":        "scene_type"
    }


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
            calibrated    = max(0.2, min(12.0, calibrated))
            return round(calibrated, 2)

    return base_scale


def get_scene_learning_summary():
    """
    Returns a sorted summary of all scenes the system has learned from.
    Most-corrected scenes appear first.
    """
    params  = load_scene_params()
    summary = []

    for fingerprint, p in params.items():
        recent = p["history"][-3:] if p["history"] else []
        if recent:
            avg_recent_ratio = sum(h["ratio"] for h in recent) / len(recent)
        else:
            avg_recent_ratio = 1.0

        if avg_recent_ratio < 0.85:
            status = "overcounting"
        elif avg_recent_ratio > 1.15:
            status = "undercounting"
        else:
            status = "converged"

        # accuracy: how close the most recent predictions are (capped at 100 %)
        accuracy = f"{min(100, round(min(avg_recent_ratio, 1 / avg_recent_ratio) * 100, 1))}%"

        summary.append({
            "scene":       fingerprint,
            "corrections": p["corrections"],
            "scale":       round(p["scale"], 3),
            "conf":        round(p["conf"],  3),
            "iou":         round(p["iou"],   3),
            "accuracy":    accuracy,
            "status":      status,
        })

    return sorted(summary, key=lambda x: x["corrections"], reverse=True)