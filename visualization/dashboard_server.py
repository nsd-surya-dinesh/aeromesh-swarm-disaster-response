"""
Interactive Web Dashboard Server using FastAPI and WebSockets
Provides real-time browser-based monitoring and dynamic event injection.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import asyncio
import json
from typing import List, Dict
from core.models import Vector3D
from simulation.simulator import MissionSimulator


class DashboardServer:
    """Web-based interactive dashboard server"""

    def __init__(self, simulator: MissionSimulator, host: str = "127.0.0.1", port: int = 8000):
        self.simulator = simulator
        self.host = host
        self.port = port
        self.app = FastAPI(title="AeroMesh-Swarm Dashboard")
        self.active_connections: List[WebSocket] = []

        self._setup_routes()

    def _setup_routes(self):
        """Sets up HTTP and WebSocket routes"""

        @self.app.get("/")
        async def get_dashboard():
            return HTMLResponse(content=self._get_html_content())

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.active_connections.append(websocket)
            try:
                while True:
                    data = await websocket.receive_text()
                    await self._handle_client_message(data)
            except WebSocketDisconnect:
                self.active_connections.remove(websocket)

        @self.app.post("/api/inject_event")
        async def inject_event(event_type: str, x: float = 0, y: float = 0, priority: float = 5.0):
            if event_type == "poi":
                self.simulator.event_manager.inject_high_priority_poi(Vector3D(x, y, 0), priority)
            elif event_type == "hazard":
                self.simulator.event_manager.inject_secondary_hazard(Vector3D(x, y, 0))
            return {"status": "success", "event": event_type}

    async def _handle_client_message(self, message_str: str):
        """Handles incoming commands from dashboard client"""
        try:
            data = json.loads(message_str)
            cmd = data.get('command')
            if cmd == 'pause':
                # Toggle pause
                pass
            elif cmd == 'inject_poi':
                x = data.get('x', 0)
                y = data.get('y', 0)
                priority = data.get('priority', 5.0)
                self.simulator.event_manager.inject_high_priority_poi(Vector3D(x, y, 0), priority)
        except Exception as e:
            print(f"Error handling client message: {e}")

    async def broadcast_state(self):
        """Broadcasts current mission state to all connected clients"""
        if not self.active_connections:
            return

        state_data = {
            'time': self.simulator.mission_state.time,
            'coverage': self.simulator.mission_state.calculate_coverage(),
            'uavs': [
                {
                    'id': u.id,
                    'x': u.position.x,
                    'y': u.position.y,
                    'z': u.position.z,
                    'battery': u.battery_level,
                    'role': u.role.value,
                    'state': u.state.value
                } for u in self.simulator.mission_state.uavs.values()
            ],
            'pois': [
                {
                    'id': p.id,
                    'x': p.position.x,
                    'y': p.position.y,
                    'priority': p.priority,
                    'surveyed': p.surveyed
                } for p in self.simulator.mission_state.pois.values()
            ]
        }

        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(state_data))
            except Exception:
                pass

    def _get_html_content(self) -> str:
        """Returns embedded HTML/JS single-page dashboard"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>AeroMesh-Swarm Mission Control</title>
    <style>
        body { margin: 0; font-family: monospace; background: #0b0f19; color: #e2e8f0; }
        #container { display: flex; height: 100vh; }
        #canvas-container { flex: 1; position: relative; }
        #sidebar { width: 350px; background: #131b2e; padding: 20px; border-left: 1px solid #1e293b; overflow-y: auto; }
        canvas { width: 100%; height: 100%; }
        .card { background: #1a233a; padding: 15px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #2d3748; }
        .btn { background: #3b82f6; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; }
        .btn-danger { background: #ef4444; }
        .gauge { display: inline-block; width: 100%; height: 10px; background: #374151; border-radius: 5px; }
        .gauge-fill { height: 100%; background: #10b981; border-radius: 5px; }
    </style>
</head>
<body>
    <div id="container">
        <div id="canvas-container">
            <canvas id="missionCanvas"></canvas>
        </div>
        <div id="sidebar">
            <h2>AeroMesh-Swarm Control</h2>
            <div class="card">
                <h3>Mission Status</h3>
                <p>Time: <span id="missionTime">0.0s</span></p>
                <p>Coverage: <span id="coverage">0.0%</span></p>
                <div class="gauge"><div id="coverageBar" class="gauge-fill" style="width: 0%;"></div></div>
            </div>
            <div class="card">
                <h3>Dynamic Event Injection</h3>
                <button class="btn" onclick="injectRandomPoI()">+ Add Emergency PoI</button>
                <button class="btn btn-danger" onclick="triggerRelayFailure()">Trigger Relay Fault</button>
            </div>
        </div>
    </div>

    <script>
        const canvas = document.getElementById('missionCanvas');
        const ctx = canvas.getContext('2d');
        let ws;

        function init() {
            resizeCanvas();
            window.addEventListener('resize', resizeCanvas);
            connectWebSocket();
        }

        function resizeCanvas() {
            canvas.width = canvas.parentElement.clientWidth;
            canvas.height = canvas.parentElement.clientHeight;
        }

        function connectWebSocket() {
            ws = new WebSocket(`ws://${location.host}/ws`);
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                updateUI(data);
                render(data);
            };
        }

        function updateUI(data) {
            document.getElementById('missionTime').innerText = data.time.toFixed(1) + 's';
            document.getElementById('coverage').innerText = data.coverage.toFixed(1) + '%';
            document.getElementById('coverageBar').style.width = data.coverage + '%';
        }

        function render(data) {
            ctx.fillStyle = '#0b0f19';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            const scale = 0.3;
            const cx = canvas.width / 2;
            const cy = canvas.height / 2;

            // Draw PoIs
            data.pois.forEach(poi => {
                const px = cx + poi.x * scale;
                const py = cy - poi.y * scale;
                ctx.beginPath();
                ctx.arc(px, py, 10, 0, 2 * Math.PI);
                ctx.fillStyle = poi.surveyed ? '#10b981' : '#ef4444';
                ctx.fill();
            });

            // Draw UAVs
            data.uavs.forEach(uav => {
                const ux = cx + uav.x * scale;
                const uy = cy - uav.y * scale;
                ctx.fillStyle = uav.role === 'relay' ? '#f59e0b' : '#3b82f6';
                ctx.fillRect(ux - 6, uy - 6, 12, 12);
            });
        }

        function injectRandomPoI() {
            const x = (Math.random() - 0.5) * 1600;
            const y = (Math.random() - 0.5) * 1600;
            fetch(`/api/inject_event?event_type=poi&x=${x}&y=${y}&priority=6.0`, {method: 'POST'});
        }

        window.onload = init;
    </script>
</body>
</html>
        """

    def run_server(self):
        """Starts the dashboard server"""
        print(f"🌐 Starting web dashboard at http://{self.host}:{self.port}")
        uvicorn.run(self.app, host=self.host, port=self.port, log_level="warning")
