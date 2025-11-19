#!/usr/bin/env python3
"""
Script de debug pour vérifier les cutoffs existants
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
    print("🔍 RECHERCHE CUTOFFS EXISTANTS")
    print("=" * 80)
    print()

    # 1. Voir les exercices disponibles
    print("📅 Exercices disponibles:")
    query = text("""
        SELECT id, annee, date_debut, date_fin, statut
        FROM exercices_comptables
        ORDER BY annee
    """)
    exercices = session.execute(query).fetchall()
    for ex in exercices:
        print(f"  ID={ex[0]} | Année {ex[1]} | {ex[2]} → {ex[3]} | {ex[4]}")
    print()

    # 2. Chercher écritures 4181 et 4081 en 2023
    print("💰 Écritures comptes 4181 et 4081 en 2023:")
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
          AND EXTRACT(YEAR FROM date_ecriture) = 2023
        ORDER BY date_ecriture DESC
    """)
    ecritures = session.execute(query).fetchall()

    if not ecritures:
        print("  ❌ Aucune écriture trouvée pour 4181/4081 en 2023")
    else:
        print(f"  {'ID':<8} {'Date':<12} {'ExercID':<10} {'Type':<30} {'Débit':<8} {'Crédit':<8} {'Montant':>12} {'Libellé'}")
        print("  " + "-" * 120)
        for ec in ecritures:
            print(f"  {ec[0]:<8} {str(ec[1]):<12} {ec[2] or 'NULL':<10} {ec[3][:30]:<30} "
                  f"{ec[4]:<8} {ec[5]:<8} {ec[6]:>12,.2f}€ {ec[7][:30]}")
    print()

    # 3. Chercher TOUS les cutoffs (peu importe l'année)
    print("📋 TOUS les cutoffs dans la base:")
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
        WHERE type_ecriture LIKE '%CUTOFF%'
        ORDER BY date_ecriture DESC
        LIMIT 20
    """)
    cutoffs = session.execute(query).fetchall()

    if not cutoffs:
        print("  ❌ Aucun cutoff trouvé dans la base")
    else:
        print(f"  {'ID':<8} {'Date':<12} {'ExercID':<10} {'Type':<30} {'Débit':<8} {'Crédit':<8} {'Montant':>12}")
        print("  " + "-" * 120)
        for cf in cutoffs:
            print(f"  {cf[0]:<8} {str(cf[1]):<12} {cf[2] or 'NULL':<10} {cf[3][:30]:<30} "
                  f"{cf[4]:<8} {cf[5]:<8} {cf[6]:>12,.2f}€")
    print()

    # 4. Compter écritures par type pour l'exercice 2023
    print("📊 Types d'écritures pour exercice_id correspondant à 2023:")
    # Trouver l'ID de l'exercice 2023
    query = text("SELECT id FROM exercices_comptables WHERE annee = 2023")
    result = session.execute(query).fetchone()
    if result:
        exercice_2023_id = result[0]
        print(f"  Exercice 2023 a l'ID = {exercice_2023_id}")

        query = text("""
            SELECT type_ecriture, COUNT(*) as nb
            FROM ecritures_comptables
            WHERE exercice_id = :exercice_id
            GROUP BY type_ecriture
            ORDER BY nb DESC
        """)
        types = session.execute(query, {'exercice_id': exercice_2023_id}).fetchall()
        for t in types:
            print(f"    {t[0]:<40} : {t[1]:>4} écritures")
    else:
        print("  ❌ Exercice 2023 non trouvé")

    print()
    print("=" * 80)

except Exception as e:
    print(f"❌ Erreur : {e}")
    import traceback
    traceback.print_exc()

finally:
    session.close()
