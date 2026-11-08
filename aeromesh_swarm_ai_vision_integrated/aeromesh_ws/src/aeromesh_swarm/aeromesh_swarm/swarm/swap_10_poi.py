"""
10-PoI Swap Algorithm — Dual-Decision Survey While Maintaining Connectivity
Implements the survey-while-connected algorithm from pasted requirements.
Each UAV makes two decisions simultaneously:
  - Mission (J(a)): Which PoI to survey next given priority, distance, energy.
  - Network: Will this movement break multi-hop link to GCS? If yes, stay/reply.
Preserves existing CBBA, ETX routing, and battery RTB logic.
"""
from typing import List, Optional, Tuple
import numpy as np
from aeromesh_swarm.core.models import UAV, PointOfInterest, MissionState, Vector3D, UAVRole, UAVState
from aeromesh_swarm.core.config import config
from aeromesh_swarm.comm.mesh_router import MeshRouter


def compute_utility(a: UAV, poi: PointOfInterest, mission_state: MissionState,
                    router: MeshRouter) -> float:
    """J(a) utility: higher = better survey choice."""
    dist = a.distance_to(poi.position)
    # Energy cost estimate
    travel_s = dist / max(1.0, config.uav.cruise_speed)
    energy_frac = (config.uav.cruise_power * travel_s) / 3600.0 / config.uav.battery_capacity
    # Disconnect risk: if move increases ETX to GCS above threshold
    # Simplified proxy: distance from GCS after move
    gcs_pos = mission_state.gcs.position
    future_dist_to_gcs = (poi.position - gcs_pos).norm()
    disconnect_penalty = 0.0 if future_dist_to_gcs < 1200 else 15.0
    return (poi.priority * 10.0 / max(1.0, dist)) - (energy_frac * 20.0) - disconnect_penalty


def can_survey_without_disconnect(a: UAV, target_poi: PointOfInterest,
                                   mission_state: MissionState,
                                   router: MeshRouter) -> bool:
    """Network decision: does moving to target maintain GCS connectivity for self + dependents?"""
    # If UAV is a critical relay with children, do not move if it breaks chain
    if a.role == UAVRole.RELAY and a.relay_children:
        # Must maintain direct or indirect GCS path after move; conservative: only allow if direct link remains likely
        target_pos = Vector3D(target_poi.position.x, target_poi.position.y, config.uav.survey_altitude)
        # Simplified: if target is far (>1500m from GCS) and UAV has relay children, deny
        dist_to_gcs = target_pos.distance_to(mission_state.gcs.position) if hasattr(target_pos, 'distance_to') else np.linalg.norm(np.array([target_pos.x, target_pos.y, target_pos.z]) - np.array([mission_state.gcs.position.x, mission_state.gcs.position.y, mission_state.gcs.position.z]))
        if dist_to_gcs > 1500:
            return False
    return True


def select_10_poi_swap(uavs: List[UAV], pois: List[PointOfInterest],
                        mission_state: MissionState, router: MeshRouter) -> List[Tuple[int, int]]:
    """
    Returns list of (uav_id, poi_id) assignments using 10-PoI swap logic.
    Each UAV evaluates all PoIs; picks best that passes network check.
    If best fails network, tries next best; if none pass, UAV holds/relay mode.
    """
    assignments = []
    for uav in uavs:
        if not uav.is_operational() or uav.battery_level < 0.25:
            continue
        candidates = [(compute_utility(uav, p, mission_state, router), p.id, p) for p in pois if not p.surveyed]
        candidates.sort(reverse=True, key=lambda x: x[0])
        assigned = False
        for score, poi_id, poi in candidates:
            if can_survey_without_disconnect(uav, poi, mission_state, router):
                assignments.append((uav.id, poi_id))
                assigned = True
                break
        if not assigned:
            # Degraded-connectivity policy: stay near nearest reachable node
            assignments.append((uav.id, -1))  # -1 = hold/reply
    return assignments


if __name__ == "__main__":
    print("10-PoI swap module loaded. Use select_10_poi_swap() with mission_state + router.")
