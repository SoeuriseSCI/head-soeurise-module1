#!/usr/bin/env python3
"""
TEST PARSEUR V6 - EXTRACTION COMPLÈTE AVEC FUNCTION CALLING
===========================================================

Test du nouveau parseur avec les PDFs de référence (Prêt A et B)
"""

import os
import sys
from pathlib import Path

# Récupérer la clé API
CLAUDE_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
if not CLAUDE_API_KEY:
    print("ERROR: ANTHROPIC_API_KEY non définie")
    sys.exit(1)

from parseur_pret_v6 import ParseurTableauPretV6


def test_pret_a():
    """Test extraction Prêt A (INVESTIMUR - 216 échéances)"""
    print("\n" + "="*70)
    print("TEST PRÊT A - INVESTIMUR (216 échéances)")
    print("="*70 + "\n")

    # Chemin du PDF
    pdf_path = "TABLEAUD'AMORTISSEMENTPRETIMMOBILIER_20230417.pdf"

    if not Path(pdf_path).exists():
        print(f"ERROR: PDF non trouvé: {pdf_path}")
        return False

    # Créer parseur
    parseur = ParseurTableauPretV6(api_key=CLAUDE_API_KEY)

    # Parser
    print(f"Parsing {pdf_path}...\n")
    result = parseur.parse_from_pdf(pdf_path, auto_insert_bd=True)

    # Afficher résultat
    print("\n" + "-"*70)
    print("RÉSULTAT:")
    print("-"*70)

    if result.get('success'):
        print(f"✅ SUCCESS")
        print(f"   Fichier créé : {result.get('filename')}")
        print(f"   Nb échéances : {result.get('nb_echeances')}")
        print(f"   Prêt ID      : {result.get('pret_id')}")

        # Vérifier avec fichier de référence
        expected = 216  # On s'attend à 216 échéances pour Prêt A
        actual = result.get('nb_echeances', 0)

        if actual == expected:
            print(f"\n✅ Nombre d'échéances CORRECT: {actual} == {expected}")
        else:
            print(f"\n❌ Nombre d'échéances INCORRECT: {actual} != {expected}")
            return False

        return True
    else:
        print(f"❌ ERREUR: {result.get('error')}")
        print(f"   Message: {result.get('message')}")
        return False


def test_pret_b():
    """Test extraction Prêt B (SOLUTION P IMMO - 252 échéances)"""
    print("\n" + "="*70)
    print("TEST PRÊT B - SOLUTION P IMMO (252 échéances)")
    print("="*70 + "\n")

    # Chemin du PDF
    pdf_path = "TABLEAUD'AMORTISSEMENTPRETIMMOBILIER_20230417-1.pdf"

    if not Path(pdf_path).exists():
        print(f"ERROR: PDF non trouvé: {pdf_path}")
        return False

    # Créer parseur
    parseur = ParseurTableauPretV6(api_key=CLAUDE_API_KEY)

    # Parser
    print(f"Parsing {pdf_path}...\n")
    result = parseur.parse_from_pdf(pdf_path, auto_insert_bd=True)

    # Afficher résultat
    print("\n" + "-"*70)
    print("RÉSULTAT:")
    print("-"*70)

    if result.get('success'):
        print(f"✅ SUCCESS")
        print(f"   Fichier créé : {result.get('filename')}")
        print(f"   Nb échéances : {result.get('nb_echeances')}")
        print(f"   Prêt ID      : {result.get('pret_id')}")

        # Vérifier avec fichier de référence
        expected = 252  # On s'attend à 252 échéances pour Prêt B
        actual = result.get('nb_echeances', 0)

        if actual == expected:
            print(f"\n✅ Nombre d'échéances CORRECT: {actual} == {expected}")
        else:
            print(f"\n❌ Nombre d'échéances INCORRECT: {actual} != {expected}")
            return False

        return True
    else:
        print(f"❌ ERREUR: {result.get('error')}")
        print(f"   Message: {result.get('message')}")
        return False


def comparer_avec_reference(filename: str, reference_file: str):
    """Compare le fichier généré avec le fichier de référence"""
    print(f"\nComparaison {filename} vs {reference_file}...")

    if not Path(filename).exists():
        print(f"❌ Fichier généré introuvable: {filename}")
        return False

    if not Path(reference_file).exists():
        print(f"❌ Fichier de référence introuvable: {reference_file}")
        return False

    # Lire les deux fichiers
    with open(filename, 'r') as f:
        generated_lines = [line.strip() for line in f if line.strip() and not line.startswith('#') and not line.startswith('**') and not line.startswith('---')]

    with open(reference_file, 'r') as f:
        reference_lines = [line.strip() for line in f if line.strip() and not line.startswith('#') and not line.startswith('**') and not line.startswith('---')]

    # Comparer le nombre de lignes
    if len(generated_lines) != len(reference_lines):
        print(f"❌ Nombre de lignes différent: {len(generated_lines)} vs {len(reference_lines)}")
        return False

    # Comparer ligne par ligne (échantillon)
    differences = 0
    for i in range(min(10, len(generated_lines))):
        if generated_lines[i] != reference_lines[i]:
            print(f"   Ligne {i+1} diff:")
            print(f"      Généré    : {generated_lines[i]}")
            print(f"      Référence : {reference_lines[i]}")
            differences += 1

    if differences == 0:
        print(f"✅ Les 10 premières lignes sont IDENTIQUES")
        return True
    else:
        print(f"⚠️  {differences} différences trouvées sur les 10 premières lignes")
        return False


if __name__ == "__main__":
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "TEST PARSEUR V6 - FUNCTION CALLING" + " "*19 + "║")
    print("╚" + "="*68 + "╝")

    # Test Prêt A
    success_a = test_pret_a()

    # Petit délai entre les tests
    import time
    time.sleep(2)

    # Test Prêt B
    success_b = test_pret_b()

    # Résumé final
    print("\n" + "="*70)
    print("RÉSUMÉ DES TESTS")
    print("="*70)
    print(f"Prêt A (INVESTIMUR)       : {'✅ PASS' if success_a else '❌ FAIL'}")
    print(f"Prêt B (SOLUTION P IMMO) : {'✅ PASS' if success_b else '❌ FAIL'}")
    print("="*70 + "\n")

    # Exit code
    sys.exit(0 if (success_a and success_b) else 1)
