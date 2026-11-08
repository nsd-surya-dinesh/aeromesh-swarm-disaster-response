# SITL Validation Documentation

## Overview
This document describes the Software-in-the-Loop (SITL) validation procedures
for AeroMesh-Swarm Stage 2. SITL allows testing the integration layer against
a simulated autopilot (PX4 or ArduPilot) without requiring physical UAV hardware.

## Validation Structure
SITL validation is organized into progressive levels. Each level must pass
before advancing to the next. The default mode must never arm a vehicle,
initiate takeoff, or execute a physical mission.

### Level 1: Simulation Only
**Requirement**: All existing pytest suites pass (42/42 baseline, 19/19 interference, 10/10 route recovery).
**Test Command**: `python -m pytest tests/ -v`
**Evidence**: Test output showing all tests passing.
**Gate**: Must pass before advancing.

### Level 2: SITL Telemetry-Only
**Requirement**: Adapter successfully receives telemetry from SITL autopilot
without issuing any flight commands.
**Test Checklist**:
- [ ] `connect(vehicle_id, config)` returns True
- [ ] `get_telemetry(vehicle_id)` returns timestamped data
  - Position (NED_LOCAL frame confirmed)
  - Velocity (NED_LOCAL frame confirmed)
  - Battery level (voltage, current, remaining ratio)
  - Flight mode (confirmed as simulated, not physical)
  - Health status (HEALTHY, DEGRADED, or CRITICAL)
  - GPS fix type and satellite count
  - RSSI and link quality
- [ ] `is_connected(vehicle_id)` returns True
- [ ] `get_health(vehicle_id)` returns correct health status
- [ ] Telemetry is stale-aware: `is_stale(max_age_sec=1.0)` works correctly
- [ ] No commands are transmitted during telemetry-only mode
- [ ] `request_mode_change()` does NOT arm or take off the vehicle

**Evidence Required**:
1. Telemetry data printout showing all fields populated
2. Confirmation that `submit_setpoint()` was NOT transmitted (mock adapter
   returns accepted but logs "no physical transmission")
3. Mode change history showing no actual mode change occurred
4. `raw_data` field contains any extra autopilot-specific fields

**Test Command Structure** (example):
```python
def test_sitl_telemetry_only():
    adapter = SimulatorAdapter(mission_state)
    adapter.connect(0, {})
    
    # Verify connection
    assert adapter.is_connected(0) == True
    
    # Receive telemetry
    telemetry = adapter.get_telemetry(0, max_age_sec=1.0)
    assert telemetry is not None
    assert telemetry.vehicle_id == 0
    assert telemetry.frame == CoordinateFrame.NED_LOCAL
    assert telemetry.battery_remaining >= 0.0
    assert telemetry.flight_mode != FlightMode.UNKNOWN  # Should have a mode
    
    # Verify no commands sent
    history = adapter.get_setpoint_history()
    assert len(history) == 0  # No setpoints submitted in telemetry-only mode
    
    # Verify mode change does not arm
    ack = adapter.request_mode_change(0, FlightMode.GUIDED, auth_token="test")
    assert ack.accepted == True  # Mock accepts, but...
    # Verify vehicle not armed (checked via telemetry or mission state)
```

### Level 3: Preview Mode
**Requirement**: Proposed setpoints are computed but not transmitted to the
autopilot. The system operates in "compute-propose-but-don't-send" mode.
**Configuration**: `SITL_COMMAND_MODE_ENABLED=false` (default, enforced by
safety layer).

**Test Checklist**:
- [ ] `submit_setpoint()` computes and logs the setpoint but returns
  `CommandAck(accepted=True, reason="preview: setpoint computed, not transmitted")`
- [ ] Setpoint history shows the proposed command but no transmission
- [ ] `request_mode_change()` does not arm or take off
- [ ] All validation gates still apply (telemetry freshness, geofence, limits)
- [ ] Setpoint targets are finite, within bounds, and consistent with flight mode

**Evidence Required**:
1. Setpoint history showing proposed commands with `reason="preview: setpoint computed, not transmitted"`
2. Confirmation that autopilot did NOT receive the setpoint (MAVLink logs,
   simulation state unchanged)
3. Telemetry remains unchanged after `submit_setpoint()` call
4. All validation rejections still logged correctly

**Test Structure**:
```python
def test_preview_mode():
    adapter = SimulatorAdapter(mission_state)
    adapter.connect(0, {})
    safety = CommandValidationSafetyLayer(adapter, {vehicles})
    
    # Telemetry is fresh
    telemetry = adapter.get_telemetry(0)
    assert telemetry is not None
    
    # Propose a setpoint (will be validated and logged, not transmitted)
    setpoint = ValidatedSetpoint(
        vehicle_id=0,
        timestamp=time.monotonic(),
        command_id=42,
        target_position_ned=(0.0, 0.0, -10.0),  # 10m above takeoff
        target_velocity_ned=(1.0, 0.0, 0.0),
        authorization_token=None,  # No token needed for preview
    )
    
    # Submit — should be accepted but logged as preview
    ack = safety.validate_and_submit(setpoint, telemetry, FlightMode.GUIDED)
    # In preview mode: ack.accepted=True but no transmission
    
    # Verify setpoint was logged but not sent
    history = adapter.get_setpoint_history()
    assert len(history) == 1
    # The setpoint is in history but autopilot state unchanged
```

