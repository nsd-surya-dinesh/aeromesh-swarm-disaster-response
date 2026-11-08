"""Sensor sources and bridge — hardware-optional I/O for the vision pipeline.

SensorSource is the base; FakeSensorSource generates test frames with no hardware.
OpenCVCameraSource and SerialLidarSource are optional adapters that import cv2/serial
only when constructed, so the package imports cleanly without them.
"""
import time
import numpy as np
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass
from enum import Enum


class SensorType(Enum):
    CAMERA = "camera"
    LIDAR = "lidar"


@dataclass
class SensorFrame:
    """One reading from a sensor source."""
    sensor_type: SensorType
    timestamp: float
    image: Optional[np.ndarray]               # HxWx3 uint8 for camera; None for lidar
    points: Optional[np.ndarray]              # Nx3 float for lidar; None for camera
    metadata: Dict[str, Any]


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------
class SensorSource(ABC):
    """Abstract sensor source."""

    @abstractmethod
    def read(self) -> Optional[SensorFrame]:
        """Return the next frame, or None if unavailable."""
        ...

    def release(self) -> None:
        """Clean up resources."""
        pass


# ---------------------------------------------------------------------------
# Fake source — runs with no hardware
# ---------------------------------------------------------------------------
class FakeSensorSource(SensorSource):
    """Generates synthetic frames for testing.

    - Camera frames: black 640x480 image with a colored rectangle.
    - Lidar scans: a small point cloud with one obstacle cluster.
    """

    def __init__(
        self,
        sensor_type: SensorType = SensorType.CAMERA,
        width: int = 640,
        height: int = 480,
        blob_color: tuple = (0, 0, 255),   # BGR red by default
        blob_rect: tuple = (200, 150, 80, 60),  # x, y, w, h
    ):
        self.sensor_type = sensor_type
        self.width = width
        self.height = height
        self.blob_color = blob_color
        self.blob_rect = blob_rect

    def read(self) -> Optional[SensorFrame]:
        if self.sensor_type == SensorType.CAMERA:
            return self._camera_frame()
        return self._lidar_frame()

    def _camera_frame(self) -> SensorFrame:
        img = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        x, y, w, h = self.blob_rect
        img[y:y + h, x:x + w] = self.blob_color
        return SensorFrame(
            sensor_type=SensorType.CAMERA,
            timestamp=time.time(),
            image=img,
            points=None,
            metadata={"source": "fake", "width": self.width, "height": self.height},
        )

    def _lidar_frame(self) -> SensorFrame:
        # One cluster of 20 points around (5.0, 3.0, 0.0)
        center = np.array([5.0, 3.0, 0.0])
        pts = center + np.random.randn(20, 3) * 0.3
        return SensorFrame(
            sensor_type=SensorType.LIDAR,
            timestamp=time.time(),
            image=None,
            points=pts.astype(np.float32),
            metadata={"source": "fake"},
        )


# ---------------------------------------------------------------------------
# Optional real adapters — import heavy libs only when constructed
# ---------------------------------------------------------------------------
class OpenCVCameraSource(SensorSource):
    """Real USB / CSI camera via OpenCV."""

    def __init__(self, device: int = 0, fps: int = 30, resolution: tuple = (640, 480)):
        import cv2  # fail fast if not installed
        self._cv2 = cv2
        self.cap = cv2.VideoCapture(device)
        self.cap.set(cv2.CAP_PROP_FPS, fps)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera device {device}")

    def read(self) -> Optional[SensorFrame]:
        ret, frame = self.cap.read()
        if not ret:
            return None
        return SensorFrame(
            sensor_type=SensorType.CAMERA,
            timestamp=time.time(),
            image=frame,
            points=None,
            metadata={"source": "opencv"},
        )

    def release(self) -> None:
        if self.cap:
            self.cap.release()


class SerialLidarSource(SensorSource):
    """Real serial lidar (e.g. RPLidar, TFmini)."""

    def __init__(self, port: str = "/dev/ttyUSB0", baud: int = 115200):
        import serial  # fail fast if not installed
        self.conn = serial.Serial(port, baud, timeout=1)

    def read(self) -> Optional[SensorFrame]:
        line = self.conn.readline().decode(errors="replace").strip()
        if not line:
            return None
        try:
            parts = line.split(",")
            pts = np.array([[float(v) for v in p.split(":")] for p in parts], dtype=np.float32)
            return SensorFrame(
                sensor_type=SensorType.LIDAR,
                timestamp=time.time(),
                image=None,
                points=pts,
                metadata={"source": "serial"},
            )
        except (ValueError, IndexError):
            return None

    def release(self) -> None:
        if self.conn and self.conn.is_open:
            self.conn.close()


# ---------------------------------------------------------------------------
# Bridge — polls a source, respects kill switch
# ---------------------------------------------------------------------------
class SensorBridge:
    """Polls a SensorSource and dispatches frames to callbacks.

    If a KillSwitch is bound, frames are suppressed while triggered.
    """

    def __init__(self, source: SensorSource):
        self.source = source
        self.callbacks: List[Callable[[SensorFrame], None]] = []
        self._kill_switch = None

    def bind_kill_switch(self, ks) -> None:
        """Bind a KillSwitch; while triggered, read() returns None."""
        self._kill_switch = ks

    def on_frame(self, callback: Callable[[SensorFrame], None]) -> None:
        self.callbacks.append(callback)

    def read(self) -> Optional[SensorFrame]:
        """Read one frame from the source, respecting the kill switch."""
        if self._kill_switch and self._kill_switch.is_triggered():
            return None
        return self.source.read()

    def tick(self) -> Optional[SensorFrame]:
        """Read one frame and dispatch to callbacks. Returns the frame."""
        frame = self.read()
        if frame is not None:
            for cb in self.callbacks:
                try:
                    cb(frame)
                except Exception:
                    pass
        return frame

    def release(self) -> None:
        self.source.release()
