#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CORRECTION COMPTE 444 → 455
============================
Migre les écritures CCA incorrectement classées sur 444 vers 455
Corrige le plan de comptes selon PCG
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
print("🔧 CORRECTION COMPTE 444 → 455")
print("=" * 80)

# ==============================================================================
# ÉTAPE 1 : IDENTIFIER LES ÉCRITURES À MIGRER
# ==============================================================================

print("\n" + "=" * 80)
print("ÉTAPE 1 : IDENTIFICATION DES ÉCRITURES À MIGRER")
print("=" * 80)

# Récupérer toutes les écritures sur 444
ecritures_444 = session.query(EcritureComptable).filter(
    (EcritureComptable.compte_debit == '444') | (EcritureComptable.compte_credit == '444')
).all()

print(f"\n📊 Écritures sur compte 444 : {len(ecritures_444)}")

ecritures_a_migrer = []
ecritures_a_supprimer = []

for e in ecritures_444:
    print(f"\n• Écriture #{e.id} - {e.date_ecriture}")
    print(f"  Libellé : {e.libelle_ecriture}")
    print(f"  Débit {e.compte_debit} / Crédit {e.compte_credit} : {e.montant}€")
    print(f"  Type : {e.type_ecriture}")

    # Identifier si c'est un CCA ou de l'IS
    if 'COMPTE COURANT' in e.libelle_ecriture.upper() or 'ASSOCIE' in e.libelle_ecriture.upper():
        print(f"  → CCA : À MIGRER vers 455")
        ecritures_a_migrer.append(e)
    elif e.date_ecriture.year == 2025:
        print(f"  → Écriture 2025 dans exercice 2024 : À SUPPRIMER")
        ecritures_a_supprimer.append(e)
    else:
        print(f"  → Nature incertaine : Vérification manuelle requise")

print(f"\n📋 Résumé :")
print(f"   Écritures à migrer (444 → 455) : {len(ecritures_a_migrer)}")
print(f"   Écritures à supprimer : {len(ecritures_a_supprimer)}")

# ==============================================================================
# ÉTAPE 2 : CORRIGER LE PLAN DE COMPTES
# ==============================================================================

print("\n" + "=" * 80)
print("ÉTAPE 2 : CORRECTION DU PLAN DE COMPTES")
print("=" * 80)

# Corriger le compte 444
compte_444 = session.query(PlanCompte).filter_by(numero_compte='444').first()
if compte_444:
    ancien_libelle = compte_444.libelle
    nouveau_libelle = "État - Impôts sur les bénéfices"

    print(f"\n📊 Compte 444 :")
    print(f"   Ancien : {ancien_libelle}")
    print(f"   Nouveau : {nouveau_libelle}")

    compte_444.libelle = nouveau_libelle
    print(f"   ✅ Libellé mis à jour")
else:
    print("\n⚠️  Compte 444 absent du plan de comptes")

# Ajouter les sous-comptes 4551, 4552, 4553 si manquants
comptes_a_ajouter = [
    ('4551', 'Associé 1 - Compte courant Ulrik', 'PASSIF'),
    ('4552', 'Associé 2 - Compte courant Emma', 'PASSIF'),
    ('4553', 'Associé 3 - Compte courant Pauline', 'PASSIF'),
]

for num_compte, libelle, type_compte in comptes_a_ajouter:
    compte_existant = session.query(PlanCompte).filter_by(numero_compte=num_compte).first()

    if not compte_existant:
        print(f"\n📊 Compte {num_compte} :")
        print(f"   Libellé : {libelle}")
        print(f"   Type : {type_compte}")

        nouveau_compte = PlanCompte(
            numero_compte=num_compte,
            libelle=libelle,
            type_compte=type_compte,
            classe=4
        )
        session.add(nouveau_compte)
        print(f"   ✅ Compte ajouté au plan")
    else:
        print(f"\n✅ Compte {num_compte} déjà présent : {compte_existant.libelle}")

# ==============================================================================
# ÉTAPE 3 : DEMANDER CONFIRMATION
# ==============================================================================

print("\n" + "=" * 80)
print("CONFIRMATION REQUISE")
print("=" * 80)

print(f"\nActions à effectuer :")
print(f"  1. Corriger libellé compte 444 : ✅")
print(f"  2. Ajouter comptes 4551/4552/4553 : ✅")
print(f"  3. Migrer {len(ecritures_a_migrer)} écritures : 444 → 455")
print(f"  4. Supprimer {len(ecritures_a_supprimer)} écritures en doublon")

