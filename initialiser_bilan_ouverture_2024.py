#!/usr/bin/env python3
"""
Initialisation du bilan d'ouverture 2024
À partir du bilan de clôture 2023
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models_module2 import get_session, EcritureComptable, PlanCompte, ExerciceComptable
from decimal import Decimal
from datetime import date

DATABASE_URL = os.getenv('DATABASE_URL')
session = get_session(DATABASE_URL)

print("="*80)
print("🔧 INITIALISATION BILAN D'OUVERTURE 2024")
print("="*80)

# Récupérer les exercices
exercice_2023 = session.query(ExerciceComptable).filter_by(annee=2023).first()
exercice_2024 = session.query(ExerciceComptable).filter_by(annee=2024).first()

if not exercice_2023 or not exercice_2024:
    print("❌ Exercice 2023 ou 2024 non trouvé")
    sys.exit(1)

print(f"\n📅 Exercice 2023 : ID={exercice_2023.id}, Statut={exercice_2023.statut}")
print(f"📅 Exercice 2024 : ID={exercice_2024.id}, Statut={exercice_2024.statut}")

# Vérifier s'il y a déjà des écritures d'ouverture 2024
ecritures_init_existantes = session.query(EcritureComptable).filter_by(
    exercice_id=exercice_2024.id,
    type_ecriture='INIT_BILAN_2023'
).count()

if ecritures_init_existantes > 0:
    print(f"\n⚠️  Il existe déjà {ecritures_init_existantes} écritures d'ouverture 2024")
    reponse = input("Voulez-vous les SUPPRIMER et recréer le bilan d'ouverture ? (OUI/non) : ")
    if reponse.upper() != 'OUI':
        print("\n❌ Opération annulée")
        sys.exit(0)

    # Supprimer les anciennes écritures d'ouverture
    session.query(EcritureComptable).filter_by(
        exercice_id=exercice_2024.id,
        type_ecriture='INIT_BILAN_2023'
    ).delete()
    session.commit()
    print(f"✅ {ecritures_init_existantes} écritures d'ouverture supprimées")

# Calculer le bilan de clôture 2023
print("\n" + "="*80)
print("📊 CALCUL BILAN CLÔTURE 2023")
print("="*80)

ecritures_2023 = session.query(EcritureComptable).filter_by(exercice_id=exercice_2023.id).all()
print(f"\nÉcritures 2023 : {len(ecritures_2023)}")

from collections import defaultdict

soldes_2023 = defaultdict(lambda: {'debit': Decimal('0'), 'credit': Decimal('0')})

for e in ecritures_2023:
    soldes_2023[e.compte_debit]['debit'] += Decimal(str(e.montant))
    soldes_2023[e.compte_credit]['credit'] += Decimal(str(e.montant))

# Calculer soldes nets
for num_compte in soldes_2023:
    compte = session.query(PlanCompte).filter_by(numero_compte=num_compte).first()
    if compte:
        soldes_2023[num_compte]['libelle'] = compte.libelle
        soldes_2023[num_compte]['type'] = compte.type_compte
    soldes_2023[num_compte]['solde'] = soldes_2023[num_compte]['debit'] - soldes_2023[num_compte]['credit']

# Séparer ACTIF et PASSIF (classes 1-5 uniquement, pas 6-7)
actif_2023 = {}
passif_2023 = {}

for num_compte, data in soldes_2023.items():
    classe = int(num_compte[0])
    if classe in [1, 2, 3, 4, 5]:  # Bilan uniquement
        solde = data['solde']
        if solde > Decimal('0.01'):
            actif_2023[num_compte] = data
        elif solde < Decimal('-0.01'):
            passif_2023[num_compte] = data

print(f"\nACTIF 2023 : {len(actif_2023)} comptes")
total_actif_2023 = sum(d['solde'] for d in actif_2023.values())
for num, data in sorted(actif_2023.items()):
    print(f"  {num} : {data['solde']:>14.2f}€ ({data.get('libelle', '?')})")
print(f"  TOTAL : {total_actif_2023:>14.2f}€")

print(f"\nPASSIF 2023 : {len(passif_2023)} comptes")
total_passif_2023 = sum(abs(d['solde']) for d in passif_2023.values())
for num, data in sorted(passif_2023.items()):
    print(f"  {num} : {abs(data['solde']):>14.2f}€ ({data.get('libelle', '?')})")
print(f"  TOTAL : {total_passif_2023:>14.2f}€")

ecart_2023 = total_actif_2023 - total_passif_2023
print(f"\nÉcart : {ecart_2023:.2f}€")

if abs(ecart_2023) > 0.01:
    print("⚠️  Bilan 2023 non équilibré !")
else:
    print("✅ Bilan 2023 équilibré")

# Créer les écritures d'ouverture 2024
print("\n" + "="*80)
print("🔧 CRÉATION ÉCRITURES D'OUVERTURE 2024")
print("="*80)

print("\nCréation des écritures avec compte 89 (Bilan d'ouverture) comme contrepartie")

ecritures_creees = []
date_ouverture = date(2024, 1, 1)

# ACTIF : Soldes débiteurs → Débit compte / Crédit 89
for i, (num_compte, data) in enumerate(sorted(actif_2023.items()), 1):
    montant = data['solde']
    libelle = data.get('libelle', f'Compte {num_compte}')

    e = EcritureComptable(
        exercice_id=exercice_2024.id,
        numero_ecriture=f"INIT-2024-{i:03d}",
        date_ecriture=date_ouverture,
        libelle_ecriture=f"Bilan ouverture 2024 - {libelle}",
        compte_debit=num_compte,
        compte_credit='89',
        montant=float(montant),
        type_ecriture='INIT_BILAN_2023'
    )
    session.add(e)
    ecritures_creees.append(e)
    print(f"  ✅ ACTIF {num_compte} : Débit {num_compte} / Crédit 89 : {montant:.2f}€")

# PASSIF : Soldes créditeurs → Débit 89 / Crédit compte
for i, (num_compte, data) in enumerate(sorted(passif_2023.items()), len(actif_2023) + 1):
    montant = abs(data['solde'])
    libelle = data.get('libelle', f'Compte {num_compte}')

    e = EcritureComptable(
        exercice_id=exercice_2024.id,
        numero_ecriture=f"INIT-2024-{i:03d}",
        date_ecriture=date_ouverture,
        libelle_ecriture=f"Bilan ouverture 2024 - {libelle}",
        compte_debit='89',
        compte_credit=num_compte,
        montant=float(montant),
        type_ecriture='INIT_BILAN_2023'
    )
    session.add(e)
    ecritures_creees.append(e)
    print(f"  ✅ PASSIF {num_compte} : Débit 89 / Crédit {num_compte} : {montant:.2f}€")

print(f"\n📊 Total écritures créées : {len(ecritures_creees)}")

# Vérifier que le compte 89 s'équilibre
total_debit_89 = sum(float(data['solde']) for data in passif_2023.values() if data['solde'] < 0)
total_credit_89 = sum(float(data['solde']) for data in actif_2023.values() if data['solde'] > 0)

print(f"\nVérification compte 89 :")
print(f"  Débit 89  : {abs(total_debit_89):.2f}€")
print(f"  Crédit 89 : {total_credit_89:.2f}€")
print(f"  Solde 89  : {total_credit_89 + total_debit_89:.2f}€")

if abs(total_credit_89 + total_debit_89) < 0.01:
    print("  ✅ Compte 89 équilibré")
else:
    print("  ⚠️  Compte 89 non équilibré !")

# Demander confirmation
print("\n" + "="*80)
print("⚠️  CONFIRMATION REQUISE")
print("="*80)
print(f"""
Cette opération va créer {len(ecritures_creees)} écritures d'ouverture 2024.

