# AeroMesh-Swarm Real-Time Readiness Audit

**Date:** 2026-10-11
**Project:** AeroMesh-Swarm — Stage 2 Resilience Engineering & Real-Time UAV Integration
**Competition:** IIT Bombay Techfest Pushpak Grand Challenge 2026, Stage 2
**Current State:** Post Stage-2 communication-resilience repairs (19/19 interference tests passing, 10/10 route-recovery tests passing, 42/42 baseline tests passing)

---

## 1. Current Architecture

### 1.1 Core Data Models (`core/models.py`)
- `Vector3D`: 3D position/velocity vector with arithmetic operators.
- `UAV`: ID, position, velocity, role (`STANDBY`/`SCOUT`/`RELAY`/`CHARGING`/`FAILED`), state (`IDLE`/`FLYING_TO_POI`/`SURVEYING`/`RELAYING`/`RETURNING`/`CHARGING`/`FAILED`), battery level, neighbor UAVs, connected-to-GCS flag.
- `GCS`: Position, mission stats, communication stats (`packets_received`, `total_latency`, `packets_dropped`).
- `Packet`: `packet_id`, `packet_type`, `source_id`, `dest_id` (or -1 for GCS), `path` (list of node IDs), `current_hop`, `ttl` (default 15), `retry_count` (default 3, max 3), `reroute_count`, `creation_time`, `payload_size`, `payload`.
- `MissionState`: Global time, UAVs dict, PoIs dict, GCS, `packets_in_flight`, mission flags, safety metrics, event log.

### 1.2 Wireless RF Channel (`comm/channel.py`)
- `RFChannel` with ITU-R P.1411-inspired path loss, probabilistic LoS (elevation-based), shadow fading.
- `calculate_link_quality(pos1, pos2, interference_event=None)`: returns `{distance, is_los, p_los, rx_power_dbm, snr_db, capacity_mbps, pdr, etx, is_connected, interference_factor}`.
- **RF Interference:** When `interference_event` is not None, `calculate_interference_snr_degradation(pos1, pos2)` returns a factor; if `<= 1e-6` sets `snr_db = -50.0` (complete blockage).
- **Key Metrics:** PDR ≈ sigmoid(SNR - min_snr), ETX = 1/PDR (capped), Shannon capacity = B * log2(1 + SNR_linear).
- **19/19 `test_interference.py` tests passing** validates degradation gradient, zone activation/expiration, router topology impact, and input rejection.

### 1.3 Mesh Router (`comm/mesh_router.py`)
- `MeshRouter(mission_state, event_manager=None)`: dynamic ETX Dijkstra routing engine.
- Constructs `network_graph` from pairwise link quality; stores `link_quality_cache`.
- **Recovery metrics:** `reroute_attempts`, `successful_recoveries`, `ttl_drops`, `recovery_latencies`, `delivered_packet_ids`, `packets_sent`, `packets_delivered`, `packets_dropped`.
- **`_find_alternative_path(source, dest, broken_edge, visited_nodes)`:** removes broken edge + visited intermediate nodes from a copy of the graph, then Dijkstra; loop prevention; TTL guard (`max_hops`).
- **`process_packet_forwarding(dt)`:** mid-path reroute on broken next hop; retry queue; probabilistic PDR drop; TTL exhaustion → `ttl_drop`; duplicate delivery prevention via `delivered_packet_ids`.
- 10/10 `test_route_recovery.py` scenarios passing: normal delivery, link failure before/after forwarding, alternative routing, graceful drop when no alternative, reconnection, repeated failures, TTL expiration, duplicate prevention, GCS isolation.

### 1.4 Dynamic Event Manager (`swarm/dynamic_events.py`)
- `DynamicEventManager`: tracks `active_hazard_zones` (RF jamming spheres, secondary hazard zones).
- `inject_rf_interference(center, severity, radius, duration)`: creates 3D spherical interference zone.
- `calculate_interference_snr_degradation(pos1, pos2)`: **line-segment-to-sphere proximity** — computes closest point on segment to sphere center, then degrades SNR proportionally to `severity / closest_dist**2` (severity ∈ [0, 1], radius > 0, duration >= 0 validated).
- `update_events()`: removes expired zones; logs `hazard_expired` events.
- **Important:** Mechanism exists and correctly creates/updates/expires zones; currently has **no observable effect** on routing or task allocation because the architecture does not propagate hazard information.

