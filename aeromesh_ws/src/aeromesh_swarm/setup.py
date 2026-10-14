from setuptools import setup
import os
from glob import glob

package_name = 'aeromesh_swarm'

setup(
    name=package_name,
    version='0.1.0',
    packages=[
        package_name,
        package_name + '.core',
        package_name + '.swarm',
        package_name + '.comm',
    ],
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
         glob('launch/*.py')),
    ],
    install_requires=['setuptools', 'networkx', 'numpy', 'scipy', 'matplotlib', 'pydantic', 'tqdm'],
    zip_safe=True,
    maintainer='Ganta Naga Surya Dinesh',
    maintainer_email='nagasuryadinesh@gmail.com',
    description='AeroMesh-Swarm Stage 2 ROS 2 nodes for PUSHPAK Grand Challenge 2026',
    license='Proprietary',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'simulation_bridge_node = aeromesh_swarm.simulation_bridge_node:main',
            'cbba_allocator_node    = aeromesh_swarm.cbba_allocator_node:main',
            'mesh_router_node       = aeromesh_swarm.mesh_router_node:main',
            'health_monitor_node    = aeromesh_swarm.health_monitor_node:main',
        ],
    },
)
