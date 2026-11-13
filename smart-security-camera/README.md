# AI-Powered Smart Security Camera
> **Intelligent Real-Time Autonomous Surveillance System**  
> *Final Year CSE Project / Computer Vision & Edge AI Surveillance Demonstration*

---

## 1. Project Overview

The **AI-Powered Smart Security Camera** is an automated video surveillance platform built with **Python, OpenCV, YOLOv8 (Ultralytics), Flask, and SQLite**. It transforms any standard laptop webcam, RTSP IP camera, or prerecorded video into an intelligent security operations center (SOC).

Unlike traditional passive CCTV systems that merely record hours of video without context, this system actively analyzes video streams in real time. It performs multi-class object detection, assigns persistent trajectory tracking IDs to individuals, monitors perimeter rules, detects suspicious activities (unauthorized zone intrusion, loitering, abnormal movement, unattended objects), triggers audio/visual alarms, captures instant forensic snapshots, and persists incidents in an auditable SQLite database.

---

## 2. Key Features

- **Live Camera Surveillance:** Real-time capture from laptop webcams (device 0) or RTSP streams with Start/Stop controls and graceful fallback simulation.
- **AI Object Detection (YOLOv8):** Detects Persons, Cars, Motorcycles, Bicycles, Backpacks, Luggage, and other COCO classes with confidence ratings.
- **Multi-Object & Person Tracking:** Custom centroid and trajectory-based tracking engine assigning persistent tags (e.g., `Person #1`, `Person #2`) across frames with motion path trails.
- **Restricted Area Violation (Unauthorized Entry):** Configurable rectangular perimeter zone. Triggers critical **HIGH RISK** alerts upon breach.
- **Loitering Detection:** Monitors dwell time and displacement. If a person stays in approximately the same area for longer than `LOITERING_TIME` (default 10s), flags **MEDIUM RISK** suspicious loitering.
- **Abnormal / Sudden Movement:** Calculates object velocity across frame history. Flags sudden rapid movement or running (default >200 px/s).
- **Unattended Object Detection:** Basic demonstration module that detects stationary luggage/backpacks that linger beyond `unattended_time` (default 15s).
- **Instant Snapshot Archival:** Automatically crops and saves full-resolution JPEG evidence frames to disk on every alert trigger.
- **SQLite Event Database:** Persistent logging of event ID, type, timestamp, camera, location, risk level, description, and snapshot path.
- **Enterprise Dark SOC Dashboard:** Cyberpunk dark security theme, live HUD telemetry, real-time metric cards, active alert stack, and recent incident logs without requiring full-page reload.
- **Event History & Forensic Query:** Search and filter historical logs by event type, risk level, and date with one-click snapshot modal inspection.
- **Dynamic Settings Interface:** Runtime configuration of zone coordinates, detection confidence, alert sound toggles, and temporal thresholds.
- **Dual Mode (Live Webcam & Demo Video):** Seamlessly switch between physical webcam and uploaded prerecorded video files (`.mp4`, `.avi`, `.mov`) with automatic looping.

---

## 3. System Architecture

```text
       +---------------------------------------------+
       |   Video Input (Webcam / Uploaded MP4 / IP)  |
       +---------------------------------------------+
                              |
                              v
       +---------------------------------------------+
       |   Frame Capture & Normalization (OpenCV)    |
       +---------------------------------------------+
                              |
                              v
       +---------------------------------------------+
       |      YOLOv8 Nano Neural Inference Engine     |
       |  (Bounding Boxes, Classes, Confidence %)    |
       +---------------------------------------------+
                              |
                              v
       +---------------------------------------------+
       |   Multi-Object Centroid & Trajectory Tracker |
       |        (Persistent IDs: Person #1, #2)      |
       +---------------------------------------------+
                              |
                              v
       +---------------------------------------------+
       |         Behavioral Activity Analyzer        |
       |  - Restricted Area Intrusion (HIGH Risk)    |
       |  - Loitering Duration Monitor (MEDIUM Risk) |
       |  - Abnormal Speed Calculation (MEDIUM Risk) |
       |  - Unattended Bag Detection   (Demo Feature)|
       +---------------------------------------------+
                              |
                              v
                   Suspicious Activity Flagged?
                    /                       \
                 YES                         NO
                 /                             \
     +---------------------------+              +-------------------------+
     |   Alert & Event Manager   |              | Stream HUD Annotator    |
     | - Debounce / Cooldown     |              | - Bounding Boxes & Tags |
     | - Capture Frame Snapshot  |              | - Restricted Box Banner |
     | - Insert SQLite Log       |              | - Motion Trails & Clock |
     | - Broadcast Active Alert  |              +-------------------------+
     +---------------------------+                           |
                 \                                           /
                  v                                         v
       +-------------------------------------------------------------+
       |          Flask Application & MJPEG Video Streaming          |
       |          REST API: /api/stats, /api/events, /settings       |
       +-------------------------------------------------------------+
                                      |
                                      v
       +-------------------------------------------------------------+
       |       Browser Frontend (HTML5, Modern Dark CSS, JS)         |
       |  - Live MJPEG Player        - Web Audio API Sound Buzzer    |
       |  - Real-time Polling Engine - Evidence Snapshot Modal       |
       +-------------------------------------------------------------+
```

