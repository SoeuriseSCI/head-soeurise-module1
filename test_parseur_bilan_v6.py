"""
Test du ParseurBilan2023V6 avec le vrai PDF Comptes annuels 2023
"""

import os
import sys
from parseur_bilan_v6 import ParseurBilan2023V6

# Configuration
PDF_PATH = "Comptes annuels 2023 SCI SOEURISE-Signé.pdf"
API_KEY = os.environ.get('ANTHROPIC_API_KEY')

if not API_KEY:
    print("❌ ANTHROPIC_API_KEY non définie")
    print("   export ANTHROPIC_API_KEY='sk-ant-api03-...'")
    sys.exit(1)

print("=" * 80)
print("TEST PARSEUR BILAN V6 - Comptes Annuels 2023 SCI SOEURISE")
print("=" * 80)
print()

# Initialiser parseur
parseur = ParseurBilan2023V6(api_key=API_KEY)

print(f"📄 Fichier PDF : {PDF_PATH}")
print(f"📊 Pages à analyser : 3-6 (bilan ACTIF/PASSIF)")
print()

# Parser le PDF
print("🔄 Parsing en cours...")
print()

result = parseur.parse_from_pdf(PDF_PATH, start_page=3, max_pages=4)

print()
print("=" * 80)
print("RÉSULTATS")
print("=" * 80)
print()

if result.get('success'):
    print(f"✅ SUCCESS")
    print()
    print(f"📅 Exercice : {result.get('exercice')}")
    print(f"📆 Date bilan : {result.get('date_bilan')}")
    print(f"📊 Nombre de comptes : {result.get('nb_comptes')}")
    print()
    print(f"💰 Total ACTIF : {result.get('total_actif'):,.2f} €")
    print(f"💰 Total PASSIF : {result.get('total_passif'):,.2f} €")
    print(f"⚖️  Équilibre : {'✅ OK' if result.get('equilibre') else '❌ ERREUR'}")
    print()

    print("COMPTES ACTIF:")
    for compte in result.get('comptes', []):
        if compte['type_bilan'] == 'ACTIF':
            print(f"  {compte['numero']:>3} - {compte['libelle']:<40} {compte['solde']:>12,.2f} €")

    print()
    print("COMPTES PASSIF:")
    for compte in result.get('comptes', []):
        if compte['type_bilan'] == 'PASSIF':
            print(f"  {compte['numero']:>3} - {compte['libelle']:<40} {compte['solde']:>12,.2f} €")

    print()

    # Comparer avec résultats attendus
    print("=" * 80)
    print("VALIDATION vs RÉSULTATS ATTENDUS")
    print("=" * 80)
    print()

    expected_nb_comptes = 11  # 5 ACTIF + 6 PASSIF (ajout compte 130)
    expected_total = 463618.00

    checks = []
    checks.append(("Nombre de comptes", result.get('nb_comptes') == expected_nb_comptes,
                   f"{result.get('nb_comptes')} / {expected_nb_comptes}"))
    checks.append(("Total ACTIF", abs(result.get('total_actif', 0) - expected_total) < 1.0,
                   f"{result.get('total_actif'):,.2f} / {expected_total:,.2f}"))
    checks.append(("Total PASSIF", abs(result.get('total_passif', 0) - expected_total) < 1.0,
                   f"{result.get('total_passif'):,.2f} / {expected_total:,.2f}"))
    checks.append(("Équilibre", result.get('equilibre') == True,
                   "OK" if result.get('equilibre') else "ERREUR"))

    all_passed = True
    for label, passed, details in checks:
        status = "✅" if passed else "❌"
        print(f"{status} {label:<25} : {details}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("🎉 TOUS LES TESTS PASSENT !")
        print()
        print("Le parseur V6 fonctionne parfaitement.")
        print("Prêt à être intégré dans le workflow de production.")
    else:
        print("⚠️  CERTAINS TESTS ÉCHOUENT")
        print()
        print("Vérifier les détails ci-dessus.")

else:
    print(f"❌ ÉCHEC: {result.get('message')}")
    if result.get('error'):
        print(f"   Erreur: {result.get('error')}")

print()
print("=" * 80)