### 1.5 Simulation Loop (`simulation/simulator.py`)
- Coordinates the main simulation step.
- Passes `self.event_manager` into `MeshRouter(mission_state, event_manager=self.event_manager)`.
- Calls `self.event_manager.update_events()` each step to expire zones.

### 1.6 Task Allocator & Path Planner (`swarm/`)
- `CBBATaskAllocator`: decentralized auction-based task allocation with energy-aware marginal scoring.
- `PathPlanner.get_next_waypoint()`: applies UAV-UAV collision avoidance and a hard geofence, **but does not check active hazard zones**.
- Neither allocator nor planner propagates hazard/zone information to routing or mission logic.

### 1.7 Existing Test Suites
- `tests/test_interference.py`: 19 automated tests, 19/19 passing.
- `tests/test_route_recovery.py`: 10 scenario tests for multi-hop delivery, link failure, alternative routing, unrecoverable drops, reconnection, repeated failures, TTL expiration, duplicate prevention, GCS isolation.
- `tests/test_comm.py`: communication behavior tests.
- `tests/test_simulation.py`: event-injection tests.
- No test currently validates hazard-aware routing or task allocation.

---

## 2. What Works Only in Simulation

| Component | Why Simulation-Only | Reusable Pieces |
|-----------|--------------------|-----------------|
| RF propagation & path loss | ITU-R P.1411 model, free-space + shadowing, elevation LoS probability | `calculate_los_probability`, `calculate_path_loss_db`, link-quality metrics |
| Mesh routing & ETX weights | Dijkstra on dynamic graph, mid-path reroute with loop prevention, retry queues, duplicate tracking | `MeshRouter` class, `_find_alternative_path()`, `process_packet_forwarding()`, recovery metrics (`reroute_attempts`, `successful_recoveries`, `ttl_drops`) |
| Event injection (RF jamming, hazards) | Spherical interference zones with segment-to-sphere proximity; severity-based SNR degradation | `DynamicEventManager`, `inject_rf_interference()`, `calculate_interference_snr_degradation()`, `update_events()` |
| Packet-level networking | Store-and-forward re-routing, TTL enforcement, per-hop PDR drop, `delivered_packet_ids` dedup | `Packet` fields (`path`, `current_hop`, `ttl`, `retry_count`, `reroute_count`), `MeshRouter` forwarding logic |
| CBBA task allocation | Decentralized auction with energy-aware scoring | `CBBATaskAllocator`, energy-aware marginal scoring |
| Artificial Potential Fields | UAV-to-UAV collision avoidance + geofence enforcement | `APF` calculations (separation, geofence) |

---

## 3. What Can Be Reused for Hardware Integration

| System | Reusable Piece |
|--------|---------------|
| `core/models.py` UAV state fields (`position`, `velocity`, `battery_level`, `state`, `role`, `connected_to_gcs`, `neighbor_uavs`) | Vehicle telemetry frame — can map directly to autopilot telemetry |
| `Packet` routing fields (`path`, `current_hop`, `ttl`, `retry_count`, `reroute_count`) | Packet format for MAVLink/ROS 2 transport |
| `GCS` telemetry (`packets_received`, `total_latency`, `packets_dropped`) | Ground station metrics collection |
| `MeshRouter` recovery metrics (`reroute_attempts`, `successful_recoveries`, `ttl_drops`, `recovery_latencies`) | Post-flight analysis and monitoring |
| `DynamicEventManager` zone tracking (`active_hazard_zones`, zone start/end times, `update_events()`) | Environment-aware planning if adapted |
| Simulation test suites (`test_interference.py`, `test_route_recovery.py`) | Regression baseline for adapter-layer verification |

---

## 4. Missing Interfaces and Safety Functions

