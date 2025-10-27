#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST - Gestionnaire Propositions En Attente
============================================
Test du module propositions_manager.py
"""

import os
from datetime import datetime

# Charge DATABASE_URL
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://soeurise:6cIWYzBxmh8YKBGBH9Or6ohidT6NiCap@dpg-d3ikk7ggjchc73ee4flg-a/soeurise"
)


def test_propositions_manager():
    """Test complet du gestionnaire de propositions"""

    from models_module2 import get_session
    from propositions_manager import PropositionsManager

    print("🔧 Test du Gestionnaire de Propositions")
    print("=" * 80)

    # Créer session
    session = get_session(DATABASE_URL)
    manager = PropositionsManager(session)

    # ═══════════════════════════════════════════════════════════════════════════
    # TEST 1: Génération token
    # ═══════════════════════════════════════════════════════════════════════════

    print("\n1️⃣  Test génération token")
    print("-" * 80)

    propositions_test = [
        {
            "numero_ecriture": "2024-1027-001",
            "type": "LOYER",
            "compte_debit": "511",
            "compte_credit": "701",
            "montant": 1500.00,
            "libelle": "Encaissement loyer octobre 2024"
        }
    ]

    token = manager.generer_token_securise(propositions_test)
    print(f"✓ Token généré: {token}")

    # ═══════════════════════════════════════════════════════════════════════════
    # TEST 2: Stockage proposition
    # ═══════════════════════════════════════════════════════════════════════════

    print("\n2️⃣  Test stockage proposition")
    print("-" * 80)

    token_stocke, prop_id = manager.stocker_proposition(
        type_evenement="LOYER",
        propositions=propositions_test,
        email_id="test@example.com",
        email_from="ulrik.c.s.be@gmail.com",
        email_date=datetime.utcnow(),
        email_subject="Test proposition"
    )

    print(f"✓ Proposition stockée avec ID: {prop_id}")
    print(f"✓ Token: {token_stocke}")

    # ═══════════════════════════════════════════════════════════════════════════
    # TEST 3: Récupération proposition
    # ═══════════════════════════════════════════════════════════════════════════

    print("\n3️⃣  Test récupération proposition")
    print("-" * 80)

    proposition = manager.recuperer_proposition(token_stocke)

    if proposition:
        print(f"✓ Proposition récupérée:")
        print(f"  - ID: {proposition['id']}")
        print(f"  - Token: {proposition['token']}")
        print(f"  - Type: {proposition['type_evenement']}")
        print(f"  - Statut: {proposition['statut']}")
        print(f"  - Nombre écritures: {len(proposition['propositions'])}")
    else:
        print("❌ Échec récupération")

    # ═══════════════════════════════════════════════════════════════════════════
    # TEST 4: Validation proposition
    # ═══════════════════════════════════════════════════════════════════════════

    print("\n4️⃣  Test validation proposition")
    print("-" * 80)

    success = manager.valider_proposition(
        token=token_stocke,
        validee_par="ulrik.c.s.be@gmail.com",
        notes="Test validation automatique"
    )

    if success:
        print("✓ Proposition validée avec succès")

        # Vérifier le statut
        proposition = manager.recuperer_proposition(token_stocke)
        print(f"  - Nouveau statut: {proposition['statut']}")
        print(f"  - Validée le: {proposition['validee_at']}")
    else:
        print("❌ Échec validation")

    # ═══════════════════════════════════════════════════════════════════════════
    # TEST 5: Statistiques
    # ═══════════════════════════════════════════════════════════════════════════

    print("\n5️⃣  Test statistiques")
    print("-" * 80)

    stats = manager.statistiques()
    print(f"✓ Statistiques:")
    print(f"  - En attente: {stats['en_attente']}")
    print(f"  - Validées: {stats['validees']}")
    print(f"  - Rejetées: {stats['rejetees']}")
    print(f"  - Expirées: {stats['expirees']}")
    print(f"  - TOTAL: {stats['total']}")

    # ═══════════════════════════════════════════════════════════════════════════
    # TEST 6: Liste propositions en attente
    # ═══════════════════════════════════════════════════════════════════════════

    print("\n6️⃣  Test liste propositions en attente")
    print("-" * 80)

    propositions_attente = manager.recuperer_propositions_en_attente(limit=10)
    print(f"✓ {len(propositions_attente)} proposition(s) en attente")

    for i, prop in enumerate(propositions_attente[:3], 1):
        print(f"  {i}. {prop['token']} - {prop['type_evenement']} ({prop['created_at']})")

    # ═══════════════════════════════════════════════════════════════════════════
    # Fermer session
    # ═══════════════════════════════════════════════════════════════════════════

    session.close()

    print("\n" + "=" * 80)
    print("✅ Tests terminés avec succès!")
    print("=" * 80)


if __name__ == "__main__":
    try:
        test_propositions_manager()
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
