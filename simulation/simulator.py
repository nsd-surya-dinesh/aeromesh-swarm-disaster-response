"""
Mission Orchestration & Discrete-Event Simulation Engine
Synchronizes all subsystems: physics, communication, task allocation, health monitoring.
"""
import numpy as np
from typing import Dict, List, Optional
from core.models import UAV, UAVRole, UAVState, PointOfInterest, GCS, Vector3D, MissionState, Packet, PacketType
from core.physics import PhysicsEngine
from core.config import config
from comm.mesh_router import MeshRouter
from comm.steiner_relay import SteinerRelayManager
from swarm.task_allocation import CBBATaskAllocator
from swarm.path_planner import PathPlanner
from swarm.health_monitor import HealthMonitor
from swarm.dynamic_events import DynamicEventManager


class MissionSimulator:
    """Orchestrates the complete UAV swarm disaster response simulation"""

    def __init__(self):
        self.config = config
        self.mission_state = MissionState()
        self.mission_state.gcs = GCS(position=Vector3D(*config.mission.gcs_position))

        # Subsystem engines
        self.physics_engine = PhysicsEngine()
        self.mesh_router = MeshRouter(self.mission_state)
        self.relay_manager = SteinerRelayManager(self.mission_state)
        self.task_allocator = CBBATaskAllocator(self.mission_state)
        self.path_planner = PathPlanner(self.mission_state)
        self.health_monitor = HealthMonitor(self.mission_state, self.relay_manager)
        self.event_manager = DynamicEventManager(self.mission_state)

        # Timing
        self.dt = config.mission.dt
        self.next_routing_update = 0.0
        self.next_allocation_update = 0.0

    def initialize_scenario(self, num_uavs: int, poi_positions: List[Vector3D],
                            poi_priorities: Optional[List[float]] = None):
        """Initializes UAVs and Points of Interest for a scenario"""
        # Initialize UAVs at GCS
        gcs_pos = self.mission_state.gcs.position
        for i in range(num_uavs):
            uav = UAV(
                id=i,
                position=Vector3D(gcs_pos.x + np.random.uniform(-10, 10),
                                  gcs_pos.y + np.random.uniform(-10, 10),
                                  0.0),
                role=UAVRole.STANDBY,
                state=UAVState.IDLE,
                battery_level=1.0
            )
            self.mission_state.uavs[i] = uav

        # Initialize PoIs
        for i, pos in enumerate(poi_positions):
            priority = poi_priorities[i] if poi_priorities and i < len(poi_priorities) else 1.0
            poi = PointOfInterest(
                id=i,
                position=pos,
                priority=priority
            )
            self.mission_state.pois[i] = poi

        self.mission_state.gcs.total_pois_discovered = len(poi_positions)

    def step(self):
        """Executes one simulation timestep"""
        t = self.mission_state.time

        # 1. Update network topology and routing
        if t >= self.next_routing_update:
            self.mesh_router.update_network_topology()
            self.mesh_router.compute_routing_tables()
            self.next_routing_update = t + config.rf.routing_update_interval

        # 2. Run CBBA task allocation
        if t >= self.next_allocation_update:
            self.task_allocator.run_cbba_allocation()
            self.next_allocation_update = t + 10.0  # Re-allocate every 10s

        # 3. Update UAV survey states
        self._update_survey_states()

        # 4. Update physics (position, velocity, energy)
        for uav in self.mission_state.get_operational_uavs():
            self.physics_engine.update_uav_kinematics(uav, self.dt)
            self.physics_engine.update_energy(uav, self.dt)

        # 5. Health monitoring (battery checks, RTB, relay handoffs)
        self.health_monitor.check_node_vitality(self.dt)

        # 6. Process packet forwarding
        self.mesh_router.process_packet_forwarding(self.dt)

        # 7. Generate telemetry packets from scouts
        self._generate_telemetry_packets()

        # 8. Check mission completion
        if self.mission_state.is_mission_complete():
            self.mission_state.mission_complete = True

        # Advance time
        self.mission_state.time += self.dt

    def _update_survey_states(self):
        """Updates PoI survey progress for UAVs in SURVEYING state"""
        for uav in self.mission_state.get_operational_uavs():
            if uav.assigned_poi is None:
                continue

            poi = self.mission_state.pois.get(uav.assigned_poi)
            if poi is None or poi.surveyed:
                # PoI already surveyed, move to next
                self._advance_uav_to_next_task(uav)
                continue

            # Check if UAV has reached PoI position
            target_2d = Vector3D(poi.position.x, poi.position.y, config.uav.survey_altitude)
            dist_to_poi = (uav.position - target_2d).norm()

            if dist_to_poi < 10.0 and uav.state != UAVState.SURVEYING:
                # Start surveying
                uav.state = UAVState.SURVEYING
                uav.survey_start_time = self.mission_state.time
                uav.target_position = target_2d  # Hold position

            elif uav.state == UAVState.SURVEYING:
                # Continue surveying
                elapsed = self.mission_state.time - uav.survey_start_time
                if elapsed >= poi.survey_duration:
                    # Survey complete
                    poi.surveyed = True
                    poi.surveyed_by = uav.id
                    poi.survey_completion_time = self.mission_state.time
                    uav.pois_surveyed += 1
                    self.mission_state.gcs.total_pois_surveyed += 1

                    self.mission_state.add_event(
                        'poi_surveyed',
                        f'[SUCCESS] PoI-{poi.id} surveyed by UAV-{uav.id}',
                        poi_id=poi.id,
                        uav_id=uav.id
                    )

                    # Move to next task
                    self._advance_uav_to_next_task(uav)

    def _advance_uav_to_next_task(self, uav: UAV):
        """Advances UAV to the next task in its bundle"""
        if uav.assigned_poi in uav.task_path:
            uav.task_path.remove(uav.assigned_poi)
        if uav.assigned_poi in uav.task_bundle:
            uav.task_bundle.remove(uav.assigned_poi)

        if uav.task_path:
            # Move to next PoI
            next_poi_id = uav.task_path[0]
            uav.assigned_poi = next_poi_id
            next_poi = self.mission_state.pois[next_poi_id]
            uav.target_position = Vector3D(
                next_poi.position.x,
                next_poi.position.y,
                config.uav.survey_altitude
            )
            uav.state = UAVState.FLYING_TO_POI
        else:
            # No more tasks
            uav.assigned_poi = None
            uav.state = UAVState.IDLE
            uav.role = UAVRole.STANDBY
            uav.target_position = None

    def _generate_telemetry_packets(self):
        """Generates periodic telemetry packets from surveying UAVs to GCS"""
        for uav in self.mission_state.get_operational_uavs():
            if uav.state == UAVState.SURVEYING and uav.connected_to_gcs:
                # Send telemetry packet every 5 seconds
                if int(self.mission_state.time) % 5 == 0:
                    packet = Packet(
                        packet_id=self.mesh_router.packets_sent,
                        packet_type=PacketType.DATA,
                        source_id=uav.id,
                        dest_id=-1,  # GCS
                        payload_size=2048.0,  # 2KB telemetry + imagery
                        payload={'uav_id': uav.id, 'poi_id': uav.assigned_poi, 'battery': uav.battery_level}
                    )
                    self.mesh_router.send_packet(packet)

    def run_simulation(self, max_time: Optional[float] = None):
        """Runs the full simulation until completion or timeout"""
        if max_time is None:
            max_time = config.mission.max_mission_time

        print(f">> Starting mission simulation...")
        print(f"   UAVs: {len(self.mission_state.uavs)}, PoIs: {len(self.mission_state.pois)}")

        last_logged_time = -1
        while self.mission_state.time < max_time:
            self.step()

            # Progress indicator (once per 30s)
            curr_sec = int(self.mission_state.time)
            if curr_sec % 30 == 0 and curr_sec != last_logged_time:
                last_logged_time = curr_sec
                coverage = self.mission_state.calculate_coverage()
                print(f"   t={self.mission_state.time:.0f}s | Coverage: {coverage:.1f}%")

            if self.mission_state.mission_complete:
                print(f"[+] Mission completed at t={self.mission_state.time:.1f}s")
                break

        return self.get_final_report()

    def get_final_report(self) -> Dict:
        """Generates comprehensive mission report"""
        coverage = self.mission_state.calculate_coverage()
        network_stats = self.mesh_router.get_network_stats()

        total_distance = sum(uav.distance_traveled for uav in self.mission_state.uavs.values())
        total_energy = sum(uav.total_energy_consumed for uav in self.mission_state.uavs.values())

        return {
            'mission_time': self.mission_state.time,
            'coverage_percent': coverage,
            'pois_surveyed': len(self.mission_state.get_surveyed_pois()),
            'pois_total': len(self.mission_state.pois),
            'mission_complete': self.mission_state.mission_complete,
            'network_pdr': network_stats['pdr'],
            'network_avg_latency': network_stats['avg_latency'],
            'network_avg_hops': network_stats['avg_hops'],
            'total_distance_km': total_distance / 1000.0,
            'total_energy_wh': total_energy,
            'num_events': len(self.mission_state.events)
        }