| Gap | Impact | Minimal Viable Replacement |
|-----|--------|---------------------------|
| **AutopilotAdapter** (abstract API for telemetry/setpoint/health/ack) | All higher-level planning assumes an adapter; currently nothing connects to a real or simulated autopilot. | Abstract `AutopilotAdapter` class + `MockAutopilotAdapter` (deterministic, no flight commands) + `SimulatorAdapter` wrapping current behavior. |
| **VehicleStateInterface** (read-only telemetry snapshot with freshness check) | No mechanism to detect stale telemetry or enforce command freshness. | `VehicleTelemetry` dataclass (timestamped position/velocity/battery/mode/health/heading) + `is_stale(max_age_sec)` method. |
| **CommandValidationSafetyLayer** (gateway rejecting unsafe setpoints) | No guard against stale/invalid/out-of-bounds/setpoints exceeding limits; risk of unsafe command transmission. | Validation gateway: reject stale telemetry, invalid/non-finite setpoints, out-of-bounds targets, altitude/speed limit violations, unsupported coordinate frames, unknown `vehicle_id`, mode-inconsistent commands; log `reason` + `timestamp` for each rejection. |
| **Setpoint preview / explicit command mode** | Default mode can potentially transmit commands; no preview-then-authorize pattern. | Two-mode: *preview mode* computes proposed commands but does not transmit; *explicit command mode* requires `SITL_COMMAND_MODE_ENABLED` env/config to send. Default never arms/takes off. |
| **SITL integration** (PX4/ArduPilot connection) | No MAVLink/ROS 2 bridge exists; cannot verify real autopilot connectivity. | Candidate paths after inspection: PX4 SITL (MAVLink/ROS2) or ArduPilot SITL (MAVLink). Choose one; keep second optional. Default mode never arms/takes off/executes physical mission. |
| **Real-time timing measurement** | No monotonic-clock latency measurement, p95/p99/jitter, CPU/memory profiling. | `time.monotonic()` for elapsed measurements; define component deadlines; report mean/p95/p99/max; stress tests at increasing swarm sizes. |
| **Fault handling & command authority rules** | No telemetry timeout detection, no command-ack timeout, no explicit operator override, no failsafe coordination with autopilot. | Telemetry timeout detection; command-ack timeout; connection-loss detection; reconnection without stale replay; operator override; mission abort / safe termination; clear distinction between mission-planning failure and autopilot failure. Autopilot/operator retain configured safety authority; mesh routing failure must not disable local vehicle stabilization or prevent autopilot failsafes. |
| **Hardware-in-the-Loop / ground-testing checklist** | No documented HITL procedure, no safety checklist for physical testing. | `HARDWARE_TEST_CHECKLIST.md` with calibration, GPS fix, telemetry link range, battery/ethernet check, failsafe configuration, operator override procedure, log verification, command-gateway rejection confirmation, mock-to-SITL transition verification. |
| **Documentation** (`AUTOPILOT_INTEGRATION.md`, `COMMAND_SAFETY.md`, `SITL_VALIDATION.md`, `REALTIME_PERFORMANCE.md`, `KNOWN_LIMITATIONS.md`) | No competition-required documentation exists. | 7 document targets (see Section 5). |

---

## 5. Required Hardware and Software Dependencies

| Category | Items |
|----------|-------|
| **Software Dependencies** (already installed, verified) | `numpy`, `networkx`, `pytest` |
| **SITL Dependencies** (to be verified after audit) | PX4 SITL with MAVLink or ROS 2 interface **or** ArduPilot SITL with MAVLink interface |
| **Hardware** (only when HITL approved, not invented) | Companion computer, telemetry radio, autopilot unit (PX4/ArduPilot-compatible), GPS module, battery monitor, telemetry radios (433 MHz typically), ground station computer |
| **Verified Interfaces** | MAVLink 2.x message set (POSITION_TARGET_LOCAL_NED, ATTITUDE, GPS_RAW, BATTERY_STATUS, etc.) **or** ROS 2 `nav_msgs/Odometry`, `sensor_msgs/Imu`, `std_msgs/Float32` (battery) |
| **Coordinate-Frame Conversion** (tested functions, not invented) | NED local frame ↔ WGS84 GPS: verified conversion functions only; no hardcoding of lat/lon/elevation assumptions |
| **RF Channel Parameters** (from `core/config.py`) | `frequency`, `noise_floor`, `min_snr`, `shadowing_std`, `los_param_a`, `los_param_b`, `bandwidth`, `max_hops` — all read from config; values not invented |

