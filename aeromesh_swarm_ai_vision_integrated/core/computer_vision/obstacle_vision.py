"""Obstacle detection — OpenCV contour-based, with a simple pinhole depth model.

Lazily imports cv2 inside detect() so the module loads without OpenCV installed.
"""
import time
import numpy as np
from typing import List, Optional
from core.computer_vision.types import Detection, Obstacle, BBox


# Assumed pinhole camera model for depth estimation (meters)
_FOCAL_LENGTH_PX = 500.0   # approximate focal length in pixels
_KNOWN_SIZE_M = 1.0         # assumed real-world size of a 1-px-at-focal-length object


class ObstacleVision:
    """Detects obstacles from a camera frame using color thresholding + contours.

    Returns a list of Obstacle with estimated 3D positions.
    """

    def __init__(
        self,
        min_area: int = 500,
        max_area: Optional[int] = None,
        hsv_lower: tuple = (0, 0, 0),
        hsv_upper: tuple = (180, 255, 80),
    ):
        self.min_area = min_area
        self.max_area = max_area
        self.hsv_lower = np.array(hsv_lower, dtype=np.uint8)
        self.hsv_upper = np.array(hsv_upper, dtype=np.uint8)

    def detect(self, frame: Optional[np.ndarray] = None) -> List[Obstacle]:
        """Run obstacle detection on a BGR image frame.

        Returns an empty list if frame is None or no obstacles found.
        """
        if frame is None or frame.size == 0:
            return []

        import cv2

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.hsv_lower, self.hsv_upper)

        # Clean up noise
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        obstacles: List[Obstacle] = []
        h_img, w_img = frame.shape[:2]
        cx_img, cy_img = w_img / 2.0, h_img / 2.0
        max_a = self.max_area if self.max_area is not None else int(0.85 * w_img * h_img)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.min_area or area > max_a:
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            # Estimate depth from apparent size (pinhole model)
            apparent_size = max(w, h)
            if apparent_size < 1:
                continue
            depth = (_FOCAL_LENGTH_PX * _KNOWN_SIZE_M) / apparent_size

            # Project pixel center to NED-local (x=forward=depth, y=right, z=down)
            px_cx = x + w / 2.0
            px_cy = y + h / 2.0
            obs_y = (px_cx - cx_img) * depth / _FOCAL_LENGTH_PX
            obs_z = (px_cy - cy_img) * depth / _FOCAL_LENGTH_PX

            obstacles.append(Obstacle(
                position=(depth, obs_y, obs_z),
                size=_KNOWN_SIZE_M,
                kind="structure",
            ))

        return obstacles

    def detect_from_lidar(self, points: Optional[np.ndarray] = None) -> List[Obstacle]:
        """Cluster a Nx3 point cloud into obstacles using simple grid binning."""
        if points is None or len(points) == 0:
            return []

        # Simple grid clustering: bin by 1m cells in XY
        cell_size = 1.0
        bins: dict = {}
        for pt in points:
            key = (int(pt[0] / cell_size), int(pt[1] / cell_size))
            bins.setdefault(key, []).append(pt)

        obstacles: List[Obstacle] = []
        for key, cluster in bins.items():
            cluster = np.array(cluster)
            if len(cluster) < 3:
                continue
            centroid = cluster.mean(axis=0)
            spread = np.linalg.norm(cluster.std(axis=0))
            obstacles.append(Obstacle(
                position=tuple(centroid),
                size=max(0.5, spread),
                kind="cluster",
            ))

        return obstacles
