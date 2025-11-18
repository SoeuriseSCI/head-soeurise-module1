#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TESTS UNITAIRES - SYSTÈME DE CUT-OFF AUTOMATIQUE
=================================================
Tests du système de rapprochement automatique des créances/dettes.

Tests couverts:
1. Détection email annonce produit à recevoir
2. Génération écriture produit à recevoir (31/12)
3. Recherche créance existante
4. Génération écriture de soldage (montant exact)
5. Génération écriture de soldage avec écart positif
6. Génération écriture de soldage avec écart négatif
7. Workflow complet (annonce + paiement)

Date: 18/11/2025
Auteur: _Head.Soeurise
"""

import os
import sys
from datetime import datetime, date
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Import modules à tester
from detecteurs_evenements import DetecteurAnnonceProduitARecevoir, DetecteurDistributionSCPI
from rapprocheur_cutoff import RapprocheurCutoff


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("❌ Variable DATABASE_URL non définie")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS DÉTECTEUR ANNONCE PRODUIT À RECEVOIR
# ═══════════════════════════════════════════════════════════════════════════════

def test_detection_email_annonce():
    """Test détection email annonce produit à recevoir"""
    print("\n" + "=" * 80)
    print("TEST 1: Détection Email Annonce Produit à Recevoir")
    print("=" * 80)

    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    detecteur = DetecteurAnnonceProduitARecevoir(session)

    # Test 1.1: Email type simple (doit être détecté)
    print("\n📧 Test 1.1: Email annonce simple")
    email_simple = {
        'type_source': 'EMAIL',
        'objet_email': 'SCPI Épargne Pierre - Distribution T4 2024',
        'corps_email': 'Votre distribution de 7 356,00 € sera versée le 29/01/2025',
        'date_reception': '2024-12-20'
    }

    if detecteur.detecter(email_simple):
        print("  ✅ Email détecté correctement")
        proposition = detecteur.generer_proposition(email_simple)
        print(f"  ✅ Type: {proposition['type_evenement']}")
        print(f"  ✅ Montant: {proposition['ecritures'][0]['montant']}€")
        print(f"  ✅ Date écriture: {proposition['ecritures'][0]['date_ecriture']}")
        print(f"  ✅ Compte débit: {proposition['ecritures'][0]['compte_debit']}")
        print(f"  ✅ Compte crédit: {proposition['ecritures'][0]['compte_credit']}")
    else:
        print("  ❌ Email non détecté (devrait être détecté)")

    # Test 1.2: Email bulletin annuel (doit être détecté)
    print("\n📧 Test 1.2: Email bulletin annuel")
    email_bulletin = {
        'type_source': 'EMAIL',
        'objet_email': 'Bulletin annuel 2024 - SCPI Épargne Pierre',
        'corps_email': 'T4 2024 : 7 356,00 € (versement prévu janvier 2025)',
        'date_reception': '2024-12-28'
    }

    if detecteur.detecter(email_bulletin):
        print("  ✅ Email détecté correctement")
    else:
        print("  ❌ Email non détecté (devrait être détecté)")

    # Test 1.3: Relevé bancaire (ne doit PAS être détecté)
    print("\n📧 Test 1.3: Relevé bancaire (anti-pattern)")
    releve_bancaire = {
        'type_source': 'RELEVE_BANCAIRE',
        'libelle': 'VIREMENT SCPI EPARGNE PIERRE DISTRIBUTION T4',
        'montant': 7356.00,
        'date_operation': '2024-01-29'
    }

    if not detecteur.detecter(releve_bancaire):
        print("  ✅ Relevé bancaire ignoré correctement")
    else:
        print("  ❌ Relevé bancaire détecté (ne devrait PAS être détecté)")

    # Test 1.4: Email versement effectué (anti-pattern)
    print("\n📧 Test 1.4: Email versement effectué (anti-pattern)")
    email_effectue = {
        'type_source': 'EMAIL',
        'objet_email': 'SCPI - Distribution T4 2024',
        'corps_email': 'Le versement de 7 356,00 € a été effectué le 29/01/2025',
        'date_reception': '2025-01-29'
    }

    if not detecteur.detecter(email_effectue):
        print("  ✅ Email versement effectué ignoré correctement")
    else:
        print("  ❌ Email versement effectué détecté (ne devrait PAS être détecté)")

    session.close()
    print("\n✅ Tests détection email terminés")


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS RAPPROCHEUR CUTOFF
# ═══════════════════════════════════════════════════════════════════════════════

def test_recherche_creance():
    """Test recherche de créance existante"""
    print("\n" + "=" * 80)
    print("TEST 2: Recherche Créance Existante")
    print("=" * 80)

    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    rapprocheur = RapprocheurCutoff(session)

    # Test 2.1: Chercher créance existante (montant exact)
    print("\n🔍 Test 2.1: Recherche créance montant exact (7 356 €)")
    creance = rapprocheur.chercher_creance(
        montant=7356.00,
        tolerance_montant=2.0,
        tolerance_pourcentage=0.02
    )

    if creance:
        print(f"  ✅ Créance trouvée: ID {creance['id']}")
        print(f"  ✅ Montant créance: {creance['montant']}€")
        print(f"  ✅ Date: {creance['date_ecriture']}")
        print(f"  ✅ Libellé: {creance['libelle']}")
        print(f"  ✅ Écart: {creance['ecart']}€ ({creance['ecart_pourcent']:.2f}%)")
    else:
        print("  ⚠️  Aucune créance trouvée (normal si pas encore créée)")

    # Test 2.2: Chercher créance avec écart +4€ (doit être trouvée)
    print("\n🔍 Test 2.2: Recherche créance avec écart +4€ (7 360 €)")
    creance_ecart_pos = rapprocheur.chercher_creance(
        montant=7360.00,
        tolerance_montant=5.0,
        tolerance_pourcentage=0.02
    )

    if creance_ecart_pos:
        print(f"  ✅ Créance trouvée avec écart: {creance_ecart_pos['ecart']}€")
    else:
        print("  ⚠️  Aucune créance trouvée")

    # Test 2.3: Chercher créance avec montant très différent (ne doit PAS être trouvée)
    print("\n🔍 Test 2.3: Recherche créance montant très différent (8 000 €)")
    creance_diff = rapprocheur.chercher_creance(
        montant=8000.00,
        tolerance_montant=2.0,
        tolerance_pourcentage=0.02
    )

    if not creance_diff:
        print("  ✅ Aucune créance trouvée (correct, écart trop important)")
    else:
        print(f"  ❌ Créance trouvée (ne devrait PAS être trouvée): {creance_diff}")

    session.close()
    print("\n✅ Tests recherche créance terminés")


def test_generation_ecritures_soldage():
    """Test génération écritures de soldage"""
    print("\n" + "=" * 80)
    print("TEST 3: Génération Écritures de Soldage")
    print("=" * 80)

    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    rapprocheur = RapprocheurCutoff(session)

    # Créer créance fictive pour tests
    creance_fictive = {
        'id': 999,
        'date_ecriture': date(2024, 12, 31),
        'montant': 7356.00,
        'libelle': 'SCPI Épargne Pierre - Revenus T4 2024 à recevoir',
        'exercice_id': 1,
        'ecart': 0.0,
        'ecart_pourcent': 0.0
    }

    # Test 3.1: Soldage montant exact
    print("\n📝 Test 3.1: Soldage montant exact (7 356 €)")
    ecritures_exact = rapprocheur.generer_ecriture_soldage_creance(
        creance=creance_fictive,
        montant_encaisse=7356.00,
        date_encaissement='2025-01-29'
    )

    print(f"  ✅ Nombre d'écritures générées: {len(ecritures_exact)}")
    for i, ecriture in enumerate(ecritures_exact, 1):
        print(f"  ✅ Écriture {i}:")
        print(f"      Débit {ecriture['compte_debit']} / Crédit {ecriture['compte_credit']}")
        print(f"      Montant: {ecriture['montant']}€")
        print(f"      Libellé: {ecriture['libelle_ecriture']}")

    # Test 3.2: Soldage avec écart positif (+4€)
    print("\n📝 Test 3.2: Soldage avec écart positif +4€ (7 360 €)")
    ecritures_ecart_pos = rapprocheur.generer_ecriture_soldage_creance(
        creance=creance_fictive,
        montant_encaisse=7360.00,
        date_encaissement='2025-01-29'
    )

    print(f"  ✅ Nombre d'écritures générées: {len(ecritures_ecart_pos)}")
    for i, ecriture in enumerate(ecritures_ecart_pos, 1):
        print(f"  ✅ Écriture {i}:")
        print(f"      Débit {ecriture['compte_debit']} / Crédit {ecriture['compte_credit']}")
        print(f"      Montant: {ecriture['montant']}€")
        print(f"      Libellé: {ecriture['libelle_ecriture']}")

    # Test 3.3: Soldage avec écart négatif (-6€)
    print("\n📝 Test 3.3: Soldage avec écart négatif -6€ (7 350 €)")
    ecritures_ecart_neg = rapprocheur.generer_ecriture_soldage_creance(
        creance=creance_fictive,
        montant_encaisse=7350.00,
        date_encaissement='2025-01-29'
    )

    print(f"  ✅ Nombre d'écritures générées: {len(ecritures_ecart_neg)}")
    for i, ecriture in enumerate(ecritures_ecart_neg, 1):
        print(f"  ✅ Écriture {i}:")
        print(f"      Débit {ecriture['compte_debit']} / Crédit {ecriture['compte_credit']}")
        print(f"      Montant: {ecriture['montant']}€")
        print(f"      Libellé: {ecriture['libelle_ecriture']}")

    session.close()
    print("\n✅ Tests génération écritures terminés")


def test_workflow_complet():
    """Test workflow complet (annonce + paiement avec rapprochement)"""
    print("\n" + "=" * 80)
    print("TEST 4: Workflow Complet (Annonce + Rapprochement)")
    print("=" * 80)

    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    rapprocheur = RapprocheurCutoff(session)

    # Test 4.1: Rapprochement automatique high-level
    print("\n🔄 Test 4.1: Rapprochement automatique (7 356 €)")
    proposition = rapprocheur.rapprocher_encaissement(
        montant=7356.00,
        date_operation='2025-01-29',
        libelle='SCPI Épargne Pierre',
        tolerance_montant=2.0,
        tolerance_pourcentage=0.02
    )

    if proposition:
        print("  ✅ Rapprochement réussi")
        print(f"  ✅ Type: {proposition['type_evenement']}")
        print(f"  ✅ Description: {proposition['description']}")
        print(f"  ✅ Confiance: {proposition['confiance']}")
        print(f"  ✅ Créance ID: {proposition['metadata']['creance_id']}")
        print(f"  ✅ Montant créance: {proposition['metadata']['creance_montant']}€")
        print(f"  ✅ Écart: {proposition['metadata']['ecart']}€")
        print(f"  ✅ Nombre écritures: {len(proposition['ecritures'])}")
    else:
        print("  ⚠️  Aucun rapprochement (normal si créance pas encore en base)")

    session.close()
    print("\n✅ Tests workflow complet terminés")


def test_detecteur_distribution_avec_rapprochement():
    """Test détecteur SCPI avec rapprochement automatique"""
    print("\n" + "=" * 80)
    print("TEST 5: Détecteur Distribution SCPI avec Rapprochement")
    print("=" * 80)

    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    detecteur = DetecteurDistributionSCPI(session)

    # Test 5.1: Distribution SCPI (devrait chercher créance)
    print("\n💰 Test 5.1: Distribution SCPI avec créance existante")
    evenement_distrib = {
        'libelle': 'VIREMENT SCPI EPARGNE PIERRE DISTRIBUTION TRIMESTRIELLE',
        'libelle_normalise': 'virement scpi epargne pierre distribution trimestrielle',
        'montant': 7356.00,
        'type_operation': 'CREDIT',
        'date_operation': '2025-01-29'
    }

    if detecteur.detecter(evenement_distrib):
        print("  ✅ Distribution détectée")
        proposition = detecteur.generer_proposition(evenement_distrib)
        print(f"  ✅ Type: {proposition['type_evenement']}")
        print(f"  ✅ Description: {proposition['description']}")

        if proposition['type_evenement'] == 'ENCAISSEMENT_PRODUIT_A_RECEVOIR':
            print("  ✅ Rapprochement effectué (créance soldée)")
            print(f"  ✅ Créance ID: {proposition['metadata']['creance_id']}")
        else:
            print("  ⚠️  Nouveau produit créé (aucune créance trouvée)")

    else:
        print("  ❌ Distribution non détectée")

    session.close()
    print("\n✅ Tests détecteur avec rapprochement terminés")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Exécute tous les tests"""
    print("\n" + "=" * 80)
    print("TESTS SYSTÈME CUT-OFF AUTOMATIQUE")
    print("=" * 80)
    print(f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"Base de données: {DATABASE_URL[:30]}...")
    print("=" * 80)

    try:
        # Test 1: Détection emails
        test_detection_email_annonce()

        # Test 2: Recherche créances
        test_recherche_creance()

        # Test 3: Génération écritures soldage
        test_generation_ecritures_soldage()

        # Test 4: Workflow complet
        test_workflow_complet()

        # Test 5: Détecteur avec rapprochement
        test_detecteur_distribution_avec_rapprochement()

        print("\n" + "=" * 80)
        print("✅ TOUS LES TESTS TERMINÉS")
        print("=" * 80)

    except Exception as e:
        print("\n" + "=" * 80)
        print(f"❌ ERREUR LORS DES TESTS: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
