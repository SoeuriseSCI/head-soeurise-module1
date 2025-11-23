#!/usr/bin/env python3
"""
Script de vérification du statut des exercices à partir d'une sauvegarde JSON
"""

import json
from datetime import datetime

def check_exercices_from_backup(backup_file):
    """Vérifie et affiche le statut de tous les exercices depuis une sauvegarde"""

    with open(backup_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Extraire les infos de sauvegarde
    metadata = data.get('metadata', {})
    backup_date = metadata.get('backup_date', 'Inconnue')
    db_name = metadata.get('database', 'Inconnue')

    print("=" * 80)
    print("📊 STATUT DES EXERCICES COMPTABLES (depuis sauvegarde)")
    print("=" * 80)
    print(f"Source           : {backup_file}")
    print(f"Date sauvegarde  : {backup_date}")
    print(f"Base de données  : {db_name}")
    print()

    # Récupérer les exercices
    exercices = data.get('exercices', [])

    if not exercices:
        print("⚠️  Aucun exercice trouvé dans la sauvegarde")
        return

    print(f"Nombre total d'exercices : {len(exercices)}")
    print()

    # Récupérer aussi les écritures pour calculer les statistiques
    ecritures = data.get('ecritures', [])

    # Créer un index des écritures par exercice_id
    ecritures_by_exercice = {}
    for ecriture in ecritures:
        ex_id = ecriture.get('exercice_id')
        if ex_id not in ecritures_by_exercice:
            ecritures_by_exercice[ex_id] = []
        ecritures_by_exercice[ex_id].append(ecriture)

    # Afficher chaque exercice
    for ex in sorted(exercices, key=lambda x: x['annee']):
        ex_id = ex['id']
        annee = ex['annee']
        statut = ex['statut']
        date_debut = ex['date_debut']
        date_fin = ex['date_fin']
        date_cloture = ex.get('date_cloture')
        resultat = ex.get('resultat_exercice')
        created_at = ex.get('created_at')

        print("─" * 80)
        print(f"🗓️  EXERCICE {annee}")
        print("─" * 80)
        print(f"  ID                  : {ex_id}")
        print(f"  Statut              : {statut}")
        print(f"  Date début          : {date_debut}")
        print(f"  Date fin            : {date_fin}")
        print(f"  Date clôture        : {date_cloture if date_cloture else 'Non clôturé'}")

        if resultat is not None:
            print(f"  Résultat exercice   : {float(resultat):,.2f} €")
        else:
            print(f"  Résultat exercice   : Non calculé")

        print(f"  Créé le             : {created_at}")

        # Calculer les statistiques des écritures
        ex_ecritures = ecritures_by_exercice.get(ex_id, [])
        nb_ecritures = len(ex_ecritures)

        total_debit = sum(float(e.get('montant_debit', 0) or 0) for e in ex_ecritures)
        total_credit = sum(float(e.get('montant_credit', 0) or 0) for e in ex_ecritures)

        print(f"  Écritures           : {nb_ecritures}")

        if nb_ecritures > 0:
            print(f"  Total débits        : {total_debit:,.2f} €")
            print(f"  Total crédits       : {total_credit:,.2f} €")

            # Vérifier l'équilibre
            diff = abs(total_debit - total_credit)
            if diff < 0.01:
                print(f"  ✅ Équilibre        : VALIDE (différence {diff:.4f} €)")
            else:
                print(f"  ⚠️  Équilibre        : DÉSÉQUILIBRÉ (différence {diff:.2f} €)")

        print()

    print("=" * 80)

    # Statistiques globales
    prets = data.get('prets', [])
    echeances = data.get('echeances', [])
    propositions = data.get('propositions_en_attente', [])

    propositions_attente = [p for p in propositions if p.get('statut') == 'EN_ATTENTE']
    propositions_validees = [p for p in propositions if p.get('statut') == 'VALIDEE']

    print("📈 STATISTIQUES GLOBALES")
    print("─" * 80)
    print(f"  Total écritures comptables       : {len(ecritures)}")
    print(f"  Total prêts immobiliers          : {len(prets)}")
    print(f"  Total échéances prêts            : {len(echeances)}")
    print(f"  Propositions en attente          : {len(propositions_attente)}")
    print(f"  Propositions validées            : {len(propositions_validees)}")
    print("=" * 80)

    # Détails des propositions en attente
    if propositions_attente:
        print()
        print("📋 PROPOSITIONS EN ATTENTE DE VALIDATION")
        print("─" * 80)
        for prop in propositions_attente:
            print(f"  Token: {prop.get('token_validation')}")
            print(f"  Type: {prop.get('type_evenement')}")
            print(f"  Créée: {prop.get('created_at')}")
            print(f"  Montant: {prop.get('montant_total', 0)} €")
            print()

if __name__ == '__main__':
    import sys

    backup_file = 'backups/soeurise_bd_20251122_095316.json'

    if len(sys.argv) > 1:
        backup_file = sys.argv[1]

    try:
        check_exercices_from_backup(backup_file)
    except Exception as e:
        print(f"❌ ERREUR : {e}")
        import traceback
        traceback.print_exc()
