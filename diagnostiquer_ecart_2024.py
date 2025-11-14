#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DIAGNOSTIC COMPLET ÉCART BILAN 2024
===================================
Identifie précisément la source de l'écart de 2,63€
"""

import os
from decimal import Decimal
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models_module2 import Base, EcritureComptable, ExerciceComptable

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
print("🔍 DIAGNOSTIC COMPLET ÉCART BILAN 2024")
print("=" * 80)

# Récupérer exercice 2024
exercice_2024 = session.query(ExerciceComptable).filter_by(annee=2024).first()
if not exercice_2024:
    print("❌ Exercice 2024 non trouvé")
    exit(1)

print(f"\n📅 Exercice 2024 : ID={exercice_2024.id}")

# Récupérer toutes les écritures
ecritures = session.query(EcritureComptable).filter_by(exercice_id=exercice_2024.id).all()

print(f"\n📊 Total écritures 2024 : {len(ecritures)}")

# 1. VÉRIFIER ÉCRITURES À 0€
print("\n" + "=" * 80)
print("1️⃣ ÉCRITURES À 0€")
print("=" * 80)

ecritures_zero = [e for e in ecritures if float(e.montant) == 0.0]

if ecritures_zero:
    print(f"\n⚠️  {len(ecritures_zero)} écritures à 0€ trouvées :")
    for e in ecritures_zero:
        print(f"\n  Écriture #{e.id} - {e.date_ecriture}")
        print(f"    Libellé : {e.libelle_ecriture}")
        print(f"    Débit {e.compte_debit} / Crédit {e.compte_credit} : {e.montant}€")
        print(f"    Type : {e.type_ecriture}")

    print(f"\n💡 Ces écritures ne devraient PAS exister (montant nul)")
else:
    print("\n✅ Aucune écriture à 0€")

# 2. CALCULER BALANCE COMPLÈTE
print("\n" + "=" * 80)
print("2️⃣ BALANCE COMPLÈTE")
print("=" * 80)

balances = {}

for e in ecritures:
    # Débit
    if e.compte_debit not in balances:
        balances[e.compte_debit] = {'debit': Decimal('0'), 'credit': Decimal('0')}
    balances[e.compte_debit]['debit'] += Decimal(str(e.montant))

    # Crédit
    if e.compte_credit not in balances:
        balances[e.compte_credit] = {'debit': Decimal('0'), 'credit': Decimal('0')}
    balances[e.compte_credit]['credit'] += Decimal(str(e.montant))

print("\nCompte | Total Débit    | Total Crédit   | Solde")
print("-" * 80)

total_debit_general = Decimal('0')
total_credit_general = Decimal('0')

for compte in sorted(balances.keys()):
    debit = balances[compte]['debit']
    credit = balances[compte]['credit']
    solde = debit - credit

    total_debit_general += debit
    total_credit_general += credit

    print(f"{compte:6} | {debit:>14.2f}€ | {credit:>14.2f}€ | {solde:>14.2f}€")

print("-" * 80)
print(f"TOTAL  | {total_debit_general:>14.2f}€ | {total_credit_general:>14.2f}€")

ecart_balance = total_debit_general - total_credit_general

print(f"\n🔍 Écart balance (débit - crédit) : {ecart_balance:.2f}€")

if abs(ecart_balance) < 0.01:
    print("✅ Balance équilibrée (écart négligeable)")
else:
    print(f"❌ Balance NON équilibrée (écart : {ecart_balance:.2f}€)")

# 3. VÉRIFIER PARTIE DOUBLE
print("\n" + "=" * 80)
print("3️⃣ VÉRIFICATION PARTIE DOUBLE")
print("=" * 80)

ecritures_non_equilibrees = []

for e in ecritures:
    # Chaque écriture doit avoir débit = crédit = montant
    # Si montant > 0, c'est OK
    # Si montant = 0, c'est suspect mais équilibré
    if float(e.montant) == 0.0:
        ecritures_non_equilibrees.append((e, "Montant = 0€"))

if ecritures_non_equilibrees:
    print(f"\n⚠️  {len(ecritures_non_equilibrees)} écritures suspectes :")
    for e, raison in ecritures_non_equilibrees:
        print(f"  Écriture #{e.id} : {raison}")
else:
    print("\n✅ Toutes les écritures respectent la partie double")

# 4. CALCULER SOLDES PAR CLASSE
print("\n" + "=" * 80)
print("4️⃣ SOLDES PAR CLASSE (BILAN)")
print("=" * 80)

classes = {
    '1': {'nom': 'Capitaux', 'solde': Decimal('0')},
    '2': {'nom': 'Immobilisations', 'solde': Decimal('0')},
    '3': {'nom': 'Stocks', 'solde': Decimal('0')},
    '4': {'nom': 'Tiers', 'solde': Decimal('0')},
    '5': {'nom': 'Financiers', 'solde': Decimal('0')},
    '6': {'nom': 'Charges', 'solde': Decimal('0')},
    '7': {'nom': 'Produits', 'solde': Decimal('0')},
    '8': {'nom': 'Spéciaux', 'solde': Decimal('0')},
}

for compte, data in balances.items():
    classe = compte[0] if compte else '?'
    solde = data['debit'] - data['credit']

    if classe in classes:
        classes[classe]['solde'] += solde

print("\nClasse | Nom                | Solde")
print("-" * 80)

for classe in sorted(classes.keys()):
    nom = classes[classe]['nom']
    solde = classes[classe]['solde']
    print(f"{classe}      | {nom:18} | {solde:>14.2f}€")

# 5. CALCULER ACTIF / PASSIF
print("\n" + "=" * 80)
print("5️⃣ ACTIF / PASSIF")
print("=" * 80)

# ACTIF = Classe 2 (débiteur) + Classe 5 (débiteur si > 0)
# PASSIF = Classe 1 (créditeur) + Classe 4 (créditeur si < 0) + Classe 5 (créditeur si < 0)
# Résultat = Classe 7 - Classe 6

resultat = classes['7']['solde'] - classes['6']['solde']
print(f"\n📊 Résultat (Classe 7 - Classe 6) : {resultat:.2f}€")

actif_brut = Decimal('0')
passif_brut = Decimal('0')

for compte, data in balances.items():
    classe = compte[0] if compte else '?'
    solde = data['debit'] - data['credit']

    # Classes 1-5 pour bilan
    if classe in ['1', '2', '3', '4', '5']:
        if solde > 0:  # Débiteur → ACTIF
            actif_brut += solde
        elif solde < 0:  # Créditeur → PASSIF
            passif_brut += abs(solde)

# Ajouter le résultat au passif
passif_avec_resultat = passif_brut + resultat

print(f"\nACTIF  : {actif_brut:>14.2f}€")
print(f"PASSIF : {passif_brut:>14.2f}€")
print(f"Résultat : {resultat:>14.2f}€")
print("-" * 80)
print(f"ACTIF  : {actif_brut:>14.2f}€")
print(f"PASSIF + Résultat : {passif_avec_resultat:>14.2f}€")
print("-" * 80)

ecart_bilan = actif_brut - passif_avec_resultat
print(f"Écart bilan : {ecart_bilan:.2f}€")

if abs(ecart_bilan) < 0.01:
    print("✅ Bilan équilibré")
elif abs(ecart_bilan - Decimal('2.63')) < 0.01:
    print(f"⚠️  Écart de {ecart_bilan:.2f}€ (correspond à l'écart observé)")
else:
    print(f"❌ Écart inattendu : {ecart_bilan:.2f}€")

# 6. DIAGNOSTIC FINAL
print("\n" + "=" * 80)
print("6️⃣ DIAGNOSTIC FINAL")
print("=" * 80)

if len(ecritures_zero) > 0:
    print(f"\n💡 HYPOTHÈSE #1 : Écritures à 0€")
    print(f"   {len(ecritures_zero)} écritures à 0€ trouvées")
    print(f"   Ces écritures ne devraient pas exister")
    print(f"   → Supprimer ces écritures et vérifier l'équilibre")

if abs(ecart_balance) > 0.01:
    print(f"\n💡 HYPOTHÈSE #2 : Balance non équilibrée")
    print(f"   Écart balance : {ecart_balance:.2f}€")
    print(f"   → Vérifier les écritures pour trouver l'erreur")

if abs(ecart_bilan - Decimal('2.63')) < 0.01:
    print(f"\n🎯 CONFIRMATION : L'écart de {ecart_bilan:.2f}€ est confirmé")
    print(f"   Source probable : Écritures à 0€ ou erreur de saisie")

session.close()

print("\n" + "=" * 80)
