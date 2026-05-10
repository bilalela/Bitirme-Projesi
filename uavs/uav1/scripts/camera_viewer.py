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
from pathlib import Path
import argparse
from queue import Queue, Empty, Full

PROJECT_ROOT = Path(__file__).resolve().parents[3]
VISION_DIR = PROJECT_ROOT / "Goruntu_isleme"
if str(VISION_DIR) not in sys.path:
    sys.path.insert(0, str(VISION_DIR))

# Detector is loaded later after parsing args to allow a low-memory "no-detect" mode
OBJECT_DETECTOR = None
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
TARGET_WIDTH = 640  # 1280 -> 640 (uzak hedef için daha iyi detay)
TARGET_HEIGHT = 360  # 720 -> 360 (uzak hedef için daha iyi detay)
# RAM azalma: 1280x720x3 → 600x330x3 = 22% (11.5MB → 2.4MB per frame) + 5 kamera (enemy kapalı)

# ---------------------------------------------------------------------------
# CLI / runtime options (allow disabling detection and reducing resolution/frame rate)
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="Multi-UAV Camera Viewer")
parser.add_argument("--no-detect", action="store_true", help="Disable YOLO detection to reduce memory/CPU")
parser.add_argument("--width", type=int, help="Target display width (overrides default)")
parser.add_argument("--height", type=int, help="Target display height (overrides default)")
parser.add_argument("--frame-skip", type=int, help="Skip N-1 frames (1=process all, 2=process every 2nd frame)")
parser.add_argument("--mode", choices=["1", "2"], help="Viewer mode: 1=per-window, 2=grid")
parser.add_argument("--auto", action="store_true", help="Auto-start viewer without interactive prompt (uses --mode)")
parser.add_argument("--dump-frames", type=int, help="Dump first N decoded frames per camera to disk for debugging")
parser.add_argument("--display-scale", type=float, default=1.0, help="Display scale factor for UI windows (e.g. 2.0)")
parser.add_argument("--detect-every", type=int, default=2, help="Run YOLO every N processed frames (default: 2 on GPU)")
parser.add_argument("--detect-imgsz", type=int, default=640, help="YOLO inference image size (default: 640 for distant targets)")
parser.add_argument("--detect-conf", type=float, default=0.08, help="YOLO confidence threshold (default: 0.08 for distant/small targets)")
parser.add_argument("--detect-device", choices=["auto", "cpu", "cuda"], default="auto", help="Inference device")
parser.add_argument("--detect-all", action="store_true", help="Enable YOLO on all cameras (default: only UAV1)")
parser.add_argument("--only-camera", type=int, help="Open only one camera (1..5)")
parser.add_argument("--detect-camera", type=int, help="Run YOLO only on one camera (1..5)")
parser.add_argument("--grid-layout", choices=["classic", "focus"], default="focus", help="Grid layout for mode=2")
parser.add_argument("--focus-camera", type=int, default=1, help="Focus camera index (1..5) for focus layout")
args = parser.parse_args()

if args.width:
    TARGET_WIDTH = int(args.width)
if args.height:
    TARGET_HEIGHT = int(args.height)
if args.frame_skip:
    FRAME_SKIP = max(1, int(args.frame_skip))
DISPLAY_SCALE = max(0.5, float(args.display_scale))
DETECT_EVERY = max(1, int(args.detect_every))
DETECT_IMGSZ = max(160, int(args.detect_imgsz))
DETECT_CONF = max(0.01, min(1.0, float(args.detect_conf)))
ONLY_CAMERA_INDEX = None
if args.only_camera is not None:
    ONLY_CAMERA_INDEX = min(max(1, int(args.only_camera)), len(UAV_NAMES)) - 1

if args.detect_all:
    DETECT_CAMERA_INDEX_SET = set(range(len(UAV_NAMES)))
