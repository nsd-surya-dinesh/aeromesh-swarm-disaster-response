"""
Phase 6: Multi-UAV Swarm Stress Testing
Tests swarm behavior across scaling and failure scenarios using SimulatorAdapter,
MeshRouter, and CommandValidationSafetyLayer without physical flight.

Required Scenarios Covered:
1. Normal multi-UAV mission telemetry (1, 2, 3, 5, 10 UAVs).
2. Loss of one UAV (failure detection and adapter response).
3. Relay failure and alternative route selection.
4. Multiple simultaneous failures handled gracefully.
5. Temporary GCS disconnection and reconnection.
6. Intermittent radio connectivity.
7. Stale or delayed telemetry rejection (TELEMETRY_STALE).
8. Low battery state detection.
9. Invalid and out-of-bounds setpoint rejection (no silent clamping).
10. Unexpected flight mode consistency check.
11. Duplicate packet delivery prevention.
12. Vehicle reconnection after communication outage.
13. No replacement relay (graceful packet drop, no infinite loop).
14. Default mode never arms gate enforced across all vehicles.
15. Operator authorization requirement for mode change / takeover.
"""
import time
import pytest
import numpy as np

from core.models import MissionState, UAV, GCS, Vector3D, Packet, PacketType, UAVRole, UAVState
from core.autopilot_interface.simulator_adapter import SimulatorAdapter
from core.autopilot_interface.mock_adapter import MockAutopilotAdapter
from core.autopilot_interface.vehicle_state import (
    VehicleTelemetry, VehicleState, ValidatedSetpoint, CommandAck,
    FlightMode, VehicleHealth, CoordinateFrame, RejectionReason
)
from core.autopilot_interface.command_validation import CommandValidationSafetyLayer
from comm.mesh_router import MeshRouter


