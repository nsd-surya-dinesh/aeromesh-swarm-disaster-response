"""
Dynamic Event Injection System
Generates dynamic mission events such as:
- New high-priority PoI discoveries
- Secondary hazards (aftershocks, landslides)
- RF interference/jamming zones
- Forced UAV hardware failures
"""
import random
from typing import List, Dict, Optional
from core.models import PointOfInterest, Vector3D, MissionState, UAV
from core.config import config


class DynamicEventManager:
    """Manages real-time dynamic event injection during mission execution"""

    def __init__(self, mission_state: MissionState):
        self.mission_state = mission_state
        self.cfg_mission = config.mission
        self.next_poi_id = 1000  # Dynamic PoIs start at ID 1000

        # Active interference zones: {id: {'center': Vector3D, 'radius': float, 'start': float, 'end': float}}
        self.active_interference_zones: Dict[int, Dict] = {}
        self.next_interference_id = 0

        # Active hazard zones: {id: {'center': Vector3D, 'radius': float, 'start': float, 'end': float}}
        self.active_hazard_zones: Dict[int, Dict] = {}

    def inject_high_priority_poi(self, position: Vector3D, priority: float = 5.0):
        """
        Injects a newly discovered high-priority PoI (e.g., survivor group detected).
        Triggers immediate bundle re-evaluation by swarm.
        """
        new_poi = PointOfInterest(
            id=self.next_poi_id,
            position=position,
            priority=priority,
            survey_duration=45.0,  # Longer inspection for emergency
            discovery_time=self.mission_state.time
        )
        self.mission_state.pois[self.next_poi_id] = new_poi
        self.next_poi_id += 1

        self.mission_state.add_event(
            'dynamic_poi_discovered',
            f'[ALERT] HIGH-PRIORITY PoI-{new_poi.id} discovered at ({position.x:.0f}, {position.y:.0f})',
            priority=priority
        )

        return new_poi

    def inject_random_high_priority_poi(self):
        """Randomly generates a new emergency PoI within mission area"""
        x = random.uniform(-self.cfg_mission.area_width / 2, self.cfg_mission.area_width / 2)
        y = random.uniform(-self.cfg_mission.area_height / 2, self.cfg_mission.area_height / 2)
        z = 0.0  # Ground level

        position = Vector3D(x, y, z)
        priority = random.uniform(3.0, 8.0)

        return self.inject_high_priority_poi(position, priority)

    def inject_secondary_hazard(self, center: Vector3D, radius: float = 200.0, duration: float = 300.0):
        """
        Simulates a secondary hazard event (aftershock, landslide) that creates a no-fly zone.

        Parameters:
            center: Center position of the hazard zone
            radius: Radius of the hazard zone in meters
            duration: Duration of the hazard in seconds

        Notes:
            Hazard zones affect path planning - UAVs will avoid entering hazard zones.
            Hazard is active from current time until current_time + duration.
        """
        hazard_id = self.next_interference_id
        self.next_interference_id += 1

        self.active_hazard_zones[hazard_id] = {
            'center': center,
            'radius': radius,
            'start': self.mission_state.time,
            'end': self.mission_state.time + duration
        }

        self.mission_state.add_event(
            'secondary_hazard',
            f'[WARNING] Secondary hazard detected at ({center.x:.0f}, {center.y:.0f}) radius={radius:.0f}m',
            hazard_center=center,
            radius=radius,
            hazard_id=hazard_id
        )

        return hazard_id

    def inject_rf_interference(self, center: Vector3D, radius: float = 300.0, duration: float = 120.0,
                                severity: float = 0.5):
        """
        Simulates localized RF jamming/interference zone that degrades link quality.

        Parameters:
            center: Center position of the interference zone
            radius: Radius of the interference zone in meters
            duration: Duration of the interference in seconds
            severity: Interference severity (0.0 = none, 1.0 = complete blockage)
                      Affects signal-to-interference-plus-noise ratio (SINR)

        Implementation:
            - Interference zones reduce effective SNR for links passing through
            - Interference follows: SNR_effective = SNR / (1 + severity * interference_factor)
            - Links with center inside the zone suffer maximum degradation
            - Links partially overlapping with zone suffer partial degradation

        Returns:
            interference_id: Unique identifier for this interference zone

        Raises:
            ValueError: If severity is outside [0, 1], radius <= 0, or duration < 0.
        """
        if not 0.0 <= severity <= 1.0:
            raise ValueError(f"Interference severity must be in [0, 1], got {severity}")
        if radius <= 0:
            raise ValueError(f"Interference radius must be positive, got {radius}")
        if duration < 0:
            raise ValueError(f"Interference duration must be non-negative, got {duration}")

        interference_id = self.next_interference_id
        self.next_interference_id += 1

        self.active_interference_zones[interference_id] = {
            'center': center,
            'radius': radius,
            'start': self.mission_state.time,
            'end': self.mission_state.time + duration,
            'severity': severity
        }

        self.mission_state.add_event(
            'rf_interference',
            f'[JAMMING] RF interference zone active at ({center.x:.0f}, {center.y:.0f}) for {duration:.0f}s',
            jamming_center=center,
            radius=radius,
            duration=duration,
            severity=severity,
            interference_id=interference_id
        )

        return interference_id

    def update_events(self):
        """
        Updates active events: checks interference and hazard zone expiration,
        and removes expired zones from active lists.
        """
        current_time = self.mission_state.time

        # Remove expired interference zones
        expired_interference = [
            id for id, zone in self.active_interference_zones.items()
            if current_time >= zone['end']
        ]
        for id in expired_interference:
            self.mission_state.add_event(
                'rf_interference_expired',
                f'RF interference zone {id} expired'
            )
            del self.active_interference_zones[id]

        # Remove expired hazard zones
        expired_hazards = [
            id for id, zone in self.active_hazard_zones.items()
            if current_time >= zone['end']
        ]
        for id in expired_hazards:
            self.mission_state.add_event(
                'hazard_expired',
                f'Hazard zone {id} expired'
            )
            del self.active_hazard_zones[id]

    def is_position_in_interference_zone(self, position: Vector3D, interference_id: int) -> bool:
        """Check if a position is within an interference zone"""
        if interference_id not in self.active_interference_zones:
            return False
        zone = self.active_interference_zones[interference_id]
        dist = (position - zone['center']).norm()
        return dist <= zone['radius']

    def is_position_in_hazard_zone(self, position: Vector3D, hazard_id: int) -> bool:
        """Check if a position is within a hazard zone (no-fly zone)"""
        if hazard_id not in self.active_hazard_zones:
            return False
        zone = self.active_hazard_zones[hazard_id]
        dist = (position - zone['center']).norm()
        return dist <= zone['radius']

    def get_active_interference_zones(self) -> Dict[int, Dict]:
        """Get all currently active interference zones"""
        current_time = self.mission_state.time
        return {
            id: zone for id, zone in self.active_interference_zones.items()
            if zone['start'] <= current_time < zone['end']
        }

    def get_active_hazard_zones(self) -> Dict[int, Dict]:
        """Get all currently active hazard zones"""
        current_time = self.mission_state.time
        return {
            id: zone for id, zone in self.active_hazard_zones.items()
            if zone['start'] <= current_time < zone['end']
        }

    def calculate_interference_snr_degradation(self, pos1: Vector3D, pos2: Vector3D) -> float:
        """
        Calculate the interference-induced SNR degradation factor for a link.

        For each active interference zone that the link passes through:
        - Determine the minimum distance from the line segment (pos1-pos2) to the zone center
        - Compute proximity-based degradation: at zone center = severity, at zone edge = 0
        - Return the maximum degradation across all zones (worst-case SNR reduction)

        Returns:
            factor: Multiplier to apply to SNR (1.0 = no degradation, 0.0 = complete blockage)
        """
        if not self.active_interference_zones:
            return 1.0

        # Compute minimum distance from line segment pos1-pos2 to each zone center
        # Using perpendicular distance from point to line, clamped within segment bounds
        max_degradation = 1.0

        for zone in self.active_interference_zones.values():
            if zone['start'] <= self.mission_state.time < zone['end']:
                center = zone['center']
                radius = zone['radius']
                severity = zone['severity']

                # Vector from pos1 to pos2
                seg_vec_x = pos2.x - pos1.x
                seg_vec_y = pos2.y - pos1.y
                seg_vec_z = pos2.z - pos1.z
                seg_len_sq = seg_vec_x**2 + seg_vec_y**2 + seg_vec_z**2

                if seg_len_sq < 1e-12:
                    # pos1 and pos2 are at the same position
                    dist_to_center = ((pos1.x - center.x)**2 + (pos1.y - center.y)**2 + (pos1.z - center.z)**2)**0.5
                else:
                    # t = projection of (center - pos1) onto seg_vec, clamped [0, 1]
                    t = max(0.0, min(1.0, ((center.x - pos1.x) * seg_vec_x + (center.y - pos1.y) * seg_vec_y + (center.z - pos1.z) * seg_vec_z) / seg_len_sq))
                    # Closest point on segment
                    closest_x = pos1.x + t * seg_vec_x
                    closest_y = pos1.y + t * seg_vec_y
                    closest_z = pos1.z + t * seg_vec_z
                    dist_to_center = ((closest_x - center.x)**2 + (closest_y - center.y)**2 + (closest_z - center.z)**2)**0.5

                # If the line passes through or near the zone
                if dist_to_center < radius:
                    # Proximity: 1.0 at center, 0.0 at edge
                    proximity = 1.0 - (dist_to_center / radius)
                    # Degradation: severity at center, 0 at edge
                    zone_degradation = 1.0 - (proximity * severity)
                    max_degradation = min(max_degradation, zone_degradation)

        return max_degradation
