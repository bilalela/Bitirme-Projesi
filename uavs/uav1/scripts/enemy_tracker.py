#!/usr/bin/env python3
"""
Enemy Tracker Module
Enemy UAV konumunu sürekli takip eder ve günceller
"""

import time
from dronekit import LocationGlobalRelative


class EnemyTracker:
    """Enemy UAV konumunu izler ve takip görevlerini yönetir."""
    
    def __init__(self):
        self.enemy_vehicle = None
        self.enemy_position = None
        self.last_update = 0
        self.update_interval = 1.0  # 1 saniyede bir güncelle
        self.is_active = False
    
    def set_enemy_vehicle(self, vehicle):
        """Enemy aracını ayarla."""
        self.enemy_vehicle = vehicle
    
    def start_tracking(self):
        """Enemy tracking'i başlat."""
        self.is_active = True
        print("[TRACKER] Enemy tracking activated")
    
    def stop_tracking(self):
        """Enemy tracking'i durdur."""
        self.is_active = False
        print("[TRACKER] Enemy tracking deactivated")
    
    def update_position(self, has_valid_position_func):
        """Enemy pozisyonunu güncelle.
        
        Args:
            has_valid_position_func: vehicle position'ı kontrol eden function
        
        Returns:
            bool: Update başarılı mı?
        """
        if not self.is_active or not self.enemy_vehicle:
            return False
        
        current_time = time.time()
        if current_time - self.last_update < self.update_interval:
            return False  # Henüz update zamanı değil
        
        if not has_valid_position_func(self.enemy_vehicle):
            return False
        
        try:
            enemy_loc = self.enemy_vehicle.location.global_relative_frame
            self.enemy_position = {
                'lat': enemy_loc.lat,
                'lon': enemy_loc.lon,
                'alt': enemy_loc.alt,
                'timestamp': current_time
            }
            self.last_update = current_time
            return True
        except Exception as e:
            print(f"[TRACKER] Position update failed: {e}")
            return False
    
    def get_rear_positions(self, get_location_metres_func, rear_distance=20, side_distance=8):
        """Enemy'nin arkasında 2 pozisyon hesapla (left ve right).
        
        Args:
            get_location_metres_func: Coordinate conversion function
            rear_distance: Enemy'nin ne kadar arkası (metre)
            side_distance: Sol/sağ offset (metre)
        
        Returns:
            tuple: (rear_left_location, rear_right_location) veya (None, None)
        """
        if not self.enemy_position:
            return None, None
        
        enemy_lat = self.enemy_position['lat']
        enemy_lon = self.enemy_position['lon']
        enemy_alt = self.enemy_position['alt']
        
        enemy_loc = LocationGlobalRelative(enemy_lat, enemy_lon, enemy_alt)
        
        rear_left = get_location_metres_func(
            enemy_loc,
            -rear_distance,   # 20m behind (south)
            -side_distance,   # 8m west
            enemy_alt
        )
        rear_right = get_location_metres_func(
            enemy_loc,
            -rear_distance,   # 20m behind (south)
            side_distance,    # 8m east
            enemy_alt
        )
        
        return rear_left, rear_right
    
    def get_status(self):
        """Tracker durumunu döndür."""
        status = {
            'active': self.is_active,
            'position': self.enemy_position,
            'last_update': self.last_update
        }
        if self.enemy_position:
            status['formatted'] = (
                f"Enemy: ({self.enemy_position['lat']:.6f}, {self.enemy_position['lon']:.6f}) "
                f"alt={self.enemy_position['alt']:.1f}m"
            )
        return status
