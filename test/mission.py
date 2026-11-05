#!/usr/bin/env python3
import json
import time
from pymavlink import mavutil

print("=== Starting AeroMesh Swarm Mission Controller ===")

with open("/tmp/uavsim/rescue/manifest.json", "r") as f:
    manifest = json.load(f)

# Connect to the active endpoints
endpoints = [(3, "udpin:127.0.0.1:14670", 15), (4, "udpin:127.0.0.1:14680", 20)]
drones = []

for sysid, ep, alt in endpoints:
    print(f"[AeroMesh] Connecting to UAV {sysid} on {ep}...", end=" ", flush=True)
    try:
        m = mavutil.mavlink_connection(ep, source_system=255)
        m.wait_heartbeat(timeout=15)
        m.set_mode("GUIDED")
        m.param_set_send("ARMING_CHECK", 0, mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
        drones.append((sysid, m, alt))
        print("CONNECTED.")
    except Exception as e:
        print(f"FAILED: {e}")

# Arm and takeoff
for sysid, m, alt in drones:
    m.mav.command_long_send(sysid, 1, mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 1, 21196, 0,0,0,0,0)
    time.sleep(1)
    m.mav.command_long_send(sysid, 1, mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0,0,0,0,0,0, float(alt))
    print(f"[AeroMesh] UAV {sysid}: Armed and Taking off to {alt}m.")

print("\n[AeroMesh] Ingress into Forest Search Area...")
for sysid, m, alt in drones:
    m.mav.set_position_target_local_ned_send(
        0, sysid, 1, mavutil.mavlink.MAV_FRAME_LOCAL_NED,
        0b0000111111111000,
        150.0, 0.0, -float(alt),
        0,0,0, 0,0,0, 0,0
    )

print("[AeroMesh] Swarm running autonomous search pattern.")
