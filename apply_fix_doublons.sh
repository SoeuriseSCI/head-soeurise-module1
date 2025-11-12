#!/bin/bash
# Script d'application du fix doublons SCPI/Apports
# À exécuter sur Render après déploiement si les commits ne sont pas poussés

set -e

echo "=========================================="
echo "Application du fix doublons SCPI/Apports"
echo "=========================================="
echo ""

# Vérifier que detection_doublons.py a la nouvelle méthode
if grep -q "calculer_fingerprint_simplifie" detection_doublons.py; then
    echo "✅ detection_doublons.py: Méthode calculer_fingerprint_simplifie présente"
else
    echo "❌ detection_doublons.py: Méthode calculer_fingerprint_simplifie MANQUANTE"
    echo "   Le fichier detection_doublons.py doit être mis à jour manuellement"
    exit 1
fi

# Vérifier que extracteur_pdf.py a la déduplication 2 passes
if grep -q "ÉTAPE 2: Grouper par fingerprint SIMPLIFIÉ" extracteur_pdf.py; then
    echo "✅ extracteur_pdf.py: Déduplication 2 passes présente"
else
    echo "⚠️  extracteur_pdf.py: Déduplication 2 passes MANQUANTE"
    echo "   Application du patch..."

    # Créer un backup
    cp extracteur_pdf.py extracteur_pdf.py.backup
    echo "   Backup créé: extracteur_pdf.py.backup"

    # Le patch doit être appliqué manuellement
    echo ""
    echo "❌ ERREUR: Le patch pour extracteur_pdf.py doit être appliqué manuellement"
    echo ""
    echo "Instructions:"
    echo "1. Ouvrir extracteur_pdf.py"
    echo "2. Remplacer la méthode _deduplicater_operations (lignes 81-153)"
    echo "3. Par la nouvelle version avec déduplication 2 passes"
    echo ""
    echo "Ou attendre que les commits soient poussés vers GitHub"
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ Tous les fichiers sont à jour"
echo "=========================================="
echo ""
echo "Pour tester:"
echo "  - Relancer le workflow via /admin/trigger-reveil"
echo "  - Vérifier les logs pour:"
echo "    • Doublons SCPI/Apports: 9"
echo "    • 108 événements créés (pas 117)"
echo ""
