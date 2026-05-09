# Simülasyon Başlatma Rehberi

## 🚀 Hızlı Başlangıç (1 Komut)

Simülasyonun tamamını başlatmak için:

```bash
cd ~/Bitirme\ Projesi && bash baslat.sh
```

Bu komut otomatik olarak:
1. ✅ Gazebo simülasyon ortamını başlatır
2. ✅ 4 adet ArduPilot SITL instance'ını başlatır (UAV1-4)
3. ✅ Her UAV'ye 2'şer füze yükler (sol + sağ kanat)
4. ✅ Kamerası aktif UAV'nin (UAV1) canlı stream'ini başlatır

---

## 📋 Terminal Yapısı

Script çalıştırıldığında **gnome-terminal** içinde birden fazla tab açılacak:

```
Terminal Tabs:
├── Gazebo          → Simülasyon motoru (3D görünüş)
├── UAV1 (Master)   → ArduPilot SITL Instance #1 (Port: 15550)
├── UAV2 (Slave)    → ArduPilot SITL Instance #2 (Port: 15560)
├── UAV3 (Slave)    → ArduPilot SITL Instance #3 (Port: 15570)
└── UAV4 (Slave)    → ArduPilot SITL Instance #4 (Port: 15580)
```

---

## 🎮 QGroundControl Bağlantısı

Simülasyon çalışırken **QGroundControl** ile bağlan:

```
1. QGroundControl aç
2. Sol üstte "+" butonuna tıkla (Add Connection)
3. Bağlantı Ayarları:
   - Protocol: UDP
   - Listening Port: 15550  (Master UAV için)
4. "Connect" butonuna tıkla
```

**Diğer UAV'lere bağlanmak için:**
- UAV2: Port 15560
- UAV3: Port 15570
- UAV4: Port 15580

---

## 📊 Sistem Portu Yapısı

| UAV | SYSID | SITL Port | QGC Port | Kamera |
|-----|-------|-----------|----------|--------|
| UAV1 (Master) | 1 | 15550 | 15550 | ✅ Aktif |
| UAV2 (Slave) | 2 | 15560 | 15560 | ✅ Aktif |
| UAV3 (Slave) | 3 | 15570 | 15570 | ✅ Aktif |
| UAV4 (Slave) | 4 | 15580 | 15580 | ✅ Aktif |
| UAV5 (Slave) | 5 | 15590 | 15590 | ✅ Aktif |
| UAV6 (Future Enemy) | 6 | 15600 | 15600 | ✅ Aktif |

---

## 🛑 Simülasyonu Durdurma

Terminal penceresini kapat veya:

```bash
# Tüm Gazebo işlemlerini öldür
pkill -f gz

# Tüm ArduPilot SITL işlemlerini öldür
pkill -f sim_vehicle.py

# Tüm terminal pencerelerini kapat
pkill -f gnome-terminal
```

---

## 🔧 Manuel Başlatma (İleri Kullanıcılar)

Eğer script yerine manuel başlatmak istersen:

### 1️⃣ Gazebo Başlat
```bash
export GAZEBO_MODEL_PATH="$HOME/Bitirme\ Projesi/ardupilot_gazebo/models:$GAZEBO_MODEL_PATH"
export GAZEBO_RESOURCE_PATH="$HOME/Bitirme\ Projesi/ardupilot_gazebo/worlds:$GAZEBO_RESOURCE_PATH"

cd ~/Bitirme\ Projesi/ardupilot_gazebo/worlds
gz sim -v4 -r vtail_runway_planes.sdf
```

### 2️⃣ UAV SITL'leri Başlat (Her UAV için ayrı terminal)

**UAV1 (Master):**
```bash
cd ~/uavs/uav1
sim_vehicle.py -v ArduPlane -f plane --model JSON \
  --add-param-file=$HOME/SITL_Models/Gazebo/config/uav0.param \
  --out=0.0.0.0:15550 --out=127.0.0.1:15550 --out=127.0.0.1:16550 \
  --console -I0 --sysid 1
```

**UAV2 (Slave):**
```bash
cd ~/uavs/uav2
sim_vehicle.py -v ArduPlane -f plane --model JSON \
  --add-param-file=$HOME/SITL_Models/Gazebo/config/uav1.param \
  --out=0.0.0.0:15560 --out=127.0.0.1:15560 \
  --console -I1 --sysid 2
```

(Benzer şekilde UAV3 ve UAV4 için port 15570, 15580)

---

## 🎯 İlk Test Adımları

1. **Simülasyonu başlat:** `bash baslat.sh`
2. **Gazebo penceresinde UAV'leri gör**
3. **QGroundControl'u aç ve bağlan**
4. **Master UAV'yi arm et:**
   ```
   QGC → Vehicle → Action → Arm
   ```
5. **Test misyonu gönder:**
   - QGC → Plan View
   - Waypoint'ler ekle
   - Upload & Start

---

## 📝 Log Dosyaları

Simülasyon sonrasında log dosyaları şurada bulunabilir:
- UAV1 logs: `~/uavs/uav1/logs/`
- UAV2 logs: `~/uavs/uav2/logs/`
- UAV3 logs: `~/uavs/uav3/logs/`
- UAV4 logs: `~/uavs/uav4/logs/`

---

## ⚠️ Sorun Giderme

### Gazebo Başlamıyor
```bash
# Model path'ini kontrol et
echo $GAZEBO_MODEL_PATH

# Ya da manuel olarak ayarla
export GAZEBO_MODEL_PATH="$HOME/Bitirme\ Projesi/ardupilot_gazebo/models"
```

### SITL Başlamıyor
```bash
# ArduPilot kurulu mu kontrol et
which sim_vehicle.py

# Ya da tam yolunu kullan
/home/bilal/ardupilot/Tools/autotest/sim_vehicle.py
```

### UAV'lerin Gazebo'da Görünmemesi
```bash
# Gazebo modeli bulamıyorsa
export GZ_SIM_RESOURCE_PATH="$HOME/Bitirme\ Projesi/ardupilot_gazebo/models"
```

---

## 🎮 Swarm Kontrol (Python Script)

Master UAV'den swarm komutları göndermek için:

```bash
python3 ~/Bitirme\ Projesi/uavs/uav1/scripts/swarm_master_controller.py
```

Bu script:
- Master UAV'yi lider olarak kullanır
- Slave'leri master konumuna göre ofsetli formation ile günceller
- **Durum Makinesi**: IDLE → ARMED → FORMATION → SEARCH → ENGAGE → RTB
- **Ana komutlar**:
  - `mission start` - Otonom swarm görevini başlat
  - `mission stop` - Görev durdur, eve dön
  - `mission status` - Görev durumunu göster
  - `arm`, `takeoff`, `status` - Manuel kontrol
  - `fire <vehicle> <hardpoint>` - Füze at

---

**Hepsi bu kadar! Simülasyon şimdi tamamen çalışacak. 🚀**
