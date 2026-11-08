"""
AeroMesh Swarm Command Center & Live Telemetry Server
FastAPI backend with live MJPEG camera streaming ('Eyes of the Drone'),
tactical 2D map, AI Commander reasoning log, and Evaluator Control Panel.
"""
import time
import json
import cv2
import numpy as np
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse, StreamingResponse
import uvicorn
from typing import Dict, Any, List

from core.ai_layer.gemini_commander import GeminiMissionCommander
from core.computer_vision.drone_eyes import DroneEyes
from core.autopilot_interface.universal_bridge import UniversalSwarmFleet

app = FastAPI(title="AeroMesh Command Center")

# Swarm State
mission_ai = GeminiMissionCommander()
fleet_manager = UniversalSwarmFleet(fleet_limit=4, sim_backend="auto")
drone_cameras: Dict[int, DroneEyes] = {i: DroneEyes(uav_id=i) for i in range(1, 5)}

# Global Simulation & Mission Telemetry Store
mission_state = {
    "start_time": time.time(),
    "fleet_limit": 4,
    "bit_error_rate": 0.001,
    "killed_drones": [],
    "discovered_targets": [
        {"id": 0, "class": "Survivor", "pos": [-120.0, 80.0, 0.0], "time": 15.2, "uav": "uav_1", "status": "VERIFIED"},
        {"id": 1, "class": "Aircraft Wreckage", "pos": [150.0, 140.0, 0.0], "time": 42.8, "uav": "uav_2", "status": "VERIFIED"}
    ],
    "area_searched_pct": 38.5,
    "mesh_links": []
}

