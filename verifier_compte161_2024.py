#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VÉRIFICATION COMPTE 161 vs 164
==============================
Vérifie qu'il n'y a plus de compte 164 et que tout est bien sur 161
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
print("🔍 VÉRIFICATION COMPTE 161 vs 164")
print("=" * 80)

# Récupérer exercice 2024
exercice_2024 = session.query(ExerciceComptable).filter_by(annee=2024).first()
if not exercice_2024:
    print("❌ Exercice 2024 non trouvé")
    exit(1)

print(f"\n📅 Exercice 2024 : ID={exercice_2024.id}")

# Chercher toutes les écritures avec compte 161 ou 164
ecritures_161 = session.query(EcritureComptable).filter(
    EcritureComptable.exercice_id == exercice_2024.id
).filter(
    (EcritureComptable.compte_debit == '161') | (EcritureComptable.compte_credit == '161')
).all()

ecritures_164 = session.query(EcritureComptable).filter(
    EcritureComptable.exercice_id == exercice_2024.id
).filter(
    (EcritureComptable.compte_debit == '164') | (EcritureComptable.compte_credit == '164')
).all()

print(f"\n📊 Écritures avec compte 161 : {len(ecritures_161)}")
print(f"📊 Écritures avec compte 164 : {len(ecritures_164)}")

# Analyser compte 161
if ecritures_161:
    print("\n" + "-" * 80)
    print("COMPTE 161 (Emprunts) ✅")
    print("-" * 80)

    total_debit_161 = Decimal('0')
    total_credit_161 = Decimal('0')

    for e in ecritures_161:
        if e.compte_debit == '161':
            total_debit_161 += e.montant
            print(f"  {e.date_ecriture} | Débit 161 : {e.montant:>12.2f}€ | {e.libelle_ecriture[:40]}")
        if e.compte_credit == '161':
            total_credit_161 += e.montant
            print(f"  {e.date_ecriture} | Crédit 161 : {e.montant:>11.2f}€ | {e.libelle_ecriture[:40]}")

    solde_161 = total_credit_161 - total_debit_161
    print(f"\n  Total Débit 161  : {total_debit_161:>12.2f}€")
    print(f"  Total Crédit 161 : {total_credit_161:>12.2f}€")
    print(f"  ────────────────────────────")
    print(f"  Solde 161 (créditeur) : {solde_161:>12.2f}€ (PASSIF)")

# Analyser compte 164
if ecritures_164:
    print("\n" + "-" * 80)
    print("COMPTE 164 (Emprunts établissements crédit) ❌")
    print("-" * 80)

    total_debit_164 = Decimal('0')
    total_credit_164 = Decimal('0')

    for e in ecritures_164:
        if e.compte_debit == '164':
            total_debit_164 += e.montant
            print(f"  {e.date_ecriture} | Débit 164 : {e.montant:>12.2f}€ | {e.libelle_ecriture[:40]}")
        if e.compte_credit == '164':
            total_credit_164 += e.montant
            print(f"  {e.date_ecriture} | Crédit 164 : {e.montant:>11.2f}€ | {e.libelle_ecriture[:40]}")

    solde_164 = total_credit_164 - total_debit_164
    print(f"\n  Total Débit 164  : {total_debit_164:>12.2f}€")
    print(f"  Total Crédit 164 : {total_credit_164:>12.2f}€")
    print(f"  ────────────────────────────")
    print(f"  Solde 164 : {solde_164:>12.2f}€")

    print(f"\n  ⚠️  LE COMPTE 164 NE DEVRAIT PAS EXISTER !")
    print(f"  ⚠️  Tous les remboursements doivent utiliser le compte 161")

# Résumé
print("\n" + "=" * 80)
print("📊 RÉSUMÉ")
print("=" * 80)

if not ecritures_164:
    print("\n✅ CORRECT : Aucune écriture sur compte 164")
    print("✅ Tous les remboursements utilisent le compte 161")
else:
    print(f"\n❌ PROBLÈME : {len(ecritures_164)} écritures utilisent le compte 164")
    print(f"❌ Ces écritures doivent être corrigées pour utiliser le compte 161")

session.close()

print("\n" + "=" * 80)