reponse = input("\nVoulez-vous appliquer ces corrections ? (OUI/non) : ").strip()

if reponse != "OUI":
    print("\n❌ Annulation des corrections")
    session.rollback()
    session.close()
    exit(0)

# ==============================================================================
# ÉTAPE 4 : MIGRER LES ÉCRITURES
# ==============================================================================

print("\n" + "=" * 80)
print("ÉTAPE 4 : MIGRATION DES ÉCRITURES")
print("=" * 80)

nb_migrees = 0
for e in ecritures_a_migrer:
    print(f"\n• Écriture #{e.id} - {e.date_ecriture}")
    print(f"  Avant : Débit {e.compte_debit} / Crédit {e.compte_credit}")

    # Remplacer 444 par 455
    if e.compte_debit == '444':
        e.compte_debit = '455'
    if e.compte_credit == '444':
        e.compte_credit = '455'

    print(f"  Après : Débit {e.compte_debit} / Crédit {e.compte_credit}")
    print(f"  ✅ Migré")
    nb_migrees += 1

print(f"\n📊 {nb_migrees} écritures migrées vers compte 455")

# ==============================================================================
# ÉTAPE 5 : SUPPRIMER LES DOUBLONS
# ==============================================================================

print("\n" + "=" * 80)
print("ÉTAPE 5 : SUPPRESSION DES DOUBLONS")
print("=" * 80)

nb_supprimees = 0
for e in ecritures_a_supprimer:
    print(f"\n• Écriture #{e.id} - {e.date_ecriture}")
    print(f"  Libellé : {e.libelle_ecriture}")
    print(f"  Montant : {e.montant}€")

    session.delete(e)
    print(f"  ✅ Supprimée")
    nb_supprimees += 1

print(f"\n📊 {nb_supprimees} écritures supprimées")

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
# ÉTAPE 7 : VÉRIFICATION POST-CORRECTION
# ==============================================================================

print("\n" + "=" * 80)
print("ÉTAPE 7 : VÉRIFICATION POST-CORRECTION")
print("=" * 80)

# Vérifier compte 444
ecritures_444_apres = session.query(EcritureComptable).filter(
    (EcritureComptable.compte_debit == '444') | (EcritureComptable.compte_credit == '444')
).all()

print(f"\n📊 Compte 444 après correction :")
print(f"   Nombre d'écritures : {len(ecritures_444_apres)}")

if len(ecritures_444_apres) == 0:
    print(f"   ✅ Compte 444 vide (normal, réservé pour IS futur)")
else:
    print(f"   ⚠️  Il reste {len(ecritures_444_apres)} écritures sur 444")
    for e in ecritures_444_apres:
        print(f"   • {e.date_ecriture} : {e.libelle_ecriture} ({e.montant}€)")

# Vérifier compte 455
ecritures_455_apres = session.query(EcritureComptable).filter(
    (EcritureComptable.compte_debit == '455') | (EcritureComptable.compte_credit == '455')
).all()

solde_455 = sum(float(e.montant) if e.compte_credit == '455' else -float(e.montant) for e in ecritures_455_apres)

print(f"\n📊 Compte 455 après correction :")
print(f"   Nombre d'écritures : {len(ecritures_455_apres)}")
print(f"   Solde : {solde_455:.2f}€ (créditeur)")

if abs(solde_455 - 15120.00) < 0.01:
    print(f"   ✅ Solde correct (15 120€)")
else:
    print(f"   ⚠️  Solde attendu : 15 120€ | Actuel : {solde_455:.2f}€")

# ==============================================================================
# RÉSUMÉ FINAL
# ==============================================================================

print("\n" + "=" * 80)
print("✅ CORRECTION TERMINÉE")
print("=" * 80)

print(f"\n📊 Résumé des actions :")
print(f"   • Plan de comptes corrigé : ✅")
print(f"   • Écritures migrées (444 → 455) : {nb_migrees}")
print(f"   • Écritures supprimées : {nb_supprimees}")
print(f"   • Compte 444 : {len(ecritures_444_apres)} écritures restantes")
print(f"   • Compte 455 : {len(ecritures_455_apres)} écritures | Solde {solde_455:.2f}€")

print(f"\n📋 Prochaines étapes :")
print(f"   1. Reconstruire états financiers : python construire_etats_financiers_2024.py")
print(f"   2. Vérifier bilan équilibré")
print(f"   3. Comparer avec documents officiels")

session.close()

print("\n" + "=" * 80)
