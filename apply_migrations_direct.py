#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Application directe des migrations en SQL
"""
import psycopg2
import os

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL non défini")
    exit(1)

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

print("🔧 Application des migrations...")
print()

# ═══════════════════════════════════════════════════════════════════════════════
# MIGRATION 002 - Synchronisation Schéma
# ═══════════════════════════════════════════════════════════════════════════════

print("📦 Migration 002: Synchronisation schéma")

# ecritures_comptables (11 colonnes)
cur.execute("""
    ALTER TABLE ecritures_comptables
    ADD COLUMN IF NOT EXISTS date_enregistrement TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS source_email_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS source_email_date TIMESTAMP,
    ADD COLUMN IF NOT EXISTS source_email_from VARCHAR(255),
    ADD COLUMN IF NOT EXISTS type_ecriture VARCHAR(50),
    ADD COLUMN IF NOT EXISTS piece_jointe VARCHAR(255),
    ADD COLUMN IF NOT EXISTS notes TEXT,
    ADD COLUMN IF NOT EXISTS valide BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS validee_par VARCHAR(255),
    ADD COLUMN IF NOT EXISTS validee_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
""")
print("  ✓ ecritures_comptables: 11 colonnes")

# evenements_comptables (8 colonnes)
cur.execute("""
    ALTER TABLE evenements_comptables
    ADD COLUMN IF NOT EXISTS email_subject VARCHAR(255),
    ADD COLUMN IF NOT EXISTS type_evenement VARCHAR(100),
    ADD COLUMN IF NOT EXISTS est_comptable BOOLEAN,
    ADD COLUMN IF NOT EXISTS statut VARCHAR(50) DEFAULT 'EN_ATTENTE',
    ADD COLUMN IF NOT EXISTS message_erreur TEXT,
    ADD COLUMN IF NOT EXISTS ecritures_creees INTEGER[],
    ADD COLUMN IF NOT EXISTS traite_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
""")
print("  ✓ evenements_comptables: 8 colonnes")

# immobilisations (5 colonnes)
cur.execute("""
    ALTER TABLE immobilisations
    ADD COLUMN IF NOT EXISTS description TEXT,
    ADD COLUMN IF NOT EXISTS taux_degressif NUMERIC(5, 2),
    ADD COLUMN IF NOT EXISTS source_email_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS source_email_date TIMESTAMP,
    ADD COLUMN IF NOT EXISTS actif BOOLEAN DEFAULT TRUE;
""")
print("  ✓ immobilisations: 5 colonnes")

# calculs_amortissements (6 colonnes)
cur.execute("""
    ALTER TABLE calculs_amortissements
    ADD COLUMN IF NOT EXISTS source_email_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS source_calcul_date TIMESTAMP,
    ADD COLUMN IF NOT EXISTS base_amortissable NUMERIC(12, 2),
    ADD COLUMN IF NOT EXISTS taux_applique NUMERIC(5, 2),
    ADD COLUMN IF NOT EXISTS ecriture_id INTEGER REFERENCES ecritures_comptables(id),
    ADD COLUMN IF NOT EXISTS notes TEXT;
""")
print("  ✓ calculs_amortissements: 6 colonnes")

# balances_mensuelles (5 colonnes)
cur.execute("""
    ALTER TABLE balances_mensuelles
    ADD COLUMN IF NOT EXISTS solde_debit NUMERIC(12, 2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS solde_credit NUMERIC(12, 2) DEFAULT 0,
    ADD COLUMN IF NOT EXISTS nb_operations INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS derniere_operation TIMESTAMP,
    ADD COLUMN IF NOT EXISTS recalcule_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
""")
print("  ✓ balances_mensuelles: 5 colonnes")

# rapports_comptables (3 colonnes)
cur.execute("""
    ALTER TABLE rapports_comptables
    ADD COLUMN IF NOT EXISTS contenu_json JSONB,
    ADD COLUMN IF NOT EXISTS genere_par VARCHAR(255),
    ADD COLUMN IF NOT EXISTS genere_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
""")
print("  ✓ rapports_comptables: 3 colonnes")

conn.commit()
print()
print("✅ Migration 002 appliquée (37 colonnes ajoutées)")
print()

# ═══════════════════════════════════════════════════════════════════════════════
# MIGRATION 003 - Table Propositions
# ═══════════════════════════════════════════════════════════════════════════════

print("📦 Migration 003: Table propositions_en_attente")

cur.execute("""
    CREATE TABLE IF NOT EXISTS propositions_en_attente (
        id SERIAL PRIMARY KEY,
        token VARCHAR(50) UNIQUE NOT NULL,
        type_evenement VARCHAR(100) NOT NULL,
        email_id VARCHAR(255),
        email_from VARCHAR(255),
        email_date TIMESTAMP,
        email_subject VARCHAR(255),
        propositions_json JSONB NOT NULL,
        statut VARCHAR(50) DEFAULT 'EN_ATTENTE',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        validee_at TIMESTAMP,
        validee_par VARCHAR(255),
        notes TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_propositions_token ON propositions_en_attente(token);
    CREATE INDEX IF NOT EXISTS idx_propositions_statut ON propositions_en_attente(statut);
    CREATE INDEX IF NOT EXISTS idx_propositions_created ON propositions_en_attente(created_at);
""")

print("  ✓ Table créée")
print("  ✓ 3 index créés")

conn.commit()
print()
print("✅ Migration 003 appliquée")
print()

cur.close()
conn.close()

print("=" * 80)
print("🎉 TOUTES LES MIGRATIONS SONT APPLIQUÉES !")
print("=" * 80)
print()
print("Exécutez maintenant: python verify_schema.py")
