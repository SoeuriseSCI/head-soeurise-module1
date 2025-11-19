#!/usr/bin/env python3
"""
Recherche des montants spécifiques 7356€ et 653€ dans toute la base
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("❌ DATABASE_URL non définie")
    exit(1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

try:
    print("=" * 80)
    print("🔍 RECHERCHE MONTANTS 7356€ et 653€")
    print("=" * 80)
    print()

    # Chercher 7356€ (revenus SCPI)
    print("💰 Recherche 7356€ (revenus SCPI attendus):")
    query = text("""
        SELECT
            id,
            date_ecriture,
            exercice_id,
            type_ecriture,
            compte_debit,
            compte_credit,
            montant,
            libelle_ecriture
        FROM ecritures_comptables
        WHERE montant = 7356.00
        ORDER BY date_ecriture DESC
    """)
    ecritures = session.execute(query).fetchall()

    if not ecritures:
        print("  ❌ Aucune écriture de 7356€ trouvée")
    else:
        print(f"  Trouvé {len(ecritures)} écriture(s):")
        for ec in ecritures:
            print(f"    ID={ec[0]} | {ec[1]} | ExercID={ec[2]} | {ec[3]} | {ec[4]} → {ec[5]} | {ec[6]}€")
            print(f"    Libellé: {ec[7]}")
    print()

    # Chercher 653€ (honoraires)
    print("💰 Recherche 653€ (honoraires attendus):")
    query = text("""
        SELECT
            id,
            date_ecriture,
            exercice_id,
            type_ecriture,
            compte_debit,
            compte_credit,
            montant,
            libelle_ecriture
        FROM ecritures_comptables
        WHERE montant = 653.00
        ORDER BY date_ecriture DESC
    """)
    ecritures = session.execute(query).fetchall()

    if not ecritures:
        print("  ❌ Aucune écriture de 653€ trouvée")
    else:
        print(f"  Trouvé {len(ecritures)} écriture(s):")
        for ec in ecritures:
            print(f"    ID={ec[0]} | {ec[1]} | ExercID={ec[2]} | {ec[3]} | {ec[4]} → {ec[5]} | {ec[6]}€")
            print(f"    Libellé: {ec[7]}")
    print()

    # Chercher toutes écritures 2024 avec 4181 ou 4081
    print("📅 Écritures 4181/4081 en 2024:")
    query = text("""
        SELECT
            id,
            date_ecriture,
            exercice_id,
            type_ecriture,
            compte_debit,
            compte_credit,
            montant,
            libelle_ecriture
        FROM ecritures_comptables
        WHERE (compte_debit IN ('4181', '4081') OR compte_credit IN ('4181', '4081'))
          AND EXTRACT(YEAR FROM date_ecriture) = 2024
        ORDER BY date_ecriture
    """)
    ecritures = session.execute(query).fetchall()

    if not ecritures:
        print("  ❌ Aucune écriture 4181/4081 en 2024")
    else:
        print(f"  Trouvé {len(ecritures)} écriture(s):")
        for ec in ecritures:
            print(f"    {ec[1]} | {ec[4]} → {ec[5]} | {ec[6]}€ | {ec[7][:50]}")
    print()

    # Vérifier le bilan d'ouverture 2024
    print("🏦 Écritures du bilan d'ouverture 2024 (compte 89):")
    query = text("""
        SELECT
            id,
            date_ecriture,
            compte_debit,
            compte_credit,
            montant,
            libelle_ecriture
        FROM ecritures_comptables
        WHERE (compte_debit = '89' OR compte_credit = '89')
          AND date_ecriture = '2024-01-01'
          AND libelle_ecriture LIKE '%ouverture%'
        ORDER BY id
        LIMIT 20
    """)
    ecritures = session.execute(query).fetchall()

    if not ecritures:
        print("  ❌ Aucune écriture de bilan d'ouverture 2024")
    else:
        print(f"  Trouvé {len(ecritures)} écriture(s):")
        total_89_debit = 0
        total_89_credit = 0
        for ec in ecritures:
            prefix = "Déb 89" if ec[2] == '89' else "Cré 89"
            compte = ec[3] if ec[2] == '89' else ec[2]
            print(f"    {prefix} | Compte {compte} | {ec[4]:>12,.2f}€ | {ec[5][:40]}")
            if ec[2] == '89':
                total_89_debit += float(ec[4])
            else:
                total_89_credit += float(ec[4])

        print(f"  ---")
        print(f"  Total 89 débité:  {total_89_debit:>12,.2f}€")
        print(f"  Total 89 crédité: {total_89_credit:>12,.2f}€")
        print(f"  Équilibre:        {total_89_debit - total_89_credit:>12,.2f}€ (doit être 0)")

    print()
    print("=" * 80)

except Exception as e:
    print(f"❌ Erreur : {e}")
    import traceback
    traceback.print_exc()

finally:
    session.close()
