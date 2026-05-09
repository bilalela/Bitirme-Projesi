#!/usr/bin/env python3
"""
Swarm Master Controller
Master UAV (UAV1) swarm kontrolü ve koordinasyon
"""

# Python 3.10+ uyumluluğu için
import collections.abc
collections.MutableMapping = collections.abc.MutableMapping

import argparse
import enum
import math
import signal
import sys
import threading
import time

from dronekit import LocationGlobalRelative, VehicleMode, connect
import dronekit


class TargetDetector:
    """Basit hedef dedektörü (placeholder)."""
    def __init__(self, vehicle_id=3):
        self.vehicle_id = vehicle_id
        self.targets = []

    def detect_in_frame(self, frame):
        """Frame'de hedef tespiti (placeholder)."""
        # Gerçek uygulamada OpenCV ile renk tespiti yapılacak
        return None

    def get_latest_target(self):
        """Son tespit edilen hedefi döndür."""
        return self.targets[-1] if self.targets else None


class MissionState(enum.Enum):
    """Swarm görev durumları."""
    IDLE = "idle"
    ARMED = "armed"
    FORMATION = "formation"
    SEARCH = "search"
    ENGAGE = "engage"
    RTB = "rtb"


class SwarmMaster:
    def __init__(self, connection_string, vehicle_id=1):
        self.connection_string = connection_string
        self.vehicle_id = vehicle_id
        self.vehicle = None
        self.slave_vehicles = {}
        self.enemy_vehicle = None  # Enemy UAV6
        self.formation_offsets = {
            2: (-4.0, -2.0),   # Sol arka (artırılmış mesafe)
            3: (-4.0, 2.0),    # Sağ arka (artırılmış mesafe)
            4: (-6.0, -2.0),   # Daha arka sol (artırılmış mesafe)
            5: (-6.0, 2.0),    # Daha arka sağ (artırılmış mesafe)
        }
        # Task assignments for slaves
        self.slave_tasks = {
            2: "REAR_GUARD_LEFT",    # Slave 2: Enemy'nin sol arkası
            3: "REAR_GUARD_RIGHT",   # Slave 3: Enemy'nin sağ arkası
            4: "FLANK_LEFT",         # Slave 4: Sol flanş
            5: "FLANK_RIGHT",        # Slave 5: Sağ flanş
        }
        # Enemy tracking
        self.enemy_position = None
        self.enemy_tracking_active = False
        self.last_enemy_update = 0
        # Mission state
        self.mission_state = MissionState.IDLE
        self.target_data = None
        self.mission_active = False
        self.search_altitude = 50.0
        self.search_radius = 100.0
        # Target detector
        self.target_detector = TargetDetector(vehicle_id=3)
        self._formation_takeoff_mode = False
        self._tasks_assigned = False  # Guard flag to prevent infinite task assignment

    def connect(self):
        """Master araca baglan."""
        print(f"Connecting to master vehicle: {self.connection_string}")
        try:
            # Connect with minimal wait (try variants if plain string fails)
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
        """Try connecting using several common DroneKit URI variants.

        Returns the connected vehicle or raises the last exception.
        """
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
        """Slave araci ekle."""
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
                # Don't raise - allow mission to continue with fewer slaves if needed

    def add_enemy(self, connection_string):
        """Enemy UAV6 (hedef olarak) ekle."""
        try:
            print(f"Connecting to Enemy UAV (UAV6)...")
            enemy = self._connect_with_variants(connection_string, timeout=20)
            self.enemy_vehicle = enemy
            print(f"Enemy UAV connected: {enemy.system_status}")
        except Exception as exc:
            print(f"Failed to connect to enemy UAV: {exc}")
            print(f"Retrying enemy UAV...")
            try:
                enemy = self._connect_with_variants(connection_string, timeout=15)
                self.enemy_vehicle = enemy
                print(f"Enemy UAV connected (retry): {enemy.system_status}")
            except Exception as exc2:
                print(f"Final attempt failed for enemy UAV: {exc2}")
                # Enemy is optional - allow mission to continue

    def _set_guided(self, vehicle):
        if vehicle.mode.name != "GUIDED":
            vehicle.mode = VehicleMode("GUIDED")
            time.sleep(1)

    def _set_armed(self, vehicle, armed=True):
        """Set armed state with timeout and exception handling."""
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
        start_time = time.time()
        while time.time() - start_time < timeout:
            current_altitude = vehicle.location.global_relative_frame.alt
            if current_altitude >= (target_altitude - tolerance):
                return True
            time.sleep(1)
        return False

    @staticmethod
    def _safe_altitude(vehicle):
        """Return a numeric altitude even if telemetry is not ready yet."""
        try:
            altitude = vehicle.location.global_relative_frame.alt
            return 0.0 if altitude is None else float(altitude)
        except Exception:
            return 0.0

    @staticmethod
    def _has_valid_position(vehicle):
        """Check whether a vehicle has usable lat/lon/alt telemetry."""
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
        """Yerel metre cinsinden ofseti GPS koordinatina cevir."""
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

    def connect_all(self):
        self.connect()
        self.add_slave(2, "127.0.0.1:15560")
        self.add_slave(3, "127.0.0.1:15570")
        self.add_slave(4, "127.0.0.1:15580")
        self.add_slave(5, "127.0.0.1:15590")
        self.add_enemy("127.0.0.1:15600")  # Enemy UAV6

    def arm_all(self):
        """Tüm araçları GUIDED + armed durumuna al."""
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
        """Tüm araçları aynı irtifaya kaldır."""
        if self.vehicle is None:
            print("Master vehicle not connected")
            return

        self.arm_all()
        print(f"Takeoff initiated to {target_altitude} m")
        print("Using AUTO mode for reliable takeoff in ArduPlane SITL...")
        
        # Try AUTO mode first (most reliable for ArduPlane takeoff)
        vehicles = [self.vehicle] + list(self.slave_vehicles.values())
        for vehicle in vehicles:
            if vehicle is None:
                continue
            try:
                # Switch to AUTO mode for takeoff
                vehicle.mode = VehicleMode("AUTO")
                time.sleep(0.5)
            except Exception as exc:
                print(f"Failed to switch to AUTO mode for vehicle: {exc}")
        
        # Fallback: use formation mode
        print("Switching to formation mode for altitude gain (fallback)...")
        self._formation_takeoff_mode = True
        self.search_altitude = target_altitude

    def _get_slave_offset(self, slave_id):
        return self.formation_offsets.get(slave_id, (-25.0, 0.0))

    def hold_formation(self, duration=None, update_interval=2.0, altitude=None):
        """Master konumuna göre sabit formation sürdür."""
        if self.vehicle is None:
            print("Master vehicle not connected")
            return

        print("Formation mode started")
        start_time = time.time()

        while self.mission_active:
            if duration is not None and (time.time() - start_time) > duration:
                break

            master_location = self.vehicle.location.global_relative_frame
            current_altitude = master_location.alt if altitude is None else altitude

            for slave_id, slave in self.slave_vehicles.items():
                if slave is None:
                    continue
                north_offset, east_offset = self._get_slave_offset(slave_id)
                target_location = self.get_location_metres(
                    master_location,
                    north_offset,
                    east_offset,
                    current_altitude,
                )
                slave.simple_goto(target_location)

            print(
                f"Master: lat={master_location.lat:.6f} lon={master_location.lon:.6f} alt={master_location.alt:.1f}"
            )
            for slave_id, slave in self.slave_vehicles.items():
                loc = slave.location.global_relative_frame
                print(f"  Slave {slave_id}: lat={loc.lat:.6f} lon={loc.lon:.6f} alt={loc.alt:.1f}")

            time.sleep(update_interval)

    def fire_missile(self, vehicle_id=None, hardpoint="port"):
        """Füze at komutu için yer tutucu."""
        if vehicle_id is None or vehicle_id == self.vehicle_id:
            target = self.vehicle
        else:
            target = self.slave_vehicles.get(vehicle_id)

        if target is None:
            print(f"Vehicle {vehicle_id} not found!")
            return False

        print(f"Missile fire command sent to vehicle {vehicle_id} hardpoint {hardpoint}")
        return True

    def print_mission_status(self):
        """Detaylı mission durumu göster."""
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
                task = self.slave_tasks.get(slave_id, "UNKNOWN")
                slave_loc = slave.location.global_relative_frame
                print(f"   UAV{slave_id}: Armed={slave.armed} | Mode={slave.mode.name} | Task={task}")
                if self._has_valid_position(slave):
                    print(f"      Pos: ({slave_loc.lat:.6f}, {slave_loc.lon:.6f}) | Alt: {slave_loc.alt:.1f}m")
        
        # Enemy status
        if self.enemy_vehicle:
            print(f"\n🔴 ENEMY (UAV6): Armed={self.enemy_vehicle.armed} | Mode={self.enemy_vehicle.mode.name}")
            enemy_loc = self.enemy_vehicle.location.global_relative_frame
            if self._has_valid_position(self.enemy_vehicle):
                print(f"   Position: ({enemy_loc.lat:.6f}, {enemy_loc.lon:.6f}) | Alt: {enemy_loc.alt:.1f}m")
        
        # Mission state details
        print(f"\n📊 MISSION STATE DETAILS:")
        if self.mission_state == MissionState.IDLE:
            print("   Status: Waiting for mission start command")
        elif self.mission_state == MissionState.ARMED:
            armed_count = sum(1 for v in [self.vehicle] + list(self.slave_vehicles.values()) if v and v.armed)
            total = len(self.slave_vehicles) + 1
            print(f"   Status: Arming all vehicles... ({armed_count}/{total})")
        elif self.mission_state == MissionState.FORMATION:
            print("   Status: Formation flight - Master leads, Slaves follow")
            if self.vehicle:
                alt = self._safe_altitude(self.vehicle)
                print(f"   Altitude: {alt:.1f}m / Target: {self.search_altitude:.1f}m")
        elif self.mission_state == MissionState.SEARCH:
            print("   Status: Searching for target...")
            if self.target_data:
                print(f"   Last target: ({self.target_data['lat']:.6f}, {self.target_data['lon']:.6f})")
        elif self.mission_state == MissionState.ENGAGE:
            print("   Status: 🔥 ENGAGING TARGET!")
            if self.target_data:
                print(f"   🎯 Target: ({self.target_data['lat']:.6f}, {self.target_data['lon']:.6f})")
                print(f"   Confidence: {self.target_data.get('confidence', 'N/A')}")
            print("   Task assignments:")
            for slave_id, task in self.slave_tasks.items():
                print(f"      - Slave {slave_id}: {task}")
        elif self.mission_state == MissionState.RTB:
            print("   Status: Returning to base")
        
        print("="*70 + "\n")

    def _detect_targets(self):
        """Hedef tespiti yap."""
        # Gerçek uygulamada camera frame'i alınacak
        # Şu anda simülasyon için 10 saniyelik bir delay ile manuel hedef simülasyonu
        if not hasattr(self, '_search_start_time') or self._search_start_time is None:
            self._search_start_time = time.time()

        elapsed = time.time() - self._search_start_time
        if elapsed > 10:  # 10 saniye sonra hedef tespit et
            print("Simulated target detected!")
            self._search_start_time = None
            master_location = self.vehicle.location.global_relative_frame if self.vehicle else None
            if master_location is None:
                return None
            master_lat = master_location.lat if master_location.lat is not None else 0.0
            master_lon = master_location.lon if master_location.lon is not None else 0.0
            return {
                'lat': master_lat + 0.0001,
                'lon': master_lon + 0.0001,
                'confidence': 0.95
            }
        return None

    def _update_enemy_position(self):
        """Enemy UAV6 konumunu sürekli oku ve update et."""
        if not self.enemy_vehicle or not self._has_valid_position(self.enemy_vehicle):
            return False
        
        try:
            enemy_loc = self.enemy_vehicle.location.global_relative_frame
            self.enemy_position = {
                'lat': enemy_loc.lat,
                'lon': enemy_loc.lon,
                'alt': enemy_loc.alt
            }
            self.last_enemy_update = time.time()
            return True
        except Exception as e:
            print(f"[WARNING] Enemy position update failed: {e}")
            return False

    def _assign_rear_guard_tasks(self):
        """Slave 2 ve 3'e enemy'nin 20m arkasına gitme görevini ata."""
        if not self.enemy_position or not self.slave_vehicles:
            return
        
        enemy_lat = self.enemy_position['lat']
        enemy_lon = self.enemy_position['lon']
        enemy_alt = self.enemy_position.get('alt', 50)
        
        # Enemy'nin 20m arkasını hesapla (south direction)
        # 20 metre south = -20 north offset
        rear_left_loc = self.get_location_metres(
            LocationGlobalRelative(enemy_lat, enemy_lon, enemy_alt),
            -20,  # 20m behind (south)
            -8,   # 8m west (left)
            enemy_alt
        )
        rear_right_loc = self.get_location_metres(
            LocationGlobalRelative(enemy_lat, enemy_lon, enemy_alt),
            -20,  # 20m behind (south)
            8,    # 8m east (right)
            enemy_alt
        )
        
        # Slave 2 -> rear left, Slave 3 -> rear right
        for slave_id in [2, 3]:
            slave = self.slave_vehicles.get(slave_id)
            if slave and self._has_valid_position(slave):
                target_loc = rear_left_loc if slave_id == 2 else rear_right_loc
                print(f"[ENEMY_TRACK] Slave {slave_id} → Enemy rear ({target_loc.lat:.6f}, {target_loc.lon:.6f}) alt={target_loc.alt:.1f}m")
                slave.simple_goto(target_loc)

    def track_enemy_slave2(self):
        """Slave 2'yi enemy'nin 20m arkasında sürekli takip etmesini sağla."""
        if not self.enemy_vehicle or not self.slave_vehicles.get(2):
            print("❌ Enemy vehicle veya Slave 2 bağlı değil")
            return
        
        slave2 = self.slave_vehicles.get(2)
        print("🎯 Slave 2 enemy tracking başlatıldı (20m arkada tutulacak)")
        self.enemy_tracking_active = True
        
        try:
            tracking_count = 0
            while self.enemy_tracking_active:
                if not self._has_valid_position(self.enemy_vehicle) or not self._has_valid_position(slave2):
                    time.sleep(1)
                    continue
                
                # Enemy konumunu al
                enemy_loc = self.enemy_vehicle.location.global_relative_frame
                enemy_alt = enemy_loc.alt if enemy_loc.alt else 50
                
                # Slave 2'nin 20m arkasında takip etmesi için hedef konum
                # Enemy'nin arkasında (-20m north)
                target_loc = self.get_location_metres(
                    LocationGlobalRelative(enemy_loc.lat, enemy_loc.lon, enemy_alt),
                    -20,  # 20m behind
                    0,    # Center (no left/right offset)
                    enemy_alt
                )
                
                # Slave 2'ye komut gönder
                slave2.simple_goto(target_loc)
                
                tracking_count += 1
                if tracking_count % 5 == 0:
                    distance = self._calculate_distance(
                        slave2.location.global_relative_frame.lat,
                        slave2.location.global_relative_frame.lon,
                        enemy_loc.lat,
                        enemy_loc.lon
                    )
                    print(f"[SLAVE2_TRACK] Enemy: ({enemy_loc.lat:.6f}, {enemy_loc.lon:.6f}) | Slave2 distance: {distance:.1f}m")
                
                time.sleep(2)  # 2 saniyede bir güncelle
        
        except KeyboardInterrupt:
            print("\n🛑 Slave 2 tracking durduruldu")
        except Exception as exc:
            print(f"❌ Tracking hatası: {exc}")
        finally:
            self.enemy_tracking_active = False

    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """İki GPS noktası arasındaki mesafeyi metre cinsinden hesapla (Haversine)."""
        earth_radius = 6378137.0
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = earth_radius * c
        return distance

    def _assign_tasks(self):
        """Slave'lere görev ata (only once per ENGAGE state)."""
        if not self.slave_vehicles or self.mission_state != MissionState.ENGAGE:
            return
        
        # Only assign tasks once when entering ENGAGE state
        if self._tasks_assigned:
            return
        
        self._tasks_assigned = True
        for slave_id, slave in self.slave_vehicles.items():
            task = self.slave_tasks.get(slave_id, "FORMATION_HOLD")
            target_lat = self.target_data['lat'] if self.target_data else 0.0
            target_lon = self.target_data['lon'] if self.target_data else 0.0
            
            print(f"\n🎯 [TASK] Assigning task to Slave {slave_id}")
            print(f"   Task: {task}")
            print(f"   Target: lat={target_lat:.6f}, lon={target_lon:.6f}")
            
            if task == "FOLLOW_TARGET":
                print(f"   → Slave {slave_id} will directly follow the target")
                if self._has_valid_position(slave):
                    target_loc = self.get_location_metres(
                        LocationGlobalRelative(target_lat, target_lon, 50),
                        0, 0, 50
                    )
                    slave.simple_goto(target_loc)
                    
            elif task == "FLANK_LEFT":
                print(f"   → Slave {slave_id} will take left flank position")
                if self._has_valid_position(slave):
                    target_loc = self.get_location_metres(
                        LocationGlobalRelative(target_lat, target_lon, 50),
                        -5, -20, 50  # 5m north, 20m west of target
                    )
                    slave.simple_goto(target_loc)
                    
            elif task == "FLANK_RIGHT":
                print(f"   → Slave {slave_id} will take right flank position")
                if self._has_valid_position(slave):
                    target_loc = self.get_location_metres(
                        LocationGlobalRelative(target_lat, target_lon, 50),
                        -5, 20, 50  # 5m north, 20m east of target
                    )
                    slave.simple_goto(target_loc)
                    
            elif task == "REAR_GUARD":
                print(f"   → Slave {slave_id} will maintain rear guard position")
                if self._has_valid_position(slave):
                    target_loc = self.get_location_metres(
                        LocationGlobalRelative(target_lat, target_lon, 50),
                        -30, 0, 50  # 30m south of target
                    )
                    slave.simple_goto(target_loc)

    def _update_mission_state(self):
        """Mission durumunu güncelle."""
        if not self.mission_active:
            self.mission_state = MissionState.IDLE
            self._tasks_assigned = False
            return

        # Duruma göre geçiş yap
        if self.mission_state == MissionState.IDLE:
            print("[STATE] IDLE → ARMED")
            self.mission_state = MissionState.ARMED

        elif self.mission_state == MissionState.ARMED:
            if all(v.armed for v in [self.vehicle] + list(self.slave_vehicles.values())):
                print("[STATE] ARMED → FORMATION")
                self.mission_state = MissionState.FORMATION
                self._search_start_time = None  # Reset search timer

        elif self.mission_state == MissionState.FORMATION:
            # Hedef arayı başlat
            detected = self._detect_targets()
            if detected:
                self.target_data = detected
                print(f"[STATE] FORMATION → SEARCH (target detected at {detected['lat']:.6f}, {detected['lon']:.6f})")
                self.mission_state = MissionState.ENGAGE
                print(f"[STATE] SEARCH → ENGAGE")
                self._tasks_assigned = False  # Reset task assignment flag for new ENGAGE state

        elif self.mission_state == MissionState.ENGAGE:
            self._assign_tasks()  # Will only run once due to _tasks_assigned guard
            # Görevi tamamladıktan sonra RTB'ye geç
            # Burada bir zaman çıkışı veya hedef çıkışı eklenebilir
            # Şimdilik manuel olarak stop_mission() ile durdurulur

    def _formation_step(self, altitude=None):
        """Formation'un bir adımını yap (sonsuz döngü olmadan)."""
        if self.vehicle is None:
            return

        if not self._has_valid_position(self.vehicle):
            print("[FORMATION] Skipping master: telemetry not ready")
            return

        # 🎯 ENEMY TRACKING: Update enemy position continuously
        if self.enemy_vehicle and self.enemy_tracking_active:
            self._update_enemy_position()
            if self.enemy_position:
                # Assign rear guard tasks for slave 2 and 3
                self._assign_rear_guard_tasks()

        master_location = self.vehicle.location.global_relative_frame
        
        # Takeoff modunda mı? O zaman yükselt
        if self._formation_takeoff_mode:
            target_altitude = self.search_altitude
            current_altitude = self._safe_altitude(self.vehicle)
            
            if current_altitude < target_altitude - 2:
                # Henüz yeterince yükselmedi, yukarı git (aggressive: 10m steps)
                increment = min(10.0, target_altitude - current_altitude)
                altitude = current_altitude + increment
                print(f"Takeoff in progress: {current_altitude:.1f}m → {target_altitude:.1f}m (increment: {increment:.1f}m)")
            else:
                # Hedef irtifaya ulaştı
                print(f"[TAKEOFF] Reached target altitude: {current_altitude:.1f}m")
                self._formation_takeoff_mode = False
                altitude = target_altitude
        else:
            current_altitude = self._safe_altitude(self.vehicle) if altitude is None else altitude
            altitude = current_altitude

        # Update all slave positions relative to master
        for slave_id, slave in self.slave_vehicles.items():
            if slave is None:
                continue
            if not self._has_valid_position(slave):
                print(f"[FORMATION] Skipping Slave {slave_id}: telemetry not ready")
                continue
            north_offset, east_offset = self._get_slave_offset(slave_id)
            target_location = self.get_location_metres(
                master_location,
                north_offset,
                east_offset,
                altitude,
            )
            slave.simple_goto(target_location)

    def start_mission(self, altitude=None):
        """Görev başlat."""
        if altitude is None:
            altitude = self.search_altitude

        print(f"Starting mission at altitude {altitude} m")
        self.mission_active = True
        self.search_altitude = altitude

        current_altitude = self._safe_altitude(self.vehicle)
        if current_altitude >= 2.0:
            print(f"Manual flight detected at {current_altitude:.1f}m, skipping takeoff phase")
            self._formation_takeoff_mode = False
        else:
            self._formation_takeoff_mode = True

        # Manuel uçuşta tekrar arm/takeoff göndermiyoruz.
        if self._formation_takeoff_mode:
            self.takeoff_all(altitude)
        elif not all(v and v.armed for v in [self.vehicle] + list(self.slave_vehicles.values())):
            self.arm_all()

        # Mission loop
        try:
            loop_count = 0
            while self.mission_active:
                self._update_mission_state()
                loop_count += 1

                if self.mission_state in (MissionState.FORMATION, MissionState.ENGAGE):
                    # Hem FORMATION hem ENGAGE durumunda master'ı takip et.
                    self._formation_step(altitude)

                    # Master'ı manuel olarak yukarı al (takeoff modu)
                    if self._formation_takeoff_mode:
                        master_alt = self._safe_altitude(self.vehicle)
                        if master_alt < altitude - 2:
                            # Aggressive altitude gain
                            target_alt = min(master_alt + 10.0, altitude)
                            if self._has_valid_position(self.vehicle):
                                target_loc = self.get_location_metres(
                                    self.vehicle.location.global_relative_frame,
                                    0, 0,
                                    target_alt
                                )
                                self.vehicle.simple_goto(target_loc)

                    # Log formation status every 5 iterations
                    if loop_count % 5 == 0:
                        master_loc = self.vehicle.location.global_relative_frame
                        print(f"[FORMATION] Master alt: {master_loc.alt:.1f}m / Slaves in formation")

                    # ENGAGE hedef log'u periyodik kalsın
                    if self.mission_state == MissionState.ENGAGE and loop_count % 10 == 0:
                        if self.target_data:
                            print(f"[ENGAGE] Target: ({self.target_data['lat']:.6f}, {self.target_data['lon']:.6f})")

                    time.sleep(2)  # 2 saniye bekle
                else:
                    time.sleep(1)

        except KeyboardInterrupt:
            print("\nMission interrupted")
        finally:
            self.mission_active = False

    def stop_mission(self):
        """Görev durdur (motor açık kalır, slave'ler master takip etmeye devam eder)."""
        print("Stopping mission")
        self.mission_active = False
        self.mission_state = MissionState.IDLE
        # NOT: disarm_all() çağırma - slave'ler master'ı takip etmeye devam etsin


    def start_formation_hold(self, duration=None):
        """Slave'ler master'ı takip etmeye devam et (armed kalır)."""
        print("Formation hold mode - slaves following master")
        self.hold_formation(duration=duration, altitude=None)

    def close(self):
        """Bağlantıları kapat."""
        if self.vehicle:
            self.vehicle.close()
        for slave in self.slave_vehicles.values():
            if slave:
                slave.close()
        if self.enemy_vehicle:
            self.enemy_vehicle.close()


