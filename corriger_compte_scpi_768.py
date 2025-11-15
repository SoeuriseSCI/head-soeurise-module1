#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de correction : SCPI distributions de plus-value
Compte 106 (Réserves) → 768 (Autres produits financiers)

Contexte:
- Les 601 € distribués par la SCPI ne sont PAS des revenus trimestriels
- C'est un partage de plus-value suite à cession d'un bien immobilier
- Compte approprié : 768 "Autres produits financiers" (non 106 "Réserves")

Écriture concernée:
- Date: 24/04/2024
- Libellé: "SCPI EPARGNE PIERRE DISTRIB CAPITAL"
- Montant: 601 €
- Type: Débit 512 (Banque) / Crédit 106 (Réserves) → Crédit 768
- Nature: Distribution de réserves de plus-values (cession immobilière)
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
    """Identifie les écritures SCPI au compte 106 à corriger"""
    conn = get_connection()
    cur = conn.cursor()

    # Dans la comptabilité en partie double :
    # - Débit 512 (Banque) / Crédit 106 (Réserves)
    # On cherche donc les écritures où compte_credit = '106'
    query = """
    SELECT
        id,
        exercice_id,
        date_ecriture,
        numero_ecriture,
        libelle_ecriture,
        compte_debit,
        compte_credit,
        montant,
        type_ecriture
    FROM ecritures_comptables
    WHERE compte_credit = '106'
      AND (
          libelle_ecriture ILIKE '%SCPI EPARGNE PIERRE%'
          OR libelle_ecriture ILIKE '%VIR SEPA SCPI%'
          OR libelle_ecriture ILIKE '%DISTRIB CAPITAL%'
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
    """Corrige les écritures : compte 106 → 768"""

    if not ecritures:
        print("❌ Aucune écriture à corriger trouvée")
        return

    print(f"\n📊 {len(ecritures)} écriture(s) à corriger identifiée(s):\n")

    total_montant = 0
    for ecriture in ecritures:
        (id_ecriture, exercice_id, date_ecriture, numero_ecriture,
         libelle_ecriture, compte_debit, compte_credit, montant, type_ecriture) = ecriture
        total_montant += montant

        print(f"  • ID {id_ecriture} | {date_ecriture} | {libelle_ecriture[:50]}...")
        print(f"    Écriture: Débit {compte_debit} / Crédit {compte_credit} | Montant: {montant:.2f}€")

    print(f"\n💰 Total concerné: {total_montant:.2f}€")

    if DRY_RUN:
        print("\n⚠️  MODE DRY-RUN : Aucune modification effectuée")
        return

    # Confirmation
    print("\n🔧 Correction à effectuer:")
    print("   Compte crédit 106 (Réserves) → 768 (Autres produits financiers)")

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

            # UPDATE compte_credit 106 → 768
            cur.execute("""
                UPDATE ecritures_comptables
                SET compte_credit = '768'
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

    # Vérifier compte 768
    cur.execute("""
        SELECT COUNT(*), SUM(montant)
        FROM ecritures_comptables
        WHERE compte_credit = '768'
          AND (
              libelle_ecriture ILIKE '%SCPI EPARGNE PIERRE%'
              OR libelle_ecriture ILIKE '%VIR SEPA SCPI%'
              OR libelle_ecriture ILIKE '%DISTRIB CAPITAL%'
          )
    """)

    count_768, sum_768 = cur.fetchone()

    # Vérifier compte 106 (ne doit plus contenir ces écritures)
    cur.execute("""
        SELECT COUNT(*)
        FROM ecritures_comptables
        WHERE compte_credit = '106'
          AND (
              libelle_ecriture ILIKE '%SCPI EPARGNE PIERRE%'
              OR libelle_ecriture ILIKE '%VIR SEPA SCPI%'
              OR libelle_ecriture ILIKE '%DISTRIB CAPITAL%'
          )
    """)

    count_106 = cur.fetchone()[0]

    cur.close()
    conn.close()

    print("\n📋 Vérification post-correction:")
    print(f"   Compte 768 (crédit) : {count_768} écriture(s) | {sum_768 or 0:.2f}€")
    print(f"   Compte 106 (crédit) : {count_106} écriture(s)")

    if count_106 == 0 and count_768 > 0:
        print("\n✅ Correction validée avec succès!")
    else:
        print("\n⚠️  Vérification à compléter")

# =====================================
# Main
# =====================================
def main():
    print("=" * 60)
    print("🔧 CORRECTION COMPTE SCPI : 106 → 768")
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
