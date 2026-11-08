# SITL Setup — AeroMesh-Swarm Stage 2
Status: NOT RUN — blocker: pymavlink not installed; ArduPilot SIM not installed; sim_vehicle not in PATH
Target: ArduPilot SITL with X500 model (Pixhawk 2.4.8 compatible)
Prerequisites (NOT currently met):
- Python package: pymavlink (ModuleNotFoundError confirmed)
- ArduPilot repository + build (sim_vehicle command missing from PATH)
- Linux/WSL environment (Windows native simulation runs; SITL requires Linux typically)
Verification command (NOT executed due to blockers):
  sim_vehicle.py -v ArduCopter -f gazebo --console --map
Expected output: MAVLink heartbeat from UDP endpoint (e.g., udp:127.0.0.1:14550)
Integration command (NOT executed — requires SITL running first):
  python -c "from core.autopilot_interface.simulator_adapter import SimulatorAdapter; ..."
Safety: Default mode SIMULATION only; never arming; mock adapter clearly separated.
Next step with approval: Install pymavlink, clone ArduPilot, build SITL, then verify heartbeat independently before integrating with AeroMesh.
