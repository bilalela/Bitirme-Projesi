#!/bin/bash

# --- 1. AYARLAR --------------------------------
PLANE_COUNT=4
OUT_IP="127.0.0.1"
EXTRA_OUT_PORT_START=15550
PROJECT_DIR="$HOME/Bitirme Projesi"
CONFIG_PATH="$PROJECT_DIR/SITL_Models/Gazebo/config"
WORLD_FILE="vtail_runway_planes"
BASE_UAV_DIR="$PROJECT_DIR/uavs"
ARDUPLANE_BIN="$HOME/ardupilot/build/sitl/bin/arduplane"

PLUGIN_DIRS=()
for dir in \
    "/usr/local/lib/ardupilot_gazebo" \
    "$HOME/gz_ws/src/ardupilot_gazebo/build"
do
    if [ -d "$dir" ]; then
        PLUGIN_DIRS+=("$dir")
    fi
done

if [ ${#PLUGIN_DIRS[@]} -eq 0 ]; then
    echo "❌ HATA: ArduPilot/Gazebo plugin klasörü bulunamadı."
    echo "   Beklenen konumlar: /usr/local/lib/ardupilot_gazebo veya $HOME/gz_ws/src/ardupilot_gazebo/build"
    exit 1
fi

PLUGIN_PATH=$(IFS=:; echo "${PLUGIN_DIRS[*]}")

# UAV konfigürasyonları: param_dosyası:master_mi_değil
UAV_CONFIGS=(
    "uav0:1"       # uav0.param, Master (SYSID=1)
    "uav1:1"       # uav1.param, Slave (SYSID=2)
    "uav2:1"       # uav2.param, Slave (SYSID=3)
    "uav3:1"       # uav3.param, Slave (SYSID=4)
    "mini_talon_vtail_5:1"       # mini_talon_vtail_5.param, Slave (SYSID=5)
    "mini_talon_vtail_6:1"       # mini_talon_vtail_6.param, Future Enemy (SYSID=6)
)

PLANE_COUNT=${#UAV_CONFIGS[@]}

# --- 2. TEMİZLİK ---
echo "======================================"
echo "Eski Gazebo ve ArduPilot süreçleri temizleniyor..."
echo "======================================"
pkill -9 -f "gz sim"
pkill -9 -f "sim_vehicle.py"
pkill -9 -f "arduplane"
pkill -9 -f "ardupilot"
pkill -9 -f "xterm"
pkill -9 -f "mavproxy"
sleep 1

# Screen session'ları temizle
screen -X -S gazebo quit 2>/dev/null
for i in 1 2 3 4 5; do screen -X -S uav$i quit 2>/dev/null; done
screen -wipe >/dev/null 2>&1
sleep 2

echo "✓ Temizlik tamamlandı"
echo ""

# --- 3. GAZEBO BAŞLAT ---
echo "======================================"
echo "Gazebo simülasyonu başlatılıyor..."
echo "======================================"
WORLD_PATH="$PROJECT_DIR/ardupilot_gazebo/worlds/$WORLD_FILE.sdf"

if [ ! -f "$WORLD_PATH" ]; then
    echo "❌ HATA: World dosyası bulunamadı: $WORLD_PATH"
    exit 1
fi

if [ -z "${DISPLAY:-}" ]; then
    export DISPLAY=:0
fi

screen -dmS gazebo bash -c "
  source ~/.bashrc
  export DISPLAY=:0
    export GZ_SIM_SYSTEM_PLUGIN_PATH=\"$PLUGIN_PATH:\${GZ_SIM_SYSTEM_PLUGIN_PATH:-}\"
    export LD_LIBRARY_PATH=\"$PLUGIN_PATH:\${LD_LIBRARY_PATH:-}\"
    export GZ_SIM_RESOURCE_PATH=\"$PROJECT_DIR/ardupilot_gazebo/models:\${GZ_SIM_RESOURCE_PATH:-}\"
  cd \"$PROJECT_DIR\"
    gz sim -v2 -r \"$WORLD_PATH\" 2>&1 | tee /tmp/gazebo.log
" 
echo "⏳ Gazebo yükleniyor (20 saniye bekleniyor)..."
sleep 20

for _ in 1 2 3 4 5 6; do
    if gz topic -l 2>/dev/null | grep -q "/world/runway/scene/info"; then
        break
    fi
    sleep 2
done

echo "✓ Gazebo başlatıldı"
echo ""

# --- 4. UAV DÖNGÜSÜ (Screen + Terminal Tab) ---
echo "======================================"
echo "$PLANE_COUNT adet uçak başlatılıyor..."
echo "======================================"

for (( i=0; i<$PLANE_COUNT; i++ ))
do
    CONF=${UAV_CONFIGS[$i]}
    PARAM_FILE=${CONF%%:*}
    
    SYSID=$((i + 1))
    PORT=$((EXTRA_OUT_PORT_START + (i * 10)))
    INSTANCE=$i
    SITL_TCP_PORT=$((5760 + (i * 10)))
    SITL_BRIDGE_PORT=$((5501 + (i * 10)))
    MAVPROXY_OUT_PORT=$((14550 + (i * 10)))
    CURRENT_PARAM="$CONFIG_PATH/$PARAM_FILE.param"
    UAV_DIR="$BASE_UAV_DIR/uav$SYSID"
    
    # Param dosyası kontrol
    if [ ! -f "$CURRENT_PARAM" ]; then
        echo "❌ HATA: Param dosyası bulunamadı: $CURRENT_PARAM"
        exit 1
    fi
    
    echo ""
    echo "UAV$SYSID başlatılıyor:"
    echo "  - SYSID: $SYSID"
    echo "  - Port: $PORT"
    echo "  - Instance: $INSTANCE"
    echo "  - Param: $PARAM_FILE"
    echo "  - Dizin: $UAV_DIR"
    
    if screen -dmS uav$SYSID bash -lc "
      export DISPLAY=\${DISPLAY:-:0}
      export XAUTHORITY=\${XAUTHORITY:-\$HOME/.Xauthority}
      cd '$UAV_DIR'
      '$ARDUPLANE_BIN' --model JSON --speedup 1 --sysid $SYSID --slave 0 --defaults '$CURRENT_PARAM' --sim-address=127.0.0.1 -I$INSTANCE > '$UAV_DIR/arduplane.log' 2>&1 &
      ARDUPLANE_PID=\$!
      for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30; do
          if ss -ltn 2>/dev/null | awk '{print $4}' | grep -q ":$SITL_TCP_PORT$"; then
              break
          fi
          sleep 1
      done
      mavproxy.py --retries 5 --out 127.0.0.1:$MAVPROXY_OUT_PORT --master tcp:127.0.0.1:$SITL_TCP_PORT --sitl 127.0.0.1:$SITL_BRIDGE_PORT --out 127.0.0.1:$PORT --console > '$UAV_DIR/mavproxy.log' 2>&1
      kill \$ARDUPLANE_PID 2>/dev/null || true
    "; then
        sleep 2
        if ! screen -S uav$SYSID -Q select . >/dev/null 2>&1; then
            echo "❌ UYARI: uav$SYSID screen oturumu başlatılamadı — devam ediliyor"
        fi
    else
        echo "❌ HATA: uav$SYSID için screen komutu başarısız oldu"
        exit 1
    fi
    
    sleep 5  # Daha uzun bekle - instance'lar önem sırasına göre başlasın
done

echo ""
echo "✓ Tüm sistemler başlatıldı"
echo ""
echo "Screen session'ları:"
screen -ls | grep -E "gazebo|uav"

# --- 5. TERMINAL TAB'LARINI AÇ ---
sleep 5
echo ""
echo "Terminal tab'ları açılıyor..."

if command -v gnome-terminal >/dev/null 2>&1 && [ -n "${DISPLAY:-}" ]; then
    gnome-terminal --tab --title="Gazebo" -- bash -c "screen -r gazebo; exec bash" &
    sleep 1

    for (( i=1; i<=$PLANE_COUNT; i++ ))
    do
        gnome-terminal --tab --title="UAV$i" -- bash -c "screen -r uav$i; exec bash" &
        sleep 1
    done
else
    echo "ℹ️  gnome-terminal bulunamadı ya da DISPLAY yok; screen oturumları kullanılacak."
fi

echo "✓ Hazır! Gazebo'da uçakları göreceksiniz."
echo ""s
echo "Console komutları (screen'de):"
echo "  arm throttle 1000"
echo "  mode guided"
echo "  takeoff 50"