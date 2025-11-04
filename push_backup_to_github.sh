#!/bin/bash
#
# PUSH BACKUP TO GITHUB
# =====================
# Pousse le fichier de sauvegarde directement vers GitHub (branche main)
#
# Usage: bash push_backup_to_github.sh
#

set -e

echo "================================================================================";
echo "📤 PUSH BACKUP VERS GITHUB";
echo "================================================================================";
echo "";

# Vérifier que le fichier existe
BACKUP_FILE="backups/soeurise_bd_20251104_160521.json"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ ERREUR : Fichier $BACKUP_FILE introuvable";
    echo "💡 Liste des backups disponibles :";
    ls -lh backups/*.json 2>/dev/null || echo "   Aucun backup trouvé";
    exit 1;
fi

FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "📂 Fichier : $BACKUP_FILE";
echo "📊 Taille  : $FILE_SIZE";
echo "";

# Configuration Git (si pas déjà configuré)
git config --global user.email "head.soeurise@sci-soeurise.com" 2>/dev/null || true
git config --global user.name "_Head.Soeurise" 2>/dev/null || true

# Initialiser le repo si nécessaire
if [ ! -d ".git" ]; then
    echo "🔧 Initialisation du repo Git...";
    git init
    git remote add origin https://github.com/SoeuriseSCI/head-soeurise-module1.git
    git fetch origin
    git checkout main
fi

# Vérifier qu'on est sur main
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "⚠️  Branche actuelle : $CURRENT_BRANCH";
    echo "🔄 Passage sur branche main...";
    git checkout main 2>/dev/null || git checkout -b main origin/main
fi

echo "📋 Statut Git actuel :";
git status --short
echo "";

# Ajouter le fichier
echo "➕ Ajout du fichier de sauvegarde...";
git add "$BACKUP_FILE"

# Vérifier si le fichier est bien ajouté
if git diff --cached --quiet; then
    echo "ℹ️  Aucun changement à commiter (fichier déjà présent?)";
    echo "";
    echo "✅ Le fichier est déjà sur GitHub !";
    exit 0;
fi

# Commiter
TIMESTAMP=$(date +"%d/%m/%Y %H:%M")
echo "💾 Création du commit...";
git commit -m "💾 Sauvegarde BD - $TIMESTAMP

- Fichier: $(basename $BACKUP_FILE)
- Taille: $FILE_SIZE
- 2 exercices, 12 comptes, 11 écritures, 2 prêts, 467 échéances
- Total: 494 enregistrements"

# Pousser vers GitHub
echo "";
echo "🚀 Push vers GitHub (main)...";

# Note: Si erreur d'authentification, il faudra définir un token
# export GH_TOKEN="votre_token_github"
# git remote set-url origin https://$GH_TOKEN@github.com/SoeuriseSCI/head-soeurise-module1.git

git push origin main

echo "";
echo "================================================================================";
echo "✅ BACKUP POUSSÉ SUR GITHUB";
echo "================================================================================";
echo "";
echo "📍 URL : https://github.com/SoeuriseSCI/head-soeurise-module1/blob/main/$BACKUP_FILE";
echo "";
