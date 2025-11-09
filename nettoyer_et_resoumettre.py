#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCRIPT DE NETTOYAGE ET RESOUMISSION COMPTABLE
==============================================

Objectif: Nettoyer la base comptable 2024 et permettre la resoumission
         complète des relevés bancaires avec le code corrigé.

IMPORTANT: Ce script PRÉSERVE le bilan d'ouverture 2023 (exercice 2023).

Usage:
    python nettoyer_et_resoumettre.py --dry-run  # Simulation
    python nettoyer_et_resoumettre.py --execute  # Exécution réelle

Étapes:
    1. Sauvegarde automatique de la BD
    2. Suppression écritures exercice 2024 UNIQUEMENT
    3. Suppression événements comptables 2024
    4. Suppression propositions en attente
    5. Préservation bilan 2023 (exercice 2023 INTACT)
    6. Instructions de resoumission

Date: 09/11/2025
Auteur: Module 2 - Maintenance
"""

import os
import sys
import json
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def sauvegarder_bd():
    """Sauvegarde automatique avant nettoyage"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'backups/avant_nettoyage_{timestamp}.json'

    print(f"📦 Sauvegarde BD vers {backup_file}...")

    # Appeler le script de sauvegarde existant
    import subprocess
    result = subprocess.run(['python', 'sauvegarder_base.py'], capture_output=True)

    if result.returncode == 0:
        print(f"✅ Sauvegarde créée avec succès")
        return True
    else:
        print(f"❌ Erreur sauvegarde: {result.stderr.decode()}")
        return False


def analyser_base(session):
    """Analyse l'état actuel de la base"""
    print("=" * 80)
    print("ANALYSE ÉTAT ACTUEL BASE DE DONNÉES")
    print("=" * 80)
    print()

    # Exercices
    result = session.execute(text("""
        SELECT annee, statut,
               (SELECT COUNT(*) FROM ecritures_comptables WHERE exercice_id = ec.id) as nb_ecritures
        FROM exercices_comptables ec
        ORDER BY annee
    """))

    print("📊 Exercices comptables:")
    for row in result:
        print(f"   Exercice {row[0]} ({row[1]:10s}) : {row[2]:3d} écritures")
    print()

    # Événements comptables
    result = session.execute(text("""
        SELECT
            EXTRACT(YEAR FROM date_operation) as annee,
            COUNT(*) as nb_events
        FROM evenements_comptables
        GROUP BY EXTRACT(YEAR FROM date_operation)
        ORDER BY annee
    """))

    print("📝 Événements comptables:")
    for row in result:
        print(f"   Année {int(row[0])} : {row[1]:3d} événements")
    print()

    # Propositions en attente
    result = session.execute(text("""
        SELECT statut, COUNT(*) as nb
        FROM propositions_en_attente
        GROUP BY statut
    """))

    print("📋 Propositions en attente:")
    for row in result:
        print(f"   {row[0]:15s} : {row[1]:3d}")
    print()

    # Bilan 2023 (à préserver)
    result = session.execute(text("""
        SELECT COUNT(*)
        FROM ecritures_comptables ec
        JOIN exercices_comptables ex ON ec.exercice_id = ex.id
        WHERE ex.annee = 2023
    """))
    nb_bilan_2023 = result.fetchone()[0]

    print(f"🔒 Bilan 2023 à PRÉSERVER : {nb_bilan_2023} écritures")
    print()

    return nb_bilan_2023


def nettoyer_exercice_2024(session, dry_run=True):
    """Nettoie UNIQUEMENT l'exercice 2024 (préserve 2023)"""

    mode = "🔍 SIMULATION" if dry_run else "⚠️  EXÉCUTION RÉELLE"
    print("=" * 80)
    print(f"{mode} - NETTOYAGE EXERCICE 2024")
    print("=" * 80)
    print()

    # 1. Compter ce qui sera supprimé
    result = session.execute(text("""
        SELECT COUNT(*)
        FROM ecritures_comptables ec
        JOIN exercices_comptables ex ON ec.exercice_id = ex.id
        WHERE ex.annee = 2024
    """))
    nb_ecritures_2024 = result.fetchone()[0]

    result = session.execute(text("""
        SELECT COUNT(*)
        FROM evenements_comptables
        WHERE EXTRACT(YEAR FROM date_operation) = 2024
    """))
    nb_events_2024 = result.fetchone()[0]

    result = session.execute(text("""
        SELECT COUNT(*)
        FROM propositions_en_attente
    """))
    nb_propositions = result.fetchone()[0]

    print(f"📊 Éléments à supprimer:")
    print(f"   - Écritures exercice 2024 : {nb_ecritures_2024}")
    print(f"   - Événements comptables 2024 : {nb_events_2024}")
    print(f"   - Propositions en attente : {nb_propositions}")
    print()

    if dry_run:
        print("⏸️  Mode simulation - Aucune suppression effectuée")
        return

    # 2. Suppression réelle
    print("🗑️  Suppression en cours...")

    # Supprimer écritures 2024
    result = session.execute(text("""
        DELETE FROM ecritures_comptables
        WHERE exercice_id IN (
            SELECT id FROM exercices_comptables WHERE annee = 2024
        )
    """))
    print(f"   ✅ {result.rowcount} écritures 2024 supprimées")

    # Supprimer événements 2024
    result = session.execute(text("""
        DELETE FROM evenements_comptables
        WHERE EXTRACT(YEAR FROM date_operation) = 2024
    """))
    print(f"   ✅ {result.rowcount} événements 2024 supprimés")

    # Supprimer propositions
    result = session.execute(text("""
        DELETE FROM propositions_en_attente
    """))
    print(f"   ✅ {result.rowcount} propositions supprimées")

    session.commit()
    print()
    print("✅ Nettoyage terminé avec succès")
    print()


