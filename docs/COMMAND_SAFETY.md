# Command Safety Documentation

## Overview
This document describes the command validation and safety architecture for
AeroMesh-Swarm Stage 2. All navigation setpoints and mode-changing commands
must pass through the `CommandValidationSafetyLayer` before submission to any
autopilot adapter.

## Safety Philosophy
- **Default mode never arms or takes off**: The system requires explicit
  authorization for any mode change that would arm motors or initiate takeoff.
- **No silent clamping**: Unsafe setpoints are always rejected with an explicit
  reason and logged timestamp. The system never silently clamps values and
  reports them as successful.
- **Autopilot retains low-level stabilization**: The safety layer validates
  high-level setpoints but does not replace the autopilot's stabilization or
  failsafe systems.
- **Explicit authorization for mode changes**: Arming, takeoff, and mode
  changes require an `authorization_token` in the `ValidatedSetpoint`.

## Validation Gates (Applied in Order)

Every proposed setpoint undergoes the following checks, applied sequentially:

### 1. Finite Values Check
- **Rejection reason**: `SETPOINT_NON_FINITE`
- **Applied when**: Any setpoint value is NaN or Inf
- **Example**: `target_position_ned = (float('nan'), 0.0, 0.0)`

### 2. Telemetry Freshness Check
- **Rejection reasons**: `TELEMETRY_STALE`, `TELEMETRY_UNAVAILABLE`
- **Applied when**: No telemetry received, or telemetry age > 1.0 s
- **Default max_age_sec**: 1.0 second (configurable per mission)

### 3. Coordinate Frame Check
- **Rejection reason**: `UNSUPPORTED_FRAME`
- **Applied when**: Telemetry position frame is not `NED_LOCAL`
- **Resolution**: Convert telemetry to NED_LOCAL frame using
  `CoordinateConverter.wgs84_to_ned()` or `CoordinateConverter.ned_to_ned()`

### 4. Geofence / Operational Boundary Check
- **Rejection reason**: `SETPOINT_OUT_OF_BOUNDS`
- **Applied when**: Target position horizontal distance from origin >
  `boundary_radius_m` (default 500.0 m)
- **Also checks**: Target altitude below `max_altitude_m` (default 120.0 m)

### 5. Altitude Limit Check
- **Rejection reason**: `ALTITUDE_LIMIT_EXCEEDED`
- **Applied when**: Target vertical speed or position exceeds limits:
  - Climb rate > `max_climb_rate_ms` (default 5.0 m/s)
  - Descent rate > `max_descent_rate_ms` (default 3.0 m/s)
  - Target altitude > `max_altitude_m` (default 120.0 m) below takeoff point

### 6. Velocity Limit Check
- **Rejection reason**: `VELOCITY_LIMIT_EXCEEDED`
- **Applied when**: Target horizontal velocity > `max_velocity_ms` (default 15.0 m/s)
- **Also checks**: Vertical velocity components exceed climb/descent rates

### 7. Unknown Vehicle Check
- **Rejection reason**: `UNKNOWN_VEHICLE`
- **Applied when**: `vehicle_id` not in the known vehicles registry

### 8. Flight Mode Consistency Check
- **Rejection reason**: `MODE_INCONSISTENT`
- **Applied when**: Setpoint is inconsistent with current flight mode
- **Example**: Submitting a forward velocity setpoint while in `RTL` mode

### 9. Authorization Check
- **Rejection reason**: `MISSING_AUTHORIZATION`
- **Applied when**: Mode-changing commands (arming, takeoff, mode change)
  lack an `authorization_token` in the `ValidatedSetpoint`
- **Default**: `authorization_token=None` is accepted for basic setpoint
  submission, but required for any command that changes vehicle state

### 10. Command Deadline Check
- **Rejection reason**: `COMMAND_EXPIRED`, `MISSION_DEADLINE_EXCEEDED`
- **Applied when**: `setpoint.deadline < time.monotonic()`
- **Mission deadline**: `setpoint.mission_deadline < time.monotonic()`

## Rejection Logging

Every rejection is logged with the following information:
- `reason`: `RejectionReason` enum value
- `rejection_details`: Human-readable description
- `timestamp`: `time.monotonic()` when the rejection occurred
- `vehicle_id`: The target vehicle's ID
- `command_id`: The setpoint's command ID (if available)
- `setpoint_fields`: Key fields from the validated setpoint (for debugging)

Logged entries are stored in the `CommandValidationSafetyLayer` and can be
exported for post-flight analysis.

## Accepted Setpoint Behavior

When a setpoint passes all validation gates:
- `validation_result.accepted = True`
- `validation_result.validated_setpoint` contains the confirmed setpoint
- `validation_result.rejection_reason = None`
- The setpoint is submitted via `AutopilotAdapter.submit_setpoint()`
- A `CommandAck` is returned from the adapter

Rejected setpoints return:
- `validation_result.accepted = False`
- `validation_result.validated_setpoint = None`
- `validation_result.rejection_reason` set to the appropriate `RejectionReason`
- `validation_result.rejection_details` with human-readable explanation
- **No CommandAck submitted** to the adapter (the gateway short-circuits)

## Configuration Per Mission

The `CommandValidationSafetyLayer` is configured per mission through:
- `boundary_radius_m`: Geofence radius in meters (default 500.0)
- `max_altitude_m`: Maximum altitude in meters (default 120.0)
- `max_velocity_ms`: Maximum horizontal velocity in m/s (default 15.0)
- `max_climb_rate_ms`: Maximum climb rate in m/s (default 5.0)
- `max_descent_rate_ms`: Maximum descent rate in m/s (default 3.0)
- `telemetry_max_age_sec`: Maximum telemetry freshness in seconds (default 1.0)
- `authorized_vehicles`: Set of vehicle IDs authorized for command submission

Example configuration:
```python
from core.autopilot_interface.command_validation import CommandValidationSafetyLayer
from core.autopilot_interface.adapter import MockAutopilotAdapter
from core.autopilot_interface.vehicle_state import VehicleState

adapter = MockAutopilotAdapter()
vehicles = {0: VehicleState(vehicle_id=0), 1: VehicleState(vehicle_id=1)}

safety_layer = CommandValidationSafetyLayer(
    adapter=adapter,
    vehicles=vehicles,
    boundary_radius_m=300.0,     # 300m geofence for this mission
    max_altitude_m=80.0,          # 80m max altitude
    max_velocity_ms=10.0,         # 10 m/s max velocity
    authorized_vehicles={0, 1},   # Only these UAVs can receive commands
)
```

## Safety Gate Diagrams

### Setpoint Validation Flow
```
Proposed Setpoint
       │
       ▼
[Finite Check] → PASSES / REJECTED (SETPOINT_NON_FINITE)
       │
       ▼
[Telemetry Freshness] → PASSES / REJECTED (TELEMETRY_STALE / TELEMETRY_UNAVAILABLE)
       │
       ▼
[Coordinate Frame Check] → PASSES / REJECTED (UNSUPPORTED_FRAME)
       │
       ▼
[Geofence Boundary] → PASSES / REJECTED (SETPOINT_OUT_OF_BOUNDS)
       │
       ▼
[Altitude Limits] → PASSES / REJECTED (ALTITUDE_LIMIT_EXCEEDED)
       │
       ▼
[Velocity Limits] → PASSES / REJECTED (VELOCITY_LIMIT_EXCEEDED)
       │
       ▼
[Unknown Vehicle] → PASSES / REJECTED (UNKNOWN_VEHICLE)
       │
       ▼
[Flight Mode Consistency] → PASSES / REJECTED (MODE_INCONSISTENT)
       │
       ▼
[Authorization Check] → PASSES / REJECTED (MISSING_AUTHORIZATION)
       │
       ▼
[Command Deadline] → PASSES / REJECTED (COMMAND_EXPIRED / MISSION_DEADLINE_EXCEEDED)
       │
       ▼
ALL PASSED → ValidatedSetpoint → submit_setpoint() → CommandAck
```

## Post-Flight Analysis

Rejection logs can be exported for post-flight analysis:

```python
# Export all rejections from a mission run
rejections = safety_layer.get_rejection_log()
with open('command_rejections.log', 'w') as f:
    for entry in rejections:
        f.write(f"{entry['timestamp']} | {entry['reason']} | vehicle {entry['vehicle_id']} | {entry['details']}\n")
```

The log includes:
- Timestamp of each rejection
- Rejection reason (RejectionReason enum)
- Vehicle ID
- Human-readable details
- Setpoint key fields (for correlation with mission log)

## Version and Metadata
- **Document**: `COMMAND_SAFETY.md`
- **Project**: AeroMesh-Swarm — Stage 2
- **Competition**: IIT Bombay Techfest Pushpak Grand Challenge 2026
- **Generated**: 2026-10-11
- **Safety Principle**: Default never arms/takes off; no silent clamping
- **Associated Files**:
  - `core/autopilot_interface/command_validation.py` — implementation
  - `core/autopilot_interface/adapter.py` — abstract API
  - `core/autopilot_interface/mock_adapter.py` — deterministic mock
  - `core/autopilot_interface/vehicle_state.py` — telemetry and state