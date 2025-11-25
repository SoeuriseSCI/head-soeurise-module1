#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CORRECTION BILAN 2024
=====================

1. Renommer INIT_BILAN_2023 → BILAN_OUVERTURE (10 écritures)
2. Passer exercice 2024 en statut OUVERT (après reset)
"""

import os
import sys
from models_module2 import get_session, ExerciceComptable, EcritureComptable

def corriger_type_ecritures(session):
    """Corriger le type des écritures de bilan d'ouverture"""

    print("\n" + "="*80)
    print("1️⃣ CORRECTION TYPE ÉCRITURES BILAN 2024")
    print("="*80)

    ex_2024 = session.query(ExerciceComptable).filter(
        ExerciceComptable.annee == 2024
    ).first()

    if not ex_2024:
        print("\n❌ Exercice 2024 non trouvé !")
        return False

    # Trouver écritures INIT_BILAN_2023
    ecritures_bilan = session.query(EcritureComptable).filter(
        EcritureComptable.exercice_id == ex_2024.id,
        EcritureComptable.type_ecriture == 'INIT_BILAN_2023'
    ).all()

    print(f"\n📝 Écritures INIT_BILAN_2023 trouvées : {len(ecritures_bilan)}")

    if len(ecritures_bilan) == 0:
        print("   ℹ️  Aucune écriture à corriger")
        return True

    # Afficher les écritures
    for e in ecritures_bilan:
        print(f"   • {e.numero_ecriture} - {e.libelle_ecriture}")

    # Corriger le type
    print(f"\n🔄 Correction en cours : INIT_BILAN_2023 → BILAN_OUVERTURE")

    for e in ecritures_bilan:
        e.type_ecriture = 'BILAN_OUVERTURE'

    session.commit()

    print(f"   ✅ {len(ecritures_bilan)} écritures corrigées")

    return True

def passer_exercice_ouvert(session):
    """Passer l'exercice 2024 en statut OUVERT"""

    print("\n" + "="*80)
    print("2️⃣ CHANGEMENT STATUT EXERCICE 2024")
    print("="*80)

    ex_2024 = session.query(ExerciceComptable).filter(
        ExerciceComptable.annee == 2024
    ).first()

    if not ex_2024:
        print("\n❌ Exercice 2024 non trouvé !")
        return False

    print(f"\n📅 Exercice 2024 : Statut actuel = {ex_2024.statut}")

    if ex_2024.statut == 'OUVERT':
        print("   ℹ️  Déjà en statut OUVERT")
        return True

    print(f"🔄 Changement : {ex_2024.statut} → OUVERT")

    ex_2024.statut = 'OUVERT'
    session.commit()

    print(f"   ✅ Exercice 2024 passé en OUVERT")

    return True

def main():
    print("="*80)
    print("🔧 CORRECTION BILAN 2024")
    print("="*80)

    # Vérifier DATABASE_URL
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        print("\n❌ ERREUR : DATABASE_URL non définie")
        sys.exit(1)

    session = get_session(DATABASE_URL)

    # 1. Corriger types écritures
    if not corriger_type_ecritures(session):
        print("\n❌ Erreur lors de la correction des types")
        sys.exit(1)

    # 2. Passer exercice en OUVERT
    if not passer_exercice_ouvert(session):
        print("\n❌ Erreur lors du changement de statut")
        sys.exit(1)

    # Résumé final
    print("\n" + "="*80)
    print("✅ CORRECTIONS TERMINÉES")
    print("="*80)

    ex_2024 = session.query(ExerciceComptable).filter(
        ExerciceComptable.annee == 2024
    ).first()

    ecritures_bilan = session.query(EcritureComptable).filter(
        EcritureComptable.exercice_id == ex_2024.id,
        EcritureComptable.type_ecriture == 'BILAN_OUVERTURE'
    ).all()

    print(f"\n📊 État exercice 2024 :")
    print(f"   • Statut : {ex_2024.statut}")
    print(f"   • Écritures BILAN_OUVERTURE : {len(ecritures_bilan)}")

    print("\n🎯 Prochaine étape : Exécuter reset_base_pour_test.py --confirm")
    print()

    session.close()

if __name__ == '__main__':
    main()
