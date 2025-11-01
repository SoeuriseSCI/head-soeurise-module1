#!/usr/bin/env python3
"""Script pour inspecter l'état de la base de données"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models_module2 import get_session, ExerciceComptable, PlanCompte, EcritureComptable, PretImmobilier, EcheancePret

print("=" * 80)
print("🔍 INSPECTION DE LA BASE DE DONNÉES")
print("=" * 80)
print()

session = get_session()

# Exercices comptables
print("📅 EXERCICES COMPTABLES")
print("-" * 80)
exercices = session.query(ExerciceComptable).all()
print(f"Nombre total : {len(exercices)}")
print()
for ex in exercices:
    print(f"  ID {ex.id} : Année {ex.annee} ({ex.date_debut} → {ex.date_fin})")
    print(f"           Statut: {ex.statut}, Description: {ex.description}")
    nb_ecritures = session.query(EcritureComptable).filter_by(exercice_id=ex.id).count()
    print(f"           Écritures associées: {nb_ecritures}")
    print()

# Plan comptable
print("💰 PLAN COMPTABLE")
print("-" * 80)
comptes = session.query(PlanCompte).all()
print(f"Nombre total : {len(comptes)}")
print()

# Écritures comptables
print("📝 ÉCRITURES COMPTABLES")
print("-" * 80)
ecritures = session.query(EcritureComptable).all()
print(f"Nombre total : {len(ecritures)}")
if ecritures:
    print()
    print("Détail par type :")
    types = {}
    for e in ecritures:
        t = e.type_ecriture or "NULL"
        types[t] = types.get(t, 0) + 1
    for t, count in types.items():
        print(f"  - {t}: {count} écriture(s)")
    print()
    print("Premières écritures :")
    for e in ecritures[:5]:
        print(f"  ID {e.id} : {e.numero_ecriture} - {e.libelle_ecriture[:50]}")
        print(f"           Type: {e.type_ecriture}, Date: {e.date_ecriture}")
        print()

# Prêts immobiliers
print("🏠 PRÊTS IMMOBILIERS")
print("-" * 80)
prets = session.query(PretImmobilier).all()
print(f"Nombre total : {len(prets)}")
print()

# Échéances
print("📊 ÉCHÉANCES DE PRÊTS")
print("-" * 80)
echeances = session.query(EcheancePret).all()
print(f"Nombre total : {len(echeances)}")
print()

print("=" * 80)
print("✅ INSPECTION TERMINÉE")
print("=" * 80)

session.close()