### Level 4: Explicit Command Mode
**Requirement**: Commands are transmitted to the SITL autopilot only when
`SITL_COMMAND_MODE_ENABLED=true` is explicitly configured. This is the first
level where physical setpoints are actually sent.
**Configuration**: `SITL_COMMAND_MODE_ENABLED=true` in environment or config file.

**Test Checklist**:
- [ ] `SITL_COMMAND_MODE_ENABLED=true` enables command transmission
- [ ] `SITL_COMMAND_MODE_ENABLED=false` (default) blocks all transmissions
- [ ] All validation gates still apply (same 10 gates as COMMAND_SAFETY.md)
- [ ] Authorization tokens required for mode-changing commands
- [ ] `submit_setpoint()` transmits via the adapter's concrete implementation
- [ ] `CommandAck` returned from actual autopilot (or mock SITL adapter)

**Evidence Required**:
1. With `SITL_COMMAND_MODE_ENABLED=true`: MAVLink messages or simulation
   state changes confirm setpoint transmission
2. With `SITL_COMMAND_MODE_ENABLED=false`: No transmission occurs, setpoints
   are only logged
3. Authorization token requirements enforced
4. Rejection logs captured for both modes

**Transition**:
The transition from Level 3 to Level 4 is controlled by a configuration
flag, not by code changes. The same `submit_setpoint()` call behaves
differently based on the flag.

### Level 5: Multi-UAV Simulation Stress
**Requirement**: 15 failure scenarios across 1, 2, 3, 5, 10+ UAVs all pass in
simulation. Reports initial/expected/actual/pass-fail + raw evidence.
**Test Scenarios** (see Phase 6 documentation for full list):
1. Normal mission execution
2. Loss of one UAV
3. Relay failure and replacement
4. Simultaneous failures
5. GCS disconnection
6. Intermittent radio connectivity
7. Stale or delayed telemetry
8. Low battery and return-to-home
9. Invalid or rejected setpoints
10. GPS/position-estimate loss (if supported)
11. Unexpected flight mode
12. Duplicate, delayed, or out-of-order messages
13. One vehicle reconnecting after communications outage
14. No available replacement relay
15. Mission cancellation and operator takeover

**Evidence Format per Scenario**:
```
Scenario: <scenario_number>_<description>
Initial State: <UAV positions, battery levels, telemetry state, config>
Expected Behavior: <what should happen per design>
Actual Behavior: <what actually happened, with raw data>
Pass/Fail: <pass or fail result>
Raw Evidence: <logs, telemetry snapshots, MAVLink messages, timestamps>
```

**Test Command**:
```python
# Example: test scenario 3 - relay failure and replacement
def test_relay_failure_replacement():
    # Setup: 3 UAVs in mesh, UAV 1 is the relay
    # Break: UAV 1 link quality set to 0 (severity=1 jamming)
    # Observe: Router reroutes through UAV 2 or 3
    # Replacement: Restore UAV 1, verify path re-converges
    # Metrics: reroute_attempts, successful_recoveries, recovery_latencies
    pass
```

### Level 6: Multi-UAV Supervised Flight
**Requirement**: Multi-UAV flight only when all prior levels (1-5) have passed
and hardware has been validated. This is the final acceptance gate.
**Preconditions**:
- [ ] Level 1: All simulation tests pass
- [ ] Level 2: SITL telemetry-only validated
- [ ] Level 3: Preview mode verified
- [ ] Level 4: Explicit command mode with `SITL_COMMAND_MODE_ENABLED=true`
- [ ] Level 5: All 15/15 scenarios pass in simulation stress test
- [ ] Hardware: All physical components calibrated and checked (HARDWARE_TEST_CHECKLIST.md)
- [ ] Safety: Operator present with full override capability

**Flight Requirements**:
- [ ] All UAVs achieve GPS fix before takeoff
- [ ] Geofence enforced during flight (max radius from home)
- [ ] Failsafe behaviors tested and confirmed (loss of telemetry, low battery)
- [ ] Operator override procedure verified
- [ ] No unauthorized arming or takeoff
- [ ] All command rejections logged and reviewed post-flight

**Post-Flight**:
- [ ] Review all command rejection logs
- [ ] Verify telemetry completeness and freshness
- [ ] Compare actual behavior against expected for each scenario
- [ ] Update KNOWN_LIMITATIONS.md with any new findings
- [ ] Document lessons learned for future iterations

## SITL Adapter Selection

### PX4 SITL Path
**Choose when**: PX4 flight stack is available and MAVLink 2.x is configured.
**Capabilities**:
- Full MAVLink 2.x message set
- POSITION_TARGET_LOCAL_NED setpoints
- ATTITUDE setpoints
- GPS_RAW telemetry
- BATTERY_STATUS telemetry
- MODE telemetry
- Comprehensive SITL test suite

