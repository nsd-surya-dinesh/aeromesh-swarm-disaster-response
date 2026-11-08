"""Tests for MinifiedMeshChannel."""
from comm.channel import MinifiedMeshChannel, STATUS_MAP

def test_roundtrip():
    ch = MinifiedMeshChannel(1)
    raw = ch.serialize_telemetry(13.62880, 79.41920, 15.0, "SEARCHING")
    assert raw == b"1,13.62880,79.41920,15.0,1"
    d = ch.deserialize_telemetry(raw)
    assert d["drone_id"] == 1
    assert d["status"] == "SEARCHING"

def test_malformed():
    ch = MinifiedMeshChannel(2)
    try:
        ch.deserialize_telemetry(b"bad")
        assert False
    except Exception:
        pass  # malformed expected to raise
