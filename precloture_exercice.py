#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PRÉ-CLÔTURE D'EXERCICE
======================

Phase préparatoire à la clôture définitive (avant AG).

ÉTAPES PRÉ-CLÔTURE :
1. Cutoff intérêts courus (déclenchement à la clôture)
2. Calcul de l'IS (impôt sur les sociétés)
3. Écriture IS si applicable (Débit 695 / Crédit 444)
4. Production états financiers provisoires
5. Proposition d'affectation du résultat

RÈGLES FISCALES SCI :
- Taux IS réduit : 15% jusqu'à 42 500€ de bénéfice (PME)
- Déficit reportable : Les pertes antérieures réduisent la base imposable
- Compte 119 = Report à nouveau débiteur (pertes accumulées)

WORKFLOW :
    python precloture_exercice.py --exercice 2024
    python precloture_exercice.py --exercice 2024 --execute
"""

import sys
import os
import json
import argparse
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models_module2 import (
    get_session, ExerciceComptable, EcritureComptable, PlanCompte
)
from cutoff_extourne_interets import CalculateurInteretsCourus


# ==============================================================================
# CONSTANTES FISCALES
# ==============================================================================

TAUX_IS_REDUIT = Decimal('0.15')  # 15% pour PME (< 42 500€)
SEUIL_TAUX_REDUIT = Decimal('42500')
TAUX_IS_NORMAL = Decimal('0.25')  # 25% au-delà

# Comptes comptables
COMPTE_RESULTAT_BENEFICE = '120'     # Résultat de l'exercice (bénéfice)
COMPTE_RESULTAT_PERTE = '129'        # Résultat de l'exercice (perte)
COMPTE_REPORT_NOUVEAU_DEBITEUR = '119'  # Report à nouveau débiteur (pertes)
COMPTE_REPORT_NOUVEAU_CREDITEUR = '110'  # Report à nouveau créditeur (bénéfices)
COMPTE_IS_CHARGE = '695'             # Impôt sur les bénéfices
COMPTE_IS_DU = '444'                 # État - Impôt sur les sociétés


class PreClotureExercice:
    """
    Gère la pré-clôture d'un exercice comptable.

    Cette phase prépare les états financiers définitifs avant
    l'approbation par l'AG.
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
        self.date_cloture = date(exercice_annee, 12, 31)

        # Résultats calculés
        self.soldes = {}
        self.total_charges = Decimal('0')
        self.total_produits = Decimal('0')
        self.resultat_brut = Decimal('0')
        self.deficit_reportable = Decimal('0')
        self.base_imposable = Decimal('0')
        self.is_calcule = Decimal('0')
        self.resultat_net = Decimal('0')

        # Écritures à créer
        self.ecritures_cutoff = []
        self.ecriture_is = None

    def charger_exercice(self) -> bool:
        """Charge l'exercice depuis la BD."""
        self.exercice = self.session.query(ExerciceComptable).filter_by(
            annee=self.annee
        ).first()

        if not self.exercice:
            print(f"❌ Exercice {self.annee} non trouvé")
            return False

        if self.exercice.statut not in ['OUVERT', 'EN_PREPARATION']:
            print(f"⚠️  Exercice {self.annee} déjà clôturé (statut: {self.exercice.statut})")
            return False

        return True

    def calculer_soldes(self) -> Dict:
        """
        Calcule les soldes finaux de tous les comptes.

        Returns:
            Dictionnaire des soldes par compte
        """
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

            # Compte débit
            self.soldes[e.compte_debit]['debit'] += montant
            cpte_d = self.session.query(PlanCompte).filter_by(
                numero_compte=e.compte_debit
            ).first()
            if cpte_d:
                self.soldes[e.compte_debit]['libelle'] = cpte_d.libelle
                self.soldes[e.compte_debit]['type'] = cpte_d.type_compte
                if e.compte_debit and e.compte_debit[0].isdigit():
                    self.soldes[e.compte_debit]['classe'] = int(e.compte_debit[0])

            # Compte crédit
            self.soldes[e.compte_credit]['credit'] += montant
            cpte_c = self.session.query(PlanCompte).filter_by(
                numero_compte=e.compte_credit
            ).first()
            if cpte_c:
                self.soldes[e.compte_credit]['libelle'] = cpte_c.libelle
                self.soldes[e.compte_credit]['type'] = cpte_c.type_compte
                if e.compte_credit and e.compte_credit[0].isdigit():
                    self.soldes[e.compte_credit]['classe'] = int(e.compte_credit[0])

        # Calculer soldes nets
        for num_compte, data in self.soldes.items():
            data['solde'] = data['debit'] - data['credit']

        return dict(self.soldes)

    def etape1_cutoff_interets(self, execute: bool = False) -> List[Dict]:
        """
        ÉTAPE 1: Cutoff des intérêts courus.

        Calcule et crée les écritures de cutoff pour les intérêts
        courus non échus au 31/12.

        Args:
            execute: Si True, crée réellement les écritures

        Returns:
            Liste des propositions de cutoff
        """
        print("\n" + "=" * 80)
        print("ÉTAPE 1 : CUTOFF INTÉRÊTS COURUS")
        print("=" * 80)

        calculateur = CalculateurInteretsCourus(self.session)
        propositions = calculateur.calculer_interets_courus_exercice(
            self.exercice.id,
            self.date_cloture
        )

        if not propositions:
            print("  ℹ️  Aucun cutoff d'intérêts à enregistrer")
            return []

        self.ecritures_cutoff = propositions

        total_interets = sum(
            ec['montant']
            for prop in propositions
            for ec in prop['ecritures']
            if ec['date_ecriture'].year == self.annee
        )

        print(f"\n  📊 Total intérêts courus : {total_interets:,.2f}€")

        if execute:
            self._creer_ecritures_cutoff(propositions)
        else:
            print("\n  🔍 Mode simulation - Écritures non créées")
            print("     Ajouter --execute pour créer les écritures")

        return propositions

    def _creer_ecritures_cutoff(self, propositions: List[Dict]):
        """Crée réellement les écritures de cutoff."""
        print("\n  💾 Création des écritures de cutoff...")

        compteur_cutoff = 1
        compteur_extourne = 1

        for prop in propositions:
            for ec in prop['ecritures']:
                is_cutoff = ec['date_ecriture'].year == self.annee

                if is_cutoff:
                    numero = f"{self.annee}-1231-CUT-{compteur_cutoff:03d}"
                    compteur_cutoff += 1
                    exercice_id = self.exercice.id
                else:
                    numero = f"{self.annee + 1}-0101-EXT-{compteur_extourne:03d}"
                    compteur_extourne += 1
                    # Trouver ou créer exercice N+1
                    exercice_suivant = self.session.query(ExerciceComptable).filter_by(
                        annee=self.annee + 1
                    ).first()
                    if not exercice_suivant:
                        exercice_suivant = ExerciceComptable(
                            annee=self.annee + 1,
                            date_debut=date(self.annee + 1, 1, 1),
                            date_fin=date(self.annee + 1, 12, 31),
                            statut='OUVERT'
                        )
                        self.session.add(exercice_suivant)
                        self.session.flush()
                    exercice_id = exercice_suivant.id

                ecriture = EcritureComptable(
                    exercice_id=exercice_id,
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
                print(f"     ✅ {numero} | {ec['compte_debit']} → {ec['compte_credit']} | {ec['montant']}€")

        self.session.commit()
        print("\n  ✅ Écritures de cutoff créées")

    def etape2_calculer_resultat(self) -> Decimal:
        """
        ÉTAPE 2: Calcul du résultat de l'exercice.

        Calcule produits - charges pour obtenir le résultat brut.

        Returns:
            Résultat brut (avant IS)
        """
        print("\n" + "=" * 80)
        print("ÉTAPE 2 : CALCUL DU RÉSULTAT BRUT")
        print("=" * 80)

        # Recalculer les soldes après cutoff
        self.calculer_soldes()

        charges = {}
        produits = {}

        for num_compte, data in self.soldes.items():
            classe = data['classe']
            if num_compte == '89':
                continue
            if classe == 6:
                charges[num_compte] = data
            elif classe == 7:
                produits[num_compte] = data

        # Total charges (solde débiteur)
        self.total_charges = sum(
            data['solde'] for data in charges.values()
        )

        # Total produits (solde créditeur → valeur absolue)
        self.total_produits = sum(
            abs(data['solde']) for data in produits.values()
        )

        self.resultat_brut = self.total_produits - self.total_charges

        print(f"\n  📊 COMPTE DE RÉSULTAT {self.annee}")
        print(f"     PRODUITS (classe 7) : {self.total_produits:>14,.2f}€")
        print(f"     CHARGES (classe 6)  : {self.total_charges:>14,.2f}€")
        print("     " + "-" * 40)
        print(f"     RÉSULTAT BRUT       : {self.resultat_brut:>14,.2f}€", end="")
        print(" (BÉNÉFICE ✅)" if self.resultat_brut >= 0 else " (PERTE ❌)")

        return self.resultat_brut

    def etape3_calculer_is(self) -> Tuple[Decimal, Decimal, Decimal]:
        """
        ÉTAPE 3: Calcul de l'impôt sur les sociétés.

        Prend en compte :
        - Le déficit reportable (compte 119)
        - Le taux réduit PME (15% jusqu'à 42 500€)

        Returns:
            Tuple (déficit_reportable, base_imposable, is_calculé)
        """
        print("\n" + "=" * 80)
        print("ÉTAPE 3 : CALCUL IMPÔT SUR LES SOCIÉTÉS")
        print("=" * 80)

        # Récupérer le déficit reportable (compte 119)
        # Le compte 119 a un solde débiteur quand il y a des pertes
        self.deficit_reportable = Decimal('0')
        if COMPTE_REPORT_NOUVEAU_DEBITEUR in self.soldes:
            solde_119 = self.soldes[COMPTE_REPORT_NOUVEAU_DEBITEUR]['solde']
            if solde_119 > 0:  # Solde débiteur = pertes antérieures
                self.deficit_reportable = solde_119

        print(f"\n  📋 SITUATION FISCALE")
        print(f"     Résultat brut {self.annee}     : {self.resultat_brut:>14,.2f}€")
        print(f"     Déficit reportable (119) : {self.deficit_reportable:>14,.2f}€")

        # Calcul base imposable
        if self.resultat_brut <= 0:
            # Perte : pas d'IS
            self.base_imposable = Decimal('0')
            self.is_calcule = Decimal('0')
            print("\n  ℹ️  Exercice déficitaire → Pas d'IS")
        else:
            # Bénéfice : imputation du déficit reportable
            imputation = min(self.deficit_reportable, self.resultat_brut)
            self.base_imposable = self.resultat_brut - imputation

            print(f"     Imputation déficit       : {imputation:>14,.2f}€")
            print("     " + "-" * 40)
            print(f"     BASE IMPOSABLE           : {self.base_imposable:>14,.2f}€")

            if self.base_imposable <= 0:
                self.is_calcule = Decimal('0')
                print("\n  ✅ Déficit absorbant le bénéfice → IS = 0€")
            else:
                # Calcul IS avec taux progressif
                if self.base_imposable <= SEUIL_TAUX_REDUIT:
                    self.is_calcule = (self.base_imposable * TAUX_IS_REDUIT).quantize(
                        Decimal('0.01'), rounding=ROUND_HALF_UP
                    )
                    print(f"\n  📊 CALCUL IS (taux réduit 15%)")
                    print(f"     {self.base_imposable:,.2f}€ × 15% = {self.is_calcule:,.2f}€")
                else:
                    # Partie au taux réduit + partie au taux normal
                    is_reduit = (SEUIL_TAUX_REDUIT * TAUX_IS_REDUIT).quantize(
                        Decimal('0.01'), rounding=ROUND_HALF_UP
                    )
                    is_normal = ((self.base_imposable - SEUIL_TAUX_REDUIT) * TAUX_IS_NORMAL).quantize(
                        Decimal('0.01'), rounding=ROUND_HALF_UP
                    )
                    self.is_calcule = is_reduit + is_normal

                    print(f"\n  📊 CALCUL IS (taux progressif)")
                    print(f"     42 500€ × 15% = {is_reduit:,.2f}€")
                    print(f"     {self.base_imposable - SEUIL_TAUX_REDUIT:,.2f}€ × 25% = {is_normal:,.2f}€")
                    print(f"     TOTAL IS = {self.is_calcule:,.2f}€")

        # Résultat net après IS
        self.resultat_net = self.resultat_brut - self.is_calcule

        print("\n  " + "=" * 50)
        print(f"  💰 RÉSULTAT NET (après IS) : {self.resultat_net:>14,.2f}€")
        print("  " + "=" * 50)

        return (self.deficit_reportable, self.base_imposable, self.is_calcule)

    def etape4_ecriture_is(self, execute: bool = False) -> Optional[Dict]:
        """
        ÉTAPE 4: Création de l'écriture d'IS si applicable.

        Écriture : Débit 695 (Charges IS) / Crédit 444 (IS dû)

        Args:
            execute: Si True, crée réellement l'écriture

        Returns:
            Proposition d'écriture IS ou None
        """
        print("\n" + "=" * 80)
        print("ÉTAPE 4 : ÉCRITURE IMPÔT SUR LES SOCIÉTÉS")
        print("=" * 80)

        if self.is_calcule <= 0:
            print("\n  ℹ️  IS = 0€ → Aucune écriture à créer")
            return None

        self.ecriture_is = {
            'date_ecriture': self.date_cloture,
            'numero_ecriture': f"{self.annee}-1231-IS-001",
            'libelle_ecriture': f"Impôt sur les sociétés {self.annee}",
            'compte_debit': COMPTE_IS_CHARGE,    # 695
            'compte_credit': COMPTE_IS_DU,       # 444
            'montant': float(self.is_calcule),
            'type_ecriture': 'IMPOT_SOCIETES',
            'notes': f"IS {self.annee} - Base imposable: {self.base_imposable}€, Taux: 15% (PME)"
        }

        print(f"\n  📝 ÉCRITURE IS PROPOSÉE")
        print(f"     Date       : {self.date_cloture}")
        print(f"     Débit 695  : {self.is_calcule:,.2f}€ (Charges d'impôt)")
        print(f"     Crédit 444 : {self.is_calcule:,.2f}€ (IS à payer)")

        if execute:
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
            print("\n  ✅ Écriture IS créée")
        else:
            print("\n  🔍 Mode simulation - Écriture non créée")

        return self.ecriture_is

    def etape5_etats_financiers(self) -> Dict:
        """
        ÉTAPE 5: Production des états financiers provisoires.

        Returns:
            Dictionnaire avec bilan et compte de résultat
        """
        print("\n" + "=" * 80)
        print("ÉTAPE 5 : ÉTATS FINANCIERS PROVISOIRES")
        print("=" * 80)

        # Recalculer après écriture IS
        self.calculer_soldes()

        # Construire bilan et compte de résultat
        actif = {}
        passif = {}
        charges = {}
        produits = {}

        for num_compte, data in self.soldes.items():
            classe = data['classe']
            solde = data['solde']

            if num_compte == '89':
                continue

            if classe == 6:
                charges[num_compte] = {
                    'libelle': data['libelle'],
                    'montant': float(solde)
                }
            elif classe == 7:
                produits[num_compte] = {
                    'libelle': data['libelle'],
                    'montant': float(abs(solde))
                }
            elif classe in [1, 2, 3, 4, 5]:
                if solde > Decimal('0.01'):
                    actif[num_compte] = {
                        'libelle': data['libelle'],
                        'montant': float(solde)
                    }
                elif solde < Decimal('-0.01'):
                    passif[num_compte] = {
                        'libelle': data['libelle'],
                        'montant': float(abs(solde))
                    }

        # Recalculer résultat avec IS
        total_charges = sum(c['montant'] for c in charges.values())
        total_produits = sum(p['montant'] for p in produits.values())
        resultat = total_produits - total_charges

        total_actif = sum(a['montant'] for a in actif.values())
        total_passif = sum(p['montant'] for p in passif.values())

        # Le résultat va au passif (si bénéfice) ou à l'actif (si perte)
        if resultat >= 0:
            total_passif += resultat
        else:
            total_actif += abs(resultat)

        ecart = total_actif - total_passif

        etats = {
            'date_generation': datetime.now().isoformat(),
            'type': 'PRE_CLOTURE',
            'exercice': {
                'annee': self.annee,
                'date_debut': str(self.exercice.date_debut),
                'date_fin': str(self.exercice.date_fin),
                'statut': self.exercice.statut
            },
            'compte_resultat': {
                'charges': charges,
                'produits': produits,
                'total_charges': total_charges,
                'total_produits': total_produits,
                'resultat_brut': float(self.resultat_brut),
                'impot_societes': float(self.is_calcule),
                'resultat_net': resultat
            },
            'bilan': {
                'actif': actif,
                'passif': passif,
                'resultat_exercice': resultat,
                'total_actif': total_actif,
                'total_passif': total_passif,
                'equilibre': abs(ecart) < 0.01
            },
            'fiscalite': {
                'deficit_reportable_avant': float(self.deficit_reportable),
                'base_imposable': float(self.base_imposable),
                'taux_is_applique': '15% (PME)',
                'is_calcule': float(self.is_calcule),
                'deficit_reportable_apres': float(
                    max(Decimal('0'), self.deficit_reportable - self.resultat_brut)
                ) if self.resultat_brut > 0 else float(
                    self.deficit_reportable + abs(self.resultat_brut)
                )
            }
        }

        # Affichage résumé
        print(f"\n  📊 BILAN AU {self.date_cloture}")
        print(f"     ACTIF  : {total_actif:>14,.2f}€")
        print(f"     PASSIF : {total_passif:>14,.2f}€")
        print(f"     Écart  : {ecart:>14,.2f}€")
        print(f"     {'✅ Équilibré' if abs(ecart) < 0.01 else '❌ Non équilibré'}")

        print(f"\n  📊 COMPTE DE RÉSULTAT {self.annee}")
        print(f"     PRODUITS         : {total_produits:>14,.2f}€")
        print(f"     CHARGES          : {total_charges:>14,.2f}€")
        print(f"     RÉSULTAT NET     : {resultat:>14,.2f}€")

        return etats

    def etape6_proposition_affectation(self) -> Dict:
        """
        ÉTAPE 6: Proposition d'affectation du résultat.

        Pour une SCI, le résultat est généralement affecté :
        - En report à nouveau (compte 110/119)
        - En réserves si statuts le prévoient

        Returns:
            Proposition d'affectation
        """
        print("\n" + "=" * 80)
        print("ÉTAPE 6 : PROPOSITION D'AFFECTATION DU RÉSULTAT")
        print("=" * 80)

        # Calculer le nouveau déficit reportable
        if self.resultat_net >= 0:
            # Bénéfice : résorbe le déficit
            nouveau_deficit = max(
                Decimal('0'),
                self.deficit_reportable - self.resultat_net
            )
            affectation_ran = min(self.deficit_reportable, self.resultat_net)
            reste_a_affecter = self.resultat_net - affectation_ran
        else:
            # Perte : augmente le déficit
            nouveau_deficit = self.deficit_reportable + abs(self.resultat_net)
            affectation_ran = Decimal('0')
            reste_a_affecter = self.resultat_net

        proposition = {
            'resultat_net': float(self.resultat_net),
            'deficit_reportable_initial': float(self.deficit_reportable),
            'affectation': {
                'absorption_deficit': float(affectation_ran),
                'report_a_nouveau': float(reste_a_affecter),
                'reserves': 0,
                'dividendes': 0
            },
            'deficit_reportable_final': float(nouveau_deficit),
            'ecritures_proposees': []
        }

        print(f"\n  📋 AFFECTATION PROPOSÉE (à valider par AG)")
        print(f"     Résultat net {self.annee}              : {self.resultat_net:>14,.2f}€")
        print(f"     Déficit reportable antérieur (119) : {self.deficit_reportable:>14,.2f}€")

        if self.resultat_net >= 0 and self.deficit_reportable > 0:
            print(f"\n  → Absorption partielle du déficit : {affectation_ran:,.2f}€")
            print(f"  → Déficit restant après absorption : {nouveau_deficit:,.2f}€")

            if reste_a_affecter > 0:
                print(f"  → Excédent en report à nouveau    : {reste_a_affecter:,.2f}€")
        elif self.resultat_net >= 0:
            print(f"\n  → Affectation en report à nouveau : {self.resultat_net:,.2f}€")
        else:
            print(f"\n  → Perte à reporter : {abs(self.resultat_net):,.2f}€")
            print(f"  → Nouveau déficit cumulé : {nouveau_deficit:,.2f}€")

        # Écritures d'affectation (seront créées lors de la clôture définitive)
        if self.resultat_net > 0:
            # Bénéfice : Débit 120 / Crédit 110 ou 119
            if affectation_ran > 0:
                proposition['ecritures_proposees'].append({
                    'libelle': f"Affectation résultat {self.annee} - Absorption déficit",
                    'compte_debit': COMPTE_RESULTAT_BENEFICE,  # 120
                    'compte_credit': COMPTE_REPORT_NOUVEAU_DEBITEUR,  # 119
                    'montant': float(affectation_ran)
                })
            if reste_a_affecter > 0:
                proposition['ecritures_proposees'].append({
                    'libelle': f"Affectation résultat {self.annee} - Report à nouveau",
                    'compte_debit': COMPTE_RESULTAT_BENEFICE,  # 120
                    'compte_credit': COMPTE_REPORT_NOUVEAU_CREDITEUR,  # 110
                    'montant': float(reste_a_affecter)
                })
        elif self.resultat_net < 0:
            # Perte : Débit 119 / Crédit 129
            proposition['ecritures_proposees'].append({
                'libelle': f"Affectation résultat {self.annee} - Perte",
                'compte_debit': COMPTE_REPORT_NOUVEAU_DEBITEUR,  # 119
                'compte_credit': COMPTE_RESULTAT_PERTE,  # 129
                'montant': float(abs(self.resultat_net))
            })

        print("\n  📝 ÉCRITURES D'AFFECTATION (après AG)")
        for ec in proposition['ecritures_proposees']:
            print(f"     Débit {ec['compte_debit']} / Crédit {ec['compte_credit']} : {ec['montant']:,.2f}€")
            print(f"        → {ec['libelle']}")

        return proposition

    def executer_precloture(self, execute: bool = False) -> Dict:
        """
        Exécute toutes les étapes de pré-clôture.

        Args:
            execute: Si True, crée réellement les écritures

        Returns:
            Rapport complet de pré-clôture
        """
        print("\n" + "=" * 80)
        print(f"🔄 PRÉ-CLÔTURE EXERCICE {self.annee}")
        print("=" * 80)
        print(f"   Mode : {'EXÉCUTION' if execute else 'SIMULATION'}")
        print(f"   Date clôture : {self.date_cloture}")

        if not self.charger_exercice():
            return {'erreur': 'Exercice non trouvé ou déjà clôturé'}

        # Exécuter les étapes
        cutoffs = self.etape1_cutoff_interets(execute)
        self.etape2_calculer_resultat()
        self.etape3_calculer_is()
        self.etape4_ecriture_is(execute)
        etats = self.etape5_etats_financiers()
        affectation = self.etape6_proposition_affectation()

        # Construire le rapport
        rapport = {
            'date_precloture': datetime.now().isoformat(),
            'exercice': self.annee,
            'mode': 'EXECUTION' if execute else 'SIMULATION',
            'cutoffs_interets': [
                {
                    'description': p['description'],
                    'montant': sum(e['montant'] for e in p['ecritures'] if e['date_ecriture'].year == self.annee)
                }
                for p in cutoffs
            ],
            'resultat': {
                'brut': float(self.resultat_brut),
                'is': float(self.is_calcule),
                'net': float(self.resultat_net)
            },
            'fiscalite': etats['fiscalite'],
            'bilan': etats['bilan'],
            'affectation_proposee': affectation,
            'prochaines_etapes': [
                "1. Convoquer l'AG pour approbation des comptes",
                "2. Faire voter l'affectation du résultat",
                "3. Établir le PV d'AG",
                "4. Lancer la clôture définitive avec cloture_exercice.py"
            ]
        }

        # Sauvegarder le rapport
        output_file = f"precloture_{self.annee}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(rapport, f, indent=2, ensure_ascii=False)

        print("\n" + "=" * 80)
        print("✅ PRÉ-CLÔTURE TERMINÉE")
        print("=" * 80)
        print(f"\n   📁 Rapport sauvegardé : {output_file}")
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
