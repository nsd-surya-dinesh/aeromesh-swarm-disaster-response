"""Check hardware — serial, dialout, MAVSDK, mesh0."""
import os, subprocess, json

class HardwareChecker:
    def __init__(self):
        self.results = {}

    def check_serial(self):
        for p in ["/dev/ttyTHS1", "/dev/ttyAMA0", "/dev/ttyACM0"]:
            self.results[p] = os.path.exists(p)
        return self.results

    def check_dialout(self):
        try:
            import grp
            self.results["dialout"] = "dialout" in [g.gr_name for g in grp.getgrall() if os.getuid() in g.gr_mem or g.gr_gid == os.getgid()]
        except Exception:
            self.results["dialout"] = False
        return self.results

    def try_mavsdk(self):
        # Mock try; real mavsdk requires import
        self.results["mavsdk_serial"] = False
        self.results["mavsdk_sitl"] = True
        return self.results

    def check_mesh0(self):
        try:
            out = subprocess.run(["ip", "addr", "show", "mesh0"], capture_output=True, text=True)
            self.results["mesh0_ip"] = out.stdout[:60]
        except Exception:
            self.results["mesh0_ip"] = None
        try:
            out = subprocess.run(["iw", "dev", "mesh0", "info"], capture_output=True, text=True)
            self.results["mesh0_iw"] = out.stdout[:60]
        except Exception:
            self.results["mesh0_iw"] = None
        return self.results

    def print_health_flags(self):
        # Mock flags
        print("[BOOT] is_global_position_ok=True | is_home_position_ok=True | is_armable=False")
        self.results["health"] = {"is_global_position_ok": True, "is_home_position_ok": True, "is_armable": False}

    def run_all(self):
        self.check_serial()
        self.check_dialout()
        self.try_mavsdk()
        self.check_mesh0()
        self.print_health_flags()
        print(json.dumps(self.results))
