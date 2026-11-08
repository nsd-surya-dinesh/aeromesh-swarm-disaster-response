"""
Pre-Configured Disaster Mission Scenarios
Implements 4 comprehensive benchmark scenarios for stage 1 verification.
"""
from typing import Tuple, List
import numpy as np
from core.models import Vector3D
from simulation.simulator import MissionSimulator


class ScenarioBuilder:
    """Constructs predefined evaluation scenarios"""

    @staticmethod
    def scenario_1_baseline_survey() -> MissionSimulator:
        """
        Scenario 1: Baseline Disaster Survey
        - 5 UAVs
        - 10 PoIs distributed across 2km x 2km area
        - GCS at (0, 0, 0)
        - Tests basic coverage, CBBA allocation, and multi-hop routing
        """
        sim = MissionSimulator()

        # 10 PoIs distributed in clusters representing disaster zones
        pois = [
            Vector3D(300, 200, 0),
            Vector3D(450, 600, 0),
            Vector3D(700, 300, 0),
            Vector3D(850, 800, 0),
            Vector3D(200, 750, 0),
            Vector3D(-300, 400, 0),
            Vector3D(-500, 700, 0),
            Vector3D(-650, 200, 0),
            Vector3D(100, 950, 0),
            Vector3D(600, 1100, 0)
        ]

        priorities = [1.0, 2.0, 1.5, 3.0, 1.0, 1.2, 2.5, 1.0, 1.8, 2.2]

        sim.initialize_scenario(num_uavs=5, poi_positions=pois, poi_priorities=priorities)
        return sim

    @staticmethod
    def scenario_2_deep_canyon_los_blockage() -> MissionSimulator:
        """
        Scenario 2: Deep Canyon / Line-of-Sight Blockage
        - 6 UAVs
        - Distant PoIs behind a simulated mountain ridge (distance > 1200m)
        - Demands dedicated multi-hop relay chain deployment
        """
        sim = MissionSimulator()

        # Distant PoIs in a deep valley
        pois = [
            Vector3D(800, 800, 0),
            Vector3D(1000, 1000, 0),
            Vector3D(1200, 900, 0),
            Vector3D(1400, 1100, 0),
            Vector3D(1100, 1300, 0),
            Vector3D(1300, 1400, 0),
            Vector3D(1500, 1200, 0),
            Vector3D(1600, 1500, 0)
        ]

        priorities = [2.0, 3.0, 2.5, 4.0, 3.5, 5.0, 3.0, 4.5]

        sim.initialize_scenario(num_uavs=6, poi_positions=pois, poi_priorities=priorities)
        return sim

    @staticmethod
    def scenario_3_dynamic_emergency_and_node_failure() -> MissionSimulator:
        """
        Scenario 3: Dynamic Hotspot Outbreak & Relay Hardware Failure
        - 6 UAVs, 8 initial PoIs
        - At t=100s: High-priority survivor cluster emerges (Priority 8.0)
        - At t=180s: Critical Relay UAV-1 experiences hardware failure
        - Tests dynamic re-allocation, preemption, and self-healing
        """
        sim = MissionSimulator()

        pois = [
            Vector3D(300, 400, 0),
            Vector3D(500, 300, 0),
            Vector3D(650, 700, 0),
            Vector3D(400, 900, 0),
            Vector3D(-350, 500, 0),
            Vector3D(-500, 800, 0),
            Vector3D(200, 1200, 0),
            Vector3D(800, 1000, 0)
        ]

        priorities = [1.5, 1.0, 2.0, 1.8, 1.2, 2.2, 3.0, 2.5]

        sim.initialize_scenario(num_uavs=6, poi_positions=pois, poi_priorities=priorities)
        return sim

    @staticmethod
    def scenario_4_continuous_swapping_endurance() -> MissionSimulator:
        """
        Scenario 4: Long-Duration Mission with Continuous Battery Recharging & Handoffs
        - 8 UAVs, 16 PoIs distributed over large area
        - Tests battery depletion, RTB, GCS charging pad cycling, and seamless relay handoff
        """
        sim = MissionSimulator()

        # 16 PoIs across wide perimeter
        pois = []
        priorities = []
        for i in range(16):
            angle = (i / 16.0) * 2 * np.pi
            r = np.random.uniform(500, 1400)
            x = r * np.cos(angle)
            y = r * np.sin(angle)
            pois.append(Vector3D(x, y, 0))
            priorities.append(np.random.uniform(1.0, 4.0))

        sim.initialize_scenario(num_uavs=8, poi_positions=pois, poi_priorities=priorities)
        return sim
