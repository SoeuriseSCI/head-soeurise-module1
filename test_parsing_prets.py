#!/usr/bin/env python3
"""
Test du parsing des tableaux d'amortissement
Valide que les corrections (ignorer ECH/DBL, extraire lignes numérotées) fonctionnent
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from module2_workflow_v2 import ParseurTableauPret

# Vérifier disponibilité de l'API Claude
CLAUDE_API_KEY = os.getenv('ANTHROPIC_API_KEY')
if not CLAUDE_API_KEY:
    print("❌ ERREUR: Variable ANTHROPIC_API_KEY non définie")
    sys.exit(1)

# Fichiers PDFs à tester
PDF_FILES = [
    "TABLEAUD'AMORTISSEMENTPRETIMMOBILIER_20230417.pdf",
    "TABLEAUD'AMORTISSEMENTPRETIMMOBILIER_20230417-1.pdf"
]

print("=" * 80)
print("TEST PARSING TABLEAUX AMORTISSEMENT (Post-fix ECH/DBL)")
print("=" * 80)
print()

parseur = ParseurTableauPret(api_key=CLAUDE_API_KEY)

for pdf_file in PDF_FILES:
    if not os.path.exists(pdf_file):
        print(f"⚠️  Fichier non trouvé: {pdf_file}")
        continue

    print(f"📄 Parsing: {pdf_file}")
    print("-" * 80)

    try:
        # Parser le PDF (24 premières échéances)
        pret_data, echeances_data = parseur.parse_tableau_pret(pdf_file)

        # Vérifier structure pret_data
        print(f"✓ Prêt:")
        print(f"  - Numéro: {pret_data.get('numero_pret', 'N/A')}")
        print(f"  - Banque: {pret_data.get('banque', 'N/A')}")
        print(f"  - Montant: {pret_data.get('montant_initial', 0):,.0f} €")
        print(f"  - Taux: {pret_data.get('taux_annuel', 0):.3f}%")
        print(f"  - Durée: {pret_data.get('duree_mois', 0)} mois")
        print(f"  - Début: {pret_data.get('date_debut', 'N/A')}")
        print(f"  - Fin: {pret_data.get('date_fin', 'N/A')}")
        print()

        # Vérifier échéances
        print(f"✓ Échéances parsées: {len(echeances_data)}")

        if len(echeances_data) == 0:
            print("  ❌ AUCUNE échéance extraite !")
        else:
            # Vérifier doublons de dates
            dates = [ech.get('date_echeance') for ech in echeances_data]
            dates_uniques = set(dates)

            if len(dates) != len(dates_uniques):
                print(f"  ❌ DOUBLONS DÉTECTÉS ! {len(dates)} échéances, {len(dates_uniques)} dates uniques")
                # Afficher les doublons
                from collections import Counter
                compteur = Counter(dates)
                doublons = [date for date, count in compteur.items() if count > 1]
                print(f"     Dates en doublon: {doublons[:5]}")
            else:
                print(f"  ✓ Aucun doublon (toutes les dates sont uniques)")

            # Afficher les 5 premières échéances
            print(f"\n  Premières échéances:")
            for i, ech in enumerate(echeances_data[:5]):
                num = ech.get('numero_echeance', '?')
                date = ech.get('date_echeance', '?')
                capital = ech.get('montant_capital', 0)
                interet = ech.get('montant_interet', 0)
                total = ech.get('montant_total', 0)
                print(f"    {num:>3}. {date} - Total: {total:>8.2f}€ (Cap: {capital:>8.2f}€, Int: {interet:>8.2f}€)")

            if len(echeances_data) > 5:
                print(f"    ... ({len(echeances_data) - 5} échéances supplémentaires)")

        print()

    except Exception as e:
        print(f"❌ ERREUR lors du parsing: {e}")
        import traceback
        traceback.print_exc()
        print()

print("=" * 80)
print("FIN DU TEST")
print("=" * 80)
