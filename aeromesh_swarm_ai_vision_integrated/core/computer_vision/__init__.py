"""Computer Vision package — real detection, simulation-first.

All detectors import cv2 lazily inside their detect()/draw() methods,
so `import core.computer_vision` always succeeds even without OpenCV.
"""
from core.computer_vision.types import Detection, Obstacle, BBox, VisionResult
from core.computer_vision.uav_detect import UAVDetector
from core.computer_vision.obstacle_vision import ObstacleVision
from core.computer_vision.hazard_overlay import HazardOverlay
from core.computer_vision.kill_switch import KillSwitch
from core.computer_vision.sensor_bridge import (
    SensorType, SensorFrame, SensorSource,
    FakeSensorSource, SensorBridge,
)

__all__ = [
    "Detection", "Obstacle", "BBox", "VisionResult",
    "UAVDetector", "ObstacleVision", "HazardOverlay", "KillSwitch",
    "SensorType", "SensorFrame", "SensorSource", "FakeSensorSource", "SensorBridge",
]
