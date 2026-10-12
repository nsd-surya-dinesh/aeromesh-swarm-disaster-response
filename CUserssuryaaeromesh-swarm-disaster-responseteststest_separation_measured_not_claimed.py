"""Phase 2 regression — separation is measured, not enforced or claimed safe."""
import pytest
from core.models import MissionState, UAV, Vector3D

def test_separation_measured_only():
    """Actual observed separation is reported; no false claim of enforced minimum."""
    state = MissionState()
    state.uavs[0] = UAV(id=0, position=Vector3D(100, 0, 50))
    state.uavs[1] = UAV(id=1, position=Vector3D(101, 0, 50))  # 1m apart
    # Simulator measures this; does not prevent it
    from simulation.simulator import Simulator
    sim = Simulator(state)
    # Just verify measurement code runs without claiming enforcement
    sim._update_safety_metrics()
    assert state.min_uav_separation_observed < 2.0
    # Explicit: this is measurement only; trajectory constraints not enforced
