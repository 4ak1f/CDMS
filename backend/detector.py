from ultralytics import YOLO
import cv2
import numpy as np

# Load the YOLOv8 nano model (lightest and fastest - perfect for M2)
# It will auto-download on first run (~6MB)
model = YOLO("yolov8n.pt")

def detect_people(frame):
    """
    Takes a video frame (image), detects all people in it.
    Returns:
        - frame with bounding boxes drawn
        - count of people detected
        - list of bounding box coordinates
    """
    results = model(frame, classes=[0], verbose=False)
    # classes=[0] means only detect 'person' class, ignore cars, animals etc.

    detections = []
    annotated_frame = frame.copy()

    for result in results:
        boxes = result.boxes
        for box in boxes:
            confidence = float(box.conf[0])

            # Only count detections we're confident about (above 40%)
            if confidence >= 0.4:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                detections.append({
                    "bbox": [x1, y1, x2, y2],
                    "confidence": round(confidence, 2)
                })

                # Draw green box around each person
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                # Show confidence score above the box
                label = f"Person {confidence:.0%}"
                cv2.putText(annotated_frame, label, (x1, y1 - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    person_count = len(detections)

    # Display count on the top-left of the frame
    cv2.putText(annotated_frame, f"People: {person_count}", (15, 35),
                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)

    return annotated_frame, person_count, detections