# AeroMesh Swarm — Stage 2 Overview

## Project Overview

**AeroMesh-Swarm** is a resilient multi-hop UAV swarm framework for autonomous disaster response, developed for the **Pushpak Grand Challenge 2026** at Techfest, IIT Bombay.

The system enables a fleet of battery-constrained UAVs to autonomously survey disaster zones while maintaining continuous telemetry and payload connectivity with a Ground Control Station (GCS) through self-healing multi-hop mesh networks.

## Stage 2 Objectives

Stage 2 focuses on bug fixes and validation improvements:

1. **Heartbeat Timeout Detection** — Implement actual failure detection using configurable timeout threshold
2. **Correct Relay Replacement Logic** — Only trigger relay handoff when a relay UAV fails, not for all failures
3. **Accurate CBBA Metrics** — Ensure iteration counting reflects actual algorithm work
4. **Deterministic Testing** — Fix flaky tests that fail due to random shadow fading

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AEROMESH-SWARM PLATFORM                               │
├─────────────────────────────────────────────────────────────────────────────┤
│  Visualization Layer  │  Pygame GUI, Web Dashboard, Video Export            │
│  Swarm Autonomy       │  CBBA, Path Planning, Health Monitoring             │
│  Mesh Network         │  Dynamic Routing, Relay Placement                    │
│  Physics Engine       │  3D Kinematics, Aerodynamic Energy Model            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Core Subsystems

| Subsystem | File | Description |
|-----------|------|-------------|
| **CBBA Task Allocation** | `swarm/task_allocation.py` | Consensus-Based Bundle Algorithm with energy-aware scoring |
| **Health Monitoring** | `swarm/health_monitor.py` | Battery management, RTB, heartbeat timeout, relay handoff |
| **Mesh Routing** | `comm/mesh_router.py` | ETX-weighted Dijkstra multi-hop routing |
| **RF Channel** | `comm/channel.py` | ITU-R P.1411 probabilistic LoS model |
| **Relay Placement** | `comm/steiner_relay.py` | Midpoint relay positioning with APF |
| **Physics Engine** | `core/physics.py` | 3D kinematics and rotorcraft power model |

## Stage 1 vs Stage 2 Differences

### Changes Made in Stage 2

| Aspect | Stage 1 | Stage 2 |
|--------|---------|---------|
| Heartbeat Timeout | Non-functional (always updated to current time) | **Now detects stale heartbeats** |
| Relay Replacement | Triggered for ALL node failures | **Only for RELAY role failures** |
| CBBA Iterations | Showed 0 in benchmark | **Shows 1 (actual final iteration)** |
| Test Determinism | One flaky test | **All 23 tests pass consistently** |
| Total Tests | 20 | **23** (added 3 regression tests) |

### Files Changed

- `swarm/health_monitor.py` — Heartbeat timeout + relay logic fixes
- `tests/test_swarm.py` — Added 3 regression tests
- `tests/test_simulation.py` — Updated test for corrected behavior
- `tests/test_comm.py` — Fixed flaky test with random seed
- `scalability_benchmark_results.txt` — Updated results
- `docs/figures/scenario_comparison.png` — Regenerated chart

## How to Install and Run

```bash
# Clone the repository
git clone https://github.com/nsd-surya-dinesh/aeromesh-swarm-disaster-response.git
cd aeromesh-swarm-disaster-response

# Install dependencies
pip install -r requirements.txt

# Switch to Stage 2 branch
git checkout stage-2-development
```

## How to Reproduce Tests and Simulations

### Run All Tests
```bash
python -m pytest tests/ -v
```

**Expected Result:** 23 passed

### Run Single Scenario
```bash
python run_simulation.py --scenario 1
python run_simulation.py --scenario 2
python run_simulation.py --scenario 3
python run_simulation.py --scenario 4
```

### Run All Scenario Benchmarks
```bash
python run_simulation.py --benchmark-all
```

### Run Scalability Benchmark
```bash
python scalability_benchmark.py
```

## How to Inspect Differences Between Stage 1 and Stage 2

### GitHub Comparison URL
Once the branch is pushed:

```
https://github.com/nsd-surya-dinesh/aeromesh-swarm-disaster-response/compare/main...stage-2-development
```

### Local Comparison
```bash
# View files changed
git diff main..stage-2-development --stat

# View detailed changes
git diff main..stage-2-development
```

### Commit History
```bash
# View Stage 2 commits only
git log stage-2-development --not main --oneline
```

## Documentation Locations

| Document | Path |
|----------|------|
| Stage 2 Change Log | `docs/STAGE2_CHANGELOG.md` |
| This Overview | `docs/STAGE2_OVERVIEW.md` |
| Main README | `README.md` |
| Technical Proposal | `docs/TECHNICAL_PROPOSAL.md` |
| Installation Guide | `docs/INSTALLATION.md` |

## Known Limitations

1. **RF Interference Simulation** — `inject_rf_interference()` logs events but doesn't degrade links
2. **Secondary Hazard Zones** — `inject_secondary_hazard()` logs events but doesn't enforce no-fly zones
3. **Steiner Point** — Implementation uses simple midpoint, not true Euclidean Steiner tree
4. **Coordinate System** — Some modules use different coordinate systems (centered vs. corner origin)
5. **ROS 2 / PX4** — Integration not yet implemented

## Competition Readiness

| Capability | Status |
|------------|--------|
| CBBA Task Allocation | ✅ Verified |
| Multi-Hop Routing | ✅ Verified |
| Self-Healing Network | ✅ Verified |
| Battery Management | ✅ Verified |
| Scenario Benchmarks | ✅ 100% coverage, 100% PDR |
| Unit Tests | ✅ 23/23 passing |
| Heartbeat Timeout | ✅ NEW in Stage 2 |
| Correct Relay Logic | ✅ NEW in Stage 2 |
| ROS 2 Integration | ❌ Future work |
| Hardware Deployment | ❌ Future work |

---

**Stage 2 Status: Ready for Competition Demonstration**

For questions, contact: nagasuryadinesh@gmail.com