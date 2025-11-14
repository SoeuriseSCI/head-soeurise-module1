#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VÉRIFICATION REMISES LCL 2024
=============================
Vérifie que toutes les remises LCL sont bien traitées en Débit 512 / Crédit 627
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
print("🔍 VÉRIFICATION REMISES LCL 2024")
print("=" * 80)

# Récupérer exercice 2024
exercice_2024 = session.query(ExerciceComptable).filter_by(annee=2024).first()
if not exercice_2024:
    print("❌ Exercice 2024 non trouvé")
    exit(1)

print(f"\n📅 Exercice 2024 : ID={exercice_2024.id}")

# Chercher toutes les écritures liées aux remises
patterns_remises = ['REMISE', 'VOTRE REM', 'REM LCL', 'REMBT']

ecritures_remises = []
for e in session.query(EcritureComptable).filter_by(exercice_id=exercice_2024.id).all():
    libelle_upper = e.libelle_ecriture.upper()
    if any(pattern in libelle_upper for pattern in patterns_remises):
        ecritures_remises.append(e)

print(f"\n📊 Écritures de remises trouvées : {len(ecritures_remises)}")

if not ecritures_remises:
    print("\n✅ Aucune remise trouvée (normal si retraitées ou absentes)")
    exit(0)

# Analyser chaque écriture
remises_correctes = []
remises_incorrectes = []

print("\n" + "-" * 80)
print("ANALYSE DÉTAILLÉE")
print("-" * 80)

for e in ecritures_remises:
    print(f"\nÉcriture #{e.id} - {e.date_ecriture}")
    print(f"  Libellé : {e.libelle_ecriture}")
    print(f"  Débit {e.compte_debit} / Crédit {e.compte_credit} : {e.montant}€")
    print(f"  Type : {e.type_ecriture}")

    # Vérifier si c'est correct : Débit 512 / Crédit 627
    if e.compte_debit == '512' and e.compte_credit == '627':
        print(f"  ✅ CORRECT (Débit 512 / Crédit 627 → Diminue charges)")
        remises_correctes.append(e)
    elif e.compte_debit == '627' and e.compte_credit == '512':
        print(f"  ❌ INCORRECT (Débit 627 / Crédit 512 → Augmente charges)")
        remises_incorrectes.append(e)
    else:
        print(f"  ⚠️  INATTENDU (comptes {e.compte_debit}/{e.compte_credit})")
        remises_incorrectes.append(e)

# Résumé
print("\n" + "=" * 80)
print("📊 RÉSUMÉ")
print("=" * 80)

total_correctes = sum(e.montant for e in remises_correctes)
total_incorrectes = sum(e.montant for e in remises_incorrectes)

print(f"\n✅ Remises CORRECTES : {len(remises_correctes)}")
print(f"   Total : {total_correctes}€")
print(f"   (Débit 512 / Crédit 627 → Diminue charges)")

print(f"\n❌ Remises INCORRECTES : {len(remises_incorrectes)}")
print(f"   Total : {total_incorrectes}€")
print(f"   (Débit 627 / Crédit 512 → Augmente charges)")

# Calculer impact sur résultat
if remises_incorrectes:
    impact = total_incorrectes * 2
    print(f"\n⚠️  IMPACT SUR RÉSULTAT : +{impact}€")
    print(f"   (Charges augmentées de {total_incorrectes}€ au lieu de diminuées)")
    print(f"   (Écart total = {total_incorrectes}€ × 2 = {impact}€)")

# Vérifier si l'écart correspond
print(f"\n🔍 DIAGNOSTIC ÉCART BILAN")
print(f"   Écart actuel bilan : 2,63€")
print(f"   Total remises incorrectes : {total_incorrectes}€")
if abs(float(total_incorrectes) - 2.63) < 0.01:
    print(f"   ✅ L'écart correspond exactement aux remises incorrectes !")
    print(f"\n💡 SOLUTION : Corriger les {len(remises_incorrectes)} remises incorrectes")

session.close()

print("\n" + "=" * 80)
