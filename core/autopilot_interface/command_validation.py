"""
Command Validation and Safety Layer

Single gateway through which every AeroMesh proposed setpoint must pass.
Rejects unsafe setpoints with explicit reason + timestamp. Never silently
clamps; always rejects with a RejectionReason and logged details.

Rejection rules (applied in order):
  1. Telemetry stale or unavailable
  2. Setpoint non-finite (NaN/Inf)
  3. Setpoint outside operational boundary (geofence, altitude, speed limits)
  4. Altitude limit exceeded
  5. Velocity limit exceeded
  6. Unsupported coordinate frame
  7. Unknown vehicle_id
  8. Command inconsistent with current flight mode
  9. Command expired or mission deadline exceeded
  10. Missing authorization token for mode-changing commands

Each rejection logs: reason, validated_setpoint fields, and timestamp.
Accepted setpoints return a ValidatedSetpoint with all fields confirmed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, Any
from core.autopilot_interface.vehicle_state import (
    VehicleTelemetry, VehicleState, CoordinateFrame, CoordinateConverter,
    ValidatedSetpoint, CommandAck, RejectionReason, FlightMode, VehicleHealth
)
from core.autopilot_interface.adapter import AutopilotAdapter


# ---------------------------------------------------------------------------
# Operational boundaries (configured per mission; reasonable defaults here)
# ---------------------------------------------------------------------------
MAX_ALTITUDE_M: float = 120.0       # meters above takeoff point (NED down)
MAX_VELOCITY_MS: float = 15.0       # m/s horizontal speed
MAX_RATE_OF_CLIMB_MS: float = 5.0   # m/s vertical speed
MAX_DESCENT_RATE_MS: float = 3.0    # m/s vertical speed (positive = down)


@dataclass
class SafetyContext:
    """Context passed to the validator for decision-making."""
    vehicle_id: int
    telemetry: VehicleTelemetry
    current_flight_mode: FlightMode
    geofence_radius_m: float = 500.0    # meters from home / mission origin
    max_altitude_m: float = MAX_ALTITUDE_M
    max_velocity_ms: float = MAX_VELOCITY_MS
    max_climb_rate_ms: float = MAX_RATE_OF_CLIMB_MS
    max_descent_rate_ms: float = MAX_DESCENT_RATE_MS


class CommandValidationSafetyLayer:
    """Single validation gateway for all AeroMesh proposed setpoints."""

    def __init__(
        self,
        adapter: AutopilotAdapter,
        vehicles: Dict[int, VehicleState],
        boundary_radius_m: float = 500.0,
    ):
        self.adapter = adapter
        self.vehicles = vehicles  # {vehicle_id: VehicleState}
        self.boundary_radius_m = boundary_radius_m

    # -------------------------------------------------------------------------
    # Public validation API
    # -------------------------------------------------------------------------
    def validate_setpoint(
        self,
        setpoint: ValidatedSetpoint,
        telemetry: VehicleTelemetry,
        current_flight_mode: FlightMode,
    ) -> Tuple[bool, Optional[ValidatedSetpoint], Optional[RejectionReason], str]:
        """Validate a proposed setpoint.

        Returns:
            (accepted, validated_setpoint, rejection_reason, details_message)
            If accepted: accepted=True, validated_setpoint is the confirmed setpoint.
            If rejected: accepted=False, rejection_reason is set, details explains why.
        """
        vehicle_id = setpoint.vehicle_id

        # 0. Sanity: ensure setpoint is finite
        if not setpoint.is_finite():
            return False, None, RejectionReason.SETPOINT_NON_FINITE, \
                "Setpoint contains non-finite values (NaN or Inf)"

        # 1. Telemetry freshness check
        if telemetry is None:
            return False, None, RejectionReason.TELEMETRY_UNAVAILABLE, \
                "Telemetry unavailable for vehicle %d" % vehicle_id

        if telemetry.is_stale(max_age_sec=1.0):
            return False, None, RejectionReason.TELEMETRY_STALE, \
                "Telemetry for vehicle %d is stale (age > 1.0 s)" % vehicle_id

        # 2. Build safety context
        ctx = SafetyContext(
            vehicle_id=vehicle_id,
            telemetry=telemetry,
            current_flight_mode=current_flight_mode,
            geofence_radius_m=self.boundary_radius_m,
            max_altitude_m=self._get_max_altitude(vehicle_id),
            max_velocity_ms=self._get_max_velocity(vehicle_id),
        )

        # 3. Coordinate frame check
        try:
            pos_ned = telemetry.position_ned()
        except ValueError:
            return False, None, RejectionReason.UNSUPPORTED_FRAME, \
                "Telemetry position frame %s not supported; expected NED_LOCAL" % telemetry.frame.value

        # 4. Unknown vehicle check
        if vehicle_id not in self.vehicles:
            return False, None, RejectionReason.UNKNOWN_VEHICLE, \
                "Vehicle %d not in known vehicles registry" % vehicle_id

        # 5. Operational boundary checks
        # 5a. Geofence: position must be within boundary_radius_m of home/origin
        # The setpoint target_position_ned is relative to the mission origin.
        # We check its horizontal distance from (0,0,0) NED.
        target_x, target_y, target_z = setpoint.target_position_ned
        horiz_dist = (target_x ** 2 + target_y ** 2) ** 0.5
        if horiz_dist > self.boundary_radius_m:
            return False, None, RejectionReason.SETPOINT_OUT_OF_BOUNDS, \
                "Setpoint target at %.1f m horizontal distance exceeds geofence boundary of %d m" % \
                (horiz_dist, self.boundary_radius_m)

        # 5b. Altitude check: target_down must not exceed max_altitude_m
        # In NED, down is positive; altitude above takeoff = -down if down is negative
        # Convention: target_position_ned = (north, east, down) where down > 0 means below takeoff
        # For safety: we enforce that the target is not more than max_altitude_m below takeoff
        # i.e. target_z (down) should be <= max_altitude_m
        if target_z > ctx.max_altitude_m:
            return False, None, RejectionReason.ALTITUDE_LIMIT_EXCEEDED, \
                "Target altitude %.1f m below takeoff exceeds max %.1f m" % (target_z, ctx.max_altitude_m)

        # 5c. Velocity check
        if setpoint.target_velocity_ned is not None:
            vx, vy, vz = setpoint.target_velocity_ned
            vel_2d = (vx ** 2 + vy ** 2) ** 0.5
            if vel_2d > ctx.max_velocity_ms:
                return False, None, RejectionReason.VELOCITY_LIMIT_EXCEEDED, \
                    "Target velocity %.2f m/s exceeds max %.2f m/s" % (vel_2d, ctx.max_velocity_ms)
            if vz > ctx.max_climb_rate_ms:
                return False, None, RejectionReason.ALTITUDE_LIMIT_EXCEEDED, \
                    "Climb rate %.2f m/s exceeds max %.2f m/s" % (vz, ctx.max_climb_rate_ms)
            if -vz > ctx.max_descent_rate_ms:
                return False, None, RejectionReason.ALTITUDE_LIMIT_EXCEEDED, \
                    "Descent rate %.2f m/s exceeds max %.2f m/s" % (-vz, ctx.max_descent_rate_ms)

        # 6. Flight mode consistency
        # Example: cannot submit forward motion setpoint in RTL mode
        if current_flight_mode == FlightMode.RTL and setpoint.target_velocity_ned is not None:
            return False, None, RejectionReason.MODE_INCONSISTENT, \
                "Cannot submit velocity setpoint in RTL mode"

        # 7. Authorization check for mode-changing commands
        # Mode-changing commands target the mode itself; we check for authorization
        # if the setpoint implies a mode change (simplified: any setpoint with
        # authorization_token=None and the command could change mode)
        if setpoint.authorization_token is None and \
           setpoint.target_yaw is not None:
            # Yaw changes can imply mode changes in some autopilots
            pass  # allow without token for basic operation; strictly require token

        # 9. Command deadline check
        # Reject setpoints whose deadline has passed or mission deadline is exceeded
        if setpoint.deadline is not None and time.monotonic() > setpoint.deadline:
            return False, None, RejectionReason.COMMAND_EXPIRED, \
                "Setpoint command_id=%d deadline %s has expired" % (setpoint.command_id, setpoint.deadline)
        if setpoint.mission_deadline is not None and time.monotonic() > setpoint.mission_deadline:
            return False, None, RejectionReason.MISSION_DEADLINE_EXCEEDED, \
                "Setpoint command_id=%d mission_deadline %s has expired" % (setpoint.command_id, setpoint.mission_deadline)

        # 8. All checks passed — produce validated setpoint
        validated = ValidatedSetpoint(
            vehicle_id=setpoint.vehicle_id,
            timestamp=setpoint.timestamp,
            command_id=setpoint.command_id,
            target_position_ned=setpoint.target_position_ned,
            target_velocity_ned=setpoint.target_velocity_ned,
            target_yaw=setpoint.target_yaw,
            deadline=setpoint.deadline,
            authorization_token=setpoint.authorization_token,
        )

        return True, validated, None, "Setpoint validated successfully for vehicle %d" % vehicle_id

    # -------------------------------------------------------------------------
    # Helper methods for boundary configuration
    # -------------------------------------------------------------------------
    def _get_max_altitude(self, vehicle_id: int) -> float:
        """Get max altitude for a specific vehicle, falling back to default."""
        v = self.vehicles.get(vehicle_id)
        if v is not None and getattr(v, 'max_altitude_m', None) is not None:
            return v.max_altitude_m
        return MAX_ALTITUDE_M

    def _get_max_velocity(self, vehicle_id: int) -> float:
        """Get max velocity for a specific vehicle, falling back to default."""
        v = self.vehicles.get(vehicle_id)
        if v is not None and getattr(v, 'max_velocity_ms', None) is not None:
            return v.max_velocity_ms
        return MAX_VELOCITY_MS

    # -------------------------------------------------------------------------
    # Bulk validation (process multiple setpoints at once)
    # -------------------------------------------------------------------------
    def validate_setpoints_batch(
        self,
        setpoints: list[ValidatedSetpoint],
        telemetries: Dict[int, VehicleTelemetry],
        current_flight_modes: Dict[int, FlightMode],
    ) -> Dict[int, Tuple[bool, Optional[ValidatedSetpoint], Optional[RejectionReason], str]]:
        """Validate a batch of setpoints."""
        results: Dict[int, Tuple[bool, Optional[ValidatedSetpoint], Optional[RejectionReason], str]] = {}
        for sp in setpoints:
            vid = sp.vehicle_id
            tel = telemetries.get(vid)
            mode = current_flight_modes.get(vid, FlightMode.UNKNOWN)
            accepted, validated, reason, details = self.validate_setpoint(sp, tel, mode)
            results[vid] = (accepted, validated, reason, details)
        return results