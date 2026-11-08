"""
Safety Limits & Geofencing Arbiter
Enforces the PUSHPAK 500m x 500m search box limits [-250, 250].
"""
class SwarmSafetyArbiter:
    def __init__(self):
        self.min_east = -250.0
        self.max_east = 250.0
        self.min_north = -250.0
        self.max_north = 250.0
        self.min_alt = 5.0
        self.max_alt = 30.0

    def clamp_waypoint(self, uav_id: int, target_north: float, target_east: float, target_alt: float):
        clamped_north = max(self.min_north, min(self.max_north, float(target_north)))
        clamped_east = max(self.min_east, min(self.max_east, float(target_east)))
        clamped_alt = max(self.min_alt, min(self.max_alt, float(target_alt)))
        if clamped_north != target_north or clamped_east != target_east:
            print(f"[GEOFENCE] Clamped UAV {uav_id} to [{clamped_east:.1f}, {clamped_north:.1f}]")
        return clamped_north, clamped_east, clamped_alt
