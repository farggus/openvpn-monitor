# Git & GitHub Usage Guide

This guide explains how to work with the OpenVPN Monitor repository using Git, in two scenarios: local editing and GitHub web editing.

---

## 🏠 Scenario 1: Editing Locally (on your server)

This is the standard flow when you change code locally and want to sync it with GitHub.

```bash
# 1. Pull latest changes from GitHub
git pull origin main

# 2. Edit code locally

# 3. Check current changes
git status

# 4. Stage updated files
git add .

# 5. Commit the changes
git commit -m "Describe what was changed"

# 6. Push changes to GitHub
git push origin main
```

---

## ☁️ Scenario 2: Editing on GitHub (Web Interface)

When you make edits via GitHub (e.g., fix something online), you must pull those changes before continuing work locally.

```bash
# Pull remote changes before working locally
git pull origin main
```

---

## 💡 Tips

- Always run `git pull origin main` before starting local work.
- Avoid editing the same file in both places at the same time.
- Use `git status` often — it's your best friend.
- Use meaningful commit messages (e.g., `Fix uptime bug`, `Update README`).

---

## 🔐 SSH Setup (if needed)

```bash
# Check if an SSH key exists
ls ~/.ssh/id_rsa.pub

# If not, generate one:
ssh-keygen -t rsa -b 4096 -C "your.email@example.com"

# Copy key and add it at: https://github.com/settings/keys
cat ~/.ssh/id_rsa.pub

# Test connection
ssh -T git@github.com
```

---

## 🧰 Additional Resources

- [Markdown Syntax Guide](./markdown_guide.md)
- [GitHub Docs: Working with Git](https://docs.github.com/en/get-started)

---

Author: Farggus  
Project: OpenVPN Monitor  
