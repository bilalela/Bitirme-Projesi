#!/usr/bin/env python3
"""
Multi-UAV Camera Viewer - OpenCV RTP Stream
Her uçağın kamerası ayrı OpenCV window'unda gösterilir
"""

import cv2
import threading
import numpy as np
import subprocess
import time
import sys
import json
import base64
try:
    import tkinter as tk
    def _get_screen_size():
        root = tk.Tk()
        root.withdraw()
        w = root.winfo_screenwidth()
        h = root.winfo_screenheight()
        root.destroy()
        return w, h
    SCREEN_WIDTH, SCREEN_HEIGHT = _get_screen_size()
except Exception:
    # Fallback if tkinter yok veya erişilemez
    SCREEN_WIDTH, SCREEN_HEIGHT = 1920, 1080

# Maksimum tek pencere boyutu (ekranın yarısı)
MAX_SINGLE_W = SCREEN_WIDTH // 2
MAX_SINGLE_H = SCREEN_HEIGHT // 2

# Kamera ayarları (Enemy kamerası kapalı - 5 kamera aktif)
PORTS = [5600, 5601, 5602, 5603, 5604]
UAV_NAMES = ["UAV1 (Master)", "UAV2 (Slave)", "UAV3 (Slave)", "UAV4 (Slave)", "UAV5 (Slave)"]
PLANE_MODELS = ["plane_Master", "plane_Slave_1", "plane_Slave_2", "plane_Slave_3", "plane_Slave_4"]

# Frame depolama
frames = {}
connection_status = {}
frame_counters = {}
frame_skip_counter = {}

# ⚡ BUFFER POOLING: Pre-allocated numpy arrays to avoid per-frame malloc
# This reduces memory fragmentation and GC pressure
rgb_buffers = {}
for name in UAV_NAMES:
    # Pre-allocate RGB buffer: 1280x720x3 (worst case, will be reshaped to 640x360x3)
    rgb_buffers[name] = np.zeros((720, 1280, 3), dtype=np.uint8, order='C')

# ⚡ PERFORMANS: Frame decimation + Resolution downscale
FRAME_SKIP = 1  # Her frame'i işle (30fps → 30fps, gerçek-zamanlı akışlı)
TARGET_WIDTH = 600  # 1280 → 600 (width 47%)
TARGET_HEIGHT = 330  # 720 → 330 (height 46%)
# RAM azalma: 1280x720x3 → 600x330x3 = 22% (11.5MB → 2.4MB per frame) + 5 kamera (enemy kapalı)

for name in UAV_NAMES:
    frames[name] = None
    connection_status[name] = "Bağlanıyor..."
    frame_counters[name] = 0
    frame_skip_counter[name] = 0

# ⚡ FPS TRACKING: Real-time FPS calculation for each camera
frame_times = {}  # name -> (frame_count, timestamp) for FPS calculation
fps_values = {}   # name -> current FPS value
fps_history = {}  # name -> list of recent fps values (for smoothing)
for name in UAV_NAMES:
    frame_times[name] = (0, time.time())
    fps_values[name] = 0.0
    fps_history[name] = []

def enable_camera_in_gazebo(plane_index):
    """Gazebo'da kamera streaming'i etkinleştir"""
    try:
        plane_model = PLANE_MODELS[plane_index]
        cmd = (
            f"gz topic -t /world/runway/model/{plane_model}/link/base_link/sensor/camera/image/enable_streaming "
            f"-m gz.msgs.Boolean -p 'data: 1'"
        )
        subprocess.run(cmd, shell=True, timeout=5, capture_output=True)
        print(f"  [✓] {UAV_NAMES[plane_index]} → Gazebo'da streaming aktif")
        return True
    except Exception as e:
        print(f"  [!] {UAV_NAMES[plane_index]} → Hata: {e}")
        return False

def enable_all_cameras_gazebo():
    """Tüm kameraları Gazebo'da etkinleştir"""
    print("\n[*] Gazebo kameralarını etkinleştiriyorum (3 sn bekleme)...\n")
    time.sleep(3)  # Gazebo'nun hazırlanmasını bekle
    
    success_count = 0
    for i in range(len(PORTS)):
        if enable_camera_in_gazebo(i):
            success_count += 1
        time.sleep(0.2)  # Kameralar arası kısa gecikme
    
    print(f"\n[✓] {success_count}/{len(PORTS)} kamera Gazebo'da açıldı!\n")
    return success_count > 0

