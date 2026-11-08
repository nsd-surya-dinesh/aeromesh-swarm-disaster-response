#!/usr/bin/env python3
"""Health Monitor Node - ROS 2 node for fleet vitality and fault recovery.

Monitors battery levels, node heartbeats, detects network partitions / dead UAVs,
and initiates autonomous relay handoffs and task reassignment."""

import rclpy
from rclpy.node import Node
from std_msgs.msg import UInt8, String, Float32
from builtin_interfaces.msg import Time as BuiltinTime


class HealthMonitorNode(Node):
    """ROS 2 node that provides fleet health monitoring as a service."""

    def __init__(self, mission_state, relay_manager):
        super().__init__('health_monitor_node')

        self.mission_state = mission_state
        self.relay_manager = relay_manager

        # QoS profiles
        qos = rclpy.qos.QoSProfile(
            reliability=rclpy.qos.QoSReliabilityPolicy.RELIABLE,
            history=rclpy.qos.QoSHistoryPolicy.KEEP_LAST,
            depth=10
        )

        # Publisher for fault events
        self.fault_pub = self.create_publisher(
            String, '/aeromesh/fault_events', qos
        )

        # Publisher for relay handoff status
        self.relay_pub = self.create_publisher(
            String, '/aeromesh/relay_handoffs', qos
        )

        # Timer for health checks (every 1 second)
        self.health_timer = self.create_timer(
            1.0, lambda: self.check_health()
        )

        # Subscribe to Gazebo clock
        self.clock_sub = self.create_subscription(
            BuiltinTime,
            '/clock',
            self.clock_callback,
            qos
        )

        self.get_logger().info('Health monitor node initialized')

    def clock_callback(self, msg):
        """Callback for Gazebo clock."""
        pass

    def check_health(self):
        """Execute health monitoring step."""
        from core.physics import PhysicsEngine

        physics_engine = PhysicsEngine()

        # Check battery thresholds for all UAVs
        for uav_id, uav in self.mission_state.uavs.items():
            # Check battery RTB thresholds
            if uav.is_operational() and uav.state not in ['RETURNING', 'CHARGING']:
                gcs_pos = self.mission_state.gcs.position
                dist_to_gcs = (uav.position - gcs_pos).norm()

                # Energy required to fly back + reserve
                return_time = dist_to_gcs / max(1.0, physics_engine.cfg_uav.cruise_speed)
                return_energy_wh = (physics_engine.cfg_uav.cruise_power * return_time) / 3600.0
                return_fraction = return_energy_wh / physics_engine.cfg_uav.battery_capacity

                rtb_safe_limit = return_fraction + physics_engine.cfg_uav.energy_reserve_ratio

                if uav.battery_level <= rtb_safe_limit:
                    # Command RTB
                    uav.state = 'RETURNING'
                    uav.target_position = gcs_pos
                    uav.task_bundle.clear()
                    uav.task_path.clear()
                    uav.assigned_poi = None

                    # Publish fault event
                    fault_msg = String()
                    fault_msg.data = f'UAV-{uav.id} initiated Return-To-Base (Battery: {uav.battery_level*100:.1f}%)'
                    self.fault_pub.publish(fault_msg)

                    self.get_logger().info(f'RTB triggered for UAV-{uav.id}')

            # Check heartbeat timeout
            current_time = self.mission_state.time
            heartbeat_timeout = 5.0  # seconds
            time_since_heartbeat = current_time - uav.last_heartbeat

            if time_since_heartbeat > heartbeat_timeout:
                # Heartbeat timeout - mark as failed
                uav.role = 'FAILED'
                uav.state = 'FAILED'
                uav.target_position = None

                # Publish fault event
                fault_msg = String()
                fault_msg.data = f'UAV-{uav.id} heartbeat timeout detected - possible failure'
                self.fault_pub.publish(fault_msg)

                self.get_logger().info(f'Heartbeat timeout for UAV-{uav.id}')

        self.get_logger().debug('Health check completed')


def main(args=None):
    rclpy.init(args=args)

    # Mission state and relay manager will be provided by bridge node
    node = HealthMonitorNode(mission_state=None, relay_manager=None)

    rclpy.spin(node)
    rclpy.shutdown()


if __name__ == '__main__':
    main()