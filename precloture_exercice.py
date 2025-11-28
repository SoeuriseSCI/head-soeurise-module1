#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRÉ-CLÔTURE D'EXERCICE
======================

Phase préalable à l'Assemblée Générale (janvier-février N+1).

OBJECTIFS :
1. Générer les 4 cutoffs + extournes automatiques
2. Calculer l'Impôt sur les Sociétés (IS)
3. Produire les états financiers provisoires
4. Proposer l'affectation du résultat

WORKFLOW :
    python precloture_exercice.py --exercice 2024
    python precloture_exercice.py --exercice 2024 --execute

ÉTAPES PRÉ-CLÔTURE :
1. Vérifications préalables (exercice existe, pas déjà pré-clôturé)
2. Créer exercice N+1 si nécessaire
3. Générer cutoffs + extournes :
   A. Intérêts courus (1688)
   B. Produits SCPI à recevoir (4181)
   C. Charges à payer - Honoraires (4081)
   D. Charges constatées d'avance - Assurance (486)
4. Calculer l'IS
5. Générer états financiers provisoires
6. Proposer affectation résultat

IMPORTANT :
- Les cutoffs sont créés sur l'exercice N (31/12/N)
- Les extournes sont créées sur l'exercice N+1 (01/01/N+1)
- L'IS est comptabilisé sur l'exercice N (31/12/N)
"""

import sys
import os
import json
import argparse
from datetime import date, datetime
from decimal import Decimal
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models_module2 import (
    get_session, ExerciceComptable, EcritureComptable, PlanCompte
)


class DateTimeEncoder(json.JSONEncoder):
    """Encodeur JSON personnalisé pour les objets date/datetime/Decimal."""
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


# ==============================================================================
# CONSTANTES
# ==============================================================================

# Comptes de régularisation temporaire (cutoff/extourne)
COMPTE_INTERETS_COURUS = '1688'  # Intérêts courus sur emprunts
COMPTE_PAR = '4181'  # Produits à recevoir
COMPTE_CAP = '4081'  # Charges à payer (FNP - Factures non parvenues)
COMPTE_CCA = '486'   # Charges constatées d'avance
COMPTE_PCA = '487'   # Produits constatés d'avance

# Comptes de gestion
COMPTE_CHARGES_INTERETS = '661'  # Charges d'intérêts
COMPTE_PRODUITS_SCPI = '761'     # Produits des participations
COMPTE_HONORAIRES = '6226'       # Honoraires
COMPTE_ASSURANCE = '616'         # Primes d'assurance

# Comptes fiscalité
COMPTE_IS = '695'                # Impôts sur les bénéfices
COMPTE_DETTE_IS = '444'          # État - Impôts sur les bénéfices

# Comptes résultat et report
COMPTE_RESULTAT_BENEFICE = '120'
COMPTE_REPORT_NOUVEAU_DEBITEUR = '119'
COMPTE_REPORT_NOUVEAU_CREDITEUR = '110'

# Statuts exercice
STATUT_OUVERT = 'OUVERT'
STATUT_CLOTURE = 'CLOTURE'


class PreClotureExercice:
    """
    Gère la pré-clôture d'un exercice comptable.

    Cette phase intervient AVANT l'Assemblée Générale.
    """

    def __init__(self, session, exercice_annee: int):
        """
        Args:
            session: Session SQLAlchemy
            exercice_annee: Année de l'exercice à pré-clôturer
        """
        self.session = session
        self.annee = exercice_annee
        self.exercice = None
        self.exercice_suivant = None
        self.date_cloture = date(exercice_annee, 12, 31)
        self.date_ouverture_suivant = date(exercice_annee + 1, 1, 1)

        # Données calculées
        self.soldes = {}
        self.resultat_brut = Decimal('0')
        self.deficit_reportable = Decimal('0')
        self.is_calcule = Decimal('0')
        self.resultat_net = Decimal('0')

        # Écritures proposées
        self.ecritures_cutoff = []
        self.ecritures_extourne = []
        self.ecriture_is = None

    def charger_exercices(self) -> bool:
        """Charge l'exercice N et vérifie/crée N+1."""
        self.exercice = self.session.query(ExerciceComptable).filter_by(
            annee=self.annee
        ).first()

        if not self.exercice:
            print(f"❌ Exercice {self.annee} non trouvé")
            return False

        if self.exercice.statut == STATUT_CLOTURE:
            print(f"⚠️  Exercice {self.annee} déjà clôturé")
            return False

        # Charger ou créer exercice N+1
        self.exercice_suivant = self.session.query(ExerciceComptable).filter_by(
            annee=self.annee + 1
        ).first()

        return True

    def calculer_soldes(self) -> Dict:
        """Calcule les soldes de tous les comptes."""
        ecritures = self.session.query(EcritureComptable).filter_by(
            exercice_id=self.exercice.id
        ).all()

        self.soldes = defaultdict(lambda: {
            'debit': Decimal('0'),
            'credit': Decimal('0'),
            'libelle': '',
            'type': '',
            'classe': 0
        })

        for e in ecritures:
            montant = Decimal(str(e.montant))
            self.soldes[e.compte_debit]['debit'] += montant
            self.soldes[e.compte_credit]['credit'] += montant

            # Récupérer infos compte
            for compte_num in [e.compte_debit, e.compte_credit]:
                cpte = self.session.query(PlanCompte).filter_by(
                    numero_compte=compte_num
                ).first()
                if cpte:
                    self.soldes[compte_num]['libelle'] = cpte.libelle
                    self.soldes[compte_num]['type'] = cpte.type_compte
                    if compte_num and compte_num[0].isdigit():
                        self.soldes[compte_num]['classe'] = int(compte_num[0])

        for num_compte, data in self.soldes.items():
            data['solde'] = data['debit'] - data['credit']

        return dict(self.soldes)

    def calculer_resultat_brut(self) -> Decimal:
        """
        Calcule le résultat brut de l'exercice (avant IS).

        Returns:
            Résultat brut (produits - charges)
        """
        self.calculer_soldes()

        total_charges = sum(
            data['solde']
            for num, data in self.soldes.items()
            if data['classe'] == 6
        )
        total_produits = sum(
            abs(data['solde'])
            for num, data in self.soldes.items()
            if data['classe'] == 7
        )

        self.resultat_brut = total_produits - total_charges

        # Récupérer le déficit reportable
        if COMPTE_REPORT_NOUVEAU_DEBITEUR in self.soldes:
            solde_119 = self.soldes[COMPTE_REPORT_NOUVEAU_DEBITEUR]['solde']
            if solde_119 > 0:
                self.deficit_reportable = solde_119

        return self.resultat_brut

    def etape1_verifications(self) -> bool:
        """
        ÉTAPE 1: Vérifications préalables.

        Returns:
            True si vérifications OK
        """
        print("\n" + "=" * 80)
        print("ÉTAPE 1 : VÉRIFICATIONS PRÉALABLES")
        print("=" * 80)

        # Vérifier que pas de cutoffs déjà existants
        cutoffs_existants = self.session.query(EcritureComptable).filter(
            EcritureComptable.exercice_id == self.exercice.id,
            EcritureComptable.type_ecriture.in_([
                'CUTOFF_INTERETS_COURUS',
                'CUTOFF_SCPI',
                'CUTOFF_HONORAIRES',
                'CUTOFF_ASSURANCE'
            ])
        ).all()

        if cutoffs_existants:
            print(f"\n  ⚠️  {len(cutoffs_existants)} cutoff(s) déjà existant(s) !")
            print("     Exercice déjà pré-clôturé ?")
            for c in cutoffs_existants:
                print(f"     - {c.type_ecriture} : {c.montant}€")
            return False

        print(f"\n  ✅ Exercice {self.annee} : {self.exercice.statut}")
        print(f"  ✅ Aucun cutoff existant")
        return True

    def etape2_creer_exercice_suivant(self, execute: bool = False) -> bool:
        """
        ÉTAPE 2: Créer l'exercice N+1 si nécessaire.

        Args:
            execute: Si True, crée réellement l'exercice

        Returns:
            True si succès
        """
        print("\n" + "=" * 80)
        print(f"ÉTAPE 2 : EXERCICE {self.annee + 1}")
        print("=" * 80)

        if self.exercice_suivant:
            print(f"\n  ℹ️  Exercice {self.annee + 1} existe déjà (statut: {self.exercice_suivant.statut})")
            return True

        if execute:
            self.exercice_suivant = ExerciceComptable(
                annee=self.annee + 1,
                date_debut=self.date_ouverture_suivant,
                date_fin=date(self.annee + 1, 12, 31),
                statut=STATUT_OUVERT,
                description=f"Exercice {self.annee + 1}"
            )
            self.session.add(self.exercice_suivant)
            self.session.flush()
            print(f"\n  ✅ Exercice {self.annee + 1} créé")
        else:
            print(f"\n  📋 Exercice {self.annee + 1} sera créé")

        return True

    def etape3_generer_cutoffs(self, execute: bool = False) -> Dict:
        """
        ÉTAPE 3: Générer les 4 cutoffs + extournes.

        A. Intérêts courus (1688)
        B. Produits SCPI à recevoir (4181)
        C. Charges à payer - Honoraires (4081)
        D. Charges constatées d'avance - Assurance (486)

        Args:
            execute: Si True, crée réellement les écritures

        Returns:
            Dictionnaire avec les écritures générées
        """
        print("\n" + "=" * 80)
        print("ÉTAPE 3 : GÉNÉRATION CUTOFFS + EXTOURNES")
        print("=" * 80)

        self.ecritures_cutoff = []
        self.ecritures_extourne = []

        # A. Intérêts courus (DÉSACTIVÉ - fourni manuellement)
        print("\n  A. INTÉRÊTS COURUS (1688)")
        print("  " + "-" * 76)
        print("  ⚠️  Calcul automatique DÉSACTIVÉ (27/11/2025)")
        print("     Les intérêts courus sont fournis manuellement via email")
        print("     pour garantir cohérence avec montants expert-comptable")
        print("     → Utiliser DetecteurCutoffsMultiples avec email manuel")

        # B. Produits SCPI à recevoir (4181)
        # NOTE: Nécessite information du gérant - pour l'instant, placeholder
        print("\n  B. PRODUITS SCPI À RECEVOIR (4181)")
        print("  " + "-" * 76)
        print("  ⚠️  Cutoff SCPI nécessite information du gérant")
        print("     (Dividendes T4 annoncés mais non encore versés)")
        print("     → À implémenter via email spécifique")

        # C. Charges à payer - Honoraires (4081)
        # NOTE: Nécessite information du gérant - pour l'instant, placeholder
        print("\n  C. CHARGES À PAYER - HONORAIRES (4081)")
        print("  " + "-" * 76)
        print("  ⚠️  Cutoff honoraires nécessite information du gérant")
        print("     (Honoraires comptables engagés mais non facturés)")
        print("     → À implémenter via email spécifique")

        # D. Charges constatées d'avance - Assurance (486)
        # NOTE: Nécessite information du gérant - pour l'instant, placeholder
        print("\n  D. CHARGES CONSTATÉES D'AVANCE - ASSURANCE (486)")
        print("  " + "-" * 76)
        print("  ⚠️  Cutoff assurance nécessite information du gérant")
        print("     (Fraction d'assurance payée couvrant N+1)")
        print("     → À implémenter via email spécifique")

        print("\n  " + "=" * 76)
        print(f"  📊 TOTAL : {len(self.ecritures_cutoff)} cutoff(s) + {len(self.ecritures_extourne)} extourne(s)")

        if execute and (self.ecritures_cutoff or self.ecritures_extourne):
            print("\n  💾 CRÉATION DES ÉCRITURES...")

            compteur_cutoff = 1
            compteur_extourne = 1

            for ec in self.ecritures_cutoff:
                numero = f"{self.annee}-1231-CUT-{compteur_cutoff:03d}"
                ecriture = EcritureComptable(
                    exercice_id=self.exercice.id,
                    numero_ecriture=numero,
                    date_ecriture=ec['date_ecriture'],
                    libelle_ecriture=ec['libelle_ecriture'],
                    compte_debit=ec['compte_debit'],
                    compte_credit=ec['compte_credit'],
                    montant=ec['montant'],
                    type_ecriture=ec['type_ecriture'],
                    notes=ec.get('notes', '')
                )
                self.session.add(ecriture)
                print(f"     ✅ {numero} | {ec['montant']}€")
                compteur_cutoff += 1

            for ec in self.ecritures_extourne:
                numero = f"{self.annee + 1}-0101-EXT-{compteur_extourne:03d}"
                ecriture = EcritureComptable(
                    exercice_id=self.exercice_suivant.id,
                    numero_ecriture=numero,
                    date_ecriture=ec['date_ecriture'],
                    libelle_ecriture=ec['libelle_ecriture'],
                    compte_debit=ec['compte_debit'],
                    compte_credit=ec['compte_credit'],
                    montant=ec['montant'],
                    type_ecriture=ec['type_ecriture'],
                    notes=ec.get('notes', '')
                )
                self.session.add(ecriture)
                print(f"     ✅ {numero} | {ec['montant']}€")
                compteur_extourne += 1

            self.session.commit()
            print("  ✅ Écritures créées")

        return {
            'cutoffs': self.ecritures_cutoff,
            'extournes': self.ecritures_extourne
        }

    def etape4_calculer_is(self, execute: bool = False) -> Dict:
        """
        ÉTAPE 4: Calculer l'Impôt sur les Sociétés.

        Formule :
        - Résultat fiscal = Résultat brut - Déficit reportable
        - Si Résultat fiscal ≤ 0 → IS = 0
        - Sinon :
            - IS = 15% (jusqu'à 42 500€) + 25% (au-delà)

        Args:
            execute: Si True, crée réellement l'écriture

        Returns:
            Dictionnaire avec détails IS
        """
        print("\n" + "=" * 80)
        print("ÉTAPE 4 : CALCUL IMPÔT SUR LES SOCIÉTÉS")
        print("=" * 80)

        # Calculer résultat brut
        self.calculer_resultat_brut()

        print(f"\n  📊 Résultat brut : {self.resultat_brut:,.2f}€")
        print(f"     Déficit reportable : {self.deficit_reportable:,.2f}€")

        # Calculer base imposable
        base_imposable = max(Decimal('0'), self.resultat_brut - self.deficit_reportable)
        print(f"     Base imposable : {base_imposable:,.2f}€")

        # Calculer IS
        if base_imposable <= 0:
            self.is_calcule = Decimal('0')
            taux_applique = "0% (déficit ou base nulle)"
        elif base_imposable <= 42500:
            self.is_calcule = base_imposable * Decimal('0.15')
            taux_applique = "15% (jusqu'à 42 500€)"
        else:
            part_15 = Decimal('42500') * Decimal('0.15')
            part_25 = (base_imposable - Decimal('42500')) * Decimal('0.25')
            self.is_calcule = part_15 + part_25
            taux_applique = "15% (42 500€) + 25% (excédent)"

        self.is_calcule = self.is_calcule.quantize(Decimal('0.01'))
        self.resultat_net = self.resultat_brut - self.is_calcule

        print(f"\n  💰 IS calculé : {self.is_calcule:,.2f}€ ({taux_applique})")
        print(f"     Résultat net : {self.resultat_net:,.2f}€")

        # Préparer écriture IS
        if self.is_calcule > 0:
            self.ecriture_is = {
                'numero_ecriture': f"{self.annee}-1231-IS-001",
                'date_ecriture': self.date_cloture,
                'libelle_ecriture': f"Impôt sur les sociétés {self.annee}",
                'compte_debit': COMPTE_IS,  # 695
                'compte_credit': COMPTE_DETTE_IS,  # 444
                'montant': float(self.is_calcule),
                'type_ecriture': 'IMPOT_SOCIETES',
                'notes': f"Base imposable: {base_imposable:,.2f}€. {taux_applique}."
            }

            if execute:
                print("\n  💾 CRÉATION ÉCRITURE IS...")
                ecriture = EcritureComptable(
                    exercice_id=self.exercice.id,
                    numero_ecriture=self.ecriture_is['numero_ecriture'],
                    date_ecriture=self.ecriture_is['date_ecriture'],
                    libelle_ecriture=self.ecriture_is['libelle_ecriture'],
                    compte_debit=self.ecriture_is['compte_debit'],
                    compte_credit=self.ecriture_is['compte_credit'],
                    montant=self.ecriture_is['montant'],
                    type_ecriture=self.ecriture_is['type_ecriture'],
                    notes=self.ecriture_is['notes']
                )
                self.session.add(ecriture)
                self.session.commit()
                print(f"     ✅ {self.ecriture_is['numero_ecriture']} | {self.is_calcule:,.2f}€")
        else:
            print("\n  ℹ️  IS = 0€ (aucune écriture nécessaire)")

        return {
            'resultat_brut': float(self.resultat_brut),
            'deficit_reportable': float(self.deficit_reportable),
            'base_imposable': float(base_imposable),
            'taux_applique': taux_applique,
            'is': float(self.is_calcule),
            'resultat_net': float(self.resultat_net),
            'ecriture': self.ecriture_is
        }

    def etape5_generer_etats_financiers(self) -> Dict:
        """
        ÉTAPE 5: Générer les états financiers provisoires.

        Returns:
            Dictionnaire avec bilan et compte de résultat
        """
        print("\n" + "=" * 80)
        print("ÉTAPE 5 : ÉTATS FINANCIERS PROVISOIRES")
        print("=" * 80)

        print("\n  ℹ️  Génération des états financiers...")
        print("     (Bilan + Compte de résultat)")

        # Calculer soldes finaux
        self.calculer_soldes()

        # Construire bilan simplifié
        actif = {}
        passif = {}

        for num_compte, data in self.soldes.items():
            classe = data['classe']
            solde = data['solde']

            if classe == 0 or abs(solde) < 0.01:
                continue

            # Classe 1 : Passif
            if classe == 1:
                if solde != 0:
                    # Compte 119 (RAN débiteur) = perte antérieure
                    # Solde débiteur (positif) → DIMINUE le passif
                    if num_compte == '119':
                        passif[num_compte] = {
                            'libelle': data['libelle'],
                            'montant': float(-abs(solde))  # Négatif au passif
                        }
                    else:
                        passif[num_compte] = {
                            'libelle': data['libelle'],
                            'montant': float(abs(solde))
                        }
            # Classe 2 : Immobilisations (actif, mais certains comptes correcteurs)
            elif classe == 2:
                if solde != 0:
                    if num_compte.startswith('29'):  # Amortissements (correcteur d'actif)
                        actif[num_compte] = {
                            'libelle': data['libelle'],
                            'montant': float(solde)  # Négatif
                        }
                    else:
                        actif[num_compte] = {
                            'libelle': data['libelle'],
                            'montant': float(solde)
                        }
            # Classe 3 : Stocks (actif)
            elif classe == 3:
                if solde != 0:
                    actif[num_compte] = {
                        'libelle': data['libelle'],
                        'montant': float(solde)
                    }
            # Classe 4 : Tiers (actif OU passif selon le solde)
            elif classe == 4:
                if solde > 0.01:  # Solde débiteur → ACTIF
                    actif[num_compte] = {
                        'libelle': data['libelle'],
                        'montant': float(solde)
                    }
                elif solde < -0.01:  # Solde créditeur → PASSIF
                    passif[num_compte] = {
                        'libelle': data['libelle'],
                        'montant': float(abs(solde))
                    }
            # Classe 5 : Financier (actif si positif, passif si négatif)
            elif classe == 5:
                if solde > 0.01:
                    actif[num_compte] = {
                        'libelle': data['libelle'],
                        'montant': float(solde)
                    }
                elif solde < -0.01:
                    passif[num_compte] = {
                        'libelle': data['libelle'],
                        'montant': float(abs(solde))
                    }

        # Ajouter résultat au passif
        if self.resultat_net != 0:
            passif['120'] = {
                'libelle': 'Résultat de l\'exercice',
                'montant': float(self.resultat_net)
            }

        total_actif = sum(data['montant'] for data in actif.values())
        total_passif = sum(data['montant'] for data in passif.values())

        print(f"\n  📊 BILAN PROVISOIRE AU 31/12/{self.annee}")
        print(f"     Total ACTIF  : {total_actif:,.2f}€")
        print(f"     Total PASSIF : {total_passif:,.2f}€")
        print(f"     Équilibre    : {'✅ OK' if abs(total_actif - total_passif) < 1 else '❌ DÉSÉQUILIBRÉ'}")

        # Compte de résultat
        charges = {
            num: {'libelle': data['libelle'], 'montant': float(data['solde'])}
            for num, data in self.soldes.items()
            if data['classe'] == 6 and data['solde'] > 0
        }

        produits = {
            num: {'libelle': data['libelle'], 'montant': float(abs(data['solde']))}
            for num, data in self.soldes.items()
            if data['classe'] == 7 and data['solde'] < 0
        }

        total_charges = sum(data['montant'] for data in charges.values())
        total_produits = sum(data['montant'] for data in produits.values())

        print(f"\n  📊 COMPTE DE RÉSULTAT {self.annee}")
        print(f"     Total CHARGES  : {total_charges:,.2f}€")
        print(f"     Total PRODUITS : {total_produits:,.2f}€")
        print(f"     RÉSULTAT NET   : {self.resultat_net:,.2f}€")

        return {
            'bilan': {
                'actif': actif,
                'passif': passif,
                'total_actif': total_actif,
                'total_passif': total_passif
            },
            'compte_resultat': {
                'charges': charges,
                'produits': produits,
                'total_charges': total_charges,
                'total_produits': total_produits,
                'resultat_net': float(self.resultat_net)
            }
        }

    def etape6_proposer_affectation(self) -> Dict:
        """
        ÉTAPE 6: Proposer l'affectation du résultat.

        Returns:
            Dictionnaire avec proposition d'affectation
        """
        print("\n" + "=" * 80)
        print("ÉTAPE 6 : PROPOSITION AFFECTATION RÉSULTAT")
        print("=" * 80)

        proposition = []

        print(f"\n  📊 Résultat net à affecter : {self.resultat_net:,.2f}€")
        print(f"     Déficit reportable      : {self.deficit_reportable:,.2f}€")

        if self.resultat_net > 0:
            # BÉNÉFICE
            if self.deficit_reportable > 0:
                # Absorption partielle ou totale du déficit
                absorption = min(self.deficit_reportable, self.resultat_net)
                reste = self.resultat_net - absorption

                if absorption > 0:
                    proposition.append({
                        'type': 'ABSORPTION_DEFICIT',
                        'montant': float(absorption),
                        'description': f"Absorption déficit antérieur : {absorption:,.2f}€",
                        'ecriture': f"Débit 120 / Crédit 119 = {absorption:,.2f}€"
                    })
                    print(f"\n  → Absorption déficit : {absorption:,.2f}€")

                if reste > 0:
                    proposition.append({
                        'type': 'REPORT_NOUVEAU_CREDITEUR',
                        'montant': float(reste),
                        'description': f"Report à nouveau (excédent) : {reste:,.2f}€",
                        'ecriture': f"Débit 120 / Crédit 110 = {reste:,.2f}€"
                    })
                    print(f"  → Report à nouveau : {reste:,.2f}€")
            else:
                # Pas de déficit, tout en report à nouveau
                proposition.append({
                    'type': 'REPORT_NOUVEAU_CREDITEUR',
                    'montant': float(self.resultat_net),
                    'description': f"Report à nouveau (bénéfice) : {self.resultat_net:,.2f}€",
                    'ecriture': f"Débit 120 / Crédit 110 = {self.resultat_net:,.2f}€"
                })
                print(f"\n  → Report à nouveau : {self.resultat_net:,.2f}€")

        elif self.resultat_net < 0:
            # PERTE
            proposition.append({
                'type': 'REPORT_NOUVEAU_DEBITEUR',
                'montant': float(abs(self.resultat_net)),
                'description': f"Report à nouveau (perte) : {abs(self.resultat_net):,.2f}€",
                'ecriture': f"Débit 119 / Crédit 129 = {abs(self.resultat_net):,.2f}€"
            })
            print(f"\n  → Report à nouveau (perte) : {abs(self.resultat_net):,.2f}€")
        else:
            print("\n  ℹ️  Résultat nul, pas d'affectation nécessaire")

        print("\n  ⚠️  IMPORTANT : Affectation sera validée par AG et comptabilisée sur N+1")

        return {
            'resultat_net': float(self.resultat_net),
            'deficit_reportable': float(self.deficit_reportable),
            'propositions': proposition
        }

    def executer_precloture(self, execute: bool = False) -> Dict:
        """
        Exécute toutes les étapes de pré-clôture.

        Args:
            execute: Si True, effectue réellement les modifications

        Returns:
            Rapport complet de pré-clôture
        """
        print("\n" + "=" * 80)
        print(f"🔍 PRÉ-CLÔTURE EXERCICE {self.annee}")
        print("=" * 80)
        print(f"   Mode : {'EXÉCUTION' if execute else 'SIMULATION'}")
        print(f"   Date : {datetime.now().strftime('%d/%m/%Y %H:%M')}")

        if not self.charger_exercices():
            return {'erreur': 'Exercice non trouvé ou déjà clôturé'}

        # Exécuter les étapes
        if not self.etape1_verifications():
            return {'erreur': 'Vérifications préalables échouées'}

        self.etape2_creer_exercice_suivant(execute)
        ecritures_cutoff = self.etape3_generer_cutoffs(execute)
        fiscalite = self.etape4_calculer_is(execute)
        etats_financiers = self.etape5_generer_etats_financiers()
        affectation = self.etape6_proposer_affectation()

        # Construire le rapport
        rapport = {
            'date_precloture': datetime.now().isoformat(),
            'exercice': self.annee,
            'mode': 'EXECUTION' if execute else 'SIMULATION',
            'exercice_suivant_cree': self.exercice_suivant is not None,
            'ecritures_cutoff': {
                'nb_cutoffs': len(self.ecritures_cutoff),
                'nb_extournes': len(self.ecritures_extourne),
                'ecritures': ecritures_cutoff
            },
            'fiscalite': fiscalite,
            'resultat': {
                'brut': float(self.resultat_brut),
                'is': float(self.is_calcule),
                'net': float(self.resultat_net)
            },
            'etats_financiers': etats_financiers,
            'affectation_proposee': affectation,
            'prochaines_etapes': [
                f"1. Vérifier les états financiers provisoires",
                f"2. Convoquer l'Assemblée Générale",
                f"3. Présenter les comptes à l'AG",
                f"4. Faire voter l'affectation du résultat",
                f"5. Établir le PV d'AG",
                f"6. Envoyer email 'CLOTURE EXERCICE {self.annee}' avec PV AG"
            ]
        }

        # Sauvegarder le rapport
        output_file = f"precloture_{self.annee}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(rapport, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)

        print("\n" + "=" * 80)
        print("✅ PRÉ-CLÔTURE TERMINÉE" if execute else "✅ SIMULATION TERMINÉE")
        print("=" * 80)
        print(f"\n   📁 Rapport sauvegardé : {output_file}")

        if execute:
            print(f"\n   ✅ Cutoffs créés : {len(self.ecritures_cutoff)}")
            print(f"   ✅ Extournes créées : {len(self.ecritures_extourne)}")
            if self.is_calcule > 0:
                print(f"   ✅ IS comptabilisé : {self.is_calcule:,.2f}€")

        print("\n   🎯 PROCHAINES ÉTAPES :")
        for etape in rapport['prochaines_etapes']:
            print(f"      {etape}")

        return rapport


# ==============================================================================
# POINT D'ENTRÉE
# ==============================================================================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Pré-clôture d'exercice comptable (avant AG)"
    )
    parser.add_argument(
        '--exercice',
        type=int,
        required=True,
        help="Année de l'exercice à pré-clôturer"
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help="Exécuter réellement (sinon simulation)"
    )
    args = parser.parse_args()

    DATABASE_URL = os.environ.get('DATABASE_URL')
    if not DATABASE_URL:
        print("❌ DATABASE_URL non définie")
        sys.exit(1)

    session = get_session(DATABASE_URL)

    try:
        precloture = PreClotureExercice(session, args.exercice)
        rapport = precloture.executer_precloture(execute=args.execute)

        if 'erreur' in rapport:
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()
