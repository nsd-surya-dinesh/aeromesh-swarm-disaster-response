"""
Core configuration parameters for UAV Swarm Disaster Response System
"""
from dataclasses import dataclass
from typing import Dict, Any
import numpy as np


@dataclass
class MissionConfig:
    """Mission-level parameters"""
    # Mission area
    area_width: float = 2000.0  # meters
    area_height: float = 2000.0  # meters
    area_depth: float = 300.0  # max altitude meters

    # Time parameters
    dt: float = 0.1  # simulation timestep (seconds)
    max_mission_time: float = 1800.0  # 30 minutes

    # GCS position
    gcs_position: tuple = (0.0, 0.0, 0.0)  # (x, y, z) meters


@dataclass
class UAVConfig:
    """UAV physical and operational parameters"""
    # Physical properties
    mass: float = 2.5  # kg
    max_speed: float = 15.0  # m/s
    cruise_speed: float = 10.0  # m/s
    max_acceleration: float = 3.0  # m/s^2

    # Battery and energy
    battery_capacity: float = 5000.0  # Wh (Watt-hours)
    hover_power: float = 150.0  # Watts
    cruise_power: float = 200.0  # Watts
    max_power: float = 350.0  # Watts

    # Energy reserve and safety margins
    energy_reserve_ratio: float = 0.15  # 15% reserve
    rtb_threshold_ratio: float = 0.25  # Return-to-base at 25%

    # Communication
    tx_power: float = 1.0  # Watts (30 dBm)
    rx_sensitivity: float = -90.0  # dBm
    antenna_gain: float = 3.0  # dBi

    # Sensing and survey
    camera_fov: float = 60.0  # degrees
    survey_altitude: float = 50.0  # meters
    survey_duration: float = 30.0  # seconds per PoI


@dataclass
class RFConfig:
    """Radio Frequency and communication parameters"""
    # RF propagation
    frequency: float = 2.4e9  # Hz (2.4 GHz)
    bandwidth: float = 20e6  # Hz (20 MHz)
    noise_floor: float = -100.0  # dBm

    # Path loss model parameters (ITU-R P.1411)
    path_loss_exponent: float = 2.5  # Free space = 2, urban = 3-4
    shadowing_std: float = 4.0  # dB (log-normal shadowing)

    # LoS probability model parameters
    los_param_a: float = 4.88
    los_param_b: float = 0.43

    # Link quality thresholds
    min_snr: float = 10.0  # dB (minimum for reliable link)
    packet_size: float = 1024.0  # bytes

    # Network parameters
    max_hops: int = 5
    routing_update_interval: float = 5.0  # seconds
    heartbeat_interval: float = 1.0  # seconds
    link_timeout: float = 3.0  # seconds


@dataclass
class SwarmConfig:
    """Swarm coordination parameters"""
    # CBBA parameters
    cbba_convergence_threshold: float = 0.01
    cbba_max_iterations: int = 50
    cbba_time_window: float = 600.0  # seconds

    # Task allocation weights
    weight_distance: float = 0.3
    weight_priority: float = 0.4
    weight_energy: float = 0.3

    # Path planning
    waypoint_tolerance: float = 5.0  # meters
    replanning_interval: float = 10.0  # seconds

    # Health monitoring
    failure_detection_timeout: float = 5.0  # seconds
    relay_replacement_timeout: float = 30.0  # seconds


class Config:
    """Global configuration singleton"""
    def __init__(self):
        self.mission = MissionConfig()
        self.uav = UAVConfig()
        self.rf = RFConfig()
        self.swarm = SwarmConfig()

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            'mission': self.mission.__dict__,
            'uav': self.uav.__dict__,
            'rf': self.rf.__dict__,
            'swarm': self.swarm.__dict__
        }

    def update(self, config_dict: Dict[str, Any]):
        """Update configuration from dictionary"""
        for section, params in config_dict.items():
            if hasattr(self, section):
                section_obj = getattr(self, section)
                for key, value in params.items():
                    if hasattr(section_obj, key):
                        setattr(section_obj, key, value)


# Global config instance
config = Config()
