"""
Integration Tests for Complete Mission Simulation
Tests end-to-end scenario execution and mission completion criteria.
"""
import pytest
import random
import numpy as np
from simulation.scenario_builder import ScenarioBuilder
from simulation.metrics import MetricsEngine


class TestScenarios:
    """Test complete mission scenario execution"""

    def test_scenario_1_baseline_completion(self):
        """Scenario 1 should achieve high coverage within time limit"""
        sim = ScenarioBuilder.scenario_1_baseline_survey()
        report = sim.run_simulation(max_time=600.0)

        assert report['coverage_percent'] > 99.0, "Should achieve >99% coverage in 10 minutes"
        assert report['pois_surveyed'] >= 8, "Should survey at least 8 out of 10 PoIs"

    def test_scenario_2_deep_canyon_connectivity(self):
        """Scenario 2 should maintain network connectivity despite distance"""
        # Set seed for reproducibility
        random.seed(42)
        np.random.seed(42)
        sim = ScenarioBuilder.scenario_2_deep_canyon_los_blockage()
        report = sim.run_simulation(max_time=600.0)

        # Network should adapt with relay deployment
        assert report['coverage_percent'] > 99.0, "Should achieve >99% coverage"
        assert report['network_pdr'] > 0.85, "Should maintain >85% PDR despite distance"

    def test_scenario_4_battery_cycling(self):
        """Scenario 4 should demonstrate battery cycling without catastrophic failures"""
        sim = ScenarioBuilder.scenario_4_continuous_swapping_endurance()
        report = sim.run_simulation(max_time=600.0)

        # Check that UAVs are managing energy properly
        operational_uavs = len(sim.mission_state.get_operational_uavs())
        total_uavs = len(sim.mission_state.uavs)

        assert operational_uavs / total_uavs > 0.95, "Should maintain >95% operational UAVs"
        assert report['coverage_percent'] > 99.0, "Should achieve >99% coverage"

    def test_scenario_3_self_healing_chain(self):
        """Scenario 3 should demonstrate self-healing after relay failure"""
        sim = ScenarioBuilder.scenario_3_dynamic_emergency_and_node_failure()
        # Manually trigger a relay UAV failure (as in test_relay_failure_recovery)
        if len(sim.mission_state.uavs) > 1:
            sim.health_monitor.handle_unexpected_node_failure(1)
        # Run the scenario
        sim.run_simulation(max_time=600.0)

        # Check that mission completed
        assert sim.mission_state.mission_complete, "Mission should complete"

        # Check for failure/recovery events
        event_types = [e['type'] for e in sim.mission_state.events]
        assert 'hardware_failure' in event_types, "Should log a hardware failure event"
        recovery_events = ['emergency_healing', 'relay_promotion', 'relay_handoff']
        assert any(e in event_types for e in recovery_events), "Should log a recovery event"

        # Measure recovery time between failure and first recovery event
        failure_time = None
        recovery_time = None
        for e in sim.mission_state.events:
            if e['type'] == 'hardware_failure':
                failure_time = e['time']
            if e['type'] in recovery_events and failure_time is not None:
                recovery_time = e['time']
                break
        if failure_time is not None and recovery_time is not None:
            recovery_duration = recovery_time - failure_time
            assert recovery_duration < 10.0, f"Recovery took too long: {recovery_duration}s"
            print(f"\n[INFO] Scenario 3 self-healing recovery time: {recovery_duration:.2f}s")

    def test_metrics_calculation(self):
        """Metrics engine should calculate comprehensive KPIs"""
        sim = ScenarioBuilder.scenario_1_baseline_survey()
        sim.run_simulation(max_time=300.0)

        metrics_engine = MetricsEngine(sim.mission_state)
        metrics = metrics_engine.generate_full_metrics_summary()

        # Check all expected metrics are present
        required_keys = [
            'coverage_percentage',
            'packet_delivery_ratio_pdr',
            'avg_end_to_end_latency_ms',
            'total_energy_kwh',
            'swarm_survival_rate'
        ]

        for key in required_keys:
            assert key in metrics, f"Metric {key} should be present"
            assert isinstance(metrics[key], (int, float)), f"Metric {key} should be numeric"


class TestEventInjection:
    """Test dynamic event handling"""

    def test_dynamic_poi_injection(self):
        """System should handle dynamically injected PoIs"""
        from core.models import Vector3D
        sim = ScenarioBuilder.scenario_1_baseline_survey()

        initial_poi_count = len(sim.mission_state.pois)

        # Inject a high-priority emergency PoI
        new_poi = sim.event_manager.inject_high_priority_poi(Vector3D(800, 800, 0), priority=8.0)

        assert len(sim.mission_state.pois) == initial_poi_count + 1, "PoI should be added"
        assert new_poi.priority == 8.0, "Priority should be set correctly"

    def test_relay_failure_recovery(self):
        """System should recover from relay node failure"""
        sim = ScenarioBuilder.scenario_3_dynamic_emergency_and_node_failure()

        # Manually trigger a relay UAV failure
        if len(sim.mission_state.uavs) > 1:
            sim.health_monitor.handle_unexpected_node_failure(1)
            failed_uav = sim.mission_state.uavs[1]

            assert not failed_uav.is_operational(), "Failed UAV should be non-operational"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
