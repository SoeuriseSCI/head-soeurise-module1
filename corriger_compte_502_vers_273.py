#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CORRECTION COMPTE 502 → 273
===========================
Migre les actions du compte 502 (VMP) vers compte 273 (Titres immobilisés)
Conforme au PCG pour investissement de long terme
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_module2 import EcritureComptable, ExerciceComptable, PlanCompte

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
print("🔧 CORRECTION COMPTE 502 → 273")
print("=" * 80)

# ==============================================================================
# ÉTAPE 1 : IDENTIFIER LES ÉCRITURES À MIGRER
# ==============================================================================

print("\n" + "=" * 80)
print("ÉTAPE 1 : IDENTIFICATION DES ÉCRITURES À MIGRER")
print("=" * 80)

# Récupérer toutes les écritures sur 502
ecritures_502 = session.query(EcritureComptable).filter(
    (EcritureComptable.compte_debit == '502') | (EcritureComptable.compte_credit == '502')
).all()

print(f"\n📊 Écritures sur compte 502 (Actions - VMP) : {len(ecritures_502)}")

if ecritures_502:
    print("\nDétail des écritures :")
    for e in ecritures_502:
        print(f"\n• Écriture #{e.id} - {e.date_ecriture}")
        print(f"  Libellé : {e.libelle_ecriture}")
        print(f"  Débit {e.compte_debit} / Crédit {e.compte_credit} : {e.montant}€")
        print(f"  Type : {e.type_ecriture}")

    # Calculer le solde 502
    solde_502 = 0
    for e in ecritures_502:
        if e.compte_debit == '502':
            solde_502 += float(e.montant)
        if e.compte_credit == '502':
            solde_502 -= float(e.montant)

    print(f"\n📊 Solde compte 502 : {solde_502:.2f}€")

# Récupérer les écritures sur 273
ecritures_273 = session.query(EcritureComptable).filter(
    (EcritureComptable.compte_debit == '273') | (EcritureComptable.compte_credit == '273')
).all()

print(f"\n📊 Écritures sur compte 273 (Titres immobilisés) : {len(ecritures_273)}")

if ecritures_273:
    # Calculer le solde 273
    solde_273 = 0
    for e in ecritures_273:
        if e.compte_debit == '273':
            solde_273 += float(e.montant)
        if e.compte_credit == '273':
            solde_273 -= float(e.montant)

    print(f"   Solde actuel : {solde_273:.2f}€")

# ==============================================================================
# ÉTAPE 2 : VÉRIFIER LE PLAN DE COMPTES
# ==============================================================================

print("\n" + "=" * 80)
print("ÉTAPE 2 : VÉRIFICATION DU PLAN DE COMPTES")
print("=" * 80)

# Vérifier compte 502
compte_502 = session.query(PlanCompte).filter_by(numero_compte='502').first()
if compte_502:
    print(f"\n📊 Compte 502 :")
    print(f"   Libellé actuel : {compte_502.libelle}")
    print(f"   Type : {compte_502.type_compte}")
    print(f"   Usage PCG : Valeurs mobilières de placement (court terme)")
    print(f"   → Inapproprié pour investissement de long terme")

# Vérifier compte 273
compte_273 = session.query(PlanCompte).filter_by(numero_compte='273').first()
if compte_273:
    print(f"\n📊 Compte 273 :")
    print(f"   Libellé actuel : {compte_273.libelle}")
    print(f"   Type : {compte_273.type_compte}")
    print(f"   Usage PCG : Titres immobilisés de l'activité de portefeuille")
    print(f"   → ✅ CORRECT pour investissement de long terme SCI")

# ==============================================================================
# ÉTAPE 3 : CALCULER L'IMPACT
# ==============================================================================

print("\n" + "=" * 80)
print("ÉTAPE 3 : CALCUL DE L'IMPACT")
print("=" * 80)

print(f"\n📊 Avant migration :")
print(f"   Compte 273 (Titres immobilisés) : {solde_273:.2f}€")
print(f"   Compte 502 (Actions VMP)        : {solde_502:.2f}€")

solde_273_apres = solde_273 + solde_502
solde_502_apres = 0

print(f"\n📊 Après migration :")
print(f"   Compte 273 (Titres immobilisés) : {solde_273_apres:.2f}€")
print(f"   Compte 502 (Actions VMP)        : {solde_502_apres:.2f}€")

print(f"\n💡 Impact sur le bilan :")
print(f"   • ACTIF immobilisé (classe 2) : +{solde_502:.2f}€")
print(f"   • ACTIF circulant (classe 5)  : -{solde_502:.2f}€")
print(f"   • Total ACTIF : INCHANGÉ ✅")
print(f"   • Équilibre bilan : MAINTENU ✅")

print(f"\n✅ Meilleure représentation économique :")
print(f"   Les actions sont classées comme investissement de long terme")
print(f"   (conforme à la stratégie patrimoniale SCI)")

