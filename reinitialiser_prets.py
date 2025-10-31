#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour réinitialiser les données des prêts en base de données
ATTENTION: Ce script supprime TOUTES les données des prêts immobiliers et leurs échéances
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_utils import get_session
from models_module2 import PretImmobilier, EcheancePret

def reinitialiser_prets(confirmer=False):
    """
    Supprime tous les prêts et échéances de la BD

    Args:
        confirmer: Si True, exécute la suppression. Si False, affiche seulement ce qui sera fait.
    """
    session = get_session()

    print("=" * 80)
    print("RÉINITIALISATION BASE DE DONNÉES - PRÊTS IMMOBILIERS")
    print("=" * 80)
    print()

    # Compter ce qui existe
    nb_prets = session.query(PretImmobilier).count()
    nb_echeances = session.query(EcheancePret).count()

    print(f"📊 Données actuelles en BD:")
    print(f"   - Prêts: {nb_prets}")
    print(f"   - Échéances: {nb_echeances}")
    print()

    if nb_prets == 0 and nb_echeances == 0:
        print("✓ La base de données est déjà vide (rien à supprimer)")
        return

    if not confirmer:
        print("⚠️  MODE SIMULATION (aucune suppression effectuée)")
        print()
        print("Pour VRAIMENT supprimer les données, relancez avec:")
        print("  python3 reinitialiser_prets.py --confirmer")
        print()
        return

    # Confirmation explicite
    print("⚠️  ATTENTION: Vous allez SUPPRIMER toutes les données !")
    print()
    reponse = input("Tapez 'OUI' en majuscules pour confirmer: ")

    if reponse != "OUI":
        print("❌ Annulé (réponse non confirmée)")
        return

    print()
    print("🗑️  Suppression en cours...")

    try:
        # Supprimer d'abord les échéances (foreign key vers prêts)
        nb_echeances_supprimees = session.query(EcheancePret).delete()
        print(f"   ✓ {nb_echeances_supprimees} échéances supprimées")

        # Puis supprimer les prêts
        nb_prets_supprimes = session.query(PretImmobilier).delete()
        print(f"   ✓ {nb_prets_supprimes} prêts supprimés")

        # Commit
        session.commit()
        print()
        print("✅ SUCCÈS: Base de données réinitialisée")

    except Exception as e:
        session.rollback()
        print()
        print(f"❌ ERREUR lors de la suppression: {e}")
        import traceback
        traceback.print_exc()

    print()
    print("=" * 80)
    print("FIN RÉINITIALISATION")
    print("=" * 80)

if __name__ == "__main__":
    # Vérifier si --confirmer dans les arguments
    confirmer = "--confirmer" in sys.argv

    try:
        reinitialiser_prets(confirmer=confirmer)
    except KeyboardInterrupt:
        print()
        print("❌ Annulé par l'utilisateur (Ctrl+C)")
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
