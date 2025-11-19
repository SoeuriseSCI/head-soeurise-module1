#!/usr/bin/env python3
"""
Générateur d'Extournes Automatiques
====================================

Génère automatiquement les écritures d'extourne au 01/01/N+1
pour toutes les écritures de cutoff de l'exercice N.

PRINCIPE:
- Recherche toutes les écritures de type CUTOFF_PRODUIT_A_RECEVOIR de l'exercice N
- Génère l'écriture inverse datée 01/01/N+1
- Permet d'annuler automatiquement les cutoffs

UTILISATION:
1. Lors de la clôture de l'exercice N
2. Ou au début de l'exercice N+1

EXEMPLE:
    python generateur_extournes.py --exercice 2024
    → Génère extournes pour exercice 2024 au 01/01/2025
"""

import os
import sys
from datetime import date
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import modèles
from models_module2 import EcritureComptable, ExerciceComptable, PropositionEnAttente


def generer_extournes_exercice(session: Session, exercice_id: int, dry_run: bool = True) -> List[Dict]:
    """
    Génère les extournes pour un exercice

    Args:
        session: Session SQLAlchemy
        exercice_id: ID de l'exercice à extourn er
        dry_run: Si True, simule sans créer les écritures

    Returns:
        Liste des écritures d'extourne générées
    """

    # 1. Récupérer l'exercice
    exercice = session.query(ExerciceComptable).filter_by(id=exercice_id).first()
    if not exercice:
        print(f"❌ Exercice ID {exercice_id} non trouvé")
        return []

    annee = exercice.annee
    date_extourne = date(annee + 1, 1, 1)

    print(f"\n📅 Génération extournes exercice {annee}")
    print(f"   Date extourne : {date_extourne}")
    print()

    # 2. Chercher toutes les écritures de cutoff (tous types)
    TYPES_CUTOFF = [
        'CUTOFF_PRODUIT_A_RECEVOIR',   # Revenus SCPI 761
        'CUTOFF_HONORAIRES',            # Honoraires 6226
        'CUTOFF_INTERETS_COURUS'        # Intérêts courus 661
    ]

    ecritures_cutoff = session.query(EcritureComptable).filter(
        EcritureComptable.exercice_id == exercice_id,
        EcritureComptable.type_ecriture.in_(TYPES_CUTOFF)
    ).all()

    if not ecritures_cutoff:
        print(f"  ℹ️  Aucune écriture de cutoff trouvée pour exercice {annee}")
        return []

    print(f"  📊 {len(ecritures_cutoff)} écritures de cutoff trouvées")
    print()

    # 3. Afficher les écritures à extourn er
    print("  📋 Écritures à extourn er :")
    print(f"  {'ID':<8} {'Date':<12} {'Débit':<8} {'Crédit':<8} {'Montant':>12} {'Libellé'}")
    print("  " + "-" * 80)

    extournes = []

    for ecriture in ecritures_cutoff:
        print(f"  {ecriture.id:<8} {str(ecriture.date_ecriture):<12} "
              f"{ecriture.compte_debit:<8} {ecriture.compte_credit:<8} "
              f"{ecriture.montant:>12,.2f}€ {ecriture.libelle_ecriture[:35]}")

        # Créer l'extourne (inversion débit ↔ crédit)
        extourne = {
            'date_ecriture': date_extourne,
            'exercice_id': exercice_id + 1 if exercice_id else None,  # Exercice suivant
            'libelle_ecriture': f'Extourne - {ecriture.libelle_ecriture}',
            'compte_debit': ecriture.compte_credit,   # INVERSION
            'compte_credit': ecriture.compte_debit,    # INVERSION
            'montant': ecriture.montant,
            'type_ecriture': 'EXTOURNE_CUTOFF',
            'notes': f'Contre-passation automatique écriture ID {ecriture.id}'
        }
        extournes.append(extourne)

    print("  " + "-" * 80)
    print()

    # 4. Générer les écritures d'extourne
    if not dry_run:
        print("  💾 Création des écritures d'extourne...")

        # Vérifier que l'exercice N+1 existe
        exercice_suivant = session.query(ExerciceComptable).filter_by(annee=annee + 1).first()
        if not exercice_suivant:
            print(f"  ⚠️  Exercice {annee + 1} n'existe pas encore")
            print(f"     Création de l'exercice {annee + 1}...")

            exercice_suivant = ExerciceComptable(
                annee=annee + 1,
                date_debut=date(annee + 1, 1, 1),
                date_fin=date(annee + 1, 12, 31),
                statut='OUVERT'
            )
            session.add(exercice_suivant)
            session.flush()
            print(f"  ✅ Exercice {annee + 1} créé (ID {exercice_suivant.id})")

        for ext in extournes:
            ext['exercice_id'] = exercice_suivant.id

            ecriture_ext = EcritureComptable(**ext)
            session.add(ecriture_ext)

        session.commit()
        print(f"  ✅ {len(extournes)} écritures d'extourne créées")

    else:
        print("  🔍 MODE DRY-RUN : Aucune écriture créée")
        print("     Pour créer réellement, utiliser --execute")

    print()

    # 5. Afficher les extournes
    print("  📋 Extournes générées :")
    print(f"  {'Date':<12} {'Débit':<8} {'Crédit':<8} {'Montant':>12} {'Libellé'}")
    print("  " + "-" * 80)

    for ext in extournes:
        print(f"  {str(ext['date_ecriture']):<12} "
              f"{ext['compte_debit']:<8} {ext['compte_credit']:<8} "
              f"{ext['montant']:>12,.2f}€ {ext['libelle_ecriture'][:35]}")

    print("  " + "-" * 80)
    print()

    return extournes


