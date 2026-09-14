"""
Physics and Kinematics Engine for UAVs
Implements 3D flight dynamics, wind disturbance, and power/energy dissipation models.
"""
import numpy as np
from typing import Tuple
from core.models import Vector3D, UAV, UAVRole, UAVState
from core.config import config


class PhysicsEngine:
    """Simulates 3D physics, kinematics, and energy consumption for the UAV fleet"""

    def __init__(self, wind_vector: Vector3D = Vector3D(0.0, 0.0, 0.0)):
        self.wind_vector = wind_vector
        self.cfg_uav = config.uav
        self.cfg_mission = config.mission

    def update_uav_kinematics(self, uav: UAV, dt: float) -> None:
        """
        Updates position, velocity, and distance traveled based on target position
        and physical constraints (max speed, acceleration).
        """
        if not uav.is_operational() or uav.state == UAVState.CHARGING:
            uav.velocity = Vector3D(0.0, 0.0, 0.0)
            return

        if uav.target_position is None:
            uav.velocity = Vector3D(0.0, 0.0, 0.0)
            return

        # Vector towards target
        delta = uav.target_position - uav.position
        dist = delta.norm()

        if dist < 0.5:
            # Reached waypoint
            uav.velocity = Vector3D(0.0, 0.0, 0.0)
            uav.position = Vector3D(uav.target_position.x, uav.target_position.y, uav.target_position.z)
            return

        # Desired velocity direction
        direction = delta.normalize()
        desired_speed = min(self.cfg_uav.cruise_speed, dist / dt)
        desired_velocity = direction * desired_speed

        # Apply acceleration limits
        velocity_delta = desired_velocity - uav.velocity
        max_v_change = self.cfg_uav.max_acceleration * dt
        if velocity_delta.norm() > max_v_change:
            velocity_delta = velocity_delta.normalize() * max_v_change

        uav.velocity = uav.velocity + velocity_delta

        # Apply wind disturbance to ground velocity
        ground_velocity = uav.velocity + (self.wind_vector * 0.2)

        # Update position
        step = ground_velocity * dt
        uav.position = uav.position + step
        uav.distance_traveled += step.norm()

        # Altitude bounds clamping
        uav.position.z = max(0.0, min(self.cfg_uav.survey_altitude * 2.0, uav.position.z))

    def calculate_power_consumption(self, uav: UAV) -> float:
        """
        Calculates instantaneous power consumption in Watts based on aerodynamic
        flight dynamics (induced power, profile power, parasite power, and payload/comm power).
        """
        if not uav.is_operational():
            return 0.0

        if uav.state == UAVState.CHARGING:
            return 0.0

        speed = uav.velocity.norm()

        # Base hover power P_hover
        p_hover = self.cfg_uav.hover_power

        # Parasite and profile drag scaling with airspeed
        # Standard aerodynamic formula: P(v) = P_induced(v) + P_profile(v) + P_parasite(v)
        if speed < 0.1:
            # Hovering
            aerodynamic_power = p_hover
        else:
            # Forward flight: induced power decreases, parasite increases (~ v^3)
            # Semi-empirical rotorcraft power curve
            v_norm = speed / self.cfg_uav.cruise_speed
            aerodynamic_power = p_hover * (0.8 + 0.3 * (v_norm ** 2) + 0.1 * (v_norm ** 3))

        # Payload power (sensors, cameras, flight controller)
        payload_power = 25.0 if uav.state == UAVState.SURVEYING else 10.0

        # RF transmission power
        rf_power = self.cfg_uav.tx_power * 10.0  # RF power + circuit power

        total_power = aerodynamic_power + payload_power + rf_power
        return min(total_power, self.cfg_uav.max_power)

    def update_energy(self, uav: UAV, dt: float) -> None:
        """
        Updates battery state-of-charge (SoC) and tracks energy consumed.
        """
        if uav.state == UAVState.CHARGING:
            # Rapid recharging at GCS (e.g. 5C fast charge: 100% in 12 minutes)
            charge_rate_per_sec = 1.0 / (12.0 * 60.0)
            uav.battery_level = min(1.0, uav.battery_level + charge_rate_per_sec * dt)
            return

        if not uav.is_operational():
            return

        power_watts = self.calculate_power_consumption(uav)
        energy_wh = (power_watts * dt) / 3600.0  # Watt-hours

        uav.total_energy_consumed += energy_wh
        drain_fraction = energy_wh / self.cfg_uav.battery_capacity

        uav.battery_level = max(0.0, uav.battery_level - drain_fraction)

        # Check for battery exhaustion
        if uav.battery_level <= 0.001:
            uav.role = UAVRole.FAILED
            uav.state = UAVState.FAILED
            uav.battery_level = 0.0

    def estimate_energy_to_return(self, current_pos: Vector3D, gcs_pos: Vector3D) -> float:
        """
        Estimates the battery fraction required to return safely to GCS.
        """
        dist = (current_pos - gcs_pos).norm()
        time_to_return = dist / max(1.0, self.cfg_uav.cruise_speed)
        energy_wh = (self.cfg_uav.cruise_power * time_to_return) / 3600.0
        return energy_wh / self.cfg_uav.battery_capacity
