"""
Wireless RF Channel Modeling
Implements Air-to-Air (A2A) and Air-to-Ground (A2G) channel models,
probabilistic Line-of-Sight (LoS), path loss, shadow fading, SNR, and Shannon capacity.
"""
import math
import numpy as np
from typing import Tuple, Dict
from core.models import Vector3D
from core.config import config


class RFChannel:
    """Simulates realistic wireless propagation in post-disaster environments"""

    def __init__(self):
        self.cfg_rf = config.rf
        self.cfg_uav = config.uav
        self.c = 3e8  # Speed of light in m/s

    def calculate_elevation_angle(self, pos1: Vector3D, pos2: Vector3D) -> float:
        """
        Calculates elevation angle (in degrees) between two nodes in 3D space.
        """
        delta_z = abs(pos1.z - pos2.z)
        horizontal_dist = math.sqrt((pos1.x - pos2.x)**2 + (pos1.y - pos2.y)**2)
        if horizontal_dist < 1e-3:
            return 90.0
        angle_rad = math.atan2(delta_z, horizontal_dist)
        return math.degrees(angle_rad)

    def calculate_los_probability(self, pos1: Vector3D, pos2: Vector3D) -> float:
        """
        Calculates probability of Line-of-Sight (LoS) based on ITU-R standard model:
        P(LoS) = 1 / (1 + a * exp(-b * (theta - a)))
        where theta is elevation angle, a and b are environment parameters.
        For Air-to-Air (both at altitude > 20m), LoS probability is very high (~0.95 - 0.99).
        """
        # If both nodes are well above terrain, A2A link is predominantly LoS
        if pos1.z > 20.0 and pos2.z > 20.0:
            dist = (pos1 - pos2).norm()
            # Slight degradation only for very long distances due to atmospheric / terrain curvature
            return max(0.85, 1.0 - (dist / 10000.0))

        # A2G link with ground station or low-altitude node
        theta = self.calculate_elevation_angle(pos1, pos2)
        a = self.cfg_rf.los_param_a
        b = self.cfg_rf.los_param_b

        p_los = 1.0 / (1.0 + a * math.exp(-b * (theta - a)))
        return float(np.clip(p_los, 0.05, 0.99))

    def calculate_path_loss_db(self, pos1: Vector3D, pos2: Vector3D, is_los: bool) -> float:
        """
        Calculates total path loss in dB including Free-Space Path Loss (FSPL),
        excess loss (for NLoS), and log-normal shadowing.
        """
        dist = max(1.0, (pos1 - pos2).norm())
        wavelength = self.c / self.cfg_rf.frequency

        # Free Space Path Loss (FSPL)
        fspl_db = 20 * math.log10(4 * math.pi * dist / wavelength)

        # Excess attenuation
        eta_los = 1.0  # dB additional loss for LoS
        eta_nlos = 20.0  # dB additional loss for NLoS (urban/terrain blockage)

        excess_loss = eta_los if is_los else eta_nlos

        # Shadow fading (log-normal standard deviation)
        shadowing = np.random.normal(0.0, self.cfg_rf.shadowing_std)

        total_pl = fspl_db + excess_loss + shadowing
        return float(total_pl)

    def calculate_link_quality(self, pos1: Vector3D, pos2: Vector3D) -> Dict[str, float]:
        """
        Evaluates full link metrics between two spatial positions:
        - Received Signal Strength (RSSI in dBm)
        - Signal-to-Noise Ratio (SNR in dB)
        - Shannon Channel Capacity (Mbps)
        - Packet Delivery Probability (PDR)
        - Expected Transmission Count (ETX)
        """
        p_los = self.calculate_los_probability(pos1, pos2)
        is_los = np.random.random() < p_los

        path_loss_db = self.calculate_path_loss_db(pos1, pos2, is_los)

        # Transmit power in dBm
        tx_power_dbm = 10 * math.log10(self.cfg_uav.tx_power * 1000.0)

        # Received power
        rx_power_dbm = tx_power_dbm + 2 * self.cfg_uav.antenna_gain - path_loss_db

        # SNR calculation
        snr_db = rx_power_dbm - self.cfg_rf.noise_floor
        snr_linear = 10 ** (snr_db / 10.0)

        # Shannon Capacity: C = B * log2(1 + SNR)
        bandwidth_hz = self.cfg_rf.bandwidth
        capacity_bps = bandwidth_hz * math.log2(1.0 + snr_linear)
        capacity_mbps = capacity_bps / 1e6

        # Packet Delivery Ratio (PDR) approximation using sigmoid over SNR threshold
        snr_diff = snr_db - self.cfg_rf.min_snr
        pdr = 1.0 / (1.0 + math.exp(-0.8 * snr_diff))
        pdr = float(np.clip(pdr, 0.0, 0.999))

        # Expected Transmission Count (ETX) = 1 / PDR (lower is better, 1.0 is ideal)
        etx = 1.0 / max(0.01, pdr) if pdr > 0.05 else 999.0

        is_connected = snr_db >= self.cfg_rf.min_snr and rx_power_dbm >= self.cfg_uav.rx_sensitivity

        return {
            'distance': (pos1 - pos2).norm(),
            'is_los': is_los,
            'p_los': p_los,
            'rx_power_dbm': rx_power_dbm,
            'snr_db': snr_db,
            'capacity_mbps': capacity_mbps,
            'pdr': pdr,
            'etx': etx,
            'is_connected': is_connected
        }
