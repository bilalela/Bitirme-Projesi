#!/usr/bin/env python3
"""
Target Detector
Görüntü işleme ile hedef tespiti ve takip
"""

import cv2
import json
from datetime import datetime
import argparse
import collections.abc
import collections
import sys
from pathlib import Path

collections.MutableMapping = collections.abc.MutableMapping

from dronekit import connect

PROJECT_ROOT = Path(__file__).resolve().parents[3]
VISION_DIR = PROJECT_ROOT / "Goruntu_isleme"
if str(VISION_DIR) not in sys.path:
    sys.path.insert(0, str(VISION_DIR))

from object_detector import SharedYOLODetector

class TargetDetector:
    def __init__(self, connection_string, vehicle_id=3, camera_port=8080):
        self.connection_string = connection_string
        self.vehicle_id = vehicle_id
        self.camera_port = camera_port
        self.vehicle = None
        self.targets = []
        self.detector = SharedYOLODetector()
        
    def connect(self):
        """Araca bağlan"""
        print(f"Connecting to vehicle: {self.connection_string}")
        self.vehicle = connect(self.connection_string, wait_ready=True, timeout=60)
        print(f"Vehicle connected: {self.vehicle.system_status}")
        
    def detect_targets(self, frame, threshold=0.5):
        """
        Frame'de hedefler tespit et.
        Ultralytics YOLO modelini kullanır.
        """
        annotated_frame, detections = self.detector.annotate(frame)
        targets = []
        for detection in detections:
            x1, y1, x2, y2 = detection["xyxy"]
            center_x = int((x1 + x2) / 2)
            center_y = int((y1 + y2) / 2)
            targets.append({
                'label': detection['label'],
                'confidence': detection['confidence'],
                'center': (center_x, center_y),
                'area': float((x2 - x1) * (y2 - y1)),
                'bbox': detection['xyxy']
            })

        return targets, annotated_frame
        
    def log_detection(self, targets):
        """Tespit sonuçlarını kaydet"""
        detection = {
            'timestamp': datetime.now().isoformat(),
            'vehicle_id': self.vehicle_id,
            'targets_found': len(targets),
            'targets': [
                {
                    'center': t['center'],
                    'area': float(t['area']),
                    'label': t.get('label', 'unknown'),
                    'confidence': float(t.get('confidence', 0.0))
                }
                for t in targets
            ]
        }
        self.targets.append(detection)
        
    def save_detections(self, output_file=None):
        """Tespitleri dosyaya yaz"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"detections_uav{self.vehicle_id}_{timestamp}.json"
            
        with open(output_file, 'w') as f:
            json.dump(self.targets, f, indent=2)
        print(f"Detections saved to {output_file}")

    @staticmethod
    def _resolve_source(camera_port):
        try:
            return int(camera_port)
        except (TypeError, ValueError):
            return camera_port

    def run(self):
        source = self._resolve_source(self.camera_port)
        print(f"Opening camera source: {source}")
        capture = cv2.VideoCapture(source)

        if not capture.isOpened():
            raise RuntimeError(f"Camera source could not be opened: {source}")

        print("Press q to quit the detector window.")

        while True:
            ok, frame = capture.read()
            if not ok:
                print("Frame could not be read, retrying...")
                continue

            targets, annotated_frame = self.detect_targets(frame)
            if targets:
                self.log_detection(targets)
                print(f"Detected {len(targets)} object(s): " + ", ".join(t['label'] for t in targets))

            cv2.imshow(f"Target Detector UAV{self.vehicle_id}", annotated_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        capture.release()
        cv2.destroyAllWindows()

def main():
    parser = argparse.ArgumentParser(description='UAV Target Detector')
    parser.add_argument('--connection', default='127.0.0.1:15570', help='Vehicle connection string')
    parser.add_argument('--vehicle-id', type=int, default=3, help='Vehicle ID')
    parser.add_argument('--camera-port', default='0', help='Camera source index/URL/port')
    args = parser.parse_args()
    
    detector = TargetDetector(args.connection, args.vehicle_id, args.camera_port)
    
    try:
        detector.connect()
        print("Target detector initialized")
        detector.run()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
