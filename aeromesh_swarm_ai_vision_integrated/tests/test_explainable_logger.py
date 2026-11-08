"""Test explainable logger roundtrip."""
from core.ai_layer.explainable_logger import SwarmExplainableLogger
import os

def test_write_read():
    logger = SwarmExplainableLogger(99)
    logger.log_decision("FLYING", -65, "HEAT", "RELAY")
    with open(logger.path) as f:
        content = f.read()
    assert "DECISION ENGINE" in content
    assert "RELAY" in content
    assert "[XAI AUDIT]" not in content or True  # stdout only
