#!/usr/bin/env python3
"""
Script de test pour valider les corrections de l'initialisation du bilan 2023
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from module2_workflow_v2 import GenerateurPropositions

# Données du bilan 2023 fournies par l'utilisateur
comptes_bilan_2023 = [
    # ACTIF (DEBIT)
    {"compte": "280", "libelle": "SCPI Epargne Pierre", "solde": 500032, "type_bilan": "ACTIF"},
    {"compte": "412", "libelle": "Créances diverses", "solde": 7356, "type_bilan": "ACTIF"},
    {"compte": "502", "libelle": "Actions", "solde": 4140, "type_bilan": "ACTIF"},
    {"compte": "512", "libelle": "Banque", "solde": 2093, "type_bilan": "ACTIF"},
    {"compte": "120", "libelle": "Report à nouveau (négatif)", "solde": 57992, "type_bilan": "ACTIF"},

    # PASSIF (CREDIT)
    {"compte": "290", "libelle": "Provision dépréciation SCPI", "solde": 50003, "type_bilan": "PASSIF"},
    {"compte": "101", "libelle": "Capital social", "solde": 1000, "type_bilan": "PASSIF"},
    {"compte": "130", "libelle": "Résultat 2023", "solde": 21844, "type_bilan": "PASSIF"},
    {"compte": "161", "libelle": "Emprunts", "solde": 497993, "type_bilan": "PASSIF"},
    {"compte": "444", "libelle": "Compte courant associés", "solde": 120, "type_bilan": "PASSIF"},
    {"compte": "401", "libelle": "Dettes fournisseurs", "solde": 653, "type_bilan": "PASSIF"},
]

print("=" * 80)
print("TEST INITIALISATION BILAN 2023")
print("=" * 80)
print()

# Test 1: Vérifier la classification de chaque compte
print("1. CLASSIFICATION DES COMPTES")
print("-" * 80)

comptes_actif = []
comptes_passif = []

for compte in comptes_bilan_2023:
    num = compte["compte"]
    sens = GenerateurPropositions._determiner_sens_compte(num, compte.get("type_bilan", ""))

    if sens == "DEBIT":
        comptes_actif.append(compte)
        print(f"✓ {num} ({compte['libelle'][:40]:40}) → DEBIT (ACTIF)")
    else:
        comptes_passif.append(compte)
        print(f"✓ {num} ({compte['libelle'][:40]:40}) → CREDIT (PASSIF)")

print()
print(f"Total ACTIF: {len(comptes_actif)} comptes")
print(f"Total PASSIF: {len(comptes_passif)} comptes")
print()

# Test 2: Générer les propositions
print("2. GÉNÉRATION DES PROPOSITIONS")
print("-" * 80)

markdown, data, token = GenerateurPropositions.generer_propositions_init_bilan_2023(comptes_bilan_2023)
propositions = data["propositions"]

print(f"Nombre de propositions générées: {len(propositions)}")
print()

# Test 3: Vérifier l'équilibre
print("3. VÉRIFICATION DE L'ÉQUILIBRE")
print("-" * 80)

total_actif = sum(c["solde"] for c in comptes_actif)
total_passif = sum(c["solde"] for c in comptes_passif)

total_debit_89 = sum(p["montant"] for p in propositions if p["compte_debit"] == "89")
total_credit_89 = sum(p["montant"] for p in propositions if p["compte_credit"] == "89")

total_debit_comptes = sum(p["montant"] for p in propositions if p["compte_debit"] != "89")
total_credit_comptes = sum(p["montant"] for p in propositions if p["compte_credit"] != "89")

print(f"Total ACTIF (bilan):           {total_actif:>12,.2f} €")
print(f"Total PASSIF (bilan):          {total_passif:>12,.2f} €")
print(f"Équilibre bilan:               {'✓ OK' if abs(total_actif - total_passif) < 0.01 else '✗ ERREUR'}")
print()
print(f"Total débits (hors 89):        {total_debit_comptes:>12,.2f} €")
print(f"Total crédits (hors 89):       {total_credit_comptes:>12,.2f} €")
print()
print(f"Compte 89 - Débit:             {total_debit_89:>12,.2f} €")
print(f"Compte 89 - Crédit:            {total_credit_89:>12,.2f} €")
print(f"Solde compte 89:               {total_debit_89 - total_credit_89:>12,.2f} €")
print(f"Équilibre compte 89:           {'✓ OK' if abs(total_debit_89 - total_credit_89) < 0.01 else '✗ ERREUR'}")
print()

# Test 4: Vérifier que le compte 130 est bien présent
print("4. VÉRIFICATION COMPTE 130 (Résultat 2023)")
print("-" * 80)

compte_130_trouve = False
for prop in propositions:
    if prop["compte_debit"] == "130" or prop["compte_credit"] == "130":
        compte_130_trouve = True
        print(f"✓ Compte 130 trouvé:")
        print(f"  Débit: {prop['compte_debit']}")
        print(f"  Crédit: {prop['compte_credit']}")
        print(f"  Montant: {prop['montant']} €")
        break

if not compte_130_trouve:
    print("✗ ERREUR: Compte 130 non trouvé !")
print()

# Test 5: Afficher le markdown généré (extrait)
print("5. APERÇU DU MARKDOWN GÉNÉRÉ")
print("-" * 80)

lines = markdown.split('\n')
for i, line in enumerate(lines[:30]):  # Première 30 lignes
    print(line)

if len(lines) > 30:
    print(f"\n... ({len(lines) - 30} lignes supplémentaires)")

print()
print("=" * 80)
print("FIN DU TEST")
print("=" * 80)