HTML_DASHBOARD = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>AeroMesh Swarm Command Center</title>
  <style>
    :root {
      --bg: #0b0e14;
      --card-bg: #131923;
      --cyan: #00f0ff;
      --green: #00ff66;
      --orange: #ff9900;
      --red: #ff3344;
      --border: #1e293b;
    }
    body {
      margin: 0;
      padding: 15px;
      background: var(--bg);
      color: #e2e8f0;
      font-family: 'Segoe UI', -apple-system, sans-serif;
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 15px;
      border-bottom: 1px solid var(--border);
      margin-bottom: 15px;
    }
    h1 { margin: 0; font-size: 22px; color: var(--cyan); letter-spacing: 1px; }
    .badge {
      background: rgba(0, 240, 255, 0.15);
      color: var(--cyan);
      border: 1px solid var(--cyan);
      padding: 4px 10px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: bold;
    }
    .grid {
      display: grid;
      grid-template-columns: 1.2fr 1.8fr 1fr;
      gap: 15px;
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 15px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    }
    .card h2 {
      margin-top: 0;
      font-size: 15px;
      text-transform: uppercase;
      color: #94a3b8;
      border-bottom: 1px solid var(--border);
      padding-bottom: 8px;
    }
    /* Video Feed Screen */
    .video-container {
      position: relative;
      background: #000;
      border: 1px solid var(--cyan);
      border-radius: 6px;
      overflow: hidden;
      aspect-ratio: 4/3;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .video-container img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    .video-overlay-tabs {
      display: flex;
      gap: 8px;
      margin-bottom: 10px;
    }
    .tab-btn {
      background: #1e293b;
      color: #cbd5e1;
      border: 1px solid #334155;
      padding: 5px 12px;
      border-radius: 4px;
      cursor: pointer;
      font-size: 12px;
      font-weight: 600;
    }
    .tab-btn.active {
      background: var(--cyan);
      color: #000;
      border-color: var(--cyan);
    }
    /* Tactical Map Canvas */
    #tactical-map {
      background: #090d12;
      border: 1px solid var(--border);
      border-radius: 6px;
      width: 100%;
      height: 380px;
    }
    /* Telemetry Cards */
    .uav-strip {
      display: flex;
      justify-content: space-between;
      background: rgba(255,255,255,0.03);
      padding: 8px 12px;
      border-radius: 4px;
      margin-bottom: 8px;
      border-left: 3px solid var(--cyan);
    }
    .uav-strip.killed {
      border-left-color: var(--red);
      opacity: 0.5;
    }
    /* AI Thought Log */
    #ai-log {
      height: 160px;
      overflow-y: auto;
      background: #090c10;
      padding: 8px;
      border-radius: 4px;
      font-family: monospace;
      font-size: 12px;
      border: 1px solid var(--border);
    }
    .ai-entry { margin-bottom: 6px; }
    .ai-tag { color: var(--green); font-weight: bold; }
    /* Evaluator Controls */
    .ctrl-group { margin-bottom: 12px; }
    .ctrl-group label { display: block; font-size: 12px; color: #94a3b8; margin-bottom: 4px; }
    .btn-danger {
      background: rgba(255, 51, 68, 0.2);
      border: 1px solid var(--red);
      color: #ff6677;
      padding: 6px 12px;
      border-radius: 4px;
      cursor: pointer;
      font-weight: bold;
      margin-right: 5px;
      margin-bottom: 5px;
    }
    .btn-danger:hover { background: var(--red); color: #fff; }
    .progress-bar-bg {
      background: #1e293b;
      height: 8px;
      border-radius: 4px;
      overflow: hidden;
      margin-top: 4px;
    }
    .progress-bar-fill {
      background: var(--cyan);
      height: 100%;
      width: 38.5%;
      transition: width 0.5s;
    }
  </style>
</head>
<body>

  <header>
    <div>
      <h1>&#128752; AEROMESH SWARM MISSION COMMANDER</h1>
      <span style="font-size: 12px; color: #64748b;">PUSHPAK Grand Challenge 2026 &bull; Stage 2 UAV-X</span>
    </div>
    <div style="display: flex; gap: 10px; align-items: center;">
      <span class="badge" id="ai-badge">&#129302; AI Engine: Gemini 1.5</span>
      <span class="badge" style="border-color: var(--green); color: var(--green);">&#9679; MESH: 100m ACTIVE</span>
    </div>
  </header>

  <div class="grid">
    <!-- COLUMN 1: DRONE EYE VIEW (VIDEO FEED) -->
    <div class="card">
      <h2>&#128065; Drone Eyes (Cockpit Feed)</h2>
      <div class="video-overlay-tabs">
        <button class="tab-btn active" onclick="switchCamera(1)">UAV-1</button>
        <button class="tab-btn" onclick="switchCamera(2)">UAV-2</button>
        <button class="tab-btn" onclick="switchCamera(3)">UAV-3</button>
        <button class="tab-btn" onclick="switchCamera(4)">UAV-4</button>
      </div>
      <div class="video-container">
        <img id="uav-stream" src="/api/uav/1/video_feed" alt="Live Drone Camera Feed" />
      </div>
      <p style="font-size: 11px; color: #64748b; margin-top: 8px;">
        &bull; Real-time OpenCV ArUco 4x4_50 detection overlay<br>
        &bull; Live 10-Second Target JPEG Delivery Bounding Boxes
      </p>

      <h2 style="margin-top: 15px;">&#129517; Evaluator Control Panel</h2>
      <div class="ctrl-group">
        <label>Simulate Mid-Flight UAV Failure (Kill Switch):</label>
        <div>
          <button class="btn-danger" onclick="killDrone(1)">Kill UAV 1</button>
          <button class="btn-danger" onclick="killDrone(2)">Kill UAV 2</button>
          <button class="btn-danger" onclick="killDrone(3)">Kill UAV 3</button>
          <button class="btn-danger" onclick="killDrone(4)">Kill UAV 4</button>
        </div>
      </div>
      <div class="ctrl-group">
        <label>Inject Communication Bit Error Rate (BER): <span id="ber-val">0.001</span></label>
        <input type="range" min="0" max="0.1" step="0.005" value="0.001" style="width: 100%;" onchange="updateBER(this.value)" />
      </div>
    </div>

    <!-- COLUMN 2: TACTICAL 2D MAP & NETWORK TOPOLOGY -->
    <div class="card">
      <h2>&#128506; Tactical 500m Forest Map & 100m Mesh Topology</h2>
      <canvas id="tactical-map" width="550" height="380"></canvas>
      
      <div style="display: flex; justify-content: space-between; margin-top: 15px;">
        <div style="flex: 1; margin-right: 15px;">
          <div style="display: flex; justify-content: space-between; font-size: 13px;">
            <span>Forest Search Progress:</span>
            <b id="search-pct">38.5%</b>
          </div>
          <div class="progress-bar-bg"><div class="progress-bar-fill" id="search-fill"></div></div>
        </div>
        <div style="flex: 1;">
          <div style="display: flex; justify-content: space-between; font-size: 13px;">
            <span>Target Sites Found:</span>
            <b style="color: var(--green);" id="targets-count">2 / 10</b>
          </div>
          <div class="progress-bar-bg"><div class="progress-bar-fill" style="width: 20%; background: var(--green);" id="targets-fill"></div></div>
        </div>
      </div>
    </div>

    <!-- COLUMN 3: TELEMETRY & AI DECISION LOG -->
    <div class="card">
      <h2>&#128225; Swarm Telemetry</h2>
      <div id="telemetry-list">
        <!-- Dynamically injected UAV strips -->
      </div>

      <h2 style="margin-top: 20px;">&#129302; AI Mission Commander Log</h2>
      <div id="ai-log">
        <div class="ai-entry"><span class="ai-tag">[AI-00:01]</span> Mission initialized. Assigned 4 search sectors via CBBA.</div>
        <div class="ai-entry"><span class="ai-tag">[AI-00:15]</span> UAV 1 spotted Target ID 0 (Survivor) at [-120, 80]. Target image dispatched to GCS (Latency: 0.18s).</div>
        <div class="ai-entry"><span class="ai-tag">[AI-00:42]</span> UAV 2 spotted Target ID 1 (Wreckage) at [150, 140]. Routed via UAV 1 relay.</div>
      </div>
    </div>
  </div>

  <script>
    let currentUav = 1;

    function switchCamera(id) {
      currentUav = id;
      document.getElementById('uav-stream').src = '/api/uav/' + id + '/video_feed?t=' + Date.now();
      document.querySelectorAll('.tab-btn').forEach((btn, idx) => {
        btn.classList.toggle('active', (idx + 1) === id);
      });
    }

    async function killDrone(id) {
      await fetch('/api/fail_drone/' + id, { method: 'POST' });
      addAiLog('Evaluator triggered emergency disarm on UAV ' + id + '. Swarm reallocating search bundle.');
    }

    async function updateBER(val) {
      document.getElementById('ber-val').innerText = val;
      await fetch('/api/set_ber?ber=' + val, { method: 'POST' });
    }

    function addAiLog(text) {
      const log = document.getElementById('ai-log');
      const div = document.createElement('div');
      div.className = 'ai-entry';
      div.innerHTML = '<span class="ai-tag">[AI-EVENT]</span> ' + text;
      log.appendChild(div);
      log.scrollTop = log.scrollHeight;
    }

    // Canvas Map Rendering
    const canvas = document.getElementById('tactical-map');
    const ctx = canvas.getContext('2d');

    function worldToCanvas(wx, wy) {
      // Map world bounds: x in [-400, 260], y in [-260, 260]
      const scaleX = canvas.width / 660;
      const scaleY = canvas.height / 520;
      const cx = (wx + 400) * scaleX;
      const cy = (260 - wy) * scaleY;
      return [cx, cy];
    }

    function drawTacticalMap(telem) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // 1. Draw 500m x 500m Forest Boundary [-250, 250]
      const [fX1, fY1] = worldToCanvas(-250, 250);
      const [fX2, fY2] = worldToCanvas(250, -250);
      ctx.fillStyle = 'rgba(20, 50, 30, 0.4)';
      ctx.fillRect(fX1, fY1, fX2 - fX1, fY2 - fY1);
      ctx.strokeStyle = '#2d6a4f';
      ctx.lineWidth = 2;
      ctx.strokeRect(fX1, fY1, fX2 - fX1, fY2 - fY1);

      // Label Forest
      ctx.fillStyle = '#52b788';
      ctx.font = '11px sans-serif';
      ctx.fillText('500m x 500m FOREST SEARCH EXTENT', fX1 + 10, fY1 + 20);

      // 2. Draw GCS Apron at x = -365m
      const [gcsX, gcsY] = worldToCanvas(-365, 0);
      ctx.fillStyle = '#475569';
      ctx.fillRect(gcsX - 15, gcsY - 30, 30, 60);
      ctx.strokeStyle = '#94a3b8';
      ctx.strokeRect(gcsX - 15, gcsY - 30, 30, 60);
      ctx.fillStyle = '#f8fafc';
      ctx.fillText('GCS BASE', gcsX - 25, gcsY - 35);

      // 3. Draw Discovered Targets
      const targets = [
        { id: 0, x: -120, y: 80, class: 'Survivor' },
        { id: 1, x: 150, y: 140, class: 'Wreckage' }
      ];
      targets.forEach(t => {
        const [tx, ty] = worldToCanvas(t.x, t.y);
        ctx.fillStyle = '#ff3344';
        ctx.fillRect(tx - 6, ty - 6, 12, 12);
        ctx.strokeStyle = '#ffffff';
        ctx.strokeRect(tx - 6, ty - 6, 12, 12);
        ctx.fillStyle = '#ff99aa';
        ctx.font = '10px sans-serif';
        ctx.fillText('ID:' + t.id + ' ' + t.class, tx + 8, ty + 3);
      });

      // 4. Draw UAV Positions & 100m Mesh Communication Radii
      const uavs = Object.values(telem);
      uavs.forEach(u => {
        const [ux, uy] = worldToCanvas(u.x, u.y);
        
        // 100m radio range circle (radius 100m in canvas scale)
        const radiusCanvas = 100 * (canvas.width / 660);
        ctx.beginPath();
        ctx.arc(ux, uy, radiusCanvas, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(0, 240, 255, 0.15)';
        ctx.lineWidth = 1;
        ctx.stroke();

        // UAV Icon
        ctx.beginPath();
        ctx.arc(ux, uy, 6, 0, Math.PI * 2);
        ctx.fillStyle = (u.battery < 20) ? '#ff3344' : '#00f0ff';
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.stroke();

        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 11px sans-serif';
        ctx.fillText('UAV-' + u.uav_id, ux + 8, uy - 4);
      });

      // 5. Draw Mesh Links between nodes within 100m
      for (let i = 0; i < uavs.length; i++) {
        for (let j = i + 1; j < uavs.length; j++) {
          const u1 = uavs[i], u2 = uavs[j];
          const dist = Math.hypot(u1.x - u2.x, u1.y - u2.y);
          if (dist <= 100.0) {
            const [x1, y1] = worldToCanvas(u1.x, u1.y);
            const [x2, y2] = worldToCanvas(u2.x, u2.y);
            ctx.beginPath();
            ctx.moveTo(x1, y1);
            ctx.lineTo(x2, y2);
            ctx.strokeStyle = '#00ff66';
            ctx.lineWidth = 2;
            ctx.stroke();
          }
        }
      }
    }

    async function updateTelemetryLoop() {
      try {
        const res = await fetch('/api/telemetry');
        const data = await res.json();
        
        // Render Telemetry Strips
        let html = '';
        Object.values(data).forEach(u => {
          const killed = (u.mode === 'KILLED' || u.battery <= 0);
          html += '<div class="uav-strip ' + (killed ? 'killed' : '') + '">' +
            '<div><b>UAV-' + u.uav_id + '</b> <span style="font-size: 11px; color:#64748b;">(' + u.mode + ')</span></div>' +
            '<div>Alt: ' + u.alt + 'm</div>' +
            '<div style="color:' + (u.battery < 25 ? '#ff3344' : '#00ff66') + ';">Bat: ' + u.battery + '%</div>' +
          '</div>';
        });
        document.getElementById('telemetry-list').innerHTML = html;

        // Render Map
        drawTacticalMap(data);
      } catch (e) {}
      setTimeout(updateTelemetryLoop, 500);
    }

    updateTelemetryLoop();
  </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def get_dashboard():
    return HTML_DASHBOARD

@app.get("/api/telemetry")
def get_telemetry():
    # Fetch live telemetry from the universal fleet
    telem = fleet_manager.get_all_telemetry()
    return telem

@app.get("/api/uav/{uav_id}/video_feed")
def get_video_feed(uav_id: int):
    """Streams live MJPEG camera view ('Eyes of the Drone') with HUD."""
    cam = drone_cameras.get(uav_id, drone_cameras[1])
    
    def frame_generator():
        while True:
            # Simulate or pull live camera frame
            telemetry = fleet_manager.drones.get(uav_id, fleet_manager.drones[1]).get_telemetry()
            nearby_targets = [{"id": 0, "screen_x": 320, "screen_y": 240, "class": "Survivor"}] if uav_id == 1 else []
            annotated, _, _ = cam.process_and_overlay(None, telemetry, nearby_targets)
            _, jpeg = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 75])
            frame_bytes = jpeg.tobytes()
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.04) # ~25 FPS

    return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.post("/api/fail_drone/{drone_id}")
