"""
Object and Person Tracking Module.
Assigns persistent IDs to detected persons across video frames
using Euclidean centroid distance and IoU matching with trajectory history.
"""

import math
import time
from collections import OrderedDict
import numpy as np
import cv2


class TrackedObject:
    """Represents a single tracked entity."""
    def __init__(self, obj_id, class_name, bbox, center):
        self.id = obj_id
        self.class_name = class_name
        self.bbox = bbox  # [x1, y1, x2, y2]
        self.center = center  # (cx, cy)
        self.history = [center]  # trajectory centers
        self.timestamps = [time.time()]
        self.disappeared_count = 0
        self.first_seen = time.time()
        self.last_seen = time.time()
        self.initial_position = center

    def update(self, bbox, center):
        self.bbox = bbox
        self.center = center
        self.history.append(center)
        self.timestamps.append(time.time())
        # Keep maximum 50 points of history
        if len(self.history) > 50:
            self.history.pop(0)
            self.timestamps.pop(0)
        self.disappeared_count = 0
        self.last_seen = time.time()

    @property
    def dwell_time(self):
        """Total time in seconds this object has been tracked."""
        return self.last_seen - self.first_seen

    @property
    def total_displacement(self):
        """Distance from initial detection point."""
        dx = self.center[0] - self.initial_position[0]
        dy = self.center[1] - self.initial_position[1]
        return math.sqrt(dx * dx + dy * dy)

    def speed_last_seconds(self, seconds=1.0):
        """Calculate movement in pixels over the last N seconds."""
        now = time.time()
        cutoff = now - seconds
        past_idx = 0
        for i, t in enumerate(self.timestamps):
            if t >= cutoff:
                past_idx = i
                break

        if past_idx < len(self.history):
            past_center = self.history[past_idx]
            dx = self.center[0] - past_center[0]
            dy = self.center[1] - past_center[1]
            return math.sqrt(dx * dx + dy * dy)
        return 0.0


class CentroidTracker:
    def __init__(self, max_disappeared=30, max_distance=80):
        """
        max_disappeared: consecutive frames an object can be missing before being deregistered
        max_distance: maximum pixel distance between centers to consider it the same object
        """
        self.next_object_id = 1
        self.objects = OrderedDict()  # id -> TrackedObject
        self.max_disappeared = max_disappeared
        self.max_distance = max_distance

    def register(self, class_name, bbox, center):
        obj = TrackedObject(self.next_object_id, class_name, bbox, center)
        self.objects[self.next_object_id] = obj
        self.next_object_id += 1
        return obj

    def deregister(self, obj_id):
        if obj_id in self.objects:
            del self.objects[obj_id]

    def update(self, detections):
        """
        Update tracker with current frame detections.
        detections: list of dicts with 'box', 'class_name', 'center', etc.
        Returns:
            list of active TrackedObject instances
        """
        # If no detections in current frame, increment disappeared count
        if len(detections) == 0:
            for obj_id in list(self.objects.keys()):
                self.objects[obj_id].disappeared_count += 1
                if self.objects[obj_id].disappeared_count > self.max_disappeared:
                    self.deregister(obj_id)
            return list(self.objects.values())

        input_bboxes = [d["box"] for d in detections]
        input_classes = [d["class_name"] for d in detections]
        input_centers = [d["center"] for d in detections]

        # If currently tracking no objects, register all detections
        if len(self.objects) == 0:
            for i in range(len(detections)):
                self.register(input_classes[i], input_bboxes[i], input_centers[i])
            return list(self.objects.values())

        # Grab existing object IDs and their centers
        object_ids = list(self.objects.keys())
        object_centers = [self.objects[oid].center for oid in object_ids]

        # Compute distance matrix between existing centers and new centers
        D = np.zeros((len(object_ids), len(input_centers)), dtype=np.float32)
        for i, oc in enumerate(object_centers):
            for j, ic in enumerate(input_centers):
                # Extra penalty if class doesn't match
                class_penalty = 0 if self.objects[object_ids[i]].class_name == input_classes[j] else 1000
                dist = math.hypot(oc[0] - ic[0], oc[1] - ic[1]) + class_penalty
                D[i, j] = dist

        # Find smallest value in each row and sort row indices
        rows = D.min(axis=1).argsort()
        cols = D.argmin(axis=1)[rows]

        used_rows = set()
        used_cols = set()

        for row, col in zip(rows, cols):
            if row in used_rows or col in used_cols:
                continue

            # Distance threshold check
            if D[row, col] > self.max_distance:
                continue

            obj_id = object_ids[row]
            self.objects[obj_id].update(input_bboxes[col], input_centers[col])
            used_rows.add(row)
            used_cols.add(col)

        # Unused rows -> object disappeared
        unused_rows = set(range(0, D.shape[0])).difference(used_rows)
        for row in unused_rows:
            obj_id = object_ids[row]
            self.objects[obj_id].disappeared_count += 1
            if self.objects[obj_id].disappeared_count > self.max_disappeared:
                self.deregister(obj_id)

        # Unused cols -> new detections to register
        unused_cols = set(range(0, D.shape[1])).difference(used_cols)
        for col in unused_cols:
            self.register(input_classes[col], input_bboxes[col], input_centers[col])

        return list(self.objects.values())

    def draw_tracks(self, frame, tracked_objects):
        """
        Draw tracking IDs and trajectory motion trails on frame.
        """
        if frame is None:
            return frame

        annotated = frame.copy()

        for obj in tracked_objects:
            if obj.disappeared_count > 0:
                continue  # don't draw if not visible this frame

            x1, y1, x2, y2 = obj.bbox
            color = (0, 255, 128) if obj.class_name == "Person" else (255, 180, 0)

            # Draw trajectory path
            if len(obj.history) > 1:
                for idx in range(1, len(obj.history)):
                    pt1 = obj.history[idx - 1]
                    pt2 = obj.history[idx]
                    alpha = idx / float(len(obj.history))
                    cv2.line(annotated, pt1, pt2, (0, int(200 * alpha), int(255 * alpha)), 2)

            # Draw tracking ID tag right above bounding box
            id_text = f"{obj.class_name} #{obj.id}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.55
            thickness = 2
            (tw, th), _ = cv2.getTextSize(id_text, font, font_scale, thickness)

            badge_y = max(y1 - 10, th + 5)
            # Background badge
            cv2.rectangle(
                annotated,
                (x1, badge_y - th - 6),
                (x1 + tw + 10, badge_y + 4),
                (20, 20, 30),
                -1
            )
            cv2.rectangle(
                annotated,
                (x1, badge_y - th - 6),
                (x1 + tw + 10, badge_y + 4),
                color,
                1
            )
            cv2.putText(
                annotated,
                id_text,
                (x1 + 5, badge_y - 2),
                font,
                font_scale,
                (255, 255, 255),
                thickness,
                cv2.LINE_AA
            )

        return annotated
