#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EXÉCUTION MIGRATION : Renommer montant_total → montant_echeance
================================================================
"""

import os
import sys
from sqlalchemy import create_engine, text

def executer_migration():
    """Exécute la migration SQL"""

    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        print("❌ DATABASE_URL non définie")
        sys.exit(1)

    engine = create_engine(DATABASE_URL)

    print("=" * 80)
    print("🔧 MIGRATION : Renommer montant_total → montant_echeance")
    print("=" * 80)

    try:
        with engine.connect() as conn:
            # Commencer transaction
            trans = conn.begin()

            # 1. Renommer colonne
            print("\n1️⃣ Renommage colonne...")
            conn.execute(text("""
                ALTER TABLE echeances_prets
                RENAME COLUMN montant_total TO montant_echeance
            """))
            print("   ✅ Colonne renommée : montant_total → montant_echeance")

            # 2. Ajouter commentaire
            print("\n2️⃣ Ajout commentaire...")
            conn.execute(text("""
                COMMENT ON COLUMN echeances_prets.montant_echeance IS
                'Montant de l''échéance mensuelle à payer (capital + intérêts)'
            """))
            print("   ✅ Commentaire ajouté")

            # Commit
            trans.commit()

            # 3. Vérification
            print("\n3️⃣ Vérification...")
            result = conn.execute(text("""
                SELECT
                    pret_id,
                    numero_echeance,
                    date_echeance,
                    montant_echeance,
                    montant_capital,
                    montant_interet
                FROM echeances_prets
                LIMIT 5
            """))

            rows = result.fetchall()
            if rows:
                print(f"   📋 Échantillon ({len(rows)} lignes) :")
                for row in rows:
                    print(f"      • Prêt {row[0]} échéance {row[1]} : {row[3]}€ ({row[2]})")
            else:
                print("   ℹ️  Aucune échéance en base")

            print("\n" + "=" * 80)
            print("✅ MIGRATION TERMINÉE")
            print("=" * 80)

    except Exception as e:
        print(f"\n❌ ERREUR : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    executer_migration()
