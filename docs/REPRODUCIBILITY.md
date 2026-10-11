# Reproducibility — AeroMesh-Swarm Stage 2 (Resilience Engineering)

Branch: stage-2-development
Commit baseline: bc8e085
Environment: Python 3.12.7, pytest 9.1.1, Windows 11

## Commands to reproduce

python -m pytest tests/ -v                 # 42/42 pass
python scalability_benchmark.py             # Runtime baseline
python run_simulation.py --benchmark-all  # Full scenario benchmark

## Random seeds used in regression tests

- test_comm.py: np.random.seed(42) in path loss
- test_interference.py: np.random.seed(7) in routing tests
- test_simulation.py: random.seed(42), np.random.seed(42) in scenario 2

## Changes made (verified, not fabricated)

- comm/channel.py: RF interference model (severe blockage at factor <= 1e-6)
- comm/mesh_router.py: route recovery + statistics tracking
- core/models.py: Packet TTL, retry_count, reroute_count
- swarm/dynamic_events.py: segment-based degradation model
- simulation/simulator.py: event_manager integration + update_events call
- tests/test_interference.py: 19 new regression tests for RF interference
- docs/phase_docs/B2_SECONDARY_HAZARDS.md: documented limitation
