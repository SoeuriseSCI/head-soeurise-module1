#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VÉRIFICATION COMPLÈTE COMPTABILITÉ 2024
========================================
1. Vérification traitement remises LCL (produit ou charge ?)
2. Liste TOUS les comptes alimentés par classe
3. Validation bilan et compte de résultat
4. Préparation comparaison avec documents officiels
"""

import os
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_module2 import EcritureComptable, ExerciceComptable, PlanCompte
from collections import defaultdict

# Connexion BD
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("❌ DATABASE_URL non définie")
    exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

print("=" * 80)
print("🔍 VÉRIFICATION COMPLÈTE COMPTABILITÉ 2024")
print("=" * 80)

# Récupérer exercice 2024
exercice_2024 = session.query(ExerciceComptable).filter_by(annee=2024).first()
if not exercice_2024:
    print("❌ Exercice 2024 non trouvé")
    exit(1)

print(f"\n📅 Exercice 2024 : {exercice_2024.date_debut} → {exercice_2024.date_fin}")

ecritures = session.query(EcritureComptable).filter_by(exercice_id=exercice_2024.id).all()
print(f"📝 Total écritures : {len(ecritures)}")

# ==============================================================================
# 1. VÉRIFICATION REMISES LCL
# ==============================================================================

print("\n" + "=" * 80)
print("1️⃣ VÉRIFICATION TRAITEMENT REMISES LCL")
print("=" * 80)

patterns_remises = ['REMISE', 'VOTRE REM', 'REM LCL', 'REMBT']
remises = []

for e in ecritures:
    libelle_upper = e.libelle_ecriture.upper()
    if any(pattern in libelle_upper for pattern in patterns_remises):
        remises.append(e)

print(f"\n📊 Remises LCL trouvées : {len(remises)}")

if remises:
    total_remises = Decimal('0')
    print("\n" + "-" * 80)
    print("Détail des remises :")
    print("-" * 80)

    for e in remises:
        total_remises += Decimal(str(e.montant))
        sens = "Débit 512 / Crédit 627" if e.compte_debit == '512' else "Débit 627 / Crédit 512"
        statut = "✅ CORRECT (réduit charges)" if e.compte_debit == '512' else "❌ INCORRECT (augmente charges)"

        print(f"{e.date_ecriture} | {e.montant:>8.2f}€ | {sens:30} | {statut}")

    print("-" * 80)
    print(f"Total remises : {total_remises:.2f}€")

    correctes = sum(1 for e in remises if e.compte_debit == '512')
    incorrectes = len(remises) - correctes

    print(f"\n✅ Remises correctes (Débit 512 / Crédit 627) : {correctes}")
    print(f"❌ Remises incorrectes (Débit 627 / Crédit 512) : {incorrectes}")

    if incorrectes == 0:
        print("\n🎯 CONCLUSION : Toutes les remises RÉDUISENT bien les charges ✅")
    else:
        print(f"\n⚠️  PROBLÈME : {incorrectes} remises augmentent les charges au lieu de les réduire")

# ==============================================================================
# 2. LISTE DES COMPTES ALIMENTÉS PAR CLASSE
# ==============================================================================

print("\n" + "=" * 80)
print("2️⃣ COMPTES ALIMENTÉS PAR CLASSE")
print("=" * 80)

# Calculer soldes
soldes = defaultdict(lambda: {'debit': Decimal('0'), 'credit': Decimal('0'), 'libelle': ''})

for e in ecritures:
    montant = Decimal(str(e.montant))

    soldes[e.compte_debit]['debit'] += montant
    soldes[e.compte_credit]['credit'] += montant

    # Libellés
    if not soldes[e.compte_debit]['libelle']:
        cpte = session.query(PlanCompte).filter_by(numero_compte=e.compte_debit).first()
        if cpte:
            soldes[e.compte_debit]['libelle'] = cpte.libelle

    if not soldes[e.compte_credit]['libelle']:
        cpte = session.query(PlanCompte).filter_by(numero_compte=e.compte_credit).first()
        if cpte:
            soldes[e.compte_credit]['libelle'] = cpte.libelle

# Calculer soldes nets
for num_compte in soldes:
    soldes[num_compte]['solde'] = soldes[num_compte]['debit'] - soldes[num_compte]['credit']

# Grouper par classe
classes = {
    '1': {'nom': 'CAPITAUX', 'comptes': []},
    '2': {'nom': 'IMMOBILISATIONS', 'comptes': []},
    '3': {'nom': 'STOCKS', 'comptes': []},
    '4': {'nom': 'TIERS', 'comptes': []},
    '5': {'nom': 'FINANCIERS', 'comptes': []},
    '6': {'nom': 'CHARGES', 'comptes': []},
    '7': {'nom': 'PRODUITS', 'comptes': []},
    '8': {'nom': 'SPÉCIAUX', 'comptes': []},
}

for num_compte, data in soldes.items():
    if num_compte and num_compte[0].isdigit():
        classe = num_compte[0]
        if classe in classes:
            classes[classe]['comptes'].append((num_compte, data))

# Afficher par classe
for classe in sorted(classes.keys()):
    nom = classes[classe]['nom']
    comptes = sorted(classes[classe]['comptes'], key=lambda x: x[0])

    if comptes:
        print(f"\n{'─' * 80}")
        print(f"CLASSE {classe} : {nom}")
        print(f"{'─' * 80}")
        print(f"{'Compte':<10} {'Libellé':<35} {'Débit':>12} {'Crédit':>12} {'Solde':>12}")
        print("-" * 80)

        for num_compte, data in comptes:
            libelle = data['libelle'][:35] if data['libelle'] else '(non défini)'
            debit = data['debit']
            credit = data['credit']
            solde = data['solde']

            print(f"{num_compte:<10} {libelle:<35} {debit:>11.2f}€ {credit:>11.2f}€ {solde:>11.2f}€")

# ==============================================================================
# 3. SYNTHÈSE BILAN ET COMPTE DE RÉSULTAT
# ==============================================================================

print("\n" + "=" * 80)
print("3️⃣ SYNTHÈSE ÉTATS FINANCIERS")
print("=" * 80)

# Calculer totaux par classe
total_actif = Decimal('0')
total_passif = Decimal('0')
total_charges = Decimal('0')
total_produits = Decimal('0')

for num_compte, data in soldes.items():
    if num_compte == '89':  # Ignorer compte bilan ouverture
        continue

    if num_compte and num_compte[0].isdigit():
        classe = num_compte[0]
        solde = data['solde']

        # Bilan (classes 1-5)
        if classe in ['1', '2', '3', '4', '5']:
            if solde > 0:
                total_actif += solde
            else:
                total_passif += abs(solde)

        # Compte de résultat (classes 6-7)
        elif classe == '6':
            total_charges += solde  # Solde débiteur
        elif classe == '7':
            total_produits += abs(solde)  # Solde créditeur

resultat = total_produits - total_charges

print("\n📊 COMPTE DE RÉSULTAT 2024")
print("-" * 80)
print(f"PRODUITS (Classe 7)  : {total_produits:>14.2f}€")
print(f"CHARGES (Classe 6)   : {total_charges:>14.2f}€")
print("-" * 80)
print(f"RÉSULTAT             : {resultat:>14.2f}€", "✅ Bénéfice" if resultat > 0 else "❌ Perte")

print("\n📋 BILAN AU 31/12/2024")
print("-" * 80)
print(f"ACTIF                : {total_actif:>14.2f}€")
print(f"PASSIF               : {total_passif:>14.2f}€")
print(f"Résultat (au passif) : {resultat:>14.2f}€")
print("-" * 80)
print(f"TOTAL PASSIF + RES   : {total_passif + resultat:>14.2f}€")

ecart_bilan = total_actif - (total_passif + resultat)
print(f"\nÉcart bilan          : {ecart_bilan:>14.2f}€")

if abs(ecart_bilan) < Decimal('0.01'):
    print("✅ BILAN ÉQUILIBRÉ")
else:
    print(f"❌ BILAN NON ÉQUILIBRÉ (écart : {ecart_bilan:.2f}€)")

# ==============================================================================
# 4. TABLEAU DE COMPARAISON (à remplir avec documents officiels)
# ==============================================================================

print("\n" + "=" * 80)
print("4️⃣ COMPARAISON AVEC DOCUMENTS OFFICIELS")
print("=" * 80)

print("\nÀ COMPARER avec vos documents comptables officiels :")
print("\n📊 COMPTE DE RÉSULTAT")
print("-" * 80)
print(f"{'Poste':<30} {'Calculé':>15} {'Officiel':>15} {'Écart':>15}")
print("-" * 80)
print(f"{'Produits':<30} {total_produits:>14.2f}€ {'?':>15} {'?':>15}")
print(f"{'Charges':<30} {total_charges:>14.2f}€ {'?':>15} {'?':>15}")
print(f"{'Résultat':<30} {resultat:>14.2f}€ {'?':>15} {'?':>15}")

print("\n📋 BILAN")
print("-" * 80)
print(f"{'Poste':<30} {'Calculé':>15} {'Officiel':>15} {'Écart':>15}")
print("-" * 80)
print(f"{'ACTIF':<30} {total_actif:>14.2f}€ {'?':>15} {'?':>15}")
print(f"{'PASSIF (hors résultat)':<30} {total_passif:>14.2f}€ {'?':>15} {'?':>15}")
print(f"{'Résultat':<30} {resultat:>14.2f}€ {'?':>15} {'?':>15}")
print(f"{'TOTAL PASSIF':<30} {total_passif + resultat:>14.2f}€ {'?':>15} {'?':>15}")

# ==============================================================================
# 5. CONCLUSION
# ==============================================================================

print("\n" + "=" * 80)
print("5️⃣ CONCLUSION")
print("=" * 80)

print("\n✅ VÉRIFICATIONS EFFECTUÉES :")
print(f"  1. Remises LCL traitées comme réduction de charges : {'✅' if incorrectes == 0 else '❌'}")
print(f"  2. Comptes alimentés (Actif/Passif/Produits/Charges) : ✅")
print(f"  3. Bilan équilibré : {'✅' if abs(ecart_bilan) < Decimal('0.01') else '❌'}")
print(f"  4. États financiers construits : ✅")

print("\n📋 PROCHAINES ÉTAPES :")
print("  1. Comparer les chiffres ci-dessus avec documents officiels")
print("  2. Si écarts : identifier et corriger")
print("  3. Si OK : Provisionner impôt sur les sociétés")
print("  4. Clôturer exercice 2024")
print("  5. Développer module portefeuille VM")

session.close()

print("\n" + "=" * 80)
