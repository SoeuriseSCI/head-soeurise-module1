"""Synchronisation schéma BD avec modèles Python

Revision ID: 002
Revises: 001
Create Date: 2025-10-27

Ajoute les colonnes manquantes pour correspondre aux modèles dans models_module2.py
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '002'
down_revision = '001'


def upgrade():
    """Ajoute les colonnes manquantes dans toutes les tables"""

    # ═══════════════════════════════════════════════════════════════════════════════
    # TABLE: ecritures_comptables (11 colonnes à ajouter)
    # ═══════════════════════════════════════════════════════════════════════════════
    op.execute("""
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

    # ═══════════════════════════════════════════════════════════════════════════════
    # TABLE: evenements_comptables (7 colonnes à ajouter)
    # ═══════════════════════════════════════════════════════════════════════════════
    op.execute("""
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

    # ═══════════════════════════════════════════════════════════════════════════════
    # TABLE: immobilisations (5 colonnes à ajouter)
    # ═══════════════════════════════════════════════════════════════════════════════
    op.execute("""
        ALTER TABLE immobilisations
        ADD COLUMN IF NOT EXISTS description TEXT,
        ADD COLUMN IF NOT EXISTS taux_degressif NUMERIC(5, 2),
        ADD COLUMN IF NOT EXISTS source_email_id VARCHAR(255),
        ADD COLUMN IF NOT EXISTS source_email_date TIMESTAMP,
        ADD COLUMN IF NOT EXISTS actif BOOLEAN DEFAULT TRUE;
    """)

    # ═══════════════════════════════════════════════════════════════════════════════
    # TABLE: calculs_amortissements (6 colonnes à ajouter)
    # ═══════════════════════════════════════════════════════════════════════════════
    op.execute("""
        ALTER TABLE calculs_amortissements
        ADD COLUMN IF NOT EXISTS source_email_id VARCHAR(255),
        ADD COLUMN IF NOT EXISTS source_calcul_date TIMESTAMP,
        ADD COLUMN IF NOT EXISTS base_amortissable NUMERIC(12, 2),
        ADD COLUMN IF NOT EXISTS taux_applique NUMERIC(5, 2),
        ADD COLUMN IF NOT EXISTS ecriture_id INTEGER REFERENCES ecritures_comptables(id),
        ADD COLUMN IF NOT EXISTS notes TEXT;
    """)

    # ═══════════════════════════════════════════════════════════════════════════════
    # TABLE: balances_mensuelles (5 colonnes à ajouter)
    # ═══════════════════════════════════════════════════════════════════════════════
    op.execute("""
        ALTER TABLE balances_mensuelles
        ADD COLUMN IF NOT EXISTS solde_debit NUMERIC(12, 2) DEFAULT 0,
        ADD COLUMN IF NOT EXISTS solde_credit NUMERIC(12, 2) DEFAULT 0,
        ADD COLUMN IF NOT EXISTS nb_operations INTEGER DEFAULT 0,
        ADD COLUMN IF NOT EXISTS derniere_operation TIMESTAMP,
        ADD COLUMN IF NOT EXISTS recalcule_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    """)

    # ═══════════════════════════════════════════════════════════════════════════════
    # TABLE: rapports_comptables (3 colonnes à ajouter)
    # ═══════════════════════════════════════════════════════════════════════════════
    op.execute("""
        ALTER TABLE rapports_comptables
        ADD COLUMN IF NOT EXISTS contenu_json JSONB,
        ADD COLUMN IF NOT EXISTS genere_par VARCHAR(255),
        ADD COLUMN IF NOT EXISTS genere_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    """)

    print("✅ Migration 002 : Toutes les colonnes manquantes ont été ajoutées")


def downgrade():
    """Supprime les colonnes ajoutées (pour rollback)"""

    # ecritures_comptables
    op.execute("""
        ALTER TABLE ecritures_comptables
        DROP COLUMN IF EXISTS date_enregistrement,
        DROP COLUMN IF EXISTS source_email_id,
        DROP COLUMN IF EXISTS source_email_date,
        DROP COLUMN IF EXISTS source_email_from,
        DROP COLUMN IF EXISTS type_ecriture,
        DROP COLUMN IF EXISTS piece_jointe,
        DROP COLUMN IF EXISTS notes,
        DROP COLUMN IF EXISTS valide,
        DROP COLUMN IF EXISTS validee_par,
        DROP COLUMN IF EXISTS validee_at,
        DROP COLUMN IF EXISTS updated_at;
    """)

    # evenements_comptables
    op.execute("""
        ALTER TABLE evenements_comptables
        DROP COLUMN IF EXISTS email_subject,
        DROP COLUMN IF EXISTS type_evenement,
        DROP COLUMN IF EXISTS est_comptable,
        DROP COLUMN IF EXISTS statut,
        DROP COLUMN IF EXISTS message_erreur,
        DROP COLUMN IF EXISTS ecritures_creees,
        DROP COLUMN IF EXISTS traite_at,
        DROP COLUMN IF EXISTS updated_at;
    """)

    # immobilisations
    op.execute("""
        ALTER TABLE immobilisations
        DROP COLUMN IF EXISTS description,
        DROP COLUMN IF EXISTS taux_degressif,
        DROP COLUMN IF EXISTS source_email_id,
        DROP COLUMN IF EXISTS source_email_date,
        DROP COLUMN IF EXISTS actif;
    """)

    # calculs_amortissements
    op.execute("""
        ALTER TABLE calculs_amortissements
        DROP COLUMN IF EXISTS source_email_id,
        DROP COLUMN IF EXISTS source_calcul_date,
        DROP COLUMN IF EXISTS base_amortissable,
        DROP COLUMN IF EXISTS taux_applique,
        DROP COLUMN IF EXISTS ecriture_id,
        DROP COLUMN IF EXISTS notes;
    """)

    # balances_mensuelles
    op.execute("""
        ALTER TABLE balances_mensuelles
        DROP COLUMN IF EXISTS solde_debit,
        DROP COLUMN IF EXISTS solde_credit,
        DROP COLUMN IF EXISTS nb_operations,
        DROP COLUMN IF EXISTS derniere_operation,
        DROP COLUMN IF EXISTS recalcule_at;
    """)

    # rapports_comptables
    op.execute("""
        ALTER TABLE rapports_comptables
        DROP COLUMN IF EXISTS contenu_json,
        DROP COLUMN IF EXISTS genere_par,
        DROP COLUMN IF EXISTS genere_at;
    """)

    print("⏪ Migration 002 : Rollback effectué")
