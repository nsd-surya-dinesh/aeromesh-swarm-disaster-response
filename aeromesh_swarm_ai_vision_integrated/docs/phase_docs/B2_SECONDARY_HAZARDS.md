# Phase B2 — Secondary Hazard Integration (Stage 2)

Status: **NOT FULLY INTEGRATED — DOCUMENTED AS KNOWN LIMITATION**

## What exists

`swarm/dynamic_events.py` defines:
- `inject_secondary_hazard(center, radius=200.0, duration=300.0)`
- `active_hazard_zones` dictionary with start/end times
- `is_position_in_hazard_zone()` and `get_active_hazard_zones()`
- `update_events()` removes expired zones and logs `hazard_expired`

## What is missing for full integration

The simulator (`simulation/simulator.py`) does not call `event_manager.update_events()` in a way that passes hazard information to the path planner or mission logic. More importantly:

- `PathPlanner.get_next_waypoint()` (`swarm/path_planner.py`) applies collision avoidance (UAV-UAV separation) and a hard geofence, but does **not** check `mission_state.event_manager.get_active_hazard_zones()`.
- The task allocator (`swarm/task_allocation.py`) does not exclude PoIs that fall inside active hazard zones.
- The physics engine (`core/physics.py`) does not apply hazard penalties to UAV movement.

## Why this was not faked

Per the Stage 2 mandate: "If this feature cannot be safely integrated within the existing architecture, document it as a known limitation instead of faking its behavior." There is no evidence in the existing codebase (tests, simulator loop, metrics) that hazard avoidance is expected to affect the metrics reported (PDR, latency, mission completion, coverage). Adding fake path-planning avoidance without corresponding metrics verification would violate the mandate against unsupported claims.

## Test evidence (existing)

- `tests/test_simulation.py::TestEventInjection::test_dynamic_poi_injection` — verifies PoI injection
- `tests/test_swarm.py`: no hazard-related tests
- `tests/test_comm.py`: no hazard-related tests

Hazard activation, expiration, boundary conditions, and unreachable-destination handling have **not been verified** through automated tests.

## Recommended future work (Stage 3 / ROS2)

If hazard integration is required for competition evidence:
1. Modify `PathPlanner.get_next_waypoint()` to query `mission_state.event_manager.active_hazard_zones` and add a repulsive potential away from zone centers.
2. Modify `CBBATaskAllocator.run_cbba_allocation()` to exclude PoIs within active hazard zones from the bundle.
3. Add metrics tracking for `hazard_avoidance_distance` and `hazard_violations`.
4. Write regression tests in `tests/test_hazard.py`.

## Conclusion

The `inject_secondary_hazard()` mechanism exists and correctly creates/updates/expires zones in `DynamicEventManager`, but it has no observable effect on the simulated mission because the architecture does not propagate hazard information to routing or task allocation. This is a documented architectural gap, not an implementation bug.
