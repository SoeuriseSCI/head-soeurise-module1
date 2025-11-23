#!/usr/bin/env python3
"""
Script de vérification détaillée du statut des exercices
"""

import json
from collections import defaultdict

def check_exercices_detailed(backup_file):
    """Vérifie et affiche le statut détaillé des exercices"""

    with open(backup_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Extraire les infos de sauvegarde
    metadata = data.get('metadata', {})
    backup_date = metadata.get('backup_date', 'Inconnue')

    print("=" * 80)
    print("📊 STATUT DÉTAILLÉ DES EXERCICES COMPTABLES")
    print("=" * 80)
    print(f"Source           : {backup_file}")
    print(f"Date sauvegarde  : {backup_date}")
    print()

    # Récupérer les données
    exercices = data.get('exercices', [])
    ecritures = data.get('ecritures', [])
    prets = data.get('prets', [])
    echeances = data.get('echeances', [])

    if not exercices:
        print("⚠️  Aucun exercice trouvé")
        return

    print(f"📋 RÉSUMÉ : {len(exercices)} exercices trouvés")
    print()

    # Organiser les écritures par exercice
    ecritures_by_ex = defaultdict(list)
    for ecriture in ecritures:
        ex_id = ecriture.get('exercice_id')
        ecritures_by_ex[ex_id].append(ecriture)

    # Afficher chaque exercice
    for ex in sorted(exercices, key=lambda x: x['annee']):
        ex_id = ex['id']
        annee = ex['annee']
        statut = ex['statut']
        date_debut = ex['date_debut']
        date_fin = ex['date_fin']
        date_cloture = ex.get('date_cloture')
        resultat = ex.get('resultat_exercice')

        print("─" * 80)
        print(f"🗓️  EXERCICE {annee}")
        print("─" * 80)
        print(f"  ID                  : {ex_id}")
        print(f"  Statut              : {statut}")
        print(f"  Date début          : {date_debut}")
        print(f"  Date fin            : {date_fin}")
        print(f"  Date clôture        : {date_cloture if date_cloture else '❌ Non renseignée'}")

        if resultat is not None:
            print(f"  Résultat exercice   : {float(resultat):,.2f} €")
        else:
            print(f"  Résultat exercice   : ❌ Non calculé")

        # Statistiques des écritures
        ex_ecritures = ecritures_by_ex.get(ex_id, [])
        nb_ecritures = len(ex_ecritures)

        print()
        print(f"  📝 ÉCRITURES        : {nb_ecritures} enregistrements")

        if nb_ecritures > 0:
            # Calculer les totaux (somme des montants débits et crédits)
            total_montants = sum(float(e.get('montant', 0)) for e in ex_ecritures)

            print(f"     Total mouvements : {total_montants:,.2f} €")

            # Compter par type
            types_count = defaultdict(int)
            for e in ex_ecritures:
                type_e = e.get('type_ecriture', 'INCONNU')
                types_count[type_e] += 1

            print(f"     Types distincts  : {len(types_count)}")

            # Afficher les 5 types les plus fréquents
            top_types = sorted(types_count.items(), key=lambda x: x[1], reverse=True)[:5]
            for type_e, count in top_types:
                print(f"       • {type_e}: {count}")

            # Vérifier l'équilibre (calcul débits/crédits par compte)
            balance_debits = defaultdict(float)
            balance_credits = defaultdict(float)

            for e in ex_ecritures:
                montant = float(e.get('montant', 0))
                compte_debit = e.get('compte_debit', '')
                compte_credit = e.get('compte_credit', '')

                if compte_debit:
                    balance_debits[compte_debit] += montant
                if compte_credit:
                    balance_credits[compte_credit] += montant

            total_debits = sum(balance_debits.values())
            total_credits = sum(balance_credits.values())
            diff = abs(total_debits - total_credits)

            print()
            print(f"  💰 ÉQUILIBRE")
            print(f"     Total débits     : {total_debits:,.2f} €")
            print(f"     Total crédits    : {total_credits:,.2f} €")

            if diff < 0.01:
                print(f"     ✅ Équilibré     : OUI (diff {diff:.4f} €)")
            else:
                print(f"     ⚠️  Équilibré     : NON (diff {diff:.2f} €)")

        # Analyse du statut
        print()
        print(f"  🔍 ANALYSE")

        issues = []

        if statut == 'CLOTURE':
            if not date_cloture:
                issues.append("❌ Statut CLOTURE mais date_cloture manquante")
            if resultat is None:
                issues.append("⚠️  Résultat non calculé")

        if statut == 'OUVERT' and annee < 2025:
            issues.append(f"⚠️  Exercice {annee} encore OUVERT (devrait être clôturé)")

        if nb_ecritures == 0:
            issues.append("⚠️  Aucune écriture comptable")

        if issues:
            for issue in issues:
                print(f"     {issue}")
        else:
            print(f"     ✅ Aucun problème détecté")

        print()

    print("=" * 80)

    # Statistiques globales
    print("📈 STATISTIQUES GLOBALES")
    print("─" * 80)
    print(f"  Exercices comptables             : {len(exercices)}")
    print(f"  Écritures comptables totales     : {len(ecritures)}")
    print(f"  Prêts immobiliers                : {len(prets)}")
    print(f"  Échéances prêts                  : {len(echeances)}")
    print()

    # Répartition par statut
    statuts = defaultdict(int)
    for ex in exercices:
        statuts[ex['statut']] += 1

    print("  Répartition par statut:")
    for statut, count in sorted(statuts.items()):
        print(f"    • {statut}: {count}")

    print("=" * 80)

if __name__ == '__main__':
    import sys

    backup_file = 'backups/soeurise_bd_20251122_095316.json'

    if len(sys.argv) > 1:
        backup_file = sys.argv[1]

    try:
        check_exercices_detailed(backup_file)
    except Exception as e:
        print(f"❌ ERREUR : {e}")
        import traceback
        traceback.print_exc()
