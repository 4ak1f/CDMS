import cv2
import numpy as np
import torch


class CrowdEnsemble:
    """
    Multi-model ensemble for crowd counting.
    Automatically selects best model based on scene analysis.
    
    Models:
    1. YOLO — best for sparse scenes (0-15 people)
    2. VGG16 density — best for moderate crowds (15-500)
    3. CSRNet-style — best for dense crowds (500+)
    4. Perspective correction — applied when camera angle detected
    """

    def __init__(self, crowd_model, device):
        self.crowd_model = crowd_model
        self.device      = device
        self.history     = []  # Track recent counts for smoothing

    def detect_camera_angle(self, frame):
        """
        Estimates camera angle using vanishing point detection.
        Returns perspective_factor (1.0 = straight on, >1.0 = overhead)
        """
        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 80,
                                minLineLength=50, maxLineGap=10)

        if lines is None or len(lines) < 5:
            return 1.0  # No clear perspective detected

        # Calculate average line angle
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 - x1 != 0:
                angle = abs(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
                angles.append(angle)

        if not angles:
            return 1.0

        avg_angle = np.mean(angles)

        # Overhead camera (angle close to 0 or 180) needs less scaling
        # Side camera (angle close to 90) may need more
        if avg_angle < 20 or avg_angle > 160:
            return 0.8   # Overhead — people look smaller, slightly reduce
        elif 70 < avg_angle < 110:
            return 1.2   # Side angle — slight increase
        else:
            return 1.0   # Normal angle

    def csrnet_estimate(self, frame):
        """
        CSRNet-inspired dense crowd estimation.
        Uses multi-scale patch analysis for ultra-dense crowds.
        """
        from backend.crowd_model import generate_density_map
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Split into overlapping patches for better dense crowd handling
        h, w  = gray.shape
        patch_size = 256
        stride     = 128
        total_count = 0
        patch_count = 0

        for y in range(0, h - patch_size + 1, stride):
            for x in range(0, w - patch_size + 1, stride):
                patch = frame[y:y+patch_size, x:x+patch_size]
                _, count, _, _fp = generate_density_map(
                    self.crowd_model, self.device, patch
                )
                total_count += count
                patch_count += 1

        if patch_count == 0:
            return 0.0

        # Normalize for overlap
        overlap_factor = (patch_size / stride) ** 2
        return total_count / overlap_factor

    def smooth_count(self, count):
        """
        Temporal smoothing — reduces jitter in real-time feeds.
        Uses exponential moving average.
        """
        self.history.append(count)
        if len(self.history) > 5:
            self.history.pop(0)

        if len(self.history) < 2:
            return count

        # Weighted average — recent counts matter more
        weights = [0.1, 0.15, 0.2, 0.25, 0.3][-len(self.history):]
        smoothed = sum(w * c for w, c in zip(weights, self.history))
        return round(smoothed)

    def predict(self, frame, yolo_count, density_count, confidence, crowd_mode="auto"):
        """
        Main ensemble prediction.
        Selects and combines models based on scene analysis.
        """
        from backend.crowd_model import generate_density_map

        # Ultra-dense check: YOLO is unreliable for dense crowds — bypass it entirely
        is_ultra_dense = (
            density_count > 200 or
            crowd_mode in ('dense', 'mega') or
            (crowd_mode == 'auto' and density_count > 150 and yolo_count < density_count * 0.1)
        )
        if is_ultra_dense:
            perspective = self.detect_camera_angle(frame)
            final = density_count * perspective
            return {
                "count":   round(final, 1),
                "method":  "DENSITY_ULTRA",
                "yolo":    yolo_count,
                "density": density_count,
                "note":    "Ultra-dense: YOLO bypassed, density model only"
            }

        # Step 1: Camera angle correction
        perspective_factor = self.detect_camera_angle(frame)

        # Step 2: Select model based on YOLO count
        # Override automatic detection with user-selected mode
        if crowd_mode == "sparse":
            final_count  = float(yolo_count)
            method       = "YOLO [Sparse Mode]"
            confidence_adj = 0.95

        elif crowd_mode == "moderate":
            final_count  = (density_count * 0.4) + (float(yolo_count) * 0.6)
            method       = "Blend [Moderate Mode]"
            confidence_adj = 0.85

        elif crowd_mode == "dense": 
            final_count  = (density_count * 0.7) + (float(yolo_count) * 0.3)
            method       = "Density [Dense Mode]"
            confidence_adj = 0.75

        elif crowd_mode == "mega":
            csrnet_count = self.csrnet_estimate(frame)
            final_count  = (csrnet_count * 0.5) + (density_count * 0.5)
            method       = "CSRNet [Mega Mode]"
            confidence_adj = 0.65

        else:  # auto
            if yolo_count <= 15:
                final_count    = float(yolo_count)
                method         = "YOLO [Auto]"
                confidence_adj = 0.95
            elif yolo_count <= 50:
                final_count    = (density_count * 0.4) + (float(yolo_count) * 0.6)
                method         = "Blend [Auto]"
                confidence_adj = 0.85
            elif density_count <= 500:
                final_count    = (density_count * 0.7) + (float(yolo_count) * 0.3)
                method         = "Density [Auto]"
                confidence_adj = 0.75
            else:
                csrnet_count = self.csrnet_estimate(frame)
                final_count  = (csrnet_count * 0.5) + (density_count * 0.5)
                method       = "CSRNet [Auto]"
                confidence_adj = 0.65

        # Step 3: Apply perspective correction
        final_count = final_count * perspective_factor

        # Step 4: Temporal smoothing
        final_count = self.smooth_count(final_count)

        return {
            "count":            final_count,
            "method":           method,
            "perspective":      round(perspective_factor, 2),
            "confidence_adj":   confidence_adj,
        }