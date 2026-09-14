"""
Dynamic Event Injection System
Generates dynamic mission events such as:
- New high-priority PoI discoveries
- Secondary hazards (aftershocks, landslides)
- RF interference/jamming zones
- Forced UAV hardware failures
"""
import random
from typing import List, Optional
from core.models import PointOfInterest, Vector3D, MissionState
from core.config import config


class DynamicEventManager:
    """Manages real-time dynamic event injection during mission execution"""

    def __init__(self, mission_state: MissionState):
        self.mission_state = mission_state
        self.cfg_mission = config.mission
        self.next_poi_id = 1000  # Dynamic PoIs start at ID 1000

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

    def inject_secondary_hazard(self, center: Vector3D, radius: float = 200.0):
        """
        Simulates a secondary hazard event (aftershock, landslide).
        Could affect nearby UAVs or create no-fly zones (not fully implemented here).
        """
        self.mission_state.add_event(
            'secondary_hazard',
            f'[WARNING] Secondary hazard detected at ({center.x:.0f}, {center.y:.0f}) radius={radius:.0f}m',
            hazard_center=center,
            radius=radius
        )

    def inject_rf_interference(self, center: Vector3D, radius: float = 300.0, duration: float = 120.0):
        """
        Simulates localized RF jamming/interference zone.
        (Implementation would degrade link quality within radius)
        """
        self.mission_state.add_event(
            'rf_interference',
            f'[JAMMING] RF interference zone active at ({center.x:.0f}, {center.y:.0f}) for {duration:.0f}s',
            jamming_center=center,
            radius=radius,
            duration=duration
        )
