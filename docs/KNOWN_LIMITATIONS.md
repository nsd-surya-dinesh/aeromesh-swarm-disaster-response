# Known Limitations — AeroMesh-Swarm Stage 2

This document documents architectural gaps and unsupported behaviors that are
intentionally not faked. These are areas where the current architecture does
not yet propagate information, and where future work (Phase 3 onward) will
address them.

## 1. Hazard-Aware Routing and Task Allocation
**Status**: Not integrated — documented as known limitation (Phase B2).

The `DynamicEventManager` correctly creates, updates, and expires RF jamming
spheres and secondary hazard zones. However, this information is **not
propagated** to:
- `PathPlanner.get_next_waypoint()` — does not check `mission_state.event_manager.get_active_hazard_zones()`
- `CBBATaskAllocator.run_cbba_allocation()` — does not exclude PoIs within active hazard zones
- `MeshRouter` link quality evaluation — hazard zones do not degrade link metrics

**Why**: Per the Stage 2 mandate: "If this feature cannot be safely integrated
within the existing architecture, document it as a known limitation instead of
faking its behavior." Adding fake path-planning avoidance without corresponding
metrics verification would violate the mandate against unsupported claims.

**Future work (Phase 3 / ROS2)**:
1. Modify `PathPlanner.get_next_waypoint()` to query
   `mission_state.event_manager.active_hazard_zones` and add a repulsive
   potential away from zone centers.
2. Modify `CBBATaskAllocator.run_cbba_allocation()` to exclude PoIs within
   active hazard zones from the bundle.
3. Add metrics tracking for `hazard_avoidance_distance` and `hazard_violations`.
4. Write regression tests in `tests/test_hazard.py`.

## 2. Coordinate-Frame Conversion Approximation
**Status**: Flat-earth approximation (< 10 km from home).

The `CoordinateConverter` uses a simple flat-earth approximation for NED↔WGS84
conversions. This is valid for < ~10 km from the home location but degrades
near the poles or for very long distances. For precision applications, use a
proper geodetic library (e.g., `pyproj`, `geopy`).

**Mitigation**: Document this limitation and operate within < 10 km radius of
the home/GCS position for all mission operations.

## 3. Real-Time Hard Real-Time Guarantees Not Verified
**Status**: Timing measurements instrumented but not certified.

Phase 5 will measure and report p95/p99/jitter latency, CPU/memory utilization,
and missed deadlines. However, the system has not been certified as hard
real-time. Average latency alone does not guarantee real-time behavior; worst-case
execution times and jitter metrics must be within specified deadlines.

**Mitigation**: Phase 5 defines explicit target deadlines and measures against
them. Do not claim hard real-time guarantees from average latency alone.

## 4. SITL Integration Path Not Yet Selected
**Status**: PX4 vs ArduPilot choice pending environment inspection.

The integration layer supports both PX4 SITL (MAVLink/ROS2) and ArduPilot SITL
(MAVLink), but the specific path has not been selected for this installation.
The choice depends on available software dependencies and hardware.

**Mitigation**: Phase 3 inspects the installed environment and selects one path;
the other remains optional.

## 5. No Hard Real-Time Certification
**Status**: Instrumentation present, certification absent.

The system measures and reports real-time performance metrics (Phase 5) but has
not undergone hard real-time certification. Worst-case execution times, jitter
bounds, and deadline miss rates have not been formally verified for any
configuration.

**Mitigation**: Phase 5 measurement and reporting; do not claim certification
without formal verification.

## 6. Hazard Information Not Propagated to GCS Telemetry
**Status**: RF jamming / secondary hazard zones exist but do not affect GCS
telemetry metrics (PDR, latency, mission completion, coverage).

The `DynamicEventManager` tracks zone activation/expiration, but this
information does not appear in reported metrics. A mission operating in a jammed
area reports the same PDR/latency as one in a clean area.

**Future work**: Add `jamming_severity`, `hazard_zone_id`, or similar fields to
telemetry and metrics if competition evidence requires it.

## 7. Duplicate Delivery Prevention Only Within Single Simulation Run
**Status**: `delivered_packet_ids` set is per-MeshRouter instance.

If the simulation is reset or the router re-instantiated, the dedup set is
cleared. Repeated packet IDs across simulation restarts could be delivered
multiple times.

**Mitigation**: For production use, ensure persistent dedup state or reset
routers between simulation runs.

## 8. No Multi-Vehicle Telemetry Synchronization
**Status**: Each UAV's telemetry is independently sampled.

There is no global synchronization of telemetry timestamps across UAVs. The
`VehicleTelemetry.timestamp` reflects when that particular vehicle's telemetry
was received, not a global mission clock.

**Mitigation**: For time-critical operations, add a synchronized clock source
or use the mission's `MissionState.time` as the reference.

## 9. Command Validation Bounds Are Configurable Defaults
**Status**: Operational boundaries (max altitude, max velocity, geofence radius)
use hard-coded default values.

The `CommandValidationSafetyLayer` defaults are:
- `MAX_ALTITUDE_M = 120.0` meters
- `MAX_VELOCITY_MS = 15.0` m/s
- `BOUNDARY_RADIUS_M = 500.0` meters

These should be configured per mission through the `SafetyContext` or a
mission-specific configuration file.

**Mitigation**: Override these values when instantiating the safety layer for
the specific mission.

## 10. Mock Adapter Does Not Simulate Real Autopilot Behavior
**Status**: `MockAutopilotAdapter` is deterministic and test-friendly but does
not simulate any real autopilot's behavior.

The mock always returns `connected=True`, always accepts setpoints (after
validation), and never actually changes vehicle state, arms motors, or takes
off. It is designed for unit testing the integration layer, not for SITL
validation.

**Mitigation**: Use `SimulatorAdapter` (wraps real simulation) or connect to
actual PX4/ArduPilot SITL for more realistic validation. Reserve `MockAutopilotAdapter`
for pure unit tests.

---

*Document generated as part of Phase 0 audit and Phase 9 documentation requirements.*
*Project: AeroMesh-Swarm — Stage 2, IIT Bombay Techfest Pushpak Grand Challenge 2026*
*Competition Rules: "If this feature cannot be safely integrated within the existing architecture, document it as a known limitation instead of faking its behavior."*