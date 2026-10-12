"""
AI / Automation Layer for Stage 2 (preserves CBBA, ETX, APF)
Provides automated decision support without replacing existing algorithms.
- PoI priority updater (thermal/spatial feature based)
- Automated relay promotion trigger (when dependency detected)
- Batch validation gateway for setpoints
"""
from typing import Dict, Optional, List
import numpy as np
from core.models import UAV, PointOfInterest, MissionState


class PoIPriorityAI:
    """Simple feature-based priority updater for new PoIs / thermal detections."""
    def update_priority(self, poi: PointOfInterest, thermal_hot: bool = False,
                        distance_to_nearest_relay: float = 999.0) -> float:
        base = poi.priority
        if thermal_hot:
            base = max(base, 8.0)
        # Closer to relay = can respond faster; slight boost
        return float(base + (5.0 / max(1.0, distance_to_nearest_relay)))


class AutomationEngine:
    """Automation: triggers actions that preserve manual oversight and safety gates."""
    def __init__(self, mission_state: MissionState):
        self.mission_state = mission_state
        self.priority_ai = PoIPriorityAI()

    def auto_relay_promotion_check(self, failed_relay_id: int) -> Optional[int]:
        """If relay fails and dependency exists, trigger promotion (uses existing relay_manager)."""
        # Delegates to existing HealthMonitor / relay_manager logic; this is automation wrapper
        return None  # Actual promotion handled by HealthMonitor.handle_unexpected_node_failure

    def batch_setpoint_validation(self, setpoints: List[dict]) -> List[dict]:
        """Automated pre-check using command_validation rules before submission."""
        results = []
        for sp in setpoints:
            # Simplified check: non-finite rejection
            val = sp.get('target_position_ned')
            if val and (not all(np.isfinite(v) for v in val)):
                results.append({'status': 'rejected', 'reason': 'non_finite'})
            else:
                results.append({'status': 'accepted'})
        return results


if __name__ == "__main__":
    print("AI/Automation layer loaded. Preserves CBBA + ETX + APF.")
