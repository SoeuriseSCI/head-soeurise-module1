#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vérifie que le schéma PostgreSQL correspond aux modèles Python

Affiche les colonnes de chaque table et compare avec models_module2.py
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Charge DATABASE_URL
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://soeurise:6cIWYzBxmh8YKBGBH9Or6ohidT6NiCap@dpg-d3ikk7ggjchc73ee4flg-a/soeurise"
)

# Colonnes attendues pour chaque table (d'après models_module2.py)
EXPECTED_COLUMNS = {
    'exercices_comptables': [
        'id', 'annee', 'date_debut', 'date_fin', 'statut', 'description',
        'created_at', 'updated_at'
    ],
    'plans_comptes': [
        'id', 'numero_compte', 'libelle', 'type_compte', 'classe',
        'description', 'actif', 'created_at'
    ],
    'ecritures_comptables': [
        'id', 'exercice_id', 'numero_ecriture', 'date_ecriture', 'date_enregistrement',
        'source_email_id', 'source_email_date', 'source_email_from',
        'libelle_ecriture', 'type_ecriture', 'compte_debit', 'compte_credit', 'montant',
        'piece_jointe', 'notes', 'valide', 'validee_par', 'validee_at',
        'created_at', 'updated_at'
    ],
    'immobilisations': [
        'id', 'numero_immobilisation', 'libelle', 'description',
        'compte_immobilisation', 'compte_amortissement',
        'valeur_brute', 'date_acquisition',
        'methode_amortissement', 'duree_amortissement', 'taux_degressif',
        'source_email_id', 'source_email_date',
        'actif', 'created_at', 'updated_at'
    ],
    'calculs_amortissements': [
        'id', 'immobilisation_id', 'exercice_id',
        'source_email_id', 'source_calcul_date',
        'base_amortissable', 'taux_applique', 'montant_amortissement',
        'ecriture_id', 'notes', 'created_at'
    ],
    'evenements_comptables': [
        'id', 'email_id', 'email_from', 'email_date', 'email_subject', 'email_body',
        'type_evenement', 'est_comptable', 'statut', 'message_erreur',
        'ecritures_creees', 'created_at', 'traite_at', 'updated_at'
    ],
    'balances_mensuelles': [
        'id', 'exercice_id', 'mois', 'compte_numero',
        'solde_debit', 'solde_credit', 'solde_net',
        'nb_operations', 'derniere_operation', 'recalcule_at', 'created_at'
    ],
    'rapports_comptables': [
        'id', 'exercice_id', 'type_rapport',
        'contenu_texte', 'contenu_json',
        'genere_par', 'genere_at', 'created_at'
    ]
}


def get_table_columns(cursor, table_name):
    """Récupère les colonnes d'une table depuis PostgreSQL"""
    cursor.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position;
    """, (table_name,))
    return cursor.fetchall()


def verify_table(cursor, table_name):
    """Vérifie qu'une table contient toutes les colonnes attendues"""
    print(f"\n{'═' * 80}")
    print(f"TABLE: {table_name}")
    print(f"{'═' * 80}")

    # Récupère les colonnes réelles
    actual_columns_raw = get_table_columns(cursor, table_name)
    actual_columns = [col['column_name'] for col in actual_columns_raw]

    # Colonnes attendues
    expected_columns = EXPECTED_COLUMNS.get(table_name, [])

    # Affiche les colonnes réelles
    print(f"\n✓ Colonnes présentes ({len(actual_columns)}):")
    for col in actual_columns_raw:
        nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
        default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
        print(f"  - {col['column_name']:<30} {col['data_type']:<20} {nullable}{default}")

    # Vérifie les colonnes manquantes
    missing = set(expected_columns) - set(actual_columns)
    if missing:
        print(f"\n❌ Colonnes MANQUANTES ({len(missing)}):")
        for col in sorted(missing):
            print(f"  - {col}")

    # Vérifie les colonnes en trop
    extra = set(actual_columns) - set(expected_columns)
    if extra:
        print(f"\n⚠️  Colonnes EN TROP ({len(extra)}):")
        for col in sorted(extra):
            print(f"  - {col}")

    # Statut
    if not missing and not extra:
        print(f"\n✅ Table {table_name} : Schéma CONFORME")
        return True
    else:
        print(f"\n⚠️  Table {table_name} : Schéma NON CONFORME")
        return False


def main():
    """Vérifie toutes les tables"""
    print("🔍 Vérification du schéma PostgreSQL")
    print(f"📡 Base de données: {DATABASE_URL[:50]}...")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        all_ok = True
        for table_name in EXPECTED_COLUMNS.keys():
            ok = verify_table(cursor, table_name)
            all_ok = all_ok and ok

        cursor.close()
        conn.close()

        # Résumé
        print(f"\n{'═' * 80}")
        if all_ok:
            print("✅ SUCCÈS : Toutes les tables sont conformes au modèle Python")
        else:
            print("⚠️  ATTENTION : Certaines tables ne sont pas conformes")
            print("   Exécutez 'python apply_migration.py' pour synchroniser le schéma")
        print(f"{'═' * 80}\n")

    except Exception as e:
        print(f"\n❌ Erreur de connexion à la base de données: {e}\n")
        return False

    return all_ok


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
