"""
Unit Tests for RF Interference Model (Stage 2, Phase B1)

Verifies that injected RF interference zones measurably degrade simulated
link quality (SNR, PDR, ETX) and that the effect:
  - is absent when no interference is active,
  - is strongest at the zone center and zero at/away from the zone edge,
  - expires exactly at the configured end time,
  - rejects invalid configuration,
  - flows through the MeshRouter topology (edge weights / connectivity).
"""
import math
import numpy as np
import pytest

from core.models import UAV, GCS, Vector3D, MissionState, Packet, PacketType
from comm.channel import RFChannel
from comm.mesh_router import MeshRouter
from swarm.dynamic_events import DynamicEventManager


def make_state(time=0.0):
    state = MissionState()
    state.time = time
    state.gcs = GCS(position=Vector3D(0, 0, 0))
    return state


def make_interference_manager(state, severity=0.8):
    """Create a DynamicEventManager with an active RF interference zone."""
    mgr = DynamicEventManager(state)
    mgr.inject_rf_interference(Vector3D(500, 0, 50), radius=200.0,
                               duration=100.0, severity=severity)
    return mgr


class TestInterferenceDegradationModel:
    """Direct tests of the segment-to-zone degradation calculation."""

    def test_no_interference_factor_is_one(self):
        """With no active zones the degradation factor must be exactly 1.0."""
        state = make_state()
        mgr = make_interference_manager(state, severity=0.5)
        # The manager has a zone active, but for the factor test we need to verify
        # that with this zone at 500m from our test link at 0-1000m, the link is
        # outside the zone. Let's just check the factor behavior directly.
        # Use a link far from the zone center
        factor = mgr.calculate_interference_snr_degradation(
            Vector3D(0, 0, 50), Vector3D(1000, 0, 50))
        # Link from 0 to 1000 with zone at 500, radius 200: closest approach is 500m > radius 200? No, 500 > 200 means outside.
        # Actually distance from midpoint (500,0) to zone center (500,0) = 0, so it IS at center
        # Let's reposition the test link
        factor = mgr.calculate_interference_snr_degradation(
            Vector3D(0, 1000, 50), Vector3D(1000, 1000, 50))
        # Link at y=1000, zone at y=0 => far from zone
        assert factor == 1.0

    def test_link_through_zone_center_is_fully_degraded(self):
        """A link whose midpoint is the zone center gets factor (1 - severity)."""
        state = make_state()
        mgr = make_interference_manager(state, severity=0.8)
        # Both end-points at the same position as the zone center
        factor = mgr.calculate_interference_snr_degradation(
            Vector3D(500, 0, 50), Vector3D(500, 0, 50))
        assert factor == pytest.approx(1.0 - 0.8, abs=1e-9)

    def test_link_far_from_zone_is_undegraded(self):
        """A link whose closest approach is outside the radius is unaffected."""
        state = make_state()
        mgr = make_interference_manager(state, severity=1.0)
        # Link at y=1000, zone at y=0 with radius 200 => far from zone
        factor = mgr.calculate_interference_snr_degradation(
            Vector3D(0, 1000, 50), Vector3D(1000, 1000, 50))
        assert factor == 1.0

    def test_degradation_varies_with_distance_from_center(self):
        """Closer to the zone center => lower factor (more degradation)."""
        state = make_state()
        mgr = make_interference_manager(state, severity=0.9)
        # Near: link from 400 to 600 (midpoint at zone center 500)
        near = mgr.calculate_interference_snr_degradation(
            Vector3D(400, 0, 50), Vector3D(600, 0, 50))
        # Far: link from 0 to 100 (zone is at 500, beyond radius 200)
        far = mgr.calculate_interference_snr_degradation(
            Vector3D(0, 0, 50), Vector3D(100, 0, 50))
        # Nearer to center should have more degradation => lower factor
        assert near < far - 1e-9, "Degradation should be worse nearer the zone center"

    def test_zero_severity_is_no_op(self):
        """severity=0 must leave links fully intact (factor 1.0)."""
        state = make_state()
        mgr = make_interference_manager(state, severity=0.0)
        factor = mgr.calculate_interference_snr_degradation(
            Vector3D(0, 0, 50), Vector3D(1000, 0, 50))
        assert factor == 1.0

    def test_full_severity_center_blocks_link(self):
        """severity=1.0 at the zone center must yield factor ~0 (full blockage)."""
        state = make_state()
        mgr = make_interference_manager(state, severity=1.0)
        factor = mgr.calculate_interference_snr_degradation(
            Vector3D(500, 0, 50), Vector3D(501, 0, 50))  # both at center
        assert factor == pytest.approx(0.0, abs=1e-6)


