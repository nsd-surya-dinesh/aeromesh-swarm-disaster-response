"""Kill switch — gates the vision pipeline and signals hard stop.

No RPi.GPIO dependency. Logs the pin number for hardware integrators;
driving a physical pin is left to the board-specific adapter layer.
"""
import time
import logging
from typing import Optional, Callable, List

logger = logging.getLogger(__name__)


class KillSwitch:
    """Hardware-safe kill switch for the vision + flight pipeline.

    - trigger() sets the flag, logs the reason, and calls all bound callbacks.
    - is_triggered() returns whether the switch is active.
    - SensorBridge checks this every tick and suppresses output while triggered.
    """

    def __init__(self, pin: Optional[int] = None):
        self.triggered = False
        self.pin = pin
        self._time_triggered = 0.0
        self._reason = ""
        self._callbacks: List[Callable[[], None]] = []

    def trigger(self, reason: str = "manual") -> None:
        """Activate the kill switch. All bound callbacks fire immediately."""
        self.triggered = True
        self._time_triggered = time.time()
        self._reason = reason
        logger.warning("KILL SWITCH TRIGGERED: %s (pin=%s)", reason, self.pin)
        for cb in self._callbacks:
            try:
                cb()
            except Exception as exc:
                logger.error("Kill-switch callback failed: %s", exc)

    def is_triggered(self) -> bool:
        return self.triggered

    def reset(self) -> None:
        """Clear the kill switch. Does NOT restart the pipeline automatically."""
        self.triggered = False
        self._time_triggered = 0.0
        self._reason = ""
        logger.info("Kill switch reset (pin=%s)", self.pin)

    def get_time_since_trigger(self) -> float:
        return time.time() - self._time_triggered if self.triggered else 0.0

    @property
    def reason(self) -> str:
        return self._reason

    def bind(self, callback: Callable[[], None]) -> None:
        """Register a callback that fires on trigger()."""
        self._callbacks.append(callback)

    def bind_vision(self, vision_pipeline) -> None:
        """Convenience: bind to a vision pipeline object.

        If the pipeline has a `stop` or `clear` method, it's called on trigger.
        """
        for method_name in ("stop", "clear", "release"):
            method = getattr(vision_pipeline, method_name, None)
            if callable(method):
                self._callbacks.append(method)
                logger.info("Kill switch bound to %s.%s()", type(vision_pipeline).__name__, method_name)
                return
        logger.warning("Kill switch: %s has no stop/clear/release method", type(vision_pipeline).__name__)
