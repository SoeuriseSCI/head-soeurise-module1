#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAUVEGARDE BASE DE DONNÉES POSTGRESQL (PYTHON)
===============================================
Alternative Python si pg_dump n'est pas disponible
Exporte les données en JSON
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

from models_module2 import (
    get_session, ExerciceComptable, PlanCompte, EcritureComptable,
    PretImmobilier, EcheancePret
)

print("=" * 80)
print("💾 SAUVEGARDE BASE DE DONNÉES (FORMAT JSON)")
print("=" * 80)
print()

# Vérifier DATABASE_URL
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("❌ ERREUR : DATABASE_URL non définie")
    sys.exit(1)

session = get_session(DATABASE_URL)

# Créer répertoire backups
BACKUP_DIR = Path("./backups")
BACKUP_DIR.mkdir(exist_ok=True)

# Nom fichier avec timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_file = BACKUP_DIR / f"soeurise_bd_{timestamp}.json"

print(f"📁 Répertoire de sauvegarde : {BACKUP_DIR}")
print(f"📄 Fichier de sauvegarde    : {backup_file}")
print()

# Structure de sauvegarde
backup_data = {
    "metadata": {
        "timestamp": timestamp,
        "date": datetime.now().isoformat(),
        "database": "soeurise_sci",
        "version": "V6.0"
    },
    "exercices": [],
    "plan_comptable": [],
    "ecritures": [],
    "prets": [],
    "echeances": []
}

# 1. Exercices comptables
print("📊 Sauvegarde exercices comptables...")
exercices = session.query(ExerciceComptable).order_by(ExerciceComptable.id).all()
for ex in exercices:
    backup_data["exercices"].append({
        "id": ex.id,
        "annee": ex.annee,
        "date_debut": str(ex.date_debut),
        "date_fin": str(ex.date_fin),
        "statut": ex.statut,
        "description": ex.description
    })
print(f"   ✅ {len(exercices)} exercices sauvegardés")

# 2. Plan comptable
print("📊 Sauvegarde plan comptable...")
comptes = session.query(PlanCompte).order_by(PlanCompte.id).all()
for compte in comptes:
    backup_data["plan_comptable"].append({
        "id": compte.id,
        "numero_compte": compte.numero_compte,
        "libelle": compte.libelle,
        "type_compte": compte.type_compte
    })
print(f"   ✅ {len(comptes)} comptes sauvegardés")

# 3. Écritures comptables
print("📊 Sauvegarde écritures comptables...")
ecritures = session.query(EcritureComptable).order_by(EcritureComptable.id).all()
for ec in ecritures:
    backup_data["ecritures"].append({
        "id": ec.id,
        "exercice_id": ec.exercice_id,
        "numero_ecriture": ec.numero_ecriture,
        "date_ecriture": str(ec.date_ecriture),
        "libelle_ecriture": ec.libelle_ecriture,
        "type_ecriture": ec.type_ecriture,
        "compte_debit": ec.compte_debit,
        "compte_credit": ec.compte_credit,
        "montant": str(ec.montant),
        "source_email_id": ec.source_email_id,
        "source_email_from": ec.source_email_from,
        "validee_at": ec.validee_at.isoformat() if ec.validee_at else None,
        "notes": ec.notes
    })
print(f"   ✅ {len(ecritures)} écritures sauvegardées")

# 4. Prêts immobiliers
print("📊 Sauvegarde prêts immobiliers...")
prets = session.query(PretImmobilier).order_by(PretImmobilier.id).all()
for pret in prets:
    backup_data["prets"].append({
        "id": pret.id,
        "numero_pret": pret.numero_pret,
        "banque": pret.banque,
        "libelle": pret.libelle,
        "montant_initial": str(pret.montant_initial),
        "taux_annuel": str(pret.taux_annuel),
        "duree_mois": pret.duree_mois,
        "date_debut": str(pret.date_debut),
        "date_fin": str(pret.date_fin),
        "type_amortissement": pret.type_amortissement,
        "mois_franchise": pret.mois_franchise,
        "echeance_mensuelle": str(pret.echeance_mensuelle) if pret.echeance_mensuelle else None,
        "interet_mensuel_franchise": str(pret.interet_mensuel_franchise) if pret.interet_mensuel_franchise else None,
        "assurance_emprunteur": pret.assurance_emprunteur,
        "assures": pret.assures,
        "source_email_id": pret.source_email_id,
        "source_document": pret.source_document,
        "actif": pret.actif,
        "notes": pret.notes
    })
print(f"   ✅ {len(prets)} prêts sauvegardés")

