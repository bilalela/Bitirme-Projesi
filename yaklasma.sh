#!/bin/bash

# --- 1. AYARLAR --------------------------------
PLANE_COUNT=4
OUT_IP="100.70.22.107"
EXTRA_OUT_PORT_START=15550
CONFIG_PATH="$HOME/SITL_Models/Gazebo/config"
WORLD_FILE="runway_yaklasma" 
BASE_UAV_DIR="$HOME/uavs"	#Her uçağın başlatıldığı klasör (log dosyaları burda tutulur.)

# UAV_LIST="param_dosyası:kamera_durumu"
UAV_CONFIGS=(
    "mini_talon_vtail:1"
    "mini_talon_vtail:0"
)

PLANE_COUNT=${#UAV_CONFIGS[@]}


# --- 2. TEMİZLİK (Eski süreçleri öldür) ---------------------
echo "Eski Gazebo ve ArduPilot süreçleri temizleniyor..."
pkill -f gz
pkill -f sim_vehicle.py
pkill -f ardupilot
pkill -f xterm
pkill -f mavproxy
sleep 2




# --- 3. GAZEBO BAŞLAT ---
gnome-terminal --tab --title="Gazebo" -- bash -c "gz sim -v4 -r $WORLD_FILE.sdf; exec bash"
# Kısa bir bekleme (Gazebo'nun yüklenmesi için)
sleep 2



# --- 4. UAV DÖNGÜSÜ ---
echo "$UCAK_SAYISI adet uçak yapılandırılıyor..."

for (( i=0; i<$PLANE_COUNT; i++ ))
do
	
	# Veriyi parçala ( : işaretine göre ayırır )
	CONF=${UAV_CONFIGS[$i]}
    PARAM_FILE=${CONF%%:*}  # İki noktanın solunu al
    CAM_STATUS=${CONF##*:}  # İki noktanın sağını al
    
	SYSID=$((i + 1))
	PORT=$((EXTRA_OUT_PORT_START + (i * 10)))
	INSTANCE=$i
	CURRENT_PARAM="$CONFIG_PATH/$PARAM_FILE.param"
	UAV_DIR="$BASE_UAV_DIR/uav$SYSID"
	
	echo "Başlatılıyor: UAV$SYSID | Port: $PORT | Model: $PARAM_FILE"
	
	gnome-terminal \
  --tab \
  --title="UAV$SYSID" \
  -- bash -c "cd $UAV_DIR && \
    sim_vehicle.py \
      -v ArduPlane \
      -f plane \
      --model JSON \
      --add-param-file=$CURRENT_PARAM \
      --out=0.0.0.0:$PORT \
      --out=$OUT_IP:$PORT \
      --console \
      -I$INSTANCE \
      --sysid $SYSID; \
    exec bash"
		
	# Eğer kamera durumu 1 ise komutu gönder
    if [ "$CAM_STATUS" == "1" ]; then
        # Arka planda sessizce çalıştır (Terminal açıp kapatmaya gerek kalmadan doğrudan gönderiyoruz)
        ( sleep 10 && gz topic -t /world/runway/model/plane_$i/link/base_link/sensor/camera/image/enable_streaming -m gz.msgs.Boolean -p 'data: 1' ) &
    fi
    
	sleep 2
	
	
done



echo "Tüm sistemler yapılandırıldı."
