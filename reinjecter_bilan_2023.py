#!/usr/bin/env python3
"""
Script pour réinjecter le bilan 2023 en base de données
Source: propositions_INIT_BILAN_2023_CORRECTED.md
"""

import os
import sys
from datetime import datetime, date
from sqlalchemy import text

# Import models
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from models_module2 import get_session

# Les 10 écritures du bilan 2023
ECRITURES_BILAN_2023 = [
    {
        "numero_ecriture": "2023-INIT-0001",
        "libelle": "Ouverture: Titres SCPI",
        "compte_debit": "280",
        "compte_credit": "899",
        "montant": 500032,
        "type_ecriture": "INIT_BILAN_2023"
    },
    {
        "numero_ecriture": "2023-INIT-0002",
        "libelle": "Ouverture: Provision epargne",
        "compte_debit": "899",
        "compte_credit": "290",
        "montant": 50003,
        "type_ecriture": "INIT_BILAN_2023"
    },
    {
        "numero_ecriture": "2023-INIT-0003",
        "libelle": "Ouverture: Autres créances",
        "compte_debit": "412",
        "compte_credit": "899",
        "montant": 7356,
        "type_ecriture": "INIT_BILAN_2023"
    },
    {
        "numero_ecriture": "2023-INIT-0004",
        "libelle": "Ouverture: Actions propres",
        "compte_debit": "502",
        "compte_credit": "899",
        "montant": 4140,
        "type_ecriture": "INIT_BILAN_2023"
    },
    {
        "numero_ecriture": "2023-INIT-0005",
        "libelle": "Ouverture: Banque LCL",
        "compte_debit": "512",
        "compte_credit": "899",
        "montant": 2093,
        "type_ecriture": "INIT_BILAN_2023"
    },
    {
        "numero_ecriture": "2023-INIT-0006",
        "libelle": "Ouverture: Capital",
        "compte_debit": "899",
        "compte_credit": "101",
        "montant": 1000,
        "type_ecriture": "INIT_BILAN_2023"
    },
    {
        "numero_ecriture": "2023-INIT-0007",
        "libelle": "Ouverture: Report à nouveau",
        "compte_debit": "120",
        "compte_credit": "899",
        "montant": 57992,
        "type_ecriture": "INIT_BILAN_2023"
    },
    {
        "numero_ecriture": "2023-INIT-0008",
        "libelle": "Ouverture: Emprunts LCL",
        "compte_debit": "899",
        "compte_credit": "161",
        "montant": 497993,
        "type_ecriture": "INIT_BILAN_2023"
    },
    {
        "numero_ecriture": "2023-INIT-0009",
        "libelle": "Ouverture: Compte courant Ulrik",
        "compte_debit": "899",
        "compte_credit": "444",
        "montant": 120,
        "type_ecriture": "INIT_BILAN_2023"
    },
    {
        "numero_ecriture": "2023-INIT-0010",
        "libelle": "Ouverture: Dettes fournisseurs",
        "compte_debit": "899",
        "compte_credit": "401",
        "montant": 653,
        "type_ecriture": "INIT_BILAN_2023"
    }
]

def main():
    print("=" * 80)
    print("RÉINJECTION BILAN 2023")
    print("=" * 80)
    print()

    # Récupérer DATABASE_URL depuis environnement
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("❌ Erreur: DATABASE_URL non définie")
        sys.exit(1)

    session = get_session(db_url)

    try:
        # 1. Vérifier l'exercice 2023
        print("1. Vérification exercice 2023...")
        result = session.execute(
            text("SELECT id FROM exercices_comptables WHERE annee = 2023")
        )
        exercice_row = result.fetchone()

        if not exercice_row:
            print("   ❌ Exercice 2023 non trouvé")
            sys.exit(1)

        exercice_id = exercice_row[0]
        print(f"   ✓ Exercice 2023 trouvé (ID: {exercice_id})")
        print()

        # 2. Vérifier si écritures existent déjà
        print("2. Vérification écritures existantes...")
        result = session.execute(
            text("SELECT COUNT(*) FROM ecritures_comptables WHERE type_ecriture = 'INIT_BILAN_2023'")
        )
        count = result.fetchone()[0]

        if count > 0:
            print(f"   ⚠️ {count} écriture(s) INIT_BILAN_2023 déjà présente(s)")
            response = input("   Supprimer et réinjecter ? (oui/non): ").strip().lower()
            if response != 'oui':
                print("   Annulation.")
                sys.exit(0)

            # Supprimer
            session.execute(
                text("DELETE FROM ecritures_comptables WHERE type_ecriture = 'INIT_BILAN_2023'")
            )
            session.commit()
            print(f"   ✓ {count} écriture(s) supprimée(s)")
        else:
            print("   ✓ Aucune écriture INIT_BILAN_2023 existante")
        print()

        # 3. Insérer les écritures
        print("3. Insertion des 10 écritures du bilan 2023...")
        date_ecriture = date(2023, 12, 31)

        for i, ecriture in enumerate(ECRITURES_BILAN_2023, 1):
            session.execute(
                text("""
                    INSERT INTO ecritures_comptables (
                        exercice_id,
                        numero_ecriture,
                        date_ecriture,
                        libelle_ecriture,
                        type_ecriture,
                        compte_debit,
                        compte_credit,
                        montant,
                        created_at
                    ) VALUES (
                        :exercice_id,
                        :numero_ecriture,
                        :date_ecriture,
                        :libelle,
                        :type_ecriture,
                        :compte_debit,
                        :compte_credit,
                        :montant,
                        NOW()
                    )
                """),
                {
                    'exercice_id': exercice_id,
                    'numero_ecriture': ecriture['numero_ecriture'],
                    'date_ecriture': date_ecriture,
                    'libelle': ecriture['libelle'],
                    'type_ecriture': ecriture['type_ecriture'],
                    'compte_debit': ecriture['compte_debit'],
                    'compte_credit': ecriture['compte_credit'],
                    'montant': ecriture['montant']
                }
            )
            print(f"   ✓ {i}/10 - {ecriture['numero_ecriture']}: {ecriture['libelle']}")

        session.commit()
        print()

        # 4. Vérification finale
        print("4. Vérification finale...")
        result = session.execute(
            text("""
                SELECT COUNT(*),
                       SUM(CASE WHEN compte_debit = '899' THEN montant ELSE 0 END) as credit_899,
                       SUM(CASE WHEN compte_credit = '899' THEN montant ELSE 0 END) as debit_899
                FROM ecritures_comptables
                WHERE type_ecriture = 'INIT_BILAN_2023'
            """)
        )
        row = result.fetchone()
        count = row[0]
        credit_899 = row[1] or 0
        debit_899 = row[2] or 0

        print(f"   ✓ {count} écritures insérées")
        print(f"   ✓ Total débits compte 899: {credit_899:,}€")
        print(f"   ✓ Total crédits compte 899: {debit_899:,}€")
        print(f"   ✓ Équilibre compte 899: {credit_899 - debit_899:,}€ (doit être 0)")
        print()

        if credit_899 == debit_899:
            print("=" * 80)
            print("✅ SUCCÈS - Bilan 2023 réinjecté avec équilibre parfait")
            print("=" * 80)
        else:
            print("=" * 80)
            print("⚠️ ATTENTION - Déséquilibre détecté !")
            print("=" * 80)

    except Exception as e:
        session.rollback()
        print()
        print("=" * 80)
        print("❌ ERREUR")
        print("=" * 80)
        print(f"Erreur: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
