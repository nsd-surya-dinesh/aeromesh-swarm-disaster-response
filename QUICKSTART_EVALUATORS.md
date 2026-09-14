# Quick Start Guide for Evaluators
## AeroMesh-Swarm - Stage 1 Submission

**Estimated Evaluation Time:** 10 minutes  
**Last Updated:** September 14, 2026

---

## Prerequisites

- Python 3.9 or higher
- Terminal / Command Prompt access
- 4GB RAM, 2+ CPU cores

---

## 3-Step Quick Evaluation

### Step 1: Setup (1 minute)

```bash
cd uav_swarm_disaster_response
pip install -r requirements.txt
```

Expected output: All dependencies installed successfully.

---

### Step 2: Run Tests (1 minute)

```bash
python -m pytest tests/ -v
```

Expected output:
```
19 passed in ~1.7s
```

---

### Step 3: Run Benchmarks (5-7 minutes)

```bash
python run_simulation.py --benchmark-all
```

Expected output:
```
================================================================================
BENCHMARK COMPARISON MATRIX
================================================================================
Metric                           | S1: Baseline | S2: Canyon   | S3: Fault    | S4: Endurance
--------------------------------------------------------------------------------
Coverage (%)                     | 100.0        | 100.0        | 100.0        | 100.0       
PDR (%)                          | 100.0        | 100.0        | 100.0        | 100.0       
Avg Latency (ms)                 | 101.7        | 282.2        | 123.0        | 114.4       
...
================================================================================
```

Charts generated at: `docs/figures/scenario_comparison.png`

---

## What to Look For

### ✅ Mission Success Criteria
- **100% Coverage**: All PoIs surveyed across all scenarios
- **100% PDR**: Zero packet loss despite multi-hop routing
- **100% Survival**: No UAV battery exhaustion failures

### ✅ Key Technical Demonstrations

| Feature | Scenario | Timestamp | What Happens |
|---------|----------|-----------|--------------|
| **Distributed Task Allocation** | S1 | t=0-60s | UAVs autonomously auction and claim PoIs without conflicts |
| **Multi-Hop Relay Formation** | S2 | t=0-120s | Deep canyon scenario deploys 3-hop relay chain |
| **Emergency Preemption** | S3 | t=100s | High-priority survivor discovery triggers immediate re-allocation |
| **Self-Healing** | S3 | t=180s | Relay failure detected and replaced within 2.1 seconds |
| **Battery Cycling** | S4 | t=0-352s | UAVs return to GCS, recharge, and resume without network loss |

---

## Optional: View Single Scenario

```bash
# Run Scenario 3 (Dynamic Fault & Self-Healing)
python run_simulation.py --scenario 3
```

Output shows timestamped progress:
```
>> Starting mission simulation...
   UAVs: 6, PoIs: 8
   t=0s | Coverage: 0.0%
   t=30s | Coverage: 0.0%
   t=60s | Coverage: 12.5%
   ...
   t=180s | Coverage: 75.0%
[+] Mission completed at t=229.9s
```

---

## Documentation Reference

| Document | Purpose | Location |
|----------|---------|----------|
| **Technical Proposal** | 6-8 page detailed design | `docs/TECHNICAL_PROPOSAL.md` |
| **README** | Project overview & architecture | `README.md` |
| **Installation Guide** | Complete setup instructions | `docs/INSTALLATION.md` |
| **Submission Package** | Deliverables checklist | `docs/SUBMISSION_PACKAGE.md` |

---

## Troubleshooting

### Issue: Tests fail with import errors
**Solution:** Ensure you're in the project root directory:
```bash
cd uav_swarm_disaster_response
python -m pytest tests/ -v
```

### Issue: Benchmark runs slowly
**Expected:** Each scenario takes 1-2 minutes in fast headless mode. Total benchmark suite: ~5-7 minutes.

### Issue: Charts not generated
**Solution:** Charts auto-generate after benchmark completion. Check:
```bash
ls docs/figures/scenario_comparison.png
```

---

## Verification Checklist for Judges

- [ ] All 19 tests pass
- [ ] All 4 scenarios achieve 100% coverage
- [ ] Benchmark matrix displays correctly
- [ ] Charts generated in `docs/figures/`
- [ ] Technical proposal is clear and comprehensive
- [ ] Code is well-documented and modular

---

## Questions or Issues?

If you encounter any problems during evaluation:
1. Check `docs/INSTALLATION.md` for detailed troubleshooting
2. Run `python verify_submission.py` to check submission status
3. Ensure Python version is 3.9 or higher: `python --version`

---

**Total Evaluation Time: ~10 minutes**  
**Expected Result: All deliverables verified successfully**
