#!/usr/bin/env python3
"""
Vérification du Bilan d'Ouverture 2024
======================================

Vérifie que le bilan d'ouverture 2024 est équilibré et cohérent.

PRINCIPE COMPTABLE :
- Bilan ouverture exercice N = Bilan clôture exercice N-1
- Compte 89 (Bilan) = contrepartie universelle
- ACTIF débités → crédit 89 / PASSIF crédités → débit 89
- Total débits = Total crédits (équilibre)

COMPTES NÉGATIFS (inversions normales) :
- 290 (Provisions actif négatif) → Débit 89 / Crédit 290
- 120 (Report à nouveau négatif) → Débit 120 / Crédit 89
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
    print("🔍 VÉRIFICATION BILAN D'OUVERTURE 2024")
    print("=" * 80)
    print(f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 80)
    print()

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 1. Identifier l'exercice 2024
        print("[1/5] Identification exercice 2024...")
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

        # 2. Récupérer toutes les écritures du bilan d'ouverture
        print("[2/5] Récupération écritures bilan d'ouverture 2024...")
        cur.execute("""
            SELECT
                id,
                date_ecriture,
                compte_debit,
                compte_credit,
                montant,
                libelle_ecriture,
                type_ecriture
            FROM ecritures_comptables
            WHERE exercice_id = %s
              AND type_ecriture = 'BILAN_OUVERTURE'
            ORDER BY id
        """, (exercice['id'],))

        ecritures = cur.fetchall()

        if not ecritures:
            print("  ❌ Aucune écriture de bilan d'ouverture trouvée")
            return

        print(f"  ✅ {len(ecritures)} écritures de bilan d'ouverture")
        print()

        # 3. Afficher toutes les écritures
        print("[3/5] Détail des écritures bilan d'ouverture...")
        print()
        print(f"{'ID':<6} {'Date':<12} {'Débit':<8} {'Crédit':<8} {'Montant':>15} {'Libellé'}")
        print("-" * 80)

        for e in ecritures:
            print(f"{e['id']:<6} {str(e['date_ecriture']):<12} "
                  f"{e['compte_debit']:<8} {e['compte_credit']:<8} "
                  f"{e['montant']:>15,.2f} {e['libelle_ecriture'][:40]}")

        print()

        # 4. Calculer les totaux par compte
        print("[4/5] Calcul des totaux par compte...")
        print()

        # Totaux débits
        cur.execute("""
            SELECT
                compte_debit as compte,
                SUM(montant) as total
            FROM ecritures_comptables
            WHERE exercice_id = %s
              AND type_ecriture = 'BILAN_OUVERTURE'
            GROUP BY compte_debit
            ORDER BY compte_debit
        """, (exercice['id'],))

        debits = {row['compte']: float(row['total']) for row in cur.fetchall()}

        # Totaux crédits
        cur.execute("""
            SELECT
                compte_credit as compte,
                SUM(montant) as total
            FROM ecritures_comptables
            WHERE exercice_id = %s
              AND type_ecriture = 'BILAN_OUVERTURE'
            GROUP BY compte_credit
            ORDER BY compte_credit
        """, (exercice['id'],))

        credits = {row['compte']: float(row['total']) for row in cur.fetchall()}

        # Afficher les totaux
        print("  DÉBITS :")
        total_debits = 0
        for compte in sorted(debits.keys()):
            montant = debits[compte]
            total_debits += montant
            print(f"    {compte:<8} : {montant:>15,.2f}€")
        print(f"    {'TOTAL':<8} : {total_debits:>15,.2f}€")
        print()

        print("  CRÉDITS :")
        total_credits = 0
        for compte in sorted(credits.keys()):
            montant = credits[compte]
            total_credits += montant
            print(f"    {compte:<8} : {montant:>15,.2f}€")
        print(f"    {'TOTAL':<8} : {total_credits:>15,.2f}€")
        print()

        # 5. Vérifier l'équilibre
        print("[5/5] Vérification de l'équilibre...")

        ecart = abs(total_debits - total_credits)

        if ecart < 0.01:  # Tolérance pour les arrondis
            print(f"  ✅ Bilan d'ouverture 2024 ÉQUILIBRÉ")
            print(f"     Total Débits  : {total_debits:,.2f}€")
            print(f"     Total Crédits : {total_credits:,.2f}€")
            print(f"     Écart         : {ecart:.2f}€")
        else:
            print(f"  ❌ DÉSÉQUILIBRE détecté")
            print(f"     Total Débits  : {total_debits:,.2f}€")
            print(f"     Total Crédits : {total_credits:,.2f}€")
            print(f"     ÉCART         : {ecart:,.2f}€")

        print()

        # Vérifications spécifiques
        print("=" * 80)
        print("📊 VÉRIFICATIONS SPÉCIFIQUES")
        print("=" * 80)
        print()

        # Compte 89 (Bilan)
        if '89' in debits or '89' in credits:
            debit_89 = debits.get('89', 0)
            credit_89 = credits.get('89', 0)
            solde_89 = debit_89 - credit_89

            print(f"  Compte 89 (Bilan) :")
            print(f"    Débit  : {debit_89:>15,.2f}€")
            print(f"    Crédit : {credit_89:>15,.2f}€")
            print(f"    Solde  : {solde_89:>15,.2f}€")

            if abs(solde_89) < 0.01:
                print(f"    ✅ Compte 89 soldé (normal)")
            else:
                print(f"    ⚠️  Compte 89 non soldé (vérifier)")
            print()

        # Compte 164 (Emprunts)
        if '164' in debits or '164' in credits:
            debit_164 = debits.get('164', 0)
            credit_164 = credits.get('164', 0)
            solde_164 = credit_164 - debit_164  # PASSIF créditeur

            print(f"  Compte 164 (Emprunts établissements crédit) :")
            print(f"    Débit  : {debit_164:>15,.2f}€ (remboursements)")
            print(f"    Crédit : {credit_164:>15,.2f}€ (emprunts)")
            print(f"    Solde  : {solde_164:>15,.2f}€ (PASSIF créditeur)")
            print()

        # Compte 4181 (Produits à recevoir)
        if '4181' in debits or '4181' in credits:
            debit_4181 = debits.get('4181', 0)
            credit_4181 = credits.get('4181', 0)
            solde_4181 = debit_4181 - credit_4181  # ACTIF débiteur

            print(f"  Compte 4181 (Produits à recevoir) :")
            print(f"    Débit  : {debit_4181:>15,.2f}€ (créances)")
            print(f"    Crédit : {credit_4181:>15,.2f}€ (encaissements)")
            print(f"    Solde  : {solde_4181:>15,.2f}€ (ACTIF débiteur)")
            print()

        # Vérifier si compte 161 encore présent (ne devrait pas)
        if '161' in debits or '161' in credits:
            print(f"  ⚠️  ATTENTION : Compte 161 encore présent dans bilan d'ouverture 2024!")
            print(f"      Débit  : {debits.get('161', 0):>15,.2f}€")
            print(f"      Crédit : {credits.get('161', 0):>15,.2f}€")
            print(f"      → Ce compte devrait être 164 (correction nécessaire)")
            print()
        else:
            print(f"  ✅ Compte 161 (obsolète) : Absent du bilan (correct)")
            print()

    except Exception as e:
        print(f"❌ Erreur : {e}")
        raise
    finally:
        cur.close()
        conn.close()

    print()
    print("=" * 80)
    print("✅ Vérification terminée")
    print("=" * 80)

if __name__ == '__main__':
    main()
