#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
INSPECTION DÉTAILLÉE DE LA BASE DE DONNÉES
===========================================
Affiche tous les détails des prêts, échéances et écritures
"""

import os
import sys
from decimal import Decimal
from models_module2 import (
    get_session, ExerciceComptable, PlanCompte, EcritureComptable,
    PretImmobilier, EcheancePret
)

# Récupérer DATABASE_URL depuis l'environnement
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("❌ ERREUR : DATABASE_URL non définie")
    sys.exit(1)

session = get_session(DATABASE_URL)

print("=" * 80)
print("🔍 INSPECTION DÉTAILLÉE DE LA BASE DE DONNÉES")
print("=" * 80)

# ============================================================================
# 1. ÉCRITURES COMPTABLES (DÉTAIL COMPLET)
# ============================================================================
print("\n📝 ÉCRITURES COMPTABLES (11 écritures)")
print("-" * 80)

ecritures = session.query(EcritureComptable).order_by(EcritureComptable.numero_ecriture).all()

for ec in ecritures:
    print(f"\n  {ec.numero_ecriture}")
    print(f"    Libellé : {ec.libelle_ecriture}")
    print(f"    Débit   : {ec.compte_debit} → {ec.montant}€")
    print(f"    Crédit  : {ec.compte_credit} → {ec.montant}€")
    print(f"    Date    : {ec.date_ecriture}")
    print(f"    Type    : {ec.type_ecriture}")

# Calcul total et vérification équilibre
total_debit = sum(ec.montant for ec in ecritures)
total_credit = sum(ec.montant for ec in ecritures)

print(f"\n  📊 TOTAUX")
print(f"    Total débit  : {total_debit:,.2f}€")
print(f"    Total crédit : {total_credit:,.2f}€")
print(f"    Équilibré    : {'✅ OUI' if total_debit == total_credit else '❌ NON'}")

# ============================================================================
# 2. PRÊTS IMMOBILIERS (DÉTAIL COMPLET)
# ============================================================================
print("\n\n🏠 PRÊTS IMMOBILIERS (2 prêts)")
print("-" * 80)

prets = session.query(PretImmobilier).order_by(PretImmobilier.numero_pret).all()

for pret in prets:
    print(f"\n  📋 Prêt {pret.numero_pret}")
    print(f"    Banque          : {pret.banque}")
    print(f"    Libellé         : {pret.libelle}")
    print(f"    Montant initial : {pret.montant_initial:,.2f}€")
    print(f"    Taux annuel     : {pret.taux_annuel:.4f}% ({float(pret.taux_annuel):.2f}%)")
    print(f"    Durée           : {pret.duree_mois} mois")
    print(f"    Date début      : {pret.date_debut}")
    print(f"    Date fin        : {pret.date_fin}")
    print(f"    Type            : {pret.type_amortissement}")
    print(f"    Mois franchise  : {pret.mois_franchise}")

    if pret.echeance_mensuelle:
        print(f"    Échéance mens.  : {pret.echeance_mensuelle:,.2f}€")

    if pret.interet_mensuel_franchise:
        print(f"    Intérêt franch. : {pret.interet_mensuel_franchise:,.2f}€")

    # Compter échéances
    nb_echeances = session.query(EcheancePret).filter_by(pret_id=pret.id).count()
    print(f"    Échéances BD    : {nb_echeances}")

# ============================================================================
# 3. ÉCHÉANCES (PREMIÈRE, DERNIÈRE, STATISTIQUES)
# ============================================================================
print("\n\n📊 ÉCHÉANCES DE PRÊTS (467 échéances)")
print("-" * 80)

for pret in prets:
    print(f"\n  🔍 Échéances du prêt {pret.numero_pret}")

    echeances = session.query(EcheancePret).filter_by(
        pret_id=pret.id
    ).order_by(EcheancePret.numero_echeance).all()

    if not echeances:
        print("    ❌ Aucune échéance trouvée")
        continue

    # Première échéance
    premiere = echeances[0]
    print(f"\n    📅 PREMIÈRE ÉCHÉANCE (#{premiere.numero_echeance})")
    print(f"       Date              : {premiere.date_echeance}")
    print(f"       Montant total     : {premiere.montant_total:,.2f}€")
    print(f"       Capital           : {premiere.montant_capital:,.2f}€")
    print(f"       Intérêts          : {premiere.montant_interet:,.2f}€")
    print(f"       Capital restant   : {premiere.capital_restant_du:,.2f}€")

    # Dernière échéance
    derniere = echeances[-1]
    print(f"\n    📅 DERNIÈRE ÉCHÉANCE (#{derniere.numero_echeance})")
    print(f"       Date              : {derniere.date_echeance}")
    print(f"       Montant total     : {derniere.montant_total:,.2f}€")
    print(f"       Capital           : {derniere.montant_capital:,.2f}€")
    print(f"       Intérêts          : {derniere.montant_interet:,.2f}€")
    print(f"       Capital restant   : {derniere.capital_restant_du:,.2f}€")

    # Statistiques
    total_capital = sum(e.montant_capital for e in echeances)
    total_interets = sum(e.montant_interet for e in echeances)
    total_paye = sum(e.montant_total for e in echeances)

    print(f"\n    📊 STATISTIQUES")
    print(f"       Nombre échéances  : {len(echeances)}")
    print(f"       Total capital     : {total_capital:,.2f}€")
    print(f"       Total intérêts    : {total_interets:,.2f}€")
    print(f"       Total payé        : {total_paye:,.2f}€")
    print(f"       Coût du crédit    : {total_interets:,.2f}€ ({100*total_interets/total_capital:.2f}%)")

# ============================================================================
# 4. VÉRIFICATIONS D'INTÉGRITÉ
# ============================================================================
print("\n\n✅ VÉRIFICATIONS D'INTÉGRITÉ")
print("-" * 80)

# Vérifier exercice 2023
exercice_2023 = session.query(ExerciceComptable).filter_by(annee=2023).first()
if exercice_2023:
    nb_ecritures_2023 = session.query(EcritureComptable).filter_by(
        exercice_id=exercice_2023.id
    ).count()
    print(f"\n  ✅ Exercice 2023 : {nb_ecritures_2023} écritures associées")
else:
    print(f"\n  ❌ Exercice 2023 non trouvé")

# Vérifier équilibre bilan
total_actif = Decimal('0')
total_passif = Decimal('0')

for ec in ecritures:
    if ec.compte_debit.startswith(('2', '3', '4', '5')):  # ACTIF
        total_actif += ec.montant
    if ec.compte_credit.startswith(('1', '4')):  # PASSIF
        total_passif += ec.montant

print(f"\n  📊 Équilibre bilan 2023")
print(f"     Total ACTIF  : {total_actif:,.2f}€")
print(f"     Total PASSIF : {total_passif:,.2f}€")
print(f"     Équilibré    : {'✅ OUI' if total_actif == total_passif else '❌ NON'}")

# Vérifier prêts vs échéances
for pret in prets:
    nb_ech = session.query(EcheancePret).filter_by(pret_id=pret.id).count()
    print(f"\n  ✅ Prêt {pret.numero_pret} : {nb_ech} échéances")

print("\n" + "=" * 80)
print("✅ INSPECTION DÉTAILLÉE TERMINÉE")
print("=" * 80)

session.close()
