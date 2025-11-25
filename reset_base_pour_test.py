#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RESET BASE DE DONNÉES POUR TEST V8.0
=====================================

ATTENTION: Ce script supprime les données de test pour permettre
un test propre du système V8.0 restauré.

CONSERVATION:
- ✅ Exercice 2023 (CLOTURE) + écritures bilan 2023
- ✅ Exercice 2024 (OUVERT) + écritures bilan ouverture 2024 UNIQUEMENT
- ✅ Plan comptable

SUPPRESSION:
- ❌ Exercice 2025 + toutes ses écritures
- ❌ Écritures 2024 SAUF bilan d'ouverture
- ❌ Prêts immobiliers + échéances
- ❌ Propositions en attente
- ❌ Événements comptables

USAGE:
    python reset_base_pour_test.py --confirm
"""

import os
import sys
import argparse
from datetime import datetime
from models_module2 import (
    get_session, ExerciceComptable, EcritureComptable,
    PretImmobilier, EcheancePret, PropositionEnAttente
)

def sauvegarder_avant_reset(session):
    """Sauvegarde complète avant reset"""
    print("\n" + "="*80)
    print("💾 SAUVEGARDE AVANT RESET")
    print("="*80)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backups/AVANT_RESET_{timestamp}.json"

    print(f"\n🔄 Exécution sauvegarder_base.py...")
    exit_code = os.system(f"python sauvegarder_base.py")

    if exit_code != 0:
        print("\n❌ ERREUR lors de la sauvegarde !")
        return False

    print(f"\n✅ Sauvegarde créée avec succès")
    return True

def afficher_etat_actuel(session):
    """Affiche l'état actuel de la base"""
    print("\n" + "="*80)
    print("📊 ÉTAT ACTUEL DE LA BASE")
    print("="*80)

    # Exercices
    exercices = session.query(ExerciceComptable).order_by(ExerciceComptable.annee).all()
    print(f"\n📅 Exercices ({len(exercices)}):")
    for ex in exercices:
        nb_ecritures = session.query(EcritureComptable).filter(
            EcritureComptable.exercice_id == ex.id
        ).count()
        print(f"  • {ex.annee} ({ex.statut}) : {nb_ecritures} écritures")

    # Prêts
    nb_prets = session.query(PretImmobilier).count()
    nb_echeances = session.query(EcheancePret).count()
    print(f"\n💰 Prêts: {nb_prets} prêts, {nb_echeances} échéances")

    # Propositions
    nb_propositions = session.query(PropositionEnAttente).count()
    print(f"\n📋 Propositions en attente: {nb_propositions}")

def reset_base(session, dry_run=False):
    """Reset de la base pour tests propres"""

    print("\n" + "="*80)
    if dry_run:
        print("🔍 MODE DRY-RUN (simulation)")
    else:
        print("🔥 RESET RÉEL DE LA BASE")
    print("="*80)

    actions = []

    # 1. Supprimer exercice 2025 et ses écritures
    print("\n1️⃣ Suppression exercice 2025...")
    ex_2025 = session.query(ExerciceComptable).filter(
        ExerciceComptable.annee == 2025
    ).first()

    if ex_2025:
        nb_ecritures_2025 = session.query(EcritureComptable).filter(
            EcritureComptable.exercice_id == ex_2025.id
        ).count()

        print(f"   • Exercice 2025 trouvé (ID: {ex_2025.id})")
        print(f"   • {nb_ecritures_2025} écritures à supprimer")

        if not dry_run:
            session.query(EcritureComptable).filter(
                EcritureComptable.exercice_id == ex_2025.id
            ).delete()
            session.delete(ex_2025)

        actions.append(f"✅ Exercice 2025 supprimé ({nb_ecritures_2025} écritures)")
    else:
        print("   • Aucun exercice 2025 trouvé")
        actions.append("ℹ️  Pas d'exercice 2025 à supprimer")

    # 2. Garder UNIQUEMENT bilan ouverture 2024
    print("\n2️⃣ Nettoyage écritures 2024 (garde bilan ouverture)...")
    ex_2024 = session.query(ExerciceComptable).filter(
        ExerciceComptable.annee == 2024
    ).first()

    if ex_2024:
        # Compter écritures à garder (bilan ouverture)
        ecritures_bilan = session.query(EcritureComptable).filter(
            EcritureComptable.exercice_id == ex_2024.id,
            EcritureComptable.type_ecriture == 'BILAN_OUVERTURE'
        ).all()

        # Compter écritures à supprimer
        ecritures_autres = session.query(EcritureComptable).filter(
            EcritureComptable.exercice_id == ex_2024.id,
            EcritureComptable.type_ecriture != 'BILAN_OUVERTURE'
        ).all()

        print(f"   • {len(ecritures_bilan)} écritures bilan ouverture (conservées)")
        print(f"   • {len(ecritures_autres)} autres écritures (supprimées)")

        if not dry_run:
            for ecriture in ecritures_autres:
                session.delete(ecriture)

        actions.append(f"✅ Exercice 2024 nettoyé (gardé {len(ecritures_bilan)} bilan ouverture, supprimé {len(ecritures_autres)} autres)")
    else:
        print("   • Aucun exercice 2024 trouvé")
        actions.append("⚠️  Pas d'exercice 2024 trouvé !")

    # 3. Supprimer prêts et échéances
    print("\n3️⃣ Suppression prêts et échéances...")
    nb_echeances = session.query(EcheancePret).count()
    nb_prets = session.query(PretImmobilier).count()

    print(f"   • {nb_prets} prêts à supprimer")
    print(f"   • {nb_echeances} échéances à supprimer")

    if not dry_run:
        session.query(EcheancePret).delete()
        session.query(PretImmobilier).delete()

    actions.append(f"✅ Prêts supprimés ({nb_prets} prêts, {nb_echeances} échéances)")

    # 4. Supprimer propositions en attente
    print("\n4️⃣ Suppression propositions en attente...")
    nb_propositions = session.query(PropositionEnAttente).count()

    print(f"   • {nb_propositions} propositions à supprimer")

    if not dry_run:
        session.query(PropositionEnAttente).delete()

    actions.append(f"✅ Propositions supprimées ({nb_propositions})")

    # 5. Commit
    if not dry_run:
        print("\n5️⃣ Commit des changements...")
        session.commit()
        print("   ✅ Changements committés")

    return actions

