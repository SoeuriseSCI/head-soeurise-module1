#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIGRATION - Enrichissement Événements Comptables
================================================
Ajoute les colonnes nécessaires pour la gestion complète des événements comptables
et crée les nouvelles tables pour le portefeuille et comptes courants.

Date: 05/11/2025
Auteur: Module Phase 1 - Accounting Events

MODIFICATIONS:
- Enrichissement table evenements_comptables
- Création table portefeuille_valeurs_mobilieres
- Création table mouvements_portefeuille
- Création table comptes_courants_associes
- Création table mouvements_comptes_courants
"""

import os
import sys
from sqlalchemy import text, create_engine

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("❌ ERREUR: Variable d'environnement DATABASE_URL non définie")
    sys.exit(1)

# Fix Render PostgreSQL URL
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTION DE MIGRATION
# ═══════════════════════════════════════════════════════════════════════════════

def migrate_database():
    """
    Applique les migrations à la base de données
    """
    print("🔧 DÉBUT DE LA MIGRATION")
    print(f"📊 Base de données: {DATABASE_URL[:50]}...")
    print()

    engine = create_engine(DATABASE_URL, echo=False)

    with engine.connect() as conn:
        # ═══════════════════════════════════════════════════════════════
        # ÉTAPE 1: Enrichir la table evenements_comptables
        # ═══════════════════════════════════════════════════════════════
        print("📝 ÉTAPE 1: Enrichissement table evenements_comptables")

        # Vérifier si les colonnes existent déjà
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'evenements_comptables'
        """))
        existing_columns = [row[0] for row in result]

        # Ajouter les nouvelles colonnes si elles n'existent pas
        new_columns = [
            ("date_operation", "DATE", "Date réelle de l'opération (extraite du PDF)"),
            ("libelle", "VARCHAR(500)", "Libellé de l'opération (extrait du relevé)"),
            ("libelle_normalise", "VARCHAR(500)", "Libellé normalisé pour comparaison"),
            ("montant", "NUMERIC(15, 2)", "Montant de l'opération"),
            ("type_operation", "VARCHAR(20)", "Type: DEBIT ou CREDIT"),
            ("fingerprint", "VARCHAR(64)", "Empreinte MD5 pour détection doublons"),
            ("phase_traitement", "INTEGER", "Phase ayant traité l'événement (1, 2, 3)"),
        ]

        for col_name, col_type, col_desc in new_columns:
            if col_name not in existing_columns:
                try:
                    conn.execute(text(f"ALTER TABLE evenements_comptables ADD COLUMN {col_name} {col_type}"))
                    conn.commit()
                    print(f"  ✅ Colonne '{col_name}' ajoutée ({col_desc})")
                except Exception as e:
                    print(f"  ⚠️  Colonne '{col_name}' non ajoutée: {e}")
            else:
                print(f"  ℹ️  Colonne '{col_name}' existe déjà")

        # Ajouter contrainte unique sur fingerprint
        try:
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_fingerprint_unique ON evenements_comptables(fingerprint)"))
            conn.commit()
            print("  ✅ Index unique sur 'fingerprint' créé")
        except Exception as e:
            print(f"  ⚠️  Index fingerprint non créé: {e}")

        # Ajouter index sur phase_traitement
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_phase_traitement ON evenements_comptables(phase_traitement)"))
            conn.commit()
            print("  ✅ Index sur 'phase_traitement' créé")
        except Exception as e:
            print(f"  ⚠️  Index phase_traitement non créé: {e}")

        print()

        # ═══════════════════════════════════════════════════════════════
        # ÉTAPE 2: Créer les nouvelles tables
        # ═══════════════════════════════════════════════════════════════
        print("📝 ÉTAPE 2: Création des nouvelles tables")

        # Créer les tables manuellement avec SQL brut
        # Table 1: portefeuille_valeurs_mobilieres
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS portefeuille_valeurs_mobilieres (
                    id SERIAL PRIMARY KEY,
                    code_isin VARCHAR(20),
                    code_ticker VARCHAR(20),
                    libelle VARCHAR(255) NOT NULL,
                    type_valeur VARCHAR(50) NOT NULL,
                    quantite NUMERIC(15, 4) NOT NULL DEFAULT 0,
                    prix_moyen_acquisition NUMERIC(15, 4) NOT NULL,
                    valeur_comptable NUMERIC(15, 2) NOT NULL,
                    compte_comptable VARCHAR(10) NOT NULL,
                    date_premiere_acquisition DATE NOT NULL,
                    date_derniere_operation DATE,
                    courtier VARCHAR(100),
                    actif BOOLEAN DEFAULT TRUE,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            print("  ✅ Table 'portefeuille_valeurs_mobilieres' créée")
        except Exception as e:
            print(f"  ℹ️  Table 'portefeuille_valeurs_mobilieres' existe déjà ou erreur: {e}")

        # Table 2: mouvements_portefeuille
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS mouvements_portefeuille (
                    id SERIAL PRIMARY KEY,
                    portefeuille_id INTEGER NOT NULL REFERENCES portefeuille_valeurs_mobilieres(id),
                    type_mouvement VARCHAR(20) NOT NULL,
                    date_operation DATE NOT NULL,
                    quantite NUMERIC(15, 4) NOT NULL,
                    prix_unitaire NUMERIC(15, 4) NOT NULL,
                    montant_total NUMERIC(15, 2) NOT NULL,
                    frais NUMERIC(15, 2) DEFAULT 0,
                    nouveau_pru NUMERIC(15, 4),
                    nouvelle_quantite NUMERIC(15, 4),
                    plus_ou_moins_value NUMERIC(15, 2),
                    source_evenement_id INTEGER REFERENCES evenements_comptables(id),
                    ecriture_comptable_id INTEGER REFERENCES ecritures_comptables(id),
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            print("  ✅ Table 'mouvements_portefeuille' créée")
        except Exception as e:
            print(f"  ℹ️  Table 'mouvements_portefeuille' existe déjà ou erreur: {e}")

        # Index pour mouvements_portefeuille
        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_portefeuille_date
                ON mouvements_portefeuille(portefeuille_id, date_operation)
            """))
            conn.commit()
            print("  ✅ Index 'idx_portefeuille_date' créé")
        except Exception as e:
            print(f"  ℹ️  Index 'idx_portefeuille_date' existe déjà: {e}")

        # Table 3: comptes_courants_associes
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS comptes_courants_associes (
                    id SERIAL PRIMARY KEY,
                    nom_associe VARCHAR(255) NOT NULL UNIQUE,
                    compte_comptable VARCHAR(10) NOT NULL,
                    solde_actuel NUMERIC(15, 2) NOT NULL DEFAULT 0,
                    date_ouverture DATE NOT NULL,
                    date_derniere_operation DATE,
                    actif BOOLEAN DEFAULT TRUE,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            print("  ✅ Table 'comptes_courants_associes' créée")
        except Exception as e:
            print(f"  ℹ️  Table 'comptes_courants_associes' existe déjà ou erreur: {e}")

        # Table 4: mouvements_comptes_courants
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS mouvements_comptes_courants (
                    id SERIAL PRIMARY KEY,
                    compte_courant_id INTEGER NOT NULL REFERENCES comptes_courants_associes(id),
                    type_mouvement VARCHAR(20) NOT NULL,
                    date_operation DATE NOT NULL,
                    montant NUMERIC(15, 2) NOT NULL,
                    nouveau_solde NUMERIC(15, 2) NOT NULL,
                    source_evenement_id INTEGER REFERENCES evenements_comptables(id),
                    ecriture_comptable_id INTEGER REFERENCES ecritures_comptables(id),
                    libelle VARCHAR(255),
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            print("  ✅ Table 'mouvements_comptes_courants' créée")
        except Exception as e:
            print(f"  ℹ️  Table 'mouvements_comptes_courants' existe déjà ou erreur: {e}")

        # Index pour mouvements_comptes_courants
        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_cc_date
                ON mouvements_comptes_courants(compte_courant_id, date_operation)
            """))
            conn.commit()
            print("  ✅ Index 'idx_cc_date' créé")
        except Exception as e:
            print(f"  ℹ️  Index 'idx_cc_date' existe déjà: {e}")

        print()

    print("✅ MIGRATION TERMINÉE")
    print()

    # Afficher statistiques
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM evenements_comptables"))
        count_events = result.fetchone()[0]
        print(f"📊 Statistiques:")
        print(f"   - Événements comptables: {count_events}")
        print()


