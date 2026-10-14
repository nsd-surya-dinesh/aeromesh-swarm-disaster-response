#!/usr/bin/env python3
"""Simulation Bridge Node - Bridges Python UAV swarm simulation to ROS 2 topics.

This node connects the AeroMesh-Swarm Python simulation state to ROS 2,
enabling integration with Gazebo/PX4 SITL for Stage 2 of the PUSHPAK Grand Challenge.

Published Topics:
  - /aeromesh/uav_{id}/pose (geometry_msgs/PoseStamped) - UAV 3D pose
  - /aeromesh/uav_{id}/battery_state (sensor_msgs/BatteryState) - Battery SoC
  - /aeromesh/uav_{id}/status (custom) - UAV role and state
  - /aeromesh/network/topology (custom MeshTopology) - Network graph
  - /aeromesh/network/link_quality (custom LinkQuality) - Link quality stats

Services:
  - /aeromesh/service/allocate_tasks - Trigger CBBA task allocation
  - /aeromesh/service/inject_emergency_poi - Inject dynamic high-priority PoI
  - /aeromesh/service/get_mission_metrics - Return mission performance metrics

Subscribed Topics:
  - /clock (std_msgs/Time) - Gazebo simulation time sync
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy, QoSDurabilityPolicy
from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import BatteryState
from std_msgs.msg import Float32, String, Bool
from std_srvs.srv import Trigger
from rosgraph_msgs.msg import Clock
from rosgraph_msgs.msg import Clock
import numpy as np

from aeromesh_swarm.core.models import UAV, UAVRole, UAVState, PointOfInterest, MissionState, Vector3D, Packet, PacketType
from aeromesh_swarm.core.physics import PhysicsEngine
from aeromesh_swarm.comm.mesh_router import MeshRouter
from aeromesh_swarm.swarm.task_allocation import CBBATaskAllocator
from aeromesh_swarm.swarm.path_planner import PathPlanner
from aeromesh_swarm.swarm.health_monitor import HealthMonitor
from aeromesh_swarm.comm.steiner_relay import SteinerRelayManager


# Data muling constants
RELAY_POINT_X, RELAY_POINT_Y = 0.0, 200.0
SURVEY_GROUND_ALT = 3.0
HOLD_AFTER_SURVEY_SEC = 5.0
DELIVERY_TRANSFER_SEC = 3.0
PAYLOAD_MB_PER_POI = 50.0


class SimulationBridgeNode(Node):
    """ROS 2 node that bridges Python swarm simulation state to ROS 2 topics."""

    def __init__(self):
        super().__init__('simulation_bridge_node')

        # Simulation state - use the existing MissionState from the Python simulation
        from aeromesh_swarm.bootstrap import bootstrap_mission_state
        self.mission_state = bootstrap_mission_state('S1')
        self.physics_engine = PhysicsEngine()
        self.mesh_router = MeshRouter(self.mission_state)
        self.task_allocator = CBBATaskAllocator(self.mission_state)
        self.path_planner = PathPlanner(self.mission_state)
        # Create relay manager BEFORE using it in HealthMonitor
        try:
            from aeromesh_swarm.comm.steiner_relay import SteinerRelayManager
            self.relay_manager = SteinerRelayManager(self.mission_state)
        except Exception as e:
            self.get_logger().warn(f'SteinerRelayManager not available: {e}')
            self.relay_manager = None

        self.health_monitor = HealthMonitor(self.mission_state, self.relay_manager)
        self.relay_manager = SteinerRelayManager(self.mission_state)

        # Timer for simulation stepping
        self.dt = 0.1  # 10Hz simulation step
        self.simulation_timer = self.create_timer(self.dt, self.simulation_step)

        # QoS profiles
        self.qos_publish = QoSProfile(
            reliability=QoSReliabilityPolicy.RELIABLE,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10
        )

        self.qos_best_effort = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=5
        )

        # Publisher counters for UAV IDs
        self.uav_publishers = {}

        # Initialize publishers
        self.initialize_publishers()

        # Create services
        self.allocate_tasks_srv = self.create_service(
            Trigger,  # Simple trigger msg
            '/aeromesh/service/allocate_tasks',
            self.handle_allocate_tasks
        )

        self.inject_epoi_srv = self.create_service(
            Trigger,
            '/aeromesh/service/inject_emergency_poi',
            self.handle_inject_emergency_poi
        )

        self.get_metrics_srv = self.create_service(
            Trigger,
            '/aeromesh/service/get_mission_metrics',
            self.handle_get_mission_metrics
        )

        # Subscribe to Gazebo clock
        self.clock_sub = self.create_subscription(
            Clock,
            '/clock',
            self.clock_callback,
            self.qos_best_effort
        )

        # Initialize UAV publishers
        self.update_uav_publishers()

        self.get_logger().info('Simulation bridge node initialized')

    def initialize_publishers(self):
        """Initialize all UAV publishers."""
        # Get number of UAVs from mission state
        num_uavs = len(self.mission_state.uavs)

        for uav_id in range(num_uavs):
            # Create pose publisher per UAV
            pose_topic = f'/aeromesh/uav_{uav_id}/pose'
            self.uav_publishers[uav_id] = {
                'pose': self.create_publisher(PoseStamped, pose_topic, self.qos_publish),
                'battery': self.create_publisher(
                    BatteryState, f'/aeromesh/uav_{uav_id}/battery_state', self.qos_publish
                ),
                'payload': self.create_publisher(Float32, f'/aeromesh/uav_{uav_id}/payload_mb', self.qos_publish),
                'status': self.create_publisher(
                    String, f'/aeromesh/uav_{uav_id}/status', self.qos_publish
                ),
            }

    def update_uav_publishers(self):
        """Update publisher count based on current UAVs."""
        # Recreate publishers for any new UAVs
        current_ids = set(self.mission_state.uavs.keys())
        for uav_id in current_ids:
            if uav_id not in self.uav_publishers:
                pose_topic = f'/aeromesh/uav_{uav_id}/pose'
                self.uav_publishers[uav_id] = {
                    'pose': self.create_publisher(PoseStamped, pose_topic, self.qos_publish),
                    'battery': self.create_publisher(
                        BatteryState, f'/aeromesh/uav_{uav_id}/battery_state', self.qos_publish
                    ),
                    'status': self.create_publisher(
                        String, f'/aeromesh/uav_{uav_id}/status', self.qos_publish
                    ),
                }

    def clock_callback(self, msg):
        """Callback for Gazebo clock - advances simulation time."""
        # Update mission time from clock
        current_time = msg.data.sec + msg.data.nanosec / 1e9
        self.mission_state.time = current_time

    def simulation_step(self):
        """Execute one simulation timestep and publish UAV states."""
        # Advance simulation time (needed for delivery timers)
        self.mission_state.time += self.dt

        # Health monitoring first
        self.health_monitor.check_node_vitality(self.dt)

        # Data-muling state machine — advance each UAV
        for uav in self.mission_state.uavs.values():
            try:
                self._advance_uav_state_machine(uav, self.dt)
            except Exception as e:
                self.get_logger().error(f'State machine error UAV {uav.id}: {e}')

        # Update UAV publishers
        self.publish_uav_states()

    def publish_uav_states(self):
        """Publish current UAV states as ROS 2 messages."""
        for uav_id, uav in self.mission_state.uavs.items():
            # Publish pose
            pose_msg = PoseStamped()
            pose_msg.header.stamp = self.get_clock().now().to_msg()
            pose_msg.header.frame_id = 'world'
            pose_msg.pose.position.x = uav.position.x
            pose_msg.pose.position.y = uav.position.y
            pose_msg.pose.position.z = uav.position.z
            pose_msg.pose.orientation.x = 0.0
            pose_msg.pose.orientation.y = 0.0
            pose_msg.pose.orientation.z = 0.0
            pose_msg.pose.orientation.w = 1.0
            self.uav_publishers[uav_id]['pose'].publish(pose_msg)

            # Publish battery state
            battery_msg = BatteryState()
            battery_msg.voltage = uav.battery_level * 28.0  # Scale: 0.0->0V, 1.0->28V
            battery_msg.current = 0.0
            battery_msg.charge = uav.battery_level * 100.0  # Percentage
            battery_msg.capacity = 200.0  # Wh
            battery_msg.power_supply_status = (
                battery_msg.POWER_SUPPLY_STATUS_CHARGING
                if uav.state == UAVState.CHARGING
                else battery_msg.POWER_SUPPLY_STATUS_DISCHARGING
            )
            self.uav_publishers[uav_id]['battery'].publish(battery_msg)

            # Publish status
            status_msg = String()
            status_msg.data = f'{uav.role.value},{uav.state.value}'
            # Publish payload (data muling)
            payload_msg = Float32()
            payload_msg.data = float(getattr(uav, 'payload_data_mb', 0.0))
            self.uav_publishers[uav_id]['payload'].publish(payload_msg)

            self.uav_publishers[uav_id]['status'].publish(status_msg)

    def handle_allocate_tasks(self, request, response):
        """Handle CBBA task allocation service request."""
        self.task_allocator.run_cbba_allocation()
        response.data = 0  # Success
        return response

    def handle_inject_emergency_poi(self, request, response):
        """Handle emergency POI injection service request."""
        import random
        from aeromesh_swarm.core.models import Vector3D

        # Generate random position within mission area
        x = random.uniform(-2000.0 / 2, 2000.0 / 2)
        y = random.uniform(-2000.0 / 2, 2000.0 / 2)
        position = Vector3D(x, y, 0.0)

        # Inject with high priority
        priority = random.uniform(5.0, 8.0)
        new_poi = self.mission_state.event_manager.inject_high_priority_poi(position, priority)

        response.data = 0  # Success
        return response

    def handle_get_mission_metrics(self, request, response):
        """Handle mission metrics service request."""
        from aeromesh_swarm.core.metrics import MetricsEngine

        metrics_engine = MetricsEngine(self.mission_state)
        metrics_summary = metrics_engine.generate_full_metrics_summary()

        # Return as string summary
        msg = f"Coverage: {metrics_summary['coverage_percentage']:.1f}%\n"
        msg += f"PDR: {metrics_summary['packet_delivery_ratio_pdr']:.1f}%\n"
        msg += f"Latency: {metrics_summary['avg_end_to_end_latency_ms']:.1f} ms\n"
        msg += f"Swarm Survival: {metrics_summary['swarm_survival_rate']:.1f}%\n"
        msg += f"POIs Surveyed: {metrics_summary['pois_surveyed']}/{metrics_summary['total_pois']}\n"
        msg += f"Mission Time: {metrics_summary['mission_duration_s']:.1f} s"

        response.data = msg
        return response


    def _advance_uav_state_machine(self, uav, dt):
        """Advance one UAV through the data-muling lifecycle."""
        from aeromesh_swarm.core.models import UAVState

        # Dynamic attributes (no dataclass edit needed)
        if not hasattr(uav, 'payload_data_mb'):
            uav.payload_data_mb = 0.0
            uav.survey_complete = False
            uav.current_target_poi = 0
            uav.survey_start_time = 0.0
            uav.delivery_start_time = 0.0

        s = uav.state

        # IDLE → FLYING_TO_POI
        if s == UAVState.IDLE:
            uav.current_target_poi = self._next_unsurveyed_poi()
            if uav.current_target_poi is not None:
                uav.state = UAVState.FLYING_TO_POI

        # FLYING_TO_POI → SURVEYING
        elif s == UAVState.FLYING_TO_POI:
            if uav.current_target_poi is None:
                uav.state = UAVState.IDLE
            else:
                target = self.mission_state.pois.get(uav.current_target_poi)
                if target is None:
                    uav.state = UAVState.IDLE
                else:
                    # Ascend to cruise altitude if needed
                    if uav.position.z < 30.0:
                        uav.position.z = min(30.0, uav.position.z + 3.0 * dt)
                    # Move horizontally toward the PoI
                    dx = target.position.x - uav.position.x
                    dy = target.position.y - uav.position.y
                    d = (dx*dx + dy*dy) ** 0.5
                    if d < 10.0:
                        uav.state = UAVState.SURVEYING
                        uav.survey_start_time = self.mission_state.time
                        uav.survey_elapsed = 0.0
                        self.get_logger().info(
                            f'UAV {uav.id}: reached PoI {uav.current_target_poi}, surveying'
                        )
                    else:
                        spd = 15.0 * dt
                        uav.position.x += (dx / d) * spd
                        uav.position.y += (dy / d) * spd

        # SURVEYING → HOLDING_AT_SURVEY (descend + dwell)
        elif s == UAVState.SURVEYING:
            if not hasattr(uav, 'survey_elapsed'):
                uav.survey_elapsed = 0.0
            # Try to descend (physics engine may override — that's OK)
            if uav.position.z > SURVEY_GROUND_ALT:
                uav.position.z = max(SURVEY_GROUND_ALT,
                                     uav.position.z - 2.0 * dt)
            # Increment timer UNCONDITIONALLY — no altitude dependency
            uav.survey_elapsed += dt
            if uav.survey_elapsed >= HOLD_AFTER_SURVEY_SEC:
                    uav.state = UAVState.HOLDING_AT_SURVEY
                    uav.survey_complete = True
                    uav.payload_data_mb = PAYLOAD_MB_PER_POI
                    if uav.current_target_poi in self.mission_state.pois:
                        self.mission_state.pois[uav.current_target_poi].surveyed = True
                    self.get_logger().info(
                        f'UAV {uav.id}: survey complete at PoI '
                        f'{uav.current_target_poi}, payload = '
                        f'{uav.payload_data_mb} MB'
                    )

        # HOLDING_AT_SURVEY → FLYING_TO_RELAY
        elif s == UAVState.HOLDING_AT_SURVEY:
            if uav.payload_data_mb > 0:
                uav.state = UAVState.FLYING_TO_RELAY
                self.get_logger().info(f'UAV {uav.id}: heading to relay')

        # FLYING_TO_RELAY → DELIVERING_DATA
        elif s == UAVState.FLYING_TO_RELAY:
            if uav.position.z < 30.0:
                uav.position.z = min(30.0, uav.position.z + 3.0 * dt)
            else:
                dx = RELAY_POINT_X - uav.position.x
                dy = RELAY_POINT_Y - uav.position.y
                dist = (dx*dx + dy*dy) ** 0.5
                if dist < 10.0:
                    uav.state = UAVState.DELIVERING_DATA
                    uav.delivery_start_time = self.mission_state.time
                else:
                    spd = 15.0 * dt
                    uav.position.x += (dx/dist) * spd
                    uav.position.y += (dy/dist) * spd

        # DELIVERING_DATA → FLYING_TO_POI (next task)
        elif s == UAVState.DELIVERING_DATA:
            elapsed = self.mission_state.time - uav.delivery_start_time
            if elapsed >= DELIVERY_TRANSFER_SEC:
                self.get_logger().info(
                    f'UAV {uav.id}: delivered {uav.payload_data_mb} MB to relay'
                )
                uav.payload_data_mb = 0.0
                uav.survey_complete = False
                nxt = self._next_unsurveyed_poi()
                if nxt is not None:
                    uav.current_target_poi = nxt
                    uav.state = UAVState.FLYING_TO_POI
                else:
                    uav.state = UAVState.IDLE

    def _next_unsurveyed_poi(self):
        """Return the first unclaimed + unsurveyed PoI, or None."""
        # Collect PoIs already claimed by other UAVs
        claimed = set()
        for other in self.mission_state.uavs.values():
            if getattr(other, 'current_target_poi', None) is not None:
                claimed.add(other.current_target_poi)
        for poi_id, poi in self.mission_state.pois.items():
            if getattr(poi, 'surveyed', False):
                continue
            if poi_id in claimed:
                continue
            return poi_id
        return None


def main(args=None):
    rclpy.init(args=args)
    node = SimulationBridgeNode()
    rclpy.spin(node)
    rclpy.shutdown()


if __name__ == '__main__':
    main()
