# Hardware-in-the-Loop (HITL) and Ground-Testing Safety Checklist

## Pre-Flight Calibration and Setup

### 1. Autopilot Calibration
- [ ] **IMU Calibration**: Accelerometer and gyroscope zero-level calibration completed.
  - Use autopilot's built-in calibration procedure (typically via ground station).
  - Confirm no unusual bias or drift in sensor readings.
- [ ] **Magnetometer Calibration**: Compass calibration performed.
  - Rotate UAV through all orientations (45° intervals, minimum 8 positions).
  - Confirm declination angle matches local magnetic model.
- [ ] **Barometer Calibration**: Pressure sensor zero-level set at known altitude.
  - Calibrate at ground level before flight.
  - Verify altitude readings match known reference.
- [ ] **Gyro Temperature Compensation**: Verify gyro readings are stable across
  expected temperature range (typically -10°C to +40°C for competition env).

### 2. GPS Setup
- [ ] **GPS Fix Quality**: At least 3D GPS fix confirmed (satellites_visible >= 6).
  - HDOP < 2.0 (ideally < 1.0) for good positional accuracy.
  - VDOP < 3.0 for vertical accuracy.
- [ ] **Home Position Saved**: GCS home position locked and stored.
  - Home position used for geofence, RTH (Return-to-Home), and coordinate conversions.
  - Verify home position matches known survey point (IIT Bombay coordinates:
    28.7041°N, 76.7731°E, ~10m alt).
- [ ] **GPS Antenna Placement**: Antenna has clear sky view, away from
  electrical interference sources (telemetry radios, power cables).

### 3. Telemetry Radio Link
- [ ] **Radio Range Test**: Transmit at maximum expected distance; confirm
  telemetry link quality > 90% PDR.
  - Measure RSSI at range; verify it's within expected path loss model.
- [ ] **Radio Redundancy**: Two independent radio modules (if available) or
  single module with frequent health checks.
- [ ] **Failsafe Radio Loss Configuration**: Autopilot configured to trigger
  failsafe if telemetry link lost for >2 seconds.
  - Test by temporarily disabling radio; confirm failsafe triggers correctly.

### 4. Battery and Power System
- [ ] **Battery Voltage Calibration**: Voltage divider ratio confirmed against
  known reference (digital multimeter).
  - Expected per-cell voltage: 3.7V nominal, 4.2V full, 3.0V empty.
- [ ] **Current Sensor Calibration**: Ammeter calibrated (shunt resistor or
  Hall-effect sensor). Verify current reading matches known load.
- [ ] **Battery Low Failsafe**: Configured low-battery voltage threshold
  (typically 3.5V per cell or configurable % remaining).
  - Test: reduce battery voltage to threshold; confirm failsafe triggers.
- [ ] **Power Distribution**: All power cables securely connected; no loose
  connections or signs of overheating.
- [ ] **Power Module Rating**: Current and voltage ratings exceed maximum
  expected draw (include 20% safety margin).

### 5. Failsafe Configuration
- [ ] **Loss of Telemetry Failsafe**: Trigger behavior configured (hover, RTH,
  land, or specified mode).
  - Test: disable telemetry; confirm autopilot enters configured failsafe mode.
- [ ] **Loss of GPS Failsafe**: Behavior configured when GPS signal lost.
  - Test: disconnect GPS antenna; confirm safe transition.
- [ ] **Low Battery Failsafe**: Voltage/current threshold configured; behavior
  confirmed.
- [ ] **RC Signal Loss Failsafe**: If using RC override, behavior when RC
  signal lost (typically RTH or hover).
- [ ] **Motor Failsafe**: If individual motor failure, behavior configured
  (reduced thrust, controlled landing).

### 6. Operator Override Procedure
- [ ] **Override Switch/Button**: Physical or telemetry-based override mechanism
  confirmed functional.
- [ ] **Override Priority**: Operator command takes precedence over automated
  mission commands (per safety architecture).
- [ ] **Override Confirmation**: Visual or auditory confirmation when override
  is active.
- [ ] **Emergency Stop**: One-handed emergency stop procedure verified.
- [ ] **Override Log**: System logs override events with timestamp and reason.

### 7. Command-Gateway Verification
- [ ] **Rejection Reason Logging**: Every rejected setpoint logged with
  `RejectionReason` and timestamp.
  - Test: submit invalid setpoints (out-of-bounds, non-finite, stale telemetry);
    confirm each is logged with correct reason.
