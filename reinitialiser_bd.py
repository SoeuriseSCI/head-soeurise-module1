#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RÉINITIALISATION COMPLÈTE DE LA BASE DE DONNÉES - Module 2
===========================================================
Script pour repartir d'un état propre avec schéma complet.

⚠️ ATTENTION : Ce script SUPPRIME toutes les données !

Étapes:
1. Drop toutes les tables
2. Recrée le schéma complet (toutes colonnes + table propositions)
3. Crée l'exercice 2023
4. Insère SEULEMENT le plan comptable (pas les écritures)
   → Permet de tester le workflow d'initialisation du bilan

Usage:
    python reinitialiser_bd.py

Après réinitialisation, la BD contient:
    - Schéma complet (8 tables + propositions)
    - Exercice 2023
    - Plan comptable (12 comptes)
    - AUCUNE écriture → Prêt pour tester l'init du bilan
"""

import os
import sys
import psycopg2
from datetime import datetime

DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL non défini")
    sys.exit(1)

# Liste des comptes pour le plan comptable
COMPTES_PLAN = [
    {"numero": "89", "libelle": "Bilan d'ouverture", "type": "DIFF", "classe": 8},
    {"numero": "101", "libelle": "Capital social", "type": "PASSIF", "classe": 1},
    {"numero": "120", "libelle": "Report à nouveau", "type": "ACTIF", "classe": 1},
    {"numero": "130", "libelle": "Résultat de l'exercice", "type": "PASSIF", "classe": 1},
    {"numero": "161", "libelle": "Emprunts", "type": "PASSIF", "classe": 1},
    {"numero": "280", "libelle": "SCPI Epargne Pierre", "type": "ACTIF", "classe": 2},
    {"numero": "290", "libelle": "Provision dépréciation SCPI", "type": "PASSIF", "classe": 2},
    {"numero": "401", "libelle": "Fournisseurs", "type": "PASSIF", "classe": 4},
    {"numero": "412", "libelle": "Créances diverses", "type": "ACTIF", "classe": 4},
    {"numero": "444", "libelle": "Compte courant associés", "type": "PASSIF", "classe": 4},
    {"numero": "502", "libelle": "Actions", "type": "ACTIF", "classe": 5},
    {"numero": "512", "libelle": "Banque", "type": "ACTIF", "classe": 5},
]


def demander_confirmation():
    """Demande confirmation avant suppression"""
    print("=" * 80)
    print("⚠️  RÉINITIALISATION COMPLÈTE DE LA BASE DE DONNÉES")
    print("=" * 80)
    print()
    print("Ce script va:")
    print("  1. SUPPRIMER toutes les tables et données existantes")
    print("  2. Recréer le schéma complet (8 tables + propositions)")
    print("  3. Créer l'exercice 2023")
    print("  4. Créer le plan comptable (12 comptes)")
    print("  5. NE PAS créer d'écritures (pour tester le workflow)")
    print()
    print("⚠️  TOUTES LES DONNÉES ACTUELLES SERONT PERDUES !")
    print()

    reponse = input("Tapez 'OUI' pour continuer : ")
    if reponse.strip().upper() != 'OUI':
        print("❌ Opération annulée")
        sys.exit(0)
    print()


def main():
    """Réinitialisation complète"""

    demander_confirmation()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # ═══════════════════════════════════════════════════════════════════════════
    # ÉTAPE 1 : Suppression des tables
    # ═══════════════════════════════════════════════════════════════════════════

    print("🗑️  ÉTAPE 1/5 : Suppression des tables")
    print("-" * 80)

    tables = [
        'propositions_en_attente',
        'rapports_comptables',
        'balances_mensuelles',
        'evenements_comptables',
        'calculs_amortissements',
        'ecritures_comptables',
        'immobilisations',
        'plans_comptes',
        'exercices_comptables',
        'alembic_version'
    ]

    for table in tables:
        cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        print(f"  ✓ {table}")

    conn.commit()
    print()

    # ═══════════════════════════════════════════════════════════════════════════
    # ÉTAPE 2 : Création du schéma complet
    # ═══════════════════════════════════════════════════════════════════════════

    print("🏗️  ÉTAPE 2/5 : Création du schéma complet")
    print("-" * 80)

    # Table exercices_comptables
    cur.execute("""
        CREATE TABLE exercices_comptables (
            id SERIAL PRIMARY KEY,
            annee INTEGER UNIQUE NOT NULL,
            date_debut DATE NOT NULL,
            date_fin DATE NOT NULL,
            statut VARCHAR(50),
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  ✓ exercices_comptables")

    # Table plans_comptes
    cur.execute("""
        CREATE TABLE plans_comptes (
            id SERIAL PRIMARY KEY,
            numero_compte VARCHAR(10) UNIQUE NOT NULL,
            libelle VARCHAR(255) NOT NULL,
            type_compte VARCHAR(50) NOT NULL,
            classe INTEGER,
            description TEXT,
            actif BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  ✓ plans_comptes")

    # Table ecritures_comptables (TOUTES les colonnes)
    cur.execute("""
        CREATE TABLE ecritures_comptables (
            id SERIAL PRIMARY KEY,
            exercice_id INTEGER NOT NULL REFERENCES exercices_comptables(id),
            numero_ecriture VARCHAR(50) NOT NULL,
            date_ecriture DATE NOT NULL,
            date_enregistrement TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_email_id VARCHAR(255),
            source_email_date TIMESTAMP,
            source_email_from VARCHAR(255),
            libelle_ecriture VARCHAR(255) NOT NULL,
            type_ecriture VARCHAR(50),
            compte_debit VARCHAR(10) NOT NULL REFERENCES plans_comptes(numero_compte),
            compte_credit VARCHAR(10) NOT NULL REFERENCES plans_comptes(numero_compte),
            montant NUMERIC(12, 2) NOT NULL,
            piece_jointe VARCHAR(255),
            notes TEXT,
            valide BOOLEAN DEFAULT FALSE,
            validee_par VARCHAR(255),
            validee_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  ✓ ecritures_comptables")

    # Table immobilisations
    cur.execute("""
        CREATE TABLE immobilisations (
            id SERIAL PRIMARY KEY,
            numero_immobilisation VARCHAR(50) UNIQUE NOT NULL,
            libelle VARCHAR(255) NOT NULL,
            description TEXT,
            compte_immobilisation VARCHAR(10) NOT NULL REFERENCES plans_comptes(numero_compte),
            compte_amortissement VARCHAR(10) NOT NULL REFERENCES plans_comptes(numero_compte),
            valeur_brute NUMERIC(12, 2) NOT NULL,
            date_acquisition DATE NOT NULL,
            methode_amortissement VARCHAR(50) NOT NULL,
            duree_amortissement INTEGER NOT NULL,
            taux_degressif NUMERIC(5, 2),
            source_email_id VARCHAR(255),
            source_email_date TIMESTAMP,
            actif BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  ✓ immobilisations")

    # Table calculs_amortissements
    cur.execute("""
        CREATE TABLE calculs_amortissements (
            id SERIAL PRIMARY KEY,
            immobilisation_id INTEGER NOT NULL REFERENCES immobilisations(id),
            exercice_id INTEGER NOT NULL REFERENCES exercices_comptables(id),
            source_email_id VARCHAR(255),
            source_calcul_date TIMESTAMP,
            base_amortissable NUMERIC(12, 2),
            taux_applique NUMERIC(5, 2),
            montant_amortissement NUMERIC(12, 2) NOT NULL,
            ecriture_id INTEGER REFERENCES ecritures_comptables(id),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  ✓ calculs_amortissements")

    # Table evenements_comptables
    cur.execute("""
        CREATE TABLE evenements_comptables (
            id SERIAL PRIMARY KEY,
            email_id VARCHAR(255) UNIQUE,
            email_from VARCHAR(255) NOT NULL,
            email_date TIMESTAMP NOT NULL,
            email_subject VARCHAR(255),
            email_body TEXT NOT NULL,
            type_evenement VARCHAR(100),
            est_comptable BOOLEAN,
            statut VARCHAR(50) DEFAULT 'EN_ATTENTE',
            message_erreur TEXT,
            ecritures_creees INTEGER[],
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            traite_at TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  ✓ evenements_comptables")

    # Table balances_mensuelles
    cur.execute("""
        CREATE TABLE balances_mensuelles (
            id SERIAL PRIMARY KEY,
            exercice_id INTEGER NOT NULL REFERENCES exercices_comptables(id),
            mois INTEGER NOT NULL,
            compte_numero VARCHAR(10) NOT NULL REFERENCES plans_comptes(numero_compte),
            solde_debit NUMERIC(12, 2) DEFAULT 0,
            solde_credit NUMERIC(12, 2) DEFAULT 0,
            solde_net NUMERIC(12, 2) DEFAULT 0,
            nb_operations INTEGER DEFAULT 0,
            derniere_operation TIMESTAMP,
            recalcule_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  ✓ balances_mensuelles")

    # Table rapports_comptables
    cur.execute("""
        CREATE TABLE rapports_comptables (
            id SERIAL PRIMARY KEY,
            exercice_id INTEGER NOT NULL REFERENCES exercices_comptables(id),
            type_rapport VARCHAR(100) NOT NULL,
            contenu_texte TEXT NOT NULL,
            contenu_json JSONB,
            genere_par VARCHAR(255),
            genere_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  ✓ rapports_comptables")

    # Table propositions_en_attente
    cur.execute("""
        CREATE TABLE propositions_en_attente (
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
        )
    """)
    print("  ✓ propositions_en_attente")

    # Index
    cur.execute("CREATE INDEX IF NOT EXISTS idx_propositions_token ON propositions_en_attente(token)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_propositions_statut ON propositions_en_attente(statut)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_propositions_created ON propositions_en_attente(created_at)")
    print("  ✓ Index créés")

    conn.commit()
    print()

    # ═══════════════════════════════════════════════════════════════════════════
    # ÉTAPE 3 : Création exercice 2023
    # ═══════════════════════════════════════════════════════════════════════════

    print("📅 ÉTAPE 3/5 : Création exercice 2023")
    print("-" * 80)

    cur.execute("""
        INSERT INTO exercices_comptables (annee, date_debut, date_fin, statut, description)
        VALUES (2023, '2023-01-01', '2023-12-31', 'OUVERT', 'Exercice 2023')
        RETURNING id
    """)
    exercice_id = cur.fetchone()[0]
    print(f"  ✓ Exercice 2023 créé (ID: {exercice_id})")

    conn.commit()
    print()

    # ═══════════════════════════════════════════════════════════════════════════
    # ÉTAPE 4 : Création du plan comptable
    # ═══════════════════════════════════════════════════════════════════════════

    print("💰 ÉTAPE 4/5 : Création du plan comptable")
    print("-" * 80)

    for compte in COMPTES_PLAN:
        cur.execute("""
            INSERT INTO plans_comptes (numero_compte, libelle, type_compte, classe, actif)
            VALUES (%s, %s, %s, %s, TRUE)
        """, (compte["numero"], compte["libelle"], compte["type"], compte["classe"]))
        print(f"  ✓ Compte {compte['numero']}: {compte['libelle']}")

    conn.commit()
    print()

    # ═══════════════════════════════════════════════════════════════════════════
    # ÉTAPE 5 : Vérification finale
    # ═══════════════════════════════════════════════════════════════════════════

    print("✅ ÉTAPE 5/5 : Vérification finale")
    print("-" * 80)

    cur.execute("SELECT COUNT(*) FROM exercices_comptables")
    nb_exercices = cur.fetchone()[0]
    print(f"  ✓ Exercices: {nb_exercices}")

    cur.execute("SELECT COUNT(*) FROM plans_comptes")
    nb_comptes = cur.fetchone()[0]
    print(f"  ✓ Comptes: {nb_comptes}")

    cur.execute("SELECT COUNT(*) FROM ecritures_comptables")
    nb_ecritures = cur.fetchone()[0]
    print(f"  ✓ Écritures: {nb_ecritures}")

    cur.execute("SELECT COUNT(*) FROM propositions_en_attente")
    nb_propositions = cur.fetchone()[0]
    print(f"  ✓ Propositions: {nb_propositions}")

    print()
    print("=" * 80)
    print("🎉 RÉINITIALISATION TERMINÉE AVEC SUCCÈS !")
    print("=" * 80)
    print()
    print("État de la base de données:")
    print(f"  - {nb_exercices} exercice (2023)")
    print(f"  - {nb_comptes} comptes dans le plan comptable")
    print(f"  - {nb_ecritures} écritures (base vide)")
    print(f"  - {nb_propositions} propositions en attente")
    print()
    print("🎯 Prêt pour tester le workflow d'initialisation du bilan 2023 !")
    print()
    print("Pour tester:")
    print("  1. Envoyer un email avec le bilan 2023 au format JSON")
    print("  2. _Head doit créer des propositions avec token")
    print("  3. Valider avec: [_Head] VALIDE: TOKEN")
    print("  4. Vérifier que les 11 écritures sont créées")
    print()

    cur.close()
    conn.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n❌ Opération annulée par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