def rollback_migration():
    """
    ROLLBACK: Annule les migrations (pour tests)
    ⚠️ ATTENTION: Cette fonction supprime les colonnes et tables créées
    """
    print("⚠️  ROLLBACK DE LA MIGRATION")
    print()

    response = input("Êtes-vous sûr de vouloir annuler la migration? (oui/non): ")
    if response.lower() != 'oui':
        print("❌ Rollback annulé")
        return

    engine = create_engine(DATABASE_URL, echo=False)

    with engine.connect() as conn:
        print("🗑️  Suppression des colonnes ajoutées...")

        columns_to_drop = [
            'date_operation',
            'libelle',
            'libelle_normalise',
            'montant',
            'type_operation',
            'fingerprint',
            'phase_traitement'
        ]

        for col_name in columns_to_drop:
            try:
                conn.execute(text(f"ALTER TABLE evenements_comptables DROP COLUMN IF EXISTS {col_name}"))
                conn.commit()
                print(f"  ✅ Colonne '{col_name}' supprimée")
            except Exception as e:
                print(f"  ⚠️  Colonne '{col_name}' non supprimée: {e}")

        print()
        print("🗑️  Suppression des nouvelles tables...")

        tables_to_drop = [
            'mouvements_comptes_courants',
            'mouvements_portefeuille',
            'comptes_courants_associes',
            'portefeuille_valeurs_mobilieres'
        ]

        for table_name in tables_to_drop:
            try:
                conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
                conn.commit()
                print(f"  ✅ Table '{table_name}' supprimée")
            except Exception as e:
                print(f"  ⚠️  Table '{table_name}' non supprimée: {e}")

        print()

    print("✅ ROLLBACK TERMINÉ")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--rollback':
        rollback_migration()
    else:
        migrate_database()
