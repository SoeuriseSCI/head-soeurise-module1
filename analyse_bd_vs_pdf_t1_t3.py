#!/usr/bin/env python3
"""
Script d'analyse: Comparer BD vs PDF T1-T3 2024

Affiche:
1. Les écritures en BD pour 2024
2. Les événements extraits du PDF
3. Les divergences
"""

import os
import sys

print("=" * 80)
print("ANALYSE BASE DE DONNÉES vs PDF T1-T3 2024")
print("=" * 80)
print()

# PARTIE 1: État de la BD
print("PARTIE 1: ÉCRITURES EN BASE DE DONNÉES 2024")
print("-" * 80)

try:
    from models_module2 import get_session, EcritureComptable, ExerciceComptable
    from sqlalchemy import text

    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL non définie - exécute sur Render!")
        sys.exit(1)

    session = get_session(db_url)

    # Exercice 2024
    exercice_2024 = session.query(ExerciceComptable).filter_by(annee=2024).first()
    if not exercice_2024:
        print("❌ Exercice 2024 non trouvé")
        sys.exit(1)

    # Toutes les écritures 2024
    ecritures = session.query(EcritureComptable).filter(
        EcritureComptable.exercice_id == exercice_2024.id
    ).order_by(EcritureComptable.date_ecriture).all()

    print(f"✅ Total écritures 2024 en BD: {len(ecritures)}")
    print()

    # Résumé par type
    result = session.execute(text("""
        SELECT type_ecriture, COUNT(*) as count, SUM(montant) as total
        FROM ecritures_comptables
        WHERE exercice_id = :ex_id
        GROUP BY type_ecriture
        ORDER BY count DESC
    """), {'ex_id': exercice_2024.id})

    print("Résumé par type:")
    total_montant = 0
    for row in result:
        print(f"  {row[0]:30s}: {row[1]:3d} écritures | {row[2]:12.2f}€")
        total_montant += row[2] if row[2] else 0

    print()
    print(f"Total montants: {total_montant:.2f}€")
    print()

    # Liste détaillée (premiers et derniers)
    print(f"{'Date':<12} {'Type':<25} {'Montant':>12} {'Débit':>6} {'Crédit':>6} {'Libellé':<45}")
    print("-" * 120)

    # Premiers
    for ecriture in ecritures[:5]:
        print(f"{str(ecriture.date_ecriture):<12} {ecriture.type_ecriture:<25} {ecriture.montant:>12.2f} {ecriture.compte_debit:>6} {ecriture.compte_credit:>6} {ecriture.libelle_ecriture[:45]:<45}")

    if len(ecritures) > 10:
        print(f"  ... ({len(ecritures) - 10} écritures omises) ...")

        # Derniers
        for ecriture in ecritures[-5:]:
            print(f"{str(ecriture.date_ecriture):<12} {ecriture.type_ecriture:<25} {ecriture.montant:>12.2f} {ecriture.compte_debit:>6} {ecriture.compte_credit:>6} {ecriture.libelle_ecriture[:45]:<45}")

    session.close()

except ImportError as e:
    print(f"❌ Erreur import: {e}")
    print("   Assure-toi d'exécuter sur Render (ou avec les bonnes dépendances)")
except Exception as e:
    print(f"❌ Erreur BD: {e}")
    sys.exit(1)

print()
print()
print("PARTIE 2: ANALYSE DU PDF T1-T3")
print("-" * 80)
print("""
Pour analyser le PDF, il faut:
1. Extraire les opérations du PDF (90 détectées)
2. Grouper par type d'événement
3. Comparer avec les écritures en BD

Résultats attendus (selon le log):
- 90 opérations extraites du PDF
- 19 événements créés (71 doublons ignorés)
- 10 propositions générées (9 sans type)
- 10 écritures insérées en BD

Questions:
1. Les 71 "doublons" sont-ils vraiment des doublons ou des pertes?
2. Les 9 événements sans type sont-ils critiques?
3. Le total de 10 écritures correspond-il aux opérations uniques?

Pour aller plus loin:
- Ouvrir le PDF et compter les opérations par mois
- Vérifier que les montants insérés matchent
- Identifier les 59 doublons réels
""")

print()
print("=" * 80)
print("INSTRUCTIONS")
print("=" * 80)
print("""
1. Sur Render shell:
   cd /opt/render/project/src
   python analyse_bd_vs_pdf_t1_t3.py

2. Cela affichera l'état exact de la BD en production

3. Ensuite, Ulrik/Claude peut:
   - Ouvrir le PDF localement
   - Compter les opérations par mois
   - Vérifier que le total correspond
""")
