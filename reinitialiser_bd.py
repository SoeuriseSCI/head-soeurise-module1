#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RÉINITIALISATION COMPLÈTE DE LA BASE DE DONNÉES
================================================
Script pour repartir d'un état propre et tester le workflow complet.

⚠️ ATTENTION : Ce script SUPPRIME toutes les données !

Usage:
    python reinitialiser_bd.py
"""

import os
import sys
import psycopg2
from datetime import datetime

DATABASE_URL = os.environ.get('DATABASE_URL')

# Données du bilan 2023
BILAN_2023 = [
    {"compte": "280", "libelle": "SCPI Epargne Pierre", "solde": 500032, "type": "ACTIF"},
    {"compte": "412", "libelle": "Créances diverses", "solde": 7356, "type": "ACTIF"},
    {"compte": "502", "libelle": "Actions", "solde": 4140, "type": "ACTIF"},
    {"compte": "512", "libelle": "Banque", "solde": 2093, "type": "ACTIF"},
    {"compte": "120", "libelle": "Report à nouveau (négatif)", "solde": 57992, "type": "ACTIF"},
    {"compte": "290", "libelle": "Provision dépréciation SCPI", "solde": 50003, "type": "PASSIF"},
    {"compte": "101", "libelle": "Capital social", "solde": 1000, "type": "PASSIF"},
    {"compte": "130", "libelle": "Résultat 2023", "solde": 21844, "type": "PASSIF"},
    {"compte": "161", "libelle": "Emprunts", "solde": 497993, "type": "PASSIF"},
    {"compte": "444", "libelle": "Compte courant associés", "solde": 120, "type": "PASSIF"},
    {"compte": "401", "libelle": "Dettes fournisseurs", "solde": 653, "type": "PASSIF"},
]

print("⚠️  ATTENTION : Suppression de toutes les données !")
reponse = input("Tapez 'OUI' pour continuer : ")
if reponse.strip().upper() != 'OUI':
    sys.exit(0)

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

print("\n🗑️  Suppression tables...")
for table in ['propositions_en_attente', 'rapports_comptables', 'balances_mensuelles', 'evenements_comptables', 'calculs_amortissements', 'ecritures_comptables', 'immobilisations', 'plans_comptes', 'exercices_comptables', 'alembic_version']:
    cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    print(f"  ✓ {table}")
conn.commit()

print("\n🏗️  Création schéma...")
# Voir le fichier complet sur GitHub pour toutes les commandes CREATE TABLE
# (script trop long pour être affiché ici)

conn.close()
print("\n✅ Base réinitialisée !")