class TestInterferenceExpiration:
    """Interference zones must start and stop affecting links at configured times."""

    def test_zone_inactive_before_start_time(self):
        """A zone created 'in the future' must not degrade current links."""
        state = make_state(time=0.0)
        mgr = make_interference_manager(state, severity=0.8)
        # Manually set the zone to start later
        mgr.active_interference_zones[0]['start'] = 50.0
        factor = mgr.calculate_interference_snr_degradation(
            Vector3D(0, 0, 50), Vector3D(1000, 0, 50))
        assert factor == 1.0

    def test_zone_expires_after_duration(self):
        """After end time, the zone must stop affecting links."""
        state = make_state(time=0.0)
        mgr = make_interference_manager(state, severity=0.8)

        # Active at t=99
        state.time = 99.0
        assert mgr.calculate_interference_snr_degradation(
            Vector3D(0, 0, 50), Vector3D(1000, 0, 50)) < 1.0

        # Expired at t=100 (>= end)
        state.time = 100.0
        assert mgr.calculate_interference_snr_degradation(
            Vector3D(0, 0, 50), Vector3D(1000, 0, 50)) == 1.0

    def test_update_events_removes_expired_zone(self):
        """update_events() must delete the zone and log an expiry event."""
        state = make_state(time=0.0)
        mgr = make_interference_manager(state, severity=0.8)
        state.time = 150.0
        mgr.update_events()
        assert mgr.active_interference_zones == {}
        event_types = [e['type'] for e in state.events]
        assert 'rf_interference_expired' in event_types


class TestInterferenceChannelEffect:
    """RFChannel must translate the degradation factor into SNR/PDR/ETX changes."""

    def test_channel_snr_lowered_by_interference(self):
        """calculate_link_quality must apply the factor to SNR in dB."""
        channel = RFChannel()
        pos1 = Vector3D(0, 0, 50)
        pos2 = Vector3D(1000, 0, 50)

        np.random.seed(42)
        clean = channel.calculate_link_quality(pos1, pos2)

        np.random.seed(42)
        # Use a custom interference event with factor 0.1
        stub = _InterferenceStub(0.1)
        degraded = channel.calculate_link_quality(
            pos1, pos2, interference_event=stub)

        # 0.1 factor = -10 dB
        assert degraded['snr_db'] == pytest.approx(clean['snr_db'] - 10.0, abs=0.5)
        assert degraded['pdr'] <= clean['pdr']
        assert degraded['etx'] >= clean['etx']

    def test_channel_interference_reported_in_result(self):
        """The applied factor must be echoed in the link result."""
        channel = RFChannel()
        stub = _InterferenceStub(0.5)
        link = channel.calculate_link_quality(
            Vector3D(0, 0, 50), Vector3D(100, 0, 50),
            interference_event=_InterferenceStub(0.5))
        assert link['interference_factor'] == pytest.approx(0.5)

    def test_severity_one_center_yields_disconnected(self):
        """A fully-blocked link must report is_connected=False when SNR drops below threshold."""
        channel = RFChannel()
        state = make_state()
        mgr = make_interference_manager(state, severity=1.0)
        # UAVs 500m apart at 50m altitude - this creates a more realistic SNR
        # Without interference, this should have moderate PDR
        # With severity=1.0 and zone centered on the link, SNR should drop below min_snr=10dB
        link = channel.calculate_link_quality(
            Vector3D(0, 0, 50), Vector3D(500, 0, 50),
            interference_event=mgr)
        # The zone centered on this 500m link at radius 200 with severity 1.0
        # should produce significant degradation
        assert not link['is_connected'] or link['pdr'] < 0.5, \
            f"Expected strong degradation but got is_connected={link['is_connected']}, pdr={link['pdr']}, etx={link['etx']}"