- [ ] **Authorization Token Enforcement**: Mode-changing commands require
  `authorization_token`; test without token is rejected.
- [ ] **No Silent Clamping**: Verify that rejected setpoints are NOT silently
  clamped; instead, an explicit rejection is returned.
- [ ] **Coordinate Frame Validation**: Test sending setpoints in wrong frame
  (e.g., GPS lat/lon to local-frame autopilot); confirm `UNSUPPORTED_FRAME`
  rejection.
- [ ] **Mode Consistency Check**: Test setpoint inconsistent with current
  flight mode; confirm `MODE_INCONSISTENT` rejection.

### 8. Mock-to-SITL Transition Verification
- [ ] **Mock Adapter Tests Pass**: All unit tests for `MockAutopilotAdapter`
  pass (deterministic telemetry, no physical commands).
- [ ] **Simulator Adapter Integration**: `SimulatorAdapter` successfully
  wraps simulation MissionState and exposes standard API.
- [ ] **SITL Adapter Swap**: When switching from mock to SITL adapter, all
  validation gates still apply identically.
- [ ] **Configuration Flag**: `SITL_COMMAND_MODE_ENABLED` flag controls
  transmission; default `false` prevents accidental arming/takeoff.
- [ ] **End-to-End Test**: Full sequence: connect → get telemetry → validate
  setpoint → submit setpoint → receive CommandAck → disconnect. All steps
  logged and verified.

### 9. GPS Drop Simulation
- [ ] **Simulated GPS Loss**: Temporarily remove GPS data; verify vehicle
  transitions to safe state (hover or last-known-position hold).
- [ ] **GPS Return**: Reconnect GPS; verify vehicle re-acquires fix and
  resumes mission or initiates appropriate recovery.
- [ ] **Partial GPS Degradation**: Simulate reduced satellite count (2D fix
  instead of 3D); verify behavior matches configured GPS dropout policy.

### 10. Battery Low and RTH Test
- [ ] **Simulated Low Battery**: Gradually reduce simulated battery voltage;
    confirm low-battery failsafe triggers at configured threshold.
- [ ] **Return-to-Home (RTH)**: Trigger RTH; verify vehicle navigates home
  safely and lands at home position.
- [ ] **RTH Cancel**: Cancel RTH mid-flight; vehicle resumes previous mission.
- [ ] **Battery Critical**: Test critical battery level (typically 20% remaining);
    confirm maximum emergency behavior.

### 11. Software Configuration Verification
- [ ] **Configuration Files**: All `core/config.py` values reviewed and
  confirmed appropriate for mission:
  - `rf.frequency`, `rf.noise_floor`, `rf.min_snr`, `rf.shadowing_std`
  - `rf.los_param_a`, `rf.los_param_b`
  - `rf.bandwidth`, `rf.max_hops`
  - `uav.tx_power`, `uav.antenna_gain`, `uav.rx_sensitivity`
  - Command validation boundaries (`MAX_ALTITUDE_M`, `MAX_VELOCITY_MS`, etc.)
- [ ] **Environment Variables**: `SITL_COMMAND_MODE_ENABLED`, `SITL_AUTOPILOT_TYPE`,
  `SITL_HOME_LAT/LON/ALT` all set correctly.
- [ ] **Dependencies**: `numpy`, `networkx`, `pytest` all installed and version-
  checked.
- [ ] **Safety Gates Disabled**: No safety gates bypassed (e.g., no `-c
  commit.gpgsign=false` equivalent for safety checks).

## During-Flight Monitoring

### 12. Real-Time Telemetry Monitoring
- [ ] **Telemetry Freshness**: Ground station displays telemetry age
  (`time.monotonic() - telemetry.timestamp`); alerts if >1.0 s.
- [ ] **PDR / SNR Monitoring**: Real-time PDR and SNR displayed for each
  link; color-coded (green > 90%, yellow 70-90%, red < 70%).
- [ ] **Link Quality per UAV**: Each UAV's connected_to_gcs status and
  neighbor list displayed.
- [ ] **Mission Progress**: PoIs surveyed, coverage %, mission timeline.

