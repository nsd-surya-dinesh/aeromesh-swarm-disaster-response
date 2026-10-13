"""Failure detector tests."""
from swarm.failure_detector import FailureDetector

def test_timeout():
    fd = FailureDetector()
    fd.update(1, 0.0)
    assert fd.get_failed_drones(10.0) == [1]
    assert fd.get_failed_drones(3.0) == []

def test_reallocate_stub():
    fd = FailureDetector()
    assert fd.reallocate_grid(99, [1, 2, 3]) == [1, 2, 3]
