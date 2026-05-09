# GitHub Setup & Push Instructions
# Bilal'ın Bitirme Projesi - Git Workflow

## 📋 Step 1: GitHub Hesabı & Repository Oluşturma

### GitHub'da Yeni Repo Oluştur:
1. https://github.com/new adresine git
2. Repository name: `Bitirme-Projesi` (ya da tercih ettiğin ad)
3. Description: "UAV Swarm Simulation with Gazebo + ArduPilot SITL"
4. Public/Private seç (varsayılan: Public)
5. ❌ "Initialize this repository with a README" seçme (zaten var)
6. ✅ "Create repository" butonuna tıkla

Sana GitHub şu bilgileri gösterecek (örnek):
```
git remote add origin https://github.com/YourUsername/Bitirme-Projesi.git
git branch -M main
git push -u origin main
```

---

## 🔐 Step 2: GitHub Authentication (HTTPS Token veya SSH)

### Seçenek A: HTTPS + Personal Access Token (Kolay)

1. GitHub → Settings → Developer settings → Personal access tokens
2. "Tokens (classic)" → "Generate new token"
3. Token adı: "Bitirme-Projesi-Push"
4. Expiration: 90 days (ya da 1 year)
5. Scopes seç:
   - ✅ repo (full control of repositories)
   - ✅ gist
   - ✅ workflow
6. "Generate token" butonuna tıkla
7. **TOKEN'ı KOPİLA VE SAKLA!** (Bir daha görüntülenemez)

Sonra terminal'de:
```bash
git config --global credential.helper store
# Sonra git push yaptığında token'ı password olarak gir
```

### Seçenek B: SSH Key (Daha güvenli)

```bash
# SSH key oluştur (hâlâ yapmadıysan)
ssh-keygen -t ed25519 -C "bilal@example.com"
# Enter file: ~/.ssh/id_ed25519
# Passphrase: (şifre gir veya boş bırak)

# Public key'i kopyala
cat ~/.ssh/id_ed25519.pub

# GitHub'a ekle:
# Settings → SSH and GPG keys → New SSH key
# Title: "Bitirme Projesi"
# Key: (yukarıdaki çıktıyı yapıştır)

# SSH çalışıyor mu test et
ssh -T git@github.com
```

---

## 🚀 Step 3: Remote Origin Ekle ve Push Et

```bash
cd "/home/bilal/Bitirme Projesi"

# Remote origin ekle (HTTPS örneği)
git remote add origin https://github.com/YourUsername/Bitirme-Projesi.git

# Branch adını main'e değiştir (opsiyonel ama GitHub standardı)
git branch -M main

# İlk push: upstream'i ayarla
git push -u origin main

# Sonraki push'lar: sadece git push yaz
git push
```

**HTTPS ile ilk push'ta:**
```
Username: YourGitHubUsername
Password: YOUR_GITHUB_TOKEN (şifre değil!)
```

---

## ✅ Step 4: Doğrulama

```bash
# Remote'ların listesini göster
git remote -v

# Şuna benzer şekilde görülmeli:
# origin  https://github.com/YourUsername/Bitirme-Projesi.git (fetch)
# origin  https://github.com/YourUsername/Bitirme-Projesi.git (push)
```

GitHub web arayüzünde repo sayfana gidip dosyaları görünceye kadar bekle (~30 saniye).

---

## 📝 Gelecek Güncellemeler: Standard Workflow

Her değişiklik sonrasında:

### Durum Kontrol Et
```bash
git status
# Hangi dosyaların değiştiğini görmek
```

### Değişiklikleri Fark Et (Opsiyonel)
```bash
git diff
# Detaylı diff'i görmek
```

### Değişiklikleri Staging'e Al
```bash
# Tüm değişiklikleri ekle
git add -A

# Veya seçici olarak
git add uavs/uav1/scripts/
git add SITL_Models/
```

