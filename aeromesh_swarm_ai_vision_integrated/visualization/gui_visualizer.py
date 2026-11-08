"""
Real-Time Interactive Desktop Visualizer using Pygame
Displays UAV positions, battery levels, network links, PoI coverage, and live event feed.
"""
import pygame
import sys
import math
from typing import Dict, List, Tuple, Optional
from core.models import MissionState, UAV, PointOfInterest, UAVRole, UAVState
from simulation.simulator import MissionSimulator


class GUIVisualizer:
    """Interactive 2D real-time mission visualizer with Pygame"""

    def __init__(self, simulator: MissionSimulator, width: int = 1400, height: int = 900):
        pygame.init()
        self.simulator = simulator
        self.mission_state = simulator.mission_state

        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("AeroMesh-Swarm Mission Control")

        # Fonts
        self.font_small = pygame.font.Font(None, 20)
        self.font_medium = pygame.font.Font(None, 28)
        self.font_large = pygame.font.Font(None, 36)

        # Colors
        self.COLOR_BG = (15, 20, 30)
        self.COLOR_GRID = (40, 45, 55)
        self.COLOR_GCS = (0, 255, 100)
        self.COLOR_UAV_SCOUT = (50, 150, 255)
        self.COLOR_UAV_RELAY = (255, 200, 50)
        self.COLOR_UAV_CHARGING = (150, 150, 150)
        self.COLOR_UAV_FAILED = (255, 50, 50)
        self.COLOR_POI_UNSURVEYED = (255, 100, 100)
        self.COLOR_POI_SURVEYED = (100, 255, 100)
        self.COLOR_LINK = (80, 120, 200, 100)
        self.COLOR_TEXT = (220, 220, 230)

        # View parameters
        self.scale = 0.25  # pixels per meter
        self.offset_x = width // 2
        self.offset_y = height // 2

        # UI state
        self.paused = False
        self.show_links = True
        self.show_paths = True
        self.speed_multiplier = 1.0

        self.clock = pygame.time.Clock()
        self.fps = 60

    def world_to_screen(self, x: float, y: float) -> Tuple[int, int]:
        """Converts world coordinates to screen pixel coordinates"""
        screen_x = int(self.offset_x + x * self.scale)
        screen_y = int(self.offset_y - y * self.scale)  # Flip Y axis
        return screen_x, screen_y

    def draw_grid(self):
        """Draws background grid"""
        grid_spacing = 200  # meters
        grid_spacing_px = int(grid_spacing * self.scale)

        # Vertical lines
        for i in range(-20, 21):
            x = self.offset_x + i * grid_spacing_px
            if 0 <= x <= self.width:
                pygame.draw.line(self.screen, self.COLOR_GRID, (x, 0), (x, self.height), 1)

        # Horizontal lines
        for i in range(-20, 21):
            y = self.offset_y + i * grid_spacing_px
            if 0 <= y <= self.height:
                pygame.draw.line(self.screen, self.COLOR_GRID, (0, y), (self.width, y), 1)

    def draw_gcs(self):
        """Draws Ground Control Station"""
        gcs_pos = self.mission_state.gcs.position
        screen_x, screen_y = self.world_to_screen(gcs_pos.x, gcs_pos.y)

        # Draw GCS as a larger square
        size = 15
        pygame.draw.rect(self.screen, self.COLOR_GCS,
                         (screen_x - size, screen_y - size, size * 2, size * 2), 3)

        # Label
        label = self.font_medium.render("GCS", True, self.COLOR_GCS)
        self.screen.blit(label, (screen_x - 15, screen_y + 20))

    def draw_pois(self):
        """Draws Points of Interest"""
        for poi in self.mission_state.pois.values():
            screen_x, screen_y = self.world_to_screen(poi.position.x, poi.position.y)

            color = self.COLOR_POI_SURVEYED if poi.surveyed else self.COLOR_POI_UNSURVEYED
            radius = int(8 + poi.priority * 2)

            pygame.draw.circle(self.screen, color, (screen_x, screen_y), radius, 2)

            # Priority indicator
            if poi.priority > 2.0:
                pygame.draw.circle(self.screen, color, (screen_x, screen_y), radius + 5, 1)

            # Label
            label_text = f"P{poi.id}"
            label = self.font_small.render(label_text, True, color)
            self.screen.blit(label, (screen_x + 10, screen_y - 5))

    def draw_communication_links(self):
        """Draws active communication links between UAVs"""
        if not self.show_links:
            return

        drawn_links = set()
        for uav in self.mission_state.get_operational_uavs():
            for neighbor_id in uav.neighbor_uavs:
                if neighbor_id in self.mission_state.uavs:
                    link_key = tuple(sorted([uav.id, neighbor_id]))
                    if link_key not in drawn_links:
                        neighbor = self.mission_state.uavs[neighbor_id]
                        x1, y1 = self.world_to_screen(uav.position.x, uav.position.y)
                        x2, y2 = self.world_to_screen(neighbor.position.x, neighbor.position.y)

                        # Draw with transparency
                        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                        pygame.draw.line(surf, self.COLOR_LINK, (x1, y1), (x2, y2), 1)
                        self.screen.blit(surf, (0, 0))
                        drawn_links.add(link_key)

            # GCS links
            if -1 in [n for n in uav.neighbor_uavs if n == -1] or uav.connected_to_gcs:
                gcs_pos = self.mission_state.gcs.position
                x1, y1 = self.world_to_screen(uav.position.x, uav.position.y)
                x2, y2 = self.world_to_screen(gcs_pos.x, gcs_pos.y)

                surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                pygame.draw.line(surf, (100, 255, 100, 120), (x1, y1), (x2, y2), 2)
                self.screen.blit(surf, (0, 0))

    def draw_uavs(self):
        """Draws UAV icons with battery indicators"""
        for uav in self.mission_state.uavs.values():
            screen_x, screen_y = self.world_to_screen(uav.position.x, uav.position.y)

            # Choose color based on role
            if uav.role == UAVRole.FAILED:
                color = self.COLOR_UAV_FAILED
            elif uav.role == UAVRole.RELAY:
                color = self.COLOR_UAV_RELAY
            elif uav.role == UAVRole.CHARGING:
                color = self.COLOR_UAV_CHARGING
            else:
                color = self.COLOR_UAV_SCOUT

            # Draw UAV as triangle
            size = 10
            points = [
                (screen_x, screen_y - size),
                (screen_x - size, screen_y + size),
                (screen_x + size, screen_y + size)
            ]
            pygame.draw.polygon(self.screen, color, points, 2 if uav.is_operational() else 0)

            # Battery bar
            bar_width = 30
            bar_height = 5
            battery_fill = int(bar_width * uav.battery_level)
            battery_color = (0, 255, 0) if uav.battery_level > 0.5 else (255, 200, 0) if uav.battery_level > 0.25 else (255, 50, 0)

            pygame.draw.rect(self.screen, (60, 60, 60),
                             (screen_x - bar_width // 2, screen_y + 15, bar_width, bar_height))
            pygame.draw.rect(self.screen, battery_color,
                             (screen_x - bar_width // 2, screen_y + 15, battery_fill, bar_height))

            # UAV ID label
            label = self.font_small.render(f"U{uav.id}", True, color)
            self.screen.blit(label, (screen_x - 10, screen_y + 22))

    def draw_hud(self):
        """Draws heads-up display with mission stats"""
        hud_x = 10
        hud_y = 10
        line_height = 25

        coverage = self.mission_state.calculate_coverage()
        operational_uavs = len(self.mission_state.get_operational_uavs())
        total_uavs = len(self.mission_state.uavs)

        stats = [
            f"Time: {self.mission_state.time:.1f}s",
            f"Coverage: {coverage:.1f}%",
            f"PoIs: {len(self.mission_state.get_surveyed_pois())}/{len(self.mission_state.pois)}",
            f"UAVs: {operational_uavs}/{total_uavs}",
            f"Speed: {self.speed_multiplier}x",
            f"[SPACE] {'Resume' if self.paused else 'Pause'}",
            f"[L] Links: {'ON' if self.show_links else 'OFF'}"
        ]

        for i, stat in enumerate(stats):
            text = self.font_medium.render(stat, True, self.COLOR_TEXT)
            self.screen.blit(text, (hud_x, hud_y + i * line_height))

    def handle_events(self) -> bool:
        """Processes user input events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_l:
                    self.show_links = not self.show_links
                elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                    self.speed_multiplier = min(10.0, self.speed_multiplier * 1.5)
                elif event.key == pygame.K_MINUS:
                    self.speed_multiplier = max(0.1, self.speed_multiplier / 1.5)
                elif event.key == pygame.K_ESCAPE:
                    return False

        return True

    def render(self):
        """Renders one frame"""
        self.screen.fill(self.COLOR_BG)
        self.draw_grid()
        self.draw_communication_links()
        self.draw_gcs()
        self.draw_pois()
        self.draw_uavs()
        self.draw_hud()
        pygame.display.flip()

    def run(self, max_time: Optional[float] = None):
        """Runs the visualization loop"""
        running = True

        while running and not self.mission_state.mission_complete:
            running = self.handle_events()

            if not self.paused:
                # Run multiple simulation steps per frame for speed control
                steps = max(1, int(self.speed_multiplier))
                for _ in range(steps):
                    self.simulator.step()

                    if max_time and self.mission_state.time >= max_time:
                        running = False
                        break

            self.render()
            self.clock.tick(self.fps)

        # Keep window open after completion
        if running:
            print("✅ Mission complete! Press ESC to exit.")
            while running:
                running = self.handle_events()
                self.render()
                self.clock.tick(30)

        pygame.quit()