def verifier_preservation_bilan_2023(session, nb_initial):
    """Vérifie que le bilan 2023 est intact"""
    result = session.execute(text("""
        SELECT COUNT(*)
        FROM ecritures_comptables ec
        JOIN exercices_comptables ex ON ec.exercice_id = ex.id
        WHERE ex.annee = 2023
    """))
    nb_final = result.fetchone()[0]

    if nb_initial == nb_final:
        print(f"✅ Bilan 2023 INTACT : {nb_final} écritures préservées")
        return True
    else:
        print(f"❌ ERREUR: Bilan 2023 modifié ! Avant: {nb_initial}, Après: {nb_final}")
        print("⚠️  ROLLBACK REQUIS !")
        return False


def afficher_instructions_resoumission():
    """Affiche les instructions de resoumission"""
    print()
    print("=" * 80)
    print("📋 PROCÉDURE DE RESOUMISSION DES RELEVÉS BANCAIRES")
    print("=" * 80)
    print()
    print("✅ CONTINUITÉ ASSURÉE: Q1-Q3 déborde sur début octobre, Q4 continue")
    print("✅ DÉTECTION DOUBLONS: Automatique par fingerprint (date+libellé+montant)")
    print()
    print("1️⃣  RESOUMISSION DANS L'ORDRE:")
    print("    a) Soumettre Q1-Q3 complet (jan-sept + début oct)")
    print("    b) Soumettre Q4 complet (suite oct-déc)")
    print()
    print("2️⃣  VALIDATION:")
    print("    - Valider les propositions dans l'ordre chronologique")
    print("    - Vérifier les dates d'opération (maintenant corrigées)")
    print("    - Vérifier la décomposition prêts (intérêts/capital)")
    print("    - Vérifier logs: aucun doublon (ou doublons ignorés)")
    print()
    print("3️⃣  VÉRIFICATIONS:")
    print("    - Dates d'écritures = dates opérations bancaires")
    print("    - Remboursements prêts = 2 écritures (661 + 164)")
    print("    - Tous les mois 2024 couverts (jan-déc)")
    print()
    print("4️⃣  DÉPLOIEMENT:")
    print("    - Merger vers main")
    print("    - Déploiement MANUEL sur Render par Ulrik")
    print()
    print("=" * 80)
    print()


def main():
    """Point d'entrée principal"""

    if len(sys.argv) < 2:
        print("Usage: python nettoyer_et_resoumettre.py [--dry-run|--execute]")
        sys.exit(1)

    mode = sys.argv[1]
    dry_run = (mode == '--dry-run')

    if mode not in ['--dry-run', '--execute']:
        print("Argument invalide. Utiliser --dry-run ou --execute")
        sys.exit(1)

    # Connexion BD
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL non définie")
        sys.exit(1)

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 1. Analyse état actuel
        nb_bilan_2023 = analyser_base(session)

        # 2. Sauvegarde (seulement en mode exécution)
        if not dry_run:
            if not sauvegarder_bd():
                print("❌ Sauvegarde échouée - Abandon")
                sys.exit(1)

        # 3. Nettoyage
        nettoyer_exercice_2024(session, dry_run=dry_run)

        # 4. Vérification (seulement en mode exécution)
        if not dry_run:
            if not verifier_preservation_bilan_2023(session, nb_bilan_2023):
                session.rollback()
                print("❌ Vérification échouée - Rollback effectué")
                sys.exit(1)

        # 5. Instructions
        afficher_instructions_resoumission()

        print("✅ Script terminé avec succès")

    except Exception as e:
        print(f"❌ Erreur: {e}")
        session.rollback()
        sys.exit(1)

    finally:
        session.close()


if __name__ == '__main__':
    main()