def generer_extournes_tous_exercices(session: Session, dry_run: bool = True):
    """
    Génère les extournes pour tous les exercices CLOTURÉS

    Args:
        session: Session SQLAlchemy
        dry_run: Si True, simule sans créer les écritures
    """

    # Récupérer tous les exercices cloturés qui n'ont pas encore d'extournes
    exercices = session.query(ExerciceComptable).filter(
        ExerciceComptable.statut == 'CLOTURE'
    ).all()

    if not exercices:
        print("ℹ️  Aucun exercice cloturé trouvé")
        return

    print(f"\n📊 {len(exercices)} exercice(s) cloturé(s) trouvé(s)")

    for exercice in exercices:
        # Vérifier si des extournes existent déjà pour cet exercice
        exercice_suivant = session.query(ExerciceComptable).filter_by(
            annee=exercice.annee + 1
        ).first()

        if exercice_suivant:
            extournes_existantes = session.query(EcritureComptable).filter(
                EcritureComptable.exercice_id == exercice_suivant.id,
                EcritureComptable.type_ecriture == 'EXTOURNE_CUTOFF',
                EcritureComptable.date_ecriture == date(exercice.annee + 1, 1, 1)
            ).count()

            if extournes_existantes > 0:
                print(f"  ⏭️  Exercice {exercice.annee} : {extournes_existantes} extournes déjà créées (ignoré)")
                continue

        generer_extournes_exercice(session, exercice.id, dry_run)


def main():
    """Point d'entrée principal"""
    import argparse

    parser = argparse.ArgumentParser(description='Générateur d\'extournes automatiques')
    parser.add_argument('--exercice', type=int, help='Année de l\'exercice à extourn er')
    parser.add_argument('--tous', action='store_true', help='Extourn er tous les exercices cloturés')
    parser.add_argument('--execute', action='store_true', help='Exécuter réellement (sinon dry-run)')

    args = parser.parse_args()

    # Connexion à la base
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        print("❌ Variable DATABASE_URL non définie")
        sys.exit(1)

    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        print("=" * 80)
        print("🔄 GÉNÉRATEUR D'EXTOURNES AUTOMATIQUES")
        print("=" * 80)

        dry_run = not args.execute

        if dry_run:
            print("\n⚠️  MODE DRY-RUN : Simulation uniquement")
            print("   Pour exécuter réellement, ajouter --execute")
        else:
            print("\n✅ MODE EXÉCUTION : Les écritures seront créées")

        if args.tous:
            generer_extournes_tous_exercices(session, dry_run)

        elif args.exercice:
            # Trouver l'exercice
            exercice = session.query(ExerciceComptable).filter_by(
                annee=args.exercice
            ).first()

            if not exercice:
                print(f"❌ Exercice {args.exercice} non trouvé")
                sys.exit(1)

            generer_extournes_exercice(session, exercice.id, dry_run)

        else:
            print("\n❌ Erreur : Spécifier --exercice ou --tous")
            parser.print_help()
            sys.exit(1)

        print("=" * 80)
        print("✅ Terminé")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
        sys.exit(1)

    finally:
        session.close()


if __name__ == '__main__':
    main()
