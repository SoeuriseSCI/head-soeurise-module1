#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NETTOYAGE DES PROPOSITIONS EN ATTENTE
======================================
Nettoie les propositions obsolètes et doublons
"""

import os
import sys
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text

def nettoyer_propositions():
    """
    Nettoie les propositions en base de données :
    1. Rejette HEAD-2E17B6ED (doublon SCPI déjà inséré)
    2. Marque comme EXPIREE les propositions > 7 jours (sauf VALIDEE)
    """

    DATABASE_URL = os.environ.get('DATABASE_URL', '').replace('postgres://', 'postgresql://')
    engine = create_engine(DATABASE_URL)

    print("═══════════════════════════════════════════════════════════")
    print("NETTOYAGE PROPOSITIONS EN ATTENTE")
    print("═══════════════════════════════════════════════════════════\n")

    with engine.connect() as conn:
        # 1. Rejeter HEAD-2E17B6ED (doublon SCPI)
        print("1️⃣  Rejet proposition doublon HEAD-2E17B6ED...")

        result = conn.execute(text("""
            UPDATE propositions_en_attente
            SET statut = 'REJETEE',
                notes = 'Doublon - SCPI cutoff déjà inséré le 20/11 (ID 520-521)',
                validee_at = NOW()
            WHERE token = 'HEAD-2E17B6ED'
            AND statut != 'REJETEE'
            RETURNING id, token
        """))
        conn.commit()

        rows = result.fetchall()
        if rows:
            for row in rows:
                print(f"   ✅ Proposition ID {row[0]} ({row[1]}) marquée REJETEE")
        else:
            print("   ℹ️  Déjà rejetée ou introuvable")

        print()

        # 2. Marquer comme EXPIREE les propositions anciennes (> 7 jours)
        print("2️⃣  Marquage propositions expirées (> 7 jours)...")

        date_limite = datetime.utcnow() - timedelta(days=7)

        result = conn.execute(text("""
            UPDATE propositions_en_attente
            SET statut = 'EXPIREE',
                notes = COALESCE(notes || ' | ', '') || 'Expirée automatiquement (> 7 jours)'
            WHERE statut IN ('EN_ATTENTE', 'ERREUR')
            AND created_at < :date_limite
            RETURNING id, token, type_evenement, created_at
        """), {'date_limite': date_limite})
        conn.commit()

        rows = result.fetchall()
        if rows:
            print(f"   ✅ {len(rows)} proposition(s) expirée(s) :")
            for row in rows:
                print(f"      - ID {row[0]} ({row[1]}) - {row[2]} - Créé le {row[3]}")
        else:
            print("   ℹ️  Aucune proposition à expirer")

        print()

        # 3. Statistiques finales
        print("3️⃣  Statistiques après nettoyage...")

        result = conn.execute(text("""
            SELECT statut, COUNT(*)
            FROM propositions_en_attente
            GROUP BY statut
            ORDER BY statut
        """))

        print("\n   État des propositions :")
        for row in result:
            print(f"   - {row[0]:15} : {row[1]:3} proposition(s)")

        print()

        # 4. Propositions EN_ATTENTE restantes
        result = conn.execute(text("""
            SELECT token, type_evenement, created_at
            FROM propositions_en_attente
            WHERE statut = 'EN_ATTENTE'
            ORDER BY created_at DESC
        """))

        rows = result.fetchall()
        if rows:
            print(f"\n   ⚠️  {len(rows)} proposition(s) EN_ATTENTE restante(s) :")
            for row in rows:
                print(f"      - {row[0]} ({row[1]}) - Créé le {row[2]}")
        else:
            print("\n   ✅ Aucune proposition EN_ATTENTE restante")

    print("\n═══════════════════════════════════════════════════════════")
    print("✅ NETTOYAGE TERMINÉ")
    print("═══════════════════════════════════════════════════════════")

if __name__ == '__main__':
    try:
        nettoyer_propositions()
    except Exception as e:
        print(f"❌ Erreur : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
