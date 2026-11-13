"""
AI-Powered Smart Security Camera
Main Flask Application and Real-Time Video Streaming Server.
"""

import os
import time
import threading
from datetime import datetime
import cv2
import numpy as np
from flask import Flask, render_template, Response, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

import config
from config import CONFIG, update_config
import database
from detection.detector import ObjectDetector
from detection.tracker import CentroidTracker
from detection.activity import ActivityAnalyzer
from alerts.alert_manager import AlertManager

# Initialize Flask application
app = Flask(__name__)
app.config["SECRET_KEY"] = "smart-security-camera-cse-key"
app.config["UPLOAD_FOLDER"] = os.path.join(config.BASE_DIR, "static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 250 * 1024 * 1024  # 250 MB max upload
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(CONFIG["snapshot_dir"], exist_ok=True)

# Initialize Database
database.init_db()

# Initialize AI Modules
detector = ObjectDetector()
tracker = CentroidTracker(max_disappeared=25, max_distance=90)
activity_analyzer = ActivityAnalyzer()
alert_manager = AlertManager()


class VideoStreamManager:
    """
    Manages camera lifecycle, background capture, YOLO inference,
    object tracking, behavioral analysis, and frame encoding.
    """
    def __init__(self):
        self.cap = None
        self.is_running = False
        self.lock = threading.Lock()
        self.current_frame = None
        self.is_demo = False
        self.active_source = CONFIG.get("camera_source", 0)

        # Real-time state metrics
        self.people_count = 0
        self.object_count = 0
        self.camera_status = "OFFLINE"
        self.worker_thread = None

        # Fallback simulation counter
        self.sim_tick = 0

    def start(self, source=None):
        with self.lock:
            if self.is_running:
                self.stop_internal()

            if source is not None:
                self.active_source = source

            self.is_running = True
            self.camera_status = "ONLINE"
            self.worker_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.worker_thread.start()
            print(f"[Camera] Started camera stream on source: {self.active_source}")

    def stop(self):
        with self.lock:
            self.stop_internal()

    def stop_internal(self):
        self.is_running = False
        self.camera_status = "OFFLINE"
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception as e:
                print(f"[Camera] Error releasing cap: {e}")
            self.cap = None
        self.people_count = 0
        self.object_count = 0
        print("[Camera] Camera stopped.")

    def _open_capture(self):
        src = self.active_source

        # Check if source is an integer string or int
        if isinstance(src, str) and src.isdigit():
            src = int(src)

        print(f"[Camera] Opening VideoCapture with source: {src}")
        cap = cv2.VideoCapture(src)

        # Set resolution if live webcam
        if isinstance(src, int):
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, CONFIG["frame_width"])
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CONFIG["frame_height"])

        return cap

    def _generate_synthetic_frame(self):
        """
        Fallback generator when physical webcam is not attached.
        Renders a realistic CCTV test feed with simulated moving security target
        so the CSE project demo works 100% reliably out of the box!
        """
        w, h = CONFIG["frame_width"], CONFIG["frame_height"]
        frame = np.zeros((h, w, 3), dtype=np.uint8)

        # Draw CCTV scanline background
        frame[:] = (22, 26, 32)
        # Floor grid lines
        for y in range(int(h * 0.4), h, 30):
            cv2.line(frame, (0, y), (w, y), (35, 42, 52), 1)
        for x in range(0, w, 60):
            cv2.line(frame, (x, int(h * 0.4)), (x, h), (35, 42, 52), 1)

        # Room walls and door
        cv2.rectangle(frame, (20, 50), (160, int(h * 0.8)), (45, 55, 68), 2)
        cv2.putText(frame, "SECURE ENTRY A", (25, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 140, 180), 1)

        # Moving simulated person target
        self.sim_tick += 1
        t = self.sim_tick * 0.03
        # Moves horizontally back and forth between x=120 and x=540
        sim_x = int(320 + 200 * np.sin(t))
        sim_y = int(260 + 20 * np.cos(t * 2))

        # Draw a synthetic human figure for visual demonstration
        # Head
        cv2.circle(frame, (sim_x, sim_y - 65), 16, (180, 200, 220), -1)
        # Torso
        cv2.rectangle(frame, (sim_x - 18, sim_y - 48), (sim_x + 18, sim_y + 10), (140, 160, 180), -1)
        # Legs
        cv2.line(frame, (sim_x - 10, sim_y + 10), (sim_x - 14, sim_y + 65), (100, 120, 140), 6)
        cv2.line(frame, (sim_x + 10, sim_y + 10), (sim_x + 14, sim_y + 65), (100, 120, 140), 6)
        # Backpack / Object on back
        cv2.rectangle(frame, (sim_x + 12, sim_y - 40), (sim_x + 28, sim_y - 10), (60, 130, 200), -1)

        cv2.putText(frame, "STANDBY / SIMULATED CCTV FEED", (15, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 230, 118), 1)
        cv2.putText(frame, "[No Physical Camera Detected - Demo Pattern Active]", (15, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 180, 200), 1)

        return frame

    def _capture_loop(self):
        """Background video processing and AI pipeline loop."""
        try:
            self.cap = self._open_capture()
        except Exception as e:
            print(f"[Camera] Failed to open capture: {e}")
            self.cap = None

        while self.is_running:
            frame = None
            if self.cap is not None and self.cap.isOpened():
                ret, raw_frame = self.cap.read()
                if ret and raw_frame is not None:
                    frame = raw_frame
                else:
                    # Video file reached the end, loop it if demo video
                    if self.is_demo:
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    else:
                        # Temporary webcam read fail, wait briefly
                        time.sleep(0.05)

            # Fallback to simulated CCTV frame if webcam unavailable
            if frame is None:
                frame = self._generate_synthetic_frame()
                time.sleep(0.033)  # ~30 fps

            # Resize frame to standard dimensions
            h, w = frame.shape[:2]
            target_w, target_h = CONFIG["frame_width"], CONFIG["frame_height"]
            if (w, h) != (target_w, target_h):
                frame = cv2.resize(frame, (target_w, target_h))

            # Raw snapshot copy before annotations for clear evidence archiving
            clean_frame = frame.copy()

            # ============================================================
            # AI SURVEILLANCE PIPELINE
            # ============================================================
            # 1. YOLO Object Detection
            detections = detector.detect(frame)

            # 2. Object & Person Tracking
            tracked_objects = tracker.update(detections)

            # 3. Behavioral / Activity Analysis
            events, visual_tags = activity_analyzer.analyze(frame.shape, tracked_objects, CONFIG)

            # 4. Alerts, Snapshots & SQLite Logging
            if events:
                alert_manager.process_events(clean_frame, events, CONFIG)

            # 5. Visual HUD Overlays
            # a) Draw Restricted Area
            frame = activity_analyzer.draw_restricted_area(frame, CONFIG)

            # b) Draw YOLO Bounding Boxes
            frame = detector.draw_detections(frame, detections)

            # c) Draw Object Tracking IDs and Trajectories
            frame = tracker.draw_tracks(frame, tracked_objects)

            # d) Draw Activity Warning Badges
            frame = activity_analyzer.draw_activity_tags(frame, tracked_objects, visual_tags)

            # e) Timestamp & Watermark Overlay
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cam_label = f"{CONFIG.get('camera_name', 'Camera 1')} | {CONFIG.get('camera_location', 'Main')}"
            cv2.putText(frame, cam_label, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(frame, now_str, (target_w - 180, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

            # Update metrics
            people = [obj for obj in tracked_objects if obj.class_name == "Person" and obj.disappeared_count == 0]
            self.people_count = len(people)
            self.object_count = len(detections)

            with self.lock:
                self.current_frame = frame

        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def get_jpeg_frame(self):
        with self.lock:
            if self.current_frame is None:
                # Return placeholder frame if camera not started
                blank = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(blank, "CAMERA STANDBY - PRESS START", (120, 240),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (120, 150, 180), 2)
                ret, jpeg = cv2.imencode('.jpg', blank)
                return jpeg.tobytes() if ret else b''

            ret, jpeg = cv2.imencode('.jpg', self.current_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            return jpeg.tobytes() if ret else b''


# Instantiate global stream manager
stream_manager = VideoStreamManager()
# Automatically initialize camera stream on startup
stream_manager.start(CONFIG.get("camera_source", 0))


# ============================================================
# FLASK ROUTING & VIEW CONTROLLERS
# ============================================================

@app.route("/")
def index():
    """Render main monitoring dashboard."""
    return render_template("index.html")


@app.route("/events")
def events_page():
    """Render historical security events log page."""
    return render_template("events.html")


@app.route("/settings")
def settings_page():
    """Render system configuration page."""
    return render_template("settings.html")


def gen_stream(manager):
    """Video streaming generator function."""
    while True:
        frame_bytes = manager.get_jpeg_frame()
        if frame_bytes:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.033)  # ~30 FPS throttle


@app.route("/video-feed")
def video_feed():
    """MJPEG streaming endpoint for HTML img tag."""
    return Response(gen_stream(stream_manager),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


# ============================================================
# HARDWARE & CONTROL ENDPOINTS
# ============================================================

@app.route("/start-camera", methods=["POST"])
def start_camera_endpoint():
    """Start or restart live camera capture."""
    try:
        stream_manager.is_demo = False
        stream_manager.start(CONFIG.get("camera_source", 0))
        return jsonify({"status": "ok", "message": "Camera started"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/stop-camera", methods=["POST"])
def stop_camera_endpoint():
    """Stop live camera stream."""
    try:
        stream_manager.stop()
        return jsonify({"status": "ok", "message": "Camera stopped"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/upload-video", methods=["POST"])
def upload_video():
    """Upload a prerecorded video for Demo Mode."""
    if "video" not in request.files:
        return jsonify({"status": "error", "message": "No video file provided"}), 400

    file = request.files["video"]
    if file.filename == "":
        return jsonify({"status": "error", "message": "No selected file"}), 400

    filename = secure_filename(f"demo_{int(time.time())}_{file.filename}")
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    # Switch stream manager to use this uploaded video
    stream_manager.is_demo = True
    stream_manager.start(filepath)

    return jsonify({
        "status": "ok",
        "message": "Demo video uploaded and activated",
        "filename": filename
    })


# ============================================================
# API ENDPOINTS
# ============================================================

@app.route("/api/stats")
def api_stats():
    """Real-time stats endpoint polled by frontend."""
    active_alerts = alert_manager.get_active_alerts()
    db_stats = database.get_stats()

    return jsonify({
        "camera_status": stream_manager.camera_status,
        "is_demo": stream_manager.is_demo,
        "people_detected": stream_manager.people_count,
        "objects_detected": stream_manager.object_count,
        "active_alerts_count": len(active_alerts),
        "active_alerts": active_alerts[:6],
        "total_db_events": db_stats.get("total_events", 0),
        "high_alerts": db_stats.get("high_alerts", 0),
    })


@app.route("/api/events")
def api_events():
    """Fetch stored events from SQLite with filtering."""
    event_type = request.args.get("event_type")
    risk_level = request.args.get("risk_level")
    date = request.args.get("date")
    limit = int(request.args.get("limit", 50))

    events = database.get_events(
        event_type=event_type,
        risk_level=risk_level,
        date=date,
        limit=limit
    )
    return jsonify(events)


@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    """Get current configuration dictionary."""
    return jsonify(config.get_config())


@app.route("/settings", methods=["POST"])
def update_settings_endpoint():
    """Update runtime configuration parameters."""
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No JSON payload"}), 400

    update_config(data)

    # Update detector confidence if changed
    if "detection_confidence" in data:
        detector.conf_threshold = float(data["detection_confidence"])

    return jsonify({"status": "ok", "message": "Settings saved successfully", "config": config.get_config()})


if __name__ == "__main__":
    print("=" * 60)
    print(" AI-POWERED SMART SECURITY CAMERA SERVER")
    print(" Starting Flask on http://127.0.0.1:5001")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5001, debug=False, threaded=True)
