#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST PARSEUR V7 - EXÉCUTION SUR RENDER
========================================

Script de test autonome pour valider le parseur V7 sur Render.
Teste l'extraction des tableaux d'amortissement SANS insertion BD.

Usage sur Render Shell :
  python test_pret_render.py
"""

import os
import sys
from pathlib import Path

# Fichiers de test
PDFS_TEST = [
    ("TABLEAUD'AMORTISSEMENTPRETIMMOBILIER_20230417.pdf", "Prêt A - INVESTIMUR"),
    ("TABLEAUD'AMORTISSEMENTPRETIMMOBILIER_20230417-1.pdf", "Prêt B - SOLUTION P IMMO")
]

FICHIERS_REFERENCE = {
    "TABLEAUD'AMORTISSEMENTPRETIMMOBILIER_20230417.pdf": "PRET_A_ECHEANCES_REFERENCE.md",
    "TABLEAUD'AMORTISSEMENTPRETIMMOBILIER_20230417-1.pdf": "PRET_B_ECHEANCES_REFERENCE.md"
}


def afficher_header(titre):
    """Affiche un header formaté"""
    print()
    print("=" * 100)
    print(f"  {titre}")
    print("=" * 100)
    print()


def afficher_section(titre):
    """Affiche une section"""
    print()
    print("-" * 100)
    print(f"  {titre}")
    print("-" * 100)
    print()


def lire_reference(filename):
    """Lit un fichier de référence et extrait les premières échéances"""
    if not Path(filename).exists():
        return None

    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    echeances = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('**') or line.startswith('---'):
            continue

        parts = line.split(':')
        if len(parts) == 5:
            try:
                echeances.append({
                    'date': parts[0],
                    'total': float(parts[1]),
                    'capital': float(parts[2]),
                    'interet': float(parts[3]),
                    'restant': float(parts[4])
                })
            except ValueError:
                continue

    return echeances


def comparer_echeances(extraites, reference, nom_pret):
    """Compare les échéances extraites avec la référence"""
    if not reference:
        print(f"⚠️  Pas de fichier de référence pour {nom_pret}")
        return

    print(f"\n📊 COMPARAISON AVEC RÉFÉRENCE ({nom_pret})")
    print("-" * 100)

    # Nombre d'échéances
    print(f"  Échéances extraites : {len(extraites)}")
    print(f"  Échéances référence : {len(reference)}")

    if len(extraites) != len(reference):
        print(f"  ⚠️  DIFFÉRENCE : {abs(len(extraites) - len(reference))} échéances d'écart")
    else:
        print(f"  ✅ Même nombre d'échéances")

    # Comparer les 5 premières échéances
    print("\n  Comparaison des 5 premières échéances :")
    print()

    nb_a_comparer = min(5, len(extraites), len(reference))
    erreurs = []

    for i in range(nb_a_comparer):
        ext = extraites[i]
        ref = reference[i]

        # Vérifier chaque champ
        match_date = ext['date_echeance'] == ref['date']
        match_total = abs(ext['montant_total'] - ref['total']) < 0.01
        match_capital = abs(ext['montant_capital'] - ref['capital']) < 0.01
        match_interet = abs(ext['montant_interet'] - ref['interet']) < 0.01
        match_restant = abs(ext['capital_restant_du'] - ref['restant']) < 0.01

        status = "✅" if all([match_date, match_total, match_capital, match_interet, match_restant]) else "❌"

        print(f"    {i+1}. {status} {ext['date_echeance']}")

        if not match_total:
            erreurs.append(f"      Échéance {i+1} - Total : {ext['montant_total']:.2f} vs {ref['total']:.2f}")
        if not match_capital:
            erreurs.append(f"      Échéance {i+1} - Capital : {ext['montant_capital']:.2f} vs {ref['capital']:.2f}")
        if not match_interet:
            erreurs.append(f"      Échéance {i+1} - Intérêt : {ext['montant_interet']:.2f} vs {ref['interet']:.2f}")
        if not match_restant:
            erreurs.append(f"      Échéance {i+1} - Restant : {ext['capital_restant_du']:.2f} vs {ref['restant']:.2f}")

    if erreurs:
        print("\n  ❌ ERREURS DÉTECTÉES :")
        for err in erreurs:
            print(err)
    else:
        print(f"\n  ✅ Les {nb_a_comparer} premières échéances correspondent parfaitement")


def tester_pret(pdf_path, nom_pret):
    """Teste l'extraction d'un prêt"""

    afficher_header(f"TEST : {nom_pret}")

    # Vérifier que le PDF existe
    if not Path(pdf_path).exists():
        print(f"❌ PDF introuvable : {pdf_path}")
        return False

    print(f"📄 Fichier : {pdf_path}")

    # Vérifier la clé API
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ANTHROPIC_API_KEY non définie (normal en local, requis sur Render)")
        return False

    print("✅ API Key détectée")

    # Import du parseur
    try:
        from parseur_pret_v7 import ParseurTableauPretV7
        print("✅ Import parseur_pret_v7 réussi")
    except ImportError as e:
        print(f"❌ Erreur import : {e}")
        return False

    afficher_section("EXTRACTION EN COURS")

    # Initialisation et parsing
    parseur = ParseurTableauPretV7(api_key=api_key)

    # Parsing SANS insertion BD
    result = parseur.parse_from_pdf(pdf_path, auto_insert_bd=False)

    afficher_section("RÉSULTATS")

    if not result.get('success'):
        print(f"❌ ÉCHEC : {result.get('message')}")
        if 'errors' in result:
            print("\n📋 Erreurs de validation :")
            for err in result['errors']:
                print(f"  - {err}")
        return False

    # Afficher les métadonnées
    pret = result.get('pret', {})
    print("📊 MÉTADONNÉES DU PRÊT")
    print(f"  Numéro       : {pret.get('numero_pret')}")
    print(f"  Intitulé     : {pret.get('intitule')}")
    print(f"  Banque       : {pret.get('banque')}")
    print(f"  Montant      : {pret.get('montant_initial'):,.2f} EUR")
    print(f"  Taux         : {pret.get('taux_annuel')}%")
    print(f"  Durée        : {pret.get('duree_mois')} mois")
    print(f"  Date début   : {pret.get('date_debut')}")
    print(f"  Date amort.  : {pret.get('date_debut_amortissement', 'N/A')}")
    print(f"  Type         : {pret.get('type_pret')}")

    # Afficher les échéances
    echeances = result.get('echeances', [])
    print()
    print(f"📋 ÉCHÉANCES : {len(echeances)} extraites")
    print()
    print("  Premières échéances :")
    for i, ech in enumerate(echeances[:3]):
        print(f"    {i+1}. {ech['date_echeance']} | "
              f"Total: {ech['montant_total']:>10.2f} | "
              f"Capital: {ech['montant_capital']:>10.2f} | "
              f"Intérêt: {ech['montant_interet']:>10.2f} | "
              f"Restant: {ech['capital_restant_du']:>12.2f}")

    print()
    print("  Dernières échéances :")
    for i, ech in enumerate(echeances[-3:], len(echeances) - 2):
        print(f"    {i}. {ech['date_echeance']} | "
              f"Total: {ech['montant_total']:>10.2f} | "
              f"Capital: {ech['montant_capital']:>10.2f} | "
              f"Intérêt: {ech['montant_interet']:>10.2f} | "
              f"Restant: {ech['capital_restant_du']:>12.2f}")

    print()
    print(f"💾 Fichier MD créé : {result.get('filename')}")

    # Comparaison avec référence si disponible
    if pdf_path in FICHIERS_REFERENCE:
        ref_file = FICHIERS_REFERENCE[pdf_path]
        reference = lire_reference(ref_file)
        comparer_echeances(echeances, reference, nom_pret)

    print()
    print("✅ TEST RÉUSSI")

    return True


def main():
    """Fonction principale"""

    afficher_header("TEST PARSEUR V7 - TABLEAUX D'AMORTISSEMENT")

    print("Ce script teste le parseur V7 avec les PDFs de tableaux d'amortissement.")
    print("Les données sont extraites mais PAS insérées en base de données.")
    print()
    print("Fichiers testés :")
    for pdf, nom in PDFS_TEST:
        statut = "✅" if Path(pdf).exists() else "❌"
        print(f"  {statut} {nom} ({pdf})")

    # Demander quel prêt tester
    print()
    print("Options :")
    print("  1. Tester Prêt A uniquement")
    print("  2. Tester Prêt B uniquement")
    print("  3. Tester les deux prêts")
    print("  0. Quitter")
    print()

    # Si on est en mode automatique (pas de stdin), tester les deux
    if not sys.stdin.isatty():
        print("Mode automatique détecté : test des deux prêts")
        choix = "3"
    else:
        choix = input("Votre choix : ").strip()

    resultats = []

    if choix == "1":
        pdf, nom = PDFS_TEST[0]
        resultats.append(tester_pret(pdf, nom))
    elif choix == "2":
        pdf, nom = PDFS_TEST[1]
        resultats.append(tester_pret(pdf, nom))
    elif choix == "3":
        for pdf, nom in PDFS_TEST:
            resultats.append(tester_pret(pdf, nom))
    elif choix == "0":
        print("Test annulé")
        return 0
    else:
        print(f"Choix invalide : {choix}")
        return 1

    # Résumé final
    afficher_header("RÉSUMÉ FINAL")

    nb_reussis = sum(1 for r in resultats if r)
    nb_total = len(resultats)

    print(f"Tests réussis : {nb_reussis}/{nb_total}")

    if nb_reussis == nb_total:
        print()
        print("✅ TOUS LES TESTS SONT RÉUSSIS")
        print()
        print("Prochaine étape : Reprise méthodique")
        print("  1. Nettoyer la BD (garder Bilan 2023)")
        print("  2. Traiter les tableaux d'amortissement via email")
        print("  3. Traiter les événements 2024 (T1-T3 puis T4)")
        return 0
    else:
        print()
        print("❌ CERTAINS TESTS ONT ÉCHOUÉ")
        print()
        print("Vérifier les erreurs ci-dessus avant de continuer.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
