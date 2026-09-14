"""
Unit Tests for Swarm Intelligence Subsystem
Tests CBBA task allocation, path planning, and health monitoring.
"""
import pytest
import numpy as np
from core.models import UAV, UAVRole, UAVState, PointOfInterest, Vector3D, MissionState, GCS
from core.config import config
from swarm.task_allocation import CBBATaskAllocator
from swarm.path_planner import PathPlanner
from swarm.health_monitor import HealthMonitor
from comm.steiner_relay import SteinerRelayManager


class TestCBBATaskAllocator:
    """Test consensus-based task allocation"""

    def test_marginal_score_calculation(self):
        """Marginal score should favor closer, higher priority PoIs"""
        mission_state = MissionState()
        mission_state.gcs = GCS(position=Vector3D(0, 0, 0))

        uav = UAV(id=0, position=Vector3D(0, 0, 50), battery_level=1.0)
        mission_state.uavs[0] = uav

        # Close, high priority PoI
        poi_close = PointOfInterest(id=0, position=Vector3D(100, 0, 0), priority=5.0)
        # Far, low priority PoI
        poi_far = PointOfInterest(id=1, position=Vector3D(1000, 0, 0), priority=1.0)

        mission_state.pois[0] = poi_close
        mission_state.pois[1] = poi_far

        allocator = CBBATaskAllocator(mission_state)

        score_close, _ = allocator.compute_marginal_score(uav, poi_close, [])
        score_far, _ = allocator.compute_marginal_score(uav, poi_far, [])

        assert score_close > score_far, "Closer, higher priority PoI should score higher"

    def test_cbba_allocation_assigns_tasks(self):
        """CBBA should allocate PoIs to UAVs"""
        mission_state = MissionState()
        mission_state.gcs = GCS(position=Vector3D(0, 0, 0))

        # Create 2 UAVs
        mission_state.uavs[0] = UAV(id=0, position=Vector3D(0, 0, 50), role=UAVRole.SCOUT, battery_level=1.0)
        mission_state.uavs[1] = UAV(id=1, position=Vector3D(100, 0, 50), role=UAVRole.SCOUT, battery_level=1.0)

        # Create 3 PoIs
        mission_state.pois[0] = PointOfInterest(id=0, position=Vector3D(200, 0, 0), priority=1.0)
        mission_state.pois[1] = PointOfInterest(id=1, position=Vector3D(400, 0, 0), priority=2.0)
        mission_state.pois[2] = PointOfInterest(id=2, position=Vector3D(600, 0, 0), priority=1.5)

        allocator = CBBATaskAllocator(mission_state)
        allocator.run_cbba_allocation()

        # Check that at least one UAV got assigned tasks
        total_assigned = sum(len(uav.task_bundle) for uav in mission_state.uavs.values())
        assert total_assigned > 0, "CBBA should assign at least one task"


class TestPathPlanner:
    """Test path planning and collision avoidance"""

    def test_collision_avoidance_repulsion(self):
        """Close UAVs should generate repulsive forces"""
        mission_state = MissionState()
        uav1 = UAV(id=0, position=Vector3D(0, 0, 50))
        uav2 = UAV(id=1, position=Vector3D(10, 0, 50))  # Very close

        mission_state.uavs[0] = uav1
        mission_state.uavs[1] = uav2

        planner = PathPlanner(mission_state)
        repulsion = planner.compute_collision_avoidance_vector(uav1)

        assert repulsion.norm() > 0, "Close UAVs should generate repulsive force"

    def test_dubins_path_generation(self):
        """Dubins path should generate smooth waypoints"""
        mission_state = MissionState()
        planner = PathPlanner(mission_state)

        start = Vector3D(0, 0, 50)
        end = Vector3D(500, 500, 50)

        waypoints = planner.generate_dubins_path(start, end, num_waypoints=10)

        assert len(waypoints) == 11, "Should generate correct number of waypoints"
        assert (waypoints[0].x, waypoints[0].y) == (start.x, start.y), "Should start at start position"
        assert abs(waypoints[-1].x - end.x) < 1, "Should end at end position"


class TestHealthMonitor:
    """Test battery monitoring and self-healing"""

    def test_low_battery_triggers_rtb(self):
        """Low battery should trigger return-to-base"""
        mission_state = MissionState()
        mission_state.gcs = GCS(position=Vector3D(0, 0, 0))

        uav = UAV(id=0, position=Vector3D(500, 0, 50), battery_level=0.15)  # Very low
        uav.role = UAVRole.SCOUT
        uav.state = UAVState.FLYING_TO_POI

        mission_state.uavs[0] = uav

        relay_mgr = SteinerRelayManager(mission_state)
        monitor = HealthMonitor(mission_state, relay_mgr)

        monitor.check_battery_thresholds(uav)

        assert uav.state == UAVState.RETURNING, "Low battery should trigger RTB"

    def test_charging_restoration(self):
        """UAV at GCS should charge and return to standby"""
        mission_state = MissionState()
        mission_state.time = 0.0
        mission_state.gcs = GCS(position=Vector3D(0, 0, 0))

        uav = UAV(id=0, position=Vector3D(5, 5, 0), battery_level=0.2)
        uav.state = UAVState.RETURNING
        mission_state.uavs[0] = uav

        relay_mgr = SteinerRelayManager(mission_state)
        monitor = HealthMonitor(mission_state, relay_mgr)

        # UAV should arrive at GCS and start charging
        monitor.check_node_vitality(dt=0.1)

        assert uav.state == UAVState.CHARGING, "UAV at GCS should charge"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
