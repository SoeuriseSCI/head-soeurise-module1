#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NETTOYAGE DONNÉES DE TEST - PRÉSERVE LE BILAN D'OUVERTURE
===========================================================

Ce script supprime les données de test pour permettre de retester
le parseur V6 avec une base propre, TOUT EN PRÉSERVANT :
- Le schéma de la base de données
- L'exercice comptable 2023
- Le plan comptable
- Les écritures du bilan d'ouverture 2023

SUPPRIME :
- Tous les prêts immobiliers et leurs échéances
- Toutes les écritures comptables SAUF le bilan d'ouverture
- Toutes les opérations bancaires
- Tous les événements comptables
- Toutes les propositions en attente

⚠️ ATTENTION : Ce script modifie la base de données !

Usage:
    python nettoyer_donnees_test.py

Après nettoyage, vous pouvez :
1. Retester le parseur V6 avec les PDFs
2. Réinsérer les prêts en BD
3. Vérifier que tout fonctionne correctement
"""

import os
import sys
import psycopg2
from datetime import datetime
import argparse

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL non défini")
    sys.exit(1)


def demander_confirmation(force=False):
    """Demande confirmation avant suppression"""
    print("=" * 80)
    print("🧹 NETTOYAGE DONNÉES DE TEST")
    print("=" * 80)
    print()
    print("Ce script va SUPPRIMER :")
    print("  ❌ Tous les prêts immobiliers")
    print("  ❌ Toutes les échéances de prêts")
    print("  ❌ Toutes les écritures comptables (SAUF bilan d'ouverture)")
    print("  ❌ Toutes les opérations bancaires")
    print("  ❌ Tous les événements comptables")
    print("  ❌ Toutes les propositions en attente")
    print()
    print("Ce script va PRÉSERVER :")
    print("  ✅ Le schéma de la base de données")
    print("  ✅ L'exercice comptable 2023")
    print("  ✅ Le plan comptable")
    print("  ✅ Les écritures du bilan d'ouverture (type_ecriture = 'INIT_BILAN_2023')")
    print()
    print("⚠️  Idéal pour retester le parseur V6 avec une base propre !")
    print()

    if force:
        print("✅ Mode --yes activé : confirmation automatique")
        print()
        return

    try:
        reponse = input("Tapez 'OUI' pour continuer : ")
        if reponse.strip().upper() != 'OUI':
            print("❌ Opération annulée")
            sys.exit(0)
        print()
    except EOFError:
        print("\n❌ Impossible de lire l'entrée (utilisez --yes pour forcer)")
        sys.exit(1)


def main(force=False):
    """Nettoyage des données de test"""

    demander_confirmation(force)

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    print("🧹 Début du nettoyage...")
    print("-" * 80)

    # ═══════════════════════════════════════════════════════════════════════════
    # ÉTAPE 1 : Suppression des échéances de prêts
    # ═══════════════════════════════════════════════════════════════════════════

    print("\n📊 ÉTAPE 1/6 : Suppression des échéances de prêts")

    cur.execute("SELECT COUNT(*) FROM echeances_prets")
    nb_avant = cur.fetchone()[0]

    cur.execute("DELETE FROM echeances_prets")
    conn.commit()

    print(f"  ✓ {nb_avant} échéances supprimées")

    # ═══════════════════════════════════════════════════════════════════════════
    # ÉTAPE 2 : Suppression des prêts immobiliers
    # ═══════════════════════════════════════════════════════════════════════════

    print("\n🏠 ÉTAPE 2/6 : Suppression des prêts immobiliers")

    cur.execute("SELECT COUNT(*) FROM prets_immobiliers")
    nb_avant = cur.fetchone()[0]

    cur.execute("DELETE FROM prets_immobiliers")
    conn.commit()

    print(f"  ✓ {nb_avant} prêts supprimés")

    # ═══════════════════════════════════════════════════════════════════════════
    # ÉTAPE 3 : Suppression des écritures comptables (SAUF bilan d'ouverture)
    # ═══════════════════════════════════════════════════════════════════════════

    print("\n💰 ÉTAPE 3/6 : Suppression des écritures comptables")

    cur.execute("SELECT COUNT(*) FROM ecritures_comptables")
    nb_total = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*) FROM ecritures_comptables
        WHERE type_ecriture = 'INIT_BILAN_2023'
    """)
    nb_bilan = cur.fetchone()[0]

    cur.execute("""
        DELETE FROM ecritures_comptables
        WHERE type_ecriture IS NULL OR type_ecriture != 'INIT_BILAN_2023'
    """)
    conn.commit()

    nb_supprimees = nb_total - nb_bilan
    print(f"  ✓ {nb_supprimees} écritures supprimées")
    print(f"  ✅ {nb_bilan} écritures du bilan d'ouverture préservées")

    # ═══════════════════════════════════════════════════════════════════════════
    # ÉTAPE 4 : Suppression des opérations bancaires
    # ═══════════════════════════════════════════════════════════════════════════

    print("\n🏦 ÉTAPE 4/6 : Suppression des opérations bancaires")

    try:
        cur.execute("SELECT COUNT(*) FROM operations_bancaires")
        nb_avant = cur.fetchone()[0]

        cur.execute("DELETE FROM operations_bancaires")
        conn.commit()

        print(f"  ✓ {nb_avant} opérations supprimées")
    except psycopg2.errors.UndefinedTable:
        conn.rollback()
        print(f"  ⚠️  Table 'operations_bancaires' n'existe pas (ignoré)")

    # ═══════════════════════════════════════════════════════════════════════════
    # ÉTAPE 5 : Suppression des événements comptables
    # ═══════════════════════════════════════════════════════════════════════════

    print("\n📧 ÉTAPE 5/6 : Suppression des événements comptables")

    try:
        cur.execute("SELECT COUNT(*) FROM evenements_comptables")
        nb_avant = cur.fetchone()[0]

        cur.execute("DELETE FROM evenements_comptables")
        conn.commit()

        print(f"  ✓ {nb_avant} événements supprimés")
    except psycopg2.errors.UndefinedTable:
        conn.rollback()
        print(f"  ⚠️  Table 'evenements_comptables' n'existe pas (ignoré)")

    # ═══════════════════════════════════════════════════════════════════════════
    # ÉTAPE 6 : Suppression des propositions en attente
    # ═══════════════════════════════════════════════════════════════════════════

    print("\n📝 ÉTAPE 6/6 : Suppression des propositions en attente")

    try:
        cur.execute("SELECT COUNT(*) FROM propositions_en_attente")
        nb_avant = cur.fetchone()[0]

        cur.execute("DELETE FROM propositions_en_attente")
        conn.commit()

        print(f"  ✓ {nb_avant} propositions supprimées")
    except psycopg2.errors.UndefinedTable:
        conn.rollback()
        print(f"  ⚠️  Table 'propositions_en_attente' n'existe pas (ignoré)")

    # ═══════════════════════════════════════════════════════════════════════════
    # VÉRIFICATION FINALE
    # ═══════════════════════════════════════════════════════════════════════════

    print()
    print("=" * 80)
    print("✅ VÉRIFICATION FINALE")
    print("=" * 80)
    print()

    # Compter ce qui reste
    cur.execute("SELECT COUNT(*) FROM exercices_comptables")
    nb_exercices = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM plans_comptes")
    nb_comptes = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM ecritures_comptables")
    nb_ecritures = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM prets_immobiliers")
    nb_prets = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM echeances_prets")
    nb_echeances = cur.fetchone()[0]

    print("État de la base après nettoyage :")
    print()
    print("✅ PRÉSERVÉ :")
    print(f"  - {nb_exercices} exercice(s) comptable(s)")
    print(f"  - {nb_comptes} comptes dans le plan comptable")
    print(f"  - {nb_ecritures} écritures (bilan d'ouverture uniquement)")
    print()
    print("🧹 NETTOYÉ :")
    print(f"  - {nb_prets} prêt(s) immobilier(s)")
    print(f"  - {nb_echeances} échéance(s) de prêt")
    print()
    print("=" * 80)
    print("🎉 NETTOYAGE TERMINÉ AVEC SUCCÈS !")
    print("=" * 80)
    print()
    print("🚀 Vous pouvez maintenant retester le parseur V6 :")
    print()
    print("  1. Exécuter : python test_parseur_v6.py")
    print("  2. Vérifier l'insertion en BD")
    print("  3. Consulter les résultats avec : python examiner_bd_prets.py")
    print()

    cur.close()
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nettoyer les données de test (préserve le bilan d'ouverture)")
    parser.add_argument('--yes', '-y', action='store_true', help='Confirmer automatiquement sans demander')
    args = parser.parse_args()

    try:
        main(force=args.yes)
    except KeyboardInterrupt:
        print("\n❌ Opération annulée par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
