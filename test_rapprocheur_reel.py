#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST RAPPROCHEUR SUR DONNÉES RÉELLES
=====================================

Test du rapprocheur avec le PDF T1T2T3 2024 (41 pages)
Objectif: Vérifier que le rapprocheur identifie correctement les 21 groupes
de doublons documentés dans ANALYSE_RAPPROCHEMENT_MANUEL.md
"""

import os
import json
from extracteur_pdf import ExtracteurPDF
from rapprocheur_operations import RapprocheurOperations


def test_rapprocheur_reel():
    """
    Test du rapprocheur avec données réelles du PDF T1T2T3 2024
    """
    print("="*80)
    print("TEST RAPPROCHEUR - DONNÉES RÉELLES T1T2T3 2024")
    print("="*80)

    # Chemin du PDF
    pdf_path = "Elements Comptables des 1-2-3T2024.pdf"
    if not os.path.exists(pdf_path):
        print(f"\n❌ ERREUR: PDF non trouvé: {pdf_path}")
        print("   Cherche le PDF dans le répertoire courant...")
        # Lister les PDFs disponibles
        pdfs = [f for f in os.listdir('.') if f.endswith('.pdf')]
        if pdfs:
            print(f"   PDFs disponibles: {pdfs}")
        return

    # ÉTAPE 1: Extraction complète (sans filtrage)
    print(f"\n📄 ÉTAPE 1: Extraction complète du PDF")
    print(f"   Fichier: {pdf_path}")

    extracteur = ExtracteurPDF(pdf_path)
    operations_brutes = extracteur.extraire_evenements()

    print(f"\n✅ Extraction terminée:")
    print(f"   Opérations extraites: {len(operations_brutes)}")
    print(f"   Attendu selon analyse manuelle: ~165 opérations")

    # ÉTAPE 2: Rapprochement intelligent
    print(f"\n🧠 ÉTAPE 2: Rapprochement intelligent via Claude API")

    rapprocheur = RapprocheurOperations()
    operations_finales, metadata = rapprocheur.rapprocher(operations_brutes)

    # ÉTAPE 3: Validation des résultats
    print(f"\n📊 ÉTAPE 3: Validation des résultats")
    print(f"{'='*80}")

    stats = metadata['stats']
    print(f"\nSTATISTIQUES GLOBALES:")
    print(f"  Opérations extraites    : {stats['total_operations']}")
    print(f"  Groupes analysés        : {stats['groupes_analyses']}")
    print(f"  Doublons détectés       : {stats['doublons_detectes']}")
    print(f"  Opérations finales      : {stats['operations_finales']}")
    print(f"  Réduction               : {stats['total_operations'] - stats['operations_finales']} opérations")

    print(f"\nVALIDATION vs ANALYSE MANUELLE:")
    print(f"  Attendu opérations finales : ~88 opérations économiques")
    print(f"  Obtenu                     : {stats['operations_finales']} opérations")
    print(f"  Attendu doublons éliminés  : ~77 doublons")
    print(f"  Obtenu                     : {stats['doublons_detectes']} doublons")

    # Vérifier si les résultats sont cohérents
    ecart_finales = abs(stats['operations_finales'] - 88)
    ecart_doublons = abs(stats['doublons_detectes'] - 77)

    print(f"\nÉCARTS:")
    print(f"  Écart opérations finales : {ecart_finales}")
    print(f"  Écart doublons           : {ecart_doublons}")

    if ecart_finales <= 5 and ecart_doublons <= 5:
        print(f"\n✅ VALIDATION RÉUSSIE - Résultats cohérents avec analyse manuelle!")
    else:
        print(f"\n⚠️  ATTENTION - Écarts significatifs détectés")
        print(f"   Nécessite investigation manuelle")

    # ÉTAPE 4: Sauvegarder les résultats pour analyse
    output_file = "resultats_rapprochement_test.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'operations_finales': operations_finales,
            'metadata': {
                'stats': stats,
                'justificatifs_count': len(metadata['justificatifs'])
            }
        }, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Résultats sauvegardés: {output_file}")
    print(f"\n{'='*80}\n")


if __name__ == '__main__':
    test_rapprocheur_reel()
