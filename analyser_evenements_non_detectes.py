#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANALYSE DES ÉVÉNEMENTS NON DÉTECTÉS
===================================
Analyse les événements sans type_evenement pour identifier les patterns

Date: 06/11/2025
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from collections import Counter

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
print("ANALYSE DES ÉVÉNEMENTS NON DÉTECTÉS")
print("=" * 80)
print()

try:
    # Récupérer les événements non détectés
    result = session.execute(text("""
        SELECT id, date_operation, libelle, libelle_normalise, montant, type_operation
        FROM evenements_comptables
        WHERE type_evenement IS NULL
        ORDER BY date_operation, id
    """))

    evenements = result.fetchall()

    if not evenements:
        print("✅ Aucun événement non détecté")
        session.close()
        exit(0)

    print(f"🔍 {len(evenements)} événements non détectés:")
    print()

    # Afficher tous les événements
    for evt in evenements:
        type_op_symbol = "💳" if evt[5] == "DEBIT" else "💰"
        print(f"{type_op_symbol} #{evt[0]:3d} | {evt[1]} | {evt[2][:60]:60s} | {evt[4]:>10.2f}€")

    print()
    print("-" * 80)
    print()

    # Analyser les patterns dans les libellés normalisés
    print("📊 ANALYSE DES PATTERNS:")
    print()

    # Extraire les mots-clés
    mots_cles = []
    for evt in evenements:
        libelle_norm = evt[3] or ""
        # Découper en mots
        mots = libelle_norm.split()
        # Garder les mots significatifs (> 3 caractères)
        mots_significatifs = [m for m in mots if len(m) > 3]
        mots_cles.extend(mots_significatifs[:3])  # 3 premiers mots de chaque libellé

    # Compter les occurrences
    counter = Counter(mots_cles)

    print("Mots-clés les plus fréquents:")
    for mot, count in counter.most_common(20):
        print(f"  {mot:30s}: {count:3d}")

    print()
    print("-" * 80)
    print()

    # Grouper par patterns manuels
    patterns = {
        'FRAIS_BANCAIRES': [],
        'HONORAIRES': [],
        'ACHATS_ETF': [],
        'ACHATS_AMAZON': [],
        'APPORTS_ULRIK': [],
        'VIREMENTS': [],
        'PRELEVEMENTS': [],
        'AUTRES': []
    }

    for evt in evenements:
        libelle_norm = evt[3] or ""

        if 'frais' in libelle_norm or 'cotisation' in libelle_norm:
            patterns['FRAIS_BANCAIRES'].append(evt)
        elif 'comptable' in libelle_norm or 'honoraire' in libelle_norm:
            patterns['HONORAIRES'].append(evt)
        elif 'degiro' in libelle_norm or 'interactive' in libelle_norm or 'etf' in libelle_norm:
            patterns['ACHATS_ETF'].append(evt)
        elif 'amazon' in libelle_norm:
            patterns['ACHATS_AMAZON'].append(evt)
        elif 'bergsten' in libelle_norm and 'vir' in libelle_norm and evt[5] == 'CREDIT':
            patterns['APPORTS_ULRIK'].append(evt)
        elif 'vir' in libelle_norm or 'virement' in libelle_norm:
            patterns['VIREMENTS'].append(evt)
        elif 'prlv' in libelle_norm or 'prelevement' in libelle_norm:
            patterns['PRELEVEMENTS'].append(evt)
        else:
            patterns['AUTRES'].append(evt)

    print("📋 RÉPARTITION PAR TYPE:")
    print()
    for type_pattern, evts in patterns.items():
        if evts:
            print(f"{type_pattern:20s}: {len(evts):3d} événements")
            for evt in evts[:3]:  # Afficher les 3 premiers exemples
                print(f"    • {evt[2][:70]}")
            if len(evts) > 3:
                print(f"    ... et {len(evts) - 3} autres")
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
