#!/usr/bin/env python3
"""
Correction Compte 622 → 6226 (Honoraires)
==========================================

PROBLÈME IDENTIFIÉ :
- Compte 622 = Rémunérations d'intermédiaires et honoraires (trop général)
- Compte 6226 = Honoraires (sous-compte précis)

La SCI Soeurise utilise ce compte pour les honoraires comptables.
→ Le compte 6226 est plus approprié et précis.

ACTIONS :
1. Créer compte 6226 dans plans_comptes
2. Marquer compte 622 comme obsolète
3. Corriger TOUTES les écritures : 622 → 6226
4. Vérifier résultats

IMPACT :
- Bilan d'ouverture 2024 (si présent)
- Toutes les écritures d'honoraires comptables 2024
- Classification plus précise selon PCG
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
    print("🔧 CORRECTION COMPTE HONORAIRES : 622 → 6226")
    print("=" * 80)
    print(f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 80)
    print()

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 1. Créer le compte 6226
        print("[1/5] Création compte 6226 (Honoraires)...")
        try:
            cur.execute("""
                INSERT INTO plans_comptes (numero_compte, libelle, type_compte, classe, actif)
                VALUES ('6226', 'Honoraires', 'CHARGE', 6, true)
                ON CONFLICT (numero_compte) DO NOTHING
            """)
            conn.commit()

            # Vérifier si le compte existait déjà
            cur.execute("SELECT numero_compte FROM plans_comptes WHERE numero_compte = '6226'")
            if cur.rowcount > 0:
                print("  ✅ Compte 6226 créé/existe")
            else:
                print("  ℹ️  Compte 6226 existe déjà")
        except Exception as e:
            print(f"  ⚠️  Erreur création compte 6226 : {e}")
            conn.rollback()

        # 2. Modifier le libellé du compte 622 pour indiquer obsolescence
        print()
        print("[2/5] Modification libellé compte 622...")
        try:
            cur.execute("""
                UPDATE plans_comptes
                SET libelle = 'Rémunérations intermédiaires et honoraires (OBSOLETE - Utiliser 6226)',
                    actif = false
                WHERE numero_compte = '622'
            """)
            conn.commit()
            print("  ✅ Compte 622 marqué comme obsolète")
        except Exception as e:
            print(f"  ⚠️  Erreur modification compte 622 : {e}")
            conn.rollback()

        # 3. Analyser les écritures à corriger
        print()
        print("[3/5] Analyse des écritures à corriger...")

        # Compter les écritures avec compte 622
        cur.execute("""
            SELECT COUNT(*) as total
            FROM ecritures_comptables
            WHERE compte_debit = '622' OR compte_credit = '622'
        """)
        total = cur.fetchone()['total']

        if total == 0:
            print("  ℹ️  Aucune écriture à corriger")
            return

        # Détail par type
        cur.execute("""
            SELECT COUNT(*) as nb
            FROM ecritures_comptables
            WHERE compte_credit = '622'
        """)
        nb_credits = cur.fetchone()['nb']

        cur.execute("""
            SELECT COUNT(*) as nb
            FROM ecritures_comptables
            WHERE compte_debit = '622'
        """)
        nb_debits = cur.fetchone()['nb']

        print(f"  📊 Écritures avec compte 622 : {total}")
        print(f"    - CREDIT 622 : {nb_credits} écritures")
        print(f"    - DEBIT 622 : {nb_debits} écritures")

        # 4. Corriger les écritures
        print()
        print("[4/5] Correction des écritures...")
        print(f"  ⚠️  {total} écritures vont être modifiées")
        print()

        # Demander confirmation
        reponse = input("❓ Confirmer la correction 622 → 6226 ? (oui/non) : ").strip().lower()
        if reponse != 'oui':
            print("  ❌ Correction annulée")
            return

        # Corriger les débits
        cur.execute("""
            UPDATE ecritures_comptables
            SET compte_debit = '6226'
            WHERE compte_debit = '622'
        """)
        nb_debits_corriges = cur.rowcount

        # Corriger les crédits
        cur.execute("""
            UPDATE ecritures_comptables
            SET compte_credit = '6226'
            WHERE compte_credit = '622'
        """)
        nb_credits_corriges = cur.rowcount

        conn.commit()

        print(f"  ✅ Débits corrigés : {nb_debits_corriges} écritures")
        print(f"  ✅ Crédits corrigés : {nb_credits_corriges} écritures")

        # 5. Vérifier les résultats
        print()
        print("[5/5] Vérification post-correction...")

        # Calculer le total du compte 6226
        cur.execute("""
            SELECT
                SUM(CASE WHEN compte_debit = '6226' THEN montant ELSE 0 END) as total_debit,
                SUM(CASE WHEN compte_credit = '6226' THEN montant ELSE 0 END) as total_credit
            FROM ecritures_comptables
        """)
        result = cur.fetchone()

        total_debit = float(result['total_debit'] or 0)
        total_credit = float(result['total_credit'] or 0)
        solde = total_debit - total_credit  # CHARGE débitrice

        print(f"  📊 Compte 6226 (Honoraires) :")
        print(f"      Total Débit  : {total_debit:>15,.2f}€ (charges)")
        print(f"      Total Crédit : {total_credit:>15,.2f}€")
        print(f"      Solde (débiteur) : {solde:>15,.2f}€ (CHARGE)")

        # Vérifier qu'il ne reste plus d'écritures sur 622
        cur.execute("""
            SELECT COUNT(*) as reste
            FROM ecritures_comptables
            WHERE compte_debit = '622' OR compte_credit = '622'
        """)
        reste = cur.fetchone()['reste']

        print()
        if reste == 0:
            print(f"  ✅ Aucune écriture restante sur compte 622")
        else:
            print(f"  ⚠️  ATTENTION : {reste} écritures restent sur compte 622")

        print()
        print("✅ Correction validée avec succès!")

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
