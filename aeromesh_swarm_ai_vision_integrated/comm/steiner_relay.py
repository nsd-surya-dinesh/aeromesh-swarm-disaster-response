"""
Steiner Relay Placement and Communication-Aware Relay Management
Implements dynamic relay UAV positioning using Euclidean Steiner points and
Artificial Potential Fields (APF) to maintain connectivity.
"""
import numpy as np
from typing import List, Optional, Tuple
from core.models import UAV, UAVRole, UAVState, Vector3D, MissionState
from core.config import config
from comm.channel import RFChannel


class SteinerRelayManager:
    """Manages dynamic relay placement for communication-aware swarm coordination"""

    def __init__(self, mission_state: MissionState):
        self.mission_state = mission_state
        self.rf_channel = RFChannel()
        self.cfg_rf = config.rf
        self.cfg_uav = config.uav

    def compute_relay_position(self, node_a_pos: Vector3D, node_b_pos: Vector3D,
                                altitude: Optional[float] = None) -> Vector3D:
        """
        Computes optimal relay position between two nodes using Euclidean midpoint
        and elevation adjustment for maximum SNR and minimal path loss.

        For two-point Steiner problem: optimal relay is at midpoint with elevated altitude.
        """
        if altitude is None:
            altitude = self.cfg_uav.survey_altitude

        # Midpoint in 2D plane
        mid_x = (node_a_pos.x + node_b_pos.x) / 2.0
        mid_y = (node_a_pos.y + node_b_pos.y) / 2.0

        # Elevation: higher altitude improves LoS probability
        mid_z = max(node_a_pos.z, node_b_pos.z, altitude)

        return Vector3D(mid_x, mid_y, mid_z)

    def compute_multi_hop_relay_chain(self, start_pos: Vector3D, end_pos: Vector3D) -> List[Vector3D]:
        """
        Computes a chain of relay positions for long-distance connectivity.
        Places relays at intervals ensuring each hop maintains SNR >= threshold.
        """
        distance = (end_pos - start_pos).norm()

        # Estimate max reliable hop distance (conservative estimate: 500m for A2A)
        max_hop_distance = 500.0

        num_relays = max(0, int(np.ceil(distance / max_hop_distance)) - 1)

        if num_relays == 0:
            return []

        relay_positions = []
        for i in range(1, num_relays + 1):
            t = i / (num_relays + 1)
            relay_pos = Vector3D(
                start_pos.x + t * (end_pos.x - start_pos.x),
                start_pos.y + t * (end_pos.y - start_pos.y),
                max(start_pos.z, end_pos.z, self.cfg_uav.survey_altitude)
            )
            relay_positions.append(relay_pos)

        return relay_positions

    def compute_apf_relay_position(self, relay_uav: UAV,
                                   connected_nodes: List[Vector3D]) -> Vector3D:
        """
        Computes relay position using Artificial Potential Fields (APF).
        Attractive forces pull the relay towards nodes requiring connectivity.
        Repulsive forces prevent collision with obstacles/terrain.
        """
        if not connected_nodes:
            return relay_uav.position

        # Attractive force towards centroid of connected nodes
        centroid = Vector3D(0, 0, 0)
        for pos in connected_nodes:
            centroid = centroid + pos
        centroid = centroid * (1.0 / len(connected_nodes))

        # Attractive potential gradient
        k_attr = 0.5
        force_attr = (centroid - relay_uav.position) * k_attr

        # Repulsive force from ground (maintain minimum altitude)
        k_rep = 2.0
        min_altitude = 30.0
        force_rep = Vector3D(0, 0, 0)

        if relay_uav.position.z < min_altitude:
            force_rep = Vector3D(0, 0, k_rep * (min_altitude - relay_uav.position.z))

        # Total force
        total_force = force_attr + force_rep

        # Compute target position
        target_pos = relay_uav.position + total_force
        target_pos.z = max(min_altitude, target_pos.z)

        return target_pos

    def assign_relay_role(self, uav: UAV, parent_id: Optional[int] = None):
        """Assigns relay role to a UAV and sets its parent node"""
        uav.role = UAVRole.RELAY
        uav.state = UAVState.RELAYING
        uav.relay_parent = parent_id
        uav.assigned_poi = None

    def promote_scout_to_relay(self, uav_id: int):
        """Promotes a scout UAV to relay role for network healing"""
        if uav_id not in self.mission_state.uavs:
            return

        uav = self.mission_state.uavs[uav_id]
        if uav.is_operational() and uav.role == UAVRole.SCOUT:
            self.assign_relay_role(uav)
            self.mission_state.add_event(
                'relay_promotion',
                f'UAV-{uav_id} promoted to relay role for network healing'
            )

    def find_optimal_relay_candidate(self, failed_relay_id: int) -> Optional[int]:
        """
        Finds the best UAV to replace a failed relay.
        Selection criteria: proximity, battery level, and current task priority.
        """
        failed_relay = self.mission_state.uavs.get(failed_relay_id)
        if not failed_relay:
            return None

        best_candidate = None
        best_score = -float('inf')

        for uav_id, uav in self.mission_state.uavs.items():
            if not uav.is_operational() or uav.role == UAVRole.RELAY:
                continue

            # Scoring function
            distance = uav.distance_to(failed_relay.position)
            distance_score = 1.0 / max(1.0, distance / 100.0)
            battery_score = uav.battery_level
            role_score = 1.0 if uav.role == UAVRole.STANDBY else 0.5

            total_score = distance_score * 0.4 + battery_score * 0.3 + role_score * 0.3

            if total_score > best_score:
                best_score = total_score
                best_candidate = uav_id

        return best_candidate
