"""
MockAutopilotAdapter — Deterministic mock adapter for deterministic tests.

Never sends physical commands. Never arms. Never takes off.
Implements the AutopilotAdapter API with test-friendly behavior:
- Connected=True always
- Telemetry is deterministic and configurable
- submit_setpoint returns a CommandAck that logs the call but does not transmit
- request_mode_change always returns rejected without an authorization token
- All calls are logged for inspection in tests
"""
import time
from typing import Optional, Dict, Any, List
from core.autopilot_interface.vehicle_state import (
    ValidatedSetpoint, CommandAck, CoordinateFrame,
    FlightMode, VehicleHealth, RejectionReason, CoordinateConverter
)
from .adapter import AutopilotAdapter


class MockAutopilotAdapter(AutopilotAdapter):
    """Deterministic mock adapter for testing. Never arms or takes off."""

    def __init__(self):
        self._connected: Dict[int, bool] = {}
        self._telemetry_buffer: Dict[int, Any] = {}
        self._setpoint_history: List[ValidatedSetpoint] = []
        self._mode_change_history: List[tuple[int, str, Optional[str]]] = []
        self._health_status: Dict[int, VehicleHealth] = {}
        self._last_command_id: int = 0

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------
    def connect(self, vehicle_id: int, config: Optional[Dict[str, Any]] = None) -> bool:
        self._connected[vehicle_id] = True
        # Initialize telemetry buffer for this vehicle
        self._telemetry_buffer[vehicle_id] = {
            'timestamp': time.monotonic(),
            'position': (0.0, 0.0, 0.0),
            'velocity': (0.0, 0.0, 0.0),
            'battery_remaining': 1.0,
            'flight_mode': FlightMode.UNKNOWN,
            'armed': False,
            'health': VehicleHealth.HEALTHY,
        }
        self._health_status[vehicle_id] = VehicleHealth.HEALTHY
        return True

    def disconnect(self, vehicle_id: int) -> None:
        self._connected[vehicle_id] = False

    def is_connected(self, vehicle_id: int) -> bool:
        return self._connected.get(vehicle_id, False)

    # ------------------------------------------------------------------
    # Telemetry
    # ------------------------------------------------------------------
    def get_telemetry(self, vehicle_id: int, max_age_sec: float = 1.0) -> Optional[Any]:
        buf = self._telemetry_buffer.get(vehicle_id)
        if buf is None:
            return None
        if time.monotonic() - buf['timestamp'] > max_age_sec:
            return None  # stale
        # Return a simple namespace-like dict
        class _Telemetry:
            def __init__(b, d):
                for k, v in d.items():
                    setattr(b, k, v)
        return _Telemetry(buf)

    def set_telemetry(self, vehicle_id: int, telemetry: Dict[str, Any]) -> None:
        """Inject deterministic telemetry for testing."""
        buf = self._telemetry_buffer.get(vehicle_id)
        if buf is None:
            buf = {}
            self._telemetry_buffer[vehicle_id] = buf
        buf.update(telemetry)
        buf['timestamp'] = time.monotonic()

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------
    def get_health(self, vehicle_id: int) -> VehicleHealth:
        return self._health_status.get(vehicle_id, VehicleHealth.UNKNOWN)

    # ------------------------------------------------------------------
    # Setpoint submission
    # ------------------------------------------------------------------
    def submit_setpoint(
        self,
        vehicle_id: int,
        setpoint: ValidatedSetpoint,
    ) -> CommandAck:
        # Always log the call
        self._setpoint_history.append(ValidatedSetpoint(
            vehicle_id=setpoint.vehicle_id,
            timestamp=setpoint.timestamp,
            command_id=setpoint.command_id,
            target_position_ned=setpoint.target_position_ned,
            target_velocity_ned=setpoint.target_velocity_ned,
            target_yaw=setpoint.target_yaw,
            deadline=setpoint.deadline,
            authorization_token=setpoint.authorization_token,
        ))
        # Never actually transmit; return accepted ack for test convenience
        # In a real adapter, this would transmit to the autopilot
        return CommandAck(
            command_id=setpoint.command_id,
            vehicle_id=vehicle_id,
            accepted=True,
            reason="mock: submitted (no physical transmission)",
        )

    # ------------------------------------------------------------------
    # Mode change request
    # ------------------------------------------------------------------
    def request_mode_change(
        self,
        vehicle_id: int,
        target_mode: str,
        authorization_token: Optional[str] = None,
    ) -> CommandAck:
        # Never arm/take off in mock. Always require explicit authorization.
        self._mode_change_history.append(
            (vehicle_id, target_mode, authorization_token)
        )
        if authorization_token is None:
            return CommandAck(
                command_id=0,
                vehicle_id=vehicle_id,
                accepted=False,
                reason="mock: mode change requires explicit authorization_token",
            )
        # In a real implementation, validate the token and change mode
        # For the mock, accept any non-None token but still return accepted
        # Note: even with a token, this mock never actually arms or takes off
        return CommandAck(
            command_id=0,
            vehicle_id=vehicle_id,
            accepted=True,
            reason="mock: mode change accepted (no physical arming/takeoff)",
        )

    # ------------------------------------------------------------------
    # Diagnostics / inspection
    # ------------------------------------------------------------------
    def get_setpoint_history(self) -> List[ValidatedSetpoint]:
        return list(self._setpoint_history)

    def get_mode_change_history(self) -> List[tuple[int, str, Optional[str]]]:
        return list(self._mode_change_history)

    def clear_history(self) -> None:
        self._setpoint_history.clear()
        self._mode_change_history.clear()
        self._last_command_id = 0