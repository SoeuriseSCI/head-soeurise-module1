#!/usr/bin/env python3
"""
Suppression Écritures Bilan 2023 Datées 02/11/2025
==================================================

CONTEXTE :
- Les écritures du bilan 2023 ont été créées le 02/11/2025
- Elles ont été datées à tort du 02/11/2025 (date de création)
- Seul le bilan d'ouverture 2024 nous intéresse
- Ces écritures doivent être supprimées

ACTIONS :
1. Identifier toutes les écritures datées 2025-11-02
2. Afficher le détail de ces écritures
3. Supprimer après confirmation
4. Vérifier résultats
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_connection():
    """Connexion à la base de données"""
    if not DATABASE_URL:
        raise ValueError("❌ DATABASE_URL non définie")
    return psycopg2.connect(DATABASE_URL)

def main():
    print("=" * 80)
    print("🗑️  SUPPRESSION ÉCRITURES BILAN 2023 (02/11/2025)")
    print("=" * 80)
    print(f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 80)
    print()

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 1. Identifier les écritures du 02/11/2025
        print("[1/4] Identification des écritures à supprimer...")
        print("      Recherche : date_ecriture = 2025-11-02")
        print()

        cur.execute("""
            SELECT
                id,
                date_ecriture,
                exercice_id,
                type_ecriture,
                compte_debit,
                compte_credit,
                montant,
                libelle_ecriture
            FROM ecritures_comptables
            WHERE date_ecriture = '2025-11-02'
            ORDER BY id
        """)

        ecritures = cur.fetchall()

        if not ecritures:
            print("  ℹ️  Aucune écriture trouvée avec date 2025-11-02")
            return

        print(f"  📊 {len(ecritures)} écritures trouvées")
        print()

        # 2. Afficher le détail
        print("[2/4] Détail des écritures à supprimer...")
        print()
        print(f"{'ID':<6} {'Exercice':<10} {'Type':<25} {'Débit':<8} {'Crédit':<8} {'Montant':>12} {'Libellé'}")
        print("-" * 110)

        total_montant = 0
        for e in ecritures:
            type_str = (e['type_ecriture'] or 'NULL')[:23]
            libelle_str = e['libelle_ecriture'][:40]
            print(f"{e['id']:<6} {e['exercice_id']:<10} {type_str:<25} "
                  f"{e['compte_debit']:<8} {e['compte_credit']:<8} "
                  f"{e['montant']:>12,.2f}€ {libelle_str}")
            total_montant += e['montant']

        print("-" * 110)
        print(f"{'TOTAL':<80} {total_montant:>12,.2f}€")
        print()

        # Vérifier exercice concerné
        exercices = set(e['exercice_id'] for e in ecritures)
        print(f"  📋 Exercices concernés : {', '.join(map(str, exercices))}")
        print()

        # 3. Demander confirmation
        print("[3/4] Confirmation suppression...")
        print(f"  ⚠️  {len(ecritures)} écritures vont être SUPPRIMÉES")
        print()

        reponse = input("❓ Confirmer la suppression ? (oui/non) : ").strip().lower()
        if reponse != 'oui':
            print("  ❌ Suppression annulée")
            return

        # Supprimer les écritures
        cur.execute("""
            DELETE FROM ecritures_comptables
            WHERE date_ecriture = '2025-11-02'
        """)
        nb_supprimees = cur.rowcount
        conn.commit()

        print(f"  ✅ {nb_supprimees} écritures supprimées")
        print()

        # 4. Vérifier résultats
        print("[4/4] Vérification post-suppression...")

        # Compter les écritures restantes au 2025-11-02
        cur.execute("""
            SELECT COUNT(*) as reste
            FROM ecritures_comptables
            WHERE date_ecriture = '2025-11-02'
        """)
        reste = cur.fetchone()['reste']

        if reste == 0:
            print(f"  ✅ Aucune écriture restante datée 2025-11-02")
        else:
            print(f"  ⚠️  ATTENTION : {reste} écritures restent datées 2025-11-02")

        # Afficher stats par exercice
        print()
        print("  📊 État des exercices après suppression :")
        cur.execute("""
            SELECT
                e.annee,
                COUNT(ec.id) as nb_ecritures,
                MIN(ec.date_ecriture) as premiere_date,
                MAX(ec.date_ecriture) as derniere_date
            FROM exercices_comptables e
            LEFT JOIN ecritures_comptables ec ON ec.exercice_id = e.id
            GROUP BY e.id, e.annee
            ORDER BY e.annee
        """)

        exercices_stats = cur.fetchall()
        for ex in exercices_stats:
            print(f"     Exercice {ex['annee']} : {ex['nb_ecritures']} écritures "
                  f"({ex['premiere_date']} → {ex['derniere_date']})")

        print()
        print("✅ Nettoyage validé avec succès!")

    except Exception as e:
        print(f"❌ Erreur : {e}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

    print()
    print("=" * 80)
    print("✅ Script terminé")
    print("=" * 80)

if __name__ == '__main__':
    main()