### 13. System Health Monitoring
- [ ] **CPU/Memory Utilization**: Ground station shows current CPU % and RSS
  in MB (matching REALTIME_PERFORMANCE.md baseline).
- [ ] **Jitter Alerts**: If p99 latency exceeds deadline by >2x, alert operator.
- [ ] **Missed Deadline Counter**: Visible counter of how many component
  deadlines were missed during the flight.
- [ ] **Packet Drop Rate**: Visible per-link PDR and overall system PDR.

### 14. Operator Override Readiness
- [ ] **Override Access**: Operator can immediately take control (one command or
  switch flip).
- [ ] **Override Latency**: Time from operator input to vehicle response < 0.5 s.
- [ ] **Override Confirmation**: Visual indicator that override is active.
- [ ] **Communication Chain**: Clear chain of communication (operator → GCS →
  autopilot) verified.

## Post-Flight Analysis

### 15. Data Review
- [ ] **Command Rejection Log**: Review all `COMMAND_SAFETY.md` rejection entries.
  Every rejection should have a valid `RejectionReason` and readable details.
- [ ] **Telemetry Freshness Analysis**: Plot telemetry age over flight duration.
  Should remain well below 1.0 s threshold.
- [ ] **Latency Analysis**: Compare actual latencies against
  `REALTIME_PERFORMANCE.md` benchmarks. Note any significant deviations.
- [ ] **Packet Drop Analysis**: Analyze `mesh_router.py` stats:
  `packets_sent`, `packets_delivered`, `packets_dropped`, `reroute_attempts`,
  `successful_recoveries`, `ttl_drops`.
- [ ] **Jamming/Interference Log**: If RF interference zones were active,
  log `hazard_expired` events and their impact on PDR/latency.
- [ ] **Failure Scenario Results**: For each of the 15 Phase 6 scenarios,
  record pass/fail and key metrics.

### 16. KNOWN_LIMITATIONS Update
- [ ] **New Findings**: Any new limitations discovered during flight documented
  in `docs/KNOWN_LIMITATIONS.md`.
- [ ] **Workarounds**: Any discovered workarounds or mitigation strategies
  added to the limitations document.
- [ ] **Future Work**: New ideas for Phase 3/4 improvements recorded.

### 17. Lessons Learned
- [ ] **What Worked**: Successful procedures and configurations documented.
- [ ] **What Did Not Work**: Failed attempts and reasons documented.
- [ ] **Recommendations**: Changes for next iteration (hardware, software, config).

## Checklist Completion Sign-Off

| Item | Completed (yes/no) | Reviewer | Date |
|------|--------------------|----------|------|
| Autopilot calibrated (IMU, mag, baro) | | | |
| GPS fix confirmed (3D, HDOP < 2.0) | | | |
| Telemetry radio range test passed | | | |
| Battery voltage/current calibrated | | | |
| Failsafe configurations set and tested | | | |
| Operator override procedure verified | | | |
| Command-gateway rejection logging verified | | | |
| Mock-to-SITL transition tested | | | |
| GPS drop simulation tested | | | |
| Battery low / RTH test completed | | | |
| Software configuration verified | | | |
| Real-time telemetry monitoring active | | | |
| System health monitoring active | | | |
| Operator override readiness confirmed | | | |
| Command rejection log reviewed post-flight | | | |
| KNOWN_LIMITATIONS updated with new findings | | | |
| Lessons learned documented | | | |

**Mission Lead Signature**: ________________________ **Date**: ____________

**Safety Officer Signature**: ________________________ **Date**: ____________

---

*Document generated as part of Phase 8 (HITL ground-testing) and Phase 9 (documentation)
requirements for AeroMesh-Swarm Stage 2.*

*Project: AeroMesh-Swarm — IIT Bombay Techfest Pushpak Grand Challenge 2026, Stage 2*

*Safety Principle: Default mode never arms/takes off. Command gateway rejects unsafe
inputs with explicit logs. No silent clamping.*

*Related Documents*:
- `docs/REALTIME_READINESS_AUDIT.md` — Phase 0 audit
- `docs/AUTOPILOT_INTEGRATION.md` — architecture overview
- `docs/COMMAND_SAFETY.md` — validation gates
- `docs/SITL_VALIDATION.md` — SITL progression levels
- `docs/REALTIME_PERFORMANCE.md` — timing measurements
- `docs/KNOWN_LIMITATIONS.md` — documented gaps