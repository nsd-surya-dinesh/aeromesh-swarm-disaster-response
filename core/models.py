"""
Core data models for UAV Swarm Disaster Response System
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Tuple
import numpy as np
from datetime import datetime


class UAVRole(Enum):
    """UAV operational roles"""
    SCOUT = "scout"  # Surveying PoIs
    RELAY = "relay"  # Communication relay
    STANDBY = "standby"  # Ready for deployment
    CHARGING = "charging"  # At GCS recharging
    FAILED = "failed"  # Hardware failure


class UAVState(Enum):
    """UAV operational states"""
    IDLE = "idle"
    FLYING_TO_POI = "flying_to_poi"
    SURVEYING = "surveying"
    RELAYING = "relaying"
    RETURNING = "returning"
    CHARGING = "charging"
    FAILED = "failed"


class PacketType(Enum):
    """Network packet types"""
    DATA = "data"  # Telemetry/imagery data
    CONTROL = "control"  # Command and control
    ROUTING = "routing"  # Routing protocol
    HEARTBEAT = "heartbeat"  # Keep-alive


@dataclass
class Vector3D:
    """3D vector representation"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def to_array(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z])

    def norm(self) -> float:
        return np.linalg.norm(self.to_array())

    def normalize(self) -> 'Vector3D':
        n = self.norm()
        if n > 0:
            return Vector3D(self.x/n, self.y/n, self.z/n)
        return Vector3D()

    def __add__(self, other: 'Vector3D') -> 'Vector3D':
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: 'Vector3D') -> 'Vector3D':
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> 'Vector3D':
        return Vector3D(self.x * scalar, self.y * scalar, self.z * scalar)


@dataclass
class PointOfInterest:
    """Point of Interest (disaster site location)"""
    id: int
    position: Vector3D
    priority: float = 1.0  # 1.0 = normal, higher = more urgent
    survey_duration: float = 30.0  # seconds
    surveyed: bool = False
    surveyed_by: Optional[int] = None  # UAV ID
    survey_completion_time: Optional[float] = None
    discovery_time: float = 0.0  # When it was discovered

    def distance_to(self, pos: Vector3D) -> float:
        """Calculate distance to a position"""
        return (self.position - pos).norm()


@dataclass
class UAV:
    """UAV agent"""
    id: int
    position: Vector3D = field(default_factory=Vector3D)
    velocity: Vector3D = field(default_factory=Vector3D)
    target_position: Optional[Vector3D] = None

    # Role and state
    role: UAVRole = UAVRole.STANDBY
    state: UAVState = UAVState.IDLE

    # Energy
    battery_level: float = 1.0  # 0.0 to 1.0 (ratio)
    total_energy_consumed: float = 0.0  # Wh

    # Task assignment
    assigned_poi: Optional[int] = None  # PoI ID
    task_bundle: List[int] = field(default_factory=list)  # List of PoI IDs
    task_path: List[int] = field(default_factory=list)  # Ordered task sequence

    # Communication
    connected_to_gcs: bool = True
    neighbor_uavs: List[int] = field(default_factory=list)  # IDs of neighbors in comm range
    relay_parent: Optional[int] = None  # Next hop towards GCS
    relay_children: List[int] = field(default_factory=list)  # UAVs using this as relay

    # Timing
    last_heartbeat: float = 0.0
    survey_start_time: Optional[float] = None
    charging_start_time: Optional[float] = None

    # Statistics
    distance_traveled: float = 0.0
    pois_surveyed: int = 0

    def distance_to(self, pos: Vector3D) -> float:
        """Calculate distance to a position"""
        return (self.position - pos).norm()

    def distance_to_uav(self, other: 'UAV') -> float:
        """Calculate distance to another UAV"""
        return self.distance_to(other.position)

    def is_operational(self) -> bool:
        """Check if UAV is operational"""
        return self.role != UAVRole.FAILED and self.state != UAVState.FAILED


@dataclass
class GCS:
    """Ground Control Station"""
    position: Vector3D = field(default_factory=Vector3D)
    connected_uavs: List[int] = field(default_factory=list)  # Directly connected UAV IDs

    # Mission state
    mission_start_time: float = 0.0
    total_pois_discovered: int = 0
    total_pois_surveyed: int = 0

    # Communication statistics
    packets_received: int = 0
    packets_dropped: int = 0
    total_latency: float = 0.0


@dataclass
class Packet:
    """Network packet"""
    packet_id: int
    packet_type: PacketType
    source_id: int  # Source UAV ID (or -1 for GCS)
    dest_id: int  # Destination UAV ID (or -1 for GCS)

    # Routing
    path: List[int] = field(default_factory=list)  # List of node IDs in route
    current_hop: int = 0

    # Timing
    creation_time: float = 0.0
    transmission_time: float = 0.0

    # Payload
    payload_size: float = 1024.0  # bytes
    payload: Optional[Dict] = None

    def next_hop(self) -> Optional[int]:
        """Get next hop in path"""
        if self.current_hop < len(self.path) - 1:
            return self.path[self.current_hop + 1]
        return None

    def advance_hop(self):
        """Move to next hop"""
        self.current_hop += 1

    def get_latency(self, current_time: float) -> float:
        """Calculate end-to-end latency"""
        return current_time - self.creation_time


@dataclass
class MissionState:
    """Global mission state"""
    time: float = 0.0  # Current simulation time

    # Entities
    uavs: Dict[int, UAV] = field(default_factory=dict)
    pois: Dict[int, PointOfInterest] = field(default_factory=dict)
    gcs: GCS = field(default_factory=GCS)

    # Network
    packets_in_flight: List[Packet] = field(default_factory=list)

    # Mission metrics
    mission_complete: bool = False
    mission_failed: bool = False
    failure_reason: Optional[str] = None

    # Event log
    events: List[Dict] = field(default_factory=list)

    def add_event(self, event_type: str, description: str, **kwargs):
        """Log a mission event"""
        self.events.append({
            'time': self.time,
            'type': event_type,
            'description': description,
            **kwargs
        })

    def get_operational_uavs(self) -> List[UAV]:
        """Get list of operational UAVs"""
        return [uav for uav in self.uavs.values() if uav.is_operational()]

    def get_unsurveyed_pois(self) -> List[PointOfInterest]:
        """Get list of unsurveyed PoIs"""
        return [poi for poi in self.pois.values() if not poi.surveyed]

    def get_surveyed_pois(self) -> List[PointOfInterest]:
        """Get list of surveyed PoIs"""
        return [poi for poi in self.pois.values() if poi.surveyed]

    def calculate_coverage(self) -> float:
        """Calculate mission coverage percentage"""
        if not self.pois:
            return 0.0
        return len(self.get_surveyed_pois()) / len(self.pois) * 100.0

    def is_mission_complete(self) -> bool:
        """Check if all PoIs have been surveyed"""
        return len(self.get_unsurveyed_pois()) == 0
