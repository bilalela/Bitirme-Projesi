# Git Workflow Türkçe Rehberi - Bitirme Projesi

## 📌 Özet

Bu proje GitHub'da versiyon kontrolü ile yönetilecektir. Böylece:
- ✅ Herhangi bir noktaya geri dönebilirsiniz
- ✅ Değişikliklerin geçmişini görebilirsiniz
- ✅ Farklı branch'lerde deney yapabilirsiniz
- ✅ Takım üyeleriyle kolayca paylaşabilirsiniz

---

## 🚀 Başlangıç: GitHub Hazırlığı

### 1️⃣ GitHub Hesabı Oluştur (Eğer yoksa)
- https://github.com/signup
- Email + şifre gir
- Verify email

### 2️⃣ Yeni Repository Oluştur
```
1. https://github.com/new aç
2. Repository name: Bitirme-Projesi
3. Description: UAV Swarm Simulation
4. Public seç (isteğe bağlı)
5. Create Repository butonuna tıkla
```

### 3️⃣ GitHub Token Oluştur (HTTPS Yöntemi - EN KOLAY)

```bash
1. GitHub → Sağ üstteki profil foto → Settings
2. Developer settings → Personal access tokens
3. Tokens (classic) → Generate new token (classic)
4. Note: "Bitirme-Projesi-Access"
5. Expiration: 90 days
6. Scopes (seç):
   ☑ repo (full control of repositories)
   ☑ workflow
7. Generate token
8. 🔐 TOKEN'I KOPYALA VE SAKLA!
```

### 4️⃣ Git Credential Helper Ayarla

Terminal'de:
```bash
git config --global credential.helper store
```

Bu ayarladıktan sonra ilk push'ta token'ı gizli yerinde tutacak.

---

## 📝 Daily Workflow (Günlük Çalışma)

### Adım 1: Değişiklikleri Kontrol Et

```bash
cd "/home/bilal/Bitirme Projesi"
git status
```

**Çıktı örneği:**
```
On branch master
Changes not staged for commit:
  modified:   uavs/uav1/scripts/swarm_master_controller.py
  modified:   SITL_Models/Gazebo/config/uav0.param

Untracked files:
  telemetry_uav1_20260509.json      ← Ignore (auto-generated)
```

### Adım 2: Değişiklikleri Staging'e Al

```bash
# Tüm değişiklikleri ekle (gitignore ignored files'ı otomatik atlar)
git add -A

# VEYA seçeli ekle:
git add uavs/uav1/scripts/swarm_master_controller.py
git add SITL_Models/Gazebo/config/uav0.param
```

### Adım 3: Diff'i Gözden Geçir (Opsiyonel ama Tavsiye Edilir)

```bash
git diff --cached
```

Bu komutu çalıştırarak tam olarak neler değiştiğini görebilirsiniz.

### Adım 4: Commit Yap

```bash
# Kısa commit (basit değişiklikler)
git commit -m "🐛 Fix formation offset calculation in swarm_master_controller"

# Detaylı commit (karmaşık değişiklikler)
git commit -m "🚀 Add rear-guard task assignment

Implemented enemy tracking:
- Added _update_enemy_position() method
- Slaves 2-3 now track enemy from 20m behind
- Deployed rear-guard formation angles

Closes #15"
```

**Commit Message Kuralları:**
- İlk satır 50 karaktere kısa olsun
- Emoji kullan (opsiyonel ama güzel):
  - 🚀 = Yeni feature
  - 🐛 = Bug fix
  - 📝 = Dokümentasyon
  - ⚡ = Performance
  - 🔧 = Config/setup
  - 🎨 = Code refactor
  - ❌ = Remove/deprecate

### Adım 5: Push Et (GitHub'a Yükle)

```bash
git push
```

**İlk push'ta:**
```
Username: BilalGitHubKullanıcıAdın
Password: YOUR_GITHUB_TOKEN
```

**Sonraki push'lar:** Credential helper otomatik yapacak.

---

## 🎯 Hızlı Push Komutu (One-Liner)

Dosya değiştirdikten hemen sonra:

```bash
git add -A && git commit -m "📝 Your message here" && git push
```

Veya dahası daha hızlı (script kullanarak):

```bash
# Repoyu klon ettikten sonra
./GIT_QUICK_START.sh
```

---

## 🌳 Branch Yönetimi (İleri Kullanım)

### Durum 1: Riskli Bir Feature Deneyeceğin

```bash
# Yeni branch oluştur
git checkout -b feature/missile-system

# Değişiklikleri yap, commit et
git add -A
git commit -m "🚀 Implement missile firing system"

# Push et (GitHub'a yeni branch olarak)
git push -u origin feature/missile-system

# GitHub web'de Pull Request oluştur
# → Merge et (veya discard et)
```

### Durum 2: Çalışmaya Geri Dön

```bash
# Main branch'e dön
git checkout main

# Veya master (eski isim)
git checkout master

# Güncel al
git pull
```

### Durum 3: Branch'leri Yönet

```bash
# Tüm branch'leri gör
git branch -a

# Branch sil (lokal)
git branch -d feature/missile-system

# Force sil
git branch -D feature/missile-system
```

---

## 🔄 Geri Dönme (Undo/Rollback)

### Senaryo 1: Henüz Commit Etmemişsin

```bash
# Tüm local değişiklikleri sıfırla
git checkout .

# VEYA belirli bir dosyayı sıfırla
git checkout -- path/to/file.py
```

