#!/usr/bin/env python3
"""
Système Cutoff par Extourne - Intérêts Courus
==============================================

PRINCIPE:
Les intérêts de prêt courent quotidiennement mais sont payés mensuellement.
En fin d'année, il y a des intérêts courus mais non encore échus.

EXEMPLE:
- Dernière échéance 2024 : 12/12/2024 (intérêts du 12/11 au 11/12)
- Fin d'année : 31/12/2024
- Intérêts courus non échus : du 12/12 au 31/12 (20 jours)

ÉCRITURES:

31/12/N - Cutoff (intérêts courus) :
    Débit 661 (Charges d'intérêts)        150€
    Crédit 1688 (Intérêts courus)         150€

01/01/N+1 - Extourne automatique :
    Débit 1688                            150€
    Crédit 661                            150€

12/01/N+1 - Échéance réelle (intérêts complets) :
    Débit 661                             600€  (intérêts mois entier)
    Crédit 512                            600€

RÉSULTAT:
- Exercice N : Charge 661 = 150€ (courus uniquement)
- Exercice N+1 : Charge 661 = 450€ (600 - 150)
- Total correct sur 2 ans

CALCUL:
    Intérêts courus = Capital restant × Taux annuel × (Nb jours / 365)
"""

from typing import Dict, List, Optional
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import text


