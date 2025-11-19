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
                numero_pret,
                banque,
                taux_annuel,
                capital_initial
            FROM echeances_prets
            WHERE date_echeance <= :date_cloture
            ORDER BY banque
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
            numero_pret = pret[0]
            banque = pret[1]
            taux_annuel = float(pret[2])
            capital_initial = float(pret[3])

            print(f"  💰 Prêt {banque} ({numero_pret[:15]}...)")
            print(f"     Taux annuel : {taux_annuel:.4f}%")

            # Trouver la dernière échéance payée avant date_cloture
            query_derniere = text("""
                SELECT
                    date_echeance,
                    capital_restant_apres,
                    montant_interet
                FROM echeances_prets
                WHERE numero_pret = :numero_pret
                  AND date_echeance <= :date_cloture
                ORDER BY date_echeance DESC
                LIMIT 1
            """)

            derniere = self.session.execute(query_derniere, {
                'numero_pret': numero_pret,
                'date_cloture': date_cloture
            }).fetchone()

            if not derniere:
                print(f"     ⚠️  Aucune échéance trouvée")
                continue

            date_derniere_echeance = derniere[0]
            capital_restant = float(derniere[1])

            # Calculer nombre de jours entre dernière échéance et clôture
            jours_courus = (date_cloture - date_derniere_echeance).days

            if jours_courus <= 0:
                print(f"     ℹ️  Échéance au {date_derniere_echeance} = jour de clôture, pas d'intérêts courus")
                continue

            # Calculer intérêts courus
            # Formule : Capital × Taux × (Jours / 365)
            interets_courus = capital_restant * (taux_annuel / 100) * (jours_courus / 365)
            interets_courus = round(interets_courus, 2)

            print(f"     Dernière échéance : {date_derniere_echeance}")
            print(f"     Capital restant : {capital_restant:,.2f}€")
            print(f"     Jours courus : {jours_courus}")
            print(f"     ✅ Intérêts courus : {interets_courus:,.2f}€")
            print()

            # Générer proposition de cutoff
            libelle = f"Cutoff {annee} - Intérêts courus prêt {banque} ({jours_courus} jours)"

            proposition = {
                'type_evenement': 'CUTOFF_INTERETS_COURUS',
                'description': f'Intérêts courus prêt {banque}: {interets_courus}€',
                'confiance': 1.0,  # Calcul automatique précis
                'ecritures': [
                    {
                        'date_ecriture': date_cloture,
                        'libelle_ecriture': libelle,
                        'compte_debit': '661',    # Charges d'intérêts
                        'compte_credit': '1688',   # Intérêts courus
                        'montant': interets_courus,
                        'type_ecriture': 'CUTOFF_INTERETS_COURUS',
                        'notes': (f'Calcul automatique: {capital_restant:,.2f}€ × {taux_annuel}% × ({jours_courus}/365). '
                                 f'Période: {date_derniere_echeance + timedelta(days=1)} → {date_cloture}. '
                                 f'Extourne automatique au 01/01/{annee+1}.')
                    }
                ]
            }

            propositions.append(proposition)

        return propositions


# EXEMPLE D'UTILISATION
if __name__ == '__main__':
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import os

    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        print("❌ DATABASE_URL non définie")
        exit(1)

    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        calculateur = CalculateurInteretsCourus(session)

        # Calculer intérêts courus pour exercice 2024
        exercice_id = 2  # ID exercice 2024
        date_cloture = date(2024, 12, 31)

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
                    total_interets += ec['montant']
                print()

            print("-" * 80)
            print(f"  TOTAL INTÉRÊTS COURUS : {total_interets:,.2f}€")
            print("=" * 80)

    except Exception as e:
        print(f"❌ Erreur : {e}")
        import traceback
        traceback.print_exc()

    finally:
        session.close()
