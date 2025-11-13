#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST STRUCTURE RAPPROCHEUR (Sans API Key)
==========================================

Valide la structure et la logique du rapprocheur sans appel API
"""

from rapprocheur_operations import RapprocheurOperations


def test_structure_sans_api():
    """
    Test de la structure sans appeler l'API Claude
    """
    print("="*80)
    print("TEST STRUCTURE RAPPROCHEUR (Sans API)")
    print("="*80)

    # Données de test
    operations_test = [
        # Groupe 1: Facture + SEPA (doublons)
        {
            'date_operation': '2024-01-02',
            'libelle': 'Facture CRP 2C n°2024013227 - Comptabilité',
            'montant': 213.60,
            'type_operation': 'DEBIT'
        },
        {
            'date_operation': '2024-01-24',
            'libelle': 'PRLV SEPA CRP Comptabilit Conseil LIBELLE:2024013227',
            'montant': 213.60,
            'type_operation': 'DEBIT'
        },
        # Groupe 2: Bulletin SCPI + Virement (doublons)
        {
            'date_operation': '2024-01-25',
            'libelle': 'BULLETIN SCPI REVENUS T4 2023 - 7356.24€',
            'montant': 7356.24,
            'type_operation': 'CREDIT'
        },
        {
            'date_operation': '2024-01-29',
            'libelle': 'VIR SEPA SCPI EPARGNE PIERRE DISTRIBUTION 4EME TRIM 2023',
            'montant': 7356.24,
            'type_operation': 'CREDIT'
        },
        # Opération unique
        {
            'date_operation': '2024-02-15',
            'libelle': 'PRET IMMOBILIER ECH 15/02/24',
            'montant': 258.33,
            'type_operation': 'DEBIT'
        }
    ]

    print(f"\n📊 Données de test:")
    print(f"   Opérations: {len(operations_test)}")
    print(f"   Attendu après rapprochement: 3 opérations (2 groupes rapprochés + 1 unique)")

    # Test du groupement par montant
    rapprocheur = RapprocheurOperations(api_key=None)  # Sans API key
    groupes = rapprocheur._grouper_par_montant(operations_test)

    print(f"\n✅ Test groupement par montant:")
    print(f"   Groupes créés: {len(groupes)}")
    print(f"   Attendu: 3 groupes")

    for montant, ops in groupes.items():
        print(f"   - {montant}€: {len(ops)} opération(s)")

    # Vérifier la structure
    assert len(groupes) == 3, f"Attendu 3 groupes, obtenu {len(groupes)}"
    assert 213.60 in groupes, "Groupe 213.60€ manquant"
    assert 7356.24 in groupes, "Groupe 7356.24€ manquant"
    assert 258.33 in groupes, "Groupe 258.33€ manquant"
    assert len(groupes[213.60]) == 2, "Groupe 213.60€ devrait avoir 2 opérations"
    assert len(groupes[7356.24]) == 2, "Groupe 7356.24€ devrait avoir 2 opérations"
    assert len(groupes[258.33]) == 1, "Groupe 258.33€ devrait avoir 1 opération"

    print(f"\n✅ STRUCTURE VALIDÉE")
    print(f"   Le rapprocheur identifie correctement:")
    print(f"   - Les groupes de montants identiques")
    print(f"   - Les groupes avec doublons potentiels (≥2 ops)")
    print(f"   - Les opérations uniques")

    print(f"\n⚠️  NOTE:")
    print(f"   Test complet avec API Claude nécessite ANTHROPIC_API_KEY")
    print(f"   À tester sur Render avec les vraies données T1T2T3 2024")

    print(f"\n{'='*80}\n")


if __name__ == '__main__':
    test_structure_sans_api()
