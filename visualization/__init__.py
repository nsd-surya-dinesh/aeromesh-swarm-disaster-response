"""
Visualization package initialization
"""
try:
    from visualization.gui_visualizer import GUIVisualizer
except ImportError:
    GUIVisualizer = None

from visualization.dashboard_server import DashboardServer
from visualization.video_recorder import VideoRecorder
from visualization.plotter import ChartPlotter

__all__ = ['GUIVisualizer', 'DashboardServer', 'VideoRecorder', 'ChartPlotter']