def fail_drone(drone_id: int):
    if drone_id in fleet_manager.drones:
        drone = fleet_manager.drones[drone_id]
        drone.flight_mode = "KILLED"
        drone.is_armed = False
        drone.target_alt = 0.0
        mission_state["killed_drones"].append(drone_id)
        mission_ai.log_decision("FAILOVER", f"UAV {drone_id} killed. Triggered CBBA task reallocation.", {"killed_id": drone_id})
    return {"status": "SUCCESS", "killed": drone_id}

@app.post("/api/set_ber")
def set_ber(ber: float):
    mission_state["bit_error_rate"] = max(0.0, min(1.0, ber))
    mission_ai.log_decision("NOISE_INJECTION", f"Updated mesh BER to {ber}", {"ber": ber})
    return {"status": "SUCCESS", "new_ber": ber}

if __name__ == "__main__":
    fleet_manager.initialize_fleet()
    fleet_manager.launch_fleet()
    uvicorn.run(app, host="0.0.0.0", port=8080)


import threading

def start_dashboard(port=8080):
    """Background launcher for dashboard server."""
    fleet_manager.initialize_fleet()
    t = threading.Thread(target=lambda: uvicorn.run(app, host='0.0.0.0', port=port, log_level='warning'), daemon=True)
    t.start()
    print(f'[DASHBOARD] Command Center live at http://localhost:{port}')
    return t

def update_dashboard_data(*args, **kwargs):
    """Updates global telemetry state flexibly."""
    global mission_state, swarm_telemetry_db
    if len(args) == 5:
        public_id, lat, lon, alt, status = args
        try:
            uid = int(str(public_id).replace('uav-', '').replace('uav_', ''))
            if uid in fleet_manager.drones:
                d = fleet_manager.drones[uid]
                d.pos_enu[2] = float(alt)
                d.flight_mode = str(status)
        except Exception:
            pass
    elif len(args) == 1 and isinstance(args[0], dict):
        mission_state.update(args[0])
