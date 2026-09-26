"""
Consensus-Based Bundle Algorithm (CBBA) & Distributed Task Allocation Engine
Implements decentralized task allocation for PoI assignment with energy awareness,
dynamic priority, and consensus resolution across the swarm.
"""
import copy
import numpy as np
from typing import Dict, List, Tuple, Optional, Set
from core.models import UAV, PointOfInterest, MissionState, Vector3D, UAVRole, UAVState
from core.config import config


class CBBATaskAllocator:
    """
    Decentralized Consensus-Based Bundle Algorithm (CBBA) for UAV swarm task allocation.
    Consists of two alternating phases:
    1. Bundle Construction Phase: Each agent greedily adds tasks maximizing marginal score.
    2. Conflict Resolution Phase: Agents exchange winning bids and achieve consensus.
    """

    def __init__(self, mission_state: MissionState, max_bundle_size: int = 4):
        self.mission_state = mission_state
        self.max_bundle_size = max_bundle_size
        self.cfg_swarm = config.swarm
        self.cfg_uav = config.uav

        # Winning bid list: {poi_id: highest_bid_value}
        self.winning_bids: Dict[int, float] = {}

        # Winning agent list: {poi_id: winning_uav_id}
        self.winning_agents: Dict[int, int] = {}

        # Timestamps of winning bids: {poi_id: timestamp}
        self.bid_timestamps: Dict[int, float] = {}

    def compute_marginal_score(self, uav: UAV, poi: PointOfInterest,
                                current_path: List[int]) -> Tuple[float, int]:
        """
        Computes marginal score of inserting a PoI into the UAV's current path.
        Returns: (max_marginal_score, best_insertion_index)
        """
        if poi.surveyed or not uav.is_operational():
            return 0.0, -1

        # Check energy feasibility
        # Distance calculation
        best_score = -float('inf')
        best_idx = 0

        # Try inserting at every possible position in the path
        for idx in range(len(current_path) + 1):
            temp_path = current_path[:idx] + [poi.id] + current_path[idx:]

            # Compute total distance of this path
            total_dist = self._calculate_path_distance(uav.position, temp_path)

            # Time to complete path
            travel_time = total_dist / max(1.0, self.cfg_uav.cruise_speed)
            survey_time = len(temp_path) * self.cfg_uav.survey_duration
            total_time = travel_time + survey_time

            # Energy estimate
            energy_required = (self.cfg_uav.cruise_power * travel_time +
                               self.cfg_uav.hover_power * survey_time) / 3600.0  # Wh
            energy_fraction = energy_required / self.cfg_uav.battery_capacity

            # Energy safety check (must be able to complete path and return to GCS)
            gcs_return_dist = (self.mission_state.pois[temp_path[-1]].position -
                               self.mission_state.gcs.position).norm()
            gcs_return_energy = (self.cfg_uav.cruise_power * (gcs_return_dist / self.cfg_uav.cruise_speed)) / 3600.0
            gcs_return_fraction = gcs_return_energy / self.cfg_uav.battery_capacity

            if uav.battery_level - (energy_fraction + gcs_return_fraction) < self.cfg_uav.energy_reserve_ratio:
                # Infeasible due to battery constraints
                continue

            # Multi-objective utility score:
            # S = Priority * discount - alpha * distance - beta * energy
            time_discount = 0.98 ** (total_time / 60.0)  # Slight decay for longer wait
            priority_reward = poi.priority * 100.0 * time_discount
            dist_penalty = (total_dist / 1000.0) * 15.0
            energy_penalty = energy_fraction * 20.0

            score = priority_reward - dist_penalty - energy_penalty

            if score > best_score:
                best_score = score
                best_idx = idx

        if best_score == -float('inf'):
            return 0.0, -1

        return max(0.0, best_score), best_idx

    def _calculate_path_distance(self, start_pos: Vector3D, path: List[int]) -> float:
        """Calculates total Euclidean travel distance for a sequence of PoIs"""
        if not path:
            return 0.0

        dist = 0.0
        curr_pos = start_pos

        for poi_id in path:
            if poi_id in self.mission_state.pois:
                next_pos = self.mission_state.pois[poi_id].position
                dist += (next_pos - curr_pos).norm()
                curr_pos = next_pos

        return dist

    def run_cbba_allocation(self):
        """
        Executes decentralized CBBA iterations until convergence or max iterations reached.
        """
        scout_uavs = [u for u in self.mission_state.uavs.values()
                      if u.is_operational() and u.role in [UAVRole.SCOUT, UAVRole.STANDBY]]

        if not scout_uavs:
            return

        # Initialize tracking tables if empty
        self.last_iteration_count = 0  # For instrumentation
        unsurveyed = self.mission_state.get_unsurveyed_pois()
        for poi in unsurveyed:
            if poi.id not in self.winning_bids:
                self.winning_bids[poi.id] = 0.0
                self.winning_agents[poi.id] = -1
                self.bid_timestamps[poi.id] = 0.0

        # Iterative bundle build and consensus
        for iteration in range(self.cfg_swarm.cbba_max_iterations):
            changes_made = False

            # Phase 1: Bundle Building
            for uav in scout_uavs:
                if uav.battery_level < self.cfg_uav.rtb_threshold_ratio:
                    continue  # Needs RTB

                while len(uav.task_bundle) < self.max_bundle_size:
                    best_poi_id = None
                    best_marginal_score = 0.0
                    best_insertion_idx = -1

                    for poi in unsurveyed:
                        if poi.id in uav.task_bundle:
                            continue

                        score, idx = self.compute_marginal_score(uav, poi, uav.task_path)

                        # Must beat current highest bid
                        curr_winning_bid = self.winning_bids.get(poi.id, 0.0)
                        if score > curr_winning_bid and score > best_marginal_score:
                            best_marginal_score = score
                            best_poi_id = poi.id
                            best_insertion_idx = idx

                    if best_poi_id is not None and best_marginal_score > 0:
                        # Add to bundle and path
                        uav.task_bundle.append(best_poi_id)
                        uav.task_path.insert(best_insertion_idx, best_poi_id)

                        self.winning_bids[best_poi_id] = best_marginal_score
                        self.winning_agents[best_poi_id] = uav.id
                        self.bid_timestamps[best_poi_id] = self.mission_state.time
                        changes_made = True
                    else:
                        break

            # Phase 2: Conflict Resolution / Consensus (simulate mesh gossip)
            for uav in scout_uavs:
                # Check for outbid tasks in bundle
                reconstructed_bundle = []
                reconstructed_path = []

                for poi_id in uav.task_path:
                    # If this UAV is still the winner for this PoI
                    if self.winning_agents.get(poi_id) == uav.id:
                        reconstructed_path.append(poi_id)
                        reconstructed_bundle.append(poi_id)
                    else:
                        # Outbid: release all subsequent tasks in bundle
                        changes_made = True
                        break

                uav.task_bundle = reconstructed_bundle
                uav.task_path = reconstructed_path

            if not changes_made:
                self.last_iteration_count = iteration + 1
                break  # Converged
        else:
            self.last_iteration_count = self.cfg_swarm.cbba_max_iterations

        # Update active target positions for scouts
        for uav in scout_uavs:
            if uav.task_path and uav.state != UAVState.RETURNING:
                uav.role = UAVRole.SCOUT
                current_target_poi_id = uav.task_path[0]
                uav.assigned_poi = current_target_poi_id
                target_poi = self.mission_state.pois[current_target_poi_id]
                uav.target_position = Vector3D(
                    target_poi.position.x,
                    target_poi.position.y,
                    self.cfg_uav.survey_altitude
                )
                if uav.state == UAVState.IDLE:
                    uav.state = UAVState.FLYING_TO_POI
            elif not uav.task_path and uav.role == UAVRole.SCOUT and uav.state == UAVState.IDLE:
                uav.role = UAVRole.STANDBY
                uav.assigned_poi = None
