#!/usr/bin/env python3
"""
Script de vérification d'intégrité complète de la base de données
Après corrections manuelles de la pré-clôture et clôture 2024
"""

import json
from collections import defaultdict
from datetime import datetime

def verifier_integrite_complete(backup_file):
    """Vérification exhaustive de l'intégrité de la base"""

    with open(backup_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    metadata = data.get('metadata', {})
    backup_date = metadata.get('backup_date', 'Inconnue')

    print("=" * 80)
    print("🔍 VÉRIFICATION D'INTÉGRITÉ COMPLÈTE - BASE SOEURISE")
    print("=" * 80)
    print(f"Date vérification : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"Source sauvegarde : {backup_file}")
    print(f"Date sauvegarde   : {backup_date}")
    print()

    exercices = data.get('exercices', [])
    ecritures = data.get('ecritures', [])
    prets = data.get('prets', [])
    echeances = data.get('echeances', [])
    propositions = data.get('propositions_en_attente', [])

    # Compteurs d'anomalies
    anomalies = []
    warnings = []

    print("📊 DONNÉES CHARGÉES")
    print("─" * 80)
    print(f"  Exercices             : {len(exercices)}")
    print(f"  Écritures comptables  : {len(ecritures)}")
    print(f"  Prêts immobiliers     : {len(prets)}")
    print(f"  Échéances prêts       : {len(echeances)}")
    print(f"  Propositions          : {len(propositions)}")
    print()

    # ====================================================================
    # 1. VÉRIFICATION DES EXERCICES
    # ====================================================================
    print("=" * 80)
    print("1️⃣  VÉRIFICATION DES EXERCICES")
    print("=" * 80)

    ecritures_by_ex = defaultdict(list)
    for ecriture in ecritures:
        ex_id = ecriture.get('exercice_id')
        ecritures_by_ex[ex_id].append(ecriture)

    for ex in sorted(exercices, key=lambda x: x['annee']):
        ex_id = ex['id']
        annee = ex['annee']
        statut = ex['statut']
        date_debut = ex.get('date_debut')
        date_fin = ex.get('date_fin')

        print(f"\n📅 EXERCICE {annee} (ID: {ex_id}) - Statut: {statut}")
        print("─" * 80)
        print(f"  Période              : {date_debut} → {date_fin}")

        # Note : date_cloture et resultat_exercice ne sont pas stockés dans le modèle
        # - date_cloture = date_fin pour les exercices clôturés
        # - resultat_exercice est calculé dynamiquement depuis les écritures (classes 6-7)

        # Vérifier équilibre
        ex_ecritures = ecritures_by_ex.get(ex_id, [])
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

        print(f"  Écritures            : {len(ex_ecritures)}")
        print(f"  Total débits         : {total_debits:,.2f} €")
        print(f"  Total crédits        : {total_credits:,.2f} €")

        if diff < 0.01:
            print(f"  ✅ Équilibre         : OUI (diff {diff:.4f} €)")
        else:
            anomalies.append(f"❌ EX{annee}: Déséquilibre {diff:.2f} €")
            print(f"  ❌ Équilibre         : NON (diff {diff:.2f} €)")

    # ====================================================================
    # 2. VÉRIFICATION DES CUT-OFFS ET EXTOURNES
    # ====================================================================
    print("\n" + "=" * 80)
    print("2️⃣  VÉRIFICATION CUT-OFFS ET EXTOURNES")
    print("=" * 80)

    cutoffs_2024 = [e for e in ecritures if e.get('exercice_id') == 2 and 'CUTOFF' in e.get('type_ecriture', '')]
    extournes_2025 = [e for e in ecritures if e.get('exercice_id') == 3 and e.get('type_ecriture') == 'EXTOURNE_CUTOFF']

    print(f"\n  Cut-offs 2024        : {len(cutoffs_2024)}")
    print(f"  Extournes 2025       : {len(extournes_2025)}")

    # Vérifier la cohérence
    cutoff_types = defaultdict(int)
    for c in cutoffs_2024:
        cutoff_types[c.get('type_ecriture')] += 1

    extourne_libelles = [e.get('libelle_ecriture', '') for e in extournes_2025]

    print("\n  Types de cut-offs 2024:")
    for type_c, count in sorted(cutoff_types.items()):
        print(f"    • {type_c}: {count}")

    print("\n  Extournes 2025:")
    for lib in extourne_libelles:
        print(f"    • {lib}")

    if len(cutoffs_2024) != len(extournes_2025):
        warnings.append(f"⚠️  Nombre de cut-offs ({len(cutoffs_2024)}) != extournes ({len(extournes_2025)})")
        print(f"\n  ⚠️  ATTENTION: {len(cutoffs_2024)} cut-offs mais {len(extournes_2025)} extournes")
    else:
        print(f"\n  ✅ Cohérence cut-offs/extournes : OK")

    # ====================================================================
    # 3. VÉRIFICATION DES ÉCRITURES DE CLÔTURE/PRÉ-CLÔTURE
    # ====================================================================
    print("\n" + "=" * 80)
    print("3️⃣  VÉRIFICATION ÉCRITURES CLÔTURE 2024")
    print("=" * 80)

    ecritures_cloture = [e for e in ecritures if e.get('exercice_id') == 2 and
                         e.get('type_ecriture') in ['PRE_CLOTURE', 'CLOTURE', 'AFFECTATION_RESULTAT']]

    print(f"\n  Total écritures clôture : {len(ecritures_cloture)}")

    types_cloture = defaultdict(int)
    for e in ecritures_cloture:
        types_cloture[e.get('type_ecriture')] += 1

    for type_e, count in sorted(types_cloture.items()):
        print(f"    • {type_e}: {count}")

    # Vérifier si les écritures ont bien été validées
    ecritures_non_validees = [e for e in ecritures_cloture if not e.get('validee_at')]
    if ecritures_non_validees:
        warnings.append(f"⚠️  {len(ecritures_non_validees)} écritures de clôture sans validee_at")
        print(f"\n  ⚠️  {len(ecritures_non_validees)} écritures sans date de validation")
        for e in ecritures_non_validees[:5]:  # Afficher les 5 premières
            print(f"      - {e.get('numero_ecriture')}: {e.get('libelle_ecriture')}")
    else:
        print(f"\n  ✅ Toutes les écritures de clôture sont validées")

    # ====================================================================
    # 4. VÉRIFICATION DES PROPOSITIONS EN ATTENTE
    # ====================================================================
    print("\n" + "=" * 80)
    print("4️⃣  VÉRIFICATION PROPOSITIONS EN ATTENTE")
    print("=" * 80)

    props_attente = [p for p in propositions if p.get('statut') == 'EN_ATTENTE']
    props_validees = [p for p in propositions if p.get('statut') == 'VALIDEE']
    props_erreur = [p for p in propositions if p.get('statut') == 'ERREUR']

    print(f"\n  EN_ATTENTE           : {len(props_attente)}")
    print(f"  VALIDEE              : {len(props_validees)}")
    print(f"  ERREUR               : {len(props_erreur)}")

    if props_attente:
        print("\n  ⚠️  PROPOSITIONS EN ATTENTE DE VALIDATION:")
        for p in props_attente:
            print(f"      Token: {p.get('token_validation')}")
            print(f"      Type : {p.get('type_evenement')}")
            print(f"      Date : {p.get('created_at')}")
            print()
        warnings.append(f"⚠️  {len(props_attente)} propositions en attente (risque de doublons)")
    else:
        print("\n  ✅ Aucune proposition en attente")

    # ====================================================================
    # 5. CALCUL DU RÉSULTAT 2024 (VÉRIFICATION)
    # ====================================================================
    print("\n" + "=" * 80)
    print("5️⃣  CALCUL RÉSULTAT 2024 (VÉRIFICATION)")
    print("=" * 80)

    ecritures_2024 = ecritures_by_ex.get(2, [])

    # Comptes de produits (7xxx)
    produits = defaultdict(float)
    # Comptes de charges (6xxx)
    charges = defaultdict(float)

    for e in ecritures_2024:
        montant = float(e.get('montant', 0))
        compte_debit = e.get('compte_debit', '')
        compte_credit = e.get('compte_credit', '')
        type_e = e.get('type_ecriture', '')

        # Ignorer les écritures d'affectation de résultat et bilan d'ouverture
        if type_e in ['AFFECTATION_RESULTAT', 'BILAN_OUVERTURE', 'INIT_BILAN_2023']:
            continue

        # Produits : compte crédit commençant par 7
        if compte_credit.startswith('7'):
            produits[compte_credit] += montant

        # Produits : compte débit commençant par 7 (correction/extourne)
        if compte_debit.startswith('7'):
            produits[compte_debit] -= montant

        # Charges : compte débit commençant par 6
        if compte_debit.startswith('6'):
            charges[compte_debit] += montant

        # Charges : compte crédit commençant par 6 (correction/extourne)
        if compte_credit.startswith('6'):
            charges[compte_credit] -= montant

    total_produits = sum(produits.values())
    total_charges = sum(charges.values())
    resultat_calcule = total_produits - total_charges

    print(f"\n  Total produits (7xxx)  : {total_produits:,.2f} €")
    print(f"  Total charges (6xxx)   : {total_charges:,.2f} €")
    print(f"  Résultat calculé       : {resultat_calcule:,.2f} €")
    print(f"  ℹ️  Note : Le résultat est calculé dynamiquement (non stocké en base)")

    # ====================================================================
    # RAPPORT FINAL
    # ====================================================================
    print("\n" + "=" * 80)
    print("📋 RAPPORT FINAL D'INTÉGRITÉ")
    print("=" * 80)

    if not anomalies and not warnings:
        print("\n  ✅ ✅ ✅  BASE DE DONNÉES INTÈGRE  ✅ ✅ ✅")
        print("\n  Aucune anomalie détectée.")
        print("  Aucun avertissement.")
        print("\n  → La base est prête pour informer _Head.Soeurise")
    else:
        if anomalies:
            print(f"\n  ❌ {len(anomalies)} ANOMALIE(S) CRITIQUE(S) DÉTECTÉE(S):")
            for anomalie in anomalies:
                print(f"     {anomalie}")

        if warnings:
            print(f"\n  ⚠️  {len(warnings)} AVERTISSEMENT(S):")
            for warning in warnings:
                print(f"     {warning}")

        print("\n  → Corriger les anomalies avant d'informer _Head.Soeurise")

    print("\n" + "=" * 80)

    return len(anomalies) == 0 and len(warnings) == 0

if __name__ == '__main__':
    import sys

    backup_file = 'backups/soeurise_bd_20251122_095316.json'

    if len(sys.argv) > 1:
        backup_file = sys.argv[1]

    try:
        integre = verifier_integrite_complete(backup_file)
        sys.exit(0 if integre else 1)
    except Exception as e:
        print(f"❌ ERREUR : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)
