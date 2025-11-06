#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIGRATION - Fix email_id constraint
===================================
Supprime la contrainte UNIQUE sur email_id car un email peut
contenir plusieurs événements (relevé bancaire = 114 opérations)

Date: 05/11/2025
"""

import os
import sys
from sqlalchemy import create_engine, text

# Récupérer l'URL de la base de données
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("❌ Variable DATABASE_URL non définie")
    sys.exit(1)

# Fix postgres:// → postgresql://
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

print("=" * 80)
print("MIGRATION - Fix email_id constraint")
print("=" * 80)
print()

# Créer la connexion
engine = create_engine(DATABASE_URL)

with engine.begin() as conn:
    print("🔍 Vérification de la contrainte email_id...")

    # Vérifier si la contrainte existe
    result = conn.execute(text("""
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_name = 'evenements_comptables'
          AND constraint_type = 'UNIQUE'
          AND constraint_name = 'evenements_comptables_email_id_key'
    """))

    constraint_exists = result.fetchone() is not None

    if constraint_exists:
        print("✅ Contrainte trouvée: evenements_comptables_email_id_key")
        print("🔧 Suppression de la contrainte...")

        conn.execute(text("""
            ALTER TABLE evenements_comptables
            DROP CONSTRAINT IF EXISTS evenements_comptables_email_id_key
        """))

        print("✅ Contrainte supprimée avec succès")
    else:
        print("ℹ️  Contrainte déjà supprimée ou inexistante")

    print()
    print("=" * 80)
    print("MIGRATION TERMINÉE")
    print("=" * 80)
    print()
    print("✅ email_id peut maintenant avoir plusieurs événements par email")
    print()
    print("Prochaine étape:")
    print("  1. Supprimer l'événement orphelin: DELETE FROM evenements_comptables WHERE id = 4")
    print("  2. Relancer le workflow")

print()
print("✅ Migration appliquée avec succès")
