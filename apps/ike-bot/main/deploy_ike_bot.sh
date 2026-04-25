#!/bin/bash

# TrustBot Auto Setup Script

echo "📁 Checking for main.py and requirements.txt..."
if [ ! -f "main.py" ]; then
  echo "❌ main.py not found. Please unzip IKE-BOT-TrustAgent.zip and run this inside the folder."
  exit 1
fi

echo "✅ Files detected. Initializing Git repository..."
git init
git remote add origin https://github.com/ihoward40/ike-bot.git
git branch -M main

echo "➕ Staging files..."
git add .
git commit -m "Initial TrustBot automation deployment"

echo "🚀 Pushing to GitHub..."
git push -u origin main

echo "✅ Done! Your IKE BOT files are now live in GitHub."
