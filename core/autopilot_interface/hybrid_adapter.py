"""HybridAutopilotAdapter — MAVSDK serial + SITL fallback."""
import asyncio

class HybridAutopilotAdapter:
    def __init__(self, serial_port="/dev/ttyTHS1", baudrate=921600,
                 sitl_address="udp://:14540"):
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.sitl_address = sitl_address
        self._connected = False

    def connect_interface(self):
        ports = ["/dev/ttyTHS1", "/dev/ttyAMA0", "/dev/ttyACM0"]
        found = None
        # Auto-detect (simulated check; in real use try open)
        for p in ports:
            if p == self.serial_port:  # use configured/default
                found = p
                break
        if found:
            print("[BOOT] HybridAdapter serial:", found)
            self._serial_url = f"serial://{found}:{self.baudrate}"
        else:
            self._serial_url = self.sitl_address
            print("[BOOT] HybridAdapter SITL fallback:", self.sitl_address)
        self._connected = True
        return self._serial_url

    async def wait_for_ekf_convergence(self, timeout=120):
        # Async loop; mock-only for tests
        print("[EKF] waiting for EKF convergence")
        for _ in range(3):
            await asyncio.sleep(0.01)
        print("[EKF] ready")
        return True

    async def telemetry_stream(self):
        # Async generator
        yield {"position": (0,0,0), "battery": 1.0, "health": {"is_global_position_ok": True, "is_home_position_ok": True}}
