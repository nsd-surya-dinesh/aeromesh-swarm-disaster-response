"""
Dynamic Multi-Hop Mesh Routing Engine
Implements AODV-inspired dynamic routing with ETX (Expected Transmission Count) metrics,
packet queuing, forwarding, and latency tracking.
"""
import heapq
import networkx as nx
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict, deque
from core.models import UAV, GCS, Packet, PacketType, MissionState, Vector3D
from core.config import config
from comm.channel import RFChannel


class MeshRouter:
    """Dynamic multi-hop routing engine for UAV mesh network"""

    def __init__(self, mission_state: MissionState):
        self.mission_state = mission_state
        self.rf_channel = RFChannel()
        self.cfg_rf = config.rf

        # Routing tables: {node_id: {dest_id: (next_hop_id, etx_cost)}}
        self.routing_table: Dict[int, Dict[int, Tuple[int, float]]] = defaultdict(dict)

        # Link quality cache: {(node_a, node_b): link_quality_dict}
        self.link_quality_cache: Dict[Tuple[int, int], Dict] = {}

        # Packet queues per UAV
        self.packet_queues: Dict[int, deque] = defaultdict(deque)

        # Network topology graph
        self.network_graph = nx.Graph()

        # Statistics
        self.packets_sent = 0
        self.packets_delivered = 0
        self.packets_dropped = 0
        self.total_hops = 0

        self.last_routing_update = 0.0

    def update_network_topology(self):
        """
        Scans all UAV positions, calculates RF link quality, and builds the network graph.
        Updates neighbor lists and connectivity status for each UAV.
        """
        current_time = self.mission_state.time
        gcs = self.mission_state.gcs
        uavs = self.mission_state.uavs

        # Clear previous topology
        self.network_graph.clear()
        self.link_quality_cache.clear()

        # Add GCS as node -1
        self.network_graph.add_node(-1, pos=gcs.position)

        # Add all operational UAVs
        for uav_id, uav in uavs.items():
            if uav.is_operational():
                self.network_graph.add_node(uav_id, pos=uav.position)

        # Evaluate all pairwise links
        nodes = list(self.network_graph.nodes())

        for i, node_a in enumerate(nodes):
            for node_b in nodes[i+1:]:
                pos_a = self._get_node_position(node_a)
                pos_b = self._get_node_position(node_b)

                link_quality = self.rf_channel.calculate_link_quality(pos_a, pos_b)

                if link_quality['is_connected']:
                    etx = link_quality['etx']
                    self.network_graph.add_edge(node_a, node_b, weight=etx, **link_quality)
                    self.link_quality_cache[(node_a, node_b)] = link_quality
                    self.link_quality_cache[(node_b, node_a)] = link_quality

        # Update UAV neighbor lists and GCS connectivity
        gcs.connected_uavs.clear()

        for uav_id, uav in uavs.items():
            if not uav.is_operational():
                continue

            uav.neighbor_uavs.clear()
            uav.connected_to_gcs = False

            if self.network_graph.has_node(uav_id):
                neighbors = list(self.network_graph.neighbors(uav_id))
                uav.neighbor_uavs = [n for n in neighbors if n >= 0]

                # Check GCS connectivity (direct or multi-hop)
                if -1 in neighbors:
                    uav.connected_to_gcs = True
                    gcs.connected_uavs.append(uav_id)
                else:
                    # Check if path to GCS exists
                    if nx.has_path(self.network_graph, uav_id, -1):
                        uav.connected_to_gcs = True

    def compute_routing_tables(self):
        """
        Computes shortest-path routing tables using Dijkstra's algorithm with ETX weights.
        Each UAV knows the next hop towards any destination (including GCS).
        """
        self.routing_table.clear()

        # For each source node, compute shortest paths to all destinations
        for source in self.network_graph.nodes():
            if source == -1:
                continue  # GCS doesn't forward packets

            try:
                # Dijkstra from source to all nodes
                paths = nx.single_source_dijkstra_path(self.network_graph, source, weight='weight')
                costs = nx.single_source_dijkstra_path_length(self.network_graph, source, weight='weight')

                for dest, path in paths.items():
                    if len(path) > 1 and dest != source:
                        next_hop = path[1]  # First hop in path
                        etx_cost = costs[dest]
                        self.routing_table[source][dest] = (next_hop, etx_cost)

            except (nx.NetworkXNoPath, nx.NodeNotFound):
                pass

    def route_packet(self, packet: Packet) -> Optional[int]:
        """
        Determines the next hop for a packet based on routing table.
        Returns next_hop UAV ID, or None if no route exists.
        """
        current_hop = packet.path[packet.current_hop] if packet.path else packet.source_id
        dest_id = packet.dest_id

        if current_hop == dest_id:
            return None  # Already at destination

        if current_hop not in self.routing_table:
            return None  # No routing info

        if dest_id in self.routing_table[current_hop]:
            next_hop, _ = self.routing_table[current_hop][dest_id]
            return next_hop

        return None

    def send_packet(self, packet: Packet) -> bool:
        """
        Initiates packet transmission from source.
        Computes route and adds to packet queue.
        """
        source_id = packet.source_id
        dest_id = packet.dest_id

        # Compute path using current routing table
        path = self._find_path(source_id, dest_id)

        if not path:
            self.packets_dropped += 1
            return False

        packet.path = path
        packet.current_hop = 0
        packet.creation_time = self.mission_state.time

        # Add to source queue
        self.packet_queues[source_id].append(packet)
        self.packets_sent += 1

        return True

    def process_packet_forwarding(self, dt: float):
        """
        Processes packet forwarding across all hops.
        Simulates transmission delay and probabilistic packet drops based on PDR.
        """
        current_time = self.mission_state.time

        # Process each UAV's outgoing queue
        for uav_id in list(self.packet_queues.keys()):
            if not self.packet_queues[uav_id]:
                continue

            packet = self.packet_queues[uav_id].popleft()

            # Check if at destination
            if packet.current_hop >= len(packet.path) - 1:
                self._deliver_packet(packet)
                continue

            current_node = packet.path[packet.current_hop]
            next_node = packet.path[packet.current_hop + 1]

            # Check link quality
            link_key = (current_node, next_node)
            if link_key not in self.link_quality_cache:
                # Link broken
                self.packets_dropped += 1
                continue

            link_quality = self.link_quality_cache[link_key]
            pdr = link_quality['pdr']

            # Probabilistic packet drop
            import random
            if random.random() > pdr:
                self.packets_dropped += 1
                continue

            # Successful transmission - advance to next hop
            packet.advance_hop()
            self.total_hops += 1

            if packet.current_hop >= len(packet.path) - 1:
                # Reached destination
                self._deliver_packet(packet)
            else:
                # Forward to next hop
                self.packet_queues[next_node].append(packet)

    def _deliver_packet(self, packet: Packet):
        """Delivers packet to final destination"""
        self.packets_delivered += 1

        if packet.dest_id == -1:
            # Delivered to GCS
            gcs = self.mission_state.gcs
            gcs.packets_received += 1
            latency = packet.get_latency(self.mission_state.time)
            gcs.total_latency += latency

    def _find_path(self, source_id: int, dest_id: int) -> Optional[List[int]]:
        """Finds shortest path from source to destination using network graph"""
        if source_id not in self.network_graph or dest_id not in self.network_graph:
            return None

        try:
            path = nx.shortest_path(self.network_graph, source_id, dest_id, weight='weight')
            if len(path) > self.cfg_rf.max_hops:
                return None
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def _get_node_position(self, node_id: int) -> Vector3D:
        """Gets position of a node (UAV or GCS)"""
        if node_id == -1:
            return self.mission_state.gcs.position
        else:
            return self.mission_state.uavs[node_id].position

    def get_network_stats(self) -> Dict:
        """Returns network performance statistics"""
        pdr_overall = self.packets_delivered / max(1, self.packets_sent)
        avg_latency = self.mission_state.gcs.total_latency / max(1, self.mission_state.gcs.packets_received)
        avg_hops = self.total_hops / max(1, self.packets_delivered)

        return {
            'packets_sent': self.packets_sent,
            'packets_delivered': self.packets_delivered,
            'packets_dropped': self.packets_dropped,
            'pdr': pdr_overall,
            'avg_latency': avg_latency,
            'avg_hops': avg_hops,
            'num_nodes': self.network_graph.number_of_nodes(),
            'num_edges': self.network_graph.number_of_edges()
        }
