#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de correction : Produits à recevoir SCPI
Compte 412 (Créances douteuses) → 4181 (Produits à recevoir)

Contexte:
- Les 7 356 € de revenus SCPI du 4T 2023 ont été classés au compte 412
- Le compte 412 est pour "Créances douteuses ou litigieuses" (incorrect)
- Le compte correct est 4181 "Produits à recevoir"

Écriture concernée:
- ID: 363
- Date: 01/01/2024 (Bilan d'ouverture)
- Libellé: "Bilan ouverture 2024 - Créances diverses"
- Montant: 7 356 €
- Type: Débit 412 / Crédit 89 → Débit 4181
- Compte correct: 4181 "Produits à recevoir"
"""

import os
import psycopg2
from datetime import datetime

# =====================================
# Configuration
# =====================================
DATABASE_URL = os.environ.get('DATABASE_URL')

# =====================================
# Connexion Base de Données
# =====================================
def get_connection():
    """Connexion PostgreSQL"""
    return psycopg2.connect(DATABASE_URL)

# =====================================
# Main
# =====================================
def main():
    print("=" * 60)
    print("🔧 CORRECTION COMPTE PRODUITS À RECEVOIR : 412 → 4181")
    print("=" * 60)
    print(f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)

    conn = get_connection()
    cur = conn.cursor()

    try:
        # Étape 1 : Créer le compte 4181 s'il n'existe pas
        print("\n[1/3] Création du compte 4181 (si nécessaire)...")

        cur.execute("""
            INSERT INTO plans_comptes (numero_compte, libelle, type_compte, classe, actif)
            VALUES ('4181', 'Produits à recevoir', 'ACTIF', 4, true)
            ON CONFLICT (numero_compte) DO NOTHING
            RETURNING numero_compte;
        """)

        result = cur.fetchone()
        if result:
            print(f"  ✅ Compte 4181 créé: {result[0]}")
        else:
            print("  ℹ️  Compte 4181 existe déjà")

        # Étape 2 : Vérifier l'écriture actuelle
        print("\n[2/3] Vérification de l'écriture ID 363...")

        cur.execute("""
            SELECT id, date_ecriture, libelle_ecriture, compte_debit, compte_credit, montant
            FROM ecritures_comptables
            WHERE id = 363;
        """)

        ecriture = cur.fetchone()
        if not ecriture:
            print("  ❌ Écriture ID 363 non trouvée")
            return

        id_ecriture, date_ecriture, libelle, compte_debit, compte_credit, montant = ecriture
        print(f"  • ID {id_ecriture} | {date_ecriture}")
        print(f"  • Libellé: {libelle}")
        print(f"  • Débit {compte_debit} / Crédit {compte_credit}")
        print(f"  • Montant: {montant:.2f}€")

        if compte_debit == '4181':
            print("\n  ℹ️  Écriture déjà corrigée (compte débit = 4181)")
            return

        # Étape 3 : Corriger l'écriture
        print("\n[3/3] Correction de l'écriture...")
        print(f"  • Compte débit: {compte_debit} → 4181")
        print(f"  • Libellé: {libelle} → Bilan ouverture 2024 - Produits à recevoir")

        confirmation = input("\n❓ Confirmer la correction ? (oui/non) : ")
        if confirmation.lower() != 'oui':
            print("❌ Correction annulée")
            return

        cur.execute("""
            UPDATE ecritures_comptables
            SET compte_debit = '4181',
                libelle_ecriture = 'Bilan ouverture 2024 - Produits à recevoir'
            WHERE id = 363;
        """)

        print("  ✅ Écriture corrigée")

        # Vérification post-correction
        cur.execute("""
            SELECT id, date_ecriture, libelle_ecriture, compte_debit, compte_credit, montant
            FROM ecritures_comptables
            WHERE id = 363;
        """)

        ecriture_corrigee = cur.fetchone()
        id_ecriture, date_ecriture, libelle, compte_debit, compte_credit, montant = ecriture_corrigee

        print("\n📋 Vérification post-correction:")
        print(f"  • ID {id_ecriture} | {date_ecriture}")
        print(f"  • Libellé: {libelle}")
        print(f"  • Débit {compte_debit} / Crédit {compte_credit}")
        print(f"  • Montant: {montant:.2f}€")

        conn.commit()
        print("\n✅ Correction validée avec succès!")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Erreur lors de la correction: {e}")
        raise

    finally:
        cur.close()
        conn.close()

    print("\n" + "=" * 60)
    print("✅ Script terminé")
    print("=" * 60)

if __name__ == '__main__':
    main()