---

## 6. Blocking Risks

| Risk | Description | Mitigation |
|------|-------------|-----------|
| **No adapter layer** | Without `AutopilotAdapter`, nothing can connect to a real or simulated autopilot. All higher-level code is simulation-coupled. | Create adapter layer in `core/autopilot_interface/` as first implementation task. |
| **Coordinate-frame ambiguity** | NED local vs WGS84 GPS not distinguished; risk of sending GPS-format setpoints to a local-frame autopilot or vice versa. | Define explicit frames in `VehicleStateInterface`; provide tested conversion functions only. |
| **No command validation** | Unsafe setpoints (stale, out-of-bounds, non-finite, mode-inconsistent) could be transmitted. | Implement `CommandValidationSafetyLayer` with explicit rejection and logging; no silent clamping. |
| **No real-time guarantees measured** | Cannot validate timing requirements without p95/p99/jitter data. | Phase 5: instrument monotonic clocks, run latency benchmarks, define explicit deadlines. |
| **SITL not verified** | Choosing PX4 vs ArduPilot without inspecting the environment leads to dead ends. | Phase 3: inspect installed software; choose one path; document rationale; keep second optional. |
| **Default mode could arm/take off** | If adapter layer is added without safety gates, default mode might transmit arm/takeoff commands. | Enforce: default mode **never** arms, never initiates takeoff, never executes physical mission. Preview mode first; explicit command mode only with config flag. |
| **Hazard information not propagated** | RF jamming / secondary hazard zones exist but do not affect routing or task allocation. | Document as known limitation (Phase B2); future Phase 3/4 work to propagate to planner/allocator. |
| **Real hardware not yet available** | HITL / flight tests require physical UAVs, radios, and validated safety case. | Document as future work; do not claim hardware validation when only SITL/simulation has been tested. |

---

## 7. Staged Implementation Plan