### Commit Yap
```bash
git commit -m "📝 Meaningful commit message

Detailed description of changes:
- Feature 1 added
- Bug fix for issue X
- Updated documentation"
```

### Push Et
```bash
git push
# veya first time için
git push -u origin main
```

---

## 🌳 Branching (İleri Kullanım)

Eğer risk almadan yeni feature deneyip gerekirse ana branch'e merge etmek istersen:

```bash
# Yeni branch oluştur
git checkout -b feature/missile-system
# Değişiklikler yap, commit, push et

git push -u origin feature/missile-system

# GitHub web'de Pull Request oluştur
# Review et → Merge et

# Geri ana branch'e dön
git checkout main
git pull
```

---

## 🔄 Geri Dönme (Rollback)

### Son commit'i geri al (henüz push etmemişsen)
```bash
git reset --soft HEAD~1
# Veya tam olarak geri al
git reset --hard HEAD~1
```

### Önceki bir commit'e dön (history bozar ⚠️)
```bash
git log --oneline
git reset --hard COMMIT_HASH
git push --force  # Risk! Dikkat kullan
```

### Belirli dosyayı eski haline getir
```bash
git checkout HEAD~1 -- path/to/file
git commit -m "Revert file to previous state"
```

### Pull request'i açmadan 10 commit geri al
```bash
git reset --soft HEAD~10
git commit -m "Squashed 10 commits"
```

---

## ⚡ Hızlı Referans

```bash
# Ekle, Commit, Push (standart workflow)
git add -A && git commit -m "Update XYZ" && git push

# Status ve log
git status
git log --oneline -n 10
git log --graph --oneline --all  # Güzel görselleştirme

# Değişiklikleri sıfırla
git checkout .  # Tüm local değişiklikleri sıfırla
git clean -fd   # Untracked files'ı sil

# Belirli dosyayı sil (silinmesi commit et)
git rm filename
git commit -m "Remove filename"
```

---

## 📌 Tavsiyeler

✅ **DO:**
- Küçük, mantıklı commit'ler yap (birkaç dosya değişikliği)
- Anlamlı commit message'ları kullan
- Push etmeden önce `git status` kontrol et
- Critical değişiklikler için branch oluştur

❌ **DON'T:**
- Hiç commit message olmadan commit yapma
- Tüm projeyi tek commit'te push etme
- `git push --force` kullanma (master/main branch'de)
- Sensitive data'yı commit'le (token, şifre, API key)

---

## 🆘 Sorun Giderme

### "fatal: destination path already exists and is not an empty directory"
```bash
cd /path/to/repo
git init
```

### "error: remote origin already exists"
```bash
git remote remove origin
git remote add origin https://github.com/...
```

### "error: failed to push some refs to 'origin'"
```bash
git pull origin main
# Merge conflict'ları çöz
git push
```

### Token ile ilgili sorun
```bash
git config --global credential.helper store
# Bir kez git push yaparak token'ı kaydet
# Sonrasında otomatik kullanılacak
```

---

## 📊 Commit Message Formatı (Opsiyonel ama İyi Pratik)

```
Emoji Type: Short description (50 chars or less)

Detailed explanation if needed.
- Change 1
- Change 2

Closes #123 (GitHub issue numarası)
```

**Emoji'ler:**
- 🚀 Feature/new functionality
- 🐛 Bug fix
- 📝 Documentation
- ⚡ Performance improvement
- 🔧 Configuration/setup
- 🎨 Code formatting/refactor
- ❌ Removed/deprecated
- 🔐 Security fix
- 📊 Data/benchmark
- 🚨 Breaking change

Örnek:
```
🚀 Add missile engagement system

Implemented rear-guard task assignment
and enemy tracking for UAV6

- Added _assign_rear_guard_tasks() method
- Implemented enemy position tracking
- Added engagement coordinate calculation

Closes #15
```

---

**İhtiyacın olursa sorular sor!** 🎯