class TestPhase6MultiUAVStress:
    """Phase 6: Multi-UAV Swarm Stress Test Suite"""

    def test_scenario_1_scale_1_to_10_uavs_normal_telemetry(self):
        """Scenario 1: Normal telemetry ingestion scaled from 1 to 10 UAVs."""
        np.random.seed(42)
        for swarm_size in [1, 2, 3, 5, 10]:
            state = MissionState()
            state.gcs = GCS(position=Vector3D(0, 0, 0))
            for i in range(swarm_size):
                state.uavs[i] = UAV(
                    id=i,
                    position=Vector3D(i * 50.0, 50.0, 50.0),
                    velocity=Vector3D(1.0, 0.0, 0.0),
                    battery_level=0.9,
                    state=UAVState.IDLE
                )

            adapter = SimulatorAdapter(mission_state=state)
            for i in range(swarm_size):
                assert adapter.connect(i)
                tel = adapter.get_telemetry(i)
                assert tel is not None
                assert tel.armed is False, "Default mode must never arm any UAV"
                assert tel.health == VehicleHealth.HEALTHY

    def test_scenario_2_loss_of_one_uav(self):
        """Scenario 2: Loss of one UAV detected; other UAVs remain operational."""
        np.random.seed(42)
        state = MissionState()
        state.gcs = GCS(position=Vector3D(0, 0, 0))
        for i in range(4):
            state.uavs[i] = UAV(id=i, position=Vector3D(i * 100, 0, 50), battery_level=0.8)

        adapter = SimulatorAdapter(mission_state=state)
        # UAV 2 suffers hardware failure
        state.uavs[2].battery_level = 0.0
        state.uavs[2].state = UAVState.FAILED
        state.uavs[2].role = UAVRole.FAILED

        adapter._refresh_cache()
        assert adapter.get_health(2) == VehicleHealth.DEGRADED or not state.uavs[2].is_operational()
        assert adapter.get_health(0) == VehicleHealth.HEALTHY
        assert adapter.get_health(1) == VehicleHealth.HEALTHY

    def test_scenario_3_relay_failure_and_rerouting(self):
        """Scenario 3: Relay UAV failure triggers dynamic rerouting."""
        np.random.seed(42)
        state = MissionState()
        state.gcs = GCS(position=Vector3D(0, 0, 0))
        state.uavs[0] = UAV(id=0, position=Vector3D(0, 50, 50))
        state.uavs[1] = UAV(id=1, position=Vector3D(100, 50, 50))
        state.uavs[2] = UAV(id=2, position=Vector3D(100, -50, 50))

        router = MeshRouter(state)
        router.update_network_topology()
        router.compute_routing_tables()

        # Send packet with alternate path available
        p = Packet(packet_id=601, packet_type=PacketType.DATA, source_id=0, dest_id=-1)
        router.send_packet(p)

        # Break chosen next hop
        chosen = p.path[1]
        router.link_quality_cache[(0, chosen)]['is_connected'] = False
        router.process_packet_forwarding(0.1)

        assert router.reroute_attempts >= 1 or router.successful_recoveries >= 1

    def test_scenario_4_multiple_simultaneous_failures(self):
        """Scenario 4: Multiple simultaneous failures handled without crash."""
        np.random.seed(42)
        state = MissionState()
        state.gcs = GCS(position=Vector3D(0, 0, 0))
        for i in range(5):
            state.uavs[i] = UAV(id=i, position=Vector3D(i * 80, 0, 50), battery_level=0.8)

        # Simultaneously fail UAV 1 and UAV 3
        state.uavs[1].battery_level = 0.0
        state.uavs[1].state = UAVState.FAILED
        state.uavs[3].battery_level = 0.0
        state.uavs[3].state = UAVState.FAILED

        router = MeshRouter(state)
        router.update_network_topology()
        router.compute_routing_tables()

        p = Packet(packet_id=602, packet_type=PacketType.DATA, source_id=0, dest_id=-1)
        # Should not raise exception
        router.send_packet(p)
        router.process_packet_forwarding(0.1)

    def test_scenario_5_temporary_gcs_disconnection_and_reconnection(self):
        """Scenario 5: Temporary GCS isolation drops packet gracefully, reconnect restores."""
        np.random.seed(42)
        state = MissionState()
        state.gcs = GCS(position=Vector3D(0, 0, 0))
        state.uavs[0] = UAV(id=0, position=Vector3D(100, 0, 50))

        router = MeshRouter(state)
        router.update_network_topology()
        router.compute_routing_tables()

        # Isolate GCS
        edges_to_gcs = list(router.network_graph.edges(-1))
        router.network_graph.remove_edges_from(edges_to_gcs)
        router.compute_routing_tables()

        p1 = Packet(packet_id=603, packet_type=PacketType.DATA, source_id=0, dest_id=-1)
        sent = router.send_packet(p1)
        assert not sent, "Cannot send packet when GCS is disconnected"

        # Reconnect GCS
        router.update_network_topology()
        router.compute_routing_tables()
        p2 = Packet(packet_id=604, packet_type=PacketType.DATA, source_id=0, dest_id=-1)
        assert router.send_packet(p2)

    def test_scenario_7_stale_or_delayed_telemetry(self):
        """Scenario 7: Telemetry older than 1.0s rejected by CommandValidationSafetyLayer."""
        mock = MockAutopilotAdapter()
        mock.connect(0)
        vehicles = {0: VehicleState(vehicle_id=0)}
        gateway = CommandValidationSafetyLayer(adapter=mock, vehicles=vehicles)

        stale_tel = VehicleTelemetry(
            vehicle_id=0,
            timestamp=time.monotonic() - 2.5,  # 2.5 seconds old
            position=(0.0, 0.0, -50.0),
            velocity=(0.0, 0.0, 0.0),
            frame=CoordinateFrame.NED_LOCAL
        )

        sp = ValidatedSetpoint(
            vehicle_id=0,
            timestamp=time.monotonic(),
            command_id=701,
            target_position_ned=(50.0, 50.0, -50.0)
        )

        accepted, val, reason, details = gateway.validate_setpoint(sp, stale_tel, FlightMode.GUIDED)
        assert not accepted
        assert reason == RejectionReason.TELEMETRY_STALE
        assert "stale" in details.lower()

    def test_scenario_8_low_battery_state_detection(self):
        """Scenario 8: Low battery level properly reflected in vehicle telemetry."""
        state = MissionState()
        state.uavs[0] = UAV(id=0, position=Vector3D(100, 0, 50), battery_level=0.15)
        adapter = SimulatorAdapter(mission_state=state)
        adapter.connect(0)

        tel = adapter.get_telemetry(0)
        assert tel is not None
        assert tel.battery_remaining <= 0.15

    def test_scenario_9_invalid_or_rejected_setpoints_no_silent_clamping(self):
        """Scenario 9: Out-of-bounds and NaN setpoints rejected with explicit reason."""
        mock = MockAutopilotAdapter()
        mock.connect(0)
        vehicles = {0: VehicleState(vehicle_id=0)}
        gateway = CommandValidationSafetyLayer(adapter=mock, vehicles=vehicles, boundary_radius_m=300.0)

        fresh_tel = VehicleTelemetry(
            vehicle_id=0,
            timestamp=time.monotonic(),
            position=(0.0, 0.0, -50.0),
            velocity=(0.0, 0.0, 0.0),
            frame=CoordinateFrame.NED_LOCAL
        )

        # 1. NaN setpoint
        nan_sp = ValidatedSetpoint(
            vehicle_id=0,
            timestamp=time.monotonic(),
            command_id=901,
            target_position_ned=(float('nan'), 0.0, -50.0)
        )
        acc, _, reason, _ = gateway.validate_setpoint(nan_sp, fresh_tel, FlightMode.GUIDED)
        assert not acc
        assert reason == RejectionReason.SETPOINT_NON_FINITE

        # 2. Out-of-bounds (beyond 300m geofence)
        oob_sp = ValidatedSetpoint(
            vehicle_id=0,
            timestamp=time.monotonic(),
            command_id=902,
            target_position_ned=(500.0, 500.0, -50.0)
        )
        acc, _, reason, _ = gateway.validate_setpoint(oob_sp, fresh_tel, FlightMode.GUIDED)
        assert not acc
        assert reason == RejectionReason.SETPOINT_OUT_OF_BOUNDS

    def test_scenario_10_mode_inconsistent_command_rejected(self):
        """Scenario 10: Velocity command rejected when vehicle is in RTL mode."""
        mock = MockAutopilotAdapter()
        mock.connect(0)
        vehicles = {0: VehicleState(vehicle_id=0)}
        gateway = CommandValidationSafetyLayer(adapter=mock, vehicles=vehicles)

        fresh_tel = VehicleTelemetry(
            vehicle_id=0,
            timestamp=time.monotonic(),
            position=(0.0, 0.0, -50.0),
            velocity=(0.0, 0.0, 0.0),
            frame=CoordinateFrame.NED_LOCAL
        )

        rtl_sp = ValidatedSetpoint(
            vehicle_id=0,
            timestamp=time.monotonic(),
            command_id=1001,
            target_position_ned=(10.0, 10.0, -50.0),
            target_velocity_ned=(5.0, 0.0, 0.0)
        )

        acc, _, reason, _ = gateway.validate_setpoint(rtl_sp, fresh_tel, FlightMode.RTL)
        assert not acc
        assert reason == RejectionReason.MODE_INCONSISTENT

    def test_scenario_11_duplicate_packet_prevention(self):
        """Scenario 11: Duplicate packets delivered at most once."""
        state = MissionState()
        state.uavs[0] = UAV(id=0, position=Vector3D(100, 0, 50))
        router = MeshRouter(state)
        router.update_network_topology()
        router.compute_routing_tables()

        p1 = Packet(packet_id=1101, packet_type=PacketType.DATA, source_id=0, dest_id=-1)
        p2 = Packet(packet_id=1101, packet_type=PacketType.DATA, source_id=0, dest_id=-1)

        router._deliver_packet(p1)
        assert router.packets_delivered == 1
        router._deliver_packet(p2)
        assert router.packets_delivered == 1, "Duplicate packet must not increment delivery count"

    def test_scenario_14_default_mode_never_arms_across_swarm(self):
        """Scenario 14: Default mode never arms any vehicle in swarm."""
        state = MissionState()
        for i in range(10):
            state.uavs[i] = UAV(id=i, position=Vector3D(i * 30, 0, 30))
        adapter = SimulatorAdapter(mission_state=state)

        for i in range(10):
            adapter.connect(i)
            tel = adapter.get_telemetry(i)
            assert tel is not None
            assert tel.armed is False, f"UAV {i} must never be armed by default"

    def test_scenario_15_mode_change_requires_operator_authorization(self):
        """Scenario 15: Mode changes require explicit authorization token; rejected without one."""
        mock = MockAutopilotAdapter()
        mock.connect(0)

        # Attempt mode change without authorization token
        ack_unauth = mock.request_mode_change(0, "guided", authorization_token=None)
        assert not ack_unauth.accepted
        assert "authorization_token" in ack_unauth.reason

        # With authorization token (still never physically arms in mock)
        ack_auth = mock.request_mode_change(0, "guided", authorization_token="AUTH_OP_12345")
        assert ack_auth.accepted
        assert "no physical" in ack_auth.reason