# 5. Échéances
print("📊 Sauvegarde échéances...")
echeances = session.query(EcheancePret).order_by(EcheancePret.id).all()
for ech in echeances:
    backup_data["echeances"].append({
        "id": ech.id,
        "pret_id": ech.pret_id,
        "numero_echeance": ech.numero_echeance,
        "date_echeance": str(ech.date_echeance),
        "montant_total": str(ech.montant_echeance),
        "montant_interet": str(ech.montant_interet),
        "montant_capital": str(ech.montant_capital),
        "capital_restant_du": str(ech.capital_restant_du),
        "montant_assurance": str(ech.montant_assurance) if ech.montant_assurance else "0",
        "comptabilise": ech.comptabilise
    })
print(f"   ✅ {len(echeances)} échéances sauvegardées")

# Écrire le fichier JSON
print()
print("💾 Écriture du fichier JSON...")
with open(backup_file, 'w', encoding='utf-8') as f:
    json.dump(backup_data, f, indent=2, ensure_ascii=False)

# Statistiques
file_size = backup_file.stat().st_size / 1024  # KB
print(f"   ✅ Fichier écrit : {file_size:.2f} KB")

print()
print("=" * 80)
print("✅ SAUVEGARDE LOCALE TERMINÉE")
print("=" * 80)
print()
print("📊 Résumé :")
print(f"   - {len(backup_data['exercices'])} exercices")
print(f"   - {len(backup_data['plan_comptable'])} comptes")
print(f"   - {len(backup_data['ecritures'])} écritures")
print(f"   - {len(backup_data['prets'])} prêts")
print(f"   - {len(backup_data['echeances'])} échéances")
print()
print(f"💾 Fichier local : {backup_file}")
print()

session.close()

# ═══════════════════════════════════════════════════════════════════
# UPLOAD AUTOMATIQUE VERS GITHUB
# ═══════════════════════════════════════════════════════════════════

print("=" * 80)
print("📤 UPLOAD VERS GITHUB")
print("=" * 80)
print()

# Vérifier que GITHUB_TOKEN est défini
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
if not GITHUB_TOKEN:
    print("⚠️  GITHUB_TOKEN non définie - Skip upload GitHub")
    print("💡 Pour activer l'upload automatique, définir GITHUB_TOKEN sur Render")
    print()
    sys.exit(0)

# Configuration GitHub
REPO_OWNER = "SoeuriseSCI"
REPO_NAME = "head-soeurise-module1"
BRANCH = "main"
github_path = f"backups/{backup_file.name}"

print(f"📍 Repository : {REPO_OWNER}/{REPO_NAME}")
print(f"📍 Branche    : {BRANCH}")
print(f"📍 Chemin     : {github_path}")
print()

# Lire le fichier et encoder en base64
print("📖 Lecture du fichier pour upload...")
with open(backup_file, 'r', encoding='utf-8') as f:
    content = f.read()

import base64
content_encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
print(f"   ✅ {len(content)} caractères encodés")

# Vérifier si le fichier existe déjà sur GitHub
print()
print("🔍 Vérification si le fichier existe déjà sur GitHub...")
url_check = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{github_path}"
headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

import requests
response = requests.get(url_check, headers=headers)
sha = None
if response.status_code == 200:
    sha = response.json().get('sha')
    print(f"   ℹ️  Fichier existe (SHA: {sha[:7]}...) - Mise à jour")
else:
    print(f"   ℹ️  Fichier n'existe pas - Création")

# Upload vers GitHub
print()
print("📤 Upload vers GitHub...")
commit_message = f"💾 Sauvegarde BD automatique - {datetime.now().strftime('%d/%m/%Y %H:%M')}"

payload = {
    "message": commit_message,
    "content": content_encoded,
    "branch": BRANCH
}

if sha:
    payload["sha"] = sha

response = requests.put(url_check, headers=headers, json=payload)

if response.status_code in [200, 201]:
    result = response.json()
    print("   ✅ Upload réussi !")
    print()
    print("=" * 80)
    print("✅ SAUVEGARDE UPLOADÉE SUR GITHUB")
    print("=" * 80)
    print()
    print("📊 Détails :")
    print(f"   Commit  : {result['commit']['sha'][:7]}")
    print(f"   URL     : {result['content']['html_url']}")
    print(f"   Message : {commit_message}")
    print()
else:
    print(f"   ❌ Erreur upload : {response.status_code}")
    print(f"   {response.text[:200]}")
    print()
    print("⚠️  Sauvegarde locale OK mais pas sur GitHub")
    sys.exit(1)
