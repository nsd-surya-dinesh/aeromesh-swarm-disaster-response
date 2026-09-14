# AeroMesh-Swarm: Demonstration Video & Evaluation Guide

This guide details how to demonstrate and evaluate the key technical features of **AeroMesh-Swarm** for Stage 1 evaluation.

---

### Demonstration Walkthrough Checklist

When evaluating the proof-of-concept simulation, the key capabilities to observe are:

| Capability | Demonstration Action | What to Look For |
|---|---|---|
| **1. Autonomous Survey & CBBA Task Allocation** | Run Scenario 1 (`--scenario 1`) | UAVs disperse from GCS, greedily auctioning PoIs without overlapping paths or collisions |
| **2. Dynamic Multi-Hop Mesh Routing** | Observe blue/green link lines | Distant scouts establish multi-hop packet forwarding back to GCS |
| **3. Steiner Relay Positioning** | Run Scenario 2 (`--scenario 2`) | When Scouts enter deep canyons, intermediate UAVs transition to `RELAY` role (orange diamond) at geometric Steiner midpoints |
| **4. Dynamic Emergency Injection** | Run Scenario 3 (`--scenario 3`) | Emergency survivor cluster appears; scouts immediately preempt current tasks to survey high-priority site |
| **5. Autonomous Relay Failure Recovery** | Observe Scenario 3 at $t=180s$ | Critical relay hardware fails (red); adjacent scout or standby UAV immediately promotes itself to replace the relay within seconds |
| **6. Battery Management & RTB Handoff** | Run Scenario 4 (`--scenario 4`) | Low-battery UAVs return to GCS charging pads and cycle back to operational status without dropping swarm connectivity |

---

### Generating Demonstration Media

#### Record Video / Animated GIF for Scenario 1 (Baseline)
```bash
python run_simulation.py --scenario 1 --record
```

#### Record Video / Animated GIF for Scenario 3 (Self-Healing & Emergency Preemption)
```bash
python run_simulation.py --scenario 3 --record
```

#### Inspecting Benchmark Figures
Generated charts are saved in:
```text
docs/figures/
└── scenario_comparison.png   # Side-by-side bar charts for Coverage, PDR, Latency, and Energy Efficiency
```
