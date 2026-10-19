"""Tests for the computer-vision pipeline — runs with no hardware.

Requires: pip install opencv-python-headless numpy pytest
"""
import sys
import time
import numpy as np
import pytest

# Ensure repo root is on sys.path
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))

from core.computer_vision.types import Detection, Obstacle, BBox, VisionResult
from core.computer_vision.sensor_bridge import (
    SensorType, SensorFrame, FakeSensorSource, SensorBridge,
)
from core.computer_vision.uav_detect import UAVDetector
from core.computer_vision.obstacle_vision import ObstacleVision
from core.computer_vision.hazard_overlay import HazardOverlay
from core.computer_vision.kill_switch import KillSwitch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _red_blob_frame(width=640, height=480, blob_x=200, blob_y=150, blob_w=80, blob_h=60):
    """Create a frame with a bright red rectangle on a black background."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    # BGR red = (0, 0, 255)
    img[blob_y:blob_y + blob_h, blob_x:blob_x + blob_w] = (0, 0, 255)
    return img


def _dark_blob_frame(width=640, height=480, blob_x=100, blob_y=100, blob_w=60, blob_h=60):
    """Create a frame with a dark gray rectangle (obstacle-like) on a lighter background."""
    img = np.full((height, width, 3), 180, dtype=np.uint8)  # light gray background
    img[blob_y:blob_y + blob_h, blob_x:blob_x + blob_w] = (30, 30, 30)  # dark blob
    return img


def _blank_frame(width=640, height=480):
    return np.zeros((height, width, 3), dtype=np.uint8)


# ---------------------------------------------------------------------------
# FakeSensorSource
# ---------------------------------------------------------------------------
class TestFakeSensorSource:
    def test_camera_frame_shape(self):
        src = FakeSensorSource(SensorType.CAMERA, width=320, height=240)
        frame = src.read()
        assert frame is not None
        assert frame.sensor_type == SensorType.CAMERA
        assert frame.image.shape == (240, 320, 3)
        assert frame.points is None

    def test_lidar_frame_shape(self):
        src = FakeSensorSource(SensorType.LIDAR)
        frame = src.read()
        assert frame is not None
        assert frame.sensor_type == SensorType.LIDAR
        assert frame.image is None
        assert frame.points is not None
        assert frame.points.shape[1] == 3


# ---------------------------------------------------------------------------
# UAVDetector
# ---------------------------------------------------------------------------
class TestUAVDetector:
    def test_detects_red_blob(self):
        """A bright red rectangle should yield at least one UAV detection."""
        det = UAVDetector(min_area=100, min_confidence=0.1)
        frame = _red_blob_frame()
        results = det.detect(frame)
        assert len(results) >= 1
        d = results[0]
        assert d.label == "uav"
        assert d.confidence > 0.0
        # Bounding box should overlap the blob region
        assert d.bbox.x < 280 and d.bbox.y < 210

    def test_blank_frame_no_detections(self):
        det = UAVDetector()
        results = det.detect(_blank_frame())
        assert results == []

    def test_none_frame(self):
        det = UAVDetector()
        assert det.detect(None) == []


# ---------------------------------------------------------------------------
# ObstacleVision
# ---------------------------------------------------------------------------
class TestObstacleVision:
    def test_detects_dark_obstacle(self):
        """A dark blob on a light background should yield at least one obstacle."""
        ov = ObstacleVision(min_area=100)
        frame = _dark_blob_frame()
        results = ov.detect(frame)
        assert len(results) >= 1
        obs = results[0]
        assert obs.kind == "structure"
        assert obs.position[0] > 0  # positive depth

    def test_blank_frame_no_obstacles(self):
        ov = ObstacleVision()
        assert ov.detect(_blank_frame()) == []

    def test_lidar_clustering(self):
        """A cluster of points should yield one obstacle."""
        ov = ObstacleVision()
        pts = np.array([
            [5.0, 3.0, 0.0],
            [5.1, 3.1, 0.1],
            [4.9, 2.9, -0.1],
            [5.2, 3.0, 0.0],
        ], dtype=np.float32)
        results = ov.detect_from_lidar(pts)
        assert len(results) >= 1
        obs = results[0]
        assert abs(obs.position[0] - 5.0) < 1.0

    def test_none_frame(self):
        ov = ObstacleVision()
        assert ov.detect(None) == []
        assert ov.detect_from_lidar(None) == []


# ---------------------------------------------------------------------------
# HazardOverlay
# ---------------------------------------------------------------------------
class TestHazardOverlay:
    def test_draw_returns_annotated_frame(self):
        ho = HazardOverlay()
        frame = _red_blob_frame()
        dets = [Detection(label="uav", bbox=BBox(200, 150, 80, 60), confidence=0.9)]
        obs = [Obstacle(position=(10.0, 0.0, 0.0), size=1.0, kind="structure")]
        result = ho.draw(frame, detections=dets, obstacles=obs)
        assert result is not None
        assert result.shape == frame.shape
        # Annotated frame should differ from original (drawings added)
        assert not np.array_equal(result, frame)

    def test_draw_none_frame(self):
        ho = HazardOverlay()
        assert ho.draw(None) is None

    def test_manual_hazards(self):
        ho = HazardOverlay()
        ho.add_hazard("fire", (300, 200), severity=0.8)
        assert len(ho.hazards) == 1
        frame = _blank_frame()
        result = ho.draw(frame)
        assert result is not None


# ---------------------------------------------------------------------------
# KillSwitch
# ---------------------------------------------------------------------------
class TestKillSwitch:
    def test_trigger_and_reset(self):
        ks = KillSwitch()
        assert not ks.is_triggered()
        ks.trigger("test")
        assert ks.is_triggered()
        assert ks.reason == "test"
        assert ks.get_time_since_trigger() >= 0
        ks.reset()
        assert not ks.is_triggered()

    def test_callback_fires(self):
        called = []
        ks = KillSwitch()
        ks.bind(lambda: called.append(True))
        ks.trigger("test")
        assert called == [True]

    def test_bind_vision_with_clear(self):
        class FakePipeline:
            def __init__(self):
                self.cleared = False
            def clear(self):
                self.cleared = True

        fp = FakePipeline()
        ks = KillSwitch()
        ks.bind_vision(fp)
        ks.trigger("test")
        assert fp.cleared


# ---------------------------------------------------------------------------
# SensorBridge
# ---------------------------------------------------------------------------
class TestSensorBridge:
    def test_reads_fake_source(self):
        src = FakeSensorSource(SensorType.CAMERA)
        bridge = SensorBridge(src)
        frame = bridge.read()
        assert frame is not None
        assert frame.sensor_type == SensorType.CAMERA

    def test_kill_switch_suppresses(self):
        src = FakeSensorSource(SensorType.CAMERA)
        ks = KillSwitch()
        bridge = SensorBridge(src)
        bridge.bind_kill_switch(ks)
        # Normal read works
        assert bridge.read() is not None
        # Triggered: suppressed
        ks.trigger("test")
        assert bridge.read() is None
        # Reset: works again
        ks.reset()
        assert bridge.read() is not None

    def test_tick_dispatches_callbacks(self):
        received = []
        src = FakeSensorSource(SensorType.CAMERA)
        bridge = SensorBridge(src)
        bridge.on_frame(lambda f: received.append(f))
        frame = bridge.tick()
        assert frame is not None
        assert len(received) == 1


# ---------------------------------------------------------------------------
# End-to-end pipeline
# ---------------------------------------------------------------------------
class TestPipeline:
    def test_full_pipeline_fake_source(self):
        """Full pipeline: fake source -> detect -> overlay -> result."""
        src = FakeSensorSource(
            SensorType.CAMERA,
            blob_color=(0, 0, 255),  # red blob
            blob_rect=(200, 150, 80, 60),
        )
        ks = KillSwitch()
        bridge = SensorBridge(src)
        bridge.bind_kill_switch(ks)

        uav_det = UAVDetector(min_area=100, min_confidence=0.1)
        obs_det = ObstacleVision(min_area=100)
        overlay = HazardOverlay()

        frame_data = bridge.read()
        assert frame_data is not None

        detections = uav_det.detect(frame_data.image)
        obstacles = obs_det.detect(frame_data.image)
        annotated = overlay.draw(frame_data.image, detections=detections, obstacles=obstacles)

        result = VisionResult(
            detections=detections,
            obstacles=obstacles,
            annotated_frame=annotated,
            timestamp=frame_data.timestamp,
        )

        assert len(result.detections) >= 1
        assert result.annotated_frame is not None
        assert not result.killed

    def test_kill_switch_blocks_pipeline(self):
        """Triggered kill switch means no output."""
        src = FakeSensorSource(SensorType.CAMERA)
        ks = KillSwitch()
        bridge = SensorBridge(src)
        bridge.bind_kill_switch(ks)

        ks.trigger("emergency")
        frame_data = bridge.read()
        assert frame_data is None  # suppressed