def capture_camera_stream(port, name, index):
    """Her kamera için ayrı thread - OpenCV ile RTP stream oku"""
    global frames, connection_status, frame_counters, frame_skip_counter
    
    print(f"[>] {name} (Port {port}) kamera akışı başlatılıyor...")
    # Yeni yöntem: Gazebo'nun JSON çıktı veren `gz topic -e --json-output` komutunu okuyup
    # gelen `data` alanını base64 decode ederek ham RGB görüntüyü oluşturuyoruz.
    topic = f"/world/runway/model/{PLANE_MODELS[index]}/link/base_link/sensor/camera/image"
    cmd = ["gz", "topic", "-e", "-t", topic, "--json-output"]

    reconnect_count = 0
    max_reconnects = 3

    while True:
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=8192)
            print(f"[✓] {name} -> subscribed to {topic}")
            connection_status[name] = "✅ Abone Olundu"

            # satır satır JSON nesneleri okunuyor
            for raw in proc.stdout:
                if not raw:
                    continue
                try:
                    line = raw.decode('utf-8').strip()
                except Exception:
                    try:
                        line = raw.decode('latin1').strip()
                    except Exception:
                        continue

                if not line:
                    continue

                try:
                    # ⚡ FRAME DECIMATION: Her 2. frame'i atla (RAM -50%)
                    frame_skip_counter[name] += 1
                    if frame_skip_counter[name] % FRAME_SKIP != 0:
                        continue
                    
                    msg = json.loads(line)
                    # msg contains: width, height, data (base64 of raw RGB)
                    w = int(msg.get('width', 0))
                    h = int(msg.get('height', 0))
                    data_b64 = msg.get('data', '')
                    if not data_b64 or w == 0 or h == 0:
                        continue
                    
                    # ⚡ BUFFER POOLING: Decode base64 directly to pre-allocated buffer
                    try:
                        raw_bytes = base64.b64decode(data_b64)
                        if len(raw_bytes) != w * h * 3:
                            connection_status[name] = f"❌ Veri boyutu {len(raw_bytes)} != {w*h*3}"
                            continue
                        # Copy to pre-allocated buffer
                        np.copyto(rgb_buffers[name][:h, :w, :], 
                                 np.frombuffer(raw_bytes, dtype=np.uint8).reshape((h, w, 3)))
                        frame = rgb_buffers[name][:h, :w, :].copy()  # Copy for safety
                    except Exception as decode_err:
                        connection_status[name] = f"❌ Decode: {str(decode_err)[:20]}"
                        continue
                    
                    # Gazebo image format R8G8B8 -> convert RGB to BGR for OpenCV
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    
                    # ⚡ RESOLUTION DOWNSCALE: 1280x720 → 640x360 (RAM -75%)
                    frame = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT), interpolation=cv2.INTER_AREA)

                    frame_counters[name] += 1
                    
                    # ⚡ FPS CALCULATION: Real-time FPS for each camera
                    current_time = time.time()
                    last_frame_count, last_frame_time = frame_times[name]
                    elapsed = current_time - last_frame_time
                    
                    if elapsed >= 1.0:  # Update FPS every 1 second
                        current_fps = (frame_counters[name] - last_frame_count) / elapsed
                        fps_history[name].append(current_fps)
                        if len(fps_history[name]) > 10:  # Keep last 10 measurements
                            fps_history[name].pop(0)
                        fps_values[name] = sum(fps_history[name]) / len(fps_history[name])  # Smooth average
                        frame_times[name] = (frame_counters[name], current_time)
                    
                    connection_status[name] = f"✅ AKTIF | FPS: {fps_values[name]:.1f} | Frame: {frame_counters[name]}"

                    # overlay info with FPS
                    fh, fw = frame.shape[:2]
                    cv2.rectangle(frame, (0, 0), (fw, 45), (0, 0, 0), -1)
                    overlay_text = f"{name} | FPS: {fps_values[name]:.1f} | Frame: {frame_counters[name]} | Res: {fw}x{fh}"
                    cv2.putText(frame, overlay_text, (8, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

                    frames[name] = frame

                except json.JSONDecodeError as e:
                    connection_status[name] = f"❌ JSON: line invalid"
                    continue
                except Exception as e:
                    connection_status[name] = f"❌ Hata: {str(e)[:20]}"
                    continue

            # proc.stdout döngüsü bitmişse yeniden bağlanmayı deneyelim
            proc.wait()
            connection_status[name] = "🔄 Yeniden bağlanıyor"
            if reconnect_count < max_reconnects:
                reconnect_count += 1
                time.sleep(1)
                continue
            else:
                connection_status[name] = "❌ Bağlantı Başarısız"
                break

        except Exception as e:
            print(f"[X] {name} - Hata: {str(e)[:80]}")
            connection_status[name] = f"❌ Hata: {str(e)[:30]}"
            time.sleep(2)

def display_camera_window(name, index):
    """Her kamera için ayrı window göster"""
    print(f"[W] {name} - Window başlatılıyor...")
    
    while True:
        if frames[name] is not None:
            # Frame'i göster
            frame = frames[name]
            h, w = frame.shape[:2]
            scale = min(1.0, MAX_SINGLE_W / w, MAX_SINGLE_H / h)
            if scale < 1.0:
                nw = int(w * scale)
                nh = int(h * scale)
                disp = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
            else:
                disp = frame
            cv2.imshow(f"🎥 {name}", disp)
        else:
            # Bekleme ekranı
            wait_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(wait_frame, name, (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (100, 100, 255), 3)
            cv2.putText(wait_frame, connection_status[name], (50, 150), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
            cv2.putText(wait_frame, "Bekleniyor...", (50, 250), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (200, 200, 0), 2)
            cv2.imshow(f"🎥 {name}", wait_frame)
        
        # q = Quit (⚡ reduced waitKey from 50ms to 16ms for 60fps+)
        if cv2.waitKey(16) & 0xFF == ord('q'):
            cv2.destroyAllWindows()
            sys.exit(0)

def display_combined_grid():
    """Tüm kameraları 3x2 grid'de bir pencerede göster"""
    print("[G] Kombinli Grid - Window başlatılıyor...")
    
    while True:
        try:
            # Tüm frame'ler hazır mı kontrol et
            available_frames = {k: v for k, v in frames.items() if v is not None}
            
            if len(available_frames) == 0:
                # Bekleme ekranı
                wait_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
                cv2.putText(wait_frame, "Kamera Aklishlari Bekleniyor...", (150, 360), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
                cv2.putText(wait_frame, "Gazebo ve kameralar baslatilsin", (150, 420), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, (200, 200, 0), 2)
                # scale wait frame to screen if needed
                cw, ch = wait_frame.shape[1], wait_frame.shape[0]
                margin = 100
                max_cw = SCREEN_WIDTH - margin
                max_ch = SCREEN_HEIGHT - margin
                scale = min(1.0, max_cw / cw, max_ch / ch)
                if scale < 1.0:
                    wait_frame = cv2.resize(wait_frame, (int(cw*scale), int(ch*scale)), interpolation=cv2.INTER_AREA)
                cv2.imshow("🎥 Kamera Grid (3x2)", wait_frame)
            
            elif len(available_frames) >= len(PORTS):
                # Tüm kameralar hazır - 3x2 Grid oluştur (veya 5 kamera için 3x2 + placeholder)
                grid_frames = [frames[name] for name in UAV_NAMES if frames[name] is not None]
                
                # Placeholder frame'ler ekle (5 kamera için 1 placeholder)
                while len(grid_frames) < 6:
                    placeholder = np.zeros((330, 600, 3), dtype=np.uint8)
                    cv2.putText(placeholder, "INACTIVE", (150, 165), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1.0, (100, 100, 255), 2)
                    grid_frames.append(placeholder)
                
                row1 = np.hstack([grid_frames[0], grid_frames[1], grid_frames[2]])
                row2 = np.hstack([grid_frames[3], grid_frames[4], grid_frames[5]])
                combined = np.vstack([row1, row2])
                
                # Üst bilgi bar'ı ekle
                h, w = combined.shape[:2]
                info_bar = np.zeros((50, w, 3), dtype=np.uint8)
                status_text = " | ".join([f"{k[:6]}: {v[:15]}" for k, v in list(connection_status.items())[:3]])
                cv2.putText(info_bar, status_text, (10, 35), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
                
                combined = np.vstack([info_bar, combined])
                # scale combined to screen if needed
                cw, ch = combined.shape[1], combined.shape[0]
                margin = 100
                max_cw = SCREEN_WIDTH - margin
                max_ch = SCREEN_HEIGHT - margin
                scale = min(1.0, max_cw / cw, max_ch / ch)
                if scale < 1.0:
                    combined = cv2.resize(combined, (int(cw*scale), int(ch*scale)), interpolation=cv2.INTER_AREA)
                cv2.imshow("🎥 Kamera Grid (3x2)", combined)
            
            else:
                # Kısmi frame'ler - mevcut olanları göster
                grid_frames = [frames[name] for name in UAV_NAMES if frames[name] is not None]
                
                # Placeholder frame'ler ekle (5 kamera için max 1 placeholder)
                while len(grid_frames) < 6:
                    placeholder = np.zeros((330, 600, 3), dtype=np.uint8)
                    cv2.putText(placeholder, "WAITING", (140, 165), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
                    grid_frames.append(placeholder)
                
                row1 = np.hstack([grid_frames[0], grid_frames[1], grid_frames[2]])
                row2 = np.hstack([grid_frames[3], grid_frames[4], grid_frames[5]])
                combined = np.vstack([row1, row2])
                cw, ch = combined.shape[1], combined.shape[0]
                margin = 100
                max_cw = SCREEN_WIDTH - margin
                max_ch = SCREEN_HEIGHT - margin
                scale = min(1.0, max_cw / cw, max_ch / ch)
                if scale < 1.0:
                    combined = cv2.resize(combined, (int(cw*scale), int(ch*scale)), interpolation=cv2.INTER_AREA)
                cv2.imshow("🎥 Kamera Grid (3x2)", combined)
            
            # q = Quit (⚡ reduced waitKey from 50ms to 16ms for 60fps+)
            if cv2.waitKey(16) & 0xFF == ord('q'):
                cv2.destroyAllWindows()
                sys.exit(0)
        
        except Exception as e:
            print(f"[G] Grid hatası: {e}")
            time.sleep(1)

# ============================================================================
# MAIN PROGRAM
# ============================================================================

print("\n" + "=" * 80)
print("🎥  MULTI-UAV CAMERA VIEWER - AYRICALIKLI PENCERELER")
print("=" * 80)
print("\n[i] Gereksinimler:")
print("    • Gazebo simülasyonu (bash baslat.sh)")
print("    • ArduPilot SITL 6 instance")
print("    • OpenCV + GStreamer")
print("\n[i] Seçenekler:")
print("    1 = Her kamera ayrı pencere")
print("    2 = Tüm kameralar 3x2 grid'de")
print("    q = Çık")
print("=" * 80 + "\n")

# Kameraları Gazebo'da etkinleştir
if not enable_all_cameras_gazebo():
    print("[!] UYARI: Gazebo kameraları etkinleştirilemedi!")
    print("[!] Gazebo çalışıyor mu kontrol edin (bash baslat.sh)\n")

# Kullanıcıdan seçim al
while True:
    choice = input("Seçiminiz (1/2/q): ").strip().lower()
    
    if choice in ['1', '2', 'q']:
        break
    else:
        print("[!] Lütfen 1, 2 veya q seçin!")

if choice == '1':
    print("\n[*] Her kamera için ayrı OpenCV window açılıyor...\n")
    
    # Capture thread'leri başlat
    for i in range(len(PORTS)):
        t = threading.Thread(target=capture_camera_stream, 
                           args=(PORTS[i], UAV_NAMES[i], i), 
                           daemon=True)
        t.start()
        time.sleep(0.1)
    
    # Display thread'leri başlat (capture başlasın diye 1 sn bekle)
    time.sleep(1)
    for i in range(len(PORTS)):
        t = threading.Thread(target=display_camera_window, 
                           args=(UAV_NAMES[i], i), 
                           daemon=True)
        t.start()
        time.sleep(0.1)
    
    print("\n[✓] Tüm window'lar açıldı!")
    print("[i] Her pencereyi 'q' tuşu ile kapatabilirsiniz")
    print("[i] Tüm window'ları kapatmak için Ctrl+C'ye basın\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Programdan çıkılıyor...")
        cv2.destroyAllWindows()
        sys.exit(0)

elif choice == '2':
    print("\n[*] Kombinli Grid viewer başlatılıyor...\n")
    
    # Capture thread'leri başlat
    for i in range(len(PORTS)):
        t = threading.Thread(target=capture_camera_stream, 
                           args=(PORTS[i], UAV_NAMES[i], i), 
                           daemon=True)
        t.start()
        time.sleep(0.1)
    
    # Display thread'i başlat (capture başlasın diye 1 sn bekle)
    time.sleep(1)
    t = threading.Thread(target=display_combined_grid, daemon=True)
    t.start()
    
    print("[✓] Grid viewer açıldı!")
    print("[i] 'q' tuşu veya Ctrl+C ile kapatın\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Programdan çıkılıyor...")
        cv2.destroyAllWindows()
        sys.exit(0)

elif choice == 'q':
    print("[✓] Çıkılıyor...")
    sys.exit(0)

else:
    print("[!] Geçersiz seçim!")
    sys.exit(1)

