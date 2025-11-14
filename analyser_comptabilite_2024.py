#!/usr/bin/env python3
"""
Script d'analyse de la comptabilité 2024
Vérifie :
1. Problème remises LCL (PRODUIT vs CHARGE)
2. Répartition par type de compte (Actif/Passif/Produits/Charges)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models_module2 import get_session, EcritureComptable, PlanCompte, ExerciceComptable
from collections import defaultdict

DATABASE_URL = os.getenv('DATABASE_URL')
session = get_session(DATABASE_URL)

print("="*80)
print("🔍 ANALYSE COMPTABILITÉ 2024")
print("="*80)

# Récupérer l'exercice 2024
exercice_2024 = session.query(ExerciceComptable).filter_by(annee=2024).first()
if not exercice_2024:
    print("❌ Exercice 2024 non trouvé")
    sys.exit(1)

ecritures_2024 = session.query(EcritureComptable).filter_by(exercice_id=exercice_2024.id).all()

print(f"\n📊 Total écritures 2024 : {len(ecritures_2024)}")
print(f"   Période : {exercice_2024.date_debut} → {exercice_2024.date_fin}")
print(f"   Statut : {exercice_2024.statut}")

# ==============================================================================
# PARTIE 1 : ANALYSE FRAIS_BANCAIRES
# ==============================================================================
print("\n" + "="*80)
print("📌 PARTIE 1 : ANALYSE FRAIS_BANCAIRES")
print("="*80)

fb = [e for e in ecritures_2024 if e.type_ecriture == 'FRAIS_BANCAIRES']
print(f"\nTotal FRAIS_BANCAIRES : {len(fb)} écritures\n")

# Grouper par pattern de libellé
groupes_fb = defaultdict(list)
for e in fb:
    lib = e.libelle_ecriture.upper()
    if 'REMISE' in lib:
        pattern = 'REMISE LCL'
    elif 'ABON' in lib or 'ACCESS' in lib:
        pattern = 'ABONNEMENT LCL ACCESS'
    elif 'COTISATION' in lib:
        pattern = 'COTISATION PRO'
    else:
        pattern = 'AUTRE'
    groupes_fb[pattern].append(e)

# Afficher chaque groupe
for pattern, ecritures in sorted(groupes_fb.items()):
    print(f"\n{'-'*80}")
    print(f"📍 {pattern} : {len(ecritures)} écriture(s)")
    print(f"{'-'*80}")

    # Analyser premier exemple
    e = ecritures[0]
    cpte_d = session.query(PlanCompte).filter_by(numero_compte=e.compte_debit).first()
    cpte_c = session.query(PlanCompte).filter_by(numero_compte=e.compte_credit).first()

    print(f"Exemple :")
    print(f"  Date : {e.date_ecriture}")
    print(f"  Libellé : {e.libelle_ecriture[:70]}")
    print(f"  Montant : {e.montant}€")
    print(f"  Écriture : {e.compte_debit} ({cpte_d.libelle if cpte_d else '?'}) → "
          f"{e.compte_credit} ({cpte_c.libelle if cpte_c else '?'})")

    if cpte_d and cpte_c:
        print(f"  Type débit : {cpte_d.type_compte}")
        print(f"  Type crédit : {cpte_c.type_compte}")

    # Statistiques
    montants = [e.montant for e in ecritures]
    print(f"  Montants : min={min(montants):.2f}€, max={max(montants):.2f}€, "
          f"total={sum(montants):.2f}€")

# Diagnostic remises LCL
print("\n" + "="*80)
print("🎯 DIAGNOSTIC REMISES LCL")
print("="*80)

remises = groupes_fb.get('REMISE LCL', [])
if remises:
    print(f"\n⚠️  REMISES LCL détectées : {len(remises)} écritures")

    # Vérifier comptabilisation
    e_exemple = remises[0]
    cpte_d = session.query(PlanCompte).filter_by(numero_compte=e_exemple.compte_debit).first()

    print(f"\nComptabilisation actuelle :")
    print(f"  Compte débit : {e_exemple.compte_debit}")
    if cpte_d:
        print(f"  Type : {cpte_d.type_compte}")
        print(f"  Libellé : {cpte_d.libelle}")

    print(f"  Montant : {e_exemple.montant}€ ({"POSITIF" if e_exemple.montant > 0 else "NÉGATIF"})")

    # Diagnostic
    if cpte_d and cpte_d.type_compte == 'CHARGE' and e_exemple.montant > 0:
        print(f"\n❌ PROBLÈME CONFIRMÉ :")
        print(f"   Les remises LCL sont comptabilisées en CHARGE (compte {e_exemple.compte_debit})")
        print(f"   avec un montant POSITIF")
        print(f"\n✅ CORRECTION NÉCESSAIRE :")
        print(f"   Option 1 : Passer en PRODUIT (compte 7xx) avec montant positif")
        print(f"   Option 2 : Garder en CHARGE (627) mais avec montant NÉGATIF")
        print(f"\n   Recommandation : Option 2 (plus simple, pas de reclassement)")
    else:
        print(f"\n✅ Comptabilisation correcte")
else:
    print("\nℹ️  Aucune remise LCL détectée")

# ==============================================================================
# PARTIE 2 : RÉPARTITION PAR TYPE DE COMPTE
# ==============================================================================
print("\n\n" + "="*80)
print("📌 PARTIE 2 : RÉPARTITION PAR TYPE DE COMPTE")
print("="*80)

# Récupérer tous les comptes utilisés
comptes_utilises = set()
for e in ecritures_2024:
    comptes_utilises.add(e.compte_debit)
    comptes_utilises.add(e.compte_credit)

# Grouper par type
repartition = defaultdict(lambda: {'comptes': set(), 'ecritures_debit': 0, 'ecritures_credit': 0, 'montant_total': 0})

for e in ecritures_2024:
    # Compte débit
    cpte_d = session.query(PlanCompte).filter_by(numero_compte=e.compte_debit).first()
    if cpte_d:
        repartition[cpte_d.type_compte]['comptes'].add(e.compte_debit)
        repartition[cpte_d.type_compte]['ecritures_debit'] += 1
        repartition[cpte_d.type_compte]['montant_total'] += e.montant

    # Compte crédit
    cpte_c = session.query(PlanCompte).filter_by(numero_compte=e.compte_credit).first()
    if cpte_c:
        repartition[cpte_c.type_compte]['comptes'].add(e.compte_credit)
        repartition[cpte_c.type_compte]['ecritures_credit'] += 1
        repartition[cpte_c.type_compte]['montant_total'] -= e.montant  # Crédit = négatif

print(f"\n{'Type Compte':<20} {'Comptes':<10} {'Débits':<10} {'Crédits':<10} {'Montant Total':<15}")
print("-"*80)

for type_compte in ['ACTIF', 'PASSIF', 'CHARGE', 'PRODUIT']:
    if type_compte in repartition:
        r = repartition[type_compte]
        print(f"{type_compte:<20} {len(r['comptes']):<10} {r['ecritures_debit']:<10} "
              f"{r['ecritures_credit']:<10} {r['montant_total']:>14.2f}€")

# Diagnostic
print("\n" + "="*80)
print("🎯 DIAGNOSTIC RÉPARTITION")
print("="*80)

types_manquants = []
for type_attendu in ['ACTIF', 'PASSIF', 'CHARGE', 'PRODUIT']:
    if type_attendu not in repartition or repartition[type_attendu]['ecritures_debit'] + repartition[type_attendu]['ecritures_credit'] == 0:
        types_manquants.append(type_attendu)

if types_manquants:
    print(f"\n⚠️  Types de comptes PAS ou PEU utilisés : {', '.join(types_manquants)}")

    if 'PRODUIT' in types_manquants:
        print(f"\n❌ ALERTE : Aucun compte de PRODUIT utilisé !")
        print(f"   Les revenus (SCPI, distributions, etc.) sont-ils comptabilisés ?")
else:
    print(f"\n✅ Tous les types de comptes sont utilisés (ACTIF, PASSIF, CHARGE, PRODUIT)")

# ==============================================================================
# PARTIE 3 : DÉTAIL PAR TYPE D'ÉCRITURE
# ==============================================================================
print("\n\n" + "="*80)
print("📌 PARTIE 3 : DÉTAIL PAR TYPE D'ÉCRITURE")
print("="*80)

types_ecritures = defaultdict(int)
for e in ecritures_2024:
    types_ecritures[e.type_ecriture or 'NULL'] += 1

print(f"\n{'Type Écriture':<30} {'Nombre':<10}")
print("-"*80)
for type_e, count in sorted(types_ecritures.items(), key=lambda x: -x[1]):
    print(f"{type_e:<30} {count:<10}")

# ==============================================================================
# CONCLUSION
# ==============================================================================
print("\n\n" + "="*80)
print("✅ SYNTHÈSE ET RECOMMANDATIONS")
print("="*80)

print("\n1️⃣  FRAIS_BANCAIRES / REMISES LCL :")
if remises and cpte_d and cpte_d.type_compte == 'CHARGE':
    print("   ❌ À corriger : Remises comptabilisées en CHARGE avec montant positif")
    print("   → Inverser le signe (montant négatif) OU reclasser en PRODUIT")
else:
    print("   ✅ OK ou non applicable")

print("\n2️⃣  RÉPARTITION PAR TYPE DE COMPTE :")
if types_manquants:
    print(f"   ⚠️  Types manquants : {', '.join(types_manquants)}")
    print("   → Vérifier que toutes les opérations sont bien enregistrées")
else:
    print("   ✅ Tous les types de comptes utilisés")

print("\n3️⃣  PROCHAINES ÉTAPES :")
print("   1. Corriger problème remises LCL (si applicable)")
print("   2. Construire bilan 2024")
print("   3. Construire compte d'exploitation 2024")
print("   4. Comparer avec documents officiels")
print("   5. Clôturer exercice 2024")
print("   6. Développer module gestion portefeuille VM")

print("\n" + "="*80)

session.close()
