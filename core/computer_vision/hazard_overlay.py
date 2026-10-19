"""Hazard overlay — draws detections and obstacles onto a camera frame.

Lazily imports cv2 inside draw() so the module loads without OpenCV installed.
"""
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from core.computer_vision.types import Detection, Obstacle, VisionResult


# Color palette (BGR) for different hazard/detection types
_COLORS = {
    "uav":       (0, 0, 255),     # red
    "structure": (0, 165, 255),   # orange
    "cluster":   (0, 255, 255),   # yellow
    "fire":      (0, 0, 200),     # dark red
    "flood":     (200, 100, 0),   # blue
    "unknown":   (128, 128, 128), # gray
}


class HazardOverlay:
    """Draws detection boxes, obstacle markers, and hazard labels onto a frame."""

    def __init__(self):
        self.hazards: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Manual hazard registration (e.g. from external data, not vision)
    # ------------------------------------------------------------------
    def add_hazard(self, hazard_type: str, location: tuple, severity: float = 1.0) -> None:
        self.hazards.append({"type": hazard_type, "location": location, "severity": severity})

    def clear_hazards(self) -> None:
        self.hazards = []

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def draw(
        self,
        frame: Optional[np.ndarray],
        detections: Optional[List[Detection]] = None,
        obstacles: Optional[List[Obstacle]] = None,
    ) -> Optional[np.ndarray]:
        """Annotate a BGR frame with detection boxes and obstacle markers.

        Returns the annotated frame, or None if frame is None.
        """
        if frame is None:
            return None

        import cv2

        out = frame.copy()
        detections = detections or []
        obstacles = obstacles or []

        # Draw detection bounding boxes
        for det in detections:
            color = _COLORS.get(det.label, _COLORS["unknown"])
            b = det.bbox
            cv2.rectangle(out, (b.x, b.y), (b.x + b.w, b.y + b.h), color, 2)
            label_text = f"{det.label} {det.confidence:.0%}"
            cv2.putText(out, label_text, (b.x, b.y - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        # Draw obstacle markers (projected as circles at image center offset)
        h_img, w_img = out.shape[:2]
        for obs in obstacles:
            color = _COLORS.get(obs.kind, _COLORS["unknown"])
            # Simple projection: depth in obs.position[0], lateral in [1]
            # Scale to image coordinates for visualization
            depth = max(obs.position[0], 0.1)
            px_x = int(w_img / 2 + obs.position[1] * 50)
            px_y = int(h_img / 2 + obs.position[2] * 50)
            radius = max(5, int(30 / depth))
            px_x = max(0, min(w_img - 1, px_x))
            px_y = max(0, min(h_img - 1, px_y))
            cv2.circle(out, (px_x, px_y), radius, color, 2)
            cv2.putText(out, obs.kind, (px_x + radius + 2, px_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        # Draw manual hazards
        for hz in self.hazards:
            color = _COLORS.get(hz["type"], _COLORS["unknown"])
            loc = hz["location"]
            if len(loc) >= 2:
                pt = (int(loc[0]), int(loc[1]))
                cv2.drawMarker(out, pt, color, cv2.MARKER_TRIANGLE_UP, 20, 2)
                cv2.putText(out, f"{hz['type']} sev={hz['severity']:.1f}",
                            (pt[0] + 12, pt[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        return out
