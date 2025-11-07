#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Résumé de l'état de la base comptable
"""
import os
from sqlalchemy import text, create_engine

DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

if not DATABASE_URL:
    print("❌ Variable DATABASE_URL non définie")
    exit(1)

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    print("=" * 80)
    print("ÉTAT DE LA BASE COMPTABLE")
    print("=" * 80)
    print()

    # Exercices
    result = conn.execute(text('SELECT * FROM exercices_comptables'))
    exercices = result.fetchall()
    print(f'📅 EXERCICES COMPTABLES: {len(exercices)}')
    for ex in exercices:
        print(f'   • ID {ex[0]}: {ex[1]} → {ex[2]} ({ex[3]})')
    print()

    # Écritures comptables
    result = conn.execute(text('''
        SELECT COUNT(*), SUM(montant_debit), SUM(montant_credit)
        FROM ecritures_comptables
    '''))
    row = result.fetchone()
    print(f'📝 ÉCRITURES COMPTABLES: {row[0]}')
    print(f'   • Débit total: {row[1]:.2f}€')
    print(f'   • Crédit total: {row[2]:.2f}€')
    print(f'   • Équilibre: {abs(row[1] - row[2]):.2f}€ {"✅" if abs(row[1] - row[2]) < 0.01 else "❌"}')
    print()

    # Prêts
    result = conn.execute(text('''
        SELECT id, numero_pret, montant_initial, taux_annuel, duree_mois
        FROM prets_immobiliers
    '''))
    prets = result.fetchall()
    print(f'🏦 PRÊTS IMMOBILIERS: {len(prets)}')
    for p in prets:
        print(f'   • #{p[0]}: {p[1]} - {p[2]:,.0f}€ @ {p[3]}% sur {p[4]} mois')
    print()

    # Échéances
    result = conn.execute(text('SELECT COUNT(*) FROM echeances_prets'))
    nb_ech = result.fetchone()[0]
    print(f'📆 ÉCHÉANCES: {nb_ech}')
    print()

    # Événements
    result = conn.execute(text('''
        SELECT COUNT(*), COUNT(CASE WHEN type_evenement IS NOT NULL THEN 1 END)
        FROM evenements_comptables
    '''))
    evt = result.fetchone()
    print(f'📊 ÉVÉNEMENTS COMPTABLES: {evt[0]} ({evt[1]} typés)')

    # Par type
    result = conn.execute(text('''
        SELECT type_evenement, COUNT(*)
        FROM evenements_comptables
        WHERE type_evenement IS NOT NULL
        GROUP BY type_evenement
        ORDER BY COUNT(*) DESC
    '''))
    print('   Par type:')
    for row in result:
        print(f'      • {row[0]}: {row[1]}')
    print()

    # Propositions en attente
    result = conn.execute(text('SELECT COUNT(*) FROM propositions_en_attente'))
    nb_prop = result.fetchone()[0]
    print(f'⏳ PROPOSITIONS EN ATTENTE: {nb_prop}')

    if nb_prop > 0:
        result = conn.execute(text('''
            SELECT type_evenement, COUNT(*)
            FROM propositions_en_attente
            GROUP BY type_evenement
            ORDER BY COUNT(*) DESC
        '''))
        print('   Par type:')
        for row in result:
            print(f'      • {row[0]}: {row[1]}')

    print()
    print("=" * 80)
