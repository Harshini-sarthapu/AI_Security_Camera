"""
Alert Manager Module.
Coordinates alert cooldowns, snapshot capture, SQLite persistence,
and real-time in-memory alert state for the dashboard.
"""

import os
import time
from datetime import datetime
import cv2
from config import CONFIG
import database


class AlertManager:
    def __init__(self):
        # Map (event_type, object_id) -> last_triggered_timestamp
        self.cooldown_tracker = {}
        # List of recent active alerts (in-memory for real-time frontend)
        self.active_alerts = []
        # Monotonically increasing alert counter for frontend client sync
        self.alert_counter = 0

        # Ensure snapshots directory exists
        os.makedirs(CONFIG["snapshot_dir"], exist_ok=True)

    def process_events(self, frame, events, current_config=None):
        """
        Process a list of raw events detected in the current frame.
        Handles debouncing/cooldown, snapshot saving, and SQLite logging.
        Returns:
            newly_triggered: list of new alerts generated in this step
        """
        cfg = current_config or CONFIG
        cooldown_sec = cfg.get("alert_cooldown", 10)
        now = time.time()
        newly_triggered = []

        for ev in events:
            ev_type = ev["event_type"]
            obj_id = ev.get("object_id", 0)
            key = (ev_type, obj_id)

            # Check cooldown
            last_time = self.cooldown_tracker.get(key, 0)
            if now - last_time < cooldown_sec:
                continue  # Skip due to cooldown

            # Update cooldown timestamp
            self.cooldown_tracker[key] = now

            # 1. Capture snapshot of frame
            snapshot_filename = f"snapshot_{int(now)}_{self.alert_counter + 1}.jpg"
            snapshot_rel_path = f"snapshots/{snapshot_filename}"
            snapshot_abs_path = os.path.join(cfg.get("snapshot_dir", CONFIG["snapshot_dir"]), snapshot_filename)

            try:
                # Save snapshot to disk
                cv2.imwrite(snapshot_abs_path, frame)
            except Exception as e:
                print(f"[AlertManager ERROR] Could not save snapshot: {e}")
                snapshot_rel_path = ""

            # 2. Add event to SQLite
            risk = ev.get("risk_level", "MEDIUM")
            camera = ev.get("camera", cfg.get("camera_name", "Camera 1"))
            location = ev.get("location", cfg.get("camera_location", "Main Entrance"))
            description = ev.get("description", "")

            db_event_id = database.add_event(
                event_type=ev_type,
                camera=camera,
                location=location,
                risk_level=risk,
                description=description,
                image_path=snapshot_rel_path
            )

            # 3. Create alert object
            alert_item = {
                "id": db_event_id,
                "event_type": ev_type,
                "risk_level": risk,
                "camera": camera,
                "location": location,
                "description": description,
                "timestamp": datetime.now().strftime("%d %b %Y, %H:%M:%S"),
                "image_url": f"/static/{snapshot_rel_path}" if snapshot_rel_path else "",
                "created_time": now
            }

            self.alert_counter += 1
            self.active_alerts.insert(0, alert_item)
            # Retain only top 25 active alerts in memory
            if len(self.active_alerts) > 25:
                self.active_alerts = self.active_alerts[:25]

            newly_triggered.append(alert_item)
            print(f"[ALERT TRIGGERED] [{risk}] {ev_type} - {description}")

        # Clean old cooldowns
        for k in list(self.cooldown_tracker.keys()):
            if now - self.cooldown_tracker[k] > cooldown_sec * 3:
                del self.cooldown_tracker[k]

        return newly_triggered

    def get_active_alerts(self):
        """Return the current active alerts."""
        return self.active_alerts

    def clear_active_alerts(self):
        """Clear the active alerts cache."""
        self.active_alerts.clear()
