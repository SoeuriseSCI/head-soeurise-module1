#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCRIPT: Marquer les soldes d'ouverture existants
================================================
Marque tous les événements avec "ANCIEN SOLDE" comme type SOLDE_OUVERTURE

Date: 05/11/2025
Auteur: Claude Code Assistant
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("❌ Variable DATABASE_URL non définie")
    exit(1)

# Connexion
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

print()
print("=" * 80)
print("MARQUAGE DES SOLDES D'OUVERTURE")
print("=" * 80)
print()

try:
    # Récupérer les événements avec "ANCIEN SOLDE"
    result = session.execute(text("""
        SELECT id, date_operation, libelle, montant
        FROM evenements_comptables
        WHERE libelle_normalise LIKE '%ancien solde%'
           OR libelle_normalise LIKE '%solde reporte%'
           OR libelle_normalise LIKE '%solde precedent%'
           OR libelle_normalise LIKE '%report solde%'
    """))

    evenements = result.fetchall()

    if not evenements:
        print("✅ Aucun solde d'ouverture à marquer")
        session.close()
        exit(0)

    print(f"🔍 {len(evenements)} soldes d'ouverture détectés:")
    print()

    for evt in evenements:
        print(f"  #{evt[0]:3d} | {evt[1]} | {evt[2][:50]:50s} | {evt[3]:>10.2f}€")

    print()
    print("-" * 80)
    print()

    # Marquer comme SOLDE_OUVERTURE
    result = session.execute(text("""
        UPDATE evenements_comptables
        SET type_evenement = 'SOLDE_OUVERTURE',
            updated_at = NOW()
        WHERE libelle_normalise LIKE '%ancien solde%'
           OR libelle_normalise LIKE '%solde reporte%'
           OR libelle_normalise LIKE '%solde precedent%'
           OR libelle_normalise LIKE '%report solde%'
    """))

    session.commit()
    nb_updated = result.rowcount

    print(f"✅ {nb_updated} événements marqués comme SOLDE_OUVERTURE")
    print()

    # Afficher les statistiques
    result = session.execute(text("""
        SELECT type_evenement, COUNT(*) as nb
        FROM evenements_comptables
        GROUP BY type_evenement
        ORDER BY nb DESC
    """))

    print("📊 Répartition par type:")
    print()
    for row in result:
        type_evt = row[0] or "(non détecté)"
        print(f"  {type_evt:30s}: {row[1]:3d}")

    print()
    print("=" * 80)
    print("✅ TERMINÉ")
    print("=" * 80)
    print()

except Exception as e:
    print(f"❌ Erreur: {e}")
    session.rollback()
    import traceback
    traceback.print_exc()
finally:
    session.close()
