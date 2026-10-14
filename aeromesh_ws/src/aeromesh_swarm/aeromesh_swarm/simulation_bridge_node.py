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
        # Step the physics engine
        for uav in self.mission_state.get_operational_uavs():
            self.physics_engine.update_uav_kinematics(uav, self.dt)
            self.physics_engine.update_energy(uav, self.dt)

        # Health monitoring
        self.health_monitor.check_node_vitality(self.dt)

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


def main(args=None):
    rclpy.init(args=args)
    node = SimulationBridgeNode()
    rclpy.spin(node)
    rclpy.shutdown()


if __name__ == '__main__':
    main()