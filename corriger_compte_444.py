#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCRIPT DE CORRECTION - Compte 444 (Bilan 2023)
==============================================
Corrige l'écriture 2023-INIT-0011 : 0€ → 120€
"""

import os
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_module2 import EcritureComptable

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("❌ DATABASE_URL non définie")
    exit(1)

# Connexion BD
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# Chercher l'écriture 2023-INIT-0011
ecriture = session.query(EcritureComptable).filter_by(
    numero_ecriture='2023-INIT-0011'
).first()

if not ecriture:
    print("❌ Écriture 2023-INIT-0011 non trouvée")
    print("💡 Assurez-vous d'avoir validé les propositions d'abord")
    session.close()
    exit(1)

# Afficher état actuel
print("\n📋 ÉTAT ACTUEL")
print(f"Numéro : {ecriture.numero_ecriture}")
print(f"Libellé : {ecriture.libelle_ecriture}")
print(f"Débit : {ecriture.compte_debit}")
print(f"Crédit : {ecriture.compte_credit}")
print(f"Montant : {ecriture.montant}€")

# Correction
if ecriture.montant == Decimal('0'):
    print("\n🔧 CORRECTION EN COURS...")
    ecriture.montant = Decimal('120')
    session.commit()
    print(f"✅ Montant corrigé : 0€ → 120€")

    # Vérification
    print("\n📋 ÉTAT APRÈS CORRECTION")
    print(f"Numéro : {ecriture.numero_ecriture}")
    print(f"Montant : {ecriture.montant}€")
else:
    print(f"\n⚠️  Montant déjà différent de 0€ : {ecriture.montant}€")
    print("Aucune correction appliquée")

session.close()
print("\n✅ Script terminé")
