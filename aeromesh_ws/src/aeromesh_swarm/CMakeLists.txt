cmake_minimum_required(VERSION 0.5.0)
project(aeromesh_swarm VERSION 1.0.0 LANGUAGES CXX C Python)

# Default build type is RelWithDebInfo unless overridden in CMakeLists.txt
find_package(ament_cmake REQUIRED)
find_package(rclpy REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(std_msgs REQUIRED)

ament_package()