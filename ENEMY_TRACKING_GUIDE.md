# 🎯 Enemy Tracking Guide - Swarm Master Controller

**Tarih:** 9 Mayıs 2026  
**Özellik:** Real-time Enemy UAV (UAV6) tracking with Slave 2 autonomous pursuit

---

## 📋 Senaryo

1. **Tüm Uçakları Havalandır**
   - Terminal 1'de `bash baslat.sh` ile Gazebo + tüm SITL instance'ları başlat

2. **Master Controller Çalıştır**
   - Terminal 2'de `python3 uavs/uav1/scripts/swarm_master_controller.py` çalıştır

3. **Formation Kurulması**
   - Master controller'da `arm` komutu gir (tüm uçaklar ARMED)
   - `takeoff` komutu gir (50m'ye kalk)
   - Tüm slave'ler master'i takip etmeye başlar

4. **Enemy Tracking Başlat** ⭐
   - Master controller'da `enemy_track on` komutu gir
   - **Slave 2, enemy UAV'nin 20m arkasında otonom olarak takip etmeye başlar**

5. **İzleme Durdurmak**
   - `enemy_track off` komutu gir

---

## 🎮 Komutlar

### Master Controller Interactive Menu

```
>>> arm                      # Tüm uçakları ARM et
>>> takeoff                  # 50m'ye kalk (formation başlat)
>>> enemy_track on           # 🎯 Slave 2 enemy tracking (20m arkada)
>>> enemy_track off          # Tracking'i durdur
>>> mission status           # Tüm uçakların durumunu göster
>>> status                   # Detaylı status
>>> exit                     # Çık
```

---

## 🔧 Teknik Detaylar

### 1. Formation Offsets (Master takip mesafesi)

**Artırıldı** (daha geniş formation):

```python
2: (-4.0, -2.0)   # Sol arka: 4m south, 2m west
3: (-4.0, 2.0)    # Sağ arka: 4m south, 2m east
4: (-6.0, -2.0)   # Sol flanş: 6m south, 2m west
5: (-6.0, 2.0)    # Sağ flanş: 6m south, 2m east
```

**Eski (daha yakın):**
```
2: (-1.5, -0.8)
3: (-1.5, 0.8)
4: (-3.0, -0.8)
5: (-3.0, 0.8)
```

### 2. Slave 2 Enemy Tracking Fonksiyonu

```python
def track_enemy_slave2(self):
    """Slave 2'yi enemy'nin 20m arkasında sürekli takip etmesini sağla"""
    # - Enemy konumunu sürekli oku
    # - Slave 2'nin hedef konumunu hesapla (20m behind)
    # - Her 2 saniyede bir güncelle
    # - Mesafeyi logla (5 güncellede bir)
```

**Algoritma:**
1. Enemy UAV'nin konumunu al
2. 20m arkasında takip konumunu hesapla: `enemy_position - 20m (north)`
3. Slave 2'ye `simple_goto(target_location)` komutu gönder
4. 2 saniye bekle
5. Tekrarla

### 3. Distance Calculation

Haversine formülü kullanarak GPS mesafeleri hesaplanır:

```
distance = earth_radius * central_angle
```

---

## 📊 Kontrol Akışı

```
Master Controller (UAV1)
    ↓
    └─→ arm_all()           [Tüm uçak ARMED]
    ↓
    └─→ takeoff_all()       [50m yüksek, tüm slave'ler master takip]
    ↓
    └─→ enemy_track on      🎯 [Slave 2 enemy tracking START]
              ↓
         track_enemy_slave2()
              ↓
         while enemy_tracking_active:
              ├─→ enemy_position = get_enemy_location()
              ├─→ target_location = 20m_behind_enemy
              ├─→ slave2.simple_goto(target_location)
              └─→ sleep(2)
    ↓
    └─→ enemy_track off     🛑 [Slave 2 enemy tracking STOP]
```

---

## 🎯 Slave 2 Peşi Sıra Takip Mantığı

### Başlangıç
- Enemy: Lat=-35.365, Lon=149.166, Alt=50m
- Slave 2: Lat=-35.360, Lon=149.160, Alt=50m (Master'in sol arkasında)

### Enemy Tracking Aktif
- Her 2 saniyede: Enemy'nin `20m güney` pozisyonunu hesapla
- Slave 2'ye `simple_goto()` komutu gönder → ArduPilot autopilot alır
- Slave 2 otomatik olarak target pozisyonuna yönelir

### Beklenen Davranış
```
Zaman  │ Enemy Pos              │ Slave 2 Target Pos       │ Mesafe
────────┼────────────────────────┼──────────────────────────┼─────────
0s     │ (35.365, 149.166)      │ (35.365-0.0002, 149.166) │ 20m
2s     │ (35.364, 149.167)      │ (35.364-0.0002, 149.167) │ ~20m
4s     │ (35.363, 149.168)      │ (35.363-0.0002, 149.168) │ ~20m
...    │ ...                    │ ...                      │ ~20m
```

---

## 💡 Notlar

1. **Formation Takip**: Diğer slave'ler (3,4,5) her zaman master'i takip etmeye devam eder
2. **Slave 2 Dual Mode**: 
   - Normal durum: Master'i (-4, -2) offsetinde takip
   - Enemy tracking aktif: Enemy'nin 20m arkasında takip
3. **Autonomous Pursuit**: Slave 2, ArduPilot autopilot sayesinde otonom olarak takip eder
4. **Mesafe Loglama**: Her 10 saniyede bir mesafe yazdırılır (5 güncelleme × 2 saniye)

---

## 🛡️ Error Handling

```python
# Enemy bağlı değilse
❌ Enemy vehicle veya Slave 2 bağlı değil

# Telemetri hazır değilse (GPS/altitude bilgisi yok)
→ 1 saniye bekle, tekrar dene

# Exception oluşursa
❌ Tracking hatası: [exception details]
→ Gracefully exit, cleanup

# User Ctrl+C basarsa
🛑 Slave 2 tracking durduruldu
```

---

## 🚀 Advanced: Custom Offsets

Eğer farklı bir offset kullanmak istersen (örn. 30m arkada, 5m solda):

```python
# track_enemy_slave2() fonksiyonunda satır 687'yi değiştir:

# Şu anki (20m arkada, center):
target_loc = self.get_location_metres(
    LocationGlobalRelative(enemy_loc.lat, enemy_loc.lon, enemy_alt),
    -20,  # 20m behind
    0,    # Center
    enemy_alt
)

# Yeni örnek (30m arkada, 5m solda):
target_loc = self.get_location_metres(
    LocationGlobalRelative(enemy_loc.lat, enemy_loc.lon, enemy_alt),
    -30,  # 30m behind
    -5,   # 5m west (left)
    enemy_alt
)
```

---

## 📝 Komut Örnekleri

### Tam Senaryo

```bash
# Terminal 1: Gazebo + SITL başlat
bash baslat.sh

# Terminal 2: Master controller
python3 uavs/uav1/scripts/swarm_master_controller.py

# Master controller'da:
>>> arm
>>> takeoff
>>> mission status
>>> enemy_track on      # 🎯 Slave 2 enemy tracking START!

# Biraz bekle, tracking durumunu gör
[SLAVE2_TRACK] Enemy: (-35.365, 149.166) | Slave2 distance: 19.8m
[SLAVE2_TRACK] Enemy: (-35.364, 149.167) | Slave2 distance: 20.1m

>>> enemy_track off     # Tracking STOP
>>> exit
```

---

## ✅ Verification Checklist

- [x] Formation offsets artırıldı (1.5→4, 3→6 metre)
- [x] `track_enemy_slave2()` fonksiyonu eklendi
- [x] `_calculate_distance()` (Haversine) eklendi
- [x] `enemy_track on/off` komutları interaktif menu'ye eklendi
- [x] Continuous 20m tracking loop implemente edildi
- [x] Distance loglama her 10 saniyede yapılıyor
- [x] Error handling ve cleanup eklendi
- [x] Syntax check passed ✓

---

## 🎓 Nasıl Çalışır?

**Teknoloji Stack:**
- **DroneKit**: Vehicle kontrol API
- **ArduPilot**: Autopilot ve flight control
- **Gazebo**: Physics simulation
- **GPS/Haversine**: Konumlar arası mesafe

**Key Components:**
1. `swarm_master_controller.py` - Ana swarm koordinatörü
2. `track_enemy_slave2()` - Real-time enemy tracking loop
3. `simple_goto()` - ArduPilot autopilot komut gönderme
4. Continuous update loop (2 saniye interval)

---

**Hazırsın! Senaryo'yu dene! 🚀**
