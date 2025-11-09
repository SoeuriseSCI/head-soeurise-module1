#!/usr/bin/env python3
"""
CLEANUP SCRIPT - Suppression sécurisée des données T1-T4 2024

Script interactif avec vérifications avant/après pour nettoyer:
- 146 écritures T1-T4 2024
- Tables associées (balances, rapports)

CONSERVE:
- Bilan 2023 (11 écritures)
- Prêts immobiliers (2) + Échéances (467)
- Plan comptable

USAGE:
  python cleanup_t1_t4_2024.py
"""

import os
import sys
from datetime import datetime
from models_module2 import get_session, EcritureComptable, ExerciceComptable, PretsImmobiliers, EcheancesPrets
from sqlalchemy import text

# Coleurs pour le terminal
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

def verify_before_deletion(session):
    """Vérifier l'état avant suppression"""
    print_header("VÉRIFICATION PRÉ-SUPPRESSION")

    # Exercice 2024
    exercice_2024 = session.query(ExerciceComptable).filter_by(annee=2024).first()
    if not exercice_2024:
        print_error("Exercice 2024 non trouvé!")
        return False
    exercice_2024_id = exercice_2024.id

    # Exercice 2023
    exercice_2023 = session.query(ExerciceComptable).filter_by(annee=2023).first()
    if not exercice_2023:
        print_error("Exercice 2023 non trouvé!")
        return False
    exercice_2023_id = exercice_2023.id

    # Bilan 2023
    bilan_2023_count = session.query(EcritureComptable).filter(
        EcritureComptable.type_ecriture == 'INIT_BILAN_2023',
        EcritureComptable.exercice_id == exercice_2023_id
    ).count()
    print(f"Bilan 2023 (à conserver): {bilan_2023_count} écritures")
    if bilan_2023_count != 11:
        print_warning(f"Attendu 11, trouvé {bilan_2023_count}")
    else:
        print_success(f"Bilan 2023 intact")

    # T1-T4 2024
    t1_t4_count = session.query(EcritureComptable).filter(
        EcritureComptable.exercice_id == exercice_2024_id,
        EcritureComptable.type_ecriture != 'INIT_BILAN_2023'
    ).count()
    print(f"\nT1-T4 2024 (à supprimer): {t1_t4_count} écritures")

    # Détail par type
    result = session.execute(text("""
        SELECT type_ecriture, COUNT(*) as count
        FROM ecritures_comptables
        WHERE exercice_id = :ex_id
        GROUP BY type_ecriture
        ORDER BY count DESC
    """), {'ex_id': exercice_2024_id})

    print("\n  Détail par type:")
    for row in result:
        print(f"    - {row[0]}: {row[1]}")

    # Prêts (à conserver)
    prets_count = session.query(PretsImmobiliers).count()
    print(f"\nPrêts immobiliers (à conserver): {prets_count}")
    print_success("Prêts intacts") if prets_count == 2 else print_warning(f"Attendu 2, trouvé {prets_count}")

    # Échéances (à conserver)
    echeances_count = session.query(EcheancesPrets).count()
    print(f"Échéances prêts (à conserver): {echeances_count}")
    print_success("Échéances intactes") if echeances_count == 467 else print_warning(f"Attendu 467, trouvé {echeances_count}")

    # Vérifier que prêts ne sont pas liés à T1-T4
    orphaned = session.execute(text("""
        SELECT COUNT(*) FROM echeances_prets ep
        WHERE ep.ecriture_comptable_id IN (
            SELECT id FROM ecritures_comptables
            WHERE exercice_id = :ex_id AND type_ecriture != 'INIT_BILAN_2023'
        )
    """), {'ex_id': exercice_2024_id}).scalar()

    print(f"\nÉchéances liées à T1-T4: {orphaned}")
    print_success("Pas de risque") if orphaned == 0 else print_error(f"DANGER: {orphaned} échéances liées!")

    return True

def delete_t1_t4_data(session):
    """Supprimer les données T1-T4 2024"""
    print_header("SUPPRESSION DES DONNÉES T1-T4 2024")

    try:
        exercice_2024 = session.query(ExerciceComptable).filter_by(annee=2024).first()
        if not exercice_2024:
            print_error("Exercice 2024 non trouvé!")
            return False

        # Compter avant suppression
        before_count = session.query(EcritureComptable).filter(
            EcritureComptable.exercice_id == exercice_2024.id,
            EcritureComptable.type_ecriture != 'INIT_BILAN_2023'
        ).count()

        print(f"Suppression de {before_count} écritures T1-T4...")

        # Suppression (en transaction)
        session.query(EcritureComptable).filter(
            EcritureComptable.exercice_id == exercice_2024.id,
            EcritureComptable.type_ecriture != 'INIT_BILAN_2023'
        ).delete()

        print(f"  → {before_count} écritures supprimées")

        # Supprimer balances mensuelles 2024 (elles seront recalculées)
        session.execute(text("""
            DELETE FROM balances_mensuelles
            WHERE exercice_id = :ex_id
        """), {'ex_id': exercice_2024.id})

        print(f"  → Balances mensuelles 2024 supprimées")

        # Commit
        session.commit()
        print_success("Suppression réussie!")
        return True

    except Exception as e:
        session.rollback()
        print_error(f"Erreur lors de la suppression: {e}")
        return False

