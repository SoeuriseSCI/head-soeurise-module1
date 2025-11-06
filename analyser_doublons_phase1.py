#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANALYSE DES DOUBLONS PHASE 1
============================
Détecte les doublons dans REMBOURSEMENT_PRET et REVENU_SCPI
Identifie les opérations de décembre 2023 (déjà dans bilan)

Date: 06/11/2025
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from collections import defaultdict
from datetime import date

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
print("ANALYSE DES DOUBLONS PHASE 1")
print("=" * 80)
print()

try:
    # Récupérer les événements Phase 1
    result = session.execute(text("""
        SELECT id, date_operation, libelle, montant, type_operation, type_evenement,
               LENGTH(libelle) as libelle_length
        FROM evenements_comptables
        WHERE type_evenement IN ('REMBOURSEMENT_PRET', 'REVENU_SCPI')
        ORDER BY date_operation, type_evenement, montant
    """))

    evenements = result.fetchall()

    if not evenements:
        print("✅ Aucun événement Phase 1")
        session.close()
        exit(0)

    print(f"🔍 {len(evenements)} événements Phase 1:")
    print()

    # Séparer par type
    by_type = defaultdict(list)
    for evt in evenements:
        by_type[evt[5]].append(evt)

    # Analyser chaque type
    for type_evt, evts in by_type.items():
        print(f"📊 {type_evt}: {len(evts)} événements")
        print("-" * 80)
        print()

        # Grouper par (date, montant arrondi)
        groups = defaultdict(list)
        for evt in evts:
            key = (evt[1], round(float(evt[3]), 2))  # (date, montant)
            groups[key].append(evt)

        # Identifier les doublons
        doublons = {k: v for k, v in groups.items() if len(v) > 1}

        if doublons:
            print(f"⚠️  {len(doublons)} groupes de doublons détectés:")
            print()

            for (date_op, montant), groupe in doublons.items():
                print(f"   📅 {date_op} | {montant:.2f}€ → {len(groupe)} occurrences")

                for evt in groupe:
                    # Marquer le plus détaillé
                    detail_score = evt[6]  # longueur du libellé
                    marker = "📝" if detail_score == max(e[6] for e in groupe) else "  "

                    print(f"      {marker} #{evt[0]:3d} | {evt[2][:70]}")
                    print(f"         Longueur: {detail_score} caractères")

                print()

            print(f"   💡 Recommandation: Garder les événements marqués 📝 (plus détaillés)")
            print()
        else:
            print("   ✅ Aucun doublon détecté")
            print()

    # Identifier les opérations de décembre 2023
    print("=" * 80)
    print("OPÉRATIONS DÉCEMBRE 2023 (déjà dans bilan d'ouverture)")
    print("=" * 80)
    print()

    result_dec = session.execute(text("""
        SELECT id, date_operation, libelle, montant, type_operation, type_evenement
        FROM evenements_comptables
        WHERE date_operation >= '2023-12-01'
          AND date_operation < '2024-01-01'
          AND type_evenement IS NOT NULL
          AND type_evenement != 'SOLDE_OUVERTURE'
        ORDER BY date_operation
    """))

    evenements_dec = result_dec.fetchall()

    if evenements_dec:
        print(f"⚠️  {len(evenements_dec)} opérations de décembre 2023:")
        print()

        for evt in evenements_dec:
            type_op_symbol = "💳" if evt[4] == "DEBIT" else "💰"
            print(f"{type_op_symbol} #{evt[0]:3d} | {evt[1]} | {evt[5]:20s} | {evt[2][:50]:50s} | {evt[3]:>10.2f}€")

        print()
        print("💡 Ces opérations ont probablement été intégrées dans le bilan d'ouverture 2023")
        print("   → Vérifier si elles doivent être supprimées ou marquées comme DEJA_DANS_BILAN")
    else:
        print("✅ Aucune opération de décembre 2023")

    print()
    print("=" * 80)
    print()

    # Résumé des actions recommandées
    print("📋 RÉSUMÉ DES ACTIONS RECOMMANDÉES:")
    print()

    total_doublons = sum(len(v) - 1 for v in doublons.values())
    print(f"1. Supprimer {total_doublons} doublons (garder les plus détaillés)")
    print(f"2. Traiter {len(evenements_dec)} opérations de décembre 2023")
    print()
    print("💡 Créer un script de nettoyage pour automatiser ces actions")

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
