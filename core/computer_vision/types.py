"""Shared types for the computer-vision pipeline."""
from dataclasses import dataclass, field
from typing import Tuple, Optional
import numpy as np


@dataclass
class BBox:
    """Axis-aligned bounding box in pixel coordinates (x, y, w, h)."""
    x: int
    y: int
    w: int
    h: int

    @property
    def center(self) -> Tuple[int, int]:
        return (self.x + self.w // 2, self.y + self.h // 2)

    @property
    def area(self) -> int:
        return self.w * self.h


@dataclass
class Detection:
    """A single detection result from any detector."""
    label: str
    bbox: BBox
    confidence: float = 0.0

    def __post_init__(self):
        self.confidence = max(0.0, min(1.0, self.confidence))


@dataclass
class Obstacle:
    """A 3D obstacle derived from vision detections."""
    position: Tuple[float, float, float]  # (x, y, z) in meters, NED-local
    size: float = 1.0                     # approximate radius in meters
    kind: str = "unknown"                 # "structure", "tree", "vehicle", etc.

    def to_vector3d(self):
        """Convert to core.models.Vector3D if available."""
        try:
            from core.models import Vector3D
            return Vector3D(*self.position)
        except ImportError:
            return self.position


@dataclass
class VisionResult:
    """Complete output of one vision-pipeline tick."""
    detections: list = field(default_factory=list)   # List[Detection]
    obstacles: list = field(default_factory=list)     # List[Obstacle]
    annotated_frame: Optional[np.ndarray] = field(default=None, repr=False)
    timestamp: float = 0.0
    killed: bool = False
