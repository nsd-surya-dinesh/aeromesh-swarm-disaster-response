"""SwarmExplainableLogger — XAI audit with thread-safe append."""
import os
import threading
from datetime import datetime

class SwarmExplainableLogger:
    def __init__(self, drone_id):
        self.drone_id = drone_id
        os.makedirs("results", exist_ok=True)
        public_id = f"uav-{drone_id}" if isinstance(drone_id, int) else str(drone_id)
        self.path = f"results/{public_id}_decision_audit.txt"
        self._lock = threading.Lock()

    def log_decision(self, current_state, network_rssi, ground_hazard, calculated_action):
        ts = datetime.now().isoformat()
        line = f"[{ts}] [DECISION ENGINE]: State={current_state} | Net={network_rssi}dBm | Vision='{ground_hazard}' -> Action: {calculated_action}\n"
        with self._lock:
            with open(self.path, "a") as f:
                f.write(line)
        print("[XAI AUDIT]", line.strip())
