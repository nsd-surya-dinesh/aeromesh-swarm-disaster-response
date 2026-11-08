"""
DroneEyes: Real-time Computer Vision & Cockpit HUD Overlay Engine.
Provides 'Eyes of the Drone' video feeds, ArUco 4x4_50 target detection,
10-second JPEG thumbnail generation, and live streaming to web browser.
"""
import time
import math
import cv2
import numpy as np
from typing import Optional, Tuple, Dict, Any, List

class DroneEyes:
    def __init__(self, uav_id: int):
        self.uav_id = uav_id
        self.width = 640
        self.height = 480
        
        # ArUco 4x4_50 dictionary (Official PUSHPAK specification)
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        self.aruco_params = cv2.aruco.DetectorParameters()
        
        self.last_frame: Optional[np.ndarray] = None
        self.last_annotated: Optional[np.ndarray] = None
        self.detections: List[Dict[str, Any]] = []

    def generate_synthetic_frame(self, telemetry: Dict[str, Any], nearby_targets: List[Dict[str, Any]]) -> np.ndarray:
        """
        Synthesizes a realistic nadir down-facing camera view over the forest
        when running in standalone simulation mode.
        """
        # Ground texture (forest green base)
        frame = np.full((self.height, self.width, 3), (35, 65, 30), dtype=np.uint8)
        
        # Scatter ground variations (bushes and trees)
        np.random.seed(int(self.uav_id * 100))
        for _ in range(25):
            tx = int(np.random.randint(20, self.width - 20))
            ty = int(np.random.randint(20, self.height - 20))
            tr = int(np.random.randint(15, 35))
            cv2.circle(frame, (tx, ty), tr, (20, 50, 18), -1)

        # Draw any ground target in current camera field of view
        for t in nearby_targets:
            px, py = t.get("screen_x", 320), t.get("screen_y", 240)
            tid = t.get("id", 0)
            tclass = t.get("class", "survivor")
            
            # Draw 3m x 3m ground plate (white rectangle)
            cv2.rectangle(frame, (px-40, py-40), (px+40, py+40), (240, 240, 240), -1)
            cv2.rectangle(frame, (px-40, py-40), (px+40, py+40), (20, 20, 20), 2)
            
            # Draw mock ArUco black-and-white grid pattern
            cv2.rectangle(frame, (px-25, py-25), (px+25, py+25), (0, 0, 0), -1)
            cv2.rectangle(frame, (px-15, py-15), (px+15, py+15), (255, 255, 255), -1)
            cv2.putText(frame, f"ID:{tid}", (px-20, py+5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

        return frame

    def process_and_overlay(self, raw_frame: Optional[np.ndarray], telemetry: Dict[str, Any], targets: List[Dict[str, Any]]) -> Tuple[np.ndarray, List[Dict[str, Any]], Optional[bytes]]:
        """
        Detects ArUco markers, overlays tactical HUD, and crops 10-second JPEG thumbnail.
        """
        if raw_frame is None:
            raw_frame = self.generate_synthetic_frame(telemetry, targets)
            
        annotated = raw_frame.copy()
        corners, ids = None, None
        try:
            if hasattr(cv2.aruco, 'ArucoDetector'):
                detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)
                corners, ids, _ = detector.detectMarkers(raw_frame)
            elif hasattr(cv2.aruco, 'detectMarkers'):
                corners, ids, _ = cv2.aruco.detectMarkers(raw_frame, self.aruco_dict, parameters=self.aruco_params)
        except Exception:
            pass
        
        target_crop_jpeg = None
        current_dets = []
        
        # 1. Process Detected ArUco Targets
        if ids is not None:
            cv2.aruco.drawDetectedMarkers(annotated, corners, ids)
            for i, marker_id in enumerate(ids.flatten()):
                c = corners[i][0]
                cx = int(c[:, 0].mean())
                cy = int(c[:, 1].mean())
                
                # Bounding box & target label
                cv2.circle(annotated, (cx, cy), 8, (0, 0, 255), -1)
                cv2.putText(annotated, f"TARGET ROI #{marker_id}", (cx - 60, cy - 45),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                
                # Crop 200x200 JPEG for 10-second GCS delivery rule
                x1, y1 = max(0, cx - 100), max(0, cy - 100)
                x2, y2 = min(self.width, cx + 100), min(self.height, cy + 100)
                crop_img = raw_frame[y1:y2, x1:x2]
                if crop_img.size > 0:
                    _, buf = cv2.imencode('.jpg', crop_img, [cv2.IMWRITE_JPEG_QUALITY, 75])
                    target_crop_jpeg = buf.tobytes()
                    
                det_info = {
                    "marker_id": int(marker_id),
                    "center": (cx, cy),
                    "timestamp": time.time(),
                    "uav_id": self.uav_id,
                    "payload_size_kb": len(target_crop_jpeg) / 1024.0 if target_crop_jpeg else 0.0
                }
                current_dets.append(det_info)
                self.detections.append(det_info)

        # 2. Draw Cockpit HUD (Artificial Horizon, Altitude, Speed, Compass)
        self._draw_hud(annotated, telemetry)
        
        self.last_frame = raw_frame
        self.last_annotated = annotated
        return annotated, current_dets, target_crop_jpeg

    def _draw_hud(self, img: np.ndarray, telem: Dict[str, Any]):
        """Renders military-grade tactical HUD overlay."""
        h, w = img.shape[:2]
        cx, cy = w // 2, h // 2
        
        # Primary HUD Color: Electric Cyan / Green
        hud_color = (0, 255, 200)
        
        # Reticle Crosshair
        cv2.line(img, (cx - 20, cy), (cx + 20, cy), hud_color, 1)
        cv2.line(img, (cx, cy - 20), (cx, cy + 20), hud_color, 1)
        cv2.circle(img, (cx, cy), 35, hud_color, 1)
        
        # Top Header Box
        cv2.rectangle(img, (0, 0), (w, 35), (10, 15, 12), -1)
        cv2.line(img, (0, 35), (w, 35), hud_color, 1)
        
        uav_label = f"UAV-0{self.uav_id} EYE-CAM" if self.uav_id > 0 else "GCS OVERVIEW"
        heading = int(telem.get("heading", 88))
        cv2.putText(img, f"[{uav_label}]  HDG: {heading:03d} DEG  CAM: NADIR -90", 
                    (15, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        
        # Left Telemetry Sidebar (Speed & Coordinates)
        alt = telem.get("alt", 15.0)
        speed = telem.get("speed", 10.0)
        climb = telem.get("climb", 0.0)
        bat = telem.get("battery", 100.0)
        mode = telem.get("mode", "GUIDED")
        
        cv2.rectangle(img, (10, 50), (190, 160), (15, 20, 18), -1)
        cv2.rectangle(img, (10, 50), (190, 160), hud_color, 1)
        cv2.putText(img, f"MODE:   {mode}", (18, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.45, hud_color, 1)
        cv2.putText(img, f"ALT:    {alt:6.1f} m", (18, 92), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
        cv2.putText(img, f"SPEED:  {speed:6.1f} m/s", (18, 112), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        cv2.putText(img, f"CLIMB:  {climb:+6.1f} m/s", (18, 132), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        cv2.putText(img, f"BATT:   {bat:5.1f} %", (18, 152), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 255) if bat > 25 else (0, 0, 255), 1)

        # Right Mesh Network Status Box
        hops = telem.get("hops_to_gcs", 1)
        latency_ms = telem.get("latency_ms", 45)
        cv2.rectangle(img, (w - 210, 50), (w - 10, 120), (15, 20, 18), -1)
        cv2.rectangle(img, (w - 210, 50), (w - 10, 120), hud_color, 1)
        cv2.putText(img, f"MESH: ACTIVE", (w - 200, 72), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)
        cv2.putText(img, f"GCS HOPS: {hops}", (w - 200, 92), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
        cv2.putText(img, f"LATENCY:  {latency_ms} ms", (w - 200, 112), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 200), 1)

    def get_jpeg_stream(self) -> bytes:
        """Returns compressed JPEG bytes for live browser streaming."""
        if self.last_annotated is None:
            blank = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            cv2.putText(blank, f"UAV-{self.uav_id} EYE CAM CONNECTING...", (120, 240), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 200), 2)
            _, buf = cv2.imencode('.jpg', blank)
            return buf.tobytes()
            
        _, buf = cv2.imencode('.jpg', self.last_annotated, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return buf.tobytes()
