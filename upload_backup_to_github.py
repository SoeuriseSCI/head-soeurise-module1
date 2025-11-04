#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UPLOAD BACKUP TO GITHUB
========================
Upload le fichier de sauvegarde vers GitHub via l'API
"""

import os
import sys
import json
import base64
import requests
from datetime import datetime

# Configuration
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')  # À définir dans Render
REPO_OWNER = "SoeuriseSCI"
REPO_NAME = "head-soeurise-module1"
BRANCH = "main"

# Fichier à uploader
BACKUP_FILE = "backups/soeurise_bd_20251104_160521.json"

if not GITHUB_TOKEN:
    print("❌ ERREUR : GITHUB_TOKEN non définie")
    print("💡 Définissez la variable d'environnement GITHUB_TOKEN sur Render")
    sys.exit(1)

print("=" * 80)
print("📤 UPLOAD BACKUP VERS GITHUB")
print("=" * 80)
print()

# Lire le fichier
print(f"📂 Lecture du fichier : {BACKUP_FILE}")
with open(BACKUP_FILE, 'r', encoding='utf-8') as f:
    content = f.read()

file_size = len(content.encode('utf-8'))
print(f"   Taille : {file_size:,} octets ({file_size/1024:.2f} KB)")

# Encoder en base64
content_encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')

# Chemin GitHub
github_path = f"backups/{os.path.basename(BACKUP_FILE)}"
print(f"📍 Chemin GitHub : {github_path}")
print()

# Vérifier si le fichier existe déjà
print("🔍 Vérification si le fichier existe déjà...")
url_check = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{github_path}"
headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

response = requests.get(url_check, headers=headers)
sha = None
if response.status_code == 200:
    sha = response.json().get('sha')
    print(f"   ✅ Fichier existe (SHA: {sha[:7]}...) - Mise à jour")
else:
    print(f"   ℹ️  Fichier n'existe pas - Création")

# Upload vers GitHub
print()
print("📤 Upload vers GitHub...")
commit_message = f"💾 Sauvegarde BD - {datetime.now().strftime('%d/%m/%Y %H:%M')}"

payload = {
    "message": commit_message,
    "content": content_encoded,
    "branch": BRANCH
}

if sha:
    payload["sha"] = sha

response = requests.put(url_check, headers=headers, json=payload)

if response.status_code in [200, 201]:
    result = response.json()
    print("   ✅ Upload réussi !")
    print()
    print("📊 Détails :")
    print(f"   Commit : {result['commit']['sha'][:7]}")
    print(f"   URL    : {result['content']['html_url']}")
    print()
    print("=" * 80)
    print("✅ SAUVEGARDE UPLOADÉE SUR GITHUB")
    print("=" * 80)
else:
    print(f"   ❌ Erreur : {response.status_code}")
    print(f"   {response.text}")
    sys.exit(1)
