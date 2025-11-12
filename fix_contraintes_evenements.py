#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIGRATION - FIX Contraintes Événements Comptables
==================================================
Corrige les incohérences identifiées dans l'analyse du 12/11/2025

PROBLÈMES CORRIGÉS:
1. Index UNIQUE sur fingerprint (empêche retraitement après GC)
2. Contrainte UNIQUE sur email_id (empêche multiple événements par email)

ACTIONS:
- Supprime idx_fingerprint_unique (UNIQUE)
- Crée idx_fingerprint_lookup (non-unique, pour performance)
- Supprime contrainte UNIQUE sur email_id
- Crée index lookup sur email_id (non-unique)

Date: 12/11/2025
Auteur: Claude Code
Référence: ANALYSE_INJECTION_EVENEMENTS.md
"""

import os
import sys
from sqlalchemy import text, create_engine

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("❌ ERREUR: Variable d'environnement DATABASE_URL non définie")
    sys.exit(1)

if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)


def migrate_fix_contraintes():
    """
    Applique les corrections aux contraintes
    """
    print("=" * 80)
    print("MIGRATION - FIX CONTRAINTES ÉVÉNEMENTS COMPTABLES")
    print("=" * 80)
    print()
    print(f"📊 Base de données: {DATABASE_URL[:50]}...")
    print()

    engine = create_engine(DATABASE_URL, echo=False)

    with engine.connect() as conn:
        # ═══════════════════════════════════════════════════════════════
        # ÉTAPE 1: Fingerprint
        # ═══════════════════════════════════════════════════════════════
        print("📝 ÉTAPE 1: Correction contrainte UNIQUE sur fingerprint")
        print("-" * 80)

        # 1.1. Vérifier si l'index UNIQUE existe
        result = conn.execute(text("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'evenements_comptables'
              AND indexname = 'idx_fingerprint_unique'
        """))
        has_unique = result.fetchone() is not None

        if has_unique:
            try:
                conn.execute(text("DROP INDEX IF EXISTS idx_fingerprint_unique"))
                conn.commit()
                print("  ✅ Index UNIQUE sur fingerprint supprimé")
            except Exception as e:
                print(f"  ❌ Erreur suppression index UNIQUE: {e}")
                conn.rollback()
        else:
            print("  ℹ️  Index UNIQUE sur fingerprint n'existe pas (déjà supprimé)")

        # 1.2. Créer index lookup (non-unique)
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_fingerprint_lookup ON evenements_comptables(fingerprint)"))
            conn.commit()
            print("  ✅ Index lookup sur fingerprint créé")
        except Exception as e:
            print(f"  ⚠️  Index lookup déjà présent: {e}")
            conn.rollback()

        print()

        # ═══════════════════════════════════════════════════════════════
        # ÉTAPE 2: Email ID
        # ═══════════════════════════════════════════════════════════════
        print("📝 ÉTAPE 2: Correction contrainte UNIQUE sur email_id")
        print("-" * 80)

        # 2.1. Trouver le nom de la contrainte UNIQUE
        result = conn.execute(text("""
            SELECT conname
            FROM pg_constraint
            WHERE conrelid = 'evenements_comptables'::regclass
              AND contype = 'u'
              AND conkey::text LIKE '%email_id%'
        """))
        constraint_row = result.fetchone()

        if constraint_row:
            constraint_name = constraint_row[0]
            try:
                conn.execute(text(f"ALTER TABLE evenements_comptables DROP CONSTRAINT IF EXISTS {constraint_name}"))
                conn.commit()
                print(f"  ✅ Contrainte UNIQUE sur email_id supprimée ({constraint_name})")
            except Exception as e:
                print(f"  ❌ Erreur suppression contrainte: {e}")
                conn.rollback()
        else:
            print("  ℹ️  Contrainte UNIQUE sur email_id n'existe pas (déjà supprimée)")

        # 2.2. Créer index lookup (non-unique)
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_email_id_lookup ON evenements_comptables(email_id)"))
            conn.commit()
            print("  ✅ Index lookup sur email_id créé")
        except Exception as e:
            print(f"  ⚠️  Index lookup déjà présent: {e}")
            conn.rollback()

        print()

        # ═══════════════════════════════════════════════════════════════
        # ÉTAPE 3: Vérification finale
        # ═══════════════════════════════════════════════════════════════
        print("📝 ÉTAPE 3: Vérification finale")
        print("-" * 80)

        # Lister tous les index sur la table
        result = conn.execute(text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'evenements_comptables'
            ORDER BY indexname
        """))
        indexes = result.fetchall()

        print("  📋 Index sur evenements_comptables:")
        for idx_name, idx_def in indexes:
            print(f"     - {idx_name}")

        print()

        # Lister toutes les contraintes UNIQUE
        result = conn.execute(text("""
            SELECT conname, pg_get_constraintdef(oid)
            FROM pg_constraint
            WHERE conrelid = 'evenements_comptables'::regclass
              AND contype = 'u'
        """))
        constraints = result.fetchall()

        if constraints:
            print("  ⚠️  Contraintes UNIQUE restantes:")
            for con_name, con_def in constraints:
                print(f"     - {con_name}: {con_def}")
        else:
            print("  ✅ Aucune contrainte UNIQUE restante")

        print()

    print("=" * 80)
    print("✅ MIGRATION TERMINÉE AVEC SUCCÈS")
    print("=" * 80)
    print()
    print("⚠️  PROCHAINES ÉTAPES:")
    print()
    print("1. Mettre à jour models_module2.py:")
    print("   - Ajouter les colonnes: date_operation, libelle, libelle_normalise,")
    print("     montant, type_operation, fingerprint, phase_traitement")
    print("   - Retirer unique=True sur email_id et fingerprint")
    print()
    print("2. Tester le workflow complet:")
    print("   - Créer événements depuis un relevé bancaire (50+ opérations)")
    print("   - Vérifier qu'aucune erreur UNIQUE violation")
    print()
    print("3. Référence:")
    print("   - Voir ANALYSE_INJECTION_EVENEMENTS.md pour détails complets")
    print()


def rollback_migration():
    """
    ROLLBACK: Restaure les contraintes UNIQUE (pour tests)
    ⚠️ ATTENTION: Cette fonction restaure les contraintes problématiques
    """
    print("⚠️  ROLLBACK DE LA MIGRATION")
    print()

    response = input("Êtes-vous sûr de vouloir restaurer les contraintes UNIQUE? (oui/non): ")
    if response.lower() != 'oui':
        print("❌ Rollback annulé")
        return

    engine = create_engine(DATABASE_URL, echo=False)

    with engine.connect() as conn:
        print("🔄 Restauration des contraintes UNIQUE...")
        print()

        # Restaurer UNIQUE sur fingerprint
        try:
            conn.execute(text("DROP INDEX IF EXISTS idx_fingerprint_lookup"))
            conn.execute(text("CREATE UNIQUE INDEX idx_fingerprint_unique ON evenements_comptables(fingerprint)"))
            conn.commit()
            print("  ✅ Index UNIQUE sur fingerprint restauré")
        except Exception as e:
            print(f"  ❌ Erreur: {e}")
            conn.rollback()

        # Restaurer UNIQUE sur email_id
        try:
            conn.execute(text("ALTER TABLE evenements_comptables ADD CONSTRAINT evenements_comptables_email_id_key UNIQUE (email_id)"))
            conn.commit()
            print("  ✅ Contrainte UNIQUE sur email_id restaurée")
        except Exception as e:
            print(f"  ❌ Erreur: {e}")
            conn.rollback()

        print()

    print("✅ ROLLBACK TERMINÉ")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--rollback':
        rollback_migration()
    else:
        migrate_fix_contraintes()
