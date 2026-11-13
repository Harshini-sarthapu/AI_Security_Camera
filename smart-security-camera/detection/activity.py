"""
Activity Analysis Module.
Performs real-time behavioral analysis on tracked objects:
1. Restricted Area Violation / Unauthorized Entry (HIGH Risk)
2. Loitering Detection (MEDIUM Risk)
3. Abnormal / Rapid Movement Detection (MEDIUM Risk)
4. Unattended Object Detection (MEDIUM/LOW Risk - Demo Module)
"""

import math
import time
import cv2
import numpy as np
from config import CONFIG, get_restricted_area_pixels


class ActivityAnalyzer:
    def __init__(self):
        # Cache of objects that have already triggered alerts to manage local state
        self.loitering_flagged = set()
        self.unauthorized_flagged = set()
        self.unattended_flagged = set()
        self.abnormal_flagged = set()

    def analyze(self, frame_shape, tracked_objects, current_config=None):
        """
        Analyze current frame's tracked objects.
        Returns:
            events: List of detected security events
            annotated_alerts: List of visual alert markers for drawing on frame
        """
        cfg = current_config or CONFIG
        h, w = frame_shape[:2]
        events = []
        visual_tags = []  # tuples: (obj_id, tag_text, color)

        restricted_box = get_restricted_area_pixels(w, h)
        rx1, ry1, rx2, ry2 = restricted_box if restricted_box else (0, 0, 0, 0)
        restricted_enabled = cfg.get("restricted_area", {}).get("enabled", True) and restricted_box is not None

        loitering_time = cfg.get("loitering_time", 10)
        loitering_dist = cfg.get("loitering_distance", 50)
        movement_thresh = cfg.get("movement_threshold", 200)
        movement_window = cfg.get("movement_window", 1.0)
        unattended_time = cfg.get("unattended_time", 15)
        unattended_dist = cfg.get("unattended_distance", 30)

        for obj in tracked_objects:
            if obj.disappeared_count > 0:
                continue

            cx, cy = obj.center
            bx1, by1, bx2, by2 = obj.bbox

            # ============================================================
            # 1. RESTRICTED AREA / UNAUTHORIZED ENTRY (People only)
            # ============================================================
            if restricted_enabled and obj.class_name == "Person":
                # Check if bottom center (feet) or center is inside restricted zone
                feet_y = by2
                in_restricted = (rx1 <= cx <= rx2) and (ry1 <= feet_y <= ry2 or ry1 <= cy <= ry2)

                if in_restricted:
                    visual_tags.append((obj.id, "RESTRICTED VIOLATION", (0, 0, 255)))
                    events.append({
                        "event_type": "Unauthorized Entry",
                        "risk_level": "HIGH",
                        "camera": cfg.get("camera_name", "Camera 1"),
                        "location": cfg.get("camera_location", "Main Entrance"),
                        "description": f"Person #{obj.id} entered designated Restricted Area.",
                        "object_id": obj.id,
                        "box": obj.bbox
                    })

            # ============================================================
            # 2. LOITERING DETECTION (People only)
            # ============================================================
            if obj.class_name == "Person":
                dwell = obj.dwell_time
                disp = obj.total_displacement

                # If person has stayed longer than loitering_time and moved less than loitering_dist
                if dwell >= loitering_time and disp <= loitering_dist:
                    visual_tags.append((obj.id, f"LOITERING ({int(dwell)}s)", (0, 165, 255)))
                    events.append({
                        "event_type": "Loitering",
                        "risk_level": "MEDIUM",
                        "camera": cfg.get("camera_name", "Camera 1"),
                        "location": cfg.get("camera_location", "Main Entrance"),
                        "description": f"Person #{obj.id} loitering in same area for {int(dwell)} seconds.",
                        "object_id": obj.id,
                        "box": obj.bbox
                    })

            # ============================================================
            # 3. ABNORMAL / RAPID MOVEMENT DETECTION
            # ============================================================
            if obj.class_name in ["Person", "Car", "Motorcycle"]:
                speed = obj.speed_last_seconds(seconds=movement_window)
                if speed >= movement_thresh:
                    visual_tags.append((obj.id, f"FAST MOVEMENT ({int(speed)}px/s)", (0, 255, 255)))
                    events.append({
                        "event_type": "Abnormal Movement",
                        "risk_level": "MEDIUM",
                        "camera": cfg.get("camera_name", "Camera 1"),
                        "location": cfg.get("camera_location", "Main Entrance"),
                        "description": f"Abnormal/rapid movement detected for {obj.class_name} #{obj.id} (velocity: {int(speed)} px/s).",
                        "object_id": obj.id,
                        "box": obj.bbox
                    })

            # ============================================================
            # 4. UNATTENDED OBJECT DETECTION (Backpack, Suitcase, etc.)
            # ============================================================
            if obj.class_name in ["Backpack", "Handbag", "Suitcase", "Bottle"]:
                dwell = obj.dwell_time
                disp = obj.total_displacement

                if dwell >= unattended_time and disp <= unattended_dist:
                    visual_tags.append((obj.id, f"UNATTENDED ({int(dwell)}s)", (0, 140, 255)))
                    events.append({
                        "event_type": "Unattended Object",
                        "risk_level": "MEDIUM",
                        "camera": cfg.get("camera_name", "Camera 1"),
                        "location": cfg.get("camera_location", "Main Entrance"),
                        "description": f"Stationary {obj.class_name} #{obj.id} unattended for {int(dwell)}s [Demo Feature].",
                        "object_id": obj.id,
                        "box": obj.bbox
                    })

        return events, visual_tags

    def draw_restricted_area(self, frame, current_config=None):
        """
        Draw a semi-transparent HUD overlay of the configured restricted zone.
        """
        if frame is None:
            return frame

        cfg = current_config or CONFIG
        h, w = frame.shape[:2]
        box = get_restricted_area_pixels(w, h)
        if not box:
            return frame

        rx1, ry1, rx2, ry2 = box
        overlay = frame.copy()

        # Semi-transparent red fill
        cv2.rectangle(overlay, (rx1, ry1), (rx2, ry2), (0, 0, 180), -1)
        cv2.addWeighted(overlay, 0.25, frame, 0.75, 0, frame)

        # High-visibility dashed/hatched boundary
        cv2.rectangle(frame, (rx1, ry1), (rx2, ry2), (0, 0, 255), 2)

        # Restricted Zone label banner
        label = "RESTRICTED AREA - NO ENTRY"
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.5
        thick = 2
        (tw, th), _ = cv2.getTextSize(label, font, scale, thick)

        banner_y = max(ry1 + th + 6, 20)
        cv2.rectangle(frame, (rx1, ry1), (min(rx1 + tw + 14, rx2), banner_y + 4), (0, 0, 200), -1)
        cv2.putText(frame, label, (rx1 + 7, banner_y - 2), font, scale, (255, 255, 255), thick, cv2.LINE_AA)

        return frame

    def draw_activity_tags(self, frame, tracked_objects, visual_tags):
        """
        Draw alert warnings over offending tracked objects.
        """
        if frame is None or not visual_tags:
            return frame

        # Map obj_id -> obj
        obj_map = {obj.id: obj for obj in tracked_objects}

        for obj_id, tag_text, color in visual_tags:
            if obj_id not in obj_map:
                continue
            obj = obj_map[obj_id]
            x1, y1, x2, y2 = obj.bbox

            # Highlight bounding box with alert color
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)

            # Draw alert banner underneath or above
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            thick = 2
            (tw, th), _ = cv2.getTextSize(tag_text, font, font_scale, thick)

            tag_y = min(y2 + th + 8, frame.shape[0] - 5)
            cv2.rectangle(frame, (x1, tag_y - th - 5), (x1 + tw + 8, tag_y + 3), color, -1)
            cv2.putText(frame, tag_text, (x1 + 4, tag_y - 2), font, font_scale, (0, 0, 0), thick, cv2.LINE_AA)

        return frame
