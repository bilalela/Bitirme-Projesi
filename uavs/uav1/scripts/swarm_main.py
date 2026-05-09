#!/usr/bin/env python3
"""
Swarm Master Controller - Main Entry Point
Master UAV swarm kontrolü ve koordinasyon
Modüler mimarisi ile genişletilebilir
"""

# Python 3.10+ uyumluluğu için
import collections.abc
collections.MutableMapping = collections.abc.MutableMapping

import argparse
import sys
import time

from swarm_core import SwarmMaster, MissionState


def main():
    parser = argparse.ArgumentParser(description="Swarm Master Controller")
    parser.add_argument("--master", default="udp:127.0.0.1:15550", help="Master vehicle connection")
    parser.add_argument("--slave1", default="udp:127.0.0.1:15560", help="Slave 1 connection")
    parser.add_argument("--slave2", default="udp:127.0.0.1:15570", help="Slave 2 connection")
    parser.add_argument("--slave3", default="udp:127.0.0.1:15580", help="Slave 3 connection")
    parser.add_argument("--slave4", default="udp:127.0.0.1:15590", help="Slave 4 connection")
    parser.add_argument("--enemy", default="udp:127.0.0.1:15600", help="Enemy UAV connection")
    parser.add_argument("--takeoff-altitude", type=float, default=50.0, help="Formation takeoff altitude")
    args = parser.parse_args()

    master = SwarmMaster(args.master)

    try:
        master.connect()
        master.add_slave(2, args.slave1)
        master.add_slave(3, args.slave2)
        master.add_slave(4, args.slave3)
        master.add_slave(5, args.slave4)
        master.add_enemy(args.enemy)

        print("\n" + "="*70)
        print("👑 SWARM MASTER CONTROLLER AKTIF (Modüler Sistem)")
        print("="*70)
        print("\nModüller:")
        print("  • enemy_tracker.py - Enemy UAV konumunu takip et")
        print("  • task_manager.py - Slave görevlerini yönet")
        print("  • swarm_core.py - Master kontrol ve koordinasyon")
        print("\nKomutlar:")
        print("  arm                    - Tüm araçları GUIDED + armed yap")
        print("  takeoff                - Tüm araçları belirtilen irtifaya kaldır")
        print("  mission start          - Swarm görevini başlat (formation → search → engage)")
        print("  mission stop           - Görev durdur ve eve dön")
        print("  mission status         - Detaylı görev durumunu göster")
        print("  status                 - Araç durumlarını göster")
        print("  tracker start          - Enemy tracking'i başlat")
        print("  tracker stop           - Enemy tracking'i durdur")
        print("  tracker status         - Enemy tracker durumunu göster")
        print("  exit                   - Çık")
        print("="*70 + "\n")

        while True:
            try:
                cmd = input(">>> ").strip().lower()

                if cmd == "exit":
                    break
                
                elif cmd == "arm":
                    master.arm_all()
                
                elif cmd == "takeoff":
                    master.takeoff_all(args.takeoff_altitude)
                
                elif cmd == "mission start":
                    print("Mission starting...")
                    master.mission_state = MissionState.FORMATION
                    master.start_mission(args.takeoff_altitude)
                
                elif cmd == "mission stop":
                    master.stop_mission()
                
                elif cmd == "mission status":
                    master.print_mission_status()
                
                elif cmd == "status":
                    master.print_mission_status()
                
                elif cmd == "tracker start":
                    master.enemy_tracker.start_tracking()
                    print("[CLI] Enemy tracking started")
                
                elif cmd == "tracker stop":
                    master.enemy_tracker.stop_tracking()
                    print("[CLI] Enemy tracking stopped")
                
                elif cmd == "tracker status":
                    status = master.enemy_tracker.get_status()
                    print(f"[TRACKER STATUS]")
                    print(f"  Active: {status['active']}")
                    if status.get('formatted'):
                        print(f"  {status['formatted']}")
                
                elif cmd:
                    print("Bilinmeyen komut")

            except KeyboardInterrupt:
                print("\n[SHUTDOWN] Interrupt signal - cleaning up...")
                master.stop_mission()
                break
            except Exception as exc:
                print(f"[ERROR] {exc}")
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
