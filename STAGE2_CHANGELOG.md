# AeroMesh-Swarm Stage 2 — Changelog

## Version 0.4.0 — 2026-10-11 (Current)
**Real-Time UAV Integration and Flight-Readiness Engineering — Phase 0 through Phase 2**

### Added
- `docs/REALTIME_READINESS_AUDIT.md` — Comprehensive audit of current architecture,
  simulation-only capabilities, reusable components, missing interfaces, dependencies,
  blocking risks, and staged implementation plan.
- `core/autopilot_interface/` package with 5 modules:
  - `adapter.py` — Abstract `AutopilotAdapter` base class defining the common API
    (connect/disconnect/get_telemetry/get_health/submit_setpoint/request_mode_change/
    get_setpoint_history/get_mode_change_history/clear_history, plus frame conversion).
  - `vehicle_state.py` — Hardware-independent data models: `VehicleTelemetry`,
    `VehicleState`, `CoordinateFrame` enum, `CoordinateConverter` with NED↔WGS84
    conversions (flat-earth approximation, <10km), `ValidatedSetpoint`, `CommandAck`,
    `RejectionReason` enum.
  - `mock_adapter.py` — Deterministic `MockAutopilotAdapter` implementing the full
    API never arms, never takes off, logs all calls, returns `connected=True` in tests,
    requires `authorization_token` for mode changes.
  - `simulator_adapter.py` — `SimulatorAdapter` wrapping the existing simulation
    `MissionState` as an `AutopilotAdapter`. Reads telemetry from the simulation,
    supports coordinate frame conversion, setpoint logging without transmission.
  - `command_validation.py` — `CommandValidationSafetyLayer` single gateway through
    which every setpoint passes. Applies 10 validation gates (finite values, telemetry
    freshness, coordinate frame, geofence, altitude/velocity limits, unknown vehicle,
    mode consistency, authorization, deadline). Rejects with explicit
    `RejectionReason` + timestamp; never silently clamps.
- `docs/AUTOPILOT_INTEGRATION.md` — Full integration architecture, interface
  specifications, integration phases (simulation → telemetry-only → preview →
  explicit command → multi-UAV stress → supervised flight), SITL adapter selection
  (PX4 vs ArduPilot), configuration variables, coordinate frame considerations.
- `docs/COMMAND_SAFETY.md` — Detailed command safety Gates documentation: 10
  validation gates in order, rejection logging format, accepted setpoint behavior,
  configuration per mission, safety gate diagrams, post-flight analysis procedures.
- `docs/SITL_VALIDATION.md` — 6-level SITL validation progression (Simulation Only
  → SITL Telemetry-Only → Preview Mode → Explicit Command Mode → Multi-UAV
  Simulation Stress → Multi-UAV Supervised Flight). Level prerequisites, test
  checklists, evidence requirements, transition rules, coordinate frame
  considerations, configuration variables.
- `docs/REALTIME_PERFORMANCE.md` — Instrumented performance measurements using
  `time.monotonic()`. Component latencies (mean/p50/p95/p99/max) for 1/2/3/5/10/20
  UAVs, jitter analysis (p99-p50), deadline configuration, CPU/memory utilization,
  telemetry age at command generation, link failure to route recovery metrics, 15
  stress test scenario results with pass/fail and raw evidence. Scalability audit
  notes. Hard real-time certification status (not certified; metrics-reported full).
- `docs/KNOWN_LIMITATIONS.md` — 10 documented architectural gaps where the current
  architecture does not yet propagate information: hazard-aware routing, coordinate-
  frame approximation, no hard real-time certification, SITL path not selected,
  no hard real-time certification, hazard info not propagated to GCS telemetry,
  dedup only within single run, no multi-vehicle telemetry sync, configurable
  validation bounds, mock adapter limitations.
- `docs/HARDWARE_TEST_CHECKLIST.md` — 22-item HITL ground-testing checklist
  covering autopilot calibration, GPS setup, telemetry radio link, battery/power,
  failsafe configuration, operator override, command-gateway verification,
  mock-to-SITL transition, GPS drop simulation, battery low/RTH test, software
  configuration, real-time monitoring, system health, operator override readiness,
  post-flight data review, KNOWN_LIMITATIONS update, lessons learned. Includes
  sign-off section with mission lead and safety officer signatures.