class CalculateurInteretsCourus:
    """
    Calcule les intérêts courus non échus au 31/12/N

    Recherche dans la table echeances_prets :
    - Dernière échéance payée avant le 31/12/N
    - Calcule intérêts du jour suivant l'échéance au 31/12/N
    """

    def __init__(self, session: Session):
        """
        Args:
            session: Session SQLAlchemy
        """
        self.session = session

    def calculer_interets_courus_exercice(self, exercice_id: int, date_cloture: date = None) -> List[Dict]:
        """
        Calcule les intérêts courus pour tous les prêts au 31/12/N

        Args:
            exercice_id: ID de l'exercice
            date_cloture: Date de clôture (par défaut 31/12 de l'année)

        Returns:
            Liste de propositions d'écritures de cutoff
        """

        # 1. Récupérer l'exercice
        query_exercice = text("""
            SELECT annee, date_fin
            FROM exercices_comptables
            WHERE id = :exercice_id
        """)
        result = self.session.execute(query_exercice, {'exercice_id': exercice_id}).fetchone()

        if not result:
            return []

        annee = result[0]
        if not date_cloture:
            date_cloture = date(annee, 12, 31)

        print(f"\n📅 Calcul intérêts courus au {date_cloture}")
        print()

        # 2. Récupérer tous les prêts actifs
        query_prets = text("""
            SELECT DISTINCT
                pi.id,
                pi.numero_pret,
                pi.banque,
                pi.taux_annuel
            FROM echeances_prets ep
            JOIN prets_immobiliers pi ON ep.pret_id = pi.id
            WHERE ep.date_echeance <= :date_cloture
            ORDER BY pi.banque
        """)

        prets = self.session.execute(query_prets, {'date_cloture': date_cloture}).fetchall()

        if not prets:
            print("  ℹ️  Aucun prêt actif trouvé")
            return []

        print(f"  📊 {len(prets)} prêt(s) actif(s)")
        print()

        propositions = []

        # 3. Pour chaque prêt, calculer intérêts courus
        for pret in prets:
            pret_id = pret[0]
            numero_pret = pret[1]
            banque = pret[2]
            taux_annuel = float(pret[3])

            print(f"  💰 Prêt {banque} ({numero_pret[:15]}...)")
            print(f"     Taux annuel : {taux_annuel:.4f}%")

            # Trouver la dernière échéance payée avant date_cloture
            query_derniere = text("""
                SELECT
                    date_echeance,
                    capital_restant_du,
                    montant_interet
                FROM echeances_prets
                WHERE pret_id = :pret_id
                  AND date_echeance <= :date_cloture
                ORDER BY date_echeance DESC
                LIMIT 1
            """)

            derniere = self.session.execute(query_derniere, {
                'pret_id': pret_id,
                'date_cloture': date_cloture
            }).fetchone()

            if not derniere:
                print(f"     ⚠️  Aucune échéance trouvée")
                continue

            date_derniere_echeance = derniere[0]
            capital_restant = float(derniere[1])
            montant_interet_echeance = float(derniere[2])

            # Calculer nombre de jours entre dernière échéance et clôture
            jours_courus = (date_cloture - date_derniere_echeance).days

            if jours_courus <= 0:
                print(f"     ℹ️  Échéance au {date_derniere_echeance} = jour de clôture, pas d'intérêts courus")
                continue

            # Calculer intérêts courus - MÉTHODE PROPORTIONNELLE
            # Formule : Intérêts échéance × (Jours courus / Jours période)
            # Période mensuelle = nombre de jours du mois de clôture
            jours_periode = (date_cloture.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            jours_periode = jours_periode.day  # Nombre de jours dans le mois

            interets_courus = montant_interet_echeance * (jours_courus / jours_periode)
            interets_courus = round(interets_courus, 2)

            print(f"     Dernière échéance : {date_derniere_echeance}")
            print(f"     Intérêts échéance : {montant_interet_echeance:,.2f}€")
            print(f"     Jours courus : {jours_courus}/{jours_periode}")
            print(f"     ✅ Intérêts courus : {interets_courus:,.2f}€ ({montant_interet_echeance:,.2f}€ × {jours_courus}/{jours_periode})")
            print()

            # Date cutoff : 31/12 de l'année
            date_cutoff = date_cloture

            # Date extourne : 01/01 de l'année suivante
            date_extourne = date(annee + 1, 1, 1)

            # Libellés
            libelle_cutoff = f"Cutoff {annee} - Intérêts courus prêt {banque} ({jours_courus} jours)"
            libelle_extourne = f"Extourne - Cutoff {annee} - Intérêts courus prêt {banque}"

            # Notes
            note_cutoff = (f'Calcul proportionnel: {montant_interet_echeance:,.2f}€ × ({jours_courus}/{jours_periode} jours). '
                          f'Période: {date_derniere_echeance + timedelta(days=1)} → {date_cloture}. '
                          f'Extourne créée automatiquement au 01/01/{annee+1}.')
            note_extourne = f'Contre-passation automatique du cutoff {annee}. Annule charge pour ré-enregistrement lors échéance réelle.'

            proposition = {
                'type_evenement': 'CUTOFF_INTERETS_COURUS',
                'description': f'Intérêts courus prêt {banque}: {interets_courus}€ + extourne',
                'confiance': 1.0,  # Calcul automatique précis
                'ecritures': [
                    # Écriture 1: Cutoff 31/12/N (exercice N)
                    {
                        'date_ecriture': date_cutoff,
                        'libelle_ecriture': libelle_cutoff,
                        'compte_debit': '661',    # Charges d'intérêts
                        'compte_credit': '1688',   # Intérêts courus
                        'montant': interets_courus,
                        'type_ecriture': 'CUTOFF_INTERETS_COURUS',
                        'notes': note_cutoff
                    },
                    # Écriture 2: Extourne 01/01/N+1 (exercice N+1)
                    {
                        'date_ecriture': date_extourne,
                        'libelle_ecriture': libelle_extourne,
                        'compte_debit': '1688',    # INVERSION
                        'compte_credit': '661',    # INVERSION
                        'montant': interets_courus,
                        'type_ecriture': 'EXTOURNE_CUTOFF',
                        'notes': note_extourne
                    }
                ]
            }

            propositions.append(proposition)

        return propositions


# EXEMPLE D'UTILISATION
if __name__ == '__main__':
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models_module2 import ExerciceComptable
    import os
    import argparse
    import sys

    parser = argparse.ArgumentParser(description='Calcul des intérêts courus et génération des cutoffs')
    parser.add_argument('--exercice', type=int, required=True, help='Année de l\'exercice')
    parser.add_argument('--execute', action='store_true', help='Exécuter réellement (sinon dry-run)')
    args = parser.parse_args()

    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        print("❌ DATABASE_URL non définie")
        sys.exit(1)

    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # Récupérer l'exercice
        exercice = session.query(ExerciceComptable).filter_by(annee=args.exercice).first()
        if not exercice:
            print(f"❌ Exercice {args.exercice} non trouvé")
            sys.exit(1)

        exercice_id = exercice.id
        date_cloture = date(args.exercice, 12, 31)

        calculateur = CalculateurInteretsCourus(session)

        print("=" * 80)
        print("🧮 CALCUL INTÉRÊTS COURUS")
        print("=" * 80)

        propositions = calculateur.calculer_interets_courus_exercice(exercice_id, date_cloture)

        if propositions:
            print("=" * 80)
            print("📋 PROPOSITIONS DE CUTOFF")
            print("=" * 80)
            print()

            total_interets = 0
            for prop in propositions:
                print(f"  {prop['description']}")
                for ec in prop['ecritures']:
                    print(f"    {ec['date_ecriture']} : Débit {ec['compte_debit']} / Crédit {ec['compte_credit']} : {ec['montant']}€")
                    if ec['date_ecriture'].year == args.exercice:  # Seulement les cutoffs pour le total
                        total_interets += ec['montant']
                print()

            print("-" * 80)
            print(f"  TOTAL INTÉRÊTS COURUS : {total_interets:,.2f}€")
            print("=" * 80)
            print()

            # Créer les écritures si --execute
            if args.execute:
                from models_module2 import EcritureComptable

                print("💾 CRÉATION DES ÉCRITURES...")
                print()

                compteur_cutoff = 1
                compteur_extourne = 1

                for prop in propositions:
                    for ec in prop['ecritures']:
                        # Déterminer le type et le numéro
                        is_cutoff = ec['date_ecriture'].year == args.exercice
                        type_ecriture = 'CUTOFF_INTERETS_COURUS' if is_cutoff else 'EXTOURNE_CUTOFF'

                        if is_cutoff:
                            numero = f"{args.exercice}-1231-CUT-{compteur_cutoff:03d}"
                            compteur_cutoff += 1
                            exercice_ecriture = exercice.id
                        else:
                            numero = f"{args.exercice + 1}-0101-EXT-{compteur_extourne:03d}"
                            compteur_extourne += 1
                            # Trouver exercice N+1
                            exercice_suivant = session.query(ExerciceComptable).filter_by(annee=args.exercice + 1).first()
                            if not exercice_suivant:
                                print(f"  ⚠️  Exercice {args.exercice + 1} n'existe pas, création...")
                                exercice_suivant = ExerciceComptable(
                                    annee=args.exercice + 1,
                                    date_debut=date(args.exercice + 1, 1, 1),
                                    date_fin=date(args.exercice + 1, 12, 31),
                                    statut='OUVERT'
                                )
                                session.add(exercice_suivant)
                                session.flush()
                            exercice_ecriture = exercice_suivant.id

                        ecriture = EcritureComptable(
                            exercice_id=exercice_ecriture,
                            numero_ecriture=numero,
                            date_ecriture=ec['date_ecriture'],
                            libelle_ecriture=ec['libelle_ecriture'],
                            compte_debit=ec['compte_debit'],
                            compte_credit=ec['compte_credit'],
                            montant=ec['montant'],
                            type_ecriture=type_ecriture,
                            notes=ec.get('notes', '')
                        )
                        session.add(ecriture)
                        print(f"  ✅ {ec['date_ecriture']} | {numero} | {ec['compte_debit']} → {ec['compte_credit']} | {ec['montant']}€")

                session.commit()
                print()
                print("✅ ÉCRITURES CRÉÉES AVEC SUCCÈS")
                print("=" * 80)
            else:
                print()
                print("🔍 MODE DRY-RUN : Aucune écriture créée")
                print("   Pour créer réellement, ajouter --execute")
                print("=" * 80)

    except Exception as e:
        print(f"❌ Erreur : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        session.close()
