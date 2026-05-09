# Bitirme Projesi - Swarm UAV ile Füze Simülasyonu

## 📋 Proje Özeti
**Gazebo + SITL ArduPilot + QGroundControl** ile 5 adet İHA (1 Master + 4 Slave) swarm sistemi.
- **Füze Sistemleri**: Hava-Hava (Air-to-Air) ve Hava-Yer (Air-to-Ground)
- **Görüntü İşleme**: Hedef tespiti ve takip (OpenCV)
- **Yer Savunma**: Anti-aircraft sistemler
- **Swarm Kontrolü**: Master-Slave mimarisi

---

## 🗂️ Proje Yapısı

```
Bitirme Projesi/
├── baslat.sh                          # Ana başlatma script'i (4 UAV)
├── yaklasma.sh                        # Alternatif scenario (2 UAV)
├── SITL_Models/
│   └── Gazebo/
│       ├── config/
│       │   ├── mini_talon_vtail.param # Ana param dosyası
│       │   ├── uav0.param             # Master (UAV1)
│       │   ├── uav1.param             # Slave (UAV2)
│       │   ├── uav2.param             # Slave (UAV3)
│       │   └── uav3.param             # Slave (UAV4)
│       └── (sim logları)
├── ardupilot_gazebo/
│   ├── models/
│   │   ├── mini_talon_vtail_1/        # UAV Model 1
│   │   │   ├── model.config
│   │   │   └── model.sdf
│   │   ├── mini_talon_vtail_2/        # UAV Model 2
│   │   ├── mini_talon_vtail_3/        # UAV Model 3
│   │   ├── mini_talon_vtail_4/        # UAV Model 4
│   │   ├── missile/                   # (removed) FÜZE MODEL - silindi
│   │   │   ├── model.config
│   │   │   ├── model.sdf
│   │   │   └── meshes/
│   │   ├── air_defense_system/        # YER SAVUNMA SİSTEMİ (SDF)
│   │   │   ├── model.config
│   │   │   └── model.sdf
│   │   ├── qr/                        # QR hedef markeri
│   │   └── runway/                    # Pist
│   └── worlds/
│       ├── runway_yaklasma.sdf        # Yaklaşma senaryosu
│       └── vtail_runway_planes.sdf    # Ana swarm dünyası
└── uavs/
    ├── uav1/        (Master)          # SYSID=1, Port=15550
    │   ├── logs/
    │   ├── missions/                  # patrol_mission.mission
    │   ├── scripts/
    │   │   ├── swarm_master_controller.py    # Swarm komutları
    │   │   └── telemetry_logger.py          # Veri kaydı
    │   └── telemetry/
    ├── uav2/        (Slave #1)        # SYSID=2, Port=15560
    │   ├── logs/
    │   ├── missions/                  # square_pattern.mission
    │   ├── scripts/
    │   └── telemetry/
    ├── uav3/        (Slave #2)        # SYSID=3, Port=15570
    │   ├── logs/
    │   ├── missions/                  # formation_test.mission
    │   ├── scripts/
    │   │   └── target_detector.py     # Görüntü işleme + hedef tespiti
    │   └── telemetry/
    ├── uav4/        (Slave #3)        # SYSID=4, Port=15580
    ├── uav5/        (Slave #4)        # SYSID=5, Port=15590
    ├── uav6/        (Future Enemy)    # SYSID=6, Port=15600
    └── README.md
```

---

## 🚀 Hızlı Başlangıç

### 1. Swarm Başlat (4 UAV)
```bash
cd ~/Bitirme\ Projesi
bash baslat.sh
```

- **Bu komut otomatik olarak:**
- ✅ Gazebo simülasyon ortamını açar (4 UAV)
- ✅ 4 adet ArduPilot SITL instance'ını başlatır
- ✅ Kamerası aktif UAV'nin canlı stream'ini başlatır

### 4. Master Kontrol (Python)
```bash
python3 ~/Bitirme\ Projesi/uavs/uav1/scripts/swarm_master_controller.py
```

Bu komut şu özellikler ile çalışır:
- **Durum Makinesi**: Otomatik IDLE→ARMED→FORMATION→SEARCH→ENGAGE→RTB geçişi
- **Mission Mode**: `mission start` komutu ile tam otonom swarm görevini başlatır
- **Manual Mode**: `arm`, `takeoff`, `status` ile manuel kontrol mümkün
- **Hedef Tespiti**: Master, 10 saniye arama sonrası simüle hedef tespit eder
- **Görev Dağıtımı**: ENGAGE durumunda slave'lere rol atanır
- Komut satırı menüsü için `mission start` yazın

**Detaylı talimatlar için:** [BASLAT_REHBERI.md](BASLAT_REHBERI.md)

### 2. QGroundControl Bağlan
```
Main Vehicle Bağlantısı: 127.0.0.1:15550 (Master - UAV1)
```

Terminal Tab'ları:
- **Gazebo** → 3D simülasyon ortamı
- **UAV1** → Master (Port 15550)
- **UAV2** → Slave (Port 15560)
- **UAV3** → Slave (Port 15570)
- **UAV4** → Slave (Port 15580)

### 3. Misyon Yükle ve Çalıştır
- QGroundControl → Plan View
- Waypoint'ler ekle
- Upload & Start

### 4. Master Kontrol (Python)
```bash
python3 ~/Bitirme\ Projesi/uavs/uav1/scripts/swarm_master_controller.py
```

---

## 📦 Teknoloji Stack