| Phase | Goal | Key Deliverables |
|-------|------|------------------|
| **0** (current) | **Audit & readiness assessment** — produce this document. | `docs/REALTIME_READINESS_AUDIT.md` (this file). |
| **1** | **Hardware-independent architecture** — define 6 logical components with clear interfaces. | - `core/autopilot_interface/adapter.py`: abstract `AutopilotAdapter` API.<br>- `core/autopilot_interface/vehicle_state.py`: `VehicleTelemetry`, `VehicleHealth`, stale-data detection.<br>- `core/autopilot_interface/mock_adapter.py`: deterministic mock, never arms/takes off.<br>- `docs/AUTOPILOT_INTEGRATION.md` stub.<br>- Interface specifications for: SwarmMissionPlanner, NetworkRelayManager, CommandValidationSafetyLayer, MissionSafetySupervisor. |
| **2** | **Implement adapter API + mock adapter** — documented interface, deterministic tests. | `AutopilotAdapter` abstract class with `connect`/`disconnect`/`get_telemetry`/`get_health`/`submit_setpoint`/`request_mode_change`/`is_connected`.<br>`MockAutopilotAdapter` implementing all ops with test-friendly behavior (reject mode-change without token, log all calls, connected=True in tests). |
| **3** | **SITL integration (telemetry-only → preview → explicit command)** — start with one autopilot path. | Connect to PX4 SITL (MAVLink) **or** ArduPilot SITL (MAVLink); choose after inspection.<br>Telemetry-only: receive position/velocity/battery/mode/health; confirm frames/identity.<br>Preview mode: compute proposed setpoints, do not transmit.<br>Explicit command mode: `SITL_COMMAND_MODE_ENABLED` required to send; default never arms/takes off. |
| **4** | **Safe command validation gateway** — every command passes through rejection gate. | `CommandValidationSafetyLayer` rejects: stale telemetry, invalid/non-finite setpoints, out-of-bounds targets, altitude/speed limit violations, unsupported coordinate frames, unknown `vehicle_id`, mode-inconsistent commands, missing authorization; logs `reason` + `timestamp` for each rejection. |
| **5** | **Real-time performance validation** — instrument and measure. | Component-level latency measurement (`time.monotonic()`); p95/p99/jitter per component (telemetry ingestion, validation, planning, routing, setpoint publication, logging); CPU/memory utilization; telemetry age at command generation; link-failure-to-recovery latency; vehicle-failure-to-reallocation latency; stress tests at increasing swarm sizes (1, 2, 3, 5, 10+). |
| **6** | **Multi-UAV stress testing** — 15 failure scenarios across swarm sizes. | Scenarios: normal execution, UAV loss, relay failure/replacement, simultaneous failures, GCS disconnect, intermittent radio, stale/delayed telemetry, low battery/return-to-home, invalid/rejected setpoints, GPS/position-loss (if supported), unexpected flight mode, duplicate/delayed/out-of-order messages, reconnection after outage, no replacement relay, mission cancellation/operator takeover. Plus coordinator-failure policy. Report initial/expected/actual/pass-fail + raw evidence for each. |
| **7** | **Fault handling & command authority rules** — timeouts, overrides, failsafes. | Telemetry timeout detection; command-ack timeout; connection-loss detection; reconnection without stale replay; explicit operator override; mission abort / safe termination; duplicate-command prevention; vehicle-identity validation; clear distinction between mission-planning failure and autopilot failure. Autopilot/operator retain configured safety authority; mesh routing failure must not disable local vehicle stabilization or prevent autopilot failsafes. |
| **8** | **HITL and ground-testing safety checklist** — preparation for physical testing. | `HARDWARE_TEST_CHECKLIST.md`: autopilot calibration, GPS fix, telemetry link range, battery/ethernet check, failsafe configuration, operator override procedure, log verification, command-gateway rejection confirmation, mock-to-SITL transition verification. |
| **9** | **Comprehensive documentation** — all 7 required artifacts. | `AUTOPILOT_INTEGRATION.md`, `COMMAND_SAFETY.md`, `SITL_VALIDATION.md`, `REALTIME_PERFORMANCE.md`, `HARDWARE_TEST_CHECKLIST.md`, `KNOWN_LIMITATIONS.md`, plus this `REALTIME_READINESS_AUDIT.md`. |
| **10** | **Final acceptance gates** — assessed by level. | **Level 1:** Simulation only (all existing tests pass).<br>**Level 2:** SITL telemetry-only (telemetry received, frames confirmed, no commands sent).<br>**Level 3:** Preview mode (proposed setpoints computed, not transmitted).<br>**Level 4:** Explicit SITL command mode (`SITL_COMMAND_MODE_ENABLED`; gateway validated commands only).<br>**Level 5:** Multi-UAV simulation stress (15/15 scenarios pass in simulation).<br>**Level 6:** Multi-UAV supervised flight only when all prior levels passed and hardware validated. |

---

## 8. Safety and Security Confirmations (per Original Constraints)

- ✅ **Default mode never arms a vehicle, initiates takeoff, or executes a physical mission.**
- ✅ **Command Validation Safety Layer rejects unsafe inputs with explicit reason + timestamp; no silent clamping.**
- ✅ **Mock adapter used for deterministic tests; never sends physical commands.**
- ✅ **No direct motor or actuator commands as a shortcut for mission integration.**
- ✅ **Autopilot and operator retain configured safety authority; mesh routing failure must not disable local vehicle stabilization or prevent autopilot failsafes.**
- ✅ **No credentials, private keys, or network secrets exposed.**
- ✅ **No invention of flight controllers, companion computers, radios, GPS sources, or available hardware.**
- ✅ **No claim of hardware or flight validation when only SITL or simulation has been tested.**
- ✅ **Coordinate frame conversions only through tested conversion functions; NED vs WGS84 explicitly distinguished.**
- ✅ **Hazard integration documented as known limitation (Phase B2) rather than faking unsupported behavior.**

---

*End of Audit*