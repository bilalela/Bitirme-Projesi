#!/usr/bin/env python3
"""
Target Detector
Görüntü işleme ile hedef tespiti ve takip
"""

import cv2
import numpy as np
import json
from datetime import datetime
from dronekit import connect
import argparse

class TargetDetector:
    def __init__(self, connection_string, vehicle_id=3, camera_port=8080):
        self.connection_string = connection_string
        self.vehicle_id = vehicle_id
        self.camera_port = camera_port
        self.vehicle = None
        self.targets = []
        
    def connect(self):
        """Araca bağlan"""
        print(f"Connecting to vehicle: {self.connection_string}")
        self.vehicle = connect(self.connection_string, wait_ready=True, timeout=60)
        print(f"Vehicle connected: {self.vehicle.system_status}")
        
    def detect_targets(self, frame, threshold=0.5):
        """
        Frame'de hedefler tespit et
        Şu anki placeholder: renk-temelli tespit
        """
        # HSV'ye dönüştür
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Kırmızı renk masksı (hedef rengi)
        lower_red1 = np.array([0, 100, 100])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 100, 100])
        upper_red2 = np.array([180, 255, 255])
        
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask = cv2.bitwise_or(mask1, mask2)
        
        # Kontürleri bul
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        targets = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 100:  # Minimum alan
                M = cv2.moments(contour)
                if M['m00'] > 0:
                    cx = int(M['m10'] / M['m00'])
                    cy = int(M['m01'] / M['m00'])
                    targets.append({
                        'center': (cx, cy),
                        'area': area,
                        'contour': contour
                    })
        
        return targets, mask
        
    def log_detection(self, targets):
        """Tespit sonuçlarını kaydet"""
        detection = {
            'timestamp': datetime.now().isoformat(),
            'vehicle_id': self.vehicle_id,
            'targets_found': len(targets),
            'targets': [
                {
                    'center': t['center'],
                    'area': float(t['area'])
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

def main():
    parser = argparse.ArgumentParser(description='UAV Target Detector')
    parser.add_argument('--connection', default='127.0.0.1:15570', help='Vehicle connection string')
    parser.add_argument('--vehicle-id', type=int, default=3, help='Vehicle ID')
    parser.add_argument('--camera-port', type=int, default=8080, help='Camera streaming port')
    args = parser.parse_args()
    
    detector = TargetDetector(args.connection, args.vehicle_id, args.camera_port)
    
    try:
        detector.connect()
        print("Target detector initialized")
        print("Camera stream from localhost:8080")
        # Real implementation would connect to camera stream
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