### Senaryo 2: Commit Ettim Ama Push Etmedim

```bash
# Son commit'i geri al (değişiklikleri tut)
git reset --soft HEAD~1

# VEYA tamamen sil
git reset --hard HEAD~1

# Değişiklikleri tekrar düzenle ve yeniden commit et
```

### Senaryo 3: Push Ettim! 😱

```bash
# Hata var, geri almak istiyorum
git revert HEAD

# Bu yeni bir commit oluşturacak (safe)
git push
```

### Senaryo 4: N Commit Geri Almak

```bash
# Son 3 commit'i geri al
git reset --soft HEAD~3

# Değişiklikleri tut ama yeni bir commit'te birleştir
git commit -m "Refactored last 3 commits"
git push --force-with-lease  # ⚠️ Dikkat! Sadece kendi branch'inde
```

---

## 📊 Log & History Görüntüleme

### Commit Geçmişini Gör

```bash
# Son 10 commit'i listele
git log --oneline -n 10

# Grafik gösterim (branch'ler görünür)
git log --graph --oneline --all

# Detaylı göster
git log --pretty=format:"%h - %an - %s" -n 5
```

### Belirli Bir Dosyanın Geçmişini Gör

```bash
git log --oneline -- path/to/file.py

# Dosyada kimin neyi değiştirdiğini gör
git blame path/to/file.py
```

### Önceki Bir Versiyonu Gör

```bash
# Commit hash'i kopyala (git log'dan)
git show 859f3a7  # Tüm değişiklikleri göster

# Dosyanın eski halini gör
git show 859f3a7:uavs/uav1/scripts/swarm_master_controller.py
```

---

## 🆘 Sık Karşılaşılan Sorunlar

### ❌ "fatal: not a git repository"

```bash
cd "/home/bilal/Bitirme Projesi"
git status
```

Bu klasör git repository değilse:
```bash
git init
git add -A
git commit -m "Initial commit"
```

### ❌ "error: failed to push some refs to origin"

```bash
# Çakışan değişiklikleri çöz
git pull origin master

# Merge conflict'ları düzenle (metin editörde)
# Sonra
git add -A
git commit -m "Merge conflict resolved"
git push
```

### ❌ "error: src refspec main does not match any"

```bash
# Branch ismini kontrol et
git branch

# Main yerine master mı kullanıyor?
git push origin master

# VEYA master'ı main'e yeniden adlandır
git branch -M main
git push origin main
```

### ❌ "Your branch is ahead of origin by X commits"

```bash
# Push etmeyi unut musunuz?
git push
```

### ❌ "Token/Authentication Failed"

```bash
# Credential helper temizle
git config --global --unset credential.helper

# Yeniden konfigüre et
git config --global credential.helper store

# Sonra git push yap (yeni token'ı sor)
```

---

## ⚡ Cheat Sheet

```bash
# Status & Log
git status                                    # Mevcut durum
git log --oneline -n 10                      # Son 10 commit

# Add, Commit, Push
git add -A                                    # Tüm değişiklikleri ekle
git commit -m "Message"                      # Commit
git push                                      # Push

# Branching
git checkout -b feature/name                 # Yeni branch oluştur
git checkout master                          # Branch değiştir
git branch -d feature/name                   # Branch sil

# Undo
git checkout .                                # Tüm değişiklikleri sıfırla
git reset --soft HEAD~1                      # Son commit'i geri al
git revert HEAD                               # Son commit'i tersine çevir

# Remote
git remote -v                                 # Remote'ları listele
git pull                                      # Master'dan çek
git fetch                                     # Güncellemeleri indir (merge etme)

# Diff & Show
git diff                                      # Unstaged değişiklikleri gör
git diff --cached                             # Staged değişiklikleri gör
git show 859f3a7                              # Commit detaylarını gör

# Cleanup
git clean -fd                                 # Untracked files'ı sil
git reset --hard HEAD                        # Tüm değişiklikleri sıfırla
```

---

## 📌 Best Practices

✅ **YAPMAN GEREKEN:**
- Her mantıklı değişiklikten sonra commit et
- Açıklayıcı commit message'ları yaz
- Push etmeden `git status` kontrol et
- Büyük değişiklikler için branch oluştur
- `git pull` ile güncel kalmaya çalış

❌ **YAPMA:**
- `git push --force` (master/main'de)
- Tüm projeyi tek commit'te push etme
- Boş commit message (git commit -m "")
- Şifre, token, API key'i commit etme
- `.gitignore` dosyasını silme

---

## 🎓 İleri Konular (İsteğe Bağlı)

### Stash (Geçici Depolama)
```bash
# Değişiklikleri geçici depola
git stash

# Stash'ı geri al
git stash pop

# Tüm stash'ları listele
git stash list
```

### Rebase (History Düzeltme)
```bash
# Son 3 commit'i interactive rebase
git rebase -i HEAD~3
# pick → reword (mesaj değiştir)
# pick → squash (birleştir)
```

### Tag (Release Marker)
```bash
# Version tag oluştur
git tag v1.0.0

# Push et
git push origin v1.0.0
```

---

## 📞 Yardım Kaynaakları

- **Git Docs:** https://git-scm.com/doc
- **GitHub Docs:** https://docs.github.com/
- **Oh My Git!:** https://ohmygit.org (interaktif öğrenme)
- **GitHub Desktop:** GUI alternatifi (https://desktop.github.com/)

---

**Herhangi bir sorun yaşarsan bize sor!** 🆘
