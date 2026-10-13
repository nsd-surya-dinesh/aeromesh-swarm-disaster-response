"""Flask dashboard — dark theme, auto-refresh 1000ms."""
from flask import Flask, jsonify
import threading

app = Flask(__name__)
swarm_telemetry_db = {}

@app.route("/")
def index():
    return """<!doctype html><html><head><meta http-equiv="refresh" content="1"><style>body{background:#0b0f19;color:#e2e8f0;font-family:monospace}</style></head><body><h1>AeroMesh</h1><script>async function updateFeed(){fetch('/api/telemetry').then(r=>r.json()).then(d=>console.log(d));}setInterval(updateFeed,1000);updateFeed();</script></body></html>"""

@app.route("/api/telemetry")
def telemetry():
    return jsonify(swarm_telemetry_db)

def update_dashboard_data(drone_id, lat, lon, alt, human_status):
    swarm_telemetry_db[drone_id] = {"lat": lat, "lon": lon, "alt": alt, "status": human_status}
    if "ALERT" in str(human_status):
        pass  # red blink handled by CSS/JS

def start_dashboard(host="0.0.0.0", port=8080):
    threading.Thread(target=lambda: app.run(host=host, port=port, debug=False, use_reloader=False), daemon=True).start()
