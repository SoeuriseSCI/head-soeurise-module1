#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EXÉCUTION MIGRATION : Ajout colonne type_taux
==============================================
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
    print("🔧 MIGRATION : Ajout colonne type_taux")
    print("=" * 80)

    try:
        with engine.connect() as conn:
            # Commencer transaction
            trans = conn.begin()

            # 1. Ajouter colonne
            print("\n1️⃣ Ajout colonne type_taux...")
            conn.execute(text("""
                ALTER TABLE prets_immobiliers
                ADD COLUMN IF NOT EXISTS type_taux VARCHAR(20) DEFAULT 'FIXE'
            """))
            print("   ✅ Colonne ajoutée")

            # 2. Mettre à jour valeurs existantes
            print("\n2️⃣ Mise à jour valeurs existantes...")
            result = conn.execute(text("""
                UPDATE prets_immobiliers
                SET type_taux = 'FIXE'
                WHERE type_taux IS NULL
            """))
            print(f"   ✅ {result.rowcount} ligne(s) mise(s) à jour")

            # 3. Ajouter commentaire
            print("\n3️⃣ Ajout commentaire...")
            conn.execute(text("""
                COMMENT ON COLUMN prets_immobiliers.type_taux IS
                'Type de taux : FIXE (presque toujours en France) ou VARIABLE'
            """))
            print("   ✅ Commentaire ajouté")

            # Commit
            trans.commit()

            # 4. Vérification
            print("\n4️⃣ Vérification...")
            result = conn.execute(text("""
                SELECT id, numero_pret, banque, type_taux, type_amortissement
                FROM prets_immobiliers
            """))

            rows = result.fetchall()
            if rows:
                print(f"   📋 {len(rows)} prêt(s) en base :")
                for row in rows:
                    print(f"      • ID {row[0]} : {row[1]} ({row[2]}) - Taux: {row[3]}, Amort: {row[4]}")
            else:
                print("   ℹ️  Aucun prêt en base")

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
