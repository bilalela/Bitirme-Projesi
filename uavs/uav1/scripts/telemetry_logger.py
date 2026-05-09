#!/usr/bin/env python3
"""
Telemetry Logger
Araç telemetrisini dosyaya kaydet
"""

import sys
import time
import json
from datetime import datetime
from dronekit import connect, VehicleMode
import argparse

class TelemetryLogger:
    def __init__(self, connection_string, log_file=None, vehicle_id=1):
        self.connection_string = connection_string
        self.vehicle_id = vehicle_id
        self.vehicle = None
        
        if log_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = f"telemetry_uav{vehicle_id}_{timestamp}.json"
            
        self.log_file = log_file
        self.data_buffer = []
        
    def connect(self):
        """Araca bağlan"""
        print(f"Connecting to vehicle: {self.connection_string}")
        self.vehicle = connect(self.connection_string, wait_ready=True, timeout=60)
        print(f"Vehicle connected: {self.vehicle.system_status}")
        
    def get_telemetry_snapshot(self):
        """Anlık telemetri verisi al"""
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'system_status': str(self.vehicle.system_status),
            'mode': self.vehicle.mode.name,
            'armed': self.vehicle.armed,
            'location': {
                'lat': self.vehicle.location.global_frame.lat,
                'lon': self.vehicle.location.global_frame.lon,
                'alt': self.vehicle.location.global_frame.alt,
            },
            'velocity': {
                'x': self.vehicle.velocity[0],
                'y': self.vehicle.velocity[1],
                'z': self.vehicle.velocity[2],
            },
            'attitude': {
                'roll': self.vehicle.attitude.roll,
                'pitch': self.vehicle.attitude.pitch,
                'yaw': self.vehicle.attitude.yaw,
            },
            'battery': {
                'voltage': self.vehicle.battery.voltage,
                'current': self.vehicle.battery.current,
                'level': self.vehicle.battery.level,
            }
        }
        return snapshot
        
    def log_telemetry(self, interval=1.0, duration=None):
        """Telemetriyi kaydet"""
        print(f"Logging telemetry for vehicle {self.vehicle_id}")
        print(f"Output file: {self.log_file}")
        
        start_time = time.time()
        
        try:
            while True:
                if duration and (time.time() - start_time) > duration:
                    break
                    
                snapshot = self.get_telemetry_snapshot()
                self.data_buffer.append(snapshot)
                
                print(f"[{snapshot['timestamp']}] "
                      f"Mode: {snapshot['mode']}, "
                      f"Alt: {snapshot['location']['alt']:.1f}m, "
                      f"Bat: {snapshot['battery']['level']:.1f}%")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\nLogging stopped by user")
        finally:
            self.save_telemetry()
            if self.vehicle:
                self.vehicle.close()
            print("Telemetry logger closed")
            
    def save_telemetry(self):
        """Telemetri verilerini dosyaya yaz"""
        try:
            with open(self.log_file, 'w') as f:
                json.dump(self.data_buffer, f, indent=2)
            print(f"Telemetry saved to {self.log_file}")
        except Exception as e:
            print(f"Error saving telemetry: {e}")

def main():
    parser = argparse.ArgumentParser(description='UAV Telemetry Logger')
    parser.add_argument('--connection', default='127.0.0.1:15550', help='Vehicle connection string')
    parser.add_argument('--vehicle-id', type=int, default=1, help='Vehicle ID')
    parser.add_argument('--output', help='Output log file')
    parser.add_argument('--interval', type=float, default=1.0, help='Logging interval (seconds)')
    parser.add_argument('--duration', type=float, help='Logging duration (seconds)')
    args = parser.parse_args()
    
    logger = TelemetryLogger(args.connection, args.output, args.vehicle_id)
    
    try:
        logger.connect()
        logger.log_telemetry(interval=args.interval, duration=args.duration)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
