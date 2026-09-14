"""
Swarm Health Monitor & Self-Healing Fault Recovery Engine
Monitors battery levels, node heartbeats, detects network partitions / dead UAVs,
and initiates autonomous relay handoffs and task reassignment.
"""
from typing import Dict, List, Optional
from core.models import UAV, UAVRole, UAVState, MissionState, Vector3D
from core.config import config
from comm.steiner_relay import SteinerRelayManager


class HealthMonitor:
    """Monitors fleet vitality and executes autonomous self-healing recovery actions"""

    def __init__(self, mission_state: MissionState, relay_manager: SteinerRelayManager):
        self.mission_state = mission_state
        self.relay_manager = relay_manager
        self.cfg_uav = config.uav
        self.cfg_swarm = config.swarm

    def check_battery_thresholds(self, uav: UAV):
        """
        Evaluates battery state. If below safe return margin, commands Return-To-Base (RTB).
        If UAV is a critical relay, triggers seamless relay replacement before leaving.
        """
        if not uav.is_operational() or uav.state in [UAVState.RETURNING, UAVState.CHARGING]:
            return

        gcs_pos = self.mission_state.gcs.position
        dist_to_gcs = (uav.position - gcs_pos).norm()

        # Energy required to fly back + reserve
        return_time = dist_to_gcs / max(1.0, self.cfg_uav.cruise_speed)
        return_energy_wh = (self.cfg_uav.cruise_power * return_time) / 3600.0
        return_fraction = return_energy_wh / self.cfg_uav.battery_capacity

        rtb_safe_limit = return_fraction + self.cfg_uav.energy_reserve_ratio

        if uav.battery_level <= rtb_safe_limit:
            # If UAV was a relay, initiate handoff before departing
            if uav.role == UAVRole.RELAY:
                self._handle_relay_departure(uav)

            # Command RTB
            uav.state = UAVState.RETURNING
            uav.target_position = Vector3D(gcs_pos.x, gcs_pos.y, 10.0)
            uav.task_bundle.clear()
            uav.task_path.clear()
            uav.assigned_poi = None

            self.mission_state.add_event(
                'battery_rtb',
                f'UAV-{uav.id} initiated Return-To-Base (Battery: {uav.battery_level*100:.1f}%)'
            )

    def _handle_relay_departure(self, relay_uav: UAV):
        """Finds a replacement UAV to take over the relay position"""
        candidate_id = self.relay_manager.find_optimal_relay_candidate(relay_uav.id)
        if candidate_id is not None:
            replacement = self.mission_state.uavs[candidate_id]
            replacement.role = UAVRole.RELAY
            replacement.state = UAVState.RELAYING
            replacement.target_position = Vector3D(
                relay_uav.position.x,
                relay_uav.position.y,
                relay_uav.position.z
            )
            replacement.task_bundle.clear()
            replacement.task_path.clear()
            replacement.assigned_poi = None

            self.mission_state.add_event(
                'relay_handoff',
                f'Seamless relay handoff: UAV-{replacement.id} replacing UAV-{relay_uav.id}'
            )

    def check_node_vitality(self, dt: float):
        """
        Scans all UAVs for heartbeat timeouts and battery levels.
        Triggers network healing if an active relay has unexpectedly failed.
        """
        current_time = self.mission_state.time

        for uav_id, uav in list(self.mission_state.uavs.items()):
            if not uav.is_operational():
                continue

            # Update heartbeat timestamp
            uav.last_heartbeat = current_time

            # Check battery
            self.check_battery_thresholds(uav)

            # Check if reached GCS for charging
            if uav.state == UAVState.RETURNING:
                dist_to_gcs = (uav.position - self.mission_state.gcs.position).norm()
                if dist_to_gcs < 15.0:
                    uav.state = UAVState.CHARGING
                    uav.role = UAVRole.CHARGING
                    uav.charging_start_time = current_time
                    uav.target_position = None
                    self.mission_state.add_event(
                        'charging_started',
                        f'UAV-{uav.id} landed at GCS charging pad'
                    )

            # Check if finished charging
            elif uav.state == UAVState.CHARGING and uav.battery_level >= 0.98:
                uav.state = UAVState.IDLE
                uav.role = UAVRole.STANDBY
                self.mission_state.add_event(
                    'charging_completed',
                    f'UAV-{uav.id} fully recharged and returned to STANDBY'
                )

    def handle_unexpected_node_failure(self, failed_uav_id: int):
        """
        Simulates unexpected hardware fault or crash of a UAV.
        Executes immediate swarm self-healing.
        """
        if failed_uav_id not in self.mission_state.uavs:
            return

        uav = self.mission_state.uavs[failed_uav_id]
        uav.role = UAVRole.FAILED
        uav.state = UAVState.FAILED
        uav.target_position = None

        self.mission_state.add_event(
            'hardware_failure',
            f'CRITICAL: UAV-{failed_uav_id} experienced catastrophic failure!'
        )

        # If it was a relay, trigger immediate emergency healing
        candidate_id = self.relay_manager.find_optimal_relay_candidate(failed_uav_id)
        if candidate_id is not None:
            replacement = self.mission_state.uavs[candidate_id]
            replacement.role = UAVRole.RELAY
            replacement.state = UAVState.RELAYING
            replacement.target_position = Vector3D(
                uav.position.x,
                uav.position.y,
                uav.position.z
            )
            replacement.task_bundle.clear()
            replacement.task_path.clear()
            replacement.assigned_poi = None

            self.mission_state.add_event(
                'emergency_healing',
                f'Self-healing triggered: UAV-{replacement.id} dispatched to replace failed UAV-{failed_uav_id}'
            )