---

## 4. Technologies Used

| Technology | Purpose |
|---|---|
| **Python 3.10+ / 3.14** | Core backend programming language |
| **OpenCV (`opencv-python`)** | Frame acquisition, image manipulation, HUD graphics, snapshot saving |
| **Ultralytics YOLOv8n** | Lightweight deep learning model for real-time object detection |
| **Flask** | Web application framework and MJPEG video streaming server |
| **SQLite3** | Embedded relational database for zero-configuration event persistence |
| **HTML5 & CSS3** | Dark SOC interface, responsive grid, telemetry indicators |
| **Vanilla JavaScript (ES6+)** | Dynamic polling, camera controls, Web Audio synthesizer, modal viewer |

---

## 5. Project Directory Structure

```text
smart-security-camera/
│
├── app.py                     # Main Flask server and video pipeline coordinator
├── config.py                  # System configuration parameters & defaults
├── database.py                # SQLite database management and query helpers
├── requirements.txt           # Python package dependencies
├── README.md                  # Comprehensive project documentation
├── generate_demo_video.py     # Script to generate sample surveillance video
├── demo_video.mp4             # Pre-generated sample surveillance video
│
├── detection/
│   ├── __init__.py
│   ├── detector.py            # YOLOv8 inference wrapper and HUD drawing
│   ├── tracker.py             # Centroid tracker with velocity and history
│   └── activity.py            # Suspicious behavior & restricted zone rules
│
├── alerts/
│   ├── __init__.py
│   └── alert_manager.py       # Alert debouncing, snapshot archival & DB persistence
│
├── database/
│   └── security.db            # SQLite database file (created automatically)
│
├── models/
│   └── yolov8n.pt             # Pre-trained YOLOv8 Nano weights (~6.5 MB)
│
├── static/
│   ├── css/
│   │   └── style.css          # Professional dark SOC dashboard styles
│   ├── js/
│   │   └── dashboard.js       # Real-time poller, audio buzzer, UI interactions
│   ├── snapshots/             # Saved event evidence snapshots (.jpg)
│   └── uploads/               # Uploaded prerecorded demo video files
│
└── templates/
    ├── index.html             # Main real-time monitoring dashboard
    ├── events.html            # Event history with search & filter
    └── settings.html          # Configuration settings page
```

---

## 6. Installation & Setup Guide

### Step 1: Navigate to the Project Directory
Open PowerShell or Command Prompt:
```powershell
cd c:\Users\sarth\OneDrive\Desktop\TBP\smart-security-camera
```

### Step 2: Install Python Dependencies
Run pip install with `requirements.txt`:
```powershell
python -m pip install -r requirements.txt
```
*Packages installed: `flask`, `opencv-python`, `ultralytics`, `numpy`, `Pillow`.*

### Step 3: YOLO Model Preparation
The lightweight model `models/yolov8n.pt` is already bundled. If you ever need to redownload it manually:
```powershell
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

---

## 7. Running the Application

To start the local surveillance server:
```powershell
python app.py
```

You will see:
```text
============================================================
 AI-POWERED SMART SECURITY CAMERA SERVER
 Starting Flask on http://127.0.0.1:5000
============================================================
 * Serving Flask app 'app'
 * Running on http://127.0.0.1:5000
```

Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 8. Operating the Security Camera

### Live Webcam Mode
1. Click **▶ Start Camera** on the dashboard.
2. The system connects to your default webcam (index `0`) and displays the annotated feed.
3. If someone walks in front of the camera, you will observe:
   - Green bounding box labelled `Person 92%`
   - Identifier tag `Person #1`
   - Real-time movement trajectory trails
4. Step into the highlighted red zone on the right of the frame:
   - A **HIGH RISK** alert `Unauthorized Entry` triggers.
   - An audible security siren sounds in the browser.
   - An evidence snapshot is captured and stored.
   - The log row appears at the top of the **Recent Security Events** table.
5. Click **⏹ Stop Camera** at any time to halt the video feed.

