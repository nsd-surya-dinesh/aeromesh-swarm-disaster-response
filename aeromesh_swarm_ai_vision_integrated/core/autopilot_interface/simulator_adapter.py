"""
SimulatorAdapter — Wraps existing AeroMesh-Swarm simulation behavior as an
AutopilotAdapter implementation. Used during Phase 3 (SITL telemetry-only) to
verify the integration layer without connecting to a real autopilot.

Reads vehicle state from the shared MissionState and exposes it through the
standard AutopilotAdapter API. Never sends physical commands; all telemetry is
read-only from the simulation.
"""
import time
from typing import Dict, Optional, Any
from core.models import MissionState, UAV, GCS, Vector3D
from core.autopilot_interface.adapter import AutopilotAdapter
from core.autopilot_interface.vehicle_state import (
    ValidatedSetpoint, CommandAck, VehicleTelemetry,
    FlightMode, VehicleHealth, CoordinateFrame, RejectionReason
)
from core.autopilot_interface.mock_adapter import MockAutopilotAdapter


class SimulatorAdapter(MockAutopilotAdapter):
    """Adapter that wraps the existing simulation MissionState.

    This adapter reads telemetry from the simulation's MissionState rather
    than from a real autopilot. It is used during Phase 3 (SITL telemetry-only)
    to verify the integration layer works end-to-end without requiring PX4/ArduPilot.
    """

    def __init__(self, mission_state: Optional[MissionState] = None):
        super().__init__()
        self._mission_state = mission_state or MissionState()
        self._vehicle_cache: Dict[int, Dict[str, Any]] = {}
        self._last_update: Dict[int, float] = {}
        # Cache telemetry for all known UAVs
        self._refresh_cache()

    def _refresh_cache(self) -> None:
        """Refresh the internal cache from the mission state."""
        self._vehicle_cache = {}
        self._last_update = {}

        # Cache GCS telemetry
        if hasattr(self._mission_state, 'gcs') and self._mission_state.gcs:
            gcs = self._mission_state.gcs
            self._vehicle_cache[-1] = {
                'timestamp': time.monotonic(),
                'position': (
                    gcs.position.x if hasattr(gcs.position, 'x') else float(gcs.position.get('x', 0)),
                    gcs.position.y if hasattr(gcs.position, 'y') else float(gcs.position.get('y', 0)),
                    gcs.position.z if hasattr(gcs.position, 'z') else float(gcs.position.get('z', 0)),
                ),
                'velocity': (0.0, 0.0, 0.0),
                'battery_remaining': 1.0,
                'flight_mode': FlightMode.GUIDED,
                'armed': False,
                'health': VehicleHealth.HEALTHY,
                'rssi': -50.0,
                'satellites_visible': 8,
                'gps_fix_type': 3,
            }
            self._last_update[-1] = time.monotonic()

        # Cache UAV telemetry
        for uav_id, uav in self._mission_state.uavs.items():
            self._vehicle_cache[uav_id] = {
                'timestamp': time.monotonic(),
                'position': (
                    uav.position.x if hasattr(uav.position, 'x') else float(uav.position.x),
                    uav.position.y if hasattr(uav.position, 'y') else float(uav.position.y),
                    uav.position.z if hasattr(uav.position, 'z') else float(uav.position.z),
                ),
                'velocity': (
                    uav.velocity.x if hasattr(uav.velocity, 'x') else float(uav.velocity.x or 0),
                    uav.velocity.y if hasattr(uav.velocity, 'y') else float(uav.velocity.y or 0),
                    uav.velocity.z if hasattr(uav.velocity, 'z') else float(uav.velocity.z or 0),
                ),
                'battery_remaining': uav.battery_level,
                # Use UNKNOWN as default; UAVState is not FlightMode
                'flight_mode': FlightMode.UNKNOWN,
                'armed': False,  # Simulation default: never armed
                'health': VehicleHealth.HEALTHY if uav.is_operational() else VehicleHealth.DEGRADED,
                'rssi': -70.0,
                'satellites_visible': 8,
                'gps_fix_type': 3,
            }
            self._last_update[uav_id] = time.monotonic()

    def connect(self, vehicle_id: int, config: Optional[Dict[str, Any]] = None) -> bool:
        """Connect by refreshing cache from mission state."""
        self._refresh_cache()
        super().connect(vehicle_id)
        return True

    def disconnect(self, vehicle_id: int) -> None:
        """No-op for simulation adapter."""
        pass

    def is_connected(self, vehicle_id: int) -> bool:
        return vehicle_id in self._vehicle_cache

    def get_telemetry(self, vehicle_id: int, max_age_sec: float = 1.0) -> Optional[VehicleTelemetry]:
        """Get telemetry for a vehicle from the cached simulation state."""
        buf = self._vehicle_cache.get(vehicle_id)
        if buf is None:
            return None
        if time.monotonic() - buf['timestamp'] > max_age_sec:
            return None  # stale
        # Build and return a VehicleTelemetry object
        pos = buf['position']
        vel = buf['velocity']
        # Ensure NED_LOCAL frame
        class _Telemetry(VehicleTelemetry):
            def __init__(self):
                self.vehicle_id = vehicle_id
                self.timestamp = buf['timestamp']
                # Position in NED frame (simulation uses local ENU-like, we map)
                # Simulation positions: x=north, y=east, z=down (NED convention)
                self.position = (pos[0], pos[1], -pos[2])  # Convert to NED: down becomes negative up
                self.velocity = (vel[0], vel[1], vel[2])
                self.frame = CoordinateFrame.NED_LOCAL
                self.roll = buf.get('roll', 0.0)
                self.pitch = buf.get('pitch', 0.0)
                self.yaw = buf.get('yaw', 0.0)
                self.battery_voltage = buf.get('battery_voltage', 0.0)
                self.battery_current = buf.get('battery_current', 0.0)
                self.battery_remaining = buf['battery_remaining']
                self.flight_mode = buf['flight_mode']
                self.armed = buf['armed']
                self.health = buf['health']
                self.gps_fix_type = buf['gps_fix_type']
                self.satellites_visible = buf['satellites_visible']
                self.hdop = buf.get('hdop', 99.9)
                self.vdop = buf.get('vdop', 99.9)
                self.rssi = buf['rssi']
                self.link_quality = 0.9  # simulation default
                self.raw_data = buf.get('raw_data', {})
        t = _Telemetry()
        t.__dict__.update(buf)  # Apply any extra fields
        return t

    def set_mission_state(self, mission_state) -> None:
        """Set the mission state and refresh cache."""
        self._mission_state = mission_state
        self._refresh_cache()

    # Health is inherited from MockAutopilotAdapter (defaults to HEALTHY)
    def get_health(self, vehicle_id: int) -> VehicleHealth:
        if vehicle_id in self._vehicle_cache:
            return self._vehicle_cache[vehicle_id].get('health', VehicleHealth.HEALTHY)
        return super().get_health(vehicle_id)

    # Setpoint submission: in simulator mode, we log and return accepted
    # but do not actually transmit to any physical device
    def submit_setpoint(
        self,
        vehicle_id: int,
        setpoint: ValidatedSetpoint,
    ) -> CommandAck:
        """Log the setpoint submission and return acceptance (no physical transmission)."""
        # Store in history (from parent mock)
        history = self.get_setpoint_history()
        history.append(setpoint)
        # Return accepted ack — the safety layer already validated
        return CommandAck(
            command_id=setpoint.command_id,
            vehicle_id=vehicle_id,
            accepted=True,
            reason="simulator: setpoint validated and logged (no physical transmission)",
        )

    def request_mode_change(
        self,
        vehicle_id: int,
        target_mode: str,
        authorization_token: Optional[str] = None,
    ) -> CommandAck:
        """Mode changes are logged but never physically executed in simulation."""
        # Call parent to log history
        ack = super().request_mode_change(vehicle_id, target_mode, authorization_token)
        # Override: never actually change mode in simulation
        return CommandAck(
            command_id=0,
            vehicle_id=vehicle_id,
            accepted=True,
            reason="simulator: mode change acknowledged (no physical arming/takeoff)",
        )

    def get_setpoint_history(self) -> list:
        """Return history of validated setpoints submitted through this adapter."""
        return super().get_setpoint_history()

    def get_mode_change_history(self) -> list:
        """Return history of mode-change requests."""
        return super().get_mode_change_history()

    def clear_history(self) -> None:
        """Clear all internal history buffers."""
        super().clear_history()
        self._vehicle_cache = {}
        self._last_update = {}