### Modified
- `tests/test_route_recovery.py::setup_diamond_network()` — Fixed diamond topology
  to place UAVs at correct positions (0, 50, 50 / 100, 50, 50 / 100, -50, 50)
  so that UAV 0 connects to UAVs 1 and 2, which connect to GCS, enabling proper
  multi-hop routing and alternative path testing when one branch breaks. Previous
  placement (400, 0, 50) resulted in direct GCS link, bypassing the routing test.
- `docs/phase_docs/B2_SECONDARY_HAZARDS.md` — Updated to reflect that hazard
  integration is a documented architectural limitation (Phase B2), not a fake
  implementation, per the Stage 2 mandate.

### Fixed
- `comm/channel.py` — `calculate_link_quality()`: Updated RF interference clamping
  so that when `interference_snr_factor <= 1e-6`, `snr_db = -50.0` is forced,
  resulting in `is_connected = False`. Previous clamping (`max(0.01,
  interference_snr_factor)`) limited max attenuation to -20 dB, which left links
  connected for close-in UAVs despite severity = 1.0.
- `comm/channel.py` — `calculate_link_quality()`: Updated `max(0.01, ...)` in ETX
  calculation to `max(0.01, pdr)` — the original was already correct in spirit
  but the clamping interaction with interference required re-verification.
- `swarm/dynamic_events.py` — Corrected variable name `seg_vec.z` → `seg_vec_z`
  in `calculate_interference_snr_degradation()` line-segment-to-sphere proximity
  calculation (Error 1 from earlier summary).
- `core/models.py` — Extended `Packet` dataclass with resilience fields:
  `path`, `current_hop`, `ttl` (default 15), `retry_count` (default 3, max 3),
  `reroute_count` (default 0). These fields enable mid-path rerouting, TTL
  enforcement, retry tracking, and duplicate delivery prevention in the mesh router.

### Deprecated
- None (all prior work preserved; new architecture builds alongside existing code).

### Security and Safety Confirmations (all preserved)
- ✅ Default mode never arms a vehicle, initiates takeoff, or executes a physical mission.
- ✅ Command Validation Safety Layer rejects unsafe inputs with explicit reason +
  timestamp; no silent clamping.
- ✅ Mock adapter used for deterministic tests; never sends physical commands.
- ✅ No direct motor or actuator commands as a shortcut for mission integration.
- ✅ Autopilot and operator retain configured safety authority; mesh routing failure
  must not disable local vehicle stabilization or prevent autopilot failsafes.
- ✅ No credentials, private keys, or network secrets exposed.
- ✅ No invention of flight controllers, companion computers, radios, GPS sources,
  or available hardware.
- ✅ No claim of hardware or flight validation when only SITL or simulation has been
  tested.
- ✅ Coordinate frame conversions only through tested functions; NED vs WGS84
  explicitly distinguished.
- ✅ Hazard integration documented as known limitation (Phase B2) rather than faking
  unsupported behavior.

## Version 0.3.0 — 2026-10-11 (Prior)
**Communication Resilience Repairs and Test Fixes**
- RF interference model verified: 19/19 `test_interference.py` passing.
- Route recovery engine implemented: 10/10 `test_route_recovery.py` passing (with
  topology fix in `setup_diamond_network()`).
- Baseline test suite: 42/42 passing tests.
- RF clamping bug fixed: `calculate_link_quality()` now forces `snr_db = -50.0`
  when `interference_snr_factor <= 1e-6`, ensuring complete channel blockage.
- Geometric calculation variable name fixed: `seg_vec.z` → `seg_vec_z`.
- Pytest `--timeout` flag removed (pytest-timeout not installed).
- `_StubFactor` test helper class created for missing test definition.

## Version 0.2.0 — Earlier Stage 2
**Phase A Baseline Reproduction**
- pytest suite and scalability benchmarks established.
- Core communication, routing, and event-injection infrastructure in place.

## Version 0.1.0 — Project Start
**Initial Setup**
- Project scaffolding, core data models, RF channel model, mesh router, dynamic
  event manager, simulation loop, basic test suites.

---
*Generated for AeroMesh-Swarm — IIT Bombay Techfest Pushpak Grand Challenge 2026, Stage 2.*
*Current date: 2026-10-11.*