"""Failure detector — heartbeat timeout, ALERT, XAI log, stub reallocation."""
from typing import List

class FailureDetector:
    heartbeat_timeout = 5.0
    def __init__(self):
        self.heartbeats = {}

    def update(self, drone_id: int, timestamp: float):
        self.heartbeats[drone_id] = timestamp

    def get_failed_drones(self, now: float) -> List[int]:
        failed = [d for d, ts in self.heartbeats.items() if (now - ts) > self.heartbeat_timeout]
        return failed

    def on_failure(self, drone_id: int):
        print(f"[FAIL] ALERT: heartbeat lost drone {drone_id}")
        print(f"[XAI] DEDUCTION: Heartbeat timeout. Marking node failed. Triggering reallocation stub.")
        # Dashboard ALERT status handled by caller; XAI audit handled by logger

    def reallocate_grid(self, failed_id: int, active_ids: List[int]) -> List[int]:
        # Stub — return active_ids as reassigned grid cells
        return active_ids[:]