# ==============================================================================
# ÉTAPE 4 : CONFIRMATION
# ==============================================================================

print("\n" + "=" * 80)
print("CONFIRMATION REQUISE")
print("=" * 80)

print(f"\nActions à effectuer :")
print(f"  1. Migrer {len(ecritures_502)} écritures : 502 → 273")
print(f"  2. Montant total migré : {solde_502:.2f}€")
print(f"  3. Nouveau solde compte 273 : {solde_273_apres:.2f}€")

reponse = input("\nVoulez-vous appliquer cette correction ? (OUI/non) : ").strip()

if reponse != "OUI":
    print("\n❌ Annulation de la migration")
    session.rollback()
    session.close()
    exit(0)

# ==============================================================================
# ÉTAPE 5 : MIGRER LES ÉCRITURES
# ==============================================================================

print("\n" + "=" * 80)
print("ÉTAPE 5 : MIGRATION DES ÉCRITURES")
print("=" * 80)

nb_migrees = 0
for e in ecritures_502:
    print(f"\n• Écriture #{e.id} - {e.date_ecriture}")
    print(f"  Avant : Débit {e.compte_debit} / Crédit {e.compte_credit}")

    # Remplacer 502 par 273
    if e.compte_debit == '502':
        e.compte_debit = '273'
    if e.compte_credit == '502':
        e.compte_credit = '273'

    print(f"  Après : Débit {e.compte_debit} / Crédit {e.compte_credit}")
    print(f"  ✅ Migré")
    nb_migrees += 1

print(f"\n📊 {nb_migrees} écritures migrées vers compte 273")

# ==============================================================================
# ÉTAPE 6 : COMMIT
# ==============================================================================

print("\n" + "=" * 80)
print("ÉTAPE 6 : COMMIT DES MODIFICATIONS")
print("=" * 80)

try:
    session.commit()
    print("\n✅ Modifications enregistrées avec succès")
except Exception as e:
    print(f"\n❌ Erreur lors du commit : {e}")
    session.rollback()
    session.close()
    exit(1)

# ==============================================================================
# ÉTAPE 7 : VÉRIFICATION POST-MIGRATION
# ==============================================================================

print("\n" + "=" * 80)
print("ÉTAPE 7 : VÉRIFICATION POST-MIGRATION")
print("=" * 80)

# Vérifier compte 502
ecritures_502_apres = session.query(EcritureComptable).filter(
    (EcritureComptable.compte_debit == '502') | (EcritureComptable.compte_credit == '502')
).all()

print(f"\n📊 Compte 502 après migration :")
print(f"   Nombre d'écritures : {len(ecritures_502_apres)}")

if len(ecritures_502_apres) == 0:
    print(f"   ✅ Compte 502 vide (actions migrées vers 273)")
else:
    print(f"   ⚠️  Il reste {len(ecritures_502_apres)} écritures sur 502")

# Vérifier compte 273
ecritures_273_apres = session.query(EcritureComptable).filter(
    (EcritureComptable.compte_debit == '273') | (EcritureComptable.compte_credit == '273')
).all()

solde_273_final = sum(
    float(e.montant) if e.compte_debit == '273' else -float(e.montant)
    for e in ecritures_273_apres
)

print(f"\n📊 Compte 273 après migration :")
print(f"   Nombre d'écritures : {len(ecritures_273_apres)}")
print(f"   Solde : {solde_273_final:.2f}€")

if abs(solde_273_final - solde_273_apres) < 0.01:
    print(f"   ✅ Solde correct : {solde_273_apres:.2f}€")
else:
    print(f"   ⚠️  Solde attendu : {solde_273_apres:.2f}€ | Actuel : {solde_273_final:.2f}€")

# ==============================================================================
# RÉSUMÉ FINAL
# ==============================================================================

print("\n" + "=" * 80)
print("✅ MIGRATION TERMINÉE")
print("=" * 80)

print(f"\n📊 Résumé des actions :")
print(f"   • Écritures migrées (502 → 273) : {nb_migrees}")
print(f"   • Compte 502 (Actions VMP) : {len(ecritures_502_apres)} écritures restantes")
print(f"   • Compte 273 (Titres immobilisés) : {len(ecritures_273_apres)} écritures | Solde {solde_273_final:.2f}€")

print(f"\n✅ Bénéfices de la migration :")
print(f"   • Classification PCG correcte : Titres immobilisés (long terme)")
print(f"   • Meilleure image financière : ACTIF immobilisé renforcé")
print(f"   • Conforme stratégie patrimoniale SCI")

print(f"\n📋 Prochaines étapes :")
print(f"   1. Reconstruire états financiers : python construire_etats_financiers_2024.py")
print(f"   2. Vérifier bilan équilibré")
print(f"   3. Comparer avec documents officiels")

session.close()

print("\n" + "=" * 80)
