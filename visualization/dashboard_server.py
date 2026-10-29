"""AeroMesh Swarm Command Center - dark-theme Flask dashboard."""
from flask import Flask, jsonify
import threading

app = Flask(__name__)
swarm_telemetry_db = {}
_db_lock = threading.Lock()

INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>AeroMesh Swarm Command Center</title>
  <style>
    body { font-family: 'Courier New', monospace; background: #0c0f12; color: #00ff66; padding: 20px; margin: 0; }
    h1 { color: #00ff66; border-bottom: 1px solid #00ff66; padding-bottom: 10px; }
    .uav-card { border: 2px solid #00ff66; padding: 15px; margin: 10px 0; background: #14191f; border-radius: 5px; }
    .uav-card h3 { margin: 0 0 8px 0; color: #00ff66; }
    .alert { color: #ff3333; font-weight: bold; }
    .muted { color: #4a5a4a; font-size: 12px; }
  </style>
</head>
<body>
  <h1>&#128752; AEROMESH MULTI-AGENT SWARM METRICS</h1>
  <div id="swarm-feed"><p class="muted">Loading telemetry...</p></div>
  <script>
    async function updateFeed() {
      try {
        const res = await fetch('/api/telemetry');
        const data = await res.json();
        let html = '';
        const ids = Object.keys(data);
        if (ids.length === 0) {
          html = '<p class="muted">No telemetry yet. Waiting for first packet...</p>';
        }
        for (const id of ids) {
          const agent = data[id];
          const alertClass = (agent.status || '').includes('ALERT') ? 'alert' : '';
          const lat = (agent.lat || 0).toFixed(5);
          const lon = (agent.lon || 0).toFixed(5);
          const alt = (agent.alt || 0).toFixed(1);
          html += '<div class="uav-card"><h3>&#129302; AGENT: ' + id.toUpperCase() + '</h3>' +
                  '<p>&#128205; <b>GPS:</b> Lat ' + lat + ', Lon ' + lon + ' | Alt ' + alt + 'm</p>' +
                  '<p class="' + alertClass + '">&#128225; <b>STATUS:</b> ' + (agent.status || 'UNKNOWN') + '</p></div>';
        }
        document.getElementById('swarm-feed').innerHTML = html;
      } catch (e) {
        document.getElementById('swarm-feed').innerHTML = '<p class="alert">Fetch error: ' + e + '</p>';
      }
    }
    updateFeed();
    setInterval(updateFeed, 1000);
  </script>
</body>
</html>
"""

@app.route('/')
def index():
    return INDEX_HTML

@app.route('/api/telemetry')
def get_telemetry():
    with _db_lock:
        return jsonify(dict(swarm_telemetry_db))

@app.route('/api/update-param', methods=['POST'])
def update_param():
    from flask import request
    try:
        data = request.get_json(force=True)
        key = data.get('key')
        value = data.get('value')
        # R6: dynamic parameter updates with validation
        if key == 'survey_altitude' and isinstance(value, (int, float)):
            from core.config import config
            if 10 <= value <= 200:
                config.uav.survey_altitude = float(value)
                return jsonify({'status':'updated','key':key,'value':value}), 200
            else:
                return jsonify({'status':'rejected','reason':'out of range [10,200]'}), 400
        elif key == 'rtb_threshold' and isinstance(value, (int, float)):
            if 0 <= value <= 1:
                from core.config import config
                config.uav.rtb_threshold_ratio = float(value)
                return jsonify({'status':'updated','key':key,'value':value}), 200
            else:
                return jsonify({'status':'rejected','reason':'fraction required [0,1]'}), 400
        return jsonify({'status':'rejected','reason':'unknown parameter'}), 400
    except Exception as e:
        return jsonify({'status':'error','reason':str(e)}), 500

def update_dashboard_data(drone_id, lat, lon, alt, human_status):
    with _db_lock:
        swarm_telemetry_db[drone_id] = {'lat': lat, 'lon': lon, 'alt': alt, 'status': human_status}

def start_dashboard(host='0.0.0.0', port=8080):
    def _run():
        app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t

class DashboardServer:
    def __init__(self, *args, **kwargs):
        raise NotImplementedError('Use start_dashboard() instead')