def verify_after_deletion(session):
    """Vérifier l'état après suppression"""
    print_header("VÉRIFICATION POST-SUPPRESSION")

    exercice_2024 = session.query(ExerciceComptable).filter_by(annee=2024).first()
    exercice_2023 = session.query(ExerciceComptable).filter_by(annee=2023).first()

    # Total écritures
    total = session.query(EcritureComptable).count()
    print(f"Total écritures restantes: {total}")
    print_success("Correct (11 = Bilan 2023)") if total == 11 else print_warning(f"Attendu 11, trouvé {total}")

    # Bilan 2023
    bilan_2023 = session.query(EcritureComptable).filter(
        EcritureComptable.type_ecriture == 'INIT_BILAN_2023',
        EcritureComptable.exercice_id == exercice_2023.id
    ).count()
    print(f"Bilan 2023: {bilan_2023} écritures")
    print_success("Préservé") if bilan_2023 == 11 else print_error(f"PROBLÈME: {bilan_2023}")

    # T1-T4 2024
    t1_t4 = session.query(EcritureComptable).filter(
        EcritureComptable.exercice_id == exercice_2024.id
    ).count()
    print(f"T1-T4 2024: {t1_t4} écritures")
    print_success("Supprimé") if t1_t4 == 0 else print_error(f"PROBLÈME: {t1_t4} encore présentes")

    # Prêts
    prets = session.query(PretsImmobiliers).count()
    print(f"Prêts immobiliers: {prets}")
    print_success("Intacts") if prets == 2 else print_error(f"PROBLÈME: {prets}")

    # Échéances
    echeances = session.query(EcheancesPrets).count()
    print(f"Échéances: {echeances}")
    print_success("Intactes") if echeances == 467 else print_error(f"PROBLÈME: {echeances}")

    return total == 11 and bilan_2023 == 11 and t1_t4 == 0

def main():
    """Workflow principal"""
    print_header("CLEANUP T1-T4 2024 - SCRIPT SÉCURISÉ")

    # Récupérer session DB
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print_error("DATABASE_URL non définie dans l'environnement!")
        sys.exit(1)

    session = get_session(db_url)

    try:
        # ÉTAPE 1: Vérification pré-suppression
        if not verify_before_deletion(session):
            sys.exit(1)

        # ÉTAPE 2: Confirmation utilisateur
        print_header("CONFIRMATION REQUISE")
        print(f"{Colors.YELLOW}Êtes-vous SÛR de vouloir supprimer les 146 écritures T1-T4 2024?{Colors.END}")
        print(f"{Colors.YELLOW}Cette action est irréversible (sauf restauration de sauvegarde).{Colors.END}")
        response = input(f"\n{Colors.BOLD}Tapez 'CONFIRME' pour continuer: {Colors.END}")

        if response != "CONFIRME":
            print_warning("Suppression annulée par l'utilisateur")
            sys.exit(0)

        # ÉTAPE 3: Suppression
        if not delete_t1_t4_data(session):
            sys.exit(1)

        # ÉTAPE 4: Vérification post-suppression
        if not verify_after_deletion(session):
            print_error("Vérification post-suppression échouée!")
            sys.exit(1)

        # SUCCÈS
        print_header("CLEANUP RÉUSSI ✅")
        print(f"{Colors.GREEN}Les données T1-T4 2024 ont été supprimées avec succès.{Colors.END}")
        print(f"{Colors.GREEN}Bilan 2023 et Prêts sont intacts.{Colors.END}")
        print(f"\n{Colors.BOLD}Prochaines étapes:{Colors.END}")
        print(f"1. Retraiter les PDFs T1, T2, T3")
        print(f"2. Générer et valider les propositions")
        print(f"3. Retraiter le PDF T4")
        print(f"4. Générer et valider les propositions")
        print(f"5. Vérifier l'intégrité des données")

    except Exception as e:
        print_error(f"Erreur non gérée: {e}")
        sys.exit(1)
    finally:
        session.close()

if __name__ == '__main__':
    main()
