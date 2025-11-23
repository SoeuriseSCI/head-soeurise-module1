#!/usr/bin/env python3
"""
Script de vérification du statut des exercices comptables
"""

import psycopg2
import os
from datetime import datetime

def check_exercices_status():
    """Vérifie et affiche le statut de tous les exercices comptables"""

    # Connexion à la base de données
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cur = conn.cursor()

    print("=" * 80)
    print("📊 STATUT DES EXERCICES COMPTABLES")
    print("=" * 80)
    print(f"Date vérification : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()

    # Récupérer tous les exercices
    cur.execute("""
        SELECT
            id,
            annee,
            statut,
            date_debut,
            date_fin,
            date_cloture,
            resultat_exercice,
            created_at
        FROM exercices_comptables
        ORDER BY annee
    """)

    exercices = cur.fetchall()

    if not exercices:
        print("⚠️  Aucun exercice trouvé dans la base de données")
        return

    print(f"Nombre total d'exercices : {len(exercices)}")
    print()

    # Afficher chaque exercice
    for ex in exercices:
        ex_id, annee, statut, date_debut, date_fin, date_cloture, resultat, created_at = ex

        print("─" * 80)
        print(f"🗓️  EXERCICE {annee}")
        print("─" * 80)
        print(f"  ID                  : {ex_id}")
        print(f"  Statut              : {statut}")
        print(f"  Date début          : {date_debut}")
        print(f"  Date fin            : {date_fin}")
        print(f"  Date clôture        : {date_cloture if date_cloture else 'Non clôturé'}")
        print(f"  Résultat exercice   : {resultat:,.2f} €" if resultat else "  Résultat exercice   : Non calculé")
        print(f"  Créé le             : {created_at}")

        # Compter les écritures pour cet exercice
        cur.execute("""
            SELECT COUNT(*), SUM(montant_debit), SUM(montant_credit)
            FROM ecritures_comptables
            WHERE exercice_id = %s
        """, (ex_id,))

        nb_ecritures, total_debit, total_credit = cur.fetchone()

        print(f"  Écritures           : {nb_ecritures}")
        if nb_ecritures > 0:
            print(f"  Total débits        : {total_debit:,.2f} €" if total_debit else "  Total débits        : 0.00 €")
            print(f"  Total crédits       : {total_credit:,.2f} €" if total_credit else "  Total crédits       : 0.00 €")

            # Vérifier l'équilibre
            if total_debit and total_credit:
                diff = abs(total_debit - total_credit)
                if diff < 0.01:
                    print(f"  ✅ Équilibre        : VALIDE (différence {diff:.2f} €)")
                else:
                    print(f"  ⚠️  Équilibre        : DÉSÉQUILIBRÉ (différence {diff:.2f} €)")

        print()

    print("=" * 80)

    # Statistiques globales
    cur.execute("SELECT COUNT(*) FROM ecritures_comptables")
    total_ecritures = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM prets_immobiliers")
    total_prets = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM echeances_prets")
    total_echeances = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM propositions_en_attente WHERE statut = 'EN_ATTENTE'")
    total_propositions_attente = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM propositions_en_attente WHERE statut = 'VALIDEE'")
    total_propositions_validees = cur.fetchone()[0]

    print("📈 STATISTIQUES GLOBALES")
    print("─" * 80)
    print(f"  Total écritures comptables       : {total_ecritures}")
    print(f"  Total prêts immobiliers          : {total_prets}")
    print(f"  Total échéances prêts            : {total_echeances}")
    print(f"  Propositions en attente          : {total_propositions_attente}")
    print(f"  Propositions validées            : {total_propositions_validees}")
    print("=" * 80)

    cur.close()
    conn.close()

if __name__ == '__main__':
    try:
        check_exercices_status()
    except Exception as e:
        print(f"❌ ERREUR : {e}")
        import traceback
        traceback.print_exc()
