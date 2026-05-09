#!/bin/bash

# 🚀 Bitirme Projesi - Git Quick Start Script
# GitHub push etmeden önce bu script'i çalıştır

echo "================================"
echo "📊 Git Status Check"
echo "================================"
git status

echo ""
echo "================================"
echo "📝 Staging Changes"
echo "================================"
git add -A
echo "✓ All changes added to staging"

echo ""
echo "================================"
echo "📋 Changes to be committed:"
echo "================================"
git diff --cached --stat

echo ""
echo "⚠️  Commit message gir (veya Ctrl+C ile iptal et):"
read -p "Enter commit message: " commit_msg

if [ -z "$commit_msg" ]; then
    echo "❌ Commit message boş! İptal ediliyor."
    git reset
    exit 1
fi

git commit -m "$commit_msg"

echo ""
echo "================================"
echo "🚀 Pushing to GitHub..."
echo "================================"
git push

echo ""
echo "✅ Push tamamlandı!"
echo "GitHub repo'nuz güncellendi: https://github.com/YourUsername/Bitirme-Projesi"