elif args.detect_camera is not None:
    DETECT_CAMERA_INDEX_SET = {min(max(1, int(args.detect_camera)), len(UAV_NAMES)) - 1}
else:
    DETECT_CAMERA_INDEX_SET = {0}

ACTIVE_CAMERA_INDEXES = [ONLY_CAMERA_INDEX] if ONLY_CAMERA_INDEX is not None else list(range(len(UAV_NAMES)))
GRID_LAYOUT = args.grid_layout
FOCUS_CAMERA_INDEX = min(max(1, int(args.focus_camera)), len(UAV_NAMES)) - 1

# Try to load detector unless explicitly disabled
if not args.no_detect:
    try:
        from object_detector import SharedYOLODetector
        OBJECT_DETECTOR = SharedYOLODetector(
            imgsz=DETECT_IMGSZ,
            conf=DETECT_CONF,
            device=args.detect_device,
        )
        if args.detect_all:
            detect_scope = "tum kameralar"
        elif args.detect_camera is not None:
            detect_scope = f"yalnizca UAV{int(args.detect_camera)}"
        else:
            detect_scope = "yalnizca UAV1"
        print(f"[✓] Nesne tespit modeli yüklendi: {OBJECT_DETECTOR.model_path}")
        print(
            f"[i] YOLO ayari -> device={OBJECT_DETECTOR.device}, fp16={OBJECT_DETECTOR.use_half}, "
            f"imgsz={DETECT_IMGSZ}, conf={DETECT_CONF}, detect_every={DETECT_EVERY}, kapsam={detect_scope}"
        )
    except Exception as exc:
        OBJECT_DETECTOR = None
        print(f"[!] Nesne tespit modeli yüklenemedi, sadece görüntü gösterilecek: {exc}")
else:
    print("[i] --no-detect set: Nesne tespiti devre disi - daha az bellek/CPU kullanilacak")

# --dump-frames: prepare dump dirs and counters
DUMP_FRAMES = int(args.dump_frames) if getattr(args, 'dump_frames', None) else 0
dump_counters = {name: 0 for name in UAV_NAMES}
if DUMP_FRAMES > 0:
    dump_root = PROJECT_ROOT / "frames_dump"
    dump_root.mkdir(parents=True, exist_ok=True)
    for name in UAV_NAMES:
        (dump_root / name.replace(' ', '_')).mkdir(parents=True, exist_ok=True)

for name in UAV_NAMES:
    frames[name] = None
    connection_status[name] = "Bağlanıyor..."
    frame_counters[name] = 0
    frame_skip_counter[name] = 0

# ⚡ FPS TRACKING: Real-time FPS calculation for each camera
frame_times = {}  # name -> (frame_count, timestamp) for FPS calculation
fps_values = {}   # name -> current FPS value
fps_history = {}  # name -> list of recent fps values (for smoothing)
detect_frame_counters = {}  # name -> processed frame count for detection cadence
last_detection_counts = {}  # name -> last detection count
detection_queues = {}  # name -> latest-frame queue for async detection worker
detection_results = {}  # name -> last detections
detection_lock = threading.Lock()
for name in UAV_NAMES:
    frame_times[name] = (0, time.time())
    fps_values[name] = 0.0
    fps_history[name] = []
    detect_frame_counters[name] = 0
    last_detection_counts[name] = 0
    detection_queues[name] = Queue(maxsize=1)
    detection_results[name] = []

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
    for i in ACTIVE_CAMERA_INDEXES:
        if enable_camera_in_gazebo(i):
            success_count += 1
        time.sleep(0.2)  # Kameralar arası kısa gecikme
    
    print(f"\n[✓] {success_count}/{len(ACTIVE_CAMERA_INDEXES)} kamera Gazebo'da açıldı!\n")
    return success_count > 0


