#!/usr/bin/env python3
"""
Construction des états financiers 2024
- Bilan 2024 (Actif / Passif)
- Compte d'exploitation 2024 (Produits / Charges)
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

ecritures_2024 = session.query(EcritureComptable).filter_by(exercice_id=exercice_2024.id).all()

print(f"\n📝 Écritures 2024 : {len(ecritures_2024)}")
print(f"   Période : {exercice_2024.date_debut} → {exercice_2024.date_fin}")

# ==============================================================================
# CALCUL DES SOLDES PAR COMPTE
# ==============================================================================

# Dictionnaire : numero_compte -> {'debit': Decimal, 'credit': Decimal, 'libelle': str, 'type': str}
soldes = defaultdict(lambda: {'debit': Decimal('0'), 'credit': Decimal('0'), 'libelle': '', 'type': ''})

for e in ecritures_2024:
    montant = Decimal(str(e.montant))

    # Compte débit
    soldes[e.compte_debit]['debit'] += montant
    cpte_d = session.query(PlanCompte).filter_by(numero_compte=e.compte_debit).first()
    if cpte_d:
        soldes[e.compte_debit]['libelle'] = cpte_d.libelle
        soldes[e.compte_debit]['type'] = cpte_d.type_compte

    # Compte crédit
    soldes[e.compte_credit]['credit'] += montant
    cpte_c = session.query(PlanCompte).filter_by(numero_compte=e.compte_credit).first()
    if cpte_c:
        soldes[e.compte_credit]['libelle'] = cpte_c.libelle
        soldes[e.compte_credit]['type'] = cpte_c.type_compte

# Calculer les soldes nets
for num_compte, data in soldes.items():
    data['solde'] = data['debit'] - data['credit']

# ==============================================================================
# PARTIE 1 : BILAN 2024
# ==============================================================================

print("\n" + "="*80)
print("📋 BILAN AU 31/12/2024")
print("="*80)

# Regrouper par type de compte
actif = {}
passif = {}

for num_compte, data in soldes.items():
    type_compte = data['type']
    solde = data['solde']

    # Classe du compte (premier chiffre)
    classe = int(num_compte[0]) if num_compte and num_compte[0].isdigit() else 0

    # Classification bilan :
    # ACTIF = classes 1-5 avec solde débiteur (positif)
    # PASSIF = classes 1-5 avec solde créditeur (négatif)
    # Exception : 512 (Banque) est un compte financier qui peut être à l'actif ou au passif

    if classe in [1, 2, 3, 4, 5]:
        if type_compte == 'ACTIF' or (type_compte == 'FINANCIERS' and solde > 0):
            actif[num_compte] = data
        elif type_compte == 'PASSIF' or (type_compte == 'FINANCIERS' and solde < 0):
            passif[num_compte] = data

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

total_passif = Decimal('0')
for num_compte in sorted(passif.keys()):
    data = passif[num_compte]
    montant = abs(data['solde'])  # Passif = valeur absolue (créditeur)
    total_passif += montant
    print(f"{num_compte:<10} {data['libelle'][:40]:<40} {montant:>14.2f}€")

print("-"*80)
print(f"{'TOTAL PASSIF':<50} {total_passif:>14.2f}€")
print("="*80)

# Vérification équilibre bilan
print("\n🎯 VÉRIFICATION ÉQUILIBRE BILAN")
print("-"*80)
print(f"Total ACTIF  : {total_actif:>14.2f}€")
print(f"Total PASSIF : {total_passif:>14.2f}€")
print(f"Écart        : {abs(total_actif - total_passif):>14.2f}€")

if abs(total_actif - total_passif) < Decimal('0.01'):
    print("✅ Bilan équilibré")
else:
    print(f"⚠️  Bilan non équilibré (écart : {total_actif - total_passif:.2f}€)")
    print("   Note : Le résultat de l'exercice doit être inscrit au passif pour équilibrer")

# ==============================================================================
# PARTIE 2 : COMPTE D'EXPLOITATION 2024
# ==============================================================================

print("\n\n" + "="*80)
print("📊 COMPTE D'EXPLOITATION 2024")
print("="*80)

# Regrouper par type
charges = {}
produits = {}

for num_compte, data in soldes.items():
    classe = int(num_compte[0]) if num_compte and num_compte[0].isdigit() else 0

    # CHARGES = classe 6
    # PRODUITS = classe 7

    if classe == 6:
        charges[num_compte] = data
    elif classe == 7:
        produits[num_compte] = data

# Afficher CHARGES
print("\n" + "-"*80)
print("CHARGES")
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
print("PRODUITS")
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

print("\n🎯 RÉSULTAT DE L'EXERCICE 2024")
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
# PARTIE 3 : EXPORT JSON (optionnel)
# ==============================================================================

print("\n\n" + "="*80)
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
        "total_actif": float(total_actif),
        "total_passif": float(total_passif)
    },
    "compte_exploitation": {
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
    }
}

# Sauvegarder dans un fichier
output_file = f"etats_financiers_2024_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(export, f, indent=2, ensure_ascii=False)

print(f"\n✅ Export JSON sauvegardé : {output_file}")
print(f"   → Utiliser ce fichier pour comparer avec documents officiels")

# ==============================================================================
# SYNTHÈSE
# ==============================================================================

print("\n\n" + "="*80)
print("✅ SYNTHÈSE")
print("="*80)

print(f"""
📋 BILAN 2024
   ACTIF  : {total_actif:>14.2f}€
   PASSIF : {total_passif:>14.2f}€
   Équilibré : {"✅ OUI" if abs(total_actif - total_passif) < 0.01 else "❌ NON"}

📊 COMPTE D'EXPLOITATION 2024
   PRODUITS : {total_produits:>14.2f}€
   CHARGES  : {total_charges:>14.2f}€
   RÉSULTAT : {resultat:>14.2f}€ {"(BÉNÉFICE ✅)" if resultat >= 0 else "(PERTE ❌)"}

📁 Export JSON : {output_file}

🎯 PROCHAINES ÉTAPES :
   1. Comparer avec documents comptables officiels
   2. Si OK → Clôturer exercice 2024
   3. Développer module gestion portefeuille VM
""")

print("="*80)

session.close()
