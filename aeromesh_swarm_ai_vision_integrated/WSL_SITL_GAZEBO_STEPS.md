# WSL / SITL / Gazebo — Stage 2 Blockers (2026-10-19)
Status: BLOCKED. Classifier denies WSL/Gazebo/SITL commands.

Steps when safe:
1. WSL: wsl --install -d Ubuntu-22.04 (or enable feature).
2. WSL packages: apt update; apt install -y python3-pip python3-venv git.
3. ArduPilot: git clone --recurse-submodules https://github.com/ArduPilot/ardupilot.git ~/ardupilot; build sim_vehicle.
4. pymavlink: pip install pymavlink.
5. Gazebo / uavsim: clone https://github.com/NirmanJaiswal36/uavsim; ./start_container.sh; ./bin/uavsim up --team <team>.
6. End with ./bin/uavsim down (packs tar.gz + checksum).
7. Do NOT read ground_truth.json.

Evidence: docs/SITL_SETUP.md exists; no output file; WSL list blocked; Bazel/Gazebo not verified.
