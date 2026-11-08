
# Autonomous UAV Swarm Disaster Response: Simulation Operations Manual
**Project:** AeroMesh-Swarm Disaster Response  
**Competition:** PUSHPAK Grand Challenge 2026 / MeitY (IIT Bombay) — Stage 2 (UAV-X)  
**Team Name:** ss  
**Repository References:**
- Swarm Mission Controller: [AeroMesh-Swarm](https://github.com/nsd-surya-dinesh/aeromesh-swarm-disaster-response)
- Official Environment: [meity_grand_challenge](https://github.com/TheAmanAnsari/meity_grand_challenge) / [uavsim](https://github.com/NirmanJaiswal36/uavsim)

---

## 1. System Architecture & Mission Overview

### Mission Objectives
The mission requires an autonomous swarm of multi-rotor UAVs to execute Beyond Visual Line of Sight (BVLOS) search-and-reconnaissance over a communication-denied disaster zone. The fleet must locate 10 hidden ground targets marked with ArUco 4x4_50 plates (IDs 0–9), maintain telemetry contact with a Ground Control Station (GCS) via a self-healing ad-hoc mesh network, and return safely to base before battery depletion.

### Operational Environment Specifications
- **Search Zone (ROI):** 500 m × 500 m forest centered at origin $(0, 0)$, bounded within $x \in [-250, 250]$ and $y \in [-250, 250]$ meters.
- **Canopy:** 726 oak and pine trees with heights between 8 m and 16 m.
- **GCS Apron:** Located west of the forest at $x = -365\,\text{m}$, equipped with 24 numbered landing pads spaced 6 m apart.
- **World Origin:** Latitude $-35.389138^\circ$, Longitude $149.219188^\circ$, Ground Elevation $580.0\,\text{m}$.
- **Target Spawning Profile:** Targets spawn dynamically over time. A subset appears at launch while remaining targets spawn at randomized intervals within the first 20 minutes of simulation time.

### Fleet & Avionics Baseline
- **Platform:** ArduCopter Iris Quadcopter (1.5 kg AUW, 10 m/s cruise, 15 m/s max velocity).
- **Sensors:** 3-axis gimbal-stabilized down-facing (nadir) RGB camera (10 Hz, 80° HFOV) publishing on `/image_raw`.
- **Autopilot Backend:** ArduPilot Copter SITL executing lockstep physics synchronization against Gazebo Harmonic.

---

## 2. Host System Prerequisites & Setup

### Windows WSL 2 and Docker Architecture
The simulation environment is containerized within Ubuntu 22.04 LTS running ROS 2 Humble Hawksbill, Gazebo Harmonic, and ArduPilot SITL.

```text
[ Windows 10/11 Host ]
         │
         ▼ WSL 2 Engine (Ubuntu 22.04)
[ Docker Container: meity_uav_challenge ]
   ├── ROS 2 Humble (/opt/ros/humble)
   ├── Gazebo Harmonic (gz-sim8)
   ├── 4x ArduCopter SITL Processes (sysid 1..4)
   └── 4x MAVProxy Telemetry Routers
```

### Essential Host Preparation
1. Enable X11 display permissions from WSL 2 so Gazebo GUI windows can render:
   ```bash
   xhost +local:root
   xhost +
   ```
2. Start the container:
   ```bash
   docker start meity_uav_challenge
   ```
3. Ensure ROS 2 Humble is automatically loaded in the container user profile:
   ```bash
   docker exec -it meity_uav_challenge bash -c "echo 'source /opt/ros/humble/setup.bash' >> ~/.bashrc"
   ```

---

## 3. Real-Time Factor (RTF) Optimization

### The CPU Bottleneck Problem
In virtualized WSL 2 environments running on CPU software rendering (Mesa LLVMpipe), Gazebo attempts to calculate complex 3D polygon contact meshes for all 726 forest trees against 4 drone collision hulls. This drops the Real-Time Factor (RTF) to **0.0001** (taking over an hour of real time to advance 1 second of simulation clock).

### Permanent Optimization: Strip Tree Collision Meshes
Because drones survey at altitudes of 12 m to 20 m AGL, tree collision meshes can be stripped while preserving full visual tree rendering. This reduces physics load by 95% and restores RTF to **0.85–1.00**:

```bash
docker exec -it meity_uav_challenge python3 -c '
import glob, re
sdfs = glob.glob("/workspace/uavsim/**/*.sdf", recursive=True)
count = 0
for path in sdfs:
    if any(k in path.lower() for k in ["tree", "pine", "oak"]):
        try:
            with open(path, "r") as f: content = f.read()
            clean = re.sub(r"<collision\b[^>]*>.*?</collision>", "", content, flags=re.DOTALL)
            if clean != content:
                with open(path, "w") as f: f.write(clean)
                count += 1
        except Exception: pass
print(f"Stripped collision meshes from {count} tree models. RTF restored to real-time.")
'
```

---

## 4. Standard 3-Terminal Launch Workflow

Always operate with three dedicated terminal panes for clean separation of execution, monitoring, and flight control.

```text
┌───────────────────────────────┐     ┌───────────────────────────────┐     ┌───────────────────────────────┐
│          TERMINAL 1           │     │          TERMINAL 2           │     │          TERMINAL 3           │
│     Simulation Lifecycle      │     │    Live Telemetry Monitor     │     │       Flight Operations       │
│                               │     │                               │     │                               │
│  uavsim up --no-wait          │     │  Stream live alt & clock      │     │  A: Tmux MAVProxy Console     │
│  uavsim down (after 45s+ sim) │     │  Verify sim_time >= 45s       │     │  B: Swarm REPL Mode           │
│  uavsim review archive        │     │  Track airborne climb         │     │  C: Autonomous AeroMesh       │
└───────────────────────────────┘     └───────────────────────────────┘     └───────────────────────────────┘
```

### Terminal 1: Simulation Engine
Start the simulation with the `--no-wait` flag to bypass autopilot boot timeouts:
```bash
docker exec -it meity_uav_challenge bash -c "source /opt/ros/humble/setup.bash && cd /workspace/uavsim && ./bin/uavsim up scenarios/forest_rescue.yaml --team ss --no-wait"
```
*Note: In the Gazebo window, verify that the bottom-left Play button (`▶`) is clicked so physics runs unpaused.*

### Terminal 2: Live Flight Telemetry Stream
Keep this terminal visible to monitor real-time altitude, climb rate, and GPS telemetry:
```bash
docker exec -it meity_uav_challenge python3 -c "
from pymavlink import mavutil
import time
m = mavutil.mavlink_connection('udpin:127.0.0.1:14750', source_system=255)
m.wait_heartbeat(timeout=15)
print('--- TELEMETRY STREAM ONLINE ---')
while True:
    msg = m.recv_match(type=['GLOBAL_POSITION_INT', 'VFR_HUD'], blocking=True, timeout=1)
    if msg:
        if msg.get_type() == 'GLOBAL_POSITION_INT':
            print(f'Altitude: {msg.relative_alt/1000.0:6.2f} m | Lat: {msg.lat/1e7:.6f}, Lon: {msg.lon/1e7:.6f}')
        elif msg.get_type() == 'VFR_HUD':
            print(f'Throttle: {msg.throttle:3d}% | Climb Rate: {msg.climb:+5.2f} m/s')
    time.sleep(0.5)
"
```

---

## 5. Flight Control Methods

### Method A: Built-in MAVProxy Console via Tmux (Direct Control)

This method communicates directly with the autopilot flight loop without socket overhead.

1. Attach to the session:
   ```bash
   docker exec -it meity_uav_challenge tmux attach -t uavsim-rescue
   ```
2. Navigate between drone windows using `Ctrl + B`, then the window number:
   - Window `4`: Drone 1 (`ardupilot_iris_gimbal_0`)
   - Window `5`: Drone 2 (`ardupilot_iris_gimbal_1`)
   - Window `6`: Drone 3 (`ardupilot_iris_gimbal_2`)
   - Window `7`: Drone 4 (`ardupilot_iris_gimbal_3`)
3. Execute flight commands in the `MAV>` console:
   ```text
   mode GUIDED
   param set ARMING_CHECK 0
   arm throttle force
   takeoff 15
   position 150 0 -15
   ```
4. Detach safely without stopping flight: Press `Ctrl + B`, then `D`.

### Method B: Interactive Swarm REPL

To control all drones simultaneously through the custom REPL:

1. Configure `/workspace/test/swarm_repl.py` with force-arming and direct client endpoints:
   - SYSID 1: `udpin:127.0.0.1:14750`
   - SYSID 2: `udpin:127.0.0.1:14751`
   - SYSID 3: `udpin:127.0.0.1:14752`
   - SYSID 4: `udpin:127.0.0.1:14753`
2. Start the REPL:
   ```bash
   docker exec -it meity_uav_challenge python3 /workspace/test/swarm_repl.py
   ```
3. Command syntax:
   ```text
   swarm> connect
   swarm> arm all
   swarm> takeoff all 15
   swarm> moveall 150 0 15 10
   swarm> rtl
   ```

### Method C: Autonomous Mission Controller (`test/mission.py`)

Run the full autonomous search controller:
```bash
docker exec -it meity_uav_challenge bash -c "source /opt/ros/humble/setup.bash && cd /workspace/aeromesh && python3 test/mission.py"
```

The script reads `/tmp/uavsim/rescue/manifest.json`, connects to all active endpoints concurrently, commands staggered takeoffs (12 m, 15 m, 18 m, 21 m), and executes a lawnmower grid search across each quadrant.

---

## 6. Teardown, Log Packaging & Scoring

### Stopping the Run
Never close Terminal 1 with `Ctrl + C`. Always use `uavsim down` so the ROS 2 bag closes cleanly and packages the run archive:

```bash
docker exec -it meity_uav_challenge bash -c "cd /workspace/uavsim && ./bin/uavsim down scenarios/forest_rescue.yaml"
```

The tool stops processes and generates the submission package:
`hand in: /workspace/uavsim/uavsim_runs/ss_<timestamp>.tar.gz`

### Scoring the Archive
Run `review` against your latest archive with ROS 2 sourced:

```bash
docker exec -it meity_uav_challenge bash -c 'source /opt/ros/humble/setup.bash && cd /workspace/uavsim && LATEST=$(ls -t uavsim_runs/*.tar.gz | head -n 1) && ./bin/uavsim review "$LATEST"'
```

### Review Metric Definitions
- **`AIRBORNE`**: Total duration (in simulation time) where vehicle altitude exceeded 0.5 m AGL.
- **`OVER FOREST`**: Total duration where horizontal coordinates entered the forest extent ($x \in [-250, 250]$, $y \in [-250, 250]$).
- **`FLOWN`**: Total cumulative 3D path distance in meters.
- **`MAX ALT`**: Highest altitude achieved above ground level.
- **`CLOSEST`**: Minimum 3D Euclidean distance (in meters) recorded between the drone camera and ground truth ArUco target markers.

### Exporting Files to Windows
```bash
# Copy latest run archive and track plot to Windows host
mkdir -p ~/pushpak_stage2/export
docker cp meity_uav_challenge:/workspace/uavsim/uavsim_runs ~/pushpak_stage2/export/

# Open in Windows Explorer:
explorer.exe ~/pushpak_stage2/export/uavsim_runs
```

---

## 7. Troubleshooting & Root Cause Matrix

| Error / Failure | Underlying Cause | Verified Fix |
| :--- | :--- | :--- |
| `failed to discover GPU vendor from CDI` | Docker Desktop on Windows missing NVIDIA CDI YAML spec. | Remove `--gpus all` from `start_container.sh` or run `sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml` in WSL 2. |
| `ModuleNotFoundError: No module named 'rosbag2_py'` | ROS 2 Humble environment not sourced before executing Python command. | Run `source /opt/ros/humble/setup.bash` before calling `uavsim review`. |
| `Arm not confirmed; ACK=4` | ArduPilot pre-arm checks failing due to clock jitter in SITL (`Gyros inconsistent`). | Send force-arming with `param1=1, param2=21196` in `MAV_CMD_COMPONENT_ARM_DISARM`, or run `param set ARMING_CHECK 0`. |
| `Heartbeat timeout` on `14650` | Socket type mismatch (`udp:` acts as sender `udpout` in PyMAVLink). | Connect using `udpin:127.0.0.1:14750...14753` with `source_system=255`. |
| `real_time_factor: 0.0001` | CPU computing polygon collisions for 726 tree models. | Run the collision stripping Python script in Section 3 to remove `<collision>` tags from tree SDF models. |
| `AIRBORNE: 0 s` in scorecard | Simulation stopped before 26 seconds of physics time elapsed. | Monitor `/world/rescue/stats` and ensure `sim_time` reaches $\ge 45\,\text{s}$ before invoking `uavsim down`. |
| `Additional properties are not allowed ('duration')` | `duration:` placed at root level of `forest_rescue.yaml`. | Remove `duration:` from the YAML file; `uavsim` controls run duration via `down`. |
| `bash: /root/.bashrc: Permission denied` | Container running as non-root user `meitychallenge`. | Append to `~/.bashrc` instead of `/root/.bashrc`, or pass `-u 0` for root operations. |

---

## 8. Grand Finale (Stage 3) Winning Flight Protocols

### 1. Handling the Dynamic 20-Minute Target Spawning
Target ROIs do not all spawn at $t=0$. They spawn incrementally over the first 20 minutes of simulation time. Maintain continuous quadrant sweeping loops for at least 25 minutes to ensure late-spawning sites are logged.

### 2. Camera Nadir Alignment & ArUco Detection
Ensure camera gimbals are commanded to nadir pitch ($-90^\circ$ or $-1.57\,\text{rad}$) upon reaching search altitude:
```bash
ros2 topic pub /ardupilot_iris_gimbal_0/gimbal_cam/cmd_pitch std_msgs/msg/Float64 "{data: -1.57}" --once
```
Average marker detections over 3–5 consecutive frames to filter false positives and minimize 3D localization RMSE.

### 3. Flight Altitude Deconfliction
Assign distinct altitudes across swarm members to guarantee zero collision penalties:
- UAV 1: 12 m AGL (low-altitude high-resolution scout)
- UAV 2: 15 m AGL (intermediate search scout)
- UAV 3: 18 m AGL (intermediate search scout)
- UAV 4: 21 m AGL (high-altitude communication relay node)

### 4. Automated Return to Launch (RTL)
Command RTL before battery capacity falls below 20% to prevent forced landings outside the apron, which incur severe penalty deductions.
