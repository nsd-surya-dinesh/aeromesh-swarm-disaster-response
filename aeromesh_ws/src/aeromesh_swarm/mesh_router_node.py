#!/usr/bin/env python3
"""Mesh Router Node - ROS 2 node for dynamic multi-hop routing.

Implements ETX-weighted Dijkstra multi-hop routing for the UAV mesh network.
Handles topology updates, packet forwarding, and link quality monitoring."""

import rclpy
from rclpy.node import Node
from std_msgs.msg import UInt8, Float32, UInt8MultiArray
from builtin_interfaces.msg import Time as BuiltinTime
import numpy as np

from core.models import UAV, GCS, Packet, PacketType, MissionState, Vector3D
from comm.mesh_router import MeshRouter


class MeshRouterNode(Node):
    """ROS 2 node that provides dynamic mesh routing as a service."""

    def __init__(self, mission_state):
        super().__init__('mesh_router_node')

        self.mission_state = mission_state

        # QoS profiles
        qos_publish = rclpy.qos.QoSProfile(
            reliability=rclpy.qos.QoSReliabilityPolicy.RELIABLE,
            history=rclpy.qos.QoSHistoryPolicy.KEEP_LAST,
            depth=10
        )

        qos_best_effort = rclpy.qos.QoSProfile(
            reliability=rclpy.qos.QoSReliabilityPolicy.BEST_EFFORT,
            history=rclpy.qos.QoSHistoryPolicy.KEEP_LAST,
            depth=5
        )

        # Publisher for network topology
        self.topology_pub = self.create_publisher(
            UInt8MultiArray, '/aeromesh/network/topology', qos_publish
        )

        # Publisher for link quality
        self.link_quality_pub = self.create_publisher(
            Float32, '/aeromesh/network/link_quality', qos_publish
        )

        # Timer for periodic topology update (every 5 seconds)
        self.topology_timer = self.create_timer(
            5.0, self.update_topology
        )

        # Subscribe to Gazebo clock
        self.clock_sub = self.create_subscription(
            BuiltinTime,
            '/clock',
            self.clock_callback,
            qos_best_effort
        )

        self.get_logger().info('Mesh router node initialized')

    def clock_callback(self, msg):
        """Callback for Gazebo clock."""
        pass  # Time tracking

    def update_topology(self):
        """Update network topology and publish metrics."""
        from core.config import config

        # Rebuild topology using current UAV positions
        mesh_router = MeshRouter(self.mission_state)
        mesh_router.update_network_topology()

        # Get network stats
        stats = mesh_router.get_network_stats()

        # Publish topology (node IDs + edge src/dst)
        topo_msg = UInt8MultiArray()
        topo_msg.data = [
            list(mesh_router.network_graph.nodes()),
        ]
        self.topology_pub.publish(topo_msg)

        # Publish average link quality (PDR)
        if stats['pdr'] > 0:
            quality_msg = Float32()
            quality_msg.data = float(stats['pdr'])
            self.link_quality_pub.publish(quality_msg)

        self.get_logger().info(
            f'Topology updated: {stats["num_nodes"]} nodes, '
            f'{stats["num_edges"]} edges, PDR: {stats["pdr"]:.2f}'
        )


def main(args=None):
    rclpy.init(args=args)

    # Mission state will be provided by the bridge node
    node = MeshRouterNode(mission_state=None)

    rclpy.spin(node)
    rclpy.shutdown()


if __name__ == '__main__':
    main()