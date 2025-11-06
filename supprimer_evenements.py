#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SUPPRESSION DES ÉVÉNEMENTS COMPTABLES
=====================================
Supprime tous les événements extraits des relevés bancaires
pour permettre un retraitement propre avec les filtres améliorés

Date: 06/11/2025
Auteur: Claude Code Assistant

ATTENTION: Ce script supprime TOUS les événements comptables !
           Les écritures liées au bilan d'ouverture ne sont PAS affectées.
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("❌ Variable DATABASE_URL non définie")
    exit(1)

# Connexion
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

print()
print("=" * 80)
print("⚠️  SUPPRESSION DES ÉVÉNEMENTS COMPTABLES")
print("=" * 80)
print()

try:
    # Compter les événements existants
    result = session.execute(text("""
        SELECT COUNT(*) FROM evenements_comptables
    """))
    total_before = result.fetchone()[0]

    if total_before == 0:
        print("✅ Aucun événement à supprimer")
        session.close()
        exit(0)

    print(f"🔍 {total_before} événements actuellement en base")
    print()

    # Afficher la répartition par type
    result = session.execute(text("""
        SELECT type_evenement, COUNT(*) as nb
        FROM evenements_comptables
        GROUP BY type_evenement
        ORDER BY nb DESC
    """))

    print("📊 Répartition par type:")
    print()
    for row in result:
        type_evt = row[0] or "(non détecté)"
        print(f"  {type_evt:30s}: {row[1]:3d}")

    print()
    print("-" * 80)
    print()

    # Demande de confirmation
    print("⚠️  ATTENTION: Cette opération est IRRÉVERSIBLE !")
    print()
    print(f"   Tous les {total_before} événements seront supprimés.")
    print("   Les écritures du bilan d'ouverture ne seront PAS affectées.")
    print()

    # En mode automatique (variable d'environnement), pas de confirmation
    auto_confirm = os.getenv('AUTO_CONFIRM', 'false').lower() == 'true'

    if not auto_confirm:
        response = input("   Confirmer la suppression? (oui/non): ").strip().lower()
        if response != 'oui':
            print()
            print("❌ Suppression annulée")
            print()
            session.close()
            exit(0)

    print()
    print("🗑️  Suppression en cours...")
    print()

    # Supprimer tous les événements
    result = session.execute(text("""
        DELETE FROM evenements_comptables
    """))

    session.commit()
    nb_supprime = result.rowcount

    print(f"✅ {nb_supprime} événements supprimés")
    print()

    # Vérifier qu'il ne reste rien
    result = session.execute(text("""
        SELECT COUNT(*) FROM evenements_comptables
    """))
    total_after = result.fetchone()[0]

    if total_after == 0:
        print("✅ Table evenements_comptables vidée avec succès")
    else:
        print(f"⚠️  {total_after} événements restants (inattendu)")

    print()
    print("=" * 80)
    print("✅ NETTOYAGE TERMINÉ")
    print("=" * 80)
    print()
    print("💡 Prochaine étape:")
    print("   Relancer le traitement avec les filtres améliorés:")
    print()
    print("   python workflow_evenements.py \\")
    print("       --pdf 'Elements Comptables des 1-2-3T2024.pdf' \\")
    print("       --date-debut 2024-01-01 \\")
    print("       --date-fin 2024-09-30")
    print()

except Exception as e:
    print(f"❌ Erreur: {e}")
    session.rollback()
    import traceback
    traceback.print_exc()
finally:
    session.close()
