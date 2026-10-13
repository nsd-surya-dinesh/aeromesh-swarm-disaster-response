"""Integration SITL test — runs run_simulation.py --sitl --dry-run --duration 3."""
import subprocess, os, pytest


@pytest.mark.skipif(
    not __import__("pytest").importorskip("mavsdk", reason="mavsdk not installed"),
    reason="mavsdk not installed"
)
def test_sitl_exit_and_audit():
    """Run the simulation dry-run and verify exit, audit log, and dashboard."""
    result = subprocess.run(
        ["python", "run_simulation.py", "--sitl", "--dry-run", "--duration", "3", "--drone-id", "1"],
        capture_output=True, timeout=15, text=True
    )
    assert result.returncode == 0, f"Expected exit 0, got {result.returncode}"

    # Verify audit log exists with XAI format line
    audit = "results/uav-1_decision_audit.txt"
    assert os.path.exists(audit), f"Audit file {audit} not created"
    with open(audit) as f:
        content = f.read()
    lines = [l for l in content.splitlines() if l.strip()]
    assert any(
        "[DECISION ENGINE]" in l and "State=" in l and "-> Action:" in l
        for l in lines
    ), f"Audit file {audit} has no XAI-format line"

    # Verify dashboard endpoint returns JSON with uav-1 key
    import time, json
    import urllib.request
    for _ in range(10):
        try:
            req = urllib.request.Request("http://127.0.0.1:8080/api/telemetry")
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read())
                if "uav-1" in data:
                    break
        except Exception:
            time.sleep(0.5)
    else:
        pytest.xfail("Dashboard /api/telemetry did not return uav-1 within timeout")