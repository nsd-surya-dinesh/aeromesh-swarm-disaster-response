"""
AutopilotAdapter — Abstract base class for all autopilot adapters.

Defines the common API that all adapter implementations must follow:
  - Telemetry, health, and setpoint submission.
  - Command acknowledgements.
  - Connection management.
  - Mode change requests with authorization.

All units and coordinate frames are explicit. Subclasses must implement
all abstract methods. The MockAutopilotAdapter provides a deterministic
implementation for testing; concrete adapters (PX4, ArduPilot) implement
the same API for real autopilot integration.

IMPORTANT: The default mode must never arm a vehicle, initiate takeoff,
or execute a physical mission. Concrete adapters must honor this gate.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Tuple
from core.autopilot_interface.vehicle_state import (
    ValidatedSetpoint, CommandAck, CoordinateFrame,
    FlightMode, VehicleHealth, RejectionReason, CoordinateConverter
)


class AutopilotAdapter(ABC):
    """Abstract base class for autopilot adapters."""

    @abstractmethod
    def connect(self, vehicle_id: int, config: Optional[Dict[str, Any]] = None) -> bool:
        """Connect to the autopilot for the given vehicle."""
        ...

    @abstractmethod
    def disconnect(self, vehicle_id: int) -> None:
        """Disconnect from the autopilot for the given vehicle."""
        ...

    @abstractmethod
    def is_connected(self, vehicle_id: int) -> bool:
        """Check if the autopilot is connected for the given vehicle."""
        ...

    @abstractmethod
    def get_telemetry(self, vehicle_id: int, max_age_sec: float = 1.0) -> Optional:
        """Get latest timestamped telemetry from the autopilot.

        Returns None if telemetry is unavailable or older than max_age_sec.
        """
        ...

    @abstractmethod
    def get_health(self, vehicle_id: int) -> VehicleHealth:
        """Get the current health status of the vehicle."""
        ...

    @abstractmethod
    def submit_setpoint(
        self,
        vehicle_id: int,
        setpoint: ValidatedSetpoint,
    ) -> CommandAck:
        """Submit a validated setpoint to the autopilot.

        The setpoint MUST have passed through the CommandValidationSafetyLayer
        before submission. Returns a CommandAck with acceptance status and reason.
        """
        ...

    @abstractmethod
    def request_mode_change(
        self,
        vehicle_id: int,
        target_mode: str,
        authorization_token: Optional[str] = None,
    ) -> CommandAck:
        """Request a mode change on the vehicle.

        The authorization_token is required for mode-changing commands
        (arming, takeoff, mode changes). Default mode must never arm or
        take off without explicit, validated authorization.
        """
        ...

    @abstractmethod
    def get_setpoint_history(self) -> List[ValidatedSetpoint]:
        """Get history of submitted setpoints for debugging/monitoring."""
        ...

    @abstractmethod
    def get_mode_change_history(self) -> List[tuple[int, str, Optional[str]]]:
        """Get history of mode-change requests for debugging/monitoring."""
        ...

    @abstractmethod
    def clear_history(self) -> None:
        """Clear all internal history buffers."""
        ...

    # ------------------------------------------------------------------
    # Convenience helpers (optional overrides)
    # ------------------------------------------------------------------
    def convert_frame(
        self,
        pos_ned: Tuple[float, float, float],
        from_frame: CoordinateFrame = CoordinateFrame.NED_LOCAL,
        to_frame: CoordinateFrame = CoordinateFrame.WGS84_GPS,
        home_lat: float = 0.0,
        home_lon: float = 0.0,
        home_alt: float = 0.0,
    ) -> Tuple[float, float, float]:
        """Convert between coordinate frames using CoordinateConverter."""
        return CoordinateConverter.wgs84_to_ned if from_frame == CoordinateFrame.WGS84_GPS and to_frame == CoordinateFrame.NED_LOCAL \
            else CoordinateConverter.ned_to_wgs84 if from_frame == CoordinateFrame.NED_LOCAL and to_frame == CoordinateFrame.WGS84_GPS \
            else (pos_ned if from_frame == to_frame else pos_ned)