"""Mock tests for HybridAutopilotAdapter."""
import pytest
import asyncio
from core.autopilot_interface.hybrid_adapter import HybridAutopilotAdapter

class MockHealth:
    is_global_position_ok = True
    is_home_position_ok = True

def test_hybrid_connect():
    a = HybridAutopilotAdapter()
    url = a.connect_interface()
    assert url.startswith("serial://") or url.startswith("udp://")

def test_ekf_ready():
    a = HybridAutopilotAdapter()
    a.connect_interface()
    # Sync wrapper for async method
    import asyncio
    result = asyncio.run(a.wait_for_ekf_convergence(timeout=120))
    assert result is True

def test_telemetry_stream():
    a = HybridAutopilotAdapter()
    a.connect_interface()
    import asyncio
    async def collect():
        vals = []
        async for v in a.telemetry_stream():
            vals.append(v)
            break
        return vals
    vals = asyncio.run(collect())
    assert len(vals) == 1
    assert vals[0]["battery"] == 1.0
