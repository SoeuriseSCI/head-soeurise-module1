#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCRIPT DE RENUMEROTATION DES EXERCICES
======================================
Objectif : Remettre les IDs dans l'ordre chronologique
- Exercice 2023 → ID = 1
- Exercice 2024 → ID = 2

État actuel (inversé) :
- Exercice 2024 → ID = 1
- Exercice 2023 → ID = 2

Stratégie (éviter conflit PK) :
1. 2024 (ID=1) → ID=3 (temporaire)
2. 2023 (ID=2) → ID=1
3. 2024 (ID=3) → ID=2

IMPORTANT : Fait une sauvegarde BD automatiquement avant toute modification
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Import models
from models_module2 import ExerciceComptable, EcritureComptable, CalculAmortissement, BalanceMensuelle, RapportComptable


def sauvegarder_avant_patch():
    """Sauvegarde BD avant modification"""
    print("\n🔄 Sauvegarde BD avant renumérotoation...")

    try:
        # Appeler le script de sauvegarde existant
        result = os.system("python sauvegarder_base.py")
        if result != 0:
            print("❌ Erreur lors de la sauvegarde")
            return False

        print("✅ Sauvegarde BD réussie")
        return True
    except Exception as e:
        print(f"❌ Erreur sauvegarde : {e}")
        return False


def renumeroter_exercices(database_url: str, dry_run: bool = False):
    """
    Renumérote les exercices pour respecter l'ordre chronologique

    Args:
        database_url: URL connexion PostgreSQL
        dry_run: Si True, affiche les actions sans les exécuter
    """

    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # ═══════════════════════════════════════════════════════════════════════
        # 1. VÉRIFIER L'ÉTAT ACTUEL
        # ═══════════════════════════════════════════════════════════════════════

        print("\n" + "="*70)
        print("ÉTAT ACTUEL DES EXERCICES")
        print("="*70)

        exercices = session.query(ExerciceComptable).order_by(ExerciceComptable.id).all()

        if len(exercices) != 2:
            print(f"❌ Erreur : {len(exercices)} exercices trouvés (attendu: 2)")
            return False

        for ex in exercices:
            nb_ecritures = session.query(EcritureComptable).filter_by(exercice_id=ex.id).count()
            nb_calculs = session.query(CalculAmortissement).filter_by(exercice_id=ex.id).count()
            nb_balances = session.query(BalanceMensuelle).filter_by(exercice_id=ex.id).count()
            nb_rapports = session.query(RapportComptable).filter_by(exercice_id=ex.id).count()

            print(f"\n📊 Exercice {ex.annee} (ID={ex.id})")
            print(f"   - Écritures comptables : {nb_ecritures}")
            print(f"   - Calculs amortissement : {nb_calculs}")
            print(f"   - Balances mensuelles : {nb_balances}")
            print(f"   - Rapports comptables : {nb_rapports}")

        # Identifier les exercices
        ex_2023 = session.query(ExerciceComptable).filter_by(annee=2023).first()
        ex_2024 = session.query(ExerciceComptable).filter_by(annee=2024).first()

        if not ex_2023 or not ex_2024:
            print("❌ Erreur : Exercices 2023 ou 2024 non trouvés")
            return False

        print(f"\n🔍 État actuel :")
        print(f"   - Exercice 2023 → ID = {ex_2023.id}")
        print(f"   - Exercice 2024 → ID = {ex_2024.id}")

        # Vérifier si déjà dans le bon ordre
        if ex_2023.id == 1 and ex_2024.id == 2:
            print("\n✅ Les exercices sont déjà dans le bon ordre (2023=1, 2024=2)")
            return True

        # Vérifier l'ordre inversé attendu
        if ex_2024.id != 1 or ex_2023.id != 2:
            print(f"\n⚠️  ATTENTION : Ordre inattendu détecté !")
            print(f"   Attendu : 2024=ID1, 2023=ID2")
            print(f"   Trouvé : 2024=ID{ex_2024.id}, 2023=ID{ex_2023.id}")
            reponse = input("\nContinuer quand même ? (oui/non) : ")
            if reponse.lower() != 'oui':
                print("❌ Opération annulée")
                return False

        # ═══════════════════════════════════════════════════════════════════════
        # 2. PLAN D'EXÉCUTION
        # ═══════════════════════════════════════════════════════════════════════

        print("\n" + "="*70)
        print("PLAN DE RENUMÉROTOATION")
        print("="*70)
        print("\nÉtape 1 : Exercice 2024 (ID=1) → ID=3 (temporaire)")
        print("Étape 2 : Exercice 2023 (ID=2) → ID=1")
        print("Étape 3 : Exercice 2024 (ID=3) → ID=2")
        print("\nRésultat final :")
        print("   - Exercice 2023 → ID = 1 ✅")
        print("   - Exercice 2024 → ID = 2 ✅")

        if dry_run:
            print("\n🔍 MODE DRY-RUN : Aucune modification ne sera effectuée")
            return True

        # Confirmation utilisateur
        print("\n⚠️  ATTENTION : Cette opération va modifier la base de données")
        print("   Une sauvegarde sera effectuée automatiquement avant.")
        reponse = input("\nContinuer ? (oui/non) : ")
        if reponse.lower() != 'oui':
            print("❌ Opération annulée")
            return False

        # ═══════════════════════════════════════════════════════════════════════
        # 3. SAUVEGARDE AVANT MODIFICATION
        # ═══════════════════════════════════════════════════════════════════════

        if not sauvegarder_avant_patch():
            print("❌ Sauvegarde échouée - Opération annulée")
            return False

        # ═══════════════════════════════════════════════════════════════════════
        # 4. RENUMÉROTOATION (TRANSACTION ATOMIQUE)
        # ═══════════════════════════════════════════════════════════════════════

        print("\n" + "="*70)
        print("EXÉCUTION DE LA RENUMÉROTOATION")
        print("="*70)

        # Démarrer transaction
        session.begin_nested()

        try:
            # DÉSACTIVER TEMPORAIREMENT LES CONTRAINTES FK
            print("\n🔄 Désactivation temporaire des contraintes FK...")
            session.execute(text("""
                ALTER TABLE ecritures_comptables DROP CONSTRAINT IF EXISTS ecritures_comptables_exercice_id_fkey;
            """))
            session.execute(text("""
                ALTER TABLE calculs_amortissements DROP CONSTRAINT IF EXISTS calculs_amortissements_exercice_id_fkey;
            """))
            session.execute(text("""
                ALTER TABLE balances_mensuelles DROP CONSTRAINT IF EXISTS balances_mensuelles_exercice_id_fkey;
            """))
            session.execute(text("""
                ALTER TABLE rapports_comptables DROP CONSTRAINT IF EXISTS rapports_comptables_exercice_id_fkey;
            """))
            print("   ✅ Contraintes FK désactivées")

            # ÉTAPE 1 : 2024 (ID=1) → ID=3
            print("\n🔄 Étape 1/3 : Exercice 2024 (ID=1) → ID=3...")
            session.execute(text("UPDATE exercices_comptables SET id = 3 WHERE id = 1;"))
            session.execute(text("UPDATE ecritures_comptables SET exercice_id = 3 WHERE exercice_id = 1;"))
            session.execute(text("UPDATE calculs_amortissements SET exercice_id = 3 WHERE exercice_id = 1;"))
            session.execute(text("UPDATE balances_mensuelles SET exercice_id = 3 WHERE exercice_id = 1;"))
            session.execute(text("UPDATE rapports_comptables SET exercice_id = 3 WHERE exercice_id = 1;"))
            print("   ✅ Exercice 2024 déplacé vers ID=3")

            # ÉTAPE 2 : 2023 (ID=2) → ID=1
            print("\n🔄 Étape 2/3 : Exercice 2023 (ID=2) → ID=1...")
            session.execute(text("UPDATE exercices_comptables SET id = 1 WHERE id = 2;"))
            session.execute(text("UPDATE ecritures_comptables SET exercice_id = 1 WHERE exercice_id = 2;"))
            session.execute(text("UPDATE calculs_amortissements SET exercice_id = 1 WHERE exercice_id = 2;"))
            session.execute(text("UPDATE balances_mensuelles SET exercice_id = 1 WHERE exercice_id = 2;"))
            session.execute(text("UPDATE rapports_comptables SET exercice_id = 1 WHERE exercice_id = 2;"))
            print("   ✅ Exercice 2023 déplacé vers ID=1")

            # ÉTAPE 3 : 2024 (ID=3) → ID=2
            print("\n🔄 Étape 3/3 : Exercice 2024 (ID=3) → ID=2...")
            session.execute(text("UPDATE exercices_comptables SET id = 2 WHERE id = 3;"))
            session.execute(text("UPDATE ecritures_comptables SET exercice_id = 2 WHERE exercice_id = 3;"))
            session.execute(text("UPDATE calculs_amortissements SET exercice_id = 2 WHERE exercice_id = 3;"))
            session.execute(text("UPDATE balances_mensuelles SET exercice_id = 2 WHERE exercice_id = 3;"))
            session.execute(text("UPDATE rapports_comptables SET exercice_id = 2 WHERE exercice_id = 3;"))

            print("   ✅ Exercice 2024 déplacé vers ID=2")

            # Réinitialiser la séquence auto-increment pour le prochain exercice
            print("\n🔄 Réinitialisation de la séquence auto-increment...")
            session.execute(text("""
                SELECT setval('exercices_comptables_id_seq', (SELECT MAX(id) FROM exercices_comptables));
            """))
            print("   ✅ Séquence réinitialisée")

            # RÉACTIVER LES CONTRAINTES FK
            print("\n🔄 Réactivation des contraintes FK...")
            session.execute(text("""
                ALTER TABLE ecritures_comptables
                ADD CONSTRAINT ecritures_comptables_exercice_id_fkey
                FOREIGN KEY (exercice_id) REFERENCES exercices_comptables(id);
            """))
            session.execute(text("""
                ALTER TABLE calculs_amortissements
                ADD CONSTRAINT calculs_amortissements_exercice_id_fkey
                FOREIGN KEY (exercice_id) REFERENCES exercices_comptables(id);
            """))
            session.execute(text("""
                ALTER TABLE balances_mensuelles
                ADD CONSTRAINT balances_mensuelles_exercice_id_fkey
                FOREIGN KEY (exercice_id) REFERENCES exercices_comptables(id);
            """))
            session.execute(text("""
                ALTER TABLE rapports_comptables
                ADD CONSTRAINT rapports_comptables_exercice_id_fkey
                FOREIGN KEY (exercice_id) REFERENCES exercices_comptables(id);
            """))
            print("   ✅ Contraintes FK réactivées")

            # Commit transaction
            session.commit()

            print("\n" + "="*70)
            print("✅ RENUMÉROTOATION RÉUSSIE")
            print("="*70)

        except Exception as e:
            session.rollback()
            print(f"\n❌ ERREUR lors de la renumérotoation : {e}")
            print("   La transaction a été annulée (ROLLBACK)")

            # Tenter de réactiver les contraintes FK même en cas d'erreur
            print("\n🔄 Tentative de réactivation des contraintes FK...")
            try:
                session.execute(text("""
                    ALTER TABLE ecritures_comptables
                    ADD CONSTRAINT ecritures_comptables_exercice_id_fkey
                    FOREIGN KEY (exercice_id) REFERENCES exercices_comptables(id);
                """))
                session.execute(text("""
                    ALTER TABLE calculs_amortissements
                    ADD CONSTRAINT calculs_amortissements_exercice_id_fkey
                    FOREIGN KEY (exercice_id) REFERENCES exercices_comptables(id);
                """))
                session.execute(text("""
                    ALTER TABLE balances_mensuelles
                    ADD CONSTRAINT balances_mensuelles_exercice_id_fkey
                    FOREIGN KEY (exercice_id) REFERENCES exercices_comptables(id);
                """))
                session.execute(text("""
                    ALTER TABLE rapports_comptables
                    ADD CONSTRAINT rapports_comptables_exercice_id_fkey
                    FOREIGN KEY (exercice_id) REFERENCES exercices_comptables(id);
                """))
                session.commit()
                print("   ✅ Contraintes FK réactivées")
            except Exception as e2:
                print(f"   ⚠️  Erreur lors de la réactivation : {e2}")
                print("   ⚠️  ATTENTION : Les contraintes FK peuvent être manquantes")

            return False

        # ═══════════════════════════════════════════════════════════════════════
        # 5. VÉRIFICATION POST-OPÉRATION
        # ═══════════════════════════════════════════════════════════════════════

        print("\n" + "="*70)
        print("VÉRIFICATION POST-OPÉRATION")
        print("="*70)

        # Recharger les exercices
        session.expire_all()
        ex_2023_new = session.query(ExerciceComptable).filter_by(annee=2023).first()
        ex_2024_new = session.query(ExerciceComptable).filter_by(annee=2024).first()

        print(f"\n📊 Nouvel état :")
        print(f"   - Exercice 2023 → ID = {ex_2023_new.id} {'✅' if ex_2023_new.id == 1 else '❌'}")
        print(f"   - Exercice 2024 → ID = {ex_2024_new.id} {'✅' if ex_2024_new.id == 2 else '❌'}")

        # Vérifier les écritures
        for ex in [ex_2023_new, ex_2024_new]:
            nb_ecritures = session.query(EcritureComptable).filter_by(exercice_id=ex.id).count()
            nb_calculs = session.query(CalculAmortissement).filter_by(exercice_id=ex.id).count()
            nb_balances = session.query(BalanceMensuelle).filter_by(exercice_id=ex.id).count()
            nb_rapports = session.query(RapportComptable).filter_by(exercice_id=ex.id).count()

            print(f"\n📊 Exercice {ex.annee} (ID={ex.id})")
            print(f"   - Écritures comptables : {nb_ecritures}")
            print(f"   - Calculs amortissement : {nb_calculs}")
            print(f"   - Balances mensuelles : {nb_balances}")
            print(f"   - Rapports comptables : {nb_rapports}")

        # Validation finale
        if ex_2023_new.id == 1 and ex_2024_new.id == 2:
            print("\n" + "="*70)
            print("🎉 SUCCÈS COMPLET")
            print("="*70)
            print("\nLes exercices sont maintenant dans l'ordre chronologique :")
            print("   - Exercice 2023 = ID 1 ✅")
            print("   - Exercice 2024 = ID 2 ✅")
            return True
        else:
            print("\n❌ ERREUR : Les IDs ne correspondent pas aux valeurs attendues")
            return False

    except Exception as e:
        print(f"\n❌ ERREUR CRITIQUE : {e}")
        session.rollback()
        return False

    finally:
        session.close()


def main():
    """Point d'entrée principal"""

    print("\n" + "="*70)
    print("SCRIPT DE RENUMÉROTOATION DES EXERCICES")
    print("="*70)
    print("\nObjectif : Remettre les IDs dans l'ordre chronologique")
    print("   - Exercice 2023 → ID = 1")
    print("   - Exercice 2024 → ID = 2")

    # Récupérer DATABASE_URL
    database_url = os.environ.get('DATABASE_URL')

    if not database_url:
        print("\n❌ Erreur : Variable DATABASE_URL non définie")
        print("   Export : export DATABASE_URL='postgresql://...'")
        sys.exit(1)

    # Mode dry-run si argument --dry-run
    dry_run = '--dry-run' in sys.argv

    if dry_run:
        print("\n🔍 MODE DRY-RUN activé (aucune modification)")

    # Exécuter la renumérotoation
    succes = renumeroter_exercices(database_url, dry_run=dry_run)

    if succes:
        print("\n✅ Opération terminée avec succès")
        sys.exit(0)
    else:
        print("\n❌ Opération échouée")
        sys.exit(1)


if __name__ == '__main__':
    main()
