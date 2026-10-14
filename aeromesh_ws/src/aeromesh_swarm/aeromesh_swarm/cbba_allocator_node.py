#!/usr/bin/env python3
"""CBBA Allocator Node - ROS 2 node for decentralized task allocation.

Implements the Consensus-Based Bundle Algorithm (CBBA) for PoI task allocation
across the UAV swarm. Exposes a ROS 2 service to trigger bundle allocation."""

import rclpy
from rclpy.node import Node
from std_srvs.srv import Trigger
from aeromesh_swarm.core.models import MissionState


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
            Trigger,  # Empty trigger message
            '/aeromesh/service/cbba_run',
            self.run_allocation
        )

        self.get_logger().info('CBBA allocator node initialized')

    def run_allocation(self, request, response):
        """Execute CBBA task allocation."""
        from aeromesh_swarm.swarm.task_allocation import CBBATaskAllocator

        # Re-initialize allocator with current mission state
        allocator = CBBATaskAllocator(self.mission_state, max_bundle_size=4)
        allocator.run_cbba_allocation()

        self.get_logger().info('CBBA task allocation completed')
        response.success = True
        response.message = "CBBA allocation complete"
        return response


def main(args=None):
    rclpy.init(args=args)

    # Mission state will be provided by the bridge node
    # This is a standalone node for the ROS 2 stack
    from aeromesh_swarm.bootstrap import bootstrap_mission_state
    state = bootstrap_mission_state('S1')
    node = CBBANode(mission_state=state)

    rclpy.spin(node)
    rclpy.shutdown()


if __name__ == '__main__':
    main()