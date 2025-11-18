#!/usr/bin/env python3
"""
Analyse complète de l'exercice 2024
===================================

Affiche toutes les informations sur l'exercice 2024 :
- Types d'écritures présentes
- Répartition par type
- Première et dernière écriture
- Comptes utilisés
"""

import os
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
    print("📊 ANALYSE EXERCICE 2024")
    print("=" * 80)
    print(f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 80)
    print()

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 1. Info exercice
        print("[1/6] Informations exercice 2024...")
        cur.execute("""
            SELECT id, annee, date_debut, date_fin, statut
            FROM exercices_comptables
            WHERE annee = 2024
        """)
        exercice = cur.fetchone()

        if not exercice:
            print("  ❌ Exercice 2024 non trouvé")
            return

        print(f"  ✅ Exercice 2024 (ID {exercice['id']}) : {exercice['statut']}")
        print(f"     Période : {exercice['date_debut']} → {exercice['date_fin']}")
        print()

        # 2. Nombre total d'écritures
        print("[2/6] Statistiques générales...")
        cur.execute("""
            SELECT COUNT(*) as total
            FROM ecritures_comptables
            WHERE exercice_id = %s
        """, (exercice['id'],))
        total = cur.fetchone()['total']

        print(f"  📝 Total écritures 2024 : {total}")
        print()

        if total == 0:
            print("  ℹ️  Aucune écriture trouvée pour 2024")
            return

        # 3. Répartition par type d'écriture
        print("[3/6] Répartition par type d'écriture...")
        cur.execute("""
            SELECT
                type_ecriture,
                COUNT(*) as nb,
                SUM(montant) as total_montant
            FROM ecritures_comptables
            WHERE exercice_id = %s
            GROUP BY type_ecriture
            ORDER BY nb DESC
        """, (exercice['id'],))

        types = cur.fetchall()

        print(f"{'Type':<40} {'Nb':<8} {'Total'}")
        print("-" * 80)
        for t in types:
            type_nom = t['type_ecriture'] or '(NULL)'
            print(f"{type_nom:<40} {t['nb']:<8} {t['total_montant']:>15,.2f}€")
        print()

        # 4. Première et dernière écriture
        print("[4/6] Période couverte...")
        cur.execute("""
            SELECT
                MIN(date_ecriture) as premiere_date,
                MAX(date_ecriture) as derniere_date
            FROM ecritures_comptables
            WHERE exercice_id = %s
        """, (exercice['id'],))

        dates = cur.fetchone()
        print(f"  📅 Première écriture : {dates['premiere_date']}")
        print(f"  📅 Dernière écriture : {dates['derniere_date']}")
        print()

        # 5. Comptes utilisés
        print("[5/6] Comptes utilisés (top 10)...")
        cur.execute("""
            SELECT compte, COUNT(*) as nb, SUM(montant) as total
            FROM (
                SELECT compte_debit as compte, montant
                FROM ecritures_comptables
                WHERE exercice_id = %s
                UNION ALL
                SELECT compte_credit as compte, montant
                FROM ecritures_comptables
                WHERE exercice_id = %s
            ) AS comptes_tous
            GROUP BY compte
            ORDER BY nb DESC
            LIMIT 10
        """, (exercice['id'], exercice['id']))

        comptes = cur.fetchall()

        print(f"{'Compte':<10} {'Nb écritures':<15} {'Total'}")
        print("-" * 80)
        for c in comptes:
            print(f"{c['compte']:<10} {c['nb']:<15} {c['total']:>15,.2f}€")
        print()

        # 6. Vérifier si bilan ouverture existe avec autre nom
        print("[6/6] Recherche bilan d'ouverture...")
        cur.execute("""
            SELECT
                id,
                date_ecriture,
                type_ecriture,
                libelle_ecriture,
                compte_debit,
                compte_credit,
                montant
            FROM ecritures_comptables
            WHERE exercice_id = %s
              AND (
                  libelle_ecriture ILIKE '%bilan%ouverture%'
                  OR libelle_ecriture ILIKE '%ouverture%2024%'
                  OR type_ecriture ILIKE '%BILAN%'
                  OR type_ecriture ILIKE '%OUVERTURE%'
                  OR date_ecriture = (
                      SELECT date_debut FROM exercices_comptables WHERE id = %s
                  )
              )
            ORDER BY date_ecriture, id
            LIMIT 20
        """, (exercice['id'], exercice['id']))

        bilan_ecritures = cur.fetchall()

        if bilan_ecritures:
            print(f"  ✅ {len(bilan_ecritures)} écritures potentielles trouvées :")
            print()
            print(f"{'ID':<6} {'Date':<12} {'Type':<30} {'Libellé'}")
            print("-" * 80)
            for e in bilan_ecritures:
                type_str = (e['type_ecriture'] or 'NULL')[:28]
                libelle_str = e['libelle_ecriture'][:40]
                print(f"{e['id']:<6} {str(e['date_ecriture']):<12} {type_str:<30} {libelle_str}")
        else:
            print("  ⚠️  Aucune écriture de bilan d'ouverture trouvée")
            print("     Le bilan d'ouverture 2024 n'a peut-être pas encore été créé")

    except Exception as e:
        print(f"❌ Erreur : {e}")
        raise
    finally:
        cur.close()
        conn.close()

    print()
    print("=" * 80)
    print("✅ Analyse terminée")
    print("=" * 80)

if __name__ == '__main__':
    main()
