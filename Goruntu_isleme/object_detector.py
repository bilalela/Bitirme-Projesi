#!/usr/bin/env python3
"""
Shared YOLO detector helper for UAV camera streams.
"""

from __future__ import annotations

import threading
from pathlib import Path

import cv2
from ultralytics import YOLO

try:
    import torch
except Exception:
    torch = None


class SharedYOLODetector:
    """Thread-safe Ultralytics YOLO wrapper for shared inference."""

    def __init__(
        self,
        model_path: str | Path | None = None,
        conf: float = 0.10,
        iou: float = 0.45,
        imgsz: int = 640,
        device: str = "auto",
    ):
        """Initialize YOLO detector with optimized defaults for real-time tracking.
        conf=0.10 for better detection sensitivity on distant/small targets
        imgsz=640 gives better small/distant target recall; GPU keeps it realtime.
        """
        vision_root = Path(__file__).resolve().parent
        default_model_path = vision_root / "models" / "best.pt"
        self.model_path = Path(model_path) if model_path is not None else default_model_path
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {self.model_path}")

        self.conf = conf  # Default lowered to 0.10
        self.iou = iou
        self.imgsz = imgsz
        self.lock = threading.Lock()
        self.model = YOLO(str(self.model_path))

        # Runtime device selection
        if device == "auto":
            cuda_ok = bool(torch is not None and torch.cuda.is_available())
            self.device = "cuda:0" if cuda_ok else "cpu"
        elif device in {"cuda", "cuda:0"}:
            cuda_ok = bool(torch is not None and torch.cuda.is_available())
            self.device = "cuda:0" if cuda_ok else "cpu"
        else:
            self.device = "cpu"

        self.use_half = self.device.startswith("cuda")
        try:
            self.model.to(self.device)
        except Exception:
            # Ultralytics may handle device per predict call.
            pass

    def infer(self, frame):
        """Run inference and return detection metadata (without plotting overhead)."""
        with self.lock:
            results = self.model.predict(
                frame,
                conf=self.conf,
                iou=self.iou,
                imgsz=self.imgsz,
                device=self.device,
                half=self.use_half,
                verbose=False,
            )

        result = results[0]
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

        return detections

    def annotate(self, frame):
        """Run inference and return an annotated frame plus detection metadata."""
        detections = self.infer(frame)
        annotated_frame = frame.copy()
        for det in detections:
            x1, y1, x2, y2 = [int(v) for v in det["xyxy"]]
            label = det["label"]
            conf = det["confidence"]
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                annotated_frame,
                f"{label} {conf:.2f}",
                (x1, max(15, y1 - 5)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1,
            )

        return annotated_frame, detections