### Prerecorded Demo Mode (No Webcam Required)
If you are presenting in a classroom or without a webcam:
1. Click **📁 Upload Demo Video** on the dashboard.
2. Choose the pre-generated `demo_video.mp4` located in `smart-security-camera/demo_video.mp4` (or any MP4 video of people walking/moving).
3. The badge will switch to **DEMO VIDEO**.
4. The system will loop the video through the YOLO detection and tracking pipeline, automatically generating events for demonstration!

---

## 9. How Suspicious Activity Detection Works

### 1. Restricted Area Violation (Unauthorized Entry)
- **Concept:** Defines a protected perimeter polygon or rectangle on the camera plane.
- **Algorithm:** The detector checks the bottom bounding-box coordinate (feet location) and center point against configured normalized boundaries `(x1, y1, x2, y2)`.
- **Classification:** `HIGH RISK`.

### 2. Loitering Detection
- **Concept:** Identifies individuals lingering suspiciously in an area for an extended duration.
- **Algorithm:** The tracker calculates total dwell time `t_dwell = last_seen - first_seen`. If `t_dwell >= LOITERING_TIME` (default 10s) and overall displacement `sqrt((x - x0)^2 + (y - y0)^2) <= loitering_distance` (50px), the person is flagged.
- **Classification:** `MEDIUM RISK`.

### 3. Abnormal Movement Detection
- **Concept:** Detects rapid sudden movement, running, fleeing, or panic behaviors.
- **Algorithm:** The tracker keeps a sliding time window (1.0 second). It computes velocity in pixels per second: `v = sqrt(dx^2 + dy^2) / dt`. If `v >= movement_threshold` (default 200px/s), an event is triggered.
- **Classification:** `MEDIUM RISK`.

### 4. Unattended Object Detection (Demonstration Module)
- **Concept:** Identifies unattended luggage, backpacks, or packages left behind in public spaces.
- **Algorithm:** Detects non-person items (`Backpack`, `Handbag`, `Suitcase`). If the item remains stationary beyond `unattended_time` (default 15s) with no person within proximity, it flags an unattended object alert.
- **Classification:** `MEDIUM RISK`.

---

## 10. Database Structure (SQLite)

The database file is stored in `database/security.db`.

### Schema: `events` Table
| Column Name | Data Type | Description |
|---|---|---|
| `id` | `INTEGER PRIMARY KEY AUTOINCREMENT` | Unique event identifier |
| `event_type` | `TEXT NOT NULL` | Type (`Unauthorized Entry`, `Loitering`, etc.) |
| `timestamp` | `TEXT NOT NULL` | Date and time formatted (`YYYY-MM-DD HH:MM:SS`) |
| `camera` | `TEXT` | Camera name (e.g., `Camera 1`) |
| `location` | `TEXT` | Camera location descriptor (e.g., `Main Entrance`) |
| `risk_level` | `TEXT CHECK(...)` | Severity (`LOW`, `MEDIUM`, `HIGH`) |
| `description` | `TEXT` | Detailed context and metrics |
| `image_path` | `TEXT` | Relative path to saved snapshot file |
| `status` | `TEXT` | Resolution status (Default: `NEW`) |

---

## 11. Limitations

1. **2D Perspective Distortion:** Pixel speed varies based on how close the subject is to the lens. A true meter-per-second calculation requires camera intrinsic matrix calibration.
2. **Simple Occlusion Handling:** The lightweight centroid tracker works reliably under moderate traffic, but severe multi-person cross-occlusions benefit from ByteTrack or DeepSORT with Re-ID feature embeddings.
3. **Lighting & Shadows:** Extreme shadows or glare can affect bounding box aspect ratios in basic cameras.

---

## 12. Future Improvements (Future Scope)

- **Mobile Application:** Push notifications to mobile devices via Firebase Cloud Messaging (FCM) or Telegram bot with attached snapshot previews.
- **Multi-Camera Support:** Centralized NVR matrix switching between multiple IP/RTSP streams with multi-threaded GPU decoders.
- **Edge AI Deployment:** Quantize YOLOv8 weights to INT8 TensorRT, ONNX Runtime, or OpenVINO for deployment on NVIDIA Jetson Orin or Raspberry Pi 5.
- **Advanced Behavior Analysis:** Pose estimation (YOLOv8-Pose) to detect slip-and-fall incidents, hands-up robbery postures, or fighting detection.
- **Cloud-Based Monitoring & Long-Term Analytics:** Automated AWS S3 / Google Cloud Storage offloading for event video clips with compliance audit trails.

---

## 13. Quick Verification Commands

```powershell
# 1. Test database operations
python -c "import database; database.init_db(); print('DB OK')"

# 2. Test YOLO detector loading
python -c "from detection.detector import ObjectDetector; d = ObjectDetector(); print('Detector loaded:', d.is_loaded)"

# 3. Generate sample demo video
python generate_demo_video.py

# 4. Launch web application
python app.py
```
