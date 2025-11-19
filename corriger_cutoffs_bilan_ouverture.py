#!/usr/bin/env python3
"""
Correction des écritures de bilan d'ouverture 2024 pour en faire des cutoffs 2023

CONTEXTE:
- Les comptes 4181 (7356€) et 4081 (653€) existent dans le bilan d'ouverture 2024
- Ils sont datés 01/01/2024 avec type INIT_BILAN_2023
- Ils doivent être transformés en cutoffs au 31/12/2023

ACTIONS:
1. Modifier écriture ID=363 (4181→89, 7356€)
   - Date: 01/01/2024 → 31/12/2023
   - Type: INIT_BILAN_2023 → CUTOFF_PRODUIT_A_RECEVOIR
   - Exercice: 2 → 1

2. Modifier écriture ID=370 (89→4081, 653€)
   - Date: 01/01/2024 → 31/12/2023
   - Type: INIT_BILAN_2023 → CUTOFF_HONORAIRES
   - Exercice: 2 → 1

Puis utiliser generateur_extournes.py pour créer les extournes automatiquement.
"""

import os
import sys
from datetime import date
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def corriger_cutoffs(dry_run: bool = True):
    """Corrige les écritures de bilan d'ouverture pour en faire des cutoffs"""

    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        print("❌ Variable DATABASE_URL non définie")
        sys.exit(1)

    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        print("=" * 80)
        print("🔧 CORRECTION CUTOFFS - Bilan d'Ouverture → Cutoffs 31/12/2023")
        print("=" * 80)
        print()

        if dry_run:
            print("⚠️  MODE DRY-RUN : Simulation uniquement")
            print("   Pour exécuter réellement, utiliser --execute")
        else:
            print("✅ MODE EXÉCUTION : Les écritures seront modifiées")
        print()

        # 1. Vérifier les écritures à modifier
        print("📋 Vérification des écritures existantes:")
        query = text("""
            SELECT id, date_ecriture, exercice_id, type_ecriture,
                   compte_debit, compte_credit, montant, libelle_ecriture
            FROM ecritures_comptables
            WHERE id IN (363, 370)
            ORDER BY id
        """)
        ecritures = session.execute(query).fetchall()

        if len(ecritures) != 2:
            print(f"❌ Erreur : {len(ecritures)} écriture(s) trouvée(s), 2 attendues")
            return False

        print(f"  ID  | Date       | Exer | Type              | Débit → Crédit | Montant")
        print("  " + "-" * 85)
        for ec in ecritures:
            print(f"  {ec[0]:<4} | {ec[1]} | {ec[2]:<4} | {ec[3]:<17} | {ec[4]} → {ec[5]:<6} | {ec[6]:>10,.2f}€")
        print()

        # 2. Préparer les modifications
        modifications = [
            {
                'id': 363,
                'nouvelle_date': date(2023, 12, 31),
                'nouveau_type': 'CUTOFF_PRODUIT_A_RECEVOIR',
                'nouvel_exercice': 1,
                'nouveau_libelle': 'Cutoff 31/12/2023 - Produits à recevoir (revenus SCPI)',
                'description': '4181 (7356€) - Produits à recevoir'
            },
            {
                'id': 370,
                'nouvelle_date': date(2023, 12, 31),
                'nouveau_type': 'CUTOFF_HONORAIRES',
                'nouvel_exercice': 1,
                'nouveau_libelle': 'Cutoff 31/12/2023 - Factures non parvenues (honoraires)',
                'description': '4081 (653€) - Factures non parvenues'
            }
        ]

        print("🔧 Modifications à appliquer:")
        for modif in modifications:
            print(f"  ID {modif['id']} - {modif['description']}")
            print(f"    • Date: → {modif['nouvelle_date']}")
            print(f"    • Type: → {modif['nouveau_type']}")
            print(f"    • Exercice: → {modif['nouvel_exercice']}")
            print(f"    • Libellé: → {modif['nouveau_libelle']}")
            print()

        # 3. Appliquer les modifications
        if not dry_run:
            print("💾 Application des modifications...")

            for modif in modifications:
                query = text("""
                    UPDATE ecritures_comptables
                    SET date_ecriture = :date,
                        type_ecriture = :type,
                        exercice_id = :exercice,
                        libelle_ecriture = :libelle
                    WHERE id = :id
                """)

                session.execute(query, {
                    'id': modif['id'],
                    'date': modif['nouvelle_date'],
                    'type': modif['nouveau_type'],
                    'exercice': modif['nouvel_exercice'],
                    'libelle': modif['nouveau_libelle']
                })

                print(f"  ✅ Écriture ID {modif['id']} modifiée")

            session.commit()
            print()
            print("✅ Modifications appliquées avec succès")
            print()

            # 4. Vérifier le résultat
            print("📋 Vérification après modification:")
            query = text("""
                SELECT id, date_ecriture, exercice_id, type_ecriture,
                       compte_debit, compte_credit, montant
                FROM ecritures_comptables
                WHERE id IN (363, 370)
                ORDER BY id
            """)
            ecritures = session.execute(query).fetchall()

            print(f"  ID  | Date       | Exer | Type                        | Débit → Crédit | Montant")
            print("  " + "-" * 95)
            for ec in ecritures:
                print(f"  {ec[0]:<4} | {ec[1]} | {ec[2]:<4} | {ec[3]:<27} | {ec[4]} → {ec[5]:<6} | {ec[6]:>10,.2f}€")
            print()

        else:
            print("🔍 MODE DRY-RUN : Aucune modification appliquée")
            print("   Pour exécuter réellement, ajouter --execute")
            print()

        # 5. Prochaines étapes
        print("📌 PROCHAINES ÉTAPES:")
        print("  1. Exécuter ce script avec --execute pour appliquer les modifications")
        print("  2. Lancer: python generateur_extournes.py --exercice 2023 --execute")
        print("     → Créera les extournes au 01/01/2024")
        print("  3. Vérifier l'équilibre du bilan avec verifier_bilan_2023.py")
        print()
        print("=" * 80)

        return True

    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
        return False

    finally:
        session.close()


def main():
    """Point d'entrée principal"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Correction des cutoffs du bilan d\'ouverture 2024'
    )
    parser.add_argument('--execute', action='store_true',
                       help='Exécuter réellement (sinon dry-run)')

    args = parser.parse_args()

    success = corriger_cutoffs(dry_run=not args.execute)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
