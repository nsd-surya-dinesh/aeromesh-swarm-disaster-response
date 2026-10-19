"""UAV detection — OpenCV HSV color + contour filter.

Lazily imports cv2 inside detect() so the module loads without OpenCV installed.
Targets bright-colored UAVs against sky/ground backgrounds.
"""
import numpy as np
from typing import List, Optional
from core.computer_vision.types import Detection, BBox


class UAVDetector:
    """Detects UAVs in a BGR camera frame by HSV color masking + contour filtering.

    Default HSV range targets red objects (common UAV marker color).
    """

    def __init__(
        self,
        hsv_lower1: tuple = (0, 120, 70),
        hsv_upper1: tuple = (10, 255, 255),
        hsv_lower2: tuple = (170, 120, 70),
        hsv_upper2: tuple = (180, 255, 255),
        min_area: int = 300,
        min_confidence: float = 0.3,
    ):
        # Red wraps around 0/180 in HSV, so we use two ranges
        self.hsv_lower1 = np.array(hsv_lower1, dtype=np.uint8)
        self.hsv_upper1 = np.array(hsv_upper1, dtype=np.uint8)
        self.hsv_lower2 = np.array(hsv_lower2, dtype=np.uint8)
        self.hsv_upper2 = np.array(hsv_upper2, dtype=np.uint8)
        self.min_area = min_area
        self.min_confidence = min_confidence

    def detect(self, frame: Optional[np.ndarray] = None) -> List[Detection]:
        """Detect UAVs in a BGR image frame.

        Returns an empty list if frame is None or no UAVs found.
        Confidence is derived from contour area relative to the frame.
        """
        if frame is None or frame.size == 0:
            return []

        import cv2

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Two masks for red (wraps at hue 0/180)
        mask1 = cv2.inRange(hsv, self.hsv_lower1, self.hsv_upper1)
        mask2 = cv2.inRange(hsv, self.hsv_lower2, self.hsv_upper2)
        mask = cv2.bitwise_or(mask1, mask2)

        # Clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        frame_area = frame.shape[0] * frame.shape[1]
        detections: List[Detection] = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.min_area:
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            # Confidence: larger contour relative to frame = higher confidence, capped at 1.0
            confidence = min(1.0, (area / frame_area) * 50.0)
            if confidence < self.min_confidence:
                continue

            # Aspect ratio filter: UAVs are roughly square-ish, not thin lines
            aspect = w / max(h, 1)
            if aspect < 0.2 or aspect > 5.0:
                continue

            detections.append(Detection(
                label="uav",
                bbox=BBox(x=x, y=y, w=w, h=h),
                confidence=confidence,
            ))

        return detections
