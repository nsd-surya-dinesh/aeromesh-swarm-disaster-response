"""
Publication-Quality Chart Generator
Generates performance charts and network topology graphs for technical proposal.
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from typing import List, Dict
import networkx as nx
from core.models import MissionState
from simulation.metrics import MetricsEngine


class ChartPlotter:
    """Generates publication-ready charts and figures"""

    def __init__(self, output_dir: str = "docs/figures"):
        self.output_dir = output_dir
        plt.style.use('seaborn-v0_8-darkgrid')

    def plot_coverage_over_time(self, time_series: List[float], coverage_series: List[float],
                                 filename: str = "coverage_vs_time.png"):
        """Plots mission coverage percentage over time"""
        fig, ax = plt.subplots(figsize=(10, 6))

        ax.plot(time_series, coverage_series, linewidth=2.5, color='#2E86AB', label='Coverage %')
        ax.fill_between(time_series, 0, coverage_series, alpha=0.3, color='#2E86AB')

        ax.set_xlabel('Time (seconds)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Coverage (%)', fontsize=12, fontweight='bold')
        ax.set_title('Mission Coverage Progress', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 105)
        ax.legend(fontsize=11)

        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/{filename}", dpi=300, bbox_inches='tight')
        plt.close()

    def plot_energy_consumption(self, uav_ids: List[int], energy_consumed: List[float],
                                filename: str = "energy_consumption.png"):
        """Bar chart of energy consumption per UAV"""
        fig, ax = plt.subplots(figsize=(10, 6))

        colors = plt.cm.viridis(np.linspace(0.2, 0.9, len(uav_ids)))
        bars = ax.bar([f"UAV-{uid}" for uid in uav_ids], energy_consumed, color=colors, edgecolor='black')

        ax.set_xlabel('UAV ID', fontsize=12, fontweight='bold')
        ax.set_ylabel('Energy Consumed (Wh)', fontsize=12, fontweight='bold')
        ax.set_title('Energy Consumption by UAV', fontsize=14, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/{filename}", dpi=300, bbox_inches='tight')
        plt.close()

    def plot_network_topology(self, mission_state: MissionState, mesh_router,
                              filename: str = "network_topology.png"):
        """Visualizes network graph topology with node positions"""
        fig, ax = plt.subplots(figsize=(12, 10))

        G = mesh_router.network_graph

        # Position nodes based on actual UAV positions
        pos = {}
        for node_id in G.nodes():
            if node_id == -1:
                pos[node_id] = (mission_state.gcs.position.x, mission_state.gcs.position.y)
            else:
                uav = mission_state.uavs[node_id]
                pos[node_id] = (uav.position.x, uav.position.y)

        # Draw edges with varying thickness based on link quality
        edge_widths = []
        for u, v, data in G.edges(data=True):
            etx = data.get('etx', 1.0)
            width = max(0.5, 3.0 / etx)  # Thicker lines for better links
            edge_widths.append(width)

        nx.draw_networkx_edges(G, pos, width=edge_widths, alpha=0.6, edge_color='gray', ax=ax)

        # Draw nodes
        gcs_nodes = [n for n in G.nodes() if n == -1]
        uav_nodes = [n for n in G.nodes() if n != -1]

        nx.draw_networkx_nodes(G, pos, nodelist=gcs_nodes, node_color='green',
                               node_size=800, node_shape='s', label='GCS', ax=ax)
        nx.draw_networkx_nodes(G, pos, nodelist=uav_nodes, node_color='skyblue',
                               node_size=400, node_shape='o', label='UAVs', ax=ax)

        # Labels
        labels = {n: f"GCS" if n == -1 else f"U{n}" for n in G.nodes()}
        nx.draw_networkx_labels(G, pos, labels, font_size=9, font_weight='bold', ax=ax)

        ax.set_title('Network Topology Snapshot', fontsize=14, fontweight='bold')
        ax.legend(fontsize=11)
        ax.axis('equal')

        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/{filename}", dpi=300, bbox_inches='tight')
        plt.close()

    def plot_scenario_comparison(self, scenario_names: List[str], metrics_list: List[Dict],
                                 filename: str = "scenario_comparison.png"):
        """Compares key metrics across multiple scenarios"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        coverage = [m['coverage_percentage'] for m in metrics_list]
        pdr = [m['packet_delivery_ratio_pdr'] for m in metrics_list]
        latency = [m['avg_end_to_end_latency_ms'] for m in metrics_list]
        energy_eff = [m['energy_efficiency_pois_per_kwh'] for m in metrics_list]

        # Coverage
        axes[0, 0].bar(scenario_names, coverage, color='#2E86AB')
        axes[0, 0].set_ylabel('Coverage (%)', fontweight='bold')
        axes[0, 0].set_title('Mission Coverage', fontweight='bold')
        axes[0, 0].grid(axis='y', alpha=0.3)

        # PDR
        axes[0, 1].bar(scenario_names, pdr, color='#A23B72')
        axes[0, 1].set_ylabel('PDR (%)', fontweight='bold')
        axes[0, 1].set_title('Packet Delivery Ratio', fontweight='bold')
        axes[0, 1].grid(axis='y', alpha=0.3)

        # Latency
        axes[1, 0].bar(scenario_names, latency, color='#F18F01')
        axes[1, 0].set_ylabel('Latency (ms)', fontweight='bold')
        axes[1, 0].set_title('Avg End-to-End Latency', fontweight='bold')
        axes[1, 0].grid(axis='y', alpha=0.3)

        # Energy Efficiency
        axes[1, 1].bar(scenario_names, energy_eff, color='#6A994E')
        axes[1, 1].set_ylabel('PoIs per kWh', fontweight='bold')
        axes[1, 1].set_title('Energy Efficiency', fontweight='bold')
        axes[1, 1].grid(axis='y', alpha=0.3)

        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/{filename}", dpi=300, bbox_inches='tight')
        plt.close()
