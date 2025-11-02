#!/usr/bin/env python3
"""
Script de test pour ParseurBilan2023V6

Test avec le PDF réel: Comptes annuels 2023 SCI SOEURISE-Signé.pdf
"""

import os
import sys
import json
from pathlib import Path

# Ajouter le répertoire courant au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from parseur_bilan_v6 import parse_bilan_v6


def test_parseur_bilan_v6():
    """
    Test du parseur V6 avec le PDF réel
    """
    print("="*80)
    print("TEST PARSEUR BILAN V6")
    print("="*80)

    # 1. Vérifier que le PDF existe
    pdf_path = "Comptes annuels 2023 SCI SOEURISE-Signé.pdf"
    if not os.path.exists(pdf_path):
        print(f"\n❌ ERREUR: PDF non trouvé: {pdf_path}")
        print("   Merci de copier le PDF dans le répertoire courant")
        return False

    print(f"\n✓ PDF trouvé: {pdf_path}")
    file_size = os.path.getsize(pdf_path) / 1024
    print(f"  Taille: {file_size:.1f} KB")

    # 2. Vérifier la clé API
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("\n❌ ERREUR: ANTHROPIC_API_KEY non définie")
        print("   export ANTHROPIC_API_KEY=sk-...")
        return False

    print(f"\n✓ API Key définie: {api_key[:15]}...{api_key[-4:]}")

    # 3. Lancer le parsing
    print("\n" + "="*80)
    print("LANCEMENT DU PARSING V6...")
    print("="*80)
    print("\nCeci peut prendre 30-60 secondes (extraction de 15 pages PDF)...")
    print()

    try:
        result = parse_bilan_v6(
            filepath=pdf_path,
            api_key=api_key,
            exercice="2023"
        )

        print("\n" + "="*80)
        print("RÉSULTAT DU PARSING")
        print("="*80)

        if result.get('success'):
            print("\n✅ SUCCÈS!")
            print(f"\nExercice: {result.get('exercice')}")
            print(f"Date bilan: {result.get('date_bilan')}")
            print(f"Nombre de comptes: {result.get('nb_comptes')}")
            print(f"Total ACTIF: {result.get('total_actif', 0):,.2f} €")
            print(f"Total PASSIF: {result.get('total_passif', 0):,.2f} €")
            print(f"Équilibre: {'✓ OK' if result.get('equilibre') else '✗ ERREUR'}")

            # Afficher les comptes ACTIF
            print("\n" + "-"*80)
            print("COMPTES ACTIF (débit au bilan)")
            print("-"*80)
            for compte in result.get('comptes_actif', []):
                print(f"  {compte['numero_compte']:>3} - {compte['libelle']:50} {compte['montant']:>12,.2f} €")

            # Afficher les comptes PASSIF
            print("\n" + "-"*80)
            print("COMPTES PASSIF (crédit au bilan)")
            print("-"*80)
            for compte in result.get('comptes_passif', []):
                print(f"  {compte['numero_compte']:>3} - {compte['libelle']:50} {compte['montant']:>12,.2f} €")

            # Vérifier vs résultat attendu
            print("\n" + "="*80)
            print("VÉRIFICATION VS RÉSULTAT ATTENDU")
            print("="*80)

            expected = {
                "nb_comptes": 10,
                "total_actif": 463618.00,
                "total_passif": 463618.00,
                "equilibre": True
            }

            checks = {
                "Nombre de comptes": (result.get('nb_comptes'), expected['nb_comptes']),
                "Total ACTIF": (result.get('total_actif'), expected['total_actif']),
                "Total PASSIF": (result.get('total_passif'), expected['total_passif']),
                "Équilibre": (result.get('equilibre'), expected['equilibre'])
            }

            all_ok = True
            for check_name, (actual, expected_val) in checks.items():
                if isinstance(actual, float):
                    ok = abs(actual - expected_val) < 0.01
                else:
                    ok = actual == expected_val

                status = "✓" if ok else "✗"
                print(f"{status} {check_name:20}: {actual} {'==' if ok else '!='} {expected_val}")
                all_ok = all_ok and ok

            if all_ok:
                print("\n🎉 TOUS LES TESTS PASSENT!")
                print("\nLe parseur V6 a correctement extrait les 10 comptes du bilan.")
                return True
            else:
                print("\n⚠️ CERTAINS TESTS ÉCHOUENT")
                print("\nLe parseur V6 a extrait des données, mais elles ne correspondent pas exactement à l'attendu.")
                return False

        else:
            print("\n❌ ÉCHEC DU PARSING")
            print(f"\nMessage: {result.get('message', 'Erreur inconnue')}")
            print(f"Erreur: {result.get('error', 'N/A')}")
            return False

    except Exception as e:
        print(f"\n❌ EXCEPTION: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_parseur_bilan_v6()
    sys.exit(0 if success else 1)
