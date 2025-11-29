#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PATCH : Ajouter l'écriture de reprise du résultat 2024 dans le bilan d'ouverture 2025

Problème :
- Le bilan d'ouverture 2025 ne reprend pas le résultat 2024
- L'écriture d'affectation débite le compte 120 sans qu'il ait été crédité
- Résultat : compte 89 déséquilibré de -17,766.29€

Solution :
- Ajouter l'écriture manquante : Débit 89 / Crédit 120 : 17,766.29€
- Cette écriture intègre le résultat 2024 au bilan d'ouverture 2025
"""

import os
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_module2 import ExerciceComptable, EcritureComptable

# Connexion BD
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("❌ DATABASE_URL non définie")
    exit(1)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

print("\n" + "="*100)
print("PATCH : REPRISE RÉSULTAT 2024 DANS BILAN D'OUVERTURE 2025")
print("="*100 + "\n")

# 1. Vérifier l'état actuel
print("1. VÉRIFICATION ÉTAT ACTUEL")
print("-"*100)

exercice_2025 = session.query(ExerciceComptable).filter_by(annee=2025).first()
if not exercice_2025:
    print("❌ Exercice 2025 non trouvé")
    session.close()
    exit(1)

print(f"✅ Exercice 2025 trouvé (ID: {exercice_2025.id})")

# Vérifier si l'écriture existe déjà
ecriture_existante = session.query(EcritureComptable).filter_by(
    exercice_id=exercice_2025.id,
    numero_ecriture='2025-0101-OUV-RES'
).first()

if ecriture_existante:
    print(f"⚠️  L'écriture 2025-0101-OUV-RES existe déjà (ID: {ecriture_existante.id})")
    print("   Aucune action nécessaire.")
    session.close()
    exit(0)

# Calculer le solde du compte 89 avant patch
ecritures_ouverture = session.query(EcritureComptable).filter_by(
    exercice_id=exercice_2025.id,
    type_ecriture='BILAN_OUVERTURE'
).all()

solde_89_avant_debit = Decimal('0')
solde_89_avant_credit = Decimal('0')

for e in ecritures_ouverture:
    if e.compte_debit == '89':
        solde_89_avant_debit += e.montant
    if e.compte_credit == '89':
        solde_89_avant_credit += e.montant

solde_89_avant = solde_89_avant_debit - solde_89_avant_credit

print(f"\nCompte 89 AVANT patch :")
print(f"  Débit  : {solde_89_avant_debit:>15,.2f} €")
print(f"  Crédit : {solde_89_avant_credit:>15,.2f} €")
print(f"  Solde  : {solde_89_avant:>15,.2f} €")

if abs(solde_89_avant) < Decimal('0.01'):
    print("✅ Compte 89 déjà équilibré - aucun patch nécessaire")
    session.close()
    exit(0)

# 2. Créer l'écriture de reprise
print(f"\n2. CRÉATION ÉCRITURE DE REPRISE")
print("-"*100)

resultat_2024 = abs(solde_89_avant)  # Le déséquilibre du 89 = résultat 2024

print(f"Résultat 2024 à reprendre : {resultat_2024:,.2f} €")

# Déterminer sens de l'écriture
if solde_89_avant < 0:
    # Solde 89 créditeur → résultat positif (bénéfice)
    compte_debit = '89'
    compte_credit = '120'
    print("Type : Bénéfice (solde 89 créditeur)")
else:
    # Solde 89 débiteur → résultat négatif (perte)
    compte_debit = '120'
    compte_credit = '89'
    print("Type : Perte (solde 89 débiteur)")

# Créer l'écriture
nouvelle_ecriture = EcritureComptable(
    exercice_id=exercice_2025.id,
    numero_ecriture='2025-0101-OUV-RES',
    date_ecriture=date(2025, 1, 1),
    libelle_ecriture='Bilan d\'ouverture 2025 - Résultat exercice 2024',
    type_ecriture='BILAN_OUVERTURE',
    compte_debit=compte_debit,
    compte_credit=compte_credit,
    montant=resultat_2024,
    source_email_id='PATCH_2024',
    source_email_from='system@soeurise.sci',
    validee_at=datetime.now(),
    notes='Patch : reprise résultat 2024 dans bilan ouverture 2025'
)

print(f"\nÉcriture à créer :")
print(f"  Numéro  : {nouvelle_ecriture.numero_ecriture}")
print(f"  Date    : {nouvelle_ecriture.date_ecriture}")
print(f"  Débit   : {nouvelle_ecriture.compte_debit}")
print(f"  Crédit  : {nouvelle_ecriture.compte_credit}")
print(f"  Montant : {nouvelle_ecriture.montant:,.2f} €")

# 3. Demander confirmation
print(f"\n3. CONFIRMATION")
print("-"*100)
reponse = input("Voulez-vous appliquer ce patch ? (oui/non) : ")

if reponse.lower() != 'oui':
    print("\n❌ Patch annulé par l'utilisateur")
    session.close()
    exit(0)

# 4. Appliquer le patch
print(f"\n4. APPLICATION DU PATCH")
print("-"*100)

try:
    session.add(nouvelle_ecriture)
    session.commit()

    print(f"✅ Écriture créée avec succès (ID: {nouvelle_ecriture.id})")

    # Vérifier le résultat
    ecritures_ouverture_apres = session.query(EcritureComptable).filter_by(
        exercice_id=exercice_2025.id,
        type_ecriture='BILAN_OUVERTURE'
    ).all()

    solde_89_apres_debit = Decimal('0')
    solde_89_apres_credit = Decimal('0')

    for e in ecritures_ouverture_apres:
        if e.compte_debit == '89':
            solde_89_apres_debit += e.montant
        if e.compte_credit == '89':
            solde_89_apres_credit += e.montant

    solde_89_apres = solde_89_apres_debit - solde_89_apres_credit

    print(f"\nCompte 89 APRÈS patch :")
    print(f"  Débit  : {solde_89_apres_debit:>15,.2f} €")
    print(f"  Crédit : {solde_89_apres_credit:>15,.2f} €")
    print(f"  Solde  : {solde_89_apres:>15,.2f} €")

    if abs(solde_89_apres) < Decimal('0.01'):
        print("\n✅ SUCCÈS : Compte 89 maintenant équilibré !")
    else:
        print(f"\n⚠️  ATTENTION : Compte 89 toujours déséquilibré de {solde_89_apres:,.2f}€")

except Exception as e:
    session.rollback()
    print(f"\n❌ ERREUR lors de l'application du patch : {e}")
    import traceback
    traceback.print_exc()
    session.close()
    exit(1)

print("\n" + "="*100)
print("PATCH TERMINÉ")
print("="*100 + "\n")

session.close()
