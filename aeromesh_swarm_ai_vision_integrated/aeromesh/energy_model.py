"""
Aerodynamic Energy & Battery Endurance Model
Calculates power consumption via Actuator Disk Momentum Theory.
"""
import math

class DroneEnergyModel:
    def __init__(self, mass_kg=1.5, num_rotors=4, prop_radius_m=0.127):
        self.mass_kg = float(mass_kg)
        self.num_rotors = int(num_rotors)
        self.gravity = 9.81
        self.air_density = 1.225
        self.prop_area = math.pi * (prop_radius_m ** 2)
        self.total_disk_area = self.num_rotors * self.prop_area
        self.cd_frame = 1.05
        self.frontal_area_m2 = 0.025
        self.induced_power_factor = 1.15
        self.battery_capacity_mah = 5000.0
        self.battery_voltage = 12.6
        self.total_energy_joules = (self.battery_capacity_mah / 1000.0) * self.battery_voltage * 3600.0
        self.consumed_joules = 0.0

    def calculate_power_watts(self, airspeed_mps=10.0, is_hover=False):
        thrust_n = self.mass_kg * self.gravity
        p_induced = self.induced_power_factor * (thrust_n ** 1.5) / math.sqrt(2 * self.air_density * self.total_disk_area)
        p_parasite = 0.5 * self.air_density * (airspeed_mps ** 3) * self.cd_frame * self.frontal_area_m2 if not is_hover else 0.0
        p_profile = 0.3 * p_induced
        return (p_induced + p_parasite + p_profile) / 0.82

    def step(self, airspeed_mps=10.0, dt_seconds=1.0):
        power_watts = self.calculate_power_watts(airspeed_mps)
        self.consumed_joules += power_watts * dt_seconds
        remaining_joules = max(0.0, self.total_energy_joules - self.consumed_joules)
        percent_left = (remaining_joules / self.total_energy_joules) * 100.0
        remaining_minutes = (remaining_joules / power_watts) / 60.0 if power_watts > 0 else 0.0
        return percent_left, remaining_minutes
