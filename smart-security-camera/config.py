"""
Configuration module for AI-Powered Smart Security Camera.
Stores all configurable settings with sensible defaults.
"""

import os

# Base directory of the project
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# Application Configuration
# ============================================================
CONFIG = {
    # --- Camera Settings ---
    "camera_source": 0,                  # 0 = default webcam, or path to video file
    "camera_name": "Camera 1",
    "camera_location": "Main Entrance",
    "frame_width": 640,
    "frame_height": 480,
    "fps": 30,

    # --- YOLO Detection Settings ---
    "model_path": os.path.join(BASE_DIR, "models", "yolov8n.pt"),
    "detection_confidence": 0.45,         # Minimum confidence threshold
    "target_classes": [0, 1, 2, 3, 24],   # person, bicycle, car, motorcycle, backpack

    # --- Restricted Area (normalized coordinates 0.0-1.0) ---
    # Default: a rectangle in the right portion of the frame
    "restricted_area": {
        "enabled": True,
        "x1": 0.6,   # top-left x  (fraction of frame width)
        "y1": 0.2,   # top-left y  (fraction of frame height)
        "x2": 0.95,  # bottom-right x
        "y2": 0.8    # bottom-right y
    },

    # --- Loitering Detection ---
    "loitering_time": 10,                 # seconds before flagging loitering
    "loitering_distance": 50,             # pixel distance threshold for "same area"

    # --- Abnormal Movement Detection ---
    "movement_threshold": 200,            # pixels moved in short time
    "movement_window": 1.0,               # seconds to measure movement over

    # --- Unattended Object Detection ---
    "unattended_time": 15,                # seconds before flagging unattended object
    "unattended_distance": 30,            # pixel distance threshold for "stationary"

    # --- Alert Settings ---
    "alert_sound": True,                  # Play alert sound in browser
    "alert_cooldown": 10,                 # seconds between duplicate alerts of same type

    # --- Database ---
    "database_path": os.path.join(BASE_DIR, "database", "security.db"),

    # --- Snapshots ---
    "snapshot_dir": os.path.join(BASE_DIR, "static", "snapshots"),

    # --- System ---
    "system_status": "ONLINE",
    "demo_mode": False,
}


def get_config():
    """Return a copy of the current configuration."""
    return CONFIG.copy()


def update_config(updates: dict):
    """Update configuration values at runtime."""
    for key, value in updates.items():
        if key in CONFIG:
            CONFIG[key] = value


def get_restricted_area_pixels(frame_width, frame_height):
    """Convert normalised restricted-area coords to pixel values."""
    ra = CONFIG["restricted_area"]
    if not ra["enabled"]:
        return None
    return (
        int(ra["x1"] * frame_width),
        int(ra["y1"] * frame_height),
        int(ra["x2"] * frame_width),
        int(ra["y2"] * frame_height),
    )