def _draw_detections(frame, detections):
    """Draw bounding boxes and labels on frame."""
    out = frame.copy()
    for det in detections:
        try:
            x1, y1, x2, y2 = [int(v) for v in det.get("xyxy", [0, 0, 0, 0])]
            label = str(det.get("label", "obj"))
            conf = float(det.get("confidence", 0.0))
            cv2.rectangle(out, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                out,
                f"{label} {conf:.2f}",
                (x1, max(15, y1 - 5)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1,
            )
        except Exception:
            continue
    return out


def _detect_with_fallback(frame):
    """Full-frame + center-crop fallback detection for distant targets."""
    detections = OBJECT_DETECTOR.infer(frame)
    if detections:
        return detections

    fh, fw = frame.shape[:2]
    crop_ratio = 0.6
    cw = int(fw * crop_ratio)
    ch = int(fh * crop_ratio)
    x0 = (fw - cw) // 2
    y0 = (fh - ch) // 2
    crop = frame[y0:y0 + ch, x0:x0 + cw]
    crop_dets = OBJECT_DETECTOR.infer(crop)

    if not crop_dets:
        return []

    remapped = []
    for det in crop_dets:
        x1, y1, x2, y2 = det["xyxy"]
        remapped.append(
            {
                "label": det.get("label", "obj"),
                "confidence": det.get("confidence", 0.0),
                "xyxy": [x1 + x0, y1 + y0, x2 + x0, y2 + y0],
            }
        )
    return remapped


def detection_worker(name, index):
    """Run YOLO in a separate thread so capture loop stays fast."""
    queue_obj = detection_queues[name]
    while True:
        try:
            frame = queue_obj.get(timeout=1.0)
        except Empty:
            continue

        if frame is None:
            break

        if OBJECT_DETECTOR is None or index not in DETECT_CAMERA_INDEX_SET:
            continue

        try:
            OBJECT_DETECTOR.conf = DETECT_CONF
            OBJECT_DETECTOR.imgsz = DETECT_IMGSZ
            detections = _detect_with_fallback(frame)
            with detection_lock:
                detection_results[name] = detections
                last_detection_counts[name] = len(detections)
        except Exception as det_exc:
            connection_status[name] = f"⚠️ Tespit Hatası: {str(det_exc)[:24]}"

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
                    
                    # Decode base64 to numpy view (avoid extra copy/copyto cost)
                    try:
                        raw_bytes = base64.b64decode(data_b64)
                        if len(raw_bytes) != w * h * 3:
                            connection_status[name] = f"❌ Veri boyutu {len(raw_bytes)} != {w*h*3}"
                            continue
                        frame = np.frombuffer(raw_bytes, dtype=np.uint8).reshape((h, w, 3))
                    except Exception as decode_err:
                        connection_status[name] = f"❌ Decode: {str(decode_err)[:20]}"
                        continue
                    
                    # Gazebo image format R8G8B8 -> convert RGB to BGR for OpenCV
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    
                    # ⚡ RESOLUTION DOWNSCALE: 1280x720 → 640x360 (RAM -75%)
                    frame = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT), interpolation=cv2.INTER_AREA)
                    # Optional: dump first decoded frames to disk for offline inspection
                    try:
                        if DUMP_FRAMES > 0 and dump_counters.get(name, 0) < DUMP_FRAMES:
                            dump_path = dump_root / name.replace(' ', '_') / f"frame_{dump_counters[name]:03d}.png"
                            cv2.imwrite(str(dump_path), frame)
                            dump_counters[name] += 1
                            print(f"[D] {name} -> dumped {dump_path}")
                    except Exception as e:
                        print(f"[D] dump error {name}: {e}")

                    detection_count = last_detection_counts[name]
                    if OBJECT_DETECTOR is not None and index in DETECT_CAMERA_INDEX_SET:
                        detect_frame_counters[name] += 1
                        if detect_frame_counters[name] % DETECT_EVERY == 0:
                            try:
                                queue_obj = detection_queues[name]
                                if queue_obj.full():
                                    try:
                                        queue_obj.get_nowait()
                                    except Empty:
                                        pass
                                queue_obj.put_nowait(frame.copy())
                            except Exception as det_exc:
                                connection_status[name] = f"⚠️ Tespit Hatası: {str(det_exc)[:24]}"

                        with detection_lock:
                            detections = detection_results.get(name, [])
                            detection_count = last_detection_counts.get(name, 0)
                        if detections:
                            frame = _draw_detections(frame, detections)

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
                    
                    connection_status[name] = f"✅ AKTIF | FPS: {fps_values[name]:.1f} | Obj: {detection_count} | Frame: {frame_counters[name]}"

                    # overlay info with FPS
                    fh, fw = frame.shape[:2]
                    cv2.rectangle(frame, (0, 0), (fw, 45), (0, 0, 0), -1)
                    overlay_text = f"{name} | FPS: {fps_values[name]:.1f} | Obj: {detection_count} | Frame: {frame_counters[name]} | Res: {fw}x{fh}"
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
    window_name = f"🎥 {name}"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    try:
        cv2.resizeWindow(window_name, int(MAX_SINGLE_W * 0.95), int(MAX_SINGLE_H * 0.95))
    except Exception:
        pass
    
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
            if DISPLAY_SCALE != 1.0:
                sw = max(1, int(disp.shape[1] * DISPLAY_SCALE))
                sh = max(1, int(disp.shape[0] * DISPLAY_SCALE))
                disp = cv2.resize(disp, (sw, sh), interpolation=cv2.INTER_LINEAR)
            cv2.imshow(window_name, disp)
            try:
                cv2.resizeWindow(window_name, disp.shape[1], disp.shape[0])
            except Exception:
                pass
        else:
            # Bekleme ekranı
            wait_frame = np.zeros((int(MAX_SINGLE_H * 0.75), int(MAX_SINGLE_W * 0.75), 3), dtype=np.uint8)
            cv2.putText(wait_frame, name, (50, 90), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (100, 100, 255), 3)
            cv2.putText(wait_frame, connection_status[name], (50, 150),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
            cv2.putText(wait_frame, "Gazebo frame bekleniyor...", (50, 250),
                       cv2.FONT_HERSHEY_SIMPLEX, 1.0, (200, 200, 0), 2)
            cv2.putText(wait_frame, "enemy_track on sonra 2-5 sn bekleyin", (50, 310),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 0), 2)
            cv2.imshow(window_name, wait_frame)
            try:
                cv2.resizeWindow(window_name, wait_frame.shape[1], wait_frame.shape[0])
            except Exception:
                pass
        
        # q = Quit (⚡ reduced waitKey from 50ms to 16ms for 60fps+)
        if cv2.waitKey(16) & 0xFF == ord('q'):
            cv2.destroyAllWindows()
            sys.exit(0)


