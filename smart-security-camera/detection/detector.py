"""
Object Detection Module using YOLOv8.
Handles model loading, inference on frames, and visual bounding box annotations.
"""

import os
import cv2
import numpy as np
from config import CONFIG

# COCO class names mapping for quick reference
COCO_CLASSES = {
    0: "Person",
    1: "Bicycle",
    2: "Car",
    3: "Motorcycle",
    5: "Bus",
    7: "Truck",
    24: "Backpack",
    26: "Handbag",
    28: "Suitcase",
    39: "Bottle",
    56: "Chair",
    67: "Cell Phone",
    63: "Laptop",
}

# Color palette for classes (BGR)
CLASS_COLORS = {
    "Person": (0, 255, 128),       # Bright neon green/cyan
    "Car": (255, 180, 0),          # Blueish amber
    "Motorcycle": (255, 100, 50),  # Blueish
    "Bicycle": (200, 200, 0),      # Cyan
    "Backpack": (0, 165, 255),     # Orange
    "Default": (0, 220, 255)       # Yellow
}


class ObjectDetector:
    def __init__(self, model_path=None, conf_threshold=None):
        """Initialize the YOLO model."""
        self.conf_threshold = conf_threshold or CONFIG.get("detection_confidence", 0.45)
        self.model_path = model_path or CONFIG.get("model_path")
        self.model = None
        self.is_loaded = False
        self._load_model()

    def _load_model(self):
        """Load YOLO model with graceful fallback and error handling."""
        try:
            from ultralytics import YOLO

            # Ensure models directory exists
            models_dir = os.path.dirname(self.model_path)
            os.makedirs(models_dir, exist_ok=True)

            # Check if model exists locally, otherwise YOLO will download yolov8n.pt automatically
            if os.path.exists(self.model_path):
                print(f"[Detector] Loading local model from: {self.model_path}")
                self.model = YOLO(self.model_path)
            else:
                print(f"[Detector] Model not found at {self.model_path}, downloading YOLOv8n...")
                self.model = YOLO("yolov8n.pt")
                # Save or copy to target path if possible
                try:
                    if not os.path.exists(self.model_path) and os.path.exists("yolov8n.pt"):
                        import shutil
                        shutil.copy("yolov8n.pt", self.model_path)
                except Exception as ex:
                    print(f"[Detector] Note: Could not copy model file: {ex}")

            self.is_loaded = True
            print("[Detector] YOLOv8 model loaded successfully.")
        except Exception as e:
            print(f"[Detector ERROR] Failed to load YOLO model: {e}")
            self.model = None
            self.is_loaded = False

    def detect(self, frame):
        """
        Run inference on a single frame.
        Returns:
            detections: List of dicts with keys:
                - 'box': [x1, y1, x2, y2]
                - 'class_id': int
                - 'class_name': str
                - 'confidence': float
                - 'center': (cx, cy)
        """
        if not self.is_loaded or self.model is None or frame is None:
            return []

        detections = []
        try:
            # Run YOLO prediction
            results = self.model.predict(
                source=frame,
                conf=self.conf_threshold,
                verbose=False
            )

            if not results or len(results) == 0:
                return []

            result = results[0]
            boxes = result.boxes

            for box in boxes:
                cls_id = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                xyxy = box.xyxy[0].cpu().numpy().astype(int).tolist()
                x1, y1, x2, y2 = xyxy

                # Get class name
                if hasattr(result, "names") and cls_id in result.names:
                    raw_name = result.names[cls_id]
                    class_name = raw_name.capitalize()
                else:
                    class_name = COCO_CLASSES.get(cls_id, f"Class_{cls_id}")

                cx = int((x1 + x2) / 2)
                cy = int((y1 + y2) / 2)

                detections.append({
                    "box": [x1, y1, x2, y2],
                    "class_id": cls_id,
                    "class_name": class_name,
                    "confidence": conf,
                    "center": (cx, cy),
                })

        except Exception as e:
            print(f"[Detector ERROR] Detection error: {e}")

        return detections

    def draw_detections(self, frame, detections):
        """
        Draw professional HUD-style bounding boxes and labels on the frame.
        """
        if frame is None or not detections:
            return frame

        annotated = frame.copy()
        for det in detections:
            x1, y1, x2, y2 = det["box"]
            cls_name = det["class_name"]
            conf = det["confidence"]
            color = CLASS_COLORS.get(cls_name, CLASS_COLORS["Default"])

            # 1. Main bounding box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            # 2. Corner accent markers for futuristic security camera HUD
            corner_len = min(15, int((x2 - x1) * 0.2), int((y2 - y1) * 0.2))
            accent_color = (255, 255, 255)
            # Top-left
            cv2.line(annotated, (x1, y1), (x1 + corner_len, y1), accent_color, 2)
            cv2.line(annotated, (x1, y1), (x1, y1 + corner_len), accent_color, 2)
            # Top-right
            cv2.line(annotated, (x2, y1), (x2 - corner_len, y1), accent_color, 2)
            cv2.line(annotated, (x2, y1), (x2, y1 + corner_len), accent_color, 2)
            # Bottom-left
            cv2.line(annotated, (x1, y2), (x1 + corner_len, y2), accent_color, 2)
            cv2.line(annotated, (x1, y2), (x1, y2 - corner_len), accent_color, 2)
            # Bottom-right
            cv2.line(annotated, (x2, y2), (x2 - corner_len, y2), accent_color, 2)
            cv2.line(annotated, (x2, y2), (x2, y2 - corner_len), accent_color, 2)

            # 3. Label tag
            label = f"{cls_name} {int(conf * 100)}%"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            thickness = 1
            (w, h), baseline = cv2.getTextSize(label, font, font_scale, thickness)

            # Background rectangle for text
            label_y = max(y1, h + 8)
            cv2.rectangle(
                annotated,
                (x1, label_y - h - 6),
                (x1 + w + 8, label_y + baseline),
                color,
                -1
            )

            # Text label
            text_color = (0, 0, 0) if (color[0] + color[1] + color[2]) > 350 else (255, 255, 255)
            cv2.putText(
                annotated,
                label,
                (x1 + 4, label_y - 2),
                font,
                font_scale,
                text_color,
                thickness,
                cv2.LINE_AA
            )

        return annotated
