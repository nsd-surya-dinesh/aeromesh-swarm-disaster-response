"""
Mission Analytics and Performance Metrics Engine
Calculates KPIs: Coverage %, PDR, Latency, Energy Efficiency, Network Resilience.
"""
from typing import Dict, List
import numpy as np
from core.models import MissionState


class MetricsEngine:
    """Calculates evaluation metrics and key performance indicators"""

    def __init__(self, mission_state: MissionState):
        self.mission_state = mission_state

    def calculate_survey_efficiency(self) -> float:
        """Calculates survey rate (PoIs surveyed per minute)"""
        surveyed_count = len(self.mission_state.get_surveyed_pois())
        time_minutes = max(0.1, self.mission_state.time / 60.0)
        return surveyed_count / time_minutes

    def calculate_energy_efficiency(self) -> float:
        """Calculates energy efficiency (PoIs surveyed per kWh consumed)"""
        total_energy_wh = sum(u.total_energy_consumed for u in self.mission_state.uavs.values())
        total_energy_kwh = max(1e-3, total_energy_wh / 1000.0)
        surveyed_count = len(self.mission_state.get_surveyed_pois())
        return surveyed_count / total_energy_kwh

    def calculate_swarm_survival_rate(self) -> float:
        """Calculates percentage of operational UAVs remaining"""
        total_uavs = len(self.mission_state.uavs)
        if total_uavs == 0:
            return 0.0
        operational = len(self.mission_state.get_operational_uavs())
        return (operational / total_uavs) * 100.0

    def generate_full_metrics_summary(self) -> Dict:
        """Generates comprehensive metrics summary dictionary"""
        gcs = self.mission_state.gcs
        total_pois = len(self.mission_state.pois)
        surveyed_pois = len(self.mission_state.get_surveyed_pois())

        total_distance = sum(u.distance_traveled for u in self.mission_state.uavs.values())
        total_energy = sum(u.total_energy_consumed for u in self.mission_state.uavs.values())

        pdr = (gcs.packets_received / max(1, gcs.packets_received + gcs.packets_dropped)) * 100.0
        avg_latency = (gcs.total_latency / max(1, gcs.packets_received)) * 1000.0  # ms

        return {
            'mission_duration_s': self.mission_state.time,
            'coverage_percentage': (surveyed_pois / max(1, total_pois)) * 100.0,
            'pois_surveyed': surveyed_pois,
            'total_pois': total_pois,
            'survey_rate_pois_per_min': self.calculate_survey_efficiency(),
            'packet_delivery_ratio_pdr': pdr,
            'avg_end_to_end_latency_ms': avg_latency,
            'total_flight_distance_km': total_distance / 1000.0,
            'total_energy_kwh': total_energy / 1000.0,
            'energy_efficiency_pois_per_kwh': self.calculate_energy_efficiency(),
            'swarm_survival_rate': self.calculate_swarm_survival_rate(),
            'total_events_logged': len(self.mission_state.events)
        }
