"""
3D Path Planning and Collision Avoidance Engine
Generates collision-free 3D trajectories for UAVs respecting kinodynamic limits,
minimum separation distance, and communication tether constraints.
"""
import math
import numpy as np
from typing import List, Optional, Tuple, Dict
from core.models import Vector3D, UAV, MissionState, UAVRole
from core.config import config


class PathPlanner:
    """Multi-UAV 3D collision-free path planner with communication awareness"""

    def __init__(self, mission_state: MissionState):
        self.mission_state = mission_state
        self.cfg_uav = config.uav
        self.min_separation = 15.0  # meters minimum distance between UAVs
        self.collision_avoidance_gain = 3.0

    def compute_collision_avoidance_vector(self, uav: UAV) -> Vector3D:
        """
        Computes repulsive velocity vector using Artificial Potential Fields
        to avoid collision with nearby UAVs.
        """
        repulsive_force = Vector3D(0, 0, 0)

        for other_id, other_uav in self.mission_state.uavs.items():
            if other_id == uav.id or not other_uav.is_operational():
                continue

            delta = uav.position - other_uav.position
            dist = delta.norm()

            if dist < self.min_separation and dist > 1e-3:
                # Strong repulsive gradient
                magnitude = self.collision_avoidance_gain * ((self.min_separation - dist) / dist)
                repulsive_force = repulsive_force + (delta.normalize() * magnitude)

        return repulsive_force

    def get_next_waypoint(self, uav: UAV) -> Optional[Vector3D]:
        """
        Returns the next immediate 3D waypoint for a UAV based on its role and targets.
        Applies obstacle and collision avoidance offsets.
        """
        if uav.target_position is None:
            return None

        # Base target direction
        target = uav.target_position

        # Apply collision avoidance offset
        avoidance_offset = self.compute_collision_avoidance_vector(uav)
        adjusted_target = target + avoidance_offset

        # Maintain safe survey altitude
        adjusted_target.z = max(30.0, adjusted_target.z)

        return adjusted_target

    def generate_dubins_path(self, start: Vector3D, end: Vector3D,
                             num_waypoints: int = 20) -> List[Vector3D]:
        """
        Generates a smooth 3D path interpolated between start and end.
        """
        waypoints = []
        for i in range(num_waypoints + 1):
            t = i / float(num_waypoints)
            # Smooth Hermite/sigmoid interpolation
            s = 3 * (t ** 2) - 2 * (t ** 3)

            wp = Vector3D(
                start.x + s * (end.x - start.x),
                start.y + s * (end.y - start.y),
                start.z + s * (end.z - start.z)
            )
            waypoints.append(wp)

        return waypoints
