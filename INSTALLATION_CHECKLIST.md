# 🚀 Bitirme Projesi - Kurulum ve Kontrol Listesi

**Son Güncelleme: 2026-05-06**

---

## ✅ Yapılan Düzeltmeler Özeti

### 1. **Füze Modelleri**
- Missille ile ilgili tüm dosyalar ve world include'ları kullanıcı isteğiyle kaldırıldı.
  - İlgili model dosyaları: `ardupilot_gazebo/models/missile/` (silindi)

### 2. **Dünya Yapılandırması** (`ardupilot_gazebo/worlds/vtail_runway_planes.sdf`)
- [x] Füze pozisyonları: Her uçağın SOL KANADININ ALTINA monte
- [x] Konumlar doğru hesaplanmış:
  - missile_0 → plane_0 (-0.15, +0.27, 0.12)
  - missile_1 → plane_1 (9.85, +0.27, 0.12)
  - missile_2 → plane_2 (19.85, +0.27, 0.12)
  - missile_3 → plane_3 (29.85, +0.27, 0.12)
- [x] Fixed joint bağlamaları: Füzeler uçakla birlikte hareket ediyor

### 3. **UAV Modelleri** (mini_talon_vtail_1-4)
- [x] FDM portları doğru:
  - plane_0: 9002/9003 (Instance 0)
  - plane_1: 9012/9013 (Instance 1)
  - plane_2: 9022/9023 (Instance 2)
  - plane_3: 9032/9033 (Instance 3)
- [x] missile_hardpoint_port/starboard linkler tanımlı
- [x] ArduPilotPlugin konfigürasyonu uygun

### 4. **Başlatma Scripti** (`baslat.sh`)
- [x] Hata kontrolü eklendi
- [x] Timing iyileştirmeleri
- [x] Gazebo resource path düzeltmesi
- [x] Detaylı logging

---

## 🧪 Test Edecek Şeyler

### Adım 1: Gazebo Simülasyonunu Başlat
```bash
cd ~/Bitirme\ Projesi
bash baslat.sh
```

**Beklenen Çıktı:**
```
======================================
Gazebo simülasyonu başlatılıyor...
======================================
⏳ Gazebo yükleniyor (20 saniye bekleniyor)...
✓ Gazebo başlatıldı

======================================
4 adet uçak başlatılıyor...
======================================

UAV1 başlatılıyor:
  - SYSID: 1
  - Port: 15550
  - Instance: 0
  ...
```

**Gazebo'da görülmesi gereken:**
- 4 Mini Talon uçağı (beyaz)
- Her uçağın sol kanadının altında 1 füze (zeytin yeşili + kırmızı başlık)
- Füzeler uçaklar ile yapışık/sabit (hareket ettiğinde birlikte hareket)

---

### Adım 2: QGroundControl Bağlantısı
```
TCP 127.0.0.1:15550 (Master - UAV1)
```

**Beklenen Sonuç:**
- "Armed" statusu
- GPS koordinatları görülmeli
- Telemetri verileri akmalı

---

### Adım 3: ArduPilot Console Komutları

Her UAV için screen session açma:
```bash
# Terminal 1: Gazebo
screen -r gazebo

# Terminal 2: UAV1
screen -r uav1
```

**Basit komutlar:**
```
# Mode GUIDED'ı seç
mode guided

# Hava yüksekliğini belirle
takeoff 50

# Verileri kontrol et
param show SIM_SPEEDUP
```

---

## 📋 Dosya Kontrol Listesi

| Dosya | Durum | Açıklama |
|-------|-------|----------|
| `missile/model.sdf` | ❌ (removed) | Füze modeli - silindi |
| `worlds/vtail_runway_planes.sdf` | ✅ | World - füze konumları |
| `models/mini_talon_vtail_1/model.sdf` | ✅ | UAV1 - FDM portları 9002/9003 |
| `models/mini_talon_vtail_2/model.sdf` | ✅ | UAV2 - FDM portları 9012/9013 |
| `models/mini_talon_vtail_3/model.sdf` | ✅ | UAV3 - FDM portları 9022/9023 |
| `models/mini_talon_vtail_4/model.sdf` | ✅ | UAV4 - FDM portları 9032/9033 |
| `baslat.sh` | ✅ | Başlatma scripti - iyileştirildi |
| `README.md` | ✅ | Dokümantasyon güncellendi |

---

## 🔍 Sorun Giderme

### Problem: "No JSON sensor message received"
**Çözüm:**
1. Gazebo tamamen yüklenmiş mi? (20 saniye bekle)
2. ArduPilot SITL başladı mı? (screen -r uav1 kontrol et)
3. FDM portları uyuşuyor mu? (uav1: 9002/9003 vs model.sdf)
4. Instance numaraları doğru mu? (-I0, -I1, -I2, -I3)

### Problem: Füzeler görünmüyor / yanlış yerde
**Kontrol Noktaları:**
- World dosyasında füze <pose>'leri kontrol et
- Joint bağlamaları base_link'e mi bağlı?
- Gazebo 3D view'de füzeler kırmızı + yeşil renkte mi?

### Problem: Uçaklar hareket etmiyor
**Bağlantı Kontrol:**
1. QGroundControl → Mavlink status
2. Param: SIM_SPEEDUP = 1.0
3. Battery: > 0%
4. GPS: 3D Fix

---

## 📞 İletişim Verisi

**Port Haritası:**
| UAV | SYSID | SITL Port | MAVLink Port | Instance |
|-----|-------|-----------|--------------|----------|
| UAV1 | 1 | 9002/9003 | 15550 | 0 |
| UAV2 | 2 | 9012/9013 | 15560 | 1 |
| UAV3 | 3 | 9022/9023 | 15570 | 2 |
| UAV4 | 4 | 9032/9033 | 15580 | 3 |
| UAV5 | 5 | 9042/9043 | 15590 | 4 |
| UAV6 | 6 | 9052/9053 | 15600 | 5 |

---

## ⚠️ Önemli Notlar

1. **Füzeler uçakla birlikte hareket ediyor** - camera gibi sabit bağlanmış
2. **Her uçağın ayrı ArduPilot instance'ı** - Independent flight control
3. **Master-Slave mimarisi** - UAV1 swarm koordinatörü
4. **JSON protokolü** - Gazebo-ArduPilot haberleşme standardı

---

## 🎯 Sonraki Adımlar

- [ ] Füze atış plugin'i (C++ Gazebo)
- [ ] Proportional Navigation guidance
- [ ] Target tracking algoritması
- [ ] ADS (Air Defense System) simülasyonu
- [ ] Multi-UAV koordinasyon

