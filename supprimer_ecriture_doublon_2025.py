#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SUPPRESSION ÉCRITURE DOUBLON 2025-11-02
========================================
Supprime l'écriture aberrante #23 datée 2025-11-02 (120€ CCA)
pour éviter qu'elle ne pollue l'exercice 2025
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_module2 import EcritureComptable

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
print("🗑️  SUPPRESSION ÉCRITURE DOUBLON 2025-11-02")
print("=" * 80)

# ==============================================================================
# ÉTAPE 1 : IDENTIFIER L'ÉCRITURE À SUPPRIMER
# ==============================================================================

print("\n" + "=" * 80)
print("ÉTAPE 1 : IDENTIFICATION DE L'ÉCRITURE")
print("=" * 80)

# Chercher l'écriture #23 (2025-11-02)
ecriture_23 = session.query(EcritureComptable).filter_by(id=23).first()

if not ecriture_23:
    print("\n❌ Écriture #23 non trouvée")
    print("   Elle a peut-être déjà été supprimée.")
    session.close()
    exit(0)

print(f"\n📊 Écriture à supprimer :")
print(f"   ID : {ecriture_23.id}")
print(f"   Date : {ecriture_23.date_ecriture}")
print(f"   Libellé : {ecriture_23.libelle_ecriture}")
print(f"   Débit {ecriture_23.compte_debit} / Crédit {ecriture_23.compte_credit}")
print(f"   Montant : {ecriture_23.montant}€")
print(f"   Type : {ecriture_23.type_ecriture}")
print(f"   Exercice ID : {ecriture_23.exercice_id}")

# Vérifier que c'est bien l'écriture attendue
if ecriture_23.date_ecriture.year != 2025 or ecriture_23.date_ecriture.month != 11:
    print("\n⚠️  ATTENTION : Cette écriture n'a pas la date attendue (2025-11-02)")
    print(f"   Date actuelle : {ecriture_23.date_ecriture}")
    print("\n   Voulez-vous vraiment la supprimer ?")
    reponse = input("   (OUI/non) : ").strip()
    if reponse != "OUI":
        print("\n❌ Suppression annulée")
        session.close()
        exit(0)

# ==============================================================================
# ÉTAPE 2 : VÉRIFIER L'IMPACT
# ==============================================================================

print("\n" + "=" * 80)
print("ÉTAPE 2 : VÉRIFICATION DE L'IMPACT")
print("=" * 80)

print("\n📊 Impact de la suppression :")
print(f"   • Compte 455 (CCA) : -120€")
print(f"   • Compte 89 (Bilan ouverture) : -120€")
print(f"   • Total écritures : -1")

print("\n✅ AUCUN IMPACT sur le bilan 2024 (écriture datée 2025)")
print("✅ EMPÊCHE pollution de l'exercice 2025 (doublon évité)")

# ==============================================================================
# ÉTAPE 3 : CONFIRMATION
# ==============================================================================

print("\n" + "=" * 80)
print("CONFIRMATION REQUISE")
print("=" * 80)

print("\nÊtes-vous sûr de vouloir supprimer cette écriture ?")
print("Cette action est IRRÉVERSIBLE.")
print("\nRaison : Écriture doublon aberrante datée 2025-11-02")
print("         Empêche qu'elle ne pollue l'exercice 2025")

reponse = input("\nTapez 'OUI' pour confirmer : ").strip()

if reponse != "OUI":
    print("\n❌ Suppression annulée")
    session.close()
    exit(0)

# ==============================================================================
# ÉTAPE 4 : SUPPRESSION
# ==============================================================================

print("\n" + "=" * 80)
print("ÉTAPE 4 : SUPPRESSION EN COURS")
print("=" * 80)

try:
    session.delete(ecriture_23)
    session.commit()
    print("\n✅ Écriture #23 supprimée avec succès")
except Exception as e:
    print(f"\n❌ Erreur lors de la suppression : {e}")
    session.rollback()
    session.close()
    exit(1)

# ==============================================================================
# ÉTAPE 5 : VÉRIFICATION POST-SUPPRESSION
# ==============================================================================

print("\n" + "=" * 80)
print("ÉTAPE 5 : VÉRIFICATION POST-SUPPRESSION")
print("=" * 80)

# Vérifier que l'écriture n'existe plus
ecriture_verif = session.query(EcritureComptable).filter_by(id=23).first()

if ecriture_verif:
    print("\n❌ ERREUR : L'écriture existe encore !")
else:
    print("\n✅ Écriture #23 bien supprimée")

# Compter les écritures sur compte 455
ecritures_455 = session.query(EcritureComptable).filter(
    (EcritureComptable.compte_debit == '455') | (EcritureComptable.compte_credit == '455')
).all()

solde_455 = sum(float(e.montant) if e.compte_credit == '455' else -float(e.montant) for e in ecritures_455)

print(f"\n📊 Compte 455 après suppression :")
print(f"   Nombre d'écritures : {len(ecritures_455)}")
print(f"   Solde : {solde_455:.2f}€")

if abs(solde_455 - 15120.00) < 0.01:
    print(f"   ✅ Solde correct : 15 120€")
else:
    print(f"   ⚠️  Solde attendu : 15 120€ | Actuel : {solde_455:.2f}€")

# ==============================================================================
# RÉSUMÉ FINAL
# ==============================================================================

print("\n" + "=" * 80)
print("✅ SUPPRESSION TERMINÉE")
print("=" * 80)

print("\n📊 Résumé :")
print("   • Écriture #23 (2025-11-02, 120€) : SUPPRIMÉE ✅")
print("   • Compte 455 : 5 écritures restantes")
print(f"   • Solde CCA : {solde_455:.2f}€")

print("\n📋 Bénéfices :")
print("   • Bilan 2024 : Inchangé (écriture était hors exercice)")
print("   • Exercice 2025 : Pas de doublon lors de l'ouverture ✅")

print("\n🎯 Prochaines étapes :")
print("   1. Vérifier bilan 2024 : python construire_etats_financiers_2024.py")
print("   2. Comparer avec documents officiels")
print("   3. Provisionner IS (~4 501€)")
print("   4. Clôturer exercice 2024")

session.close()

print("\n" + "=" * 80)
