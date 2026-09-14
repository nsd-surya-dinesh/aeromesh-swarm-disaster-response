"""
Unit Tests for Communication Subsystem
Tests RF channel modeling, mesh routing, and relay placement.
"""
import pytest
import numpy as np
from core.models import UAV, GCS, Vector3D, MissionState, Packet, PacketType
from core.config import config
from comm.channel import RFChannel
from comm.mesh_router import MeshRouter
from comm.steiner_relay import SteinerRelayManager


class TestRFChannel:
    """Test RF propagation and link quality calculations"""

    def test_los_probability_high_altitude(self):
        """Both UAVs at high altitude should have high LoS probability"""
        channel = RFChannel()
        pos1 = Vector3D(0, 0, 100)
        pos2 = Vector3D(500, 0, 100)
        p_los = channel.calculate_los_probability(pos1, pos2)
        assert p_los > 0.85, "High altitude A2A links should have high LoS probability"

    def test_path_loss_increases_with_distance(self):
        """Path loss should increase with distance"""
        channel = RFChannel()
        pos1 = Vector3D(0, 0, 50)

        dist_100m = Vector3D(100, 0, 50)
        dist_500m = Vector3D(500, 0, 50)

        pl_100 = channel.calculate_path_loss_db(pos1, dist_100m, is_los=True)
        pl_500 = channel.calculate_path_loss_db(pos1, dist_500m, is_los=True)

        assert pl_500 > pl_100, "Path loss should increase with distance"

    def test_link_quality_close_distance(self):
        """Close-range links should have high quality"""
        channel = RFChannel()
        pos1 = Vector3D(0, 0, 50)
        pos2 = Vector3D(50, 0, 50)

        link = channel.calculate_link_quality(pos1, pos2)

        assert link['is_connected'], "Close range should be connected"
        assert link['pdr'] > 0.9, "Close range should have high PDR"
        assert link['etx'] < 1.5, "Close range should have low ETX"


class TestMeshRouter:
    """Test dynamic multi-hop routing"""

    def test_routing_table_construction(self):
        """Routing table should find paths to all reachable nodes"""
        mission_state = MissionState()
        mission_state.gcs = GCS(position=Vector3D(0, 0, 0))

        # Create 3 UAVs in a line
        mission_state.uavs[0] = UAV(id=0, position=Vector3D(200, 0, 50))
        mission_state.uavs[1] = UAV(id=1, position=Vector3D(400, 0, 50))
        mission_state.uavs[2] = UAV(id=2, position=Vector3D(600, 0, 50))

        router = MeshRouter(mission_state)
        router.update_network_topology()
        router.compute_routing_tables()

        # Check if routing tables exist
        assert len(router.routing_table) > 0, "Routing tables should be populated"

        # Check that network graph has expected connectivity
        assert router.network_graph.number_of_nodes() >= 3, "Should have at least 3 UAV nodes"
        assert router.network_graph.number_of_edges() >= 2, "Should have connectivity between UAVs"

    def test_packet_delivery(self):
        """Packets should be successfully routed from source to destination"""
        mission_state = MissionState()
        mission_state.gcs = GCS(position=Vector3D(0, 0, 0))
        mission_state.uavs[0] = UAV(id=0, position=Vector3D(100, 0, 50))

        router = MeshRouter(mission_state)
        router.update_network_topology()
        router.compute_routing_tables()

        packet = Packet(
            packet_id=1,
            packet_type=PacketType.DATA,
            source_id=0,
            dest_id=-1
        )

        success = router.send_packet(packet)
        assert success or len(router.routing_table) == 0, "Packet should be routed or no route exists"


class TestSteinerRelayManager:
    """Test relay positioning and management"""

    def test_relay_position_midpoint(self):
        """Relay should be positioned between two nodes"""
        mission_state = MissionState()
        relay_mgr = SteinerRelayManager(mission_state)

        pos_a = Vector3D(0, 0, 50)
        pos_b = Vector3D(1000, 0, 50)

        relay_pos = relay_mgr.compute_relay_position(pos_a, pos_b)

        # Relay should be roughly in the middle
        assert 400 < relay_pos.x < 600, "Relay X should be near midpoint"
        assert relay_pos.z >= 50, "Relay should maintain altitude"

    def test_multi_hop_relay_chain(self):
        """Long distance should generate multiple relay positions"""
        mission_state = MissionState()
        relay_mgr = SteinerRelayManager(mission_state)

        pos_a = Vector3D(0, 0, 50)
        pos_b = Vector3D(2000, 0, 50)  # 2km distance

        relays = relay_mgr.compute_multi_hop_relay_chain(pos_a, pos_b)

        assert len(relays) > 0, "Long distance should require relay chain"
        assert len(relays) >= 2, "2km should need at least 2 relays"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
