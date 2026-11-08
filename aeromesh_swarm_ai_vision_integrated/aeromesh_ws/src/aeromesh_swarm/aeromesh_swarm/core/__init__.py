"""
Core package initialization
"""
from aeromesh_swarm.core.models import (
    UAV, UAVRole, UAVState, PointOfInterest, GCS, Packet, PacketType,
    Vector3D, MissionState
)
from aeromesh_swarm.core.config import config, Config
from aeromesh_swarm.core.physics import PhysicsEngine

__all__ = [
    'UAV', 'UAVRole', 'UAVState', 'PointOfInterest', 'GCS', 'Packet', 'PacketType',
    'Vector3D', 'MissionState', 'config', 'Config', 'PhysicsEngine'
]
