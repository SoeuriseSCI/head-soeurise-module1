#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VÉRIFICATION BILAN 2023 - DÉTECTION ABERRATIONS
================================================
Extrait les écritures du bilan 2023 en base et compare avec les valeurs attendues.
"""

import os
import sys
from decimal import Decimal

# Import des modèles
try:
    from models_module2 import (
        get_session, ExerciceComptable, EcritureComptable
    )
except ImportError as e:
    print(f"❌ ERREUR Import : {e}")
    print("   Installer : pip install sqlalchemy psycopg2-binary")
    sys.exit(1)

# DATABASE_URL depuis environnement
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("❌ ERREUR : DATABASE_URL non définie")
    print("   Utiliser : export DATABASE_URL='postgresql://...'")
    sys.exit(1)

print("=" * 80)
print("🔍 VÉRIFICATION BILAN 2023 - ÉCRITURES COMPTABLES")
print("=" * 80)
print()

# Connexion
try:
    session = get_session(DATABASE_URL)
    print("✅ Connexion PostgreSQL réussie")
    print()
except Exception as e:
    print(f"❌ ERREUR Connexion : {e}")
    sys.exit(1)

# Valeurs attendues (source : propositions_INIT_BILAN_2023_20251102_095312.md)
VALEURS_ATTENDUES = [
    # ACTIF (Débits) - contrepartie crédit 89
    {"numero": "2023-INIT-0001", "debit": "280", "credit": "89", "montant": Decimal("500032.00"), "libelle": "Titres immobilisés"},
    {"numero": "2023-INIT-0002", "debit": "290", "credit": "89", "montant": Decimal("50003.00"), "libelle": "Provision épargne pierre"},
    {"numero": "2023-INIT-0003", "debit": "412", "credit": "89", "montant": Decimal("7356.00"), "libelle": "Autres créances"},
    {"numero": "2023-INIT-0004", "debit": "502", "credit": "89", "montant": Decimal("4140.00"), "libelle": "Actions propres"},
    {"numero": "2023-INIT-0005", "debit": "512", "credit": "89", "montant": Decimal("2093.00"), "libelle": "Banque LCL"},
    # PASSIF (Crédits) - contrepartie débit 89
    {"numero": "2023-INIT-0006", "debit": "89", "credit": "101", "montant": Decimal("1000.00"), "libelle": "Capital"},
    {"numero": "2023-INIT-0007", "debit": "89", "credit": "120", "montant": Decimal("57992.00"), "libelle": "Report à nouveau"},
    {"numero": "2023-INIT-0008", "debit": "89", "credit": "130", "montant": Decimal("21844.00"), "libelle": "Résultat exercice"},
    {"numero": "2023-INIT-0009", "debit": "89", "credit": "161", "montant": Decimal("497993.00"), "libelle": "Emprunts"},
    {"numero": "2023-INIT-0010", "debit": "89", "credit": "401", "montant": Decimal("653.00"), "libelle": "Fournisseurs"},
    {"numero": "2023-INIT-0011", "debit": "89", "credit": "444", "montant": Decimal("120.00"), "libelle": "Compte courant"},
]

# Totaux attendus
TOTAL_ACTIF_ATTENDU = Decimal("563624.00")
TOTAL_PASSIF_ATTENDU = Decimal("579602.00")

# Récupération exercice 2023
exercice_2023 = session.query(ExerciceComptable).filter_by(annee=2023).first()
if not exercice_2023:
    print("❌ ERREUR : Exercice 2023 non trouvé en base")
    session.close()
    sys.exit(1)

print(f"✅ Exercice 2023 trouvé (ID: {exercice_2023.id}, statut: {exercice_2023.statut})")
print()

# Récupération écritures bilan
ecritures = session.query(EcritureComptable).filter(
    EcritureComptable.exercice_id == exercice_2023.id,
    EcritureComptable.numero_ecriture.like('2023-INIT-%')
).order_by(EcritureComptable.numero_ecriture).all()

print(f"📊 Nombre d'écritures trouvées : {len(ecritures)}")
print()

if len(ecritures) == 0:
    print("⚠️  AUCUNE ÉCRITURE trouvée pour le bilan 2023 !")
    print("   Le bilan n'a peut-être jamais été inséré ?")
    session.close()
    sys.exit(0)

if len(ecritures) != 11:
    print(f"⚠️  ATTENTION : {len(ecritures)} écritures au lieu de 11 attendues")
    print()

# Analyse détaillée
print("=" * 80)
print("ANALYSE DÉTAILLÉE DES ÉCRITURES")
print("=" * 80)
print()

erreurs_trouvees = []
warnings = []

for i, ecriture in enumerate(ecritures):
    attendu = VALEURS_ATTENDUES[i] if i < len(VALEURS_ATTENDUES) else None

    print(f"📋 Écriture {i+1}/{len(ecritures)} : {ecriture.numero_ecriture}")
    print(f"   Débit  : {ecriture.compte_debit}")
    print(f"   Crédit : {ecriture.compte_credit}")
    print(f"   Montant: {ecriture.montant:,.2f}€")
    print(f"   Libellé: {ecriture.libelle_ecriture}")

    if attendu:
        # Comparaison
        erreur_locale = []

        if ecriture.numero_ecriture != attendu["numero"]:
            erreur_locale.append(f"Numéro: {ecriture.numero_ecriture} vs {attendu['numero']}")

        if ecriture.compte_debit != attendu["debit"]:
            erreur_locale.append(f"Débit: {ecriture.compte_debit} vs {attendu['debit']}")

        if ecriture.compte_credit != attendu["credit"]:
            erreur_locale.append(f"Crédit: {ecriture.compte_credit} vs {attendu['credit']}")

        if ecriture.montant != attendu["montant"]:
            ecart = ecriture.montant - attendu["montant"]
            erreur_locale.append(f"Montant: {ecriture.montant:,.2f}€ vs {attendu['montant']:,.2f}€ (écart: {ecart:+,.2f}€)")

        if erreur_locale:
            print(f"   ❌ ERREURS DÉTECTÉES:")
            for err in erreur_locale:
                print(f"      • {err}")
            erreurs_trouvees.extend(erreur_locale)
        else:
            print(f"   ✅ Conforme aux attentes")

        # Vérifications spécifiques
        if ecriture.compte_debit == ecriture.compte_credit:
            warning = f"{ecriture.numero_ecriture}: Même compte débit/crédit ({ecriture.compte_debit})"
            print(f"   ⚠️  ABERRATION: {warning}")
            warnings.append(warning)

        if ecriture.montant < 0:
            warning = f"{ecriture.numero_ecriture}: Montant négatif ({ecriture.montant}€)"
            print(f"   ⚠️  ABERRATION: {warning}")
            warnings.append(warning)
    else:
        print(f"   ⚠️  Pas de valeur attendue pour comparaison")

    print()

# Calcul totaux
total_actif_reel = sum(e.montant for e in ecritures if e.compte_credit == "89")
total_passif_reel = sum(e.montant for e in ecritures if e.compte_debit == "89")

print("=" * 80)
print("TOTAUX ET ÉQUILIBRE")
print("=" * 80)
print()

print(f"ACTIF (crédits compte 89):")
print(f"  Réel    : {total_actif_reel:,.2f}€")
print(f"  Attendu : {TOTAL_ACTIF_ATTENDU:,.2f}€")
if total_actif_reel == TOTAL_ACTIF_ATTENDU:
    print(f"  ✅ Conforme")
else:
    ecart = total_actif_reel - TOTAL_ACTIF_ATTENDU
    print(f"  ❌ Écart: {ecart:+,.2f}€")
print()

print(f"PASSIF (débits compte 89):")
print(f"  Réel    : {total_passif_reel:,.2f}€")
print(f"  Attendu : {TOTAL_PASSIF_ATTENDU:,.2f}€")
if total_passif_reel == TOTAL_PASSIF_ATTENDU:
    print(f"  ✅ Conforme")
else:
    ecart = total_passif_reel - TOTAL_PASSIF_ATTENDU
    print(f"  ❌ Écart: {ecart:+,.2f}€")
print()

# Vérification utilisation compte 101 au lieu de 89
compte_101_actif = sum(1 for e in ecritures if e.compte_credit == "101" and e.compte_debit != "89")
compte_101_passif = sum(1 for e in ecritures if e.compte_debit == "101" and e.compte_credit != "89")

if compte_101_actif > 0 or compte_101_passif > 0:
    print("⚠️  COMPTE 101 UTILISÉ AU LIEU DE 89:")
    print(f"   • {compte_101_actif} écritures ACTIF avec crédit 101 (devrait être 89)")
    print(f"   • {compte_101_passif} écritures PASSIF avec débit 101 (devrait être 89)")
    print()

# RÉSUMÉ FINAL
print("=" * 80)
print("RÉSUMÉ FINAL")
print("=" * 80)
print()

if not erreurs_trouvees and not warnings:
    print("✅ BILAN 2023 CONFORME")
    print("   Toutes les écritures correspondent aux valeurs attendues")
else:
    print(f"❌ PROBLÈMES DÉTECTÉS:")
    print(f"   • {len(erreurs_trouvees)} erreurs")
    print(f"   • {len(warnings)} avertissements (aberrations)")
    print()

    if compte_101_actif > 0 or compte_101_passif > 0:
        print("🚨 ABERRATION MAJEURE:")
        print("   Le compte 101 (Capital) est utilisé comme contrepartie")
        print("   au lieu du compte 89 (Bilan d'ouverture)")
        print()
        print("   ➡️  CORRECTION NÉCESSAIRE : Recréer le bilan avec compte 89")

    if warnings:
        print("⚠️  ABERRATIONS COMPTABLES:")
        for w in warnings:
            print(f"   • {w}")

print()
print("=" * 80)

session.close()
