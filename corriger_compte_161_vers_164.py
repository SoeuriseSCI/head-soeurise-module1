#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de correction : Compte 161 → 164
Emprunts obligataires → Emprunts établissements de crédit

Contexte:
- Compte 161 = Emprunts obligataires convertibles (INCORRECT pour SCI)
- Compte 164 = Emprunts auprès établissements de crédit (CORRECT)
- Prêts LCL + INVESTIMUR = emprunts bancaires → 164

Corrections à effectuer:
1. Plan comptable: Créer compte 164, modifier libellé 161
2. Bilan d'ouverture 2024: Crédit 161 → Crédit 164
3. Tous les remboursements 2024: Débit 161 → Débit 164
"""

import os
import psycopg2
from datetime import datetime

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def main():
    print("=" * 80)
    print("🔧 CORRECTION COMPTE EMPRUNTS : 161 → 164")
    print("=" * 80)
    print(f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 80)

    conn = get_connection()
    cur = conn.cursor()

    try:
        # ÉTAPE 1: Créer compte 164 s'il n'existe pas
        print("\n[1/5] Création compte 164 (Emprunts établissements de crédit)...")

        cur.execute("""
            INSERT INTO plans_comptes (numero_compte, libelle, type_compte, classe, actif)
            VALUES ('164', 'Emprunts auprès des établissements de crédit', 'PASSIF', 1, true)
            ON CONFLICT (numero_compte) DO NOTHING
            RETURNING numero_compte;
        """)

        result = cur.fetchone()
        if result:
            print(f"  ✅ Compte 164 créé")
        else:
            print(f"  ℹ️  Compte 164 existe déjà")

        # ÉTAPE 2: Modifier libellé compte 161 pour clarté
        print("\n[2/5] Modification libellé compte 161...")

        cur.execute("""
            UPDATE plans_comptes
            SET libelle = 'Emprunts obligataires convertibles (OBSOLETE - Utiliser 164)',
                actif = false
            WHERE numero_compte = '161';
        """)
        print("  ✅ Compte 161 marqué comme obsolète")

        # ÉTAPE 3: Compter les écritures à corriger
        print("\n[3/5] Analyse des écritures à corriger...")

        cur.execute("""
            SELECT COUNT(*)
            FROM ecritures_comptables
            WHERE compte_debit = '161' OR compte_credit = '161';
        """)
        nb_ecritures = cur.fetchone()[0]
        print(f"  📊 Écritures avec compte 161 : {nb_ecritures}")

        if nb_ecritures == 0:
            print("  ℹ️  Aucune écriture à corriger")
            return

        # Détail par type
        cur.execute("""
            SELECT
                CASE
                    WHEN compte_debit = '161' THEN 'DEBIT'
                    WHEN compte_credit = '161' THEN 'CREDIT'
                END as type,
                COUNT(*) as nb
            FROM ecritures_comptables
            WHERE compte_debit = '161' OR compte_credit = '161'
            GROUP BY type;
        """)

        for row in cur.fetchall():
            print(f"    - {row[0]} 161 : {row[1]} écritures")

        # ÉTAPE 4: Confirmation
        print("\n[4/5] Correction des écritures...")
        print(f"  ⚠️  {nb_ecritures} écritures vont être modifiées")

        confirmation = input("\n❓ Confirmer la correction 161 → 164 ? (oui/non) : ")
        if confirmation.lower() != 'oui':
            print("❌ Correction annulée")
            return

        # Corriger les débits
        cur.execute("""
            UPDATE ecritures_comptables
            SET compte_debit = '164'
            WHERE compte_debit = '161';
        """)
        nb_debit = cur.rowcount
        print(f"  ✅ Débits corrigés : {nb_debit} écritures")

        # Corriger les crédits
        cur.execute("""
            UPDATE ecritures_comptables
            SET compte_credit = '164'
            WHERE compte_credit = '161';
        """)
        nb_credit = cur.rowcount
        print(f"  ✅ Crédits corrigés : {nb_credit} écritures")

        # ÉTAPE 5: Vérification post-correction
        print("\n[5/5] Vérification post-correction...")

        # Vérifier solde compte 164
        cur.execute("""
            SELECT
                SUM(CASE WHEN compte_debit = '164' THEN montant ELSE 0 END) as total_debit,
                SUM(CASE WHEN compte_credit = '164' THEN montant ELSE 0 END) as total_credit
            FROM ecritures_comptables;
        """)

        debit, credit = cur.fetchone()
        solde = (credit or 0) - (debit or 0)

        print(f"  📊 Compte 164 (Emprunts établissements de crédit) :")
        print(f"      Total Débit  : {debit:>12.2f}€ (remboursements capital)")
        print(f"      Total Crédit : {credit:>12.2f}€ (emprunts initiaux)")
        print(f"      Solde (créditeur) : {solde:>12.2f}€ (PASSIF)")

        # Vérifier qu'il ne reste rien sur 161
        cur.execute("""
            SELECT COUNT(*)
            FROM ecritures_comptables
            WHERE compte_debit = '161' OR compte_credit = '161';
        """)
        nb_restant = cur.fetchone()[0]

        if nb_restant == 0:
            print(f"\n  ✅ Aucune écriture restante sur compte 161")
        else:
            print(f"\n  ⚠️  {nb_restant} écritures restent sur compte 161 (anormal)")

        conn.commit()
        print("\n✅ Correction validée avec succès!")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Erreur lors de la correction: {e}")
        raise

    finally:
        cur.close()
        conn.close()

    print("\n" + "=" * 80)
    print("✅ Script terminé")
    print("=" * 80)

if __name__ == '__main__':
    main()
