#!/bin/bash

# 🚀 Git Aliases & Functions Setupi
# Bu dosyayı ~/.bashrc veya ~/.zshrc'ye ekle

# Git alias'ları ekle
cat >> ~/.bashrc << 'ALIASES'

# === GIT ALIASES ===
alias gs='git status'                                    # Status
alias ga='git add -A'                                    # Add all
alias gc='git commit -m'                                 # Commit
alias gp='git push'                                      # Push
alias gl='git log --oneline -n 10'                      # Log (10 lines)
alias gll='git log --graph --oneline --all'             # Log (graph)
alias gd='git diff'                                      # Diff
alias gdc='git diff --cached'                            # Diff staged
alias gb='git branch -a'                                 # Branches
alias gco='git checkout'                                 # Checkout
alias greset='git reset --hard HEAD'                    # Reset (DANGER!)
alias gundo='git reset --soft HEAD~1'                   # Undo last commit
alias gstash='git stash'                                # Stash
alias gpop='git stash pop'                              # Unstash

# === GIT FUNCTIONS ===

# Quick commit + push
gcp() {
    git add -A
    git commit -m "$1"
    git push
}

# Safe undo (doesn't delete files)
gundo() {
    git reset --soft HEAD~1
    echo "✓ Last commit undone (files preserved)"
}

# View specific commit
gshow() {
    git show "$1"
}

# Create new feature branch
gfeat() {
    git checkout -b "feature/$1"
    echo "✓ Created feature branch: feature/$1"
}

# Push new branch
gpush-new() {
    git push -u origin "$(git rev-parse --abbrev-ref HEAD)"
    echo "✓ Pushed new branch"
}

# Current branch info
ginfo() {
    echo "📊 Git Repository Info:"
    echo "Branch: $(git rev-parse --abbrev-ref HEAD)"
    echo "Remote: $(git config --get remote.origin.url)"
    echo "Commits: $(git rev-list --count HEAD)"
    echo "Last: $(git log -1 --pretty=format:'%s')"
}

# Cleanup
gclean() {
    git clean -fd
    echo "✓ Cleaned untracked files"
}

ALIASES

echo "✅ Git aliases added to ~/.bashrc"
echo ""
echo "Reload your shell:"
echo "  source ~/.bashrc"
echo ""
echo "Or logout and login again"
