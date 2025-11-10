#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test du parseur V7 avec les PDFs de tableaux d'amortissement
"""

import os
import sys
from pathlib import Path

# Configuration
PDF_TEST = "TABLEAUD'AMORTISSEMENTPRETIMMOBILIER_20230417.pdf"  # Prêt A

def test_parseur_v7():
    """Test du parseur V7"""

    print("=" * 80)
    print("TEST PARSEUR V7 - APPROCHE SIMPLIFIÉE")
    print("=" * 80)
    print()

    # Vérifier que le PDF existe
    if not Path(PDF_TEST).exists():
        print(f"❌ ERREUR : PDF {PDF_TEST} introuvable")
        return False

    print(f"📄 PDF : {PDF_TEST}")
    print()

    # Vérifier la clé API
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ERREUR : ANTHROPIC_API_KEY non définie")
        return False

    print("✅ API Key : OK")
    print()

    # Import du parseur
    try:
        from parseur_pret_v7 import ParseurTableauPretV7
        print("✅ Import parseur_pret_v7 : OK")
    except ImportError as e:
        print(f"❌ ERREUR Import : {e}")
        return False

    print()
    print("-" * 80)
    print("PARSING EN COURS...")
    print("-" * 80)
    print()

    # Initialisation parseur
    parseur = ParseurTableauPretV7(api_key=api_key)

    # Parsing (sans insertion BD pour ce test)
    result = parseur.parse_from_pdf(PDF_TEST, auto_insert_bd=False)

    print()
    print("=" * 80)
    print("RÉSULTATS")
    print("=" * 80)
    print()

    if not result.get('success'):
        print(f"❌ ÉCHEC : {result.get('message')}")
        if 'errors' in result:
            print("\nErreurs détectées :")
            for err in result['errors']:
                print(f"  - {err}")
        return False

    # Afficher les résultats
    pret = result.get('pret', {})
    print("📊 MÉTADONNÉES DU PRÊT")
    print("-" * 80)
    print(f"  Numéro       : {pret.get('numero_pret')}")
    print(f"  Intitulé     : {pret.get('intitule')}")
    print(f"  Banque       : {pret.get('banque')}")
    print(f"  Montant      : {pret.get('montant_initial'):,.2f} EUR")
    print(f"  Taux         : {pret.get('taux_annuel')}%")
    print(f"  Durée        : {pret.get('duree_mois')} mois")
    print(f"  Date début   : {pret.get('date_debut')}")
    print(f"  Type         : {pret.get('type_pret')}")
    print()

    echeances = result.get('echeances', [])
    print("📋 ÉCHÉANCES")
    print("-" * 80)
    print(f"  Total        : {len(echeances)} échéances")
    print()

    # Afficher les 3 premières et 3 dernières échéances
    if echeances:
        print("  Premières échéances :")
        for i, ech in enumerate(echeances[:3]):
            print(f"    {i+1}. {ech['date_echeance']} | "
                  f"Total: {ech['montant_total']:>10.2f} | "
                  f"Capital: {ech['montant_capital']:>10.2f} | "
                  f"Intérêt: {ech['montant_interet']:>10.2f} | "
                  f"Restant: {ech['capital_restant_du']:>12.2f}")

        print()
        print("  Dernières échéances :")
        for i, ech in enumerate(echeances[-3:], len(echeances) - 2):
            print(f"    {i}. {ech['date_echeance']} | "
                  f"Total: {ech['montant_total']:>10.2f} | "
                  f"Capital: {ech['montant_capital']:>10.2f} | "
                  f"Intérêt: {ech['montant_interet']:>10.2f} | "
                  f"Restant: {ech['capital_restant_du']:>12.2f}")

    print()
    print("💾 FICHIER GÉNÉRÉ")
    print("-" * 80)
    print(f"  {result.get('filename')}")
    print()

    print("=" * 80)
    print("✅ TEST RÉUSSI")
    print("=" * 80)

    return True


if __name__ == "__main__":
    success = test_parseur_v7()
    sys.exit(0 if success else 1)
