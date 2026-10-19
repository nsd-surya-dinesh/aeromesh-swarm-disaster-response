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
        (os.path.join('share', 'ament_index', 'resource_index', 'packages'),
         ['resource/' + package_name]),
        (os.path.join('share', package_name), ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
    ],
    install_requires=['setuptools', 'networkx', 'numpy', 'scipy'],
    zip_safe=True,
    maintainer='Ganga Naga Surya Dinesh',
    maintainer_email='nagasuryadinesh@gmail.com',
    description='AeroMesh-Swarm Stage 2 ROS 2 nodes',
    license='Proprietary',
    entry_points={
        'console_scripts': [
            'simulation_bridge_node = aeromesh_swarm.simulation_bridge_node:main',
            'cbba_allocator_node    = aeromesh_swarm.cbba_allocator_node:main',
            'mesh_router_node       = aeromesh_swarm.mesh_router_node:main',
            'health_monitor_node    = aeromesh_swarm.health_monitor_node:main',
        ],
    },
)


# --- Post-install: force-generate ament_prefix_path hook ---
# Workaround for colcon not generating this on some Humble setups.
import os
from setuptools.command.install import install as _install
from setuptools.command.develop import develop as _develop

def _write_hook():
    prefix = os.path.abspath(os.path.dirname(__file__))
    hook_dir = os.path.join(prefix, 'share', 'aeromesh_swarm', 'hook')
    os.makedirs(hook_dir, exist_ok=True)
    with open(os.path.join(hook_dir, 'ament_prefix_path.sh'), 'w') as f:
        f.write('ament_prepend_unique_value() { if [ "${1#*$2}" = "$1" ]; then export $1="$2${1:+${1:+:}$1}"; fi; }\n')
        f.write(f'ament_prepend_unique_value AMENT_PREFIX_PATH "{os.path.abspath(prefix)}"\n')
    with open(os.path.join(hook_dir, 'ament_prefix_path.dsv'), 'w') as f:
        f.write(f'prepend-non-duplicate;AMENT_PREFIX_PATH;{os.path.abspath(prefix)}\n')

class PostInstall(_install):
    def run(self):
        super().run()
        _write_hook()

class PostDevelop(_develop):
    def run(self):
        super().run()
        _write_hook()
