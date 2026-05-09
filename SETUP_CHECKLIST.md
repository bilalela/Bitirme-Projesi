# ✅ Git & GitHub Setup Checklist

## 🟢 TAMAMLANDI (Local'de)

- [x] Git repository initialize edildi (`git init`)
- [x] `.gitignore` oluşturuldu (build artifacts, logs, generated files)
- [x] `.gitkeep` dosyaları oluşturuldu (boş klasörleri korumak için)
- [x] İlk commit yapıldı: `859f3a7 - Initial commit`
- [x] Setup rehberleri yazıldı:
  - `GITHUB_SETUP.md` - Detaylı setup talimatları
  - `GIT_WORKFLOW_TR.md` - Türkçe workflow rehberi
- [x] Quick start script oluşturuldu: `GIT_QUICK_START.sh`
- [x] Local git config ayarlandı (user.name, user.email)

**Mevcut durum:**
```
3 commits, master branch'inde
Proje klasörü GitHub'a bağlanmış değil (henüz)
```

---

## 🔴 TODO: GitHub'a Bağlantı (Senin Yapman Gereken)

### Adım 1: GitHub Hesabında Repository Oluştur
- [ ] https://github.com/new aç
- [ ] Repository name: `Bitirme-Projesi`
- [ ] Description: "UAV Swarm Simulation with Gazebo + ArduPilot SITL"
- [ ] Public seç
- [ ] "Create repository" tıkla
- [ ] Repo URL'ini kopyala (https://github.com/YourUsername/Bitirme-Projesi.git)

### Adım 2: GitHub Personal Access Token Oluştur
- [ ] GitHub → Profil → Settings → Developer settings
- [ ] Personal access tokens → Tokens (classic)
- [ ] Generate new token (classic)
- [ ] Name: "Bitirme-Projesi-Token"
- [ ] Expiration: 90 days (veya 1 year)
- [ ] Scopes: ☑ repo, ☑ workflow
- [ ] "Generate token" tıkla
- [ ] **TOKEN'I SAKLA!** (Sonra görüntülenemez)

### Adım 3: Local Terminal'de Push Hazırlaması
```bash
cd "/home/bilal/Bitirme Projesi"

# Remote origin ekle (HTTPS_URL yerine: https://github.com/YourUsername/Bitirme-Projesi.git)
git remote add origin HTTPS_URL

# Branch'i main'e yeniden adlandır
git branch -M main

# Credential helper'ı ayarla (token'ı saklayacak)
git config --global credential.helper store
```

- [ ] Yukarıdaki komutları çalıştır

### Adım 4: İlk Push
```bash
cd "/home/bilal/Bitirme Projesi"
git push -u origin main
```

- [ ] Push yap
- [ ] Cevab olarak:
  - **Username:** GitHub kullanıcı adın
  - **Password:** TOKEN'ı yapıştır (şifreniz değil!)

### Adım 5: Doğrulama
- [ ] https://github.com/YourUsername/Bitirme-Projesi adresini ziyaret et
- [ ] Tüm dosyaları görebilmen gerekir
- [ ] 3 commit'i görebilmen gerekir (git history'de)

---

## 📋 Kontrol Listesi: Komutları Hazırla

Kopyala-yapıştır için hazır komutlar:

```bash
# 1. Remote ekle
git remote add origin https://github.com/YourUsername/Bitirme-Projesi.git

# 2. Branch'i yeniden adlandır
git branch -M main

# 3. Credential helper'ı ayarla
git config --global credential.helper store

# 4. Doğrula (remote'ları gör)
git remote -v

# 5. İlk push
git push -u origin main
```

**Expected output (Step 5'ten sonra):**
```
Username: YourGitHubUsername
Password: YOUR_GITHUB_TOKEN
Enumerating objects: 24, done.
...
To https://github.com/YourUsername/Bitirme-Projesi.git
 * [new branch]      main -> main
Branch 'main' set up to track remote branch 'main' from 'origin'.
✓ Push successful!
```

---

## 🔄 Sonraki Adımlar: Günlük Kullanım

Push yapıldıktan sonra, normal workflow şu şekilde olacak:

### Her Değişiklikten Sonra:
```bash
git add -A
git commit -m "📝 Açıklayıcı mesaj"
git push
```

### Veya Script Kullanarak:
```bash
./GIT_QUICK_START.sh
```

### Veya One-Liner:
```bash
git add -A && git commit -m "📝 Message" && git push
```

---

## ⏮️ Geri Dönme (Herhangi Bir Noktaya)

Eğer kötü bir şey olursa, hiç endişelenme:

```bash
# Tüm commit'leri gör
git log --oneline

# Belirli bir commit'e geri dön
git reset --hard 859f3a7  # İlk commit'e geri dön

# VEYA güvenli şekilde
git revert HEAD           # Son değişiklikleri tersine çevir (yeni commit)
```

---

## 📞 Sorunlar & Çözümler

### "error: remote origin already exists"
```bash
git remote remove origin
git remote add origin https://github.com/YourUsername/Bitirme-Projesi.git
```

### "fatal: destination path already exists"
```bash
cd "/home/bilal/Bitirme Projesi"
git status  # Eğer .git var, zaten git repo'su
```

### "Username/Password hatası"
```bash
git config credential.helper store  # Tekrar token'ı gir
git push
```

### "fatal: Could not read from remote repository"
```bash
ssh -T git@github.com     # Eğer SSH kullanıyorsan
# veya
git remote -v             # URL'i kontrol et
```

---

## 📊 Git Komut Özeti

```
git status              → Durum kontrol
git log -n 5            → Son 5 commit
git add -A              → Tüm değişiklikleri ekle
git commit -m "msg"     → Commit
git push                → GitHub'a yükle
git pull                → GitHub'dan indir
git checkout -b feature → Yeni branch
git reset --hard HEAD~1 → Undo (dikkat!)
```

---

## 🎯 Bitirme Listesi

- [x] Local git setup tamamlandı
- [x] Rehber dosyaları oluşturuldu
- [ ] GitHub repo oluşturulacak (SENIN YAPACAĞIN)
- [ ] Token oluşturulacak (SENIN YAPACAĞIN)
- [ ] Remote eklenecek (SENIN YAPACAĞIN)
- [ ] İlk push yapılacak (SENIN YAPACAĞIN)

**Hazır mısın? 🚀**

---

## 📧 Hızlı Referans: İlk Push Komutu

Aşağıdaki kodu kopyala-yapıştır (GITHUB_URL ve USERNAME'i değiştir):

```bash
#!/bin/bash
cd "/home/bilal/Bitirme Projesi"

# Değişkenleri ayarla
GITHUB_URL="https://github.com/USERNAME/Bitirme-Projesi.git"

# Remote ekle
git remote add origin $GITHUB_URL

# Branch'i yeniden adlandır
git branch -M main

# Credential helper
git config --global credential.helper store

# Push et
git push -u origin main

echo "✅ Push tamamlandı!"
```

Bunu `push.sh` adıyla kaydet ve çalıştır:
```bash
chmod +x push.sh
./push.sh
```

---

**Not:** Rehber dosyalarını oku (`GIT_SETUP.md` ve `GIT_WORKFLOW_TR.md`).
Herhangi bir sorun yaşarsan, terminal'de `git status` yaz ve çıktıyı kontrol et.
