# AeroMesh-Swarm: Installation & Setup Guide

This guide provides step-by-step instructions to set up, test, and run the **AeroMesh-Swarm** platform on Linux, macOS, and Windows.

---

### 1. Prerequisites

- **Python**: Version 3.9, 3.10, 3.11, 3.12, 3.13, or 3.14
- **Operating System**: Ubuntu 20.04/22.04/24.04, macOS (Intel/Apple Silicon), or Windows 10/11
- **Hardware**: Standard laptop / desktop (minimum 2 cores, 4GB RAM)

---

### 2. Quick Installation

#### Step 1: Clone or Navigate to the Repository
```bash
git clone https://github.com/nsd-surya-dinesh/aeromesh-swarm-disaster-response.git
cd aeromesh-swarm-disaster-response
```

#### Step 2: Create a Virtual Environment (Recommended)
```bash
# On Linux / macOS:
python3 -m venv venv
source venv/bin/activate

# On Windows (PowerShell / Command Prompt):
python -m venv venv
.\venv\Scripts\activate
```

#### Step 3: Install Required Dependencies
```bash
pip install -r requirements.txt
```

*Note: If `pygame` fails to build on your specific OS platform, all simulations, web dashboards, video recorders, and benchmark runners operate headlessly with 100% functionality without requiring pygame.*

---

### 3. Running Automated Tests

Run the complete test suite (19 unit and integration tests):
```bash
python -m pytest tests/ -v
```

Expected Output:
```text
tests/test_comm.py::TestRFChannel::test_los_probability_high_altitude PASSED
tests/test_comm.py::TestRFChannel::test_path_loss_increases_with_distance PASSED
tests/test_comm.py::TestRFChannel::test_link_quality_close_distance PASSED
tests/test_comm.py::TestMeshRouter::test_routing_table_construction PASSED
tests/test_comm.py::TestMeshRouter::test_packet_delivery PASSED
tests/test_comm.py::TestSteinerRelayManager::test_relay_position_midpoint PASSED
tests/test_comm.py::TestSteinerRelayManager::test_multi_hop_relay_chain PASSED
tests/test_simulation.py::TestScenarios::test_scenario_1_baseline_completion PASSED
tests/test_simulation.py::TestScenarios::test_scenario_2_deep_canyon_connectivity PASSED
tests/test_simulation.py::TestScenarios::test_scenario_4_battery_cycling PASSED
tests/test_simulation.py::TestScenarios::test_metrics_calculation PASSED
tests/test_simulation.py::TestEventInjection::test_dynamic_poi_injection PASSED
tests/test_simulation.py::TestEventInjection::test_relay_failure_recovery PASSED
tests/test_swarm.py::TestCBBATaskAllocator::test_marginal_score_calculation PASSED
tests/test_swarm.py::TestCBBATaskAllocator::test_cbba_allocation_assigns_tasks PASSED
tests/test_swarm.py::TestPathPlanner::test_collision_avoidance_repulsion PASSED
tests/test_swarm.py::TestPathPlanner::test_dubins_path_generation PASSED
tests/test_swarm.py::TestHealthMonitor::test_low_battery_triggers_rtb PASSED
tests/test_swarm.py::TestHealthMonitor::test_charging_restoration PASSED
============================= 19 passed in ~1.5s ==============================
```

---

### 4. Running Mission Scenarios

#### Run a Single Scenario (Headless Fast Execution)
```bash
# Scenario 1: Baseline Survey (5 UAVs, 10 PoIs)
python run_simulation.py --scenario 1

# Scenario 2: Deep Canyon / Line-of-Sight Obstacle (6 UAVs, 8 PoIs)
python run_simulation.py --scenario 2

# Scenario 3: Dynamic Emergency & Relay Failure (6 UAVs, 8 PoIs)
python run_simulation.py --scenario 3

# Scenario 4: Endurance & Continuous Battery Swapping (8 UAVs, 16 PoIs)
python run_simulation.py --scenario 4
```

#### Run All Scenarios & Generate Benchmark Report
```bash
python run_simulation.py --benchmark-all
```
This command runs all 4 scenarios, prints the side-by-side performance matrix, and generates comparative publication charts in `docs/figures/scenario_comparison.png`.

---

### 5. Interactive Visualizations & Demo Recording

#### 1. Interactive Desktop GUI (Pygame)
```bash
python run_simulation.py --scenario 1 --gui
```
- **Controls**:
  - `[SPACE]`: Pause / Resume simulation
  - `[L]`: Toggle wireless communication mesh links
  - `[+] / [-]`: Increase / Decrease simulation speed (up to 10x)
  - `[ESC]`: Exit

#### 2. Headless Video / GIF Demo Generator
```bash
python run_simulation.py --scenario 3 --record
```
Generates `scenario_3_demo.mp4` (or `.gif` if FFmpeg is not installed) showcasing dynamic survivor preemption and autonomous relay self-healing.
