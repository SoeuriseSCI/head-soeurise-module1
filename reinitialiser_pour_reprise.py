#!/usr/bin/env python3
"""
RÉINITIALISATION BD POUR REPRISE MÉTHODIQUE
============================================

Nettoie la base de données pour une reprise propre :
- CONSERVE : Bilan 2023 (11 écritures validées)
- SUPPRIME : Tout le reste (prêts, échéances, événements, propositions)

Usage:
    # Sur Render shell
    python reinitialiser_pour_reprise.py

Date: 09/11/2025
Auteur: Claude Code
"""

import os
import sys
from datetime import datetime
from models_module2 import get_session, ExerciceComptable, EcritureComptable
from sqlalchemy import text

# Coloration terminal
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(msg):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{msg}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")

def print_success(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.END}")

def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.END}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.END}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.END}")


def creer_sauvegarde():
    """Crée une sauvegarde JSON avant nettoyage"""
    print_header("ÉTAPE 1/4: SAUVEGARDE DE SÉCURITÉ")

    try:
        import subprocess
        result = subprocess.run(
            ['python', 'sauvegarder_base.py'],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            print_success("Sauvegarde créée avec succès")
            # Afficher le nom du fichier de sauvegarde
            for line in result.stdout.split('\n'):
                if 'backups/soeurise_bd_' in line:
                    print(f"   📁 {line.strip()}")
            return True
        else:
            print_error("Échec création sauvegarde")
            print(result.stderr)
            return False

    except Exception as e:
        print_error(f"Erreur sauvegarde: {e}")
        return False


def verifier_etat_initial(session):
    """Vérifie l'état de la BD avant nettoyage"""
    print_header("ÉTAPE 2/4: ÉTAT INITIAL DE LA BASE")

    try:
        # Bilan 2023
        exercice_2023 = session.query(ExerciceComptable).filter_by(annee=2023).first()
        if not exercice_2023:
            print_error("Exercice 2023 non trouvé!")
            return False

        bilan_2023 = session.query(EcritureComptable).filter(
            EcritureComptable.type_ecriture == 'INIT_BILAN_2023',
            EcritureComptable.exercice_id == exercice_2023.id
        ).count()

        print(f"📊 Bilan 2023: {bilan_2023} écritures")
        if bilan_2023 != 11:
            print_warning(f"Attendu 11, trouvé {bilan_2023}")
        else:
            print_success("Bilan 2023 intact")

        # Autres données
        result = session.execute(text("SELECT COUNT(*) FROM prets_immobiliers"))
        nb_prets = result.scalar()

        result = session.execute(text("SELECT COUNT(*) FROM echeances_prets"))
        nb_echeances = result.scalar()

        result = session.execute(text("SELECT COUNT(*) FROM evenements_comptables"))
        nb_evenements = result.scalar()

        result = session.execute(text("SELECT COUNT(*) FROM propositions_comptables"))
        nb_propositions = result.scalar()

        result = session.execute(text("SELECT COUNT(*) FROM ecritures_comptables WHERE type_ecriture != 'INIT_BILAN_2023'"))
        nb_ecritures_autres = result.scalar()

        print(f"\n📋 Données à supprimer:")
        print(f"   - Prêts immobiliers: {nb_prets}")
        print(f"   - Échéances: {nb_echeances}")
        print(f"   - Événements: {nb_evenements}")
        print(f"   - Propositions: {nb_propositions}")
        print(f"   - Écritures (hors Bilan 2023): {nb_ecritures_autres}")

        return True

    except Exception as e:
        print_error(f"Erreur vérification: {e}")
        return False


def nettoyer_base(session):
    """Supprime tout sauf le Bilan 2023"""
    print_header("ÉTAPE 3/4: NETTOYAGE DE LA BASE")

    try:
        # Exercice 2023 (à conserver)
        exercice_2023 = session.query(ExerciceComptable).filter_by(annee=2023).first()
        if not exercice_2023:
            print_error("Exercice 2023 non trouvé!")
            return False

        print("🗑️  Suppression en cours...")

        # 1. Supprimer les événements comptables
        result = session.execute(text("DELETE FROM evenements_comptables"))
        nb_evenements = result.rowcount
        print(f"   ✓ {nb_evenements} événements supprimés")

        # 2. Supprimer les propositions
        result = session.execute(text("DELETE FROM propositions_comptables"))
        nb_propositions = result.rowcount
        print(f"   ✓ {nb_propositions} propositions supprimées")

        # 3. Supprimer les échéances de prêts
        result = session.execute(text("DELETE FROM echeances_prets"))
        nb_echeances = result.rowcount
        print(f"   ✓ {nb_echeances} échéances supprimées")

        # 4. Supprimer les prêts
        result = session.execute(text("DELETE FROM prets_immobiliers"))
        nb_prets = result.rowcount
        print(f"   ✓ {nb_prets} prêts supprimés")

        # 5. Supprimer les écritures SAUF Bilan 2023
        result = session.execute(
            text("""
                DELETE FROM ecritures_comptables
                WHERE NOT (type_ecriture = 'INIT_BILAN_2023' AND exercice_id = :ex_id)
            """),
            {'ex_id': exercice_2023.id}
        )
        nb_ecritures = result.rowcount
        print(f"   ✓ {nb_ecritures} écritures (hors Bilan 2023) supprimées")

        # 6. Supprimer balances mensuelles
        result = session.execute(text("DELETE FROM balances_mensuelles"))
        nb_balances = result.rowcount
        print(f"   ✓ {nb_balances} balances supprimées")

        # Commit
        session.commit()
        print_success("Nettoyage terminé")

        return True

    except Exception as e:
        session.rollback()
        print_error(f"Erreur nettoyage: {e}")
        return False


def verifier_etat_final(session):
    """Vérifie que seul le Bilan 2023 reste"""
    print_header("ÉTAPE 4/4: VÉRIFICATION FINALE")

    try:
        # Vérifier Bilan 2023
        exercice_2023 = session.query(ExerciceComptable).filter_by(annee=2023).first()
        bilan_2023 = session.query(EcritureComptable).filter(
            EcritureComptable.type_ecriture == 'INIT_BILAN_2023',
            EcritureComptable.exercice_id == exercice_2023.id
        ).count()

        print(f"📊 Bilan 2023: {bilan_2023} écritures")
        if bilan_2023 == 11:
            print_success("Bilan 2023 préservé ✓")
        else:
            print_error(f"PROBLÈME: {bilan_2023} écritures au lieu de 11")
            return False

        # Vérifier que tout le reste est vide
        result = session.execute(text("SELECT COUNT(*) FROM prets_immobiliers"))
        nb_prets = result.scalar()

        result = session.execute(text("SELECT COUNT(*) FROM echeances_prets"))
        nb_echeances = result.scalar()

        result = session.execute(text("SELECT COUNT(*) FROM evenements_comptables"))
        nb_evenements = result.scalar()

        result = session.execute(text("SELECT COUNT(*) FROM propositions_comptables"))
        nb_propositions = result.scalar()

        result = session.execute(text("SELECT COUNT(*) FROM ecritures_comptables WHERE type_ecriture != 'INIT_BILAN_2023'"))
        nb_ecritures_autres = result.scalar()

        print(f"\n📋 Autres données:")
        print(f"   - Prêts: {nb_prets}")
        print(f"   - Échéances: {nb_echeances}")
        print(f"   - Événements: {nb_evenements}")
        print(f"   - Propositions: {nb_propositions}")
        print(f"   - Écritures (hors Bilan): {nb_ecritures_autres}")

        tous_vides = (nb_prets == 0 and nb_echeances == 0 and nb_evenements == 0
                     and nb_propositions == 0 and nb_ecritures_autres == 0)

        if tous_vides:
            print_success("Base nettoyée correctement ✓")
            return True
        else:
            print_error("Des données subsistent encore")
            return False

    except Exception as e:
        print_error(f"Erreur vérification finale: {e}")
        return False


def main():
    """Workflow principal"""
    print_header("RÉINITIALISATION BD POUR REPRISE MÉTHODIQUE")

    print(f"{Colors.YELLOW}Ce script va:{Colors.END}")
    print(f"  1. Créer une sauvegarde JSON")
    print(f"  2. Supprimer TOUTES les données SAUF le Bilan 2023")
    print(f"  3. Vérifier que le Bilan 2023 est intact")
    print()
    print(f"{Colors.RED}ATTENTION: Cette action est irréversible (sauf restauration sauvegarde){Colors.END}")
    print()

    response = input(f"{Colors.BOLD}Tapez 'OUI' pour continuer: {Colors.END}")

    if response != "OUI":
        print_warning("Annulé par l'utilisateur")
        sys.exit(0)

    # Récupérer session
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print_error("DATABASE_URL non définie!")
        sys.exit(1)

    session = get_session(db_url)

    try:
        # Étape 1: Sauvegarde
        if not creer_sauvegarde():
            print_error("Sauvegarde échouée - abandon")
            sys.exit(1)

        # Étape 2: État initial
        if not verifier_etat_initial(session):
            print_error("Vérification initiale échouée - abandon")
            sys.exit(1)

        # Étape 3: Nettoyage
        if not nettoyer_base(session):
            print_error("Nettoyage échoué - abandon")
            sys.exit(1)

        # Étape 4: Vérification finale
        if not verifier_etat_final(session):
            print_error("Vérification finale échouée")
            sys.exit(1)

        # SUCCÈS
        print_header("✅ RÉINITIALISATION RÉUSSIE")
        print(f"{Colors.GREEN}La base est prête pour la reprise méthodique:{Colors.END}")
        print(f"  ✓ Bilan 2023 préservé (11 écritures)")
        print(f"  ✓ Toutes les autres données supprimées")
        print()
        print(f"{Colors.BOLD}Prochaines étapes:{Colors.END}")
        print(f"  1. Traiter les tableaux d'amortissement")
        print(f"  2. Traiter les événements T1-T3 2024")
        print(f"  3. Traiter les événements T4 2024")

    except Exception as e:
        print_error(f"Erreur non gérée: {e}")
        sys.exit(1)
    finally:
        session.close()


if __name__ == '__main__':
    main()
