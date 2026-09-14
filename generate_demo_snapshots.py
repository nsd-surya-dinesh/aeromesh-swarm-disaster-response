"""
Simple demonstration snapshot generator (no video encoding required)
Generates PNG snapshots at key mission moments for demonstration purposes.
"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from simulation.simulator import MissionSimulator
from core.models import UAVRole
import os


class SnapshotGenerator:
    """Generates demonstration snapshots without video encoding"""

    def __init__(self, simulator: MissionSimulator):
        self.simulator = simulator
        self.mission_state = simulator.mission_state
        self.snapshots = []

    def capture_snapshot(self, title: str):
        """Captures current mission state as a snapshot"""
        snapshot = {
            'title': title,
            'time': self.mission_state.time,
            'uavs': {},
            'pois': {},
            'gcs_pos': (self.mission_state.gcs.position.x,
                       self.mission_state.gcs.position.y),
            'coverage': self.mission_state.calculate_coverage()
        }

        for uav_id, uav in self.mission_state.uavs.items():
            snapshot['uavs'][uav_id] = {
                'pos': (uav.position.x, uav.position.y),
                'battery': uav.battery_level,
                'role': uav.role.value,
                'neighbors': uav.neighbor_uavs.copy(),
                'operational': uav.is_operational()
            }

        for poi_id, poi in self.mission_state.pois.items():
            snapshot['pois'][poi_id] = {
                'pos': (poi.position.x, poi.position.y),
                'surveyed': poi.surveyed,
                'priority': poi.priority
            }

        self.snapshots.append(snapshot)

    def run_and_capture(self, capture_times: list, max_time: float = 600.0):
        """Runs simulation and captures snapshots at specified times"""
        print(f">> Running simulation with snapshot capture...")

        next_capture_idx = 0
        capture_times = sorted(capture_times)

        while self.mission_state.time < max_time:
            self.simulator.step()

            # Check if we should capture
            if next_capture_idx < len(capture_times):
                if self.mission_state.time >= capture_times[next_capture_idx]:
                    title = f"t={self.mission_state.time:.0f}s"
                    self.capture_snapshot(title)
                    print(f"   Captured snapshot at t={self.mission_state.time:.0f}s")
                    next_capture_idx += 1

            if self.mission_state.mission_complete:
                self.capture_snapshot(f"Mission Complete (t={self.mission_state.time:.0f}s)")
                print(f"[+] Mission completed at t={self.mission_state.time:.1f}s")
                break

        print(f"[+] Captured {len(self.snapshots)} snapshots")

    def export_snapshots(self, output_dir: str = "demo_snapshots"):
        """Exports all snapshots as individual PNG files"""
        os.makedirs(output_dir, exist_ok=True)

        for idx, snapshot in enumerate(self.snapshots):
            filename = f"{output_dir}/snapshot_{idx+1:02d}_{snapshot['time']:.0f}s.png"
            self._render_snapshot(snapshot, filename)
            print(f"   Exported: {filename}")

        print(f"\n[+] All snapshots exported to {output_dir}/")

    def _render_snapshot(self, snapshot, filename):
        """Renders a single snapshot to PNG"""
        fig, ax = plt.subplots(figsize=(12, 10))

        ax.set_xlim(-1200, 1200)
        ax.set_ylim(-1200, 1200)
        ax.set_aspect('equal')
        ax.grid(True, alpha=0.3)
        ax.set_facecolor('#0b0f19')
        fig.patch.set_facecolor('#131b2e')

        # Draw GCS
        gcs_x, gcs_y = snapshot['gcs_pos']
        gcs_rect = patches.Rectangle((gcs_x - 20, gcs_y - 20), 40, 40,
                                      linewidth=3, edgecolor='lime', facecolor='none')
        ax.add_patch(gcs_rect)
        ax.text(gcs_x, gcs_y - 40, 'GCS', ha='center', fontsize=12,
               fontweight='bold', color='lime')

        # Draw PoIs
        for poi_id, poi_data in snapshot['pois'].items():
            x, y = poi_data['pos']
            color = 'lightgreen' if poi_data['surveyed'] else 'red'
            radius = 15 + poi_data['priority'] * 5
            circle = patches.Circle((x, y), radius, linewidth=2,
                                   edgecolor=color, facecolor='none')
            ax.add_patch(circle)
            ax.text(x, y - radius - 10, f"PoI-{poi_id}", ha='center',
                   fontsize=9, color=color)

        # Draw communication links
        for uav_id, uav_data in snapshot['uavs'].items():
            if not uav_data['operational']:
                continue
            x1, y1 = uav_data['pos']
            for neighbor_id in uav_data['neighbors']:
                if neighbor_id in snapshot['uavs']:
                    x2, y2 = snapshot['uavs'][neighbor_id]['pos']
                    ax.plot([x1, x2], [y1, y2], 'b-', alpha=0.3, linewidth=1)

        # Draw UAVs
        for uav_id, uav_data in snapshot['uavs'].items():
            x, y = uav_data['pos']
            role = uav_data['role']

            if not uav_data['operational']:
                color = 'red'
                marker = 'x'
                size = 200
            elif role == 'relay':
                color = 'orange'
                marker = 'D'
                size = 150
            elif role == 'scout':
                color = 'deepskyblue'
                marker = '^'
                size = 150
            else:
                color = 'gray'
                marker = 'o'
                size = 100

            ax.scatter(x, y, marker=marker, s=size, c=color,
                      edgecolors='white', linewidth=2, zorder=5)

            # Battery indicator
            battery = uav_data['battery']
            battery_color = 'lime' if battery > 0.5 else 'yellow' if battery > 0.25 else 'red'
            ax.text(x, y + 35, f"{battery*100:.0f}%", ha='center',
                   fontsize=8, color=battery_color, fontweight='bold')
            ax.text(x, y - 35, f"UAV-{uav_id}", ha='center',
                   fontsize=9, color='white', fontweight='bold')

        # Title with mission stats
        title_text = f"{snapshot['title']} | Coverage: {snapshot['coverage']:.1f}%"
        ax.set_title(title_text, fontsize=16, fontweight='bold', color='white', pad=20)
        ax.set_xlabel('X (meters)', fontsize=12, color='white')
        ax.set_ylabel('Y (meters)', fontsize=12, color='white')

        # Style axes
        ax.tick_params(colors='white')
        ax.spines['bottom'].set_color('white')
        ax.spines['left'].set_color('white')
        ax.spines['top'].set_color('white')
        ax.spines['right'].set_color('white')

        plt.tight_layout()
        plt.savefig(filename, dpi=200, facecolor='#131b2e')
        plt.close()


def generate_demo_snapshots(scenario: int):
    """Main function to generate demonstration snapshots"""
    from simulation.scenario_builder import ScenarioBuilder

    builders = {
        1: ScenarioBuilder.scenario_1_baseline_survey,
        2: ScenarioBuilder.scenario_2_deep_canyon_los_blockage,
        3: ScenarioBuilder.scenario_3_dynamic_emergency_and_node_failure,
        4: ScenarioBuilder.scenario_4_continuous_swapping_endurance
    }

    print(f"\n>> Generating demonstration snapshots for Scenario {scenario}...")
    sim = builders[scenario]()

    # Capture at key moments
    capture_times = [0, 30, 60, 120, 180, 240, 300]

    generator = SnapshotGenerator(sim)
    generator.run_and_capture(capture_times, max_time=600.0)
    generator.export_snapshots(f"scenario_{scenario}_snapshots")

    print(f"\n[+] Demo snapshots generated successfully!")
    print(f"    View snapshots in: scenario_{scenario}_snapshots/")


if __name__ == "__main__":
    import sys
    scenario = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    generate_demo_snapshots(scenario)
