#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compléter le plan de comptes avec les comptes manquants
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

if not DATABASE_URL:
    print("❌ Variable DATABASE_URL non définie")
    exit(1)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

print("=" * 80)
print("COMPLÉTION DU PLAN DE COMPTES")
print("=" * 80)
print()

# 1. Vérifier les comptes existants
result = session.execute(text("""
    SELECT numero_compte, libelle, type_compte
    FROM plans_comptes
    ORDER BY numero_compte
"""))
comptes_existants = result.fetchall()

print(f"📊 Comptes existants: {len(comptes_existants)}")
print()
for compte in comptes_existants:
    print(f"   {compte[0]:10s} | {compte[2]:10s} | {compte[1]}")
print()

# Créer un set des numéros de comptes existants
numeros_existants = {c[0] for c in comptes_existants}

# 2. Définir les comptes nécessaires selon le PCG
comptes_necessaires = [
    # CLASSE 1 - CAPITAUX
    ('101', 'Capital social', 'PASSIF', 1),
    ('106', 'Réserves', 'PASSIF', 1),
    ('120', 'Report à nouveau', 'PASSIF', 1),
    ('129', 'Résultat de l\'exercice', 'PASSIF', 1),
    ('164', 'Emprunts auprès des établissements de crédit', 'PASSIF', 1),

    # CLASSE 2 - IMMOBILISATIONS
    ('211', 'Terrains', 'ACTIF', 2),
    ('213', 'Constructions', 'ACTIF', 2),
    ('2731', 'Titres immobilisés - actions', 'ACTIF', 2),
    ('273', 'Titres immobilisés', 'ACTIF', 2),
    ('2813', 'Amortissements des constructions', 'ACTIF', 2),
    ('290', 'Provisions pour dépréciation des immobilisations', 'ACTIF', 2),

    # CLASSE 4 - COMPTES DE TIERS
    ('4081', 'Fournisseurs - Factures non parvenues', 'PASSIF', 4),
    ('444', 'État - Impôts sur les bénéfices', 'PASSIF', 4),
    ('455', 'Associés - Comptes courants', 'PASSIF', 4),
    ('467', 'Autres comptes débiteurs ou créditeurs', 'PASSIF', 4),

    # CLASSE 5 - COMPTES FINANCIERS
    ('512', 'Banques', 'ACTIF', 5),
    ('503', 'Actions', 'ACTIF', 5),
    ('506', 'Obligations', 'ACTIF', 5),

    # CLASSE 6 - CHARGES
    ('601', 'Achats stockés - Matières premières', 'CHARGE', 6),
    ('606', 'Achats non stockés de matières et fournitures', 'CHARGE', 6),
    ('613', 'Locations', 'CHARGE', 6),
    ('616', 'Primes d\'assurance', 'CHARGE', 6),
    ('6226', 'Honoraires', 'CHARGE', 6),
    ('623', 'Publicité, publications, relations publiques', 'CHARGE', 6),
    ('625', 'Déplacements, missions et réceptions', 'CHARGE', 6),
    ('626', 'Frais postaux et de télécommunications', 'CHARGE', 6),
    ('627', 'Services bancaires et assimilés', 'CHARGE', 6),
    ('6354', 'Cotisations sociales personnelles', 'CHARGE', 6),
    ('661', 'Charges d\'intérêts', 'CHARGE', 6),
    ('6811', 'Dotations aux amortissements sur immobilisations incorporelles et corporelles', 'CHARGE', 6),

    # CLASSE 7 - PRODUITS
    ('701', 'Ventes de produits finis', 'PRODUIT', 7),
    ('706', 'Prestations de services', 'PRODUIT', 7),
    ('752', 'Revenus des immeubles non affectés à l\'exploitation', 'PRODUIT', 7),
    ('761', 'Produits de participations', 'PRODUIT', 7),
    ('764', 'Revenus des valeurs mobilières de placement', 'PRODUIT', 7),
    ('768', 'Autres produits financiers', 'PRODUIT', 7),

    # COMPTE 89 - BILAN D'OUVERTURE
    ('89', 'Bilan d\'ouverture', 'DIFF', 8),
]

# 3. Identifier et ajouter les comptes manquants
comptes_a_ajouter = []
for numero, libelle, type_compte, classe in comptes_necessaires:
    if numero not in numeros_existants:
        comptes_a_ajouter.append((numero, libelle, type_compte, classe))

if comptes_a_ajouter:
    print(f"➕ Comptes à ajouter: {len(comptes_a_ajouter)}")
    print()

    for numero, libelle, type_compte, classe in comptes_a_ajouter:
        print(f"   Ajout: {numero:10s} | {type_compte:10s} | {libelle}")

        session.execute(text("""
            INSERT INTO plans_comptes (numero_compte, libelle, type_compte, classe, actif)
            VALUES (:numero, :libelle, :type, :classe, true)
        """), {
            'numero': numero,
            'libelle': libelle,
            'type': type_compte,
            'classe': classe
        })

    session.commit()
    print()
    print(f"✅ {len(comptes_a_ajouter)} comptes ajoutés")
else:
    print("✅ Tous les comptes nécessaires existent déjà")

print()

# 4. Vérification finale
result = session.execute(text("SELECT COUNT(*) FROM plans_comptes"))
total = result.fetchone()[0]
print(f"📊 Total comptes dans le plan: {total}")

print()
print("=" * 80)
print("✅ COMPLÉTION TERMINÉE")
print("=" * 80)

session.close()
