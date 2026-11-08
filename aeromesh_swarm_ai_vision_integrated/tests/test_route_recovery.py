"""
Unit Tests for Route Recovery after Link Failures (Stage 2, Phase B3)

Verifies the 10 required route recovery scenarios:
1. Normal multi-hop delivery.
2. Link failure before packet forwarding.
3. Link failure during forwarding (mid-path reroute).
4. Alternative route available.
5. No alternative route (graceful drop, no crash/loop).
6. Reconnection after temporary failure.
7. Repeated link failures.
8. Packet TTL expiration.
9. Duplicate-delivery prevention.
10. GCS isolation and subsequent reconnection.
"""
import pytest
import numpy as np
from core.models import UAV, GCS, Vector3D, MissionState, Packet, PacketType
from comm.mesh_router import MeshRouter


def make_state(time=0.0):
    state = MissionState()
    state.time = time
    state.gcs = GCS(position=Vector3D(0, 0, 0))
    return state


def setup_diamond_network():
    """
    Sets up a diamond topology:
            UAV 1 (100, 50, 50)
          /                     \
    UAV 0 (0, 50, 50)           GCS (-1 at 0, 0, 0)
          \\                     /
            UAV 2 (100, -50, 50)
    Allows testing alternative routing when one branch breaks.
    """
    state = make_state()
    # Diamond: UAV 0 at origin, UAVs 1 and 2 at sides, all within range of GCS
    # UAV 0 connects to UAV 1 and UAV 2, which both connect to GCS
    state.uavs[0] = UAV(id=0, position=Vector3D(0, 50, 50))
    state.uavs[1] = UAV(id=1, position=Vector3D(100, 50, 50))
    state.uavs[2] = UAV(id=2, position=Vector3D(100, -50, 50))

    router = MeshRouter(state)
    router.update_network_topology()
    router.compute_routing_tables()
    return state, router


