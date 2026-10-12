AEROMESH STAGE 2 — UNRESOLVED BLOCKERS (2026-10-11)
Evidence-based only; no fabricated resolutions.

1. WSL2 / Ubuntu 22.04 — NOT STARTED
   Blocker: Not required for simulation-stage verification; user approval needed before installation.
   Evidence: day1_wsl_ubuntu_environment.txt (NOT RUN — not failed)

2. ArduPilot SITL — BLOCKED
   Blocker: MAVLink/pymavlink and ArduPilot simulator not installed in Windows environment.
   Evidence: docs/SITL_SETUP.md exists; adapter framework intact; no SITL output file exists.
   Resolution path: Install dependencies; then run SITL; do not claim success before evidence exists.

3. Thermal sensing module — BLOCKED
   Blocker: Exact model, interface (I2C/USB?), resolution, FOV not specified in budget.
   Evidence: docs/HARDWARE_COMPATIBILITY_MATRIX.md (status BLOCKED)
   Resolution: Identify model; obtain datasheet; integrate after verification.

4. UWB positioning module — BLOCKED
   Blocker: Module model, protocol (DW1000/UWB-1?), anchor count/placement not specified.
   Evidence: docs/HARDWARE_COMPATIBILITY_MATRIX.md (status BLOCKED)
   Resolution: Identify model; verify protocol; confirm anchor placement.

5. Five-run full repeatability — PARTIAL
   Blocker: Requires extended runtime (each scenario ~260s+); not fully executed.
   Evidence: 1 representative seed-42 run completed (scenario 1, 263.9s, coverage 100%) saved in results/final_demo/
   Resolution: Execute remaining 4 runs when time permits; preserve all outputs.

6. test_5 route-recovery — DOCUMENTED (not hidden)
   Blocker: Fixture creates direct GCS link; graceful-drop assertion impossible at this spacing.
   Evidence: tests/test_route_recovery.py lines 160-185; test comment line 165.
   Resolution: No production fix needed; document for demonstration; do not change fixture or weaken assertion.

7. Power/ground/connector design — BLOCKED
   Blocker: Wiring diagram, voltage levels, connector pinouts not finalized; no physical build started.
   Evidence: Hardware matrix lists as BLOCKED (needs design).
   Resolution: Design before any physical connection.

8. Physical flight / motor test — NOT STARTED (intentionally blocked by safety rules)
   Blocker: Safety policy prohibits physical arming, takeoff, motor tests.
   Evidence: Safety rules documented; mock adapter never sends physical commands.
   Resolution: Not a blocker — correct behavior for simulation stage.
