#!/usr/bin/env python3
"""
Analyse du bilan d'ouverture 2024 et comparaison avec bilan de clôture 2023
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models_module2 import get_session, EcritureComptable, ExerciceComptable
from collections import defaultdict
from decimal import Decimal

DATABASE_URL = os.getenv('DATABASE_URL')
session = get_session(DATABASE_URL)

print("="*80)
print("🔍 ANALYSE BILAN D'OUVERTURE 2024 vs CLÔTURE 2023")
print("="*80)

# ==============================================================================
# PARTIE 1 : BILAN DE CLÔTURE 2023
# ==============================================================================

exercice_2023 = session.query(ExerciceComptable).filter_by(annee=2023).first()
if not exercice_2023:
    print("❌ Exercice 2023 non trouvé")
    sys.exit(1)

ecritures_2023 = session.query(EcritureComptable).filter_by(exercice_id=exercice_2023.id).all()

print(f"\n📅 EXERCICE 2023")
print(f"   Écritures : {len(ecritures_2023)}")
print(f"   Statut : {exercice_2023.statut}")

# Calculer soldes 2023
soldes_2023 = defaultdict(lambda: {'debit': Decimal('0'), 'credit': Decimal('0')})

for e in ecritures_2023:
    montant = Decimal(str(e.montant))
    soldes_2023[e.compte_debit]['debit'] += montant
    soldes_2023[e.compte_credit]['credit'] += montant

# Calculer soldes nets 2023
for num_compte, data in soldes_2023.items():
    data['solde'] = data['debit'] - data['credit']

print("\n" + "-"*80)
print("📋 BILAN DE CLÔTURE 2023 (depuis écritures)")
print("-"*80)

# Regrouper actif/passif
actif_2023 = {}
passif_2023 = {}

for num_compte, data in soldes_2023.items():
    if not num_compte:
        continue

    classe = int(num_compte[0]) if num_compte[0].isdigit() else 0
    solde = data['solde']

    # Bilan = classes 1-5
    if classe in [1, 2, 3, 4, 5]:
        if solde > 0:
            actif_2023[num_compte] = data
        elif solde < 0:
            passif_2023[num_compte] = data

print(f"\nACTIF 2023 :")
total_actif_2023 = Decimal('0')
for num_compte in sorted(actif_2023.keys()):
    solde = actif_2023[num_compte]['solde']
    total_actif_2023 += solde
    print(f"  {num_compte} : {solde:>14.2f}€")
print(f"  {'TOTAL':<10} : {total_actif_2023:>14.2f}€")

print(f"\nPASSIF 2023 :")
total_passif_2023 = Decimal('0')
for num_compte in sorted(passif_2023.keys()):
    solde = abs(passif_2023[num_compte]['solde'])
    total_passif_2023 += solde
    print(f"  {num_compte} : {solde:>14.2f}€")
print(f"  {'TOTAL':<10} : {total_passif_2023:>14.2f}€")

print(f"\n{'Écart bilan 2023 :':30} {abs(total_actif_2023 - total_passif_2023):>14.2f}€")

# ==============================================================================
# PARTIE 2 : BILAN D'OUVERTURE 2024
# ==============================================================================

exercice_2024 = session.query(ExerciceComptable).filter_by(annee=2024).first()
if not exercice_2024:
    print("❌ Exercice 2024 non trouvé")
    sys.exit(1)

# Écritures d'ouverture 2024 (type INIT_BILAN_2023)
ecritures_init_2024 = session.query(EcritureComptable).filter_by(
    exercice_id=exercice_2024.id,
    type_ecriture='INIT_BILAN_2023'
).all()

print("\n" + "="*80)
print(f"📅 BILAN D'OUVERTURE 2024")
print("="*80)
print(f"   Écritures d'initialisation : {len(ecritures_init_2024)}")

if not ecritures_init_2024:
    print("   ⚠️  Aucune écriture d'initialisation trouvée !")
    print("   Le bilan d'ouverture 2024 n'a pas été enregistré.")
    sys.exit(1)

# Afficher les écritures d'initialisation
print(f"\n{'Date':<12} {'Libellé':<50} {'Débit':<10} {'Crédit':<10} {'Montant':>12}")
print("-"*100)

solde_89 = Decimal('0')
for e in ecritures_init_2024:
    print(f"{str(e.date_ecriture):<12} {e.libelle_ecriture[:50]:<50} {e.compte_debit:<10} {e.compte_credit:<10} {e.montant:>11.2f}€")

    # Calculer solde compte 89 (doit être 0)
    if e.compte_debit == '89':
        solde_89 += Decimal(str(e.montant))
    if e.compte_credit == '89':
        solde_89 -= Decimal(str(e.montant))

print("-"*100)
print(f"\n🎯 Vérification compte 89 (Bilan d'ouverture) :")
print(f"   Solde compte 89 : {solde_89:.2f}€")
if abs(solde_89) < Decimal('0.01'):
    print(f"   ✅ Compte 89 équilibré")
else:
    print(f"   ❌ Compte 89 NON équilibré (écart : {solde_89:.2f}€)")

# Calculer soldes d'ouverture 2024 (hors compte 89)
soldes_ouverture_2024 = defaultdict(lambda: {'debit': Decimal('0'), 'credit': Decimal('0')})

for e in ecritures_init_2024:
    montant = Decimal(str(e.montant))

    if e.compte_debit != '89':
        soldes_ouverture_2024[e.compte_debit]['debit'] += montant

    if e.compte_credit != '89':
        soldes_ouverture_2024[e.compte_credit]['credit'] += montant

# Calculer soldes nets
for num_compte, data in soldes_ouverture_2024.items():
    data['solde'] = data['debit'] - data['credit']

print(f"\n{'Compte':<10} {'Solde Ouverture 2024':>25}")
print("-"*40)
for num_compte in sorted(soldes_ouverture_2024.keys()):
    solde = soldes_ouverture_2024[num_compte]['solde']
    print(f"{num_compte:<10} {solde:>24.2f}€")

# ==============================================================================
# PARTIE 3 : COMPARAISON
# ==============================================================================

print("\n" + "="*80)
print("🔍 COMPARAISON CLÔTURE 2023 vs OUVERTURE 2024")
print("="*80)

# Comptes présents en 2023 mais pas en 2024
print("\n⚠️  Comptes manquants à l'ouverture 2024 :")
comptes_manquants = []
for num_compte in soldes_2023.keys():
    classe = int(num_compte[0]) if num_compte and num_compte[0].isdigit() else 0

    if classe in [1, 2, 3, 4, 5] and num_compte not in soldes_ouverture_2024:
        solde_2023 = soldes_2023[num_compte]['solde']
        if abs(solde_2023) > Decimal('0.01'):  # Ignorer soldes ~ 0
            comptes_manquants.append((num_compte, solde_2023))
            print(f"  {num_compte} : {solde_2023:>14.2f}€")

if not comptes_manquants:
    print("  ✅ Aucun compte manquant")

# Comptes avec soldes différents
print("\n⚠️  Comptes avec soldes différents :")
for num_compte in set(soldes_2023.keys()) & set(soldes_ouverture_2024.keys()):
    classe = int(num_compte[0]) if num_compte and num_compte[0].isdigit() else 0

    if classe in [1, 2, 3, 4, 5]:
        solde_2023 = soldes_2023[num_compte]['solde']
        solde_2024 = soldes_ouverture_2024[num_compte]['solde']
        ecart = solde_2024 - solde_2023

        if abs(ecart) > Decimal('0.01'):
            print(f"  {num_compte} : {solde_2023:>12.2f}€ (2023) → {solde_2024:>12.2f}€ (2024) | Écart: {ecart:>12.2f}€")

# ==============================================================================
# SYNTHÈSE
# ==============================================================================

print("\n" + "="*80)
print("✅ SYNTHÈSE")
print("="*80)

print(f"""
📊 BILAN CLÔTURE 2023
   ACTIF  : {total_actif_2023:>14.2f}€
   PASSIF : {total_passif_2023:>14.2f}€

📋 BILAN OUVERTURE 2024
   Écritures d'init : {len(ecritures_init_2024)}
   Compte 89 équilibré : {"✅" if abs(solde_89) < 0.01 else "❌"}

🎯 DIAGNOSTIC
   Comptes manquants à l'ouverture : {len(comptes_manquants)}

🔧 RECOMMANDATIONS
""")

if comptes_manquants:
    print("   ❌ Le bilan d'ouverture 2024 est INCOMPLET")
    print("   → Créer les écritures d'ouverture manquantes")
    print(f"   → Comptes à ajouter : {', '.join([c[0] for c in comptes_manquants])}")
else:
    print("   ✅ Le bilan d'ouverture 2024 semble complet")
    print("   → Vérifier la cohérence avec le bilan de clôture 2023")

print("\n" + "="*80)

session.close()