def display_all_windows():
    """Güncellenmiş: Tek GUI döngüsü ile tüm pencereleri ana iş parçacığında göster"""
    print("[W] Tüm pencereler - tek GUI döngüsü başlatılıyor...")
    # Oluştur pencereler
    for name in UAV_NAMES:
        cv2.namedWindow(f"🎥 {name}", cv2.WINDOW_NORMAL)

    try:
        while True:
            for name in UAV_NAMES:
                if frames[name] is not None:
                    frame = frames[name]
                    h, w = frame.shape[:2]
                    scale = min(1.0, MAX_SINGLE_W / w, MAX_SINGLE_H / h)
                    if scale < 1.0:
                        nw = int(w * scale)
                        nh = int(h * scale)
                        disp = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
                    else:
                        disp = frame
                    if DISPLAY_SCALE != 1.0:
                        sw = max(1, int(disp.shape[1] * DISPLAY_SCALE))
                        sh = max(1, int(disp.shape[0] * DISPLAY_SCALE))
                        disp = cv2.resize(disp, (sw, sh), interpolation=cv2.INTER_LINEAR)
                    cv2.imshow(f"🎥 {name}", disp)
                else:
                    wait_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    cv2.putText(wait_frame, name, (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (100, 100, 255), 3)
                    cv2.putText(wait_frame, connection_status[name], (50, 150), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
                    cv2.putText(wait_frame, "Bekleniyor...", (50, 250), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1.0, (200, 200, 0), 2)
                    cv2.imshow(f"🎥 {name}", wait_frame)

            if cv2.waitKey(30) & 0xFF == ord('q'):
                cv2.destroyAllWindows()
                sys.exit(0)

            time.sleep(0.02)

    except KeyboardInterrupt:
        cv2.destroyAllWindows()
        sys.exit(0)


def _make_placeholder(label, width, height, color=(0, 0, 255)):
    img = np.zeros((height, width, 3), dtype=np.uint8)
    cv2.putText(img, label, (max(10, width // 8), height // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    return img


def _ensure_size(frame, width, height):
    if frame is None:
        return np.zeros((height, width, 3), dtype=np.uint8)
    fh, fw = frame.shape[:2]
    if (fh, fw) == (height, width):
        return frame
    return cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)


def _fit_to_screen(image, margin=100):
    max_w = max(320, SCREEN_WIDTH - margin)
    max_h = max(240, SCREEN_HEIGHT - margin)
    h, w = image.shape[:2]
    scale = min(1.0, max_w / w, max_h / h)
    if scale < 1.0:
        return cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return image


def _build_classic_grid(frame_map):
    cell_w, cell_h = TARGET_WIDTH, TARGET_HEIGHT
    tiles = []
    for name in UAV_NAMES:
        frame = frame_map.get(name)
        if frame is None:
            frame = _make_placeholder("WAITING", cell_w, cell_h)
        tiles.append(_ensure_size(frame, cell_w, cell_h))

    while len(tiles) < 6:
        tiles.append(_make_placeholder("INACTIVE", cell_w, cell_h, color=(100, 100, 255)))

    row1 = np.hstack([tiles[0], tiles[1], tiles[2]])
    row2 = np.hstack([tiles[3], tiles[4], tiles[5]])
    return np.vstack([row1, row2])


def _build_focus_grid(frame_map):
    cell_w, cell_h = TARGET_WIDTH, TARGET_HEIGHT
    big_w, big_h = cell_w * 4, cell_h * 2

    focus_name = UAV_NAMES[FOCUS_CAMERA_INDEX]
    focus_frame = frame_map.get(focus_name)
    if focus_frame is None:
        focus_frame = _make_placeholder(f"{focus_name} WAITING", big_w, big_h)
    else:
        focus_frame = _ensure_size(focus_frame, big_w, big_h)

    others = [n for i, n in enumerate(UAV_NAMES) if i != FOCUS_CAMERA_INDEX]
    thumbs = []
    for name in others:
        frame = frame_map.get(name)
        if frame is None:
            frame = _make_placeholder(f"{name[:6]} WAIT", cell_w, cell_h)
        thumbs.append(_ensure_size(frame, cell_w, cell_h))

    while len(thumbs) < 4:
        thumbs.append(_make_placeholder("INACTIVE", cell_w, cell_h, color=(100, 100, 255)))

    thumb_row = np.hstack(thumbs[:4])
    return np.vstack([focus_frame, thumb_row])

def display_combined_grid():
    """Tüm kameraları 3x2 grid'de bir pencerede göster"""
    print("[G] Kombinli Grid - Window başlatılıyor...")
    window_name = "🎥 Kamera Grid (3x2)"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
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
                cv2.imshow(window_name, wait_frame)
                try:
                    cv2.resizeWindow(window_name, wait_frame.shape[1], wait_frame.shape[0])
                except Exception:
                    pass
            
            elif len(available_frames) >= len(PORTS):
                # Tüm kameralar hazır - 3x2 Grid oluştur (veya 5 kamera için 3x2 + placeholder)
                grid_frames = [frames[name] for name in UAV_NAMES if frames[name] is not None]

                # Placeholder frame'ler ekle (5 kamera için 1 placeholder)
                while len(grid_frames) < 6:
                    placeholder = np.zeros((TARGET_HEIGHT, TARGET_WIDTH, 3), dtype=np.uint8)
                    cv2.putText(placeholder, "INACTIVE", (max(10, TARGET_WIDTH//4), TARGET_HEIGHT//2), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 100, 255), 2)
                    grid_frames.append(placeholder)

                # Tüm frame'leri hücre boyutuna yeniden boyutlandır (hstack için eşit yükseklik gerekir)
                cell_w, cell_h = TARGET_WIDTH, TARGET_HEIGHT
                resized = []
                for f in grid_frames:
                    if f is None:
                        resized.append(np.zeros((cell_h, cell_w, 3), dtype=np.uint8))
                        continue
                    fh, fw = f.shape[:2]
                    if (fh, fw) != (cell_h, cell_w):
                        try:
                            rf = cv2.resize(f, (cell_w, cell_h), interpolation=cv2.INTER_AREA)
                        except Exception:
                            rf = cv2.resize(f, (cell_w, cell_h))
                        resized.append(rf)
                    else:
                        resized.append(f)

                row1 = np.hstack([resized[0], resized[1], resized[2]])
                row2 = np.hstack([resized[3], resized[4], resized[5]])
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
                if DISPLAY_SCALE != 1.0:
                    sw = max(1, int(combined.shape[1] * DISPLAY_SCALE))
                    sh = max(1, int(combined.shape[0] * DISPLAY_SCALE))
                    combined = cv2.resize(combined, (sw, sh), interpolation=cv2.INTER_LINEAR)
                cv2.imshow(window_name, combined)
                try:
                    cv2.resizeWindow(window_name, combined.shape[1], combined.shape[0])
                except Exception:
                    pass
            
            else:
                # Kısmi frame'ler - mevcut olanları göster
                grid_frames = [frames[name] for name in UAV_NAMES if frames[name] is not None]

                # Placeholder frame'ler ekle (5 kamera için max 1 placeholder)
                while len(grid_frames) < 6:
                    placeholder = np.zeros((TARGET_HEIGHT, TARGET_WIDTH, 3), dtype=np.uint8)
                    cv2.putText(placeholder, "WAITING", (max(10, TARGET_WIDTH//6), TARGET_HEIGHT//2), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                    grid_frames.append(placeholder)

                # Normalize all frames to cell size
                cell_w, cell_h = TARGET_WIDTH, TARGET_HEIGHT
                resized = []
                for f in grid_frames:
                    if f is None:
                        resized.append(np.zeros((cell_h, cell_w, 3), dtype=np.uint8))
                        continue
                    fh, fw = f.shape[:2]
                    if (fh, fw) != (cell_h, cell_w):
                        try:
                            rf = cv2.resize(f, (cell_w, cell_h), interpolation=cv2.INTER_AREA)
                        except Exception:
                            rf = cv2.resize(f, (cell_w, cell_h))
                        resized.append(rf)
                    else:
                        resized.append(f)

                row1 = np.hstack([resized[0], resized[1], resized[2]])
                row2 = np.hstack([resized[3], resized[4], resized[5]])
                combined = np.vstack([row1, row2])
                cw, ch = combined.shape[1], combined.shape[0]
                margin = 100
                max_cw = SCREEN_WIDTH - margin
                max_ch = SCREEN_HEIGHT - margin
                scale = min(1.0, max_cw / cw, max_ch / ch)
                if scale < 1.0:
                    combined = cv2.resize(combined, (int(cw*scale), int(ch*scale)), interpolation=cv2.INTER_AREA)
                if DISPLAY_SCALE != 1.0:
                    sw = max(1, int(combined.shape[1] * DISPLAY_SCALE))
                    sh = max(1, int(combined.shape[0] * DISPLAY_SCALE))
                    combined = cv2.resize(combined, (sw, sh), interpolation=cv2.INTER_LINEAR)
                cv2.imshow(window_name, combined)
                try:
                    cv2.resizeWindow(window_name, combined.shape[1], combined.shape[0])
                except Exception:
                    pass
            
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

# Kullanıcıdan seçim al (varsayılan: her zaman sor)
# Not: Sadece --auto ve --mode birlikte verilirse prompt atlanır.
if args.auto and args.mode:
    choice = args.mode
    print(f"[i] --auto ile başlatılıyor, mode={choice}")
else:
    default_hint = args.mode if args.mode in ['1', '2'] else None
    while True:
        if default_hint:
            raw_choice = input(f"Seçiminiz (1/2/q) [varsayılan {default_hint}]: ").strip().lower()
            choice = default_hint if raw_choice == '' else raw_choice
        else:
            choice = input("Seçiminiz (1/2/q): ").strip().lower()

        if choice in ['1', '2', 'q']:
            break
        print("[!] Lütfen 1, 2 veya q seçin!")

if choice == '1':
    print("\n[*] Her kamera için ayrı OpenCV window açılıyor...\n")

    # Detection workers: YOLO ayrı thread'de çalışsın, capture bloklanmasın.
    if OBJECT_DETECTOR is not None:
        for i in ACTIVE_CAMERA_INDEXES:
            if i in DETECT_CAMERA_INDEX_SET:
                dt = threading.Thread(
                    target=detection_worker,
                    args=(UAV_NAMES[i], i),
                    daemon=True,
                )
                dt.start()
    
    # Capture thread'leri başlat
    for i in ACTIVE_CAMERA_INDEXES:
        t = threading.Thread(target=capture_camera_stream, 
                           args=(PORTS[i], UAV_NAMES[i], i), 
                           daemon=True)
        t.start()
        time.sleep(0.1)
    
    print("\n[✓] Tüm window'lar açıldı!")
    print("[i] Her pencereyi 'q' tuşu ile kapatabilirsiniz")
    print("[i] Tüm window'ları kapatmak için Ctrl+C'ye basın\n")

    # GUI mutlaka ana thread'de çalışsın (Qt/OpenCV thread sorunlarını önler)
    time.sleep(0.5)
    display_all_windows()

elif choice == '2':
    print("\n[*] Kombinli Grid viewer başlatılıyor...\n")

    # Detection workers: YOLO ayrı thread'de çalışsın, capture bloklanmasın.
    if OBJECT_DETECTOR is not None:
        for i in ACTIVE_CAMERA_INDEXES:
            if i in DETECT_CAMERA_INDEX_SET:
                dt = threading.Thread(
                    target=detection_worker,
                    args=(UAV_NAMES[i], i),
                    daemon=True,
                )
                dt.start()
    
    # Capture thread'leri başlat
    for i in ACTIVE_CAMERA_INDEXES:
        t = threading.Thread(target=capture_camera_stream, 
                           args=(PORTS[i], UAV_NAMES[i], i), 
                           daemon=True)
        t.start()
        time.sleep(0.1)
    
    # GUI ana thread'de çalışsın
    time.sleep(0.5)
    
    print("[✓] Grid viewer açıldı!")
    print("[i] 'q' tuşu veya Ctrl+C ile kapatın\n")

    if len(ACTIVE_CAMERA_INDEXES) == 1:
        active_index = ACTIVE_CAMERA_INDEXES[0]
        display_camera_window(UAV_NAMES[active_index], active_index)
    else:
        display_combined_grid()

elif choice == 'q':
    print("[✓] Çıkılıyor...")
    sys.exit(0)

else:
    print("[!] Geçersiz seçim!")
    sys.exit(1)