def afficher_etat_final(session):
    """Affiche l'état final après reset"""
    print("\n" + "="*80)
    print("📊 ÉTAT FINAL APRÈS RESET")
    print("="*80)

    # Exercices
    exercices = session.query(ExerciceComptable).order_by(ExerciceComptable.annee).all()
    print(f"\n📅 Exercices ({len(exercices)}):")
    for ex in exercices:
        nb_ecritures = session.query(EcritureComptable).filter(
            EcritureComptable.exercice_id == ex.id
        ).count()
        print(f"  • {ex.annee} ({ex.statut}) : {nb_ecritures} écritures")

    # Vérifier bilan ouverture 2024
    ex_2024 = session.query(ExerciceComptable).filter(
        ExerciceComptable.annee == 2024
    ).first()

    if ex_2024:
        ecritures_bilan = session.query(EcritureComptable).filter(
            EcritureComptable.exercice_id == ex_2024.id
        ).all()

        print(f"\n📋 Détail écritures 2024:")
        for e in ecritures_bilan:
            print(f"  • {e.numero_ecriture} - {e.type_ecriture} - {e.libelle_ecriture}")

    # Prêts
    nb_prets = session.query(PretImmobilier).count()
    nb_echeances = session.query(EcheancePret).count()
    print(f"\n💰 Prêts: {nb_prets} prêts, {nb_echeances} échéances")

    # Propositions
    nb_propositions = session.query(PropositionEnAttente).count()
    print(f"\n📋 Propositions: {nb_propositions}")

def main():
    parser = argparse.ArgumentParser(
        description="Reset base de données pour test V8.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXEMPLES:
  # Simulation (dry-run)
  python reset_base_pour_test.py

  # Reset réel
  python reset_base_pour_test.py --confirm
        """
    )
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='Confirmer le reset RÉEL (sans cette option = dry-run)'
    )

    args = parser.parse_args()

    print("="*80)
    print("🔥 RESET BASE POUR TEST V8.0")
    print("="*80)

    # Vérifier DATABASE_URL
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        print("\n❌ ERREUR : DATABASE_URL non définie")
        sys.exit(1)

    session = get_session(DATABASE_URL)

    # Afficher état actuel
    afficher_etat_actuel(session)

    # Mode
    if not args.confirm:
        print("\n" + "="*80)
        print("⚠️  MODE DRY-RUN (simulation)")
        print("="*80)
        print("\nPour effectuer le reset RÉEL, ajouter : --confirm")
        print()
    else:
        # Sauvegarde obligatoire
        if not sauvegarder_avant_reset(session):
            print("\n❌ Abandon : sauvegarde échouée")
            sys.exit(1)

        # Confirmation finale
        print("\n" + "="*80)
        print("⚠️  DERNIÈRE CONFIRMATION")
        print("="*80)
        print("\nCette opération va SUPPRIMER définitivement :")
        print("  - Exercice 2025 + toutes ses écritures")
        print("  - Écritures 2024 SAUF bilan d'ouverture")
        print("  - Tous les prêts et échéances")
        print("  - Toutes les propositions en attente")
        print()
        confirmation = input("Taper 'RESET' pour confirmer : ")

        if confirmation != 'RESET':
            print("\n❌ Abandon : confirmation non reçue")
            sys.exit(1)

    # Reset
    actions = reset_base(session, dry_run=not args.confirm)

    # Afficher résumé
    print("\n" + "="*80)
    print("📋 RÉSUMÉ DES ACTIONS")
    print("="*80)
    for action in actions:
        print(f"  {action}")

    if args.confirm:
        # Afficher état final
        afficher_etat_final(session)

        print("\n" + "="*80)
        print("✅ RESET TERMINÉ")
        print("="*80)
        print("\n🎯 Base prête pour test V8.0 :")
        print("  1. Envoyer email avec tableaux amortissement (prêts)")
        print("  2. Envoyer email avec relevé bancaire T1-T3 2024 (41 pages)")
        print("  3. Vérifier 86/86 événements extraits")
        print()
    else:
        print("\n" + "="*80)
        print("ℹ️  DRY-RUN TERMINÉ (aucune modification)")
        print("="*80)
        print("\nPour effectuer le reset RÉEL : --confirm")
        print()

    session.close()

if __name__ == '__main__':
    main()
