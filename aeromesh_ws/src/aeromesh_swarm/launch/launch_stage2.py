#!/usr/bin/env python3
"""Launch file for Stage 2 ROS 2 deployment.

Launches all Stage 2 nodes: simulation bridge, CBBA allocator, mesh router,
and health monitor. Connects the Python simulation to Gazebo/PX4 SITL."""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='aeromesh_swarm',
            executable='simulation_bridge_node',
            name='simulation_bridge_node',
            output='screen',
            parameters=[{'use_sim_time': False}]
        ),
        Node(
            package='aeromesh_swarm',
            executable='cbba_allocator_node',
            name='cbba_allocator_node',
            output='screen',
            parameters=[{'use_sim_time': False}]
        ),
        Node(
            package='aeromesh_swarm',
            executable='mesh_router_node',
            name='mesh_router_node',
            output='screen',
            parameters=[{'use_sim_time': False}]
        ),
        Node(
            package='aeromesh_swarm',
            executable='health_monitor_node',
            name='health_monitor_node',
            output='screen',
            parameters=[{'use_sim_time': False}]
        ),
    ])


def main(argv=None, *args, **kwargs):
    import sys
    argv = sys.argv[1:] if len(sys.argv) > 1 else None
    ld = generate_launch_description()
    return ld


if __name__ == '__main__':
    ld = main()
    print(generate_launch_description())
