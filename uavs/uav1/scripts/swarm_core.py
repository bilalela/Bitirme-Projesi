#!/usr/bin/env python3
"""
Swarm Core Module
Master UAV kontrol ve koordinasyon
"""

# Python 3.10+ uyumluluğu için
import collections.abc
collections.MutableMapping = collections.abc.MutableMapping

import enum
import math
import time

from dronekit import LocationGlobalRelative, VehicleMode, connect
import dronekit

from enemy_tracker import EnemyTracker
from task_manager import TaskManager


class MissionState(enum.Enum):
    """Swarm görev durumları."""
    IDLE = "idle"
    ARMED = "armed"
    FORMATION = "formation"
    SEARCH = "search"
    ENGAGE = "engage"
    RTB = "rtb"


class SwarmMaster:
    """Master UAV swarm kontrolü."""
    
    def __init__(self, connection_string, vehicle_id=1):
        self.connection_string = connection_string
        self.vehicle_id = vehicle_id
        self.vehicle = None
        self.slave_vehicles = {}
        self.enemy_vehicle = None
        
        # Modüler sistemler
        self.enemy_tracker = EnemyTracker()
        self.task_manager = TaskManager()
        
        # Formation offsets
        self.formation_offsets = {
            2: (-1.5, -0.8),
            3: (-1.5, 0.8),
            4: (-3.0, -0.8),
            5: (-3.0, 0.8),
        }
        
        # Mission state
        self.mission_state = MissionState.IDLE
        self.mission_active = False
        self.search_altitude = 50.0
        self.search_radius = 100.0
        
        self._formation_takeoff_mode = False
        self._tasks_assigned = False
    
    def connect(self):
        """Master araca bağlan."""
        print(f"Connecting to master vehicle: {self.connection_string}")
        try:
            self.vehicle = self._connect_with_variants(self.connection_string, timeout=30)
            print(f"Master vehicle connected: {self.vehicle.system_status}")
        except Exception as exc:
            print(f"Connection attempt failed: {exc}")
            print("Retrying with extended timeout...")
            try:
                self.vehicle = self._connect_with_variants(self.connection_string, timeout=40)
                print(f"Master vehicle connected (retry): {self.vehicle.system_status}")
            except Exception as exc2:
                print(f"Final connection attempt failed: {exc2}")
                raise
    
    def _connect_with_variants(self, conn_str, timeout=30):
        """TCP/UDP variant'larını dene."""
        variants = [conn_str]
        if not conn_str.startswith("tcp:") and not conn_str.startswith("udp:") and not conn_str.startswith("serial:"):
            variants.extend([f"tcp:{conn_str}", f"udp:{conn_str}"])
        
        last_exc = None
        for uri in variants:
            try:
                v = connect(uri, wait_ready=False, timeout=timeout, heartbeat_timeout=60)
                return v
            except Exception as e:
                last_exc = e
                print(f"Connection to {uri} failed: {e}")
                time.sleep(0.5)
        
        raise last_exc
    
    def add_slave(self, slave_id, connection_string):
        """Slave araç ekle."""
        try:
            print(f"Connecting to Slave {slave_id}...")
            slave = self._connect_with_variants(connection_string, timeout=20)
            self.slave_vehicles[slave_id] = slave
            print(f"Slave {slave_id} connected: {slave.system_status}")
        except Exception as exc:
            print(f"Failed to connect to slave {slave_id}: {exc}")
            print(f"Retrying slave {slave_id}...")
            try:
                slave = self._connect_with_variants(connection_string, timeout=15)
                self.slave_vehicles[slave_id] = slave
                print(f"Slave {slave_id} connected (retry): {slave.system_status}")
            except Exception as exc2:
                print(f"Final attempt failed for slave {slave_id}: {exc2}")
    
    def add_enemy(self, connection_string):
        """Enemy UAV ekle."""
        try:
            print(f"Connecting to Enemy UAV (UAV6)...")
            enemy = self._connect_with_variants(connection_string, timeout=20)
            self.enemy_vehicle = enemy
            self.enemy_tracker.set_enemy_vehicle(enemy)
            print(f"Enemy UAV connected: {enemy.system_status}")
        except Exception as exc:
            print(f"Failed to connect to enemy UAV: {exc}")
            print(f"Retrying enemy UAV...")
            try:
                enemy = self._connect_with_variants(connection_string, timeout=15)
                self.enemy_vehicle = enemy
                self.enemy_tracker.set_enemy_vehicle(enemy)
                print(f"Enemy UAV connected (retry): {enemy.system_status}")
            except Exception as exc2:
                print(f"Final attempt failed for enemy UAV: {exc2}")
    
    def connect_all(self):
        """Tüm araçlara bağlan."""
        self.connect()
        self.add_slave(2, "udp:127.0.0.1:15560")
        self.add_slave(3, "udp:127.0.0.1:15570")
        self.add_slave(4, "udp:127.0.0.1:15580")
        self.add_slave(5, "udp:127.0.0.1:15590")
        self.add_enemy("udp:127.0.0.1:15600")
    
    def _set_guided(self, vehicle):
        """GUIDED mode'a geç."""
        if vehicle.mode.name != "GUIDED":
            vehicle.mode = VehicleMode("GUIDED")
            time.sleep(1)
    
    def _set_armed(self, vehicle, armed=True):
        """Armed state'i ayarla."""
        try:
            vehicle.armed = armed
            timeout = time.time() + 30
            while vehicle.armed != armed and time.time() < timeout:
                try:
                    time.sleep(0.5)
                except KeyboardInterrupt:
                    print(f"Interrupted while setting armed={armed}")
                    raise
        except AttributeError:
            print(f"Vehicle connection lost while setting armed state")
            return
        except KeyboardInterrupt:
            raise
    
    def _wait_for_altitude(self, vehicle, target_altitude, tolerance=2.0, timeout=120):
        """Hedef irtifaya ulaşmayı bekle."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            current_altitude = vehicle.location.global_relative_frame.alt
            if current_altitude >= (target_altitude - tolerance):
                return True
            time.sleep(1)
        return False
    
    @staticmethod
    def _safe_altitude(vehicle):
        """Güvenli altitude döndür."""
        try:
            altitude = vehicle.location.global_relative_frame.alt
            return 0.0 if altitude is None else float(altitude)
        except Exception:
            return 0.0
    
    @staticmethod
    def _has_valid_position(vehicle):
        """Vehicle position kontrolü."""
        try:
            location = vehicle.location.global_relative_frame
            return (
                location is not None
                and location.lat is not None
                and location.lon is not None
                and location.alt is not None
            )
        except Exception:
            return False
    
    @staticmethod
    def get_location_metres(original_location, d_north, d_east, altitude=None):
        """Metre offset'i GPS coordinate'e çevir."""
        original_lat = 0.0 if original_location.lat is None else float(original_location.lat)
        original_lon = 0.0 if original_location.lon is None else float(original_location.lon)
        original_alt = 0.0 if original_location.alt is None else float(original_location.alt)
        earth_radius = 6378137.0
        d_lat = d_north / earth_radius
        d_lon = d_east / (earth_radius * math.cos(math.pi * original_lat / 180.0))
        
        new_lat = original_lat + (d_lat * 180.0 / math.pi)
        new_lon = original_lon + (d_lon * 180.0 / math.pi)
        new_alt = original_alt if altitude is None else altitude
        return LocationGlobalRelative(new_lat, new_lon, new_alt)
    
    def arm_all(self):
        """Tüm araçları GUIDED + armed yap."""
        vehicles = [(self.vehicle_id, self.vehicle)] + list(self.slave_vehicles.items())
        for vehicle_id, vehicle in vehicles:
            if vehicle is None:
                continue
            print(f"Preparing vehicle {vehicle_id}...")
            self._set_guided(vehicle)
            self._set_armed(vehicle, True)
    
    def disarm_all(self):
        """Tüm araçları silahsızlandır."""
        print("Disarming all vehicles...")
        vehicles = [self.vehicle] + list(self.slave_vehicles.values())
        if self.enemy_vehicle:
            vehicles.append(self.enemy_vehicle)
        
        for vehicle in vehicles:
            if vehicle is None:
                continue
            try:
                self._set_armed(vehicle, False)
            except (KeyboardInterrupt, AttributeError, Exception) as exc:
                print(f"Error disarming vehicle: {exc}")
                continue
    
    def takeoff_all(self, target_altitude=50.0):
        """Tüm araçları kaldır."""
        if self.vehicle is None:
            print("Master vehicle not connected")
            return
        
        self.arm_all()
        print(f"Takeoff initiated to {target_altitude} m")
        
        vehicles = [self.vehicle] + list(self.slave_vehicles.values())
        for vehicle in vehicles:
            if vehicle is None:
                continue
            try:
                vehicle.mode = VehicleMode("AUTO")
                time.sleep(0.5)
            except Exception as exc:
                print(f"Failed to switch to AUTO mode: {exc}")
        
        print("Switching to formation mode for altitude gain (fallback)...")
        self._formation_takeoff_mode = True
        self.search_altitude = target_altitude
    
    def _get_slave_offset(self, slave_id):
        """Slave offset'i döndür."""
        return self.formation_offsets.get(slave_id, (-25.0, 0.0))
    
    def _formation_step(self, altitude=None):
        """Formation adımı (enemy tracking ile)."""
        if self.vehicle is None:
            return
        
        if not self._has_valid_position(self.vehicle):
            print("[FORMATION] Skipping master: telemetry not ready")
            return
        
        # 🎯 Enemy tracking
        if self.enemy_tracker.update_position(self._has_valid_position):
            rear_positions = self.enemy_tracker.get_rear_positions(self.get_location_metres)
            self.task_manager.assign_rear_guard_tasks(
                self.slave_vehicles,
                rear_positions,
                self._has_valid_position
            )
            status = self.enemy_tracker.get_status()
            if 'formatted' in status:
                print(f"[TRACKER] {status['formatted']}")
        
        master_location = self.vehicle.location.global_relative_frame
        
        # Takeoff
        if self._formation_takeoff_mode:
            target_altitude = self.search_altitude
            current_altitude = self._safe_altitude(self.vehicle)
            
            if current_altitude < target_altitude - 2:
                increment = min(10.0, target_altitude - current_altitude)
                altitude = current_altitude + increment
                print(f"Takeoff in progress: {current_altitude:.1f}m → {target_altitude:.1f}m")
            else:
                print(f"[TAKEOFF] Reached target altitude: {current_altitude:.1f}m")
                self._formation_takeoff_mode = False
                altitude = target_altitude
        else:
            current_altitude = self._safe_altitude(self.vehicle) if altitude is None else altitude
            altitude = current_altitude
        
        # Update slave positions
        for slave_id, slave in self.slave_vehicles.items():
            if slave is None:
                continue
            if not self._has_valid_position(slave):
                continue
            north_offset, east_offset = self._get_slave_offset(slave_id)
            target_location = self.get_location_metres(
                master_location,
                north_offset,
                east_offset,
                altitude,
            )
            slave.simple_goto(target_location)
    
    def print_mission_status(self):
        """Mission durumunu göster."""
        print("\n" + "="*70)
        print(f"🎯 SWARM MISSION STATE: {self.mission_state.value.upper()}")
        print("="*70)
        
        # Master status
        if self.vehicle:
            master_loc = self.vehicle.location.global_relative_frame
            print(f"👑 MASTER (UAV1): Armed={self.vehicle.armed} | Mode={self.vehicle.mode.name}")
            if self._has_valid_position(self.vehicle):
                print(f"   Position: ({master_loc.lat:.6f}, {master_loc.lon:.6f}) | Alt: {master_loc.alt:.1f}m")
        
        # Slaves status
        print(f"\n👥 SLAVES ({len(self.slave_vehicles)} connected):")
        for slave_id, slave in self.slave_vehicles.items():
            if slave:
                slave_loc = slave.location.global_relative_frame
                print(f"   UAV{slave_id}: Armed={slave.armed} | Mode={slave.mode.name}")
                if self._has_valid_position(slave):
                    print(f"      Pos: ({slave_loc.lat:.6f}, {slave_loc.lon:.6f}) | Alt: {slave_loc.alt:.1f}m")
        
        # Enemy status
        if self.enemy_vehicle:
            print(f"\n🔴 ENEMY (UAV6): Armed={self.enemy_vehicle.armed} | Mode={self.enemy_vehicle.mode.name}")
            enemy_loc = self.enemy_vehicle.location.global_relative_frame
            if self._has_valid_position(self.enemy_vehicle):
                print(f"   Position: ({enemy_loc.lat:.6f}, {enemy_loc.lon:.6f}) | Alt: {enemy_loc.alt:.1f}m")
        
        # Enemy tracker status
        tracker_status = self.enemy_tracker.get_status()
        print(f"\n📡 ENEMY TRACKER: {'ACTIVE' if tracker_status['active'] else 'INACTIVE'}")
        if tracker_status.get('formatted'):
            print(f"   {tracker_status['formatted']}")
        
        # Task status
        task_status = self.task_manager.get_task_status()
        if task_status['active_tasks']:
            print(f"\n📋 ACTIVE TASKS:")
            for slave_id, task_info in task_status['active_tasks'].items():
                print(f"   Slave {slave_id}: {task_info['type']}")
        
        print("="*70 + "\n")
    
    def start_mission(self, altitude=None):
        """Görev başlat."""
        if altitude is None:
            altitude = self.search_altitude
        
        print(f"Starting mission at altitude {altitude} m")
        self.mission_active = True
        self.search_altitude = altitude
        
        # Enemy tracking'i başlat
        self.enemy_tracker.start_tracking()
        
        current_altitude = self._safe_altitude(self.vehicle)
        if current_altitude >= 2.0:
            print(f"Manual flight detected at {current_altitude:.1f}m, skipping takeoff phase")
            self._formation_takeoff_mode = False
        else:
            self._formation_takeoff_mode = True
        
        if self._formation_takeoff_mode:
            self.takeoff_all(altitude)
        elif not all(v and v.armed for v in [self.vehicle] + list(self.slave_vehicles.values())):
            self.arm_all()
        
        # Mission loop
        try:
            loop_count = 0
            while self.mission_active:
                loop_count += 1
                
                if self.mission_state in (MissionState.FORMATION, MissionState.ENGAGE):
                    self._formation_step(altitude)
                    
                    if self._formation_takeoff_mode:
                        master_alt = self._safe_altitude(self.vehicle)
                        if master_alt < altitude - 2:
                            target_alt = min(master_alt + 10.0, altitude)
                            if self._has_valid_position(self.vehicle):
                                target_loc = self.get_location_metres(
                                    self.vehicle.location.global_relative_frame,
                                    0, 0,
                                    target_alt
                                )
                                self.vehicle.simple_goto(target_loc)
                    
                    if loop_count % 5 == 0:
                        master_loc = self.vehicle.location.global_relative_frame
                        print(f"[FORMATION] Master alt: {master_loc.alt:.1f}m")
                    
                    time.sleep(2)
                else:
                    time.sleep(1)
        
        except KeyboardInterrupt:
            print("\nMission interrupted")
        finally:
            self.mission_active = False
            self.enemy_tracker.stop_tracking()
    
    def stop_mission(self):
        """Görev durdur."""
        print("Stopping mission")
        self.mission_active = False
        self.mission_state = MissionState.RTB
        self.enemy_tracker.stop_tracking()
        self.disarm_all()
    
    def close(self):
        """Bağlantıları kapat."""
        if self.vehicle:
            self.vehicle.close()
        for slave in self.slave_vehicles.values():
            if slave:
                slave.close()
        if self.enemy_vehicle:
            self.enemy_vehicle.close()