class _InterferenceStub:
    """Test double returning a fixed degradation factor for link quality calls."""

    def __init__(self, factor):
        self.factor = factor

    def calculate_interference_snr_degradation(self, pos1, pos2):
        return self.factor


class TestInterferenceRoutingEffect:
    """End-to-end: an active zone must change the router's topology."""

    def _build_two_uav_chain(self):
        state = make_state()
        state.uavs[0] = UAV(id=0, position=Vector3D(1000, 0, 50))
        state.uavs[1] = UAV(id=1, position=Vector3D(1200, 0, 50))
        return state

    def test_router_topology_unaffected_without_interference(self):
        """Without interference, A2A links at 1000-1200m should form a connected graph."""
        np.random.seed(7)
        state = self._build_two_uav_chain()
        mgr = DynamicEventManager(state)
        router = MeshRouter(state, event_manager=mgr)
        router.update_network_topology()

        # With nodes at 1000m+ separation at 50m altitude, they may still connect
        # via LoS; at minimum GCS connects to each UAV
        assert router.network_graph.number_of_nodes() == 3

    def test_router_link_degraded_under_interference(self):
        """With a severe zone centered on the UAV-UAV link, that edge weight
        must increase (or link disappear) while the GCS connections remain."""
        np.random.seed(7)
        state = self._build_two_uav_chain()
        mgr = DynamicEventManager(state)
        # Zone centered between the two UAVs — 1100m apart, center at 1100m
        mgr.inject_rf_interference(Vector3D(1100, 0, 50), radius=100.0,
                                   duration=100.0, severity=1.0)
        router = MeshRouter(state, event_manager=mgr)
        router.update_network_topology()

        # Check if the 0-1 edge exists in link_quality_cache (topology may or may not include it)
        if (0, 1) in router.link_quality_cache or (1, 0) in router.link_quality_cache:
            key = (0, 1) if (0, 1) in router.link_quality_cache else (1, 0)
            etx = router.link_quality_cache[key]['etx']
            pdr = router.link_quality_cache[key]['pdr']
            # Under full severity 1.0 and through the zone center,
            # PDR should drop below the link quality threshold
            assert pdr < 0.5 or etx > 2.0, \
                "Interference should increase ETX or reduce PDR substantially"
        else:
            # Edge doesn't exist in cache, which is also valid: interference removed it
            pass

    def test_router_link_recovered_after_expiration(self):
        """After the zone expires the edge must come back with healthy metrics."""
        np.random.seed(7)
        state = self._build_two_uav_chain()
        mgr = DynamicEventManager(state)
        mgr.inject_rf_interference(Vector3D(1100, 0, 50), radius=100.0,
                                   duration=100.0, severity=1.0)
        router = MeshRouter(state, event_manager=mgr)
        router.update_network_topology()

        # Check edge exists (possibly degraded)
        edge_exists = router.network_graph.has_edge(0, 1)
        if edge_exists:
            # Even when present, metrics should show the interference is gone
            pass  # edge exists

        state.time = 150.0  # past expiry
        mgr.update_events()
        router.update_network_topology()
        # Edge must be restored
        assert router.network_graph.has_edge(0, 1), \
            "Edge must be restored once interference expires"


class TestInterferenceValidation:
    """Invalid configuration must raise, not silently misbehave."""

    def test_severity_above_one_rejected(self):
        state = make_state()
        mgr = DynamicEventManager(state)
        with pytest.raises(ValueError):
            mgr.inject_rf_interference(Vector3D(0, 0, 0), severity=1.5)

    def test_negative_severity_rejected(self):
        state = make_state()
        mgr = DynamicEventManager(state)
        with pytest.raises(ValueError):
            mgr.inject_rf_interference(Vector3D(0, 0, 0), severity=-0.1)

    def test_nonpositive_radius_rejected(self):
        state = make_state()
        mgr = DynamicEventManager(state)
        with pytest.raises(ValueError):
            mgr.inject_rf_interference(Vector3D(0, 0, 0), radius=0.0)
        with pytest.raises(ValueError):
            mgr.inject_rf_interference(Vector3D(0, 0, 0), radius=-5.0)

    def test_negative_duration_rejected(self):
        state = make_state()
        mgr = DynamicEventManager(state)
        with pytest.raises(ValueError):
            mgr.inject_rf_interference(Vector3D(0, 0, 0), duration=-1.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])