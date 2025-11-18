#!/usr/bin/env python3
"""
Correction Compte 401 → 4081 (Factures non parvenues)
======================================================

PROBLÈME IDENTIFIÉ :
- Compte 401 = Fournisseurs (dettes génériques)
- Compte 4081 = Fournisseurs - Factures non parvenues (provisions pour factures attendues)

La SCI Soeurise utilise ce compte pour provisionner les honoraires comptables
en fin d'année avant réception de la facture.
→ Le compte 4081 est plus approprié et précis.

CONTEXTE :
- Bilan 2023 : 653€ au compte 401 "Fournisseurs"
- Il s'agit d'honoraires comptables provisionnés
- Devrait être au compte 4081 (Factures non parvenues)

ACTIONS :
1. Créer compte 4081 dans plans_comptes
2. Marquer compte 401 comme obsolète (ou ajuster libellé)
3. Corriger TOUTES les écritures : 401 → 4081
4. Vérifier résultats

IMPACT :
- Bilan d'ouverture 2024 (653€)
- Autres écritures de provisions pour factures
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
    print("🔧 CORRECTION COMPTE FOURNISSEURS : 401 → 4081")
    print("=" * 80)
    print(f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 80)
    print()

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 1. Créer le compte 4081
        print("[1/5] Création compte 4081 (Fournisseurs - Factures non parvenues)...")
        try:
            cur.execute("""
                INSERT INTO plans_comptes (numero_compte, libelle, type_compte, classe, actif)
                VALUES ('4081', 'Fournisseurs - Factures non parvenues', 'PASSIF', 4, true)
                ON CONFLICT (numero_compte) DO NOTHING
            """)
            conn.commit()

            # Vérifier si le compte existait déjà
            cur.execute("SELECT numero_compte FROM plans_comptes WHERE numero_compte = '4081'")
            if cur.rowcount > 0:
                print("  ✅ Compte 4081 créé/existe")
            else:
                print("  ℹ️  Compte 4081 existe déjà")
        except Exception as e:
            print(f"  ⚠️  Erreur création compte 4081 : {e}")
            conn.rollback()

        # 2. Modifier le libellé du compte 401
        print()
        print("[2/5] Modification libellé compte 401...")
        try:
            cur.execute("""
                UPDATE plans_comptes
                SET libelle = 'Fournisseurs (OBSOLETE pour factures non parvenues - Utiliser 4081)',
                    actif = false
                WHERE numero_compte = '401'
            """)
            conn.commit()
            print("  ✅ Compte 401 marqué comme obsolète pour provisions")
        except Exception as e:
            print(f"  ⚠️  Erreur modification compte 401 : {e}")
            conn.rollback()

        # 3. Analyser les écritures à corriger
        print()
        print("[3/5] Analyse des écritures à corriger...")

        # Compter les écritures avec compte 401
        cur.execute("""
            SELECT COUNT(*) as total
            FROM ecritures_comptables
            WHERE compte_debit = '401' OR compte_credit = '401'
        """)
        total = cur.fetchone()['total']

        if total == 0:
            print("  ℹ️  Aucune écriture à corriger")
            return

        # Détail par type
        cur.execute("""
            SELECT COUNT(*) as nb
            FROM ecritures_comptables
            WHERE compte_credit = '401'
        """)
        nb_credits = cur.fetchone()['nb']

        cur.execute("""
            SELECT COUNT(*) as nb
            FROM ecritures_comptables
            WHERE compte_debit = '401'
        """)
        nb_debits = cur.fetchone()['nb']

        print(f"  📊 Écritures avec compte 401 : {total}")
        print(f"    - CREDIT 401 : {nb_credits} écritures (provisions)")
        print(f"    - DEBIT 401 : {nb_debits} écritures (paiements)")

        # Afficher détail des écritures
        print()
        print("  📋 Détail des écritures à corriger :")
        cur.execute("""
            SELECT
                id,
                date_ecriture,
                type_ecriture,
                compte_debit,
                compte_credit,
                montant,
                libelle_ecriture
            FROM ecritures_comptables
            WHERE compte_debit = '401' OR compte_credit = '401'
            ORDER BY date_ecriture, id
        """)

        ecritures = cur.fetchall()
        for e in ecritures:
            sens = "CRÉDIT 401" if e['compte_credit'] == '401' else "DÉBIT 401"
            print(f"     {e['id']:<6} {str(e['date_ecriture']):<12} {sens:<12} "
                  f"{e['montant']:>10,.2f}€ {e['libelle_ecriture'][:40]}")

        # 4. Corriger les écritures
        print()
        print("[4/5] Correction des écritures...")
        print(f"  ⚠️  {total} écritures vont être modifiées")
        print()

        # Demander confirmation
        reponse = input("❓ Confirmer la correction 401 → 4081 ? (oui/non) : ").strip().lower()
        if reponse != 'oui':
            print("  ❌ Correction annulée")
            return

        # Corriger les débits
        cur.execute("""
            UPDATE ecritures_comptables
            SET compte_debit = '4081'
            WHERE compte_debit = '401'
        """)
        nb_debits_corriges = cur.rowcount

        # Corriger les crédits
        cur.execute("""
            UPDATE ecritures_comptables
            SET compte_credit = '4081'
            WHERE compte_credit = '401'
        """)
        nb_credits_corriges = cur.rowcount

        conn.commit()

        print(f"  ✅ Débits corrigés : {nb_debits_corriges} écritures")
        print(f"  ✅ Crédits corrigés : {nb_credits_corriges} écritures")

        # 5. Vérifier les résultats
        print()
        print("[5/5] Vérification post-correction...")

        # Calculer le total du compte 4081
        cur.execute("""
            SELECT
                SUM(CASE WHEN compte_debit = '4081' THEN montant ELSE 0 END) as total_debit,
                SUM(CASE WHEN compte_credit = '4081' THEN montant ELSE 0 END) as total_credit
            FROM ecritures_comptables
        """)
        result = cur.fetchone()

        total_debit = float(result['total_debit'] or 0)
        total_credit = float(result['total_credit'] or 0)
        solde = total_credit - total_debit  # PASSIF créditeur

        print(f"  📊 Compte 4081 (Factures non parvenues) :")
        print(f"      Total Débit  : {total_debit:>15,.2f}€ (paiements)")
        print(f"      Total Crédit : {total_credit:>15,.2f}€ (provisions)")
        print(f"      Solde (créditeur) : {solde:>15,.2f}€ (PASSIF)")

        # Vérifier qu'il ne reste plus d'écritures sur 401
        cur.execute("""
            SELECT COUNT(*) as reste
            FROM ecritures_comptables
            WHERE compte_debit = '401' OR compte_credit = '401'
        """)
        reste = cur.fetchone()['reste']

        print()
        if reste == 0:
            print(f"  ✅ Aucune écriture restante sur compte 401")
        else:
            print(f"  ⚠️  ATTENTION : {reste} écritures restent sur compte 401")

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
