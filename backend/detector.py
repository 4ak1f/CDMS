from ultralytics import YOLO
import cv2
import numpy as np

# YOLOv8 nano segmentation model
model = YOLO("yolov8n-seg.pt")
model.overrides['iou']  = 0.4
model.overrides['conf'] = 0.25


def detect_people(frame):
    """
    Detects people using YOLOv8 segmentation.
    - Draws outlines (masks) for sparse crowds
    - Filters phone screens and tiny detections
    - Runs multi-scale detection for better coverage
    Returns: annotated_frame, person_count, detections
    """
    h, w       = frame.shape[:2]
    frame_area = h * w
    detections = []
    annotated_frame = frame.copy()

    # Adaptive confidence based on frame size
    min_conf = 0.25 if frame_area > 500000 else 0.35

    # Run detection at original size
    all_results = model(frame, classes=[0], verbose=False)

    # Also run on upper half for standing people
    upper         = frame[:h//2, :]
    upper_results = model(upper, classes=[0], verbose=False, imgsz=320)

    # Process main results
    for result in all_results:
        boxes = result.boxes
        masks = result.masks

        for i, box in enumerate(boxes):
            confidence = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            box_area  = (x2 - x1) * (y2 - y1)
            box_ratio = box_area / frame_area

            # Filter out tiny detections (phone screens, photos)
            if confidence < min_conf or box_ratio < 0.005:
                continue

            detections.append({
                "bbox":       [x1, y1, x2, y2],
                "confidence": round(confidence, 2)
            })

            # Draw segmentation mask if available
            if masks is not None and i < len(masks.data):
                try:
                    mask = masks.data[i].cpu().numpy()
                    mask_resized = cv2.resize(mask, (w, h))
                    colored = np.zeros_like(annotated_frame)
                    colored[mask_resized > 0.5] = [0, 255, 80]
                    annotated_frame = cv2.addWeighted(
                        annotated_frame, 1, colored, 0.35, 0
                    )
                    # Draw outline around mask
                    contours, _ = cv2.findContours(
                        (mask_resized > 0.5).astype(np.uint8),
                        cv2.RETR_EXTERNAL,
                        cv2.CHAIN_APPROX_SIMPLE
                    )
                    cv2.drawContours(annotated_frame, contours, -1, (0, 255, 80), 2)
                except Exception:
                    cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 80), 2)
            else:
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 80), 2)

            # Confidence label
            cv2.putText(annotated_frame, f"{confidence:.0%}",
                        (x1, y1 - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 80), 1)

    # Process upper half results — add only NEW detections not already found
    existing_centers = set()
    for d in detections:
        cx = (d["bbox"][0] + d["bbox"][2]) // 2
        cy = (d["bbox"][1] + d["bbox"][3]) // 2
        existing_centers.add((cx // 20, cy // 20))  # Grid-based dedup

    for result in upper_results:
        for box in result.boxes:
            confidence = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            # Scale y coordinates back to full frame
            y1_full = y1
            y2_full = y2
            box_area  = (x2 - x1) * (y2_full - y1_full)
            box_ratio = box_area / frame_area

            if confidence < min_conf or box_ratio < 0.003:
                continue

            cx = (x1 + x2) // 2
            cy = (y1_full + y2_full) // 2
            grid_key = (cx // 20, cy // 20)

            if grid_key not in existing_centers:
                detections.append({
                    "bbox":       [x1, y1_full, x2, y2_full],
                    "confidence": round(confidence, 2)
                })
                existing_centers.add(grid_key)
                cv2.rectangle(annotated_frame,
                              (x1, y1_full), (x2, y2_full),
                              (0, 200, 255), 2)

    person_count = len(detections)

    # Count overlay
    cv2.putText(annotated_frame, f"People: {person_count}",
                (15, 35), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

    return annotated_frame, person_count, detections