**Setup**:
```bash
# Install PX4 SITL
git clone https://github.com/PX4/PX4-Autopilot.git
cd PX4-Autopilot
pip install -e .
px4 sitl # starts simulation

# In Python:
from core.autopilot_interface.simulator_adapter import SimulatorAdapter
adapter = SimulatorAdapter(mission_state)
adapter.connect(0, {'autopilot_type': 'px4'})
```

### ArduPilot SITL Path
**Choose when**: ArduPilot flight stack is available and MAVLink 2.x is configured.
**Capabilities**:
- MAVLink 2.x message set
- COMMAND_DO_SETPOSITION setpoints
- GPS_INFORMATION telemetry
- BATTERY_STATUS telemetry
- FLIGHT_MODE telemetry

**Setup**:
```bash
# Install ArduPilot SITL
pip install maavlink
ardupilot sitl # starts simulation

# In Python:
from core.autopilot_interface.simulator_adapter import SimulatorAdapter
adapter = SimulatorAdapter(mission_state)
adapter.connect(0, {'autopilot_type': 'ardupilot'})
```

### Mock Adapter (Always Available)
**Choose when**: No SITL environment is available, or for unit testing.
**Behavior**:
- Deterministic telemetry
- Never arms or takes off
- All setpoints logged, no transmission
- Mode changes acknowledged but not physically executed
- Used for unit tests and early development

## Coordinate Frame Considerations in SITL

### NED_LOCAL Frame (Used Internally)
- Position: (north, east, down) in meters from home
- Velocity: (vn, ve, vd) in m/s
- Right-handed system: North = forward, East = right, Down = down
- Origin: GCS/home location

### WGS84_GPS Frame (External)
- Position: (lat, lon, alt) in degrees and meters MSL
- Used for external communication (GPS, ground stations)
- Conversions handled by `CoordinateConverter`

### MAVLink Frame Mapping
- MAVLink typically uses NED_LOCAL for setpoints (`POSITION_TARGET_LOCAL_NED`)
- GPS data comes in WGS84_GPS and must be converted
- `CoordinateConverter.ned_to_wgs84()` and `wgs84_to_ned()` handle the conversion

**Safety**: Always verify the frame before sending setpoints. Sending GPS
coordinates to a local-frame autopilot (or vice versa) will cause undefined
behavior.

## Configuration Variables

| Variable | Description | Default | Overridable |
|----------|-------------|---------|-------------|
| `SITL_COMMAND_MODE_ENABLED` | Enable explicit command transmission | `false` | Yes (env/config) |
| `SITL_AUTOPILOT_TYPE` | Which autopilot to connect to | `mock` | Yes (env/config) |
| `SITL_HOME_LAT` | Home latitude for coordinate conversions | `28.7041` (IIT Bombay) | Yes |
| `SITL_HOME_LON` | Home longitude for coordinate conversions | `76.7731` (IIT Bombay) | Yes |
| `SITL_HOME_ALT` | Home altitude (meters MSL) | `10.0` | Yes |
| `SITL_MAX_ALTITUDE_M` | Maximum allowed altitude | `120.0` | Yes |
| `SITL_MAX_VELOCITY_MS` | Maximum allowed horizontal velocity | `15.0` | Yes |
| `SITL_GEOFENCE_RADIUS_M` | Geofence radius from home | `500.0` | Yes |

## Version and Metadata
- **Document**: `SITL_VALIDATION.md`
- **Project**: AeroMesh-Swarm — Stage 2
- **Competition**: IIT Bombay Techfest Pushpak Grand Challenge 2026
- **Generated**: 2026-10-11
- **Safety**: Default never arms/takes off; 6-level acceptance gates
- **Associated Files**:
  - `core/autopilot_interface/simulator_adapter.py` — SITL telemetry adapter
  - `core/autopilot_interface/command_validation.py` — validation gateway
  - `docs/COMMAND_SAFETY.md` — command safety gates
  - `docs/HARDWARE_TEST_CHECKLIST.md` — HITL preparation
  - `docs/KNOWN_LIMITATIONS.md` — documented gaps

## Acceptance Gate Progression

| Level | Description | Must Pass |
|-------|-------------|-----------|
| 1 | Simulation Only | All pytest suites pass (42/42, 19/19, 10/10) |
| 2 | SITL Telemetry-Only | Receive telemetry, no commands sent |
| 3 | Preview Mode | Compute setpoints, do not transmit |
| 4 | Explicit Command Mode | `SITL_COMMAND_MODE_ENABLED=true` sends commands |
| 5 | Multi-UAV Simulation Stress | 15/15 scenarios pass |
| 6 | Multi-UAV Supervised Flight | All prior + hardware validated |

*Level 6 is only reached when all prior levels have passed AND hardware has
been validated per HARDWARE_TEST_CHECKLIST.md. Default mode never arms/takes
off at any level.*