#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MODIFICATION PROPOSITION AVANT VALIDATION
=========================================
Modifie la proposition INIT_BILAN_2023 pour corriger compte 444: 0€ → 120€
ET recalcule le token MD5 pour maintenir l'intégrité
"""

import os
import json
import hashlib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_module2 import PropositionEnAttente

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("❌ DATABASE_URL non définie")
    exit(1)

# Connexion BD
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# Token actuel
TOKEN_ACTUEL = "3c5285fbd3751a4d9a1be1182314db78"

# Chercher la proposition
proposition = session.query(PropositionEnAttente).filter_by(
    token=TOKEN_ACTUEL
).first()

if not proposition:
    print(f"❌ Proposition {TOKEN_ACTUEL} non trouvée")
    session.close()
    exit(1)

print(f"✅ Proposition trouvée : {proposition.token}")
print(f"Type : {proposition.type_evenement}")
print(f"Statut : {proposition.statut}")

# Récupérer les propositions
propositions_data = proposition.propositions_json
propositions = propositions_data.get('propositions', [])

print(f"\n📊 Nombre d'écritures : {len(propositions)}")

# Chercher l'écriture du compte 444 (2023-INIT-0011)
ecriture_444 = None
for i, prop in enumerate(propositions):
    if prop.get('numero_ecriture') == '2023-INIT-0011':
        ecriture_444 = prop
        ecriture_444_index = i
        break

if not ecriture_444:
    print("❌ Écriture 2023-INIT-0011 non trouvée")
    session.close()
    exit(1)

print(f"\n📋 ÉCRITURE ACTUELLE (2023-INIT-0011)")
print(f"Compte débit : {ecriture_444.get('compte_debit')}")
print(f"Compte crédit : {ecriture_444.get('compte_credit')}")
print(f"Montant : {ecriture_444.get('montant')}€")
print(f"Libellé : {ecriture_444.get('libelle')}")

# Correction
if ecriture_444.get('montant') == 0:
    print("\n🔧 CORRECTION EN COURS...")

    # Modifier le montant
    propositions[ecriture_444_index]['montant'] = 120

    # Recalculer le nouveau token MD5
    nouveau_token = hashlib.md5(
        json.dumps(propositions, sort_keys=True).encode()
    ).hexdigest()

    print(f"\n🔐 TOKEN MD5")
    print(f"Ancien : {TOKEN_ACTUEL}")
    print(f"Nouveau : {nouveau_token}")

    # Mettre à jour la proposition
    proposition.propositions_json = {"propositions": propositions}
    proposition.token = nouveau_token

    session.commit()

    print(f"\n✅ CORRECTION APPLIQUÉE")
    print(f"Montant : 0€ → 120€")
    print(f"\n⚠️  IMPORTANT : Utilisez le NOUVEAU token pour valider :")
    print(f"\n[_Head] VALIDE: {nouveau_token}")

else:
    print(f"\n⚠️  Montant déjà différent de 0€ : {ecriture_444.get('montant')}€")
    print("Aucune correction appliquée")

session.close()
print("\n✅ Script terminé")