def signal_handler(sig, frame):
    """Ctrl+C handler - graceful shutdown"""
    print("\n[SIGNAL] Ctrl+C detected - stopping mission...")
    # Signal handler will let KeyboardInterrupt be raised
    raise KeyboardInterrupt()

def main():
    # Setup signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    parser = argparse.ArgumentParser(description="Swarm Master Controller")
    parser.add_argument("--master", default="127.0.0.1:15550", help="Master vehicle connection")
    parser.add_argument("--slave1", default="127.0.0.1:15560", help="Slave 1 connection")
    parser.add_argument("--slave2", default="127.0.0.1:15570", help="Slave 2 connection")
    parser.add_argument("--slave3", default="127.0.0.1:15580", help="Slave 3 connection")
    parser.add_argument("--slave4", default="127.0.0.1:15590", help="Slave 4 connection")
    parser.add_argument("--enemy", default="127.0.0.1:15600", help="Enemy UAV connection")
    parser.add_argument("--takeoff-altitude", type=float, default=50.0, help="Formation takeoff altitude")
    parser.add_argument("--formation-duration", type=float, help="Optional formation runtime in seconds")
    args = parser.parse_args()

    master = SwarmMaster(args.master)

    try:
        master.connect()
        master.add_slave(2, args.slave1)
        master.add_slave(3, args.slave2)
        master.add_slave(4, args.slave3)
        master.add_slave(5, args.slave4)
        master.add_enemy(args.enemy)  # Connect to enemy UAV

        print("\n" + "="*70)
        print("👑 SWARM MASTER CONTROLLER AKTIF")
        print("="*70)
        print("\nKomutlar:")
        print("  arm                    - Tüm araçları GUIDED + armed yap")
        print("  takeoff                - Tüm araçları belirtilen irtifaya kaldır")
        print("  hold                   - Slave'ler master'ı takip etsin (armed kalır)")
        print("  mission start          - Swarm görevini başlat (formation → search → engage)")
        print("  mission stop           - Görev durdur (motor açık)")
        print("  mission status         - Detaylı görev durumunu göster")
        print("  enemy_track on         - Slave 2'yi enemy'nin 20m arkasında takip et")
        print("  enemy_track off        - Enemy tracking'i durdur")
        print("  disarm                 - Tüm araçları disarm et")
        print("  status                 - Araç durumlarını göster")
        print("  fire <slave>           - Füze atış komutu gönder")
        print("  exit                   - Çık")
        print("="*70 + "\n")

        while True:
            try:
                cmd = input(">>> ").strip().lower()

                if cmd == "exit":
                    break
                if cmd == "arm":
                    master.arm_all()
                elif cmd == "takeoff":
                    master.takeoff_all(args.takeoff_altitude)
                elif cmd == "mission start":
                    print("Mission starting...")
                    # Background thread'de çalıştır (blocking olmaz)
                    mission_thread = threading.Thread(target=master.start_mission, args=(args.takeoff_altitude,), daemon=True)
                    mission_thread.start()
                elif cmd == "mission stop":
                    master.stop_mission()
                elif cmd == "hold":
                    print("Formation hold starting...")
                    # Background thread'de çalıştır
                    hold_thread = threading.Thread(target=master.start_formation_hold, daemon=True)
                    hold_thread.start()
                elif cmd == "mission status":
                    master.print_mission_status()
                elif cmd == "enemy_track on":
                    print("Enemy tracking başlatılıyor...")
                    # Background thread'de çalıştır (blocking olmaz)
                    tracking_thread = threading.Thread(target=master.track_enemy_slave2, daemon=True)
                    tracking_thread.start()
                elif cmd == "enemy_track off":
                    print("Enemy tracking durdurulması istendi...")
                    master.enemy_tracking_active = False
                elif cmd == "disarm":
                    master.disarm_all()
                elif cmd == "status":
                    master.status()
                elif cmd.startswith("fire"):
                    parts = cmd.split()
                    if len(parts) >= 2:
                        vehicle_id = int(parts[1]) if parts[1].isdigit() else 1
                        hardpoint = parts[2] if len(parts) > 2 else "port"
                        master.fire_missile(vehicle_id, hardpoint)
                    else:
                        print("Usage: fire <vehicle> <hardpoint>")
                elif cmd:
                    print("Bilinmeyen komut")

            except KeyboardInterrupt:
                print("\n[SIGNAL] Mission stopped - Formation hold starting...")
                master.stop_mission()
                # Background thread'de hold başlat (slave'ler master takip etsin)
                hold_thread = threading.Thread(target=master.start_formation_hold, daemon=True)
                hold_thread.start()
                continue  # ← Input loop devam et!
            except dronekit.APIException as exc:
                print(f"[ERROR] Drone API error: {exc}")
                print("[INFO] Check SITL/Gazebo connection status")
                continue
            except Exception as exc:
                print(f"[ERROR] Unexpected error: {exc}")
                continue

    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Main thread interrupted")
    except Exception as exc:
        print(f"[CRITICAL] Fatal error: {exc}")
    finally:
        print("[SHUTDOWN] Cleaning up connections...")
        try:
            master.disarm_all()
        except Exception as exc:
            print(f"[WARNING] Error during disarm cleanup: {exc}")
        try:
            master.close()
        except Exception as exc:
            print(f"[WARNING] Error closing connections: {exc}")
        print("[SHUTDOWN] Swarm Master Controller kapatıldı")


if __name__ == "__main__":
    main()
