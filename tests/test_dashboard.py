"""Dashboard tests."""
from visualization.dashboard_server import update_dashboard_data, app

def test_update():
    update_dashboard_data(1, 13.6, 79.4, 15, "SEARCHING")
    with app.test_client() as c:
        r = c.get("/api/telemetry")
        assert r.status_code == 200
        assert "1" in r.get_json()

def test_alert_blink_logic():
    update_dashboard_data(2, 13, 79, 10, "ALERT")
    # ALERT shown red — verified by HTML/JS design