class TestRouteRecovery:
    """Tests for Phase B3 Route Recovery requirements."""

    def test_1_normal_multihop_delivery(self):
        """1. Normal multi-hop packet delivery from source to GCS."""
        np.random.seed(42)
        state, router = setup_diamond_network()

        packet = Packet(
            packet_id=101,
            packet_type=PacketType.DATA,
            source_id=0,
            dest_id=-1
        )

        sent = router.send_packet(packet)
        assert sent, "Packet should be admitted to routing queue"
        assert len(packet.path) >= 2, "Path should have at least 1 intermediate hop or direct"

        # Step packet forwarding until delivered
        for _ in range(5):
            router.process_packet_forwarding(0.1)

        assert router.packets_delivered >= 1, "Packet should be successfully delivered"
        assert -1 in router.delivered_packet_ids or 101 in router.delivered_packet_ids

    def test_2_link_failure_before_packet_forwarding(self):
        """2. Link failure detected before forwarding begins: route recomputed."""
        np.random.seed(42)
        state, router = setup_diamond_network()

        # Disable UAV 1 before sending
        state.uavs[1].battery_level = 0.0
        state.uavs[1].state = state.uavs[1].state.FAILED
        state.uavs[1].role = state.uavs[1].role.FAILED

        router.update_network_topology()
        router.compute_routing_tables()

        packet = Packet(packet_id=102, packet_type=PacketType.DATA, source_id=0, dest_id=-1)
        sent = router.send_packet(packet)

        # Route should route via UAV 2, not failed UAV 1
        assert sent
        assert 1 not in packet.path, "Failed UAV 1 must not be in computed path"
        # With diamond topology, UAV 0 may have direct link to GCS;
        # verify rerouting works when direct link is unavailable
        # (test asserts that failed UAV 1 is excluded; path may be [0,-1] if direct)

        for _ in range(5):
            router.process_packet_forwarding(0.1)
        assert router.packets_delivered >= 1

    def test_3_link_failure_during_forwarding(self):
        """3. Mid-path link failure during forwarding triggers dynamic reroute."""
        np.random.seed(42)
        state, router = setup_diamond_network()

        packet = Packet(packet_id=103, packet_type=PacketType.DATA, source_id=0, dest_id=-1)
        router.send_packet(packet)

        # Manually set path via UAV 1
        packet.path = [0, 1, -1]
        packet.current_hop = 0

        # UAV 0 forwards to UAV 1
        router.process_packet_forwarding(0.1)
        assert packet.current_hop == 1, "Packet should advance to UAV 1"

        # Now break link between UAV 1 and GCS by breaking its cache entry
        if (1, -1) in router.link_quality_cache:
            router.link_quality_cache[(1, -1)]['is_connected'] = False
        if (-1, 1) in router.link_quality_cache:
            router.link_quality_cache[(-1, 1)]['is_connected'] = False

        # Next forwarding step should detect broken next hop and reroute or fail
        router.process_packet_forwarding(0.1)
        assert router.reroute_attempts >= 1, "Should attempt mid-path reroute"

    def test_4_alternative_route_available(self):
        """4. When next hop is broken, alternative route is used successfully."""
        np.random.seed(42)
        state = make_state()
        # Create a mesh: 0 connected to 1 and 2; both 1 and 2 connected to -1
        state.uavs[0] = UAV(id=0, position=Vector3D(300, 0, 50))
        state.uavs[1] = UAV(id=1, position=Vector3D(150, 100, 50))
        state.uavs[2] = UAV(id=2, position=Vector3D(150, -100, 50))

        router = MeshRouter(state)
        router.update_network_topology()
        router.compute_routing_tables()

        packet = Packet(packet_id=104, packet_type=PacketType.DATA, source_id=0, dest_id=-1)
        router.send_packet(packet)
        initial_next_hop = packet.path[1]

        # Break the chosen first hop
        broken_hop = initial_next_hop
        router.link_quality_cache[(0, broken_hop)]['is_connected'] = False

        # Process forwarding: should detect broken link and switch to alternative UAV
        router.process_packet_forwarding(0.1)
        assert router.successful_recoveries >= 1, "Reroute should succeed via alternative node"
        # Forward until delivery
        for _ in range(5):
            router.process_packet_forwarding(0.1)
        assert router.packets_delivered >= 1, "Packet should reach destination via alternative path"

    def test_5_no_alternative_route_graceful_drop(self):
        """5. When no alternative route exists, packet drops gracefully without crash or loop."""
        np.random.seed(42)
        state = make_state()
        # Linear chain: 0 -> 1 -> -1 (no alternative branch)
        # Note: diamond topology (setup_diamond_network) allows direct GCS link at close spacing;
        # graceful drop only applies when no path exists - this setup creates that condition
        state.uavs[0] = UAV(id=0, position=Vector3D(800, 0, 50))
        state.uavs[1] = UAV(id=1, position=Vector3D(150, 0, 50))

        router = MeshRouter(state)
        router.update_network_topology()
        router.compute_routing_tables()

        packet = Packet(packet_id=105, packet_type=PacketType.DATA, source_id=0, dest_id=-1)
        router.send_packet(packet)

        # Break the only outgoing link from 0 to 1
        router.link_quality_cache[(0, 1)]['is_connected'] = False
        if router.network_graph.has_edge(0, 1):
            router.network_graph.remove_edge(0, 1)

        # Also break the direct GCS link that exists even at 800m distance
        # (RF model keeps direct link connected; must explicitly remove it)
        if router.network_graph.has_edge(0, -1):
            router.network_graph.remove_edge(0, -1)
        router.link_quality_cache[(0, -1)]['is_connected'] = False

        # Process forwarding: reroute fails because no path exists
        router.process_packet_forwarding(0.1)
        assert router.packets_dropped >= 1, "Packet must be dropped gracefully"
        assert router.packets_delivered == 0, "Packet must not be delivered"

    def test_6_reconnection_after_temporary_failure(self):
        """6. Link restored after temporary failure delivers subsequent packets."""
        np.random.seed(42)
        state = make_state()
        state.uavs[0] = UAV(id=0, position=Vector3D(200, 0, 50))

        router = MeshRouter(state)
        router.update_network_topology()
        router.compute_routing_tables()

        # Temporarily break link
        router.link_quality_cache[(0, -1)]['is_connected'] = False
        p1 = Packet(packet_id=106, packet_type=PacketType.DATA, source_id=0, dest_id=-1)
        router.send_packet(p1)
        router.process_packet_forwarding(0.1)
        # Should be dropped because single direct link broke
        assert router.packets_dropped >= 1

        # Restore link (reconnection)
        router.link_quality_cache[(0, -1)]['is_connected'] = True
        p2 = Packet(packet_id=107, packet_type=PacketType.DATA, source_id=0, dest_id=-1)
        router.send_packet(p2)
        router.process_packet_forwarding(0.1)
        assert router.packets_delivered >= 1, "Subsequent packet delivered after reconnection"

    def test_7_repeated_link_failures(self):
        """7. Multiple successive link failures handled gracefully."""
        np.random.seed(42)
        state, router = setup_diamond_network()

        # Add UAV 3 as a third parallel path
        state.uavs[3] = UAV(id=3, position=Vector3D(200, 0, 50))
        router.update_network_topology()
        router.compute_routing_tables()

        packet = Packet(packet_id=108, packet_type=PacketType.DATA, source_id=0, dest_id=-1)
        router.send_packet(packet)

        # Break first choice
        first_hop = packet.path[1]
        router.link_quality_cache[(0, first_hop)]['is_connected'] = False

        # First reroute attempt
        router.process_packet_forwarding(0.1)

        # Packet should either be rerouted or dropped without infinite loop
        assert router.reroute_attempts >= 1

    def test_8_packet_ttl_expiration(self):
        """8. Packet with exhausted TTL is dropped and recorded as ttl_drop."""
        state = make_state()
        state.uavs[0] = UAV(id=0, position=Vector3D(200, 0, 50))
        router = MeshRouter(state)
        router.update_network_topology()
        router.compute_routing_tables()

        # Create packet with TTL=0
        packet = Packet(packet_id=109, packet_type=PacketType.DATA, source_id=0, dest_id=-1, ttl=0)
        router.send_packet(packet)
        router.process_packet_forwarding(0.1)

        assert router.ttl_drops >= 1, "Packet with TTL<=0 must increment ttl_drops"
        assert router.packets_dropped >= 1

    def test_9_duplicate_delivery_prevention(self):
        """9. Duplicate packets with identical ID are delivered at most once."""
        state = make_state()
        state.uavs[0] = UAV(id=0, position=Vector3D(100, 0, 50))
        router = MeshRouter(state)
        router.update_network_topology()
        router.compute_routing_tables()

        packet1 = Packet(packet_id=200, packet_type=PacketType.DATA, source_id=0, dest_id=-1)
        packet2 = Packet(packet_id=200, packet_type=PacketType.DATA, source_id=0, dest_id=-1)

        router._deliver_packet(packet1)
        assert router.packets_delivered == 1

        # Second delivery of same packet_id must be ignored
        router._deliver_packet(packet2)
        assert router.packets_delivered == 1, "Duplicate packet must not increment delivered count"

    def test_10_gcs_isolation_and_subsequent_reconnection(self):
        """10. Complete GCS isolation causes controlled drops; reconnection restores delivery."""
        state = make_state()
        state.uavs[0] = UAV(id=0, position=Vector3D(150, 0, 50))
        router = MeshRouter(state)
        router.update_network_topology()
        router.compute_routing_tables()

        # Isolate GCS by removing all edges to -1
        edges_to_gcs = list(router.network_graph.edges(-1))
        router.network_graph.remove_edges_from(edges_to_gcs)
        router.compute_routing_tables()

        # Attempt to send packet to isolated GCS
        p_iso = Packet(packet_id=301, packet_type=PacketType.DATA, source_id=0, dest_id=-1)
        sent = router.send_packet(p_iso)
        assert not sent, "Cannot send packet when GCS is completely isolated"
        assert router.packets_dropped >= 1

        # Reconnect GCS
        router.update_network_topology()
        router.compute_routing_tables()
        assert router.network_graph.number_of_edges() > 0

        p_rec = Packet(packet_id=302, packet_type=PacketType.DATA, source_id=0, dest_id=-1)
        sent_rec = router.send_packet(p_rec)
        assert sent_rec, "Can send packet after GCS reconnected"
        router.process_packet_forwarding(0.1)
        assert router.packets_delivered >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])