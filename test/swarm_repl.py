#!/usr/bin/env python3
"""AeroMesh Direct MAVLink Swarm REPL"""
import sys, time
from pymavlink import mavutil

ENDPOINTS = [
    (1, "tcp:127.0.0.1:5760", "ardupilot_iris_gimbal_0"),
    (2, "tcp:127.0.0.1:5770", "ardupilot_iris_gimbal_1"),
    (3, "tcp:127.0.0.1:5780", "ardupilot_iris_gimbal_2"),
    (4, "tcp:127.0.0.1:5790", "ardupilot_iris_gimbal_3"),
]

class DirectRepl:
    def __init__(self):
        self.drones = {}

    def connect(self):
        print("\nConnecting directly to ArduPilot via internal TCP...")
        for sysid, ep, name in ENDPOINTS:
            print(f"[{sysid}] Connecting to {ep} ({name})...", end=" ", flush=True)
            try:
                m = mavutil.mavlink_connection(ep, source_system=255)
                m.wait_heartbeat(timeout=8)
                m.set_mode("GUIDED")
                m.param_set_send("ARMING_CHECK", 0, mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
                self.drones[sysid] = m
                print("CONNECTED!")
            except Exception as e:
                print("SKIPPED (not spawned)")

        print(f"\nConnected: {len(self.drones)} drones ready in GUIDED mode.\n")

    def status(self):
        for sysid, m in self.drones.items():
            print(f"[{sysid}] Active in GUIDED mode")

    def arm(self, target="all"):
        targets = self.drones.keys() if target == "all" else [int(target)]
        for sysid in targets:
            if sysid in self.drones:
                m = self.drones[sysid]
                m.set_mode("GUIDED")
                m.mav.command_long_send(sysid, 1, mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 1, 21196, 0,0,0,0,0)
                print(f"[{sysid}] Armed (force).")

    def takeoff(self, target="all", alt=15):
        targets = self.drones.keys() if target == "all" else [int(target)]
        for sysid in targets:
            if sysid in self.drones:
                m = self.drones[sysid]
                m.set_mode("GUIDED")
                m.mav.command_long_send(sysid, 1, mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 1, 21196, 0,0,0,0,0)
                time.sleep(1)
                m.mav.command_long_send(sysid, 1, mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0,0,0,0,0,0, float(alt))
                print(f"[{sysid}] Climbing to {alt}m.")

    def moveall(self, north=150, east=0, down=15, dur=10):
        for sysid, m in self.drones.items():
            m.mav.set_position_target_local_ned_send(
                0, sysid, 1, mavutil.mavlink.MAV_FRAME_LOCAL_NED,
                0b0000111111111000,
                float(north), float(east), -abs(float(down)),
                0,0,0, 0,0,0, 0,0
            )
            print(f"[{sysid}] Flying forward into forest [{north}m, {east}m].")

    def rtl(self):
        for sysid, m in self.drones.items():
            m.set_mode("RTL")
            print(f"[{sysid}] Returning to launch pad (RTL).")

def main():
    r = DirectRepl()
    print("=== Easy Direct MAVLink REPL ===")
    print("Commands: connect | arm <id|all> | takeoff <id|all> <alt> | moveall <N> <E> <alt> | rtl | exit")
    while True:
        try:
            line = input("swarm> ").strip().split()
            if not line: continue
            cmd = line[0].lower()
            if cmd in ("exit", "quit"): break
            elif cmd == "connect": r.connect()
            elif cmd == "status": r.status()
            elif cmd == "arm": r.arm(line[1] if len(line) > 1 else "all")
            elif cmd == "takeoff": r.takeoff(line[1] if len(line) > 1 else "all", line[2] if len(line) > 2 else 15)
            elif cmd == "moveall": r.moveall(line[1] if len(line) > 1 else 150, line[2] if len(line) > 2 else 0, line[3] if len(line) > 3 else 15)
            elif cmd == "rtl": r.rtl()
            else: print("Available: connect, arm, takeoff, moveall, rtl, exit")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
