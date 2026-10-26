# Entry point for judge
# 1. docker run ... (see RESTART_CHECKLIST.md)
# 2. uavsim up scenarios/forest_rescue.yaml
# 3. python3 test/mission.py
# Expected: 4 connections, sysid-matched heartbeat, GPS/EKF >=3, arm once, GUIDED, log to uavsim_runs/
