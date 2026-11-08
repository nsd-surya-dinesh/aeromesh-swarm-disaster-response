"""
Headless Video Recorder for Demo Generation
Records simulation frames and exports to MP4/GIF for demonstration purposes.
"""
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.animation import FuncAnimation, FFMpegWriter, PillowWriter
import numpy as np
from typing import List, Optional
from core.models import MissionState, UAVRole
from simulation.simulator import MissionSimulator


class VideoRecorder:
    """Records simulation visualization to video file"""

    def __init__(self, simulator: MissionSimulator, figsize=(12, 8)):
        self.simulator = simulator
        self.mission_state = simulator.mission_state
        self.figsize = figsize

        self.frames_data = []
        self.record_interval = 10  # Record every 10 timesteps

    def capture_frame(self):
        """Captures current mission state as frame data"""
        frame = {
            'time': self.mission_state.time,
            'uavs': {},
            'pois': {},
            'gcs_pos': (self.mission_state.gcs.position.x, self.mission_state.gcs.position.y),
            'coverage': self.mission_state.calculate_coverage()
        }

        for uav_id, uav in self.mission_state.uavs.items():
            frame['uavs'][uav_id] = {
                'pos': (uav.position.x, uav.position.y),
                'battery': uav.battery_level,
                'role': uav.role.value,
                'neighbors': uav.neighbor_uavs.copy()
            }

        for poi_id, poi in self.mission_state.pois.items():
            frame['pois'][poi_id] = {
                'pos': (poi.position.x, poi.position.y),
                'surveyed': poi.surveyed,
                'priority': poi.priority
            }

        self.frames_data.append(frame)

    def run_and_record(self, max_time: float = 600.0):
        """Runs simulation while recording frames"""
        print(f">> Recording simulation...")
        step_count = 0

        while self.mission_state.time < max_time and not self.mission_state.mission_complete:
            self.simulator.step()
            step_count += 1

            if step_count % self.record_interval == 0:
                self.capture_frame()

            if int(self.mission_state.time) % 60 == 0:
                print(f"   Recorded {self.mission_state.time:.0f}s ({len(self.frames_data)} frames)")

        print(f"[+] Recording complete: {len(self.frames_data)} frames captured")

    def export_video(self, filename: str = "mission_demo.mp4", fps: int = 15):
        """Exports recorded frames to MP4 video"""
        if not self.frames_data:
            print("[-] No frames to export")
            return

        print(f">> Exporting video to {filename}...")

        fig, ax = plt.subplots(figsize=self.figsize)

        def update_frame(frame_idx):
            ax.clear()
            frame = self.frames_data[frame_idx]

            # Set axis limits
            ax.set_xlim(-1200, 1200)
            ax.set_ylim(-1200, 1200)
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)

            # Draw GCS
            gcs_x, gcs_y = frame['gcs_pos']
            gcs_rect = patches.Rectangle((gcs_x - 20, gcs_y - 20), 40, 40,
                                          linewidth=3, edgecolor='green', facecolor='none')
            ax.add_patch(gcs_rect)
            ax.text(gcs_x, gcs_y - 40, 'GCS', ha='center', fontsize=10, fontweight='bold', color='green')

            # Draw PoIs
            for poi_id, poi_data in frame['pois'].items():
                x, y = poi_data['pos']
                color = 'lightgreen' if poi_data['surveyed'] else 'red'
                radius = 15 + poi_data['priority'] * 5
                circle = patches.Circle((x, y), radius, linewidth=2, edgecolor=color, facecolor='none')
                ax.add_patch(circle)

            # Draw communication links
            for uav_id, uav_data in frame['uavs'].items():
                x1, y1 = uav_data['pos']
                for neighbor_id in uav_data['neighbors']:
                    if neighbor_id in frame['uavs']:
                        x2, y2 = frame['uavs'][neighbor_id]['pos']
                        ax.plot([x1, x2], [y1, y2], 'b-', alpha=0.3, linewidth=1)

            # Draw UAVs
            for uav_id, uav_data in frame['uavs'].items():
                x, y = uav_data['pos']
                role = uav_data['role']

                if role == 'relay':
                    color = 'orange'
                    marker = 'D'
                elif role == 'scout':
                    color = 'blue'
                    marker = '^'
                else:
                    color = 'gray'
                    marker = 'o'

                ax.plot(x, y, marker=marker, markersize=10, color=color, markeredgecolor='black', markeredgewidth=1)

                # Battery indicator
                battery_color = 'green' if uav_data['battery'] > 0.5 else 'orange' if uav_data['battery'] > 0.25 else 'red'
                ax.text(x, y + 30, f"{uav_data['battery']*100:.0f}%", ha='center', fontsize=8, color=battery_color)

            # Title with stats
            ax.set_title(f"t={frame['time']:.1f}s | Coverage: {frame['coverage']:.1f}%",
                         fontsize=14, fontweight='bold')
            ax.set_xlabel('X (meters)', fontsize=11)
            ax.set_ylabel('Y (meters)', fontsize=11)

        anim = FuncAnimation(fig, update_frame, frames=len(self.frames_data), interval=1000/fps, repeat=False)

        try:
            writer = FFMpegWriter(fps=fps, bitrate=2000)
            anim.save(filename, writer=writer)
            print(f"[+] Video exported: {filename}")
        except Exception as e:
            print(f"[*] FFmpeg not available, trying GIF export: {e}")
            gif_filename = filename.replace('.mp4', '.gif')
            writer = PillowWriter(fps=fps)
            anim.save(gif_filename, writer=writer)
            print(f"[+] GIF exported: {gif_filename}")

        plt.close()
