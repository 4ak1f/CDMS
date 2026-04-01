import cv2
import numpy as np


def estimate_density(person_count, frame_width, frame_height, thresholds=None):
    if thresholds is None:
        thresholds = {
            "warning_threshold": 50,
            "danger_threshold":  100,
            "safe_label":        "SAFE",
            "warning_label":     "WARNING",
            "danger_label":      "OVERCROWDED"
        }

    frame_area    = frame_width * frame_height
    density_score = (person_count / frame_area) * 100000 if frame_area > 0 else 0

    # Use person COUNT for thresholds, not density score
    if person_count < thresholds["warning_threshold"]:
        risk_level = thresholds["safe_label"]
        color      = "green"
        message    = "Crowd density is within safe limits."
    elif person_count < thresholds["danger_threshold"]:
        risk_level = thresholds["warning_label"]
        color      = "orange"
        message    = "Crowd density is getting high. Monitor closely."
    else:
        risk_level = thresholds["danger_label"]
        color      = "red"
        message    = f"ALERT: {thresholds['danger_label'].upper()} — Immediate action required."

    return {
        "person_count":  person_count,
        "density_score": round(density_score, 4),
        "risk_level":    risk_level,
        "color":         color,
        "message":       message,
        "frame_width":   frame_width,
        "frame_height":  frame_height
    }


def estimate_density_from_frame(frame, thresholds=None):
    """
    FOR ULTRA-DENSE CROWDS where individual detection fails.
    Uses image processing to estimate crowd density from visual patterns.
    """
    if thresholds is None:
        thresholds = {
            "warning_threshold": 2.0,
            "danger_threshold":  5.0,
            "safe_label":        "SAFE",
            "warning_label":     "WARNING",
            "danger_label":      "OVERCROWDED"
        }

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    edges        = cv2.Canny(gray, 50, 150)
    edge_density = np.sum(edges > 0) / (h * w)

    laplacian     = cv2.Laplacian(gray, cv2.CV_64F)
    texture_score = laplacian.var()

    grid_rows, grid_cols = 4, 4
    cell_h = h // grid_rows
    cell_w = w // grid_cols
    cell_scores = []

    for r in range(grid_rows):
        for c in range(grid_cols):
            cell       = gray[r*cell_h:(r+1)*cell_h, c*cell_w:(c+1)*cell_w]
            cell_edges = cv2.Canny(cell, 50, 150)
            cell_score = np.sum(cell_edges > 0) / (cell_h * cell_w)
            cell_scores.append(cell_score)

    occupied_cells   = sum(1 for s in cell_scores if s > 0.05)
    estimated_count  = int((edge_density * 1000) + (texture_score * 0.01) + (occupied_cells * 5))
    estimated_count  = max(0, min(estimated_count, 5000))

    if edge_density < 0.08:
        risk_level = thresholds["safe_label"]
        color      = "green"
        message    = "Low crowd density detected."
    elif edge_density < 0.18:
        risk_level = thresholds["warning_label"]
        color      = "orange"
        message    = "Moderate crowd density. Monitor closely."
    else:
        risk_level = thresholds["danger_label"]
        color      = "red"
        message    = f"ALERT: {thresholds['danger_label'].upper()} — Immediate action may be required."

    return {
        "person_count":  estimated_count,
        "density_score": round(edge_density * 100, 4),
        "risk_level":    risk_level,
        "color":         color,
        "message":       message,
        "frame_width":   w,
        "frame_height":  h,
        "method":        "visual_density_estimation"
    }