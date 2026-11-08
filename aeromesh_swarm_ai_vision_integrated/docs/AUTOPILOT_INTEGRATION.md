# AutoPilot Integration Documentation

## Overview
This document describes the AeroMesh-Swarm auto-pilot integration architecture, interfaces, and validation procedures for the IIT Bombay Techfest Pushpak Grand Challenge 2026, Stage 2.

## Architecture Philosophy
- **Hardware-independent design**: The integration layer is abstracted behind `AutopilotAdapter` interfaces, enabling simulation-first development.
- **Safety-first**: All commands pass through a `CommandValidationSafetyLayer` before submission. Default mode never arms or takes off.
- **Two-mode operation**: 
  1. **Preview mode**: Proposed setpoints are computed but not transmitted to the autopilot.
  2. **Explicit command mode**: Commands are transmitted only when `SITL_COMMAND_MODE_ENABLED` is configured.
- **Modular adapters**: PX4 SITL, ArduPilot SITL, and a deterministic mock adapter implement the same API.

## Interface Summary

### AutopilotAdapter API
All adapters implement this abstract base class (`core/autopilot_interface/adapter.py`):

| Method | Description |
|--------|-------------|
| `connect(vehicle_id, config)` | Establish connection to autopilot |
| `disconnect(vehicle_id)` | Cleanly terminate connection |
| `is_connected(vehicle_id)` | Check connection status |
| `get_telemetry(vehicle_id, max_age_sec)` | Receive timestamped telemetry |
| `get_health(vehicle_id)` | Get vehicle health status |
| `submit_setpoint(vehicle_id, setpoint)` | Submit validated setpoint; returns `CommandAck` |
| `request_mode_change(vehicle_id, target_mode, authorization_token)` | Request mode change with authorization |
| `get_setpoint_history()` | Inspect submitted setpoints (debugging) |
| `get_mode_change_history()` | Inspect mode-change requests (debugging) |
| `clear_history()` | Clear internal history buffers |

### ValidatedSetpoint
All setpoints must be wrapped in `ValidatedSetpoint` after passing through `CommandValidationSafetyLayer`:

```python
@dataclass
class ValidatedSetpoint:
    vehicle_id: int
    timestamp: float
    command_id: int
    target_position_ned: tuple[float, float, float]  # (north, east, down) meters
    target_velocity_ned: Optional[tuple[float, float, float]] = None
    target_yaw: Optional[float] = None
    deadline: Optional[float] = None
    authorization_token: Optional[str] = None
```

### CommandAck
Acknowledgement returned by `submit_setpoint`:

```python
@dataclass
class CommandAck:
    command_id: int
    vehicle_id: int
    accepted: bool
    reason: str = ""
    timestamp: float = field(default_factory=time.monotonic)
    raw_response: Optional[dict] = None
```

### VehicleTelemetry
Telemetry received from the autopilot:

```python
@dataclass
class VehicleTelemetry:
    vehicle_id: int
    timestamp: float
    position: tuple[float, float, float]  # frame-specific
    velocity: tuple[float, float, float]
    frame: CoordinateFrame = CoordinateFrame.NED_LOCAL
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0
    battery_voltage: float = 0.0
    battery_current: float = 0.0
    battery_remaining: float = 1.0
    flight_mode: FlightMode = FlightMode.UNKNOWN
    armed: bool = False
    health: VehicleHealth = VehicleHealth.UNKNOWN
    gps_fix_type: int = 0
    satellites_visible: int = 0
    hdop: float = 99.9
    vdop: float = 99.9
    rssi: float = -100.0
    link_quality: float = 0.0
    raw_data: dict = field(default_factory=dict)
```

### CoordinateFrames
Explicit frame enumeration prevents mix-ups:

- `CoordinateFrame.NED_LOCAL` — North-East-Down local tangent (meters, origin at home/GCS)
- `CoordinateFrame.WGS84_GPS` — Latitude/Longitude/Altitude (degrees, degrees, meters MSL)
- `CoordinateFrame.ENU_LOCAL` — East-North-Up local tangent
- `CoordinateFrame.BODY_FRD` — Body Forward-Right-Down

Conversion is handled by `CoordinateConverter` (`core/autopilot_interface/vehicle_state.py`):
- `ned_to_wgs84(ned_pos, home_lat, home_lon, home_alt)`
- `wgs84_to_ned(wgs84_pos, home_lat, home_lon, home_alt)`
- `enu_to_ned(enu_pos)`
- `ned_to_enu(ned_pos)`
- `body_to_ned(body_vel, roll, pitch, yaw)`

### RejectionReason
Standardized rejection reasons from `CommandValidationSafetyLayer`:

| Reason | When Applied |
|--------|-------------|
| `TELEMETRY_STALE` | Telemetry age > 1.0 s |
| `TELEMETRY_UNAVAILABLE` | No telemetry received |
| `SETPOINT_NON_FINITE` | NaN or Inf in setpoint values |
| `SETPOINT_OUT_OF_BOUNDS` | Target outside geofence or operational boundary |
| `ALTITUDE_LIMIT_EXCEEDED` | Target altitude exceeds max |
| `VELOCITY_LIMIT_EXCEEDED` | Target velocity exceeds max |
| `UNSUPPORTED_FRAME` | Telemetry position frame not NED_LOCAL |
| `UNKNOWN_VEHICLE` | vehicle_id not in registry |
| `MODE_INCONSISTENT` | Setpoint inconsistent with current flight mode |
| `COMMAND_EXPIRED` | Setpoint deadline passed |
| `MISSION_DEADLINE_EXCEEDED` | Setpoint mission deadline exceeded |
| `MISSING_AUTHORIZATION` | Mode-changing command without authorization token |
| `INVALID_COMMAND` | General invalid command |
| `AUTOPILOT_UNHEALTHY` | Autopilot reports unhealthy state |
| `AUTOPILOT_UNSUPPORTED_STATE` | Autopilot state not supported by adapter |

## Integration Phases

### Phase 1: Simulation Adapter
- **File**: `core/autopilot_interface/adapter.py` (abstract) + `mock_adapter.py`
- **Status**: Implemented and tested
- **Behavior**: `SimulatorAdapter` wraps existing simulation behavior. `MockAutopilotAdapter` provides deterministic telemetry without physical commands.

### Phase 2: SITL Telemetry-Only
- Connect to PX4 SITL (MAVLink) **or** ArduPilot SITL (MAVLink).
- Receive position, velocity, battery, mode, health telemetry.
- Confirm timestamps, coordinate frames, vehicle identity.
- Display telemetry without issuing flight commands.
- **Default**: Never arms, never takes off.

### Phase 3: Preview Mode
- Compute proposed setpoints but do not transmit.
- Set `SITL_COMMAND_MODE_ENABLED=false` (default).
- `submit_setpoint` computes and logs but returns `CommandAck(accepted=True, reason="mock: preview, not transmitted")`.

### Phase 4: Explicit Command Mode
- Enable with `SITL_COMMAND_MODE_ENABLED=true` in environment/config.
- `submit_setpoint` transmits validated commands to SITL via MAVLink.
- All commands have already passed through `CommandValidationSafetyLayer`.
- Authorization tokens required for mode-changing commands.

### Phase 5: Multi-UAV Stress
- Stress test 1, 2, 3, 5, 10+ UAVs across 15 failure scenarios.
- Measure p95/p99 latency, jitter, CPU/memory.
- Report initial/expected/actual/pass-fail + raw evidence.

## Installation and Setup

### Dependencies (already installed)
- `numpy`
- `networkx`
- `pytest`

### SITL Dependencies (verify after inspection)
- **PX4 SITL**: `px4 sitl` with MAVLink 2.x
  - Or PX4 SITL with ROS 2 interface
- **ArduPilot SITL**: `arducopter` or `plane` with MAVLink 2.x

### Environment Configuration
| Variable | Description | Default |
|----------|-------------|---------|
| `SITL_COMMAND_MODE_ENABLED` | Enable explicit command transmission | `false` |
| `SITL_AUTOPILOT_TYPE` | Which autopilot to connect to | `mock` |
| `SITL_HOME_LAT` | Home latitude for coordinate conversions | `28.7041` (IIT Bombay) |
| `SITL_HOME_LON` | Home longitude for coordinate conversions | `76.7731` |
| `SITL_HOME_ALT` | Home altitude (meters MSL) | `10.0` |

## Safety Gates (Enforced by CommandValidationSafetyLayer)

Every submitted setpoint is validated against these gates:

1. **Finite values**: NaN/Inf rejected
2. **Telemetry freshness**: Stale telemetry (>1s old) rejected
3. **Geofence**: Target must be within configured radius of mission origin
4. **Altitude limits**: Target below max_altitude_m (default 120m)
5. **Velocity limits**: Target velocity below max_velocity_ms (default 15 m/s)
6. **Coordinate frame**: Telemetry must be NED_LOCAL; conversion errors rejected
7. **Known vehicle**: vehicle_id must be registered
8. **Flight mode consistency**: Setpoint consistent with current flight mode
9. **Authorization**: Mode-changing commands require authorization_token
10. **Mission deadline**: Setpoint must not exceed configured deadline

Rejected setpoints return `CommandAck(accepted=False, reason="<RejectionReason>")`. No silent clamping.

## HITL and Ground Testing

### Hardware Test Checklist (`HARDWARE_TEST_CHECKLIST.md`)
- [ ] Autopilot calibration (IMU, magnetometer, barometer)
- [ ] GPS fix quality (3D fix, HDOP < 2.0)
- [ ] Telemetry link range test (telemetry received at max expected distance)
- [ ] Battery voltage and current monitoring
- [ ] Failsafe configuration (low battery, loss of RC, loss of telemetry)
- [ ] Operator override procedure verified
- [ ] Command-gateway rejection confirmation (all rejection reasons logged)
- [ ] Mock-to-SITL transition verification (mock adapter → SITL adapter swap)
- [ ] GPS drop simulation (verify position-loss handling)
- [ ] Battery low return-to-home test
- [ ] RF interference/jamming scenario test (verify degradation model)

## Known Limitations
- Hazard-aware routing and task allocation not yet propagated from `DynamicEventManager`
- Coordinate-frame conversions use flat-earth approximation (< 10 km from home)
- Real-time timing measurements require instrumented benchmarks (Phase 5)
- SITL integration path (PX4 vs ArduPilot) chosen after environment inspection
- Default mode never arms or takes off; explicit config required for command mode

## Version and Metadata
- **Project**: AeroMesh-Swarm — Stage 2
- **Competition**: IIT Bombay Techfest Pushpak Grand Challenge 2026
- **Generated**: 2026-10-11
- **Safety**: Default never arms/takes off; command gateway rejects unsafe inputs with logs