| Bileşen | Teknoloji | Rol |
|---------|-----------|-----|
| Simülasyon | Gazebo 11+ | Physics engine |
| Autopilot | ArduPilot | UAV kontrolü |
| SITL | ArduPilot SITL | Software-in-the-loop |
| GCS | QGroundControl | Misyon planlama |
| Görüntü İşleme | OpenCV + Python | Target detection |
| Swarm | MAVLink + Python | UAV iletişimi |
| Scripting | Lua + Python | Custom logic |

---

## ✨ İmplante Edilen Modüller

### ✅ Tamamlanan
- [x] Temel swarm mimarisi (4 UAV)
- [x] SITL yapılandırması
- [x] Master-Slave haberleşme
- [x] Telemetri yönetimi
- [x] Misyon dosyaları
- [x] UAV klasör yapısı
- [x] **Füze Modeli** (removed)
- [x] **Yer Savunma Sistemi** (ADS) - SDF + Radar

### 🔨 Geliştirme Aşamasında
- [ ] **Füze Plugin** (C++ Gazebo)
- [ ] **Görüntü İşleme** (Target tracking)
- [ ] **Füze Guidans** (Proportional Navigation)
- [ ] MAVLink füze atış komutları
- [ ] ADS simülasyonu (yer savunma sistemi)

### ⏳ Planlanan
- [ ] Multi-UAV füze koordinasyonu
- [ ] ROS2 entegrasyonu
- [ ] Daha gelişmiş AI targeting
- [ ] 3D görselleştirme

---

## 🛠️ Geçmiş Güncellemeler

### [2026-05-06] Füze Montaj ve Simülasyon Iyileştirmeleri ✅
**Yapılan Değişiklikler:**

#### 🎯 Füze Modeli (model.sdf)
- ✅ **Askeri standart renkler:**
  - Warhead: Koyu kırmızı (RGB: 0.70, 0.10, 0.10)
  - Fuselage: Zeytin yeşili (RGB: 0.45, 0.55, 0.35)
  - Tail fins: Koyu yeşil
- ✅ **Boyut optimizasyonu:**
  - Çap: 0.024m (ince, gerçekçi)
  - Warhead uzunluğu: 0.065m
  - Fuselage uzunluğu: 0.30m
  - Tail fins eklendi (4x aerodinamik stabil kanat)
- ✅ **Kitle azaltıldı:** 5.0kg → 2.5kg (gerçekçi)
- ✅ **Sensörler:** Seeker camera + IMU (füze kontrol için)

#### 🛫 Dünya Yapılandırması (vtail_runway_planes.sdf)
- ✅ **Füze konumlandırması - HER UÇAĞIN SOL KANADININ ALTINA:**
  ```
  plane_0 (0, 0, 0.2)         → missile_0 (-0.15, 0.27, 0.12)
  plane_1 (10, 0, 0.2)        → missile_1 (9.85, 0.27, 0.12)
  plane_2 (20, 0, 0.2)        → missile_2 (19.85, 0.27, 0.12)
  plane_3 (30, 0, 0.2)        → missile_3 (29.85, 0.27, 0.12)
  ```
- ✅ **Fixed joint bağlamaları:**
  - `missile_0_to_plane_0` → `plane_0::base_link` 
  - `missile_1_to_plane_1` → `plane_1::base_link`
  - `missile_2_to_plane_2` → `plane_2::base_link`
  - `missile_3_to_plane_3` → `plane_3::base_link`
- ✅ **Füzeler uçakla birlikte hareket ediyor** (camera parametreli)

#### 📜 Başlatma Scripti (baslat.sh)
- ✅ **Geliştirilmiş hata kontrolü:**
  - World dosyası varlık kontrol
  - Param dosyası varlık kontrol
  - ArduPilot başlatma hataları yakalama
- ✅ **Timing iyileştirmeleri:**
  - Gazebo yükleme: 20 saniye (eski: 15)
  - Instance yükleme arası: 5 saniye (eski: 3)
  - Gazebo resource path düzeltildi
- ✅ **Detaylı logging:**
  - Her UAV başlatma sırasında info
  - Screen session kontrol
  - Debug çıktısı (2>&1)

#### 🔧 ArduPilot-Gazebo İletişimi
- ✅ **FDM Port eşleştirmeleri doğrulandı:**
  - Instance 0 → Port 9002/9003 (plane_0)
  - Instance 1 → Port 9012/9013 (plane_1)
  - Instance 2 → Port 9022/9023 (plane_2)
  - Instance 3 → Port 9032/9033 (plane_3)
- ✅ **JSON model kullanılıyor** (--model JSON)
- ✅ **lockstep senkronizasyonu:** 1 (simülasyon-ArduPilot sync)

---

### [2026-05-05] Füzeleri UAV'lara Entegre Etme
**Eklenen:**
- UAV klasörleri yapısı (uav1-5)
- Swarm master controller (Python)
- Target detector (OpenCV template)
- Telemetry logger
- Misyon dosyaları templates
- Ana README dosyası

---

## 🔗 Bağlantılar

- **Gazebo Docs**: https://gazebosim.org/
- **ArduPilot Docs**: https://ardupilot.org/
- **MAVLink Protokolü**: https://mavlink.io/
- **QGroundControl**: http://qgroundcontrol.com/

---

## 📞 Notlar

- Tüm UAV'lar aynı Gazebo dünyasında çalışır
- SITL instance'ları localhost:15550-15590 portlarında dinler
- Master UAV (uav1) tüm swarm komutlarını koordine eder
- Telemetri JSON formatında kaydedilir

---

**Sonraki Adımlar:**
1. Gazebo Plugin (C++) yazı (füze kontrol & guidance)
2. MAVLink komutları (UAV'lardan füze atış)
3. Hedef takip algoritması (Proportional Navigation)
4. ADS otomatik fire sistemi
