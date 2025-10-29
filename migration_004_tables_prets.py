#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIGRATION 004 : Création tables références prêts immobiliers
============================================================

Objectif : Stocker tableaux d'amortissement pour ventilation intérêts/capital

Tables créées :
- prets_immobiliers : Contrats de prêts (identification, montants, durée)
- echeances_prets : Échéancier ligne par ligne (ventilation intérêts/capital)

Usage workflow :
1. Email avec tableau amortissement → Type PRET_IMMOBILIER
2. Parser tableau → Stocker dans prets_immobiliers + echeances_prets
3. Email relevé bancaire → Type CLOTURE_EXERCICE
4. Détecter ligne prêt → Lookup echeances_prets par (pret_id, date)
5. Générer écriture avec ventilation précise intérêts/capital

Date : 27/10/2025
"""

import os
import sys
import psycopg2

# Récupérer DATABASE_URL depuis env
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("❌ ERREUR : DATABASE_URL non défini dans les variables d'environnement")
    sys.exit(1)


def appliquer_migration():
    """Applique la migration 004"""

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        print("🔧 Migration 004 : Création tables prêts immobiliers...")

        # ═══════════════════════════════════════════════════════════════════
        # TABLE 1 : prets_immobiliers (contrats)
        # ═══════════════════════════════════════════════════════════════════

        print("  → Création table prets_immobiliers...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS prets_immobiliers (
                id SERIAL PRIMARY KEY,

                -- Identification
                numero_pret VARCHAR(50) UNIQUE NOT NULL,
                banque VARCHAR(100) NOT NULL,
                libelle VARCHAR(255),

                -- Montants
                montant_initial NUMERIC(15, 2) NOT NULL,
                taux_annuel NUMERIC(6, 4) NOT NULL,

                -- Durée
                duree_mois INTEGER NOT NULL,
                date_debut DATE NOT NULL,
                date_fin DATE NOT NULL,

                -- Type amortissement
                type_amortissement VARCHAR(50) NOT NULL,
                mois_franchise INTEGER DEFAULT 0,

                -- Montants mensuels
                echeance_mensuelle NUMERIC(15, 2),
                interet_mensuel_franchise NUMERIC(15, 2),

                -- Assurance
                assurance_emprunteur BOOLEAN DEFAULT FALSE,
                assures VARCHAR(255),

                -- Source document
                source_email_id VARCHAR(255),
                source_document VARCHAR(500),
                date_ingestion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                -- Métadonnées
                actif BOOLEAN DEFAULT TRUE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Index pour recherche rapide
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_prets_numero
            ON prets_immobiliers(numero_pret);
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_prets_actif
            ON prets_immobiliers(actif)
            WHERE actif = TRUE;
        """)

        print("  ✓ Table prets_immobiliers créée")

        # ═══════════════════════════════════════════════════════════════════
        # TABLE 2 : echeances_prets (échéancier détaillé)
        # ═══════════════════════════════════════════════════════════════════

        print("  → Création table echeances_prets...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS echeances_prets (
                id SERIAL PRIMARY KEY,

                -- Lien avec prêt
                pret_id INTEGER NOT NULL REFERENCES prets_immobiliers(id) ON DELETE CASCADE,

                -- Identifiants échéance
                numero_echeance INTEGER NOT NULL,
                date_echeance DATE NOT NULL,

                -- Ventilation financière
                montant_total NUMERIC(15, 2) NOT NULL,
                montant_interet NUMERIC(15, 2) NOT NULL,
                montant_capital NUMERIC(15, 2) NOT NULL,
                capital_restant_du NUMERIC(15, 2) NOT NULL,

                -- Assurance
                montant_assurance NUMERIC(15, 2) DEFAULT 0,

                -- Statut comptabilisation
                comptabilise BOOLEAN DEFAULT FALSE,
                ecriture_comptable_id INTEGER REFERENCES ecritures_comptables(id),
                date_comptabilisation TIMESTAMP,

                -- Métadonnées
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                -- Contrainte unicité (un prêt ne peut avoir qu'une ligne par date)
                CONSTRAINT uq_pret_date_echeance UNIQUE (pret_id, date_echeance)
            );
        """)

        # Index pour recherche rapide par date
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_echeances_date
            ON echeances_prets(date_echeance);
        """)

        # Index pour recherche rapide par prêt + date
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_echeances_pret_date
            ON echeances_prets(pret_id, date_echeance);
        """)

        # Index pour échéances non comptabilisées
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_echeances_non_comptabilisees
            ON echeances_prets(comptabilise)
            WHERE comptabilise = FALSE;
        """)

        print("  ✓ Table echeances_prets créée")

        # ═══════════════════════════════════════════════════════════════════
        # COMMIT
        # ═══════════════════════════════════════════════════════════════════

        conn.commit()
        print("✅ Migration 004 appliquée avec succès")
        print("")
        print("📊 Tables créées :")
        print("  - prets_immobiliers : Contrats de prêts")
        print("  - echeances_prets : Échéancier ligne par ligne")
        print("")
        print("🔍 Usage :")
        print("  1. Email tableau amortissement → Ingestion données")
        print("  2. Email relevé bancaire → Lookup échéance pour ventilation")

    except Exception as e:
        conn.rollback()
        print(f"❌ ERREUR lors de la migration : {e}")
        raise

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    appliquer_migration()
