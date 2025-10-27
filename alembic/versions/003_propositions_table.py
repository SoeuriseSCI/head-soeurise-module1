"""Ajout table propositions_en_attente pour workflow validation

Revision ID: 003
Revises: 002
Create Date: 2025-10-27

Cette table permet de stocker les propositions d'écritures en attente de validation
et de valider via token uniquement (sans avoir à renvoyer le JSON complet).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '003'
down_revision = '002'


def upgrade():
    """Crée la table propositions_en_attente"""

    op.execute("""
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
    """)

    # Index sur le token pour recherche rapide
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_propositions_token
        ON propositions_en_attente(token);
    """)

    # Index sur le statut pour filtrage
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_propositions_statut
        ON propositions_en_attente(statut);
    """)

    # Index sur la date de création pour nettoyage des anciennes propositions
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_propositions_created
        ON propositions_en_attente(created_at);
    """)

    print("✅ Migration 003 : Table propositions_en_attente créée avec succès")


def downgrade():
    """Supprime la table propositions_en_attente"""

    op.execute("""
        DROP TABLE IF EXISTS propositions_en_attente CASCADE;
    """)

    print("⏪ Migration 003 : Table propositions_en_attente supprimée")
