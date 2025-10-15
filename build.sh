#!/bin/bash
# Build script pour Render.com - V3.0
# Installation des dépendances système nécessaires pour OCR

echo "🔧 Installation des dépendances système..."

# Poppler-utils : requis pour pdf2image (conversion PDF → images)
apt-get update
apt-get install -y poppler-utils

echo "✅ Dépendances système installées"
echo "📦 Installation des dépendances Python..."

pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Build terminé - V3.0 OCR Intelligent prêt"
