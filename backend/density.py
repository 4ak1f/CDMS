import cv2
import numpy as np

def estimate_density(person_count, frame_width, frame_height):
    """
    Estimates crowd density based on people count vs frame area.
    Returns density score and risk level.
    """
    frame_area = frame_width * frame_height
    density_score = (person_count / frame_area) * 100000

    if density_score < 2.0:
        risk_level = "SAFE"
        color = "green"
        message = "Crowd density is within safe limits."
    elif density_score < 5.0:
        risk_level = "WARNING"
        color = "orange"
        message = "Crowd density is getting high. Monitor closely."
    else:
        risk_level = "DANGER"
        color = "red"
        message = "CRITICAL: Dangerous crowd density detected! Immediate action required."

    return {
        "person_count": person_count,
        "density_score": round(density_score, 4),
        "risk_level": risk_level,
        "color": color,
        "message": message,
        "frame_width": frame_width,
        "frame_height": frame_height
    }


def estimate_density_from_frame(frame):
    """
    FOR ULTRA-DENSE CROWDS where individual detection fails.
    Uses image processing to estimate crowd density from visual patterns.
    Works by analyzing pixel intensity, edges, and texture complexity.
    Returns estimated crowd count and density result.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # Step 1: Edge detection — more edges = more people
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.sum(edges > 0) / (h * w)

    # Step 2: Texture complexity using Laplacian variance
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    texture_score = laplacian.var()

    # Step 3: Divide frame into a 4x4 grid, analyze each cell
    grid_rows, grid_cols = 4, 4
    cell_h = h // grid_rows
    cell_w = w // grid_cols
    cell_scores = []

    for r in range(grid_rows):
        for c in range(grid_cols):
            cell = gray[r*cell_h:(r+1)*cell_h, c*cell_w:(c+1)*cell_w]
            cell_edges = cv2.Canny(cell, 50, 150)
            cell_score = np.sum(cell_edges > 0) / (cell_h * cell_w)
            cell_scores.append(cell_score)

    avg_cell_score = np.mean(cell_scores)
    occupied_cells = sum(1 for s in cell_scores if s > 0.05)

    # Step 4: Estimate people count from edge density
    # Calibrated formula based on typical crowd images
    estimated_count = int((edge_density * 1000) + (texture_score * 0.01) + (occupied_cells * 5))
    estimated_count = max(0, min(estimated_count, 5000))  # Cap at 5000

    # Step 5: Classify risk based on edge density thresholds
    if edge_density < 0.08:
        risk_level = "SAFE"
        color = "green"
        message = "Low crowd density detected."
    elif edge_density < 0.18:
        risk_level = "WARNING"
        color = "orange"
        message = "Moderate crowd density. Monitor closely."
    else:
        risk_level = "DANGER"
        color = "red"
        message = "CRITICAL: High crowd density detected! Immediate action required."

    return {
        "person_count": estimated_count,
        "density_score": round(edge_density * 100, 4),
        "risk_level": risk_level,
        "color": color,
        "message": message,
        "frame_width": w,
        "frame_height": h,
        "method": "visual_density_estimation"
    }