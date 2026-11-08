#!/usr/bin/env python3
"""CBBA Allocator Node - ROS 2 node for decentralized task allocation.

Implements the Consensus-Based Bundle Algorithm (CBBA) for PoI task allocation
across the UAV swarm. Exposes a ROS 2 service to trigger bundle allocation."""

import rclpy
from rclpy.node import Node
from std_msgs.msg import UInt8


class CBBANode(Node):
    """ROS 2 node that provides CBBA task allocation as a service."""

    def __init__(self, mission_state):
        super().__init__('cbba_allocator_node')

        self.mission_state = mission_state

        # QoS for service
        qos = rclpy.qos.QoSProfile(
            reliability=rclpy.qos.QoSReliabilityPolicy.RELIABLE,
            history=rclpy.qos.QoSHistoryPolicy.KEEP_LAST,
            depth=10
        )

        # Create service to trigger CBBA allocation
        self.allocation_srv = self.create_service(
            UInt8,  # Empty trigger message
            '/aeromesh/service/allocate_tasks',
            self.run_allocation
        )

        self.get_logger().info('CBBA allocator node initialized')

    def run_allocation(self, request, response):
        """Execute CBBA task allocation."""
        from swarm.task_allocation import CBBATaskAllocator

        # Re-initialize allocator with current mission state
        allocator = CBBATaskAllocator(self.mission_state, max_bundle_size=4)
        allocator.run_cbba_allocation()

        self.get_logger().info('CBBA task allocation completed')
        response.data = 0  # Success
        return response


def main(args=None):
    rclpy.init(args=args)

    # Mission state will be provided by the bridge node
    # This is a standalone node for the ROS 2 stack
    node = CBBANode(mission_state=None)

    rclpy.spin(node)
    rclpy.shutdown()


if __name__ == '__main__':
    main()