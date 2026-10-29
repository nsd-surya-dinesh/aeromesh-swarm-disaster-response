"""UAV Brain — Operator-Guarded AI Controller.
Requires operator permission (`operator_approve`) before ANY autonomous action.
Provides virtual flight memory + feature-checking + chat interface.
Never arms without approval; never claims flight without evidence.
"""
import time, json, os
from typing import Dict, Optional, List
from core.models import UAV, MissionState, UAVState, UAVRole
from core.config import config


class FlightMemory:
    """Virtual memory for every flight: events, decisions, telemetry log."""
    def __init__(self, flight_id: str):
        self.flight_id = flight_id
        self.events: List[Dict] = []
        self.decisions: List[str] = []
        self.start_time = time.monotonic()

    def log(self, event_type: str, description: str, **meta):
        self.events.append({
            "ts": time.monotonic() - self.start_time,
            "type": event_type,
            "desc": description,
            **meta
        })

    def record_decision(self, decision_text: str):
        self.decisions.append({"ts": time.monotonic() - self.start_time, "decision": decision_text})

    def save(self, path="brain_memory.json"):
        with open(path, "w") as f:
            json.dump({
                "flight_id": self.flight_id,
                "events": self.events,
                "decisions": self.decisions,
                "duration_s": time.monotonic() - self.start_time
            }, f, indent=2)


class UAVBrain:
    """The AI brain controlling UAV — always asks user/operator until approved."""
    def __init__(self, flight_id: str = "flight-001"):
        self.memory = FlightMemory(flight_id)
        self.approved = False  # Operator must grant permission
        self.operator_chat_log: List[str] = []
        self.feature_checks_passed = self._check_project_features()

    # --- Operator permission gate (MANDATORY) ---
    def request_approval(self, action_description: str) -> bool:
        """Ask operator; return True ONLY if user grants automode."""
        self.memory.log("approval_request", f"Ask operator for: {action_description}")
        # In real use: prompt user / webhook / panel button
        # Here: requires explicit approval; default False = BLOCKED
        print(f"[BRAIN REQUEST] Operator approval needed: {action_description}")
        # User must set approved = True via /operator-approve endpoint or call
        return self.approved

    def approve(self, operator_id: str = "operator"):
        """Call after operator confirms."""
        self.approved = True
        self.memory.log("operator_approved", f"Operator {operator_id} granted automode", approved=True)
        print(f"[BRAIN] Operator {operator_id} approved automode. AI control enabled.")

    def deny(self, reason: str = "user denied"):
        """Block action; stay in manual/hold."""
        self.approved = False
        self.memory.log("operator_denied", reason)
        print(f"[BRAIN BLOCKED] {reason}. No autonomous action.")

    # --- Feature-checking: verify all project features present ---
    def _check_project_features(self) -> Dict:
        checks = {
            "simulator": os.path.exists("simulation/simulator.py"),
            "physics": os.path.exists("core/physics.py"),
            "mesh_router": os.path.exists("comm/mesh_router.py"),
            "cbba": os.path.exists("swarm/task_allocation.py"),
            "vision": os.path.exists("core/computer_vision/uav_detect.py"),
            "dashboard": os.path.exists("visualization/dashboard_server.py"),
            "autopilot_adapter": os.path.exists("core/autopilot_interface/adapter.py"),
            "command_validation": os.path.exists("core/autopilot_interface/command_validation.py"),
            "test_mission": os.path.exists("test/mission.py"),
        }
        all_ok = all(checks.values())
        self.memory.log("feature_check", f"Features OK: {sum(checks.values())}/{len(checks)}", checks=checks)
        return checks

    # --- Chat interface (AI talks to operator / to UAV) ---
    def chat(self, user_input: str) -> str:
        self.operator_chat_log.append(user_input)
        # Interpret request; check approval
        if "arm" in user_input.lower() or "takeoff" in user_input.lower() or "fly" in user_input.lower():
            if not self.approved:
                return "BRAIN: Action requires operator approval. Use /approve to grant automode. No arm/command sent."
            else:
                self.memory.record_decision(f"AI approved action: {user_input}")
                return f"BRAIN: Approved automode active. Executing: {user_input}. Memory log updated."
        # Status query
        if "status" in user_input.lower() or "what" in user_input.lower():
            return f"BRAIN: UAV status — approved={self.approved}, memory_events={len(self.memory.events)}, features_ok={all(self.feature_checks_passed.values())}. Chat log length={len(self.operator_chat_log)}."
        # Memory review
        if "memory" in user_input.lower() or "log" in user_input.lower():
            return f"BRAIN: Flight memory has {len(self.memory.events)} events. Call save() to persist to brain_memory.json."
        # Default
        self.memory.record_decision(f"Chat: {user_input}")
        return f"BRAIN: Received '{user_input}'. Awaiting approval or clarification."

    # --- Autonomous decision engine (only when approved) ---
    def decide_action(self, mission_state) -> str:
        """AI decides next action based on mission state — NEVER executes without approval."""
        if not self.approved:
            return "HOLD: Operator approval required before any autonomous decision."

        # Check all features before acting (R3: don't work if missing)
        if not all(self.feature_checks_passed.values()):
            missing = [k for k, v in self.feature_checks_passed.items() if not v]
            return f"BLOCKED: Missing features {missing}. Cannot act."

        # Read UAV status from mission
        uavs = list(mission_state.uavs.values())
        if not uavs:
            return "HOLD: No UAVs in mission state."

        # Simple decision rule: if any UAV battery < RTB, command return
        for uav in uavs:
            if uav.battery_level < config.uav.rtb_threshold_ratio:
                return f"DECISION: UAV-{uav.id} battery low ({uav.battery_level*100:.0f}%). Command RTB (approved={self.approved})."

        return f"DECISION: All systems OK. {len(uavs)} UAVs operational. Waiting for next command (approved={self.approved})."


# Global instance (use with care; always requires approval)
brain = UAVBrain("aeromesh-flight-001")
