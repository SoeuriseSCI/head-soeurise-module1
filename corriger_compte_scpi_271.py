#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de correction : Parts SCPI - Classification correcte
Compte 280 (Amortissements) → 271 (Titres immobilisés)

Contexte:
- Les parts de SCPI Epargne Pierre (500 032 €) ont été classées au compte 280
- Le compte 280 est pour les "Amortissements des immobilisations incorporelles"
- Les parts de SCPI sont des immobilisations financières, pas des amortissements

Écriture concernée:
- Date: 01/01/2023 (Bilan d'ouverture)
- Libellé: "Titres immobilisés" ou "SCPI Epargne Pierre"
- Montant: 500 032 €
- Compte correct: 271 "Titres immobilisés (autres que TIAP)"
"""

import os
import psycopg2
from datetime import datetime

# =====================================
# Configuration
# =====================================
DATABASE_URL = os.environ.get('DATABASE_URL')
DRY_RUN = False  # False = exécution réelle

# =====================================
# Connexion Base de Données
# =====================================
def get_connection():
    """Connexion PostgreSQL"""
    return psycopg2.connect(DATABASE_URL)

# =====================================
# Identification des écritures
# =====================================
def identifier_ecritures_scpi():
    """Identifie les écritures SCPI au compte 280 à corriger"""
    conn = get_connection()
    cur = conn.cursor()

    query = """
    SELECT
        id,
        exercice_id,
        date_ecriture,
        compte_id,
        libelle,
        debit,
        credit,
        type_ecriture
    FROM ecritures_comptables
    WHERE compte_id = '280'
      AND (
          libelle ILIKE '%SCPI%'
          OR libelle ILIKE '%Titres immobilisés%'
      )
    ORDER BY date_ecriture;
    """

    cur.execute(query)
    ecritures = cur.fetchall()

    cur.close()
    conn.close()

    return ecritures

# =====================================
# Correction des écritures
# =====================================
def corriger_ecritures(ecritures):
    """Corrige les écritures : compte 280 → 271"""

    if not ecritures:
        print("❌ Aucune écriture à corriger trouvée")
        return

    print(f"\n📊 {len(ecritures)} écriture(s) à corriger identifiée(s):\n")

    total_montant = 0
    for ecriture in ecritures:
        id_ecriture, exercice_id, date_ecriture, compte_id, libelle, debit, credit, type_ecriture = ecriture
        montant = debit if debit > 0 else credit
        total_montant += montant

        print(f"  • ID {id_ecriture} | {date_ecriture} | {libelle[:50]}...")
        print(f"    Compte: {compte_id} | Débit: {debit:.2f}€ | Crédit: {credit:.2f}€")

    print(f"\n💰 Total concerné: {total_montant:.2f}€")
    print(f"💡 Montant attendu: 500 032.00€")

    if DRY_RUN:
        print("\n⚠️  MODE DRY-RUN : Aucune modification effectuée")
        return

    # Confirmation
    print("\n🔧 Correction à effectuer:")
    print("   Compte 280 (Amortissements) → 271 (Titres immobilisés)")

    confirmation = input("\n❓ Confirmer la correction ? (oui/non) : ")
    if confirmation.lower() != 'oui':
        print("❌ Correction annulée")
        return

    # Exécution
    conn = get_connection()
    cur = conn.cursor()

    try:
        for ecriture in ecritures:
            id_ecriture = ecriture[0]

            # UPDATE compte 280 → 271
            cur.execute("""
                UPDATE ecritures_comptables
                SET compte_id = '271'
                WHERE id = %s
            """, (id_ecriture,))

            print(f"  ✅ Écriture {id_ecriture} corrigée")

        conn.commit()
        print(f"\n✅ {len(ecritures)} écriture(s) corrigée(s) avec succès")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Erreur lors de la correction: {e}")
        raise

    finally:
        cur.close()
        conn.close()

# =====================================
# Vérification post-correction
# =====================================
def verifier_correction():
    """Vérifie que les écritures ont bien été corrigées"""
    conn = get_connection()
    cur = conn.cursor()

    # Vérifier compte 271
    cur.execute("""
        SELECT COUNT(*), SUM(debit), SUM(credit)
        FROM ecritures_comptables
        WHERE compte_id = '271'
          AND (
              libelle ILIKE '%SCPI%'
              OR libelle ILIKE '%Titres immobilisés%'
          )
    """)

    count_271, sum_debit_271, sum_credit_271 = cur.fetchone()
    total_271 = (sum_debit_271 or 0) + (sum_credit_271 or 0)

    # Vérifier compte 280 (ne doit plus contenir ces écritures)
    cur.execute("""
        SELECT COUNT(*)
        FROM ecritures_comptables
        WHERE compte_id = '280'
          AND (
              libelle ILIKE '%SCPI%'
              OR libelle ILIKE '%Titres immobilisés%'
          )
    """)

    count_280 = cur.fetchone()[0]

    cur.close()
    conn.close()

    print("\n📋 Vérification post-correction:")
    print(f"   Compte 271 : {count_271} écriture(s) | {total_271:.2f}€")
    print(f"   Compte 280 : {count_280} écriture(s)")
    print(f"   ✅ Attendu : 500 032.00€ au compte 271")

    if count_280 == 0 and count_271 > 0:
        print("\n✅ Correction validée avec succès!")
    else:
        print("\n⚠️  Vérification à compléter")

# =====================================
# Main
# =====================================
def main():
    print("=" * 60)
    print("🔧 CORRECTION COMPTE SCPI : 280 → 271")
    print("=" * 60)
    print(f"Mode: {'DRY-RUN' if DRY_RUN else 'EXÉCUTION RÉELLE'}")
    print(f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)

    # Étape 1 : Identifier
    print("\n[1/3] Identification des écritures...")
    ecritures = identifier_ecritures_scpi()

    # Étape 2 : Corriger
    print("\n[2/3] Correction des écritures...")
    corriger_ecritures(ecritures)

    # Étape 3 : Vérifier
    if not DRY_RUN and ecritures:
        print("\n[3/3] Vérification...")
        verifier_correction()

    print("\n" + "=" * 60)
    print("✅ Script terminé")
    print("=" * 60)

if __name__ == '__main__':
    main()
