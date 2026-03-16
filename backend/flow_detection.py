import cv2
import numpy as np


class CrowdFlowDetector:
    """
    Detects crowd movement direction using Lucas-Kanade Optical Flow.
    
    Optical Flow tracks feature points between consecutive frames
    and calculates their velocity vectors. By analyzing these vectors
    we can determine overall crowd movement direction and detect
    dangerous surge patterns.
    
    Used in real stampede prevention systems at large events.
    """

    def __init__(self):
        self.prev_frame = None
        self.prev_points = None

        # Lucas-Kanade optical flow parameters
        self.lk_params = dict(
            winSize=(15, 15),
            maxLevel=2,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03)
        )

        # Parameters for detecting good feature points to track
        self.feature_params = dict(
            maxCorners=150,
            qualityLevel=0.3,
            minDistance=7,
            blockSize=7
        )

        self.flow_history = []  # Store recent flow vectors
        self.max_history = 10

    def detect_flow(self, frame):
        """
        Processes a frame and returns crowd flow analysis.
        Returns flow vectors, dominant direction, speed, and danger assessment.
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        result = {
            "direction": "Unknown",
            "angle": 0.0,
            "speed": 0.0,
            "flow_danger": False,
            "flow_message": "Insufficient data for flow analysis",
            "vectors": [],
            "surge_detected": False
        }

        # First frame — just store it
        if self.prev_frame is None:
            self.prev_frame = gray
            self.prev_points = cv2.goodFeaturesToTrack(gray, mask=None, **self.feature_params)
            return result, frame

        # Track points from previous frame
        if self.prev_points is not None and len(self.prev_points) > 0:
            curr_points, status, _ = cv2.calcOpticalFlowPyrLK(
                self.prev_frame, gray, self.prev_points, None, **self.lk_params
            )

            if curr_points is not None:
                # Keep only successfully tracked points
                good_new = curr_points[status == 1]
                good_old = self.prev_points[status == 1]

                if len(good_new) > 10:
                    # Calculate flow vectors
                    flow_vectors = good_new - good_old
                    velocities = np.sqrt(flow_vectors[:, 0]**2 + flow_vectors[:, 1]**2)
                    avg_speed = float(np.mean(velocities))

                    # Calculate dominant direction (mean angle)
                    angles = np.arctan2(flow_vectors[:, 1], flow_vectors[:, 0])
                    mean_angle = float(np.degrees(np.arctan2(
                        np.mean(np.sin(angles)),
                        np.mean(np.cos(angles))
                    )))

                    direction = self._angle_to_direction(mean_angle)

                    # Detect surge — high speed + low directional variance = stampede risk
                    angle_variance = float(np.degrees(np.std(angles)))
                    surge_detected = avg_speed > 8.0 and angle_variance < 30.0

                    # Flow danger assessment
                    if surge_detected:
                        flow_danger = True
                        flow_message = f"⚠️ SURGE DETECTED: Crowd moving {direction} at high speed!"
                    elif avg_speed > 5.0:
                        flow_danger = True
                        flow_message = f"Rapid crowd movement detected: {direction}"
                    elif avg_speed > 2.0:
                        flow_danger = False
                        flow_message = f"Moderate crowd movement: {direction}"
                    else:
                        flow_danger = False
                        flow_message = f"Normal crowd movement: {direction}"

                    # Store in history
                    self.flow_history.append({
                        "speed": avg_speed,
                        "angle": mean_angle,
                        "surge": surge_detected
                    })
                    if len(self.flow_history) > self.max_history:
                        self.flow_history.pop(0)

                    result = {
                        "direction": direction,
                        "angle": round(mean_angle, 2),
                        "speed": round(avg_speed, 2),
                        "flow_danger": flow_danger,
                        "flow_message": flow_message,
                        "vectors": flow_vectors[:20].tolist(),
                        "surge_detected": surge_detected,
                        "tracked_points": len(good_new)
                    }

                    # Draw flow arrows on frame
                    frame = self._draw_flow(frame, good_new, good_old, flow_danger)

        # Update for next frame
        self.prev_frame = gray
        self.prev_points = cv2.goodFeaturesToTrack(gray, mask=None, **self.feature_params)

        return result, frame

    def _angle_to_direction(self, angle):
        """Converts angle in degrees to human readable direction."""
        if -22.5 <= angle < 22.5:
            return "→ Right"
        elif 22.5 <= angle < 67.5:
            return "↘ Down-Right"
        elif 67.5 <= angle < 112.5:
            return "↓ Down"
        elif 112.5 <= angle < 157.5:
            return "↙ Down-Left"
        elif angle >= 157.5 or angle < -157.5:
            return "← Left"
        elif -157.5 <= angle < -112.5:
            return "↖ Up-Left"
        elif -112.5 <= angle < -67.5:
            return "↑ Up"
        else:
            return "↗ Up-Right"

    def _draw_flow(self, frame, good_new, good_old, is_danger):
        """Draws optical flow arrows on frame."""
        color = (0, 0, 255) if is_danger else (0, 255, 150)
        annotated = frame.copy()

        for new, old in zip(good_new, good_old):
            a, b = new.ravel().astype(int)
            c, d = old.ravel().astype(int)
            # Draw arrow
            cv2.arrowedLine(annotated, (c, d), (a, b), color, 2, tipLength=0.4)
            cv2.circle(annotated, (a, b), 3, color, -1)

        return annotated

    def reset(self):
        """Resets detector state — call when switching cameras."""
        self.prev_frame = None
        self.prev_points = None
        self.flow_history = []