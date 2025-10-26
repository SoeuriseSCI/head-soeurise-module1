#!/usr/bin/env python3
"""
Script manuel pour valider et insérer le bilan 2023
À utiliser en cas d'échec du workflow email
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from models_module2 import (
    get_session, ExerciceComptable, EcritureComptable,
    EvenementComptable, PlanCompte
)

# JSON des propositions validées
propositions = [
    {
        "numero_ecriture": "2023-INIT-0001",
        "type": "INIT_BILAN_2023",
        "compte_debit": "280",
        "compte_credit": "89",
        "montant": 500032,
        "libelle": "Ouverture: SCPI Epargne Pierre"
    },
    {
        "numero_ecriture": "2023-INIT-0002",
        "type": "INIT_BILAN_2023",
        "compte_debit": "412",
        "compte_credit": "89",
        "montant": 7356,
        "libelle": "Ouverture: Créances diverses"
    },
    {
        "numero_ecriture": "2023-INIT-0003",
        "type": "INIT_BILAN_2023",
        "compte_debit": "502",
        "compte_credit": "89",
        "montant": 4140,
        "libelle": "Ouverture: Actions"
    },
    {
        "numero_ecriture": "2023-INIT-0004",
        "type": "INIT_BILAN_2023",
        "compte_debit": "512",
        "compte_credit": "89",
        "montant": 2093,
        "libelle": "Ouverture: Banque"
    },
    {
        "numero_ecriture": "2023-INIT-0005",
        "type": "INIT_BILAN_2023",
        "compte_debit": "120",
        "compte_credit": "89",
        "montant": 57992,
        "libelle": "Ouverture: Report à nouveau (négatif)"
    },
    {
        "numero_ecriture": "2023-INIT-0006",
        "type": "INIT_BILAN_2023",
        "compte_debit": "89",
        "compte_credit": "290",
        "montant": 50003,
        "libelle": "Ouverture: Provision dépréciation SCPI"
    },
    {
        "numero_ecriture": "2023-INIT-0007",
        "type": "INIT_BILAN_2023",
        "compte_debit": "89",
        "compte_credit": "101",
        "montant": 1000,
        "libelle": "Ouverture: Capital social"
    },
    {
        "numero_ecriture": "2023-INIT-0008",
        "type": "INIT_BILAN_2023",
        "compte_debit": "89",
        "compte_credit": "130",
        "montant": 21844,
        "libelle": "Ouverture: Résultat 2023"
    },
    {
        "numero_ecriture": "2023-INIT-0009",
        "type": "INIT_BILAN_2023",
        "compte_debit": "89",
        "compte_credit": "161",
        "montant": 497993,
        "libelle": "Ouverture: Emprunts"
    },
    {
        "numero_ecriture": "2023-INIT-0010",
        "type": "INIT_BILAN_2023",
        "compte_debit": "89",
        "compte_credit": "444",
        "montant": 120,
        "libelle": "Ouverture: Compte courant associés"
    },
    {
        "numero_ecriture": "2023-INIT-0011",
        "type": "INIT_BILAN_2023",
        "compte_debit": "89",
        "compte_credit": "401",
        "montant": 653,
        "libelle": "Ouverture: Dettes fournisseurs"
    }
]

def main():
    print("=" * 80)
    print("VALIDATION MANUELLE BILAN 2023")
    print("=" * 80)
    print()

    # Utiliser DATABASE_URL depuis env ou argument
    database_url = os.environ.get('DATABASE_URL', 'postgresql://soeurise:6cIWYzBxmh8YKBGBH9Or6ohidT6NiCap@dpg-d3ikk7ggjchc73ee4flg-a/soeurise')
    session = get_session(database_url)

    try:
        # 1. Créer ou récupérer l'exercice 2023
        print("1. Vérification exercice 2023...")
        exercice = session.query(ExerciceComptable).filter_by(annee=2023).first()

        if not exercice:
            exercice = ExerciceComptable(
                annee=2023,
                date_debut=datetime(2023, 1, 1),
                date_fin=datetime(2023, 12, 31),
                statut='OUVERT'
            )
            session.add(exercice)
            session.flush()
            print(f"   ✓ Exercice 2023 créé (ID: {exercice.id})")
        else:
            print(f"   ✓ Exercice 2023 existant (ID: {exercice.id})")

        # 2. Créer l'événement comptable
        print("\n2. Création événement comptable...")
        evenement = EvenementComptable(
            email_from="ulrik.c.s.be@gmail.com",
            email_subject="Initialisation bilan 2023",
            email_body="Validation manuelle via script",
            type_evenement="INIT_BILAN_2023",
            est_comptable=True,
            statut='VALIDE',
            nb_propositions=len(propositions)
        )
        session.add(evenement)
        session.flush()
        print(f"   ✓ Événement créé (ID: {evenement.id})")

        # 3. Insérer les écritures
        print("\n3. Insertion des écritures...")
        ecritures_creees = []

        for i, prop in enumerate(propositions, 1):
            ecriture = EcritureComptable(
                exercice_id=exercice.id,
                evenement_id=evenement.id,
                numero_ecriture=prop['numero_ecriture'],
                date_ecriture=datetime(2023, 1, 1),
                compte_debit=prop['compte_debit'],
                compte_credit=prop['compte_credit'],
                montant=prop['montant'],
                libelle=prop['libelle'],
                type_operation=prop['type']
            )
            session.add(ecriture)
            ecritures_creees.append(ecriture)
            print(f"   ✓ {i}/11: {prop['numero_ecriture']} - {prop['libelle'][:50]}")

        # 4. Commit
        print("\n4. Sauvegarde en base de données...")
        session.commit()
        print("   ✓ Toutes les écritures ont été sauvegardées")

        # 5. Vérification
        print("\n5. Vérification...")
        total_ecritures = session.query(EcritureComptable).filter_by(
            exercice_id=exercice.id
        ).count()
        print(f"   ✓ Total écritures exercice 2023: {total_ecritures}")

        # Calcul des totaux
        total_debit_89 = sum(e.montant for e in ecritures_creees if e.compte_debit == '89')
        total_credit_89 = sum(e.montant for e in ecritures_creees if e.compte_credit == '89')

        print(f"\n6. Équilibre compte 89:")
        print(f"   - Débit:  {total_debit_89:>12,.2f} €")
        print(f"   - Crédit: {total_credit_89:>12,.2f} €")
        print(f"   - Solde:  {total_debit_89 - total_credit_89:>12,.2f} €")

        if abs(total_debit_89 - total_credit_89) < 0.01:
            print("   ✓ ÉQUILIBRE PARFAIT")
        else:
            print("   ✗ ERREUR: Déséquilibre détecté !")

        print()
        print("=" * 80)
        print("✅ INITIALISATION BILAN 2023 TERMINÉE AVEC SUCCÈS")
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
        return 1

    finally:
        session.close()

    return 0

if __name__ == '__main__':
    sys.exit(main())
