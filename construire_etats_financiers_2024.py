#!/usr/bin/env python3
"""
Construction des états financiers 2024
- Bilan 2024 (Actif / Passif)
- Compte d'exploitation 2024 (Produits / Charges)

MÉTHODE COMPTABLE CORRECTE :
1. Calculer soldes finaux de TOUS les comptes (ouverture + flux)
2. Séparer bilan (classes 1-5) et résultat (classes 6-7)
3. Inscrire le résultat au passif
4. Vérifier équilibre ACTIF = PASSIF
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models_module2 import get_session, EcritureComptable, PlanCompte, ExerciceComptable
from collections import defaultdict
from decimal import Decimal

DATABASE_URL = os.getenv('DATABASE_URL')
session = get_session(DATABASE_URL)

print("="*80)
print("📊 CONSTRUCTION ÉTATS FINANCIERS 2024")
print("="*80)

# Récupérer l'exercice 2024
exercice_2024 = session.query(ExerciceComptable).filter_by(annee=2024).first()
if not exercice_2024:
    print("❌ Exercice 2024 non trouvé")
    sys.exit(1)

# TOUTES les écritures 2024 (ouverture + flux)
ecritures_2024 = session.query(EcritureComptable).filter_by(exercice_id=exercice_2024.id).all()

print(f"\n📝 Écritures 2024 : {len(ecritures_2024)}")
print(f"   Dont écritures d'ouverture : {sum(1 for e in ecritures_2024 if e.type_ecriture == 'INIT_BILAN_2023')}")
print(f"   Dont flux de l'année : {sum(1 for e in ecritures_2024 if e.type_ecriture != 'INIT_BILAN_2023')}")
print(f"   Période : {exercice_2024.date_debut} → {exercice_2024.date_fin}")

# ==============================================================================
# ÉTAPE 1 : CALCUL DES SOLDES FINAUX PAR COMPTE
# ==============================================================================

print("\n" + "="*80)
print("ÉTAPE 1 : CALCUL DES SOLDES FINAUX")
print("="*80)

# Dictionnaire : numero_compte -> {'debit': Decimal, 'credit': Decimal, 'libelle': str, 'type': str, 'classe': int}
soldes = defaultdict(lambda: {
    'debit': Decimal('0'),
    'credit': Decimal('0'),
    'libelle': '',
    'type': '',
    'classe': 0
})

for e in ecritures_2024:
    montant = Decimal(str(e.montant))

    # Compte débit
    soldes[e.compte_debit]['debit'] += montant
    cpte_d = session.query(PlanCompte).filter_by(numero_compte=e.compte_debit).first()
    if cpte_d:
        soldes[e.compte_debit]['libelle'] = cpte_d.libelle
        soldes[e.compte_debit]['type'] = cpte_d.type_compte
        if e.compte_debit and e.compte_debit[0].isdigit():
            soldes[e.compte_debit]['classe'] = int(e.compte_debit[0])

    # Compte crédit
    soldes[e.compte_credit]['credit'] += montant
    cpte_c = session.query(PlanCompte).filter_by(numero_compte=e.compte_credit).first()
    if cpte_c:
        soldes[e.compte_credit]['libelle'] = cpte_c.libelle
        soldes[e.compte_credit]['type'] = cpte_c.type_compte
        if e.compte_credit and e.compte_credit[0].isdigit():
            soldes[e.compte_credit]['classe'] = int(e.compte_credit[0])

# Calculer les soldes nets
for num_compte, data in soldes.items():
    data['solde'] = data['debit'] - data['credit']

print(f"\nNombre de comptes mouvementés : {len(soldes)}")

# Vérifier le compte 89 (doit être à 0)
if '89' in soldes:
    solde_89 = soldes['89']['solde']
    print(f"Vérification compte 89 (Bilan d'ouverture) : {solde_89:.2f}€")
    if abs(solde_89) < Decimal('0.01'):
        print("   ✅ Compte 89 équilibré")
    else:
        print(f"   ⚠️  Compte 89 non équilibré (écart : {solde_89:.2f}€)")

# ==============================================================================
# ÉTAPE 2 : COMPTE DE RÉSULTAT 2024
# ==============================================================================

print("\n" + "="*80)
print("ÉTAPE 2 : COMPTE DE RÉSULTAT 2024")
print("="*80)

charges = {}
produits = {}

for num_compte, data in soldes.items():
    classe = data['classe']

    # Ignorer compte 89 (bilan d'ouverture)
    if num_compte == '89':
        continue

    # CHARGES = classe 6
    if classe == 6:
        charges[num_compte] = data
    # PRODUITS = classe 7
    elif classe == 7:
        produits[num_compte] = data

# Afficher CHARGES
print("\n" + "-"*80)
print("CHARGES (Classe 6)")
print("-"*80)
print(f"{'Compte':<10} {'Libellé':<40} {'Montant':>15}")
print("-"*80)

total_charges = Decimal('0')
for num_compte in sorted(charges.keys()):
    data = charges[num_compte]
    montant = data['debit']  # Charges = débit
    total_charges += montant
    print(f"{num_compte:<10} {data['libelle'][:40]:<40} {montant:>14.2f}€")

print("-"*80)
print(f"{'TOTAL CHARGES':<50} {total_charges:>14.2f}€")
print("="*80)

# Afficher PRODUITS
print("\n" + "-"*80)
print("PRODUITS (Classe 7)")
print("-"*80)
print(f"{'Compte':<10} {'Libellé':<40} {'Montant':>15}")
print("-"*80)

total_produits = Decimal('0')
for num_compte in sorted(produits.keys()):
    data = produits[num_compte]
    montant = data['credit']  # Produits = crédit
    total_produits += montant
    print(f"{num_compte:<10} {data['libelle'][:40]:<40} {montant:>14.2f}€")

print("-"*80)
print(f"{'TOTAL PRODUITS':<50} {total_produits:>14.2f}€")
print("="*80)

# Calcul résultat
resultat = total_produits - total_charges

print("\n🎯 RÉSULTAT DE L'EXERCICE 2024 (AVANT IMPÔT)")
print("-"*80)
print(f"Total PRODUITS : {total_produits:>14.2f}€")
print(f"Total CHARGES  : {total_charges:>14.2f}€")
print("-"*80)
if resultat >= 0:
    print(f"BÉNÉFICE       : {resultat:>14.2f}€ ✅")
else:
    print(f"PERTE          : {abs(resultat):>14.2f}€ ❌")
print("="*80)

# ==============================================================================
# ÉTAPE 3 : BILAN AU 31/12/2024
# ==============================================================================

print("\n" + "="*80)
print("ÉTAPE 3 : BILAN AU 31/12/2024")
print("="*80)

actif = {}
passif = {}

for num_compte, data in soldes.items():
    classe = data['classe']
    solde = data['solde']

    # Ignorer compte 89 (bilan d'ouverture, déjà soldé)
    if num_compte == '89':
        continue

    # Ignorer classes 6 et 7 (comptes de gestion, dans le résultat)
    if classe in [6, 7]:
        continue

    # Classes 1-5 = BILAN
    if classe in [1, 2, 3, 4, 5]:
        # Solde DÉBITEUR → ACTIF
        if solde > Decimal('0.01'):
            actif[num_compte] = data
        # Solde CRÉDITEUR → PASSIF
        elif solde < Decimal('-0.01'):
            passif[num_compte] = data
        # Solde ~ 0 : ignorer

# Afficher ACTIF
print("\n" + "-"*80)
print("ACTIF")
print("-"*80)
print(f"{'Compte':<10} {'Libellé':<40} {'Montant':>15}")
print("-"*80)

total_actif = Decimal('0')
for num_compte in sorted(actif.keys()):
    data = actif[num_compte]
    montant = data['solde']
    total_actif += montant
    print(f"{num_compte:<10} {data['libelle'][:40]:<40} {montant:>14.2f}€")

print("-"*80)
print(f"{'TOTAL ACTIF':<50} {total_actif:>14.2f}€")
print("="*80)

# Afficher PASSIF
print("\n" + "-"*80)
print("PASSIF")
print("-"*80)
print(f"{'Compte':<10} {'Libellé':<40} {'Montant':>15}")
print("-"*80)

total_passif_avant_resultat = Decimal('0')
for num_compte in sorted(passif.keys()):
    data = passif[num_compte]
    montant = abs(data['solde'])  # Passif = valeur absolue (créditeur)
    total_passif_avant_resultat += montant
    print(f"{num_compte:<10} {data['libelle'][:40]:<40} {montant:>14.2f}€")

# AJOUTER LE RÉSULTAT AU PASSIF (ou à l'actif si perte)
print("-"*80)
if resultat >= 0:
    print(f"{'12X':<10} {'Résultat de exercice 2024 (bénéfice)':<40} {resultat:>14.2f}€")
    total_passif_final = total_passif_avant_resultat + resultat
else:
    # Si perte, le résultat irait à l'actif (en comptabilité, on ne met généralement pas le résultat négatif au passif)
    print(f"{'12X':<10} {'Résultat de exercice 2024 (perte)':<40} {abs(resultat):>14.2f}€")
    print("   ⚠️  En cas de perte, à inscrire à l'ACTIF")
    total_passif_final = total_passif_avant_resultat

print("-"*80)
print(f"{'TOTAL PASSIF':<50} {total_passif_final:>14.2f}€")
print("="*80)

# ==============================================================================
# ÉTAPE 4 : VÉRIFICATION ÉQUILIBRE BILAN
# ==============================================================================

print("\n" + "="*80)
print("ÉTAPE 4 : VÉRIFICATION ÉQUILIBRE BILAN")
print("="*80)

actif_final = total_actif
passif_final = total_passif_final

# Si perte, l'ajouter à l'actif
if resultat < 0:
    actif_final += abs(resultat)
    print(f"\nPerte ajoutée à l'ACTIF : {abs(resultat):.2f}€")

ecart = actif_final - passif_final

print(f"\nTotal ACTIF  : {actif_final:>14.2f}€")
print(f"Total PASSIF : {passif_final:>14.2f}€")
print("-"*80)
print(f"Écart        : {ecart:>14.2f}€")

if abs(ecart) < Decimal('0.01'):
    print("\n✅ BILAN ÉQUILIBRÉ")
else:
    print(f"\n⚠️  BILAN NON ÉQUILIBRÉ (écart : {ecart:.2f}€)")
    print("\nDiagnostic possible :")
    print("- Vérifier que toutes les écritures d'ouverture sont présentes")
    print("- Vérifier la cohérence du bilan d'ouverture")

# ==============================================================================
# EXPORT JSON
# ==============================================================================

print("\n" + "="*80)
print("💾 EXPORT JSON")
print("="*80)

import json
from datetime import datetime

export = {
    "date_generation": datetime.now().isoformat(),
    "exercice": {
        "annee": 2024,
        "date_debut": str(exercice_2024.date_debut),
        "date_fin": str(exercice_2024.date_fin),
        "statut": exercice_2024.statut
    },
    "compte_resultat": {
        "charges": {
            num: {
                "libelle": data['libelle'],
                "montant": float(data['debit'])
            }
            for num, data in charges.items()
        },
        "produits": {
            num: {
                "libelle": data['libelle'],
                "montant": float(data['credit'])
            }
            for num, data in produits.items()
        },
        "total_charges": float(total_charges),
        "total_produits": float(total_produits),
        "resultat": float(resultat)
    },
    "bilan": {
        "actif": {
            num: {
                "libelle": data['libelle'],
                "montant": float(data['solde'])
            }
            for num, data in actif.items()
        },
        "passif": {
            num: {
                "libelle": data['libelle'],
                "montant": float(abs(data['solde']))
            }
            for num, data in passif.items()
        },
        "resultat_exercice": float(resultat),
        "total_actif": float(actif_final),
        "total_passif": float(passif_final),
        "equilibre": abs(ecart) < 0.01
    }
}

output_file = f"etats_financiers_2024_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(export, f, indent=2, ensure_ascii=False)

print(f"\n✅ Export JSON sauvegardé : {output_file}")

# ==============================================================================
# SYNTHÈSE FINALE
# ==============================================================================

print("\n" + "="*80)
print("✅ SYNTHÈSE FINALE")
print("="*80)

print(f"""
📊 COMPTE DE RÉSULTAT 2024
   PRODUITS : {total_produits:>14.2f}€
   CHARGES  : {total_charges:>14.2f}€
   ────────────────────────────────
   RÉSULTAT : {resultat:>14.2f}€ {"(BÉNÉFICE ✅)" if resultat >= 0 else "(PERTE ❌)"}
   (avant impôt sur les sociétés)

📋 BILAN AU 31/12/2024
   ACTIF  : {actif_final:>14.2f}€
   PASSIF : {passif_final:>14.2f}€
   (dont résultat : {resultat:>12.2f}€)
   ────────────────────────────────
   Équilibré : {"✅ OUI" if abs(ecart) < 0.01 else f"❌ NON (écart {ecart:.2f}€)"}

📁 Export : {output_file}

🎯 PROCHAINES ÉTAPES :
   1. Comparer avec documents comptables officiels
   2. Si écart : identifier et corriger
   3. Si OK : Provisionner impôt sur les sociétés (≈25% du bénéfice)
   4. Clôturer exercice 2024
   5. Développer module gestion portefeuille VM
""")

print("="*80)

session.close()
