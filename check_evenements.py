#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de vérification des événements présents dans la base
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
    result = conn.execute(text("""
        SELECT
            id,
            email_id,
            email_from,
            email_date,
            email_subject,
            date_operation,
            libelle,
            montant,
            type_operation,
            type_evenement,
            statut,
            fingerprint,
            phase_traitement,
            created_at
        FROM evenements_comptables
        ORDER BY id
    """))

    evenements = result.fetchall()

    print(f"📊 Total événements: {len(evenements)}")
    print()

    for evt in evenements:
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"🔹 Événement #{evt[0]}")
        print(f"   Email ID: {evt[1]}")
        print(f"   Email From: {evt[2]}")
        print(f"   Email Date: {evt[3]}")
        print(f"   Email Subject: {evt[4]}")
        print(f"   Date opération: {evt[5]}")
        print(f"   Libellé: {evt[6]}")
        print(f"   Montant: {evt[7]}€")
        print(f"   Type opération: {evt[8]}")
        print(f"   Type événement: {evt[9]}")
        print(f"   Statut: {evt[10]}")
        print(f"   Fingerprint: {evt[11]}")
        print(f"   Phase traitement: {evt[12]}")
        print(f"   Créé le: {evt[13]}")
        print()
