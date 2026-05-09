#!/usr/bin/env python3
"""
Shared YOLO detector helper for UAV camera streams.
"""

from __future__ import annotations

import threading
from pathlib import Path

from ultralytics import YOLO


class SharedYOLODetector:
    """Thread-safe Ultralytics YOLO wrapper for shared inference."""

    def __init__(self, model_path: str | Path | None = None, conf: float = 0.25, iou: float = 0.45, imgsz: int = 640):
        vision_root = Path(__file__).resolve().parent
        default_model_path = vision_root / "models" / "best.pt"
        self.model_path = Path(model_path) if model_path is not None else default_model_path
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {self.model_path}")

        self.conf = conf
        self.iou = iou
        self.imgsz = imgsz
        self.lock = threading.Lock()
        self.model = YOLO(str(self.model_path))

    def annotate(self, frame):
        """Run inference and return an annotated frame plus detection metadata."""
        with self.lock:
            results = self.model.predict(
                frame,
                conf=self.conf,
                iou=self.iou,
                imgsz=self.imgsz,
                verbose=False,
            )

        result = results[0]
        annotated_frame = result.plot()
        detections = []
        class_names = result.names or {}

        if result.boxes is not None:
            for box in result.boxes:
                class_id = int(box.cls[0]) if hasattr(box.cls, "__len__") else int(box.cls)
                confidence = float(box.conf[0]) if hasattr(box.conf, "__len__") else float(box.conf)
                xyxy = box.xyxy[0].tolist()
                detections.append(
                    {
                        "label": class_names.get(class_id, str(class_id)),
                        "confidence": confidence,
                        "xyxy": [float(value) for value in xyxy],
                    }
                )

        return annotated_frame, detections