Bilan d'ouverture 2024 :
  ACTIF  : {total_actif_2023:.2f}€
  PASSIF : {total_passif_2023:.2f}€

Êtes-vous sûr de vouloir continuer ?
""")

reponse = input("Tapez 'OUI' pour confirmer : ")
if reponse.upper() != 'OUI':
    print("\n❌ Opération annulée (rollback)")
    session.rollback()
    session.close()
    sys.exit(0)

# Commit
print("\n⚠️  Commit en cours...")
try:
    session.commit()
    print("✅ Commit réussi")
except Exception as ex:
    print(f"❌ Erreur lors du commit : {ex}")
    session.rollback()
    session.close()
    sys.exit(1)

# Vérification
nb_ecritures_init = session.query(EcritureComptable).filter_by(
    exercice_id=exercice_2024.id,
    type_ecriture='INIT_BILAN_2023'
).count()

print("\n" + "="*80)
print("✅ INITIALISATION TERMINÉE")
print("="*80)
print(f"""
Écritures d'ouverture 2024 : {nb_ecritures_init}
Bilan d'ouverture 2024 :
  ACTIF  : {total_actif_2023:.2f}€
  PASSIF : {total_passif_2023:.2f}€

Prochaine étape :
  python construire_etats_financiers_2024.py

  Le bilan 2024 devrait maintenant être équilibré.
""")

session.close()
