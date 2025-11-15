#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VÉRIFICATION PLAN COMPTABLE - Conformité PCG
=============================================
Identifie les comptes utilisés de manière incorrecte par rapport au PCG
"""

import os
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
print("🔍 VÉRIFICATION CONFORMITÉ PLAN COMPTABLE (PCG)")
print("=" * 80)

# ==============================================================================
# DÉFINITIONS PCG CORRECTES
# ==============================================================================

PCG_CORRECT = {
    '444': {
        'libelle': 'État - Impôts sur les bénéfices',
        'usage': 'IS dû, à payer à l\'État',
        'type': 'PASSIF'
    },
    '455': {
        'libelle': 'Associés - Comptes courants',
        'usage': 'Avances/apports des associés remboursables',
        'type': 'PASSIF'
    },
    '4551': {
        'libelle': 'Associé 1 - Compte courant',
        'usage': 'CCA Ulrik',
        'type': 'PASSIF'
    },
    '4552': {
        'libelle': 'Associé 2 - Compte courant',
        'usage': 'CCA Emma',
        'type': 'PASSIF'
    },
    '4553': {
        'libelle': 'Associé 3 - Compte courant',
        'usage': 'CCA Pauline',
        'type': 'PASSIF'
    },
}

# ==============================================================================
# 1. VÉRIFIER LE PLAN DE COMPTES
# ==============================================================================

print("\n" + "=" * 80)
print("1️⃣ VÉRIFICATION PLAN DE COMPTES")
print("=" * 80)

comptes_a_verifier = ['444', '455', '4551', '4552', '4553']
problemes_plan = []

for num_compte in comptes_a_verifier:
    compte_bd = session.query(PlanCompte).filter_by(numero_compte=num_compte).first()

    if num_compte in PCG_CORRECT:
        pcg = PCG_CORRECT[num_compte]

        if compte_bd:
            print(f"\n📊 Compte {num_compte}")
            print(f"   BD    : {compte_bd.libelle}")
            print(f"   PCG   : {pcg['libelle']}")
            print(f"   Usage : {pcg['usage']}")

            if compte_bd.libelle != pcg['libelle']:
                print(f"   ⚠️  LIBELLÉ INCORRECT")
                problemes_plan.append({
                    'compte': num_compte,
                    'probleme': 'libelle',
                    'actuel': compte_bd.libelle,
                    'correct': pcg['libelle']
                })
            else:
                print(f"   ✅ Libellé correct")
        else:
            print(f"\n📊 Compte {num_compte}")
            print(f"   ❌ ABSENT du plan de comptes")
            print(f"   PCG   : {pcg['libelle']}")
            print(f"   Usage : {pcg['usage']}")

            problemes_plan.append({
                'compte': num_compte,
                'probleme': 'absent',
                'correct': pcg['libelle']
            })

# ==============================================================================
# 2. VÉRIFIER L'UTILISATION DES COMPTES
# ==============================================================================

print("\n" + "=" * 80)
print("2️⃣ VÉRIFICATION UTILISATION DES COMPTES")
print("=" * 80)

# Récupérer toutes les écritures sur compte 444
ecritures_444 = session.query(EcritureComptable).filter(
    (EcritureComptable.compte_debit == '444') | (EcritureComptable.compte_credit == '444')
).all()

print(f"\n📊 Compte 444 (État - IS) :")
print(f"   Nombre d'écritures : {len(ecritures_444)}")

if ecritures_444:
    print("\n   Détail des écritures :")
    for e in ecritures_444:
        print(f"   • {e.date_ecriture} | {e.libelle_ecriture[:50]}")
        print(f"     Débit {e.compte_debit} / Crédit {e.compte_credit} : {e.montant}€")
        print(f"     Type : {e.type_ecriture}")

        # Vérifier si c'est vraiment de l'IS
        if 'IMPOT' not in e.libelle_ecriture.upper() and 'IS' not in e.libelle_ecriture.upper():
            print(f"     ⚠️  USAGE INCORRECT : Ne semble pas être de l'IS")

# Récupérer toutes les écritures sur compte 455
ecritures_455 = session.query(EcritureComptable).filter(
    (EcritureComptable.compte_debit == '455') | (EcritureComptable.compte_credit == '455')
).all()

print(f"\n📊 Compte 455 (CCA) :")
print(f"   Nombre d'écritures : {len(ecritures_455)}")

if ecritures_455:
    print("\n   Détail des écritures :")
    for e in ecritures_455:
        print(f"   • {e.date_ecriture} | {e.libelle_ecriture[:50]}")
        print(f"     Débit {e.compte_debit} / Crédit {e.compte_credit} : {e.montant}€")
        print(f"     Type : {e.type_ecriture}")

# ==============================================================================
# 3. PROPOSITIONS DE CORRECTION
# ==============================================================================

print("\n" + "=" * 80)
print("3️⃣ PROPOSITIONS DE CORRECTION")
print("=" * 80)

if ecritures_444:
    print("\n⚠️  COMPTE 444 utilisé de manière incorrecte")
    print("\nActions recommandées :")
    print("1. Identifier la nature réelle des écritures sur 444")
    print("2. Si CCA → Migrer vers 455 (ou 4551/4552/4553 par associé)")
    print("3. Si IS → Conserver sur 444")

    # Calculer le solde 444
    solde_444 = 0
    for e in ecritures_444:
        if e.compte_debit == '444':
            solde_444 -= float(e.montant)
        if e.compte_credit == '444':
            solde_444 += float(e.montant)

    print(f"\nSolde compte 444 : {solde_444:.2f}€ ({'créditeur' if solde_444 > 0 else 'débiteur'})")

# Calculer le solde 455
if ecritures_455:
    solde_455 = 0
    for e in ecritures_455:
        if e.compte_debit == '455':
            solde_455 -= float(e.montant)
        if e.compte_credit == '455':
            solde_455 += float(e.montant)

    print(f"\nSolde compte 455 : {solde_455:.2f}€ ({'créditeur' if solde_455 > 0 else 'débiteur'})")

# ==============================================================================
# 4. AUTRES COMPTES POTENTIELLEMENT INCORRECTS
# ==============================================================================

print("\n" + "=" * 80)
print("4️⃣ AUTRES COMPTES À VÉRIFIER")
print("=" * 80)

# Lister tous les comptes utilisés
comptes_utilises = set()
for e in session.query(EcritureComptable).all():
    comptes_utilises.add(e.compte_debit)
    comptes_utilises.add(e.compte_credit)

print("\nComptes classe 4 utilisés :")
comptes_4 = sorted([c for c in comptes_utilises if c and c[0] == '4'])
for c in comptes_4:
    cpte = session.query(PlanCompte).filter_by(numero_compte=c).first()
    if cpte:
        print(f"   {c} : {cpte.libelle}")
    else:
        print(f"   {c} : (non défini dans plan de comptes)")

# ==============================================================================
# 5. RÉSUMÉ ET RECOMMANDATIONS
# ==============================================================================

print("\n" + "=" * 80)
print("5️⃣ RÉSUMÉ ET RECOMMANDATIONS")
print("=" * 80)

if len(ecritures_444) > 0:
    print("\n❌ PROBLÈMES DÉTECTÉS :")
    print(f"   • Compte 444 utilisé {len(ecritures_444)} fois (devrait être pour IS uniquement)")
    print(f"   • Solde 444 : {solde_444:.2f}€")

    print("\n📋 PLAN D'ACTION :")
    print("   1. Créer un script de migration 444 → 455 (si CCA)")
    print("   2. Corriger le plan de comptes")
    print("   3. Mettre à jour les détecteurs d'événements")
    print("   4. Réinitialiser et retraiter les PDFs 2024")
else:
    print("\n✅ Aucun problème détecté sur compte 444")

session.close()

print("\n" + "=" * 80)
