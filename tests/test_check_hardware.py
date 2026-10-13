"""Mock tests for check_hardware parsing."""
from tools.check_hardware import HardwareChecker

def test_serial_check():
    c = HardwareChecker()
    c.check_serial()
    assert isinstance(c.results.get("/dev/ttyTHS1"), bool)

def test_mesh_parse():
    c = HardwareChecker()
    c.check_mesh0()
    assert "mesh0_ip" in c.results

def test_health_flags():
    c = HardwareChecker()
    c.print_health_flags()
    assert c.results["health"]["is_global_position_ok"] is True
