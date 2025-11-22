#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLÔTURE DÉFINITIVE D'EXERCICE
=============================

Phase finale après approbation des comptes par l'AG.

PRÉREQUIS :
- Pré-clôture effectuée (precloture_exercice.py)
- PV d'AG validant les comptes et l'affectation du résultat

ÉTAPES CLÔTURE DÉFINITIVE :
1. Vérifier que la pré-clôture est faite
2. Enregistrer l'affectation du résultat (vers Report à Nouveau)
3. Geler l'exercice (statut = CLOTURE)
4. Créer/vérifier le bilan d'ouverture N+1
5. Vérifier les extournes automatiques
6. Générer les Cerfa (déclarations fiscales) - PLACEHOLDER

WORKFLOW :
    python cloture_exercice.py --exercice 2024 --pv-ag "PV AG du 15/03/2025"
    python cloture_exercice.py --exercice 2024 --pv-ag "PV AG du 15/03/2025" --execute
"""

import sys
import os
import json
import argparse
from datetime import date, datetime
from decimal import Decimal
from collections import defaultdict
from typing import Dict, List, Optional


class DateTimeEncoder(json.JSONEncoder):
    """Encodeur JSON personnalisé pour les objets date/datetime/Decimal."""
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models_module2 import (
    get_session, ExerciceComptable, EcritureComptable, PlanCompte
)


# ==============================================================================
# CONSTANTES
# ==============================================================================

# Comptes comptables pour l'affectation
COMPTE_RESULTAT_BENEFICE = '120'
COMPTE_RESULTAT_PERTE = '129'
COMPTE_REPORT_NOUVEAU_DEBITEUR = '119'
COMPTE_REPORT_NOUVEAU_CREDITEUR = '110'
COMPTE_BILAN_OUVERTURE = '89'

# Statuts exercice
STATUT_OUVERT = 'OUVERT'
STATUT_CLOTURE = 'CLOTURE'
STATUT_VALIDE = 'VALIDE'


class ClotureExercice:
    """
    Gère la clôture définitive d'un exercice comptable.

    Cette phase intervient APRÈS l'approbation des comptes par l'AG.
    """

    def __init__(self, session, exercice_annee: int, pv_ag: str):
        """
        Args:
            session: Session SQLAlchemy
            exercice_annee: Année de l'exercice à clôturer
            pv_ag: Référence du PV d'AG (ex: "PV AG du 15/03/2025")
        """
        self.session = session
        self.annee = exercice_annee
        self.pv_ag = pv_ag
        self.exercice = None
        self.exercice_suivant = None
        self.date_cloture = date(exercice_annee, 12, 31)
        self.date_ouverture_suivant = date(exercice_annee + 1, 1, 1)

        # Données calculées
        self.soldes = {}
        self.resultat_net = Decimal('0')
        self.deficit_reportable = Decimal('0')

    def charger_exercices(self) -> bool:
        """Charge l'exercice N et N+1."""
        self.exercice = self.session.query(ExerciceComptable).filter_by(
            annee=self.annee
        ).first()

        if not self.exercice:
            print(f"❌ Exercice {self.annee} non trouvé")
            return False

        if self.exercice.statut == STATUT_VALIDE:
            print(f"⚠️  Exercice {self.annee} déjà validé définitivement")
            return False

        # Charger ou créer exercice N+1
        self.exercice_suivant = self.session.query(ExerciceComptable).filter_by(
            annee=self.annee + 1
        ).first()

        return True

    def calculer_soldes(self) -> Dict:
        """Calcule les soldes finaux de tous les comptes."""
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

    def _calculer_soldes_cloture(self) -> Dict:
        """
        Calcule les soldes de clôture de l'exercice N pour le bilan d'ouverture N+1.

        IMPORTANT : Exclut explicitement les écritures d'affectation pour garantir
        que les écritures d'ouverture reflètent l'état AVANT affectation.

        Contexte : Les écritures d'affectation sont normalement créées sur l'exercice N+1,
        mais par sécurité (compatibilité avec d'anciennes versions), on les exclut explicitement.

        Returns:
            Dictionnaire des soldes par compte (état de clôture N = état d'ouverture N+1)
        """
        ecritures = self.session.query(EcritureComptable).filter(
            EcritureComptable.exercice_id == self.exercice.id,
            EcritureComptable.type_ecriture != 'AFFECTATION_RESULTAT'
        ).all()

        soldes = defaultdict(lambda: {
            'debit': Decimal('0'),
            'credit': Decimal('0'),
            'libelle': '',
            'type': '',
            'classe': 0
        })

        for e in ecritures:
            montant = Decimal(str(e.montant))
            soldes[e.compte_debit]['debit'] += montant
            soldes[e.compte_credit]['credit'] += montant

            # Récupérer infos compte
            for compte_num in [e.compte_debit, e.compte_credit]:
                cpte = self.session.query(PlanCompte).filter_by(
                    numero_compte=compte_num
                ).first()
                if cpte:
                    soldes[compte_num]['libelle'] = cpte.libelle
                    soldes[compte_num]['type'] = cpte.type_compte
                    if compte_num and compte_num[0].isdigit():
                        soldes[compte_num]['classe'] = int(compte_num[0])

        for num_compte, data in soldes.items():
            data['solde'] = data['debit'] - data['credit']

        return dict(soldes)

    def calculer_resultat_net(self) -> Decimal:
        """
        Calcule le résultat net de l'exercice.

        Returns:
            Résultat net (produits - charges incluant IS)
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

        self.resultat_net = total_produits - total_charges

        # Récupérer le déficit reportable
        if COMPTE_REPORT_NOUVEAU_DEBITEUR in self.soldes:
            solde_119 = self.soldes[COMPTE_REPORT_NOUVEAU_DEBITEUR]['solde']
            if solde_119 > 0:
                self.deficit_reportable = solde_119

        return self.resultat_net

    def etape1_verifier_precloture(self) -> bool:
        """
        ÉTAPE 1: Vérifier que la pré-clôture a été effectuée.

        Vérifie la présence des écritures de cutoff et IS.

        Returns:
            True si pré-clôture OK
        """
        print("\n" + "=" * 80)
        print("ÉTAPE 1 : VÉRIFICATION PRÉ-CLÔTURE")
        print("=" * 80)

        # Vérifier écritures de cutoff
        ecritures_cutoff = self.session.query(EcritureComptable).filter(
            EcritureComptable.exercice_id == self.exercice.id,
            EcritureComptable.type_ecriture == 'CUTOFF_INTERETS_COURUS'
        ).all()

        # Vérifier écriture IS (si bénéfice)
        ecriture_is = self.session.query(EcritureComptable).filter(
            EcritureComptable.exercice_id == self.exercice.id,
            EcritureComptable.type_ecriture == 'IMPOT_SOCIETES'
        ).first()

        print(f"\n  📋 Vérifications :")
        print(f"     Écritures cutoff intérêts : {len(ecritures_cutoff)}")
        print(f"     Écriture IS               : {'✅ Présente' if ecriture_is else 'ℹ️  Absente (IS=0 ou non calculé)'}")

        # Calculer le résultat pour vérification
        self.calculer_resultat_net()
        print(f"     Résultat net calculé      : {self.resultat_net:,.2f}€")

        # Si bénéfice et pas d'écriture IS, avertir mais ne pas bloquer
        # (IS peut être 0 en cas de déficit reportable)
        if self.resultat_net > 0 and not ecriture_is:
            print("\n  ⚠️  Bénéfice détecté mais pas d'écriture IS")
            print("     Vérifiez que le déficit reportable couvre le bénéfice")

        return True

    def etape2_affectation_resultat(self, execute: bool = False) -> List[Dict]:
        """
        ÉTAPE 2: Enregistrer l'affectation du résultat.

        Le résultat est affecté au report à nouveau.
        Si bénéfice et déficit antérieur : absorption du déficit.

        Args:
            execute: Si True, crée réellement les écritures

        Returns:
            Liste des écritures créées
        """
        print("\n" + "=" * 80)
        print("ÉTAPE 2 : AFFECTATION DU RÉSULTAT")
        print("=" * 80)

        # PROTECTION ANTI-DOUBLON : Vérifier si des écritures d'affectation existent déjà
        ecritures_existantes = self.session.query(EcritureComptable).filter(
            EcritureComptable.exercice_id == self.exercice.id,
            EcritureComptable.type_ecriture == 'AFFECTATION_RESULTAT'
        ).all()

        if ecritures_existantes:
            print(f"\n  ⚠️  ATTENTION : {len(ecritures_existantes)} écriture(s) d'affectation existe(nt) déjà !")
            for ec in ecritures_existantes:
                print(f"     - ID {ec.id} : {ec.numero_ecriture} | {ec.montant}€")
            print("\n  ❌ Affectation annulée pour éviter les doublons.")
            print("     Supprimez les écritures existantes si vous voulez relancer l'affectation.")
            return []

        ecritures = []

        print(f"\n  📊 Résultat à affecter : {self.resultat_net:,.2f}€")
        print(f"     Déficit reportable  : {self.deficit_reportable:,.2f}€")
        print(f"     Référence AG        : {self.pv_ag}")

        if self.resultat_net > 0:
            # BÉNÉFICE
            if self.deficit_reportable > 0:
                # Absorption partielle ou totale du déficit
                absorption = min(self.deficit_reportable, self.resultat_net)
                reste = self.resultat_net - absorption

                if absorption > 0:
                    ecritures.append({
                        'numero_ecriture': f"{self.annee}-1231-AFF-001",
                        'date_ecriture': self.date_cloture,
                        'libelle_ecriture': f"Affectation résultat {self.annee} - Absorption déficit ({self.pv_ag})",
                        'compte_debit': COMPTE_RESULTAT_BENEFICE,  # 120
                        'compte_credit': COMPTE_REPORT_NOUVEAU_DEBITEUR,  # 119
                        'montant': float(absorption),
                        'type_ecriture': 'AFFECTATION_RESULTAT',
                        'notes': f"Absorption déficit antérieur. {self.pv_ag}"
                    })
                    print(f"\n  → Absorption déficit : {absorption:,.2f}€")
                    print(f"    Débit 120 / Crédit 119")

                if reste > 0:
                    ecritures.append({
                        'numero_ecriture': f"{self.annee}-1231-AFF-002",
                        'date_ecriture': self.date_cloture,
                        'libelle_ecriture': f"Affectation résultat {self.annee} - Report à nouveau ({self.pv_ag})",
                        'compte_debit': COMPTE_RESULTAT_BENEFICE,  # 120
                        'compte_credit': COMPTE_REPORT_NOUVEAU_CREDITEUR,  # 110
                        'montant': float(reste),
                        'type_ecriture': 'AFFECTATION_RESULTAT',
                        'notes': f"Excédent après absorption déficit. {self.pv_ag}"
                    })
                    print(f"\n  → Report à nouveau : {reste:,.2f}€")
                    print(f"    Débit 120 / Crédit 110")
            else:
                # Pas de déficit, tout en report à nouveau
                ecritures.append({
                    'numero_ecriture': f"{self.annee}-1231-AFF-001",
                    'date_ecriture': self.date_cloture,
                    'libelle_ecriture': f"Affectation résultat {self.annee} - Report à nouveau ({self.pv_ag})",
                    'compte_debit': COMPTE_RESULTAT_BENEFICE,  # 120
                    'compte_credit': COMPTE_REPORT_NOUVEAU_CREDITEUR,  # 110
                    'montant': float(self.resultat_net),
                    'type_ecriture': 'AFFECTATION_RESULTAT',
                    'notes': f"Bénéfice reporté. {self.pv_ag}"
                })
                print(f"\n  → Report à nouveau (bénéfice) : {self.resultat_net:,.2f}€")
                print(f"    Débit 120 / Crédit 110")

        elif self.resultat_net < 0:
            # PERTE
            ecritures.append({
                'numero_ecriture': f"{self.annee}-1231-AFF-001",
                'date_ecriture': self.date_cloture,
                'libelle_ecriture': f"Affectation résultat {self.annee} - Perte ({self.pv_ag})",
                'compte_debit': COMPTE_REPORT_NOUVEAU_DEBITEUR,  # 119
                'compte_credit': COMPTE_RESULTAT_PERTE,  # 129
                'montant': float(abs(self.resultat_net)),
                'type_ecriture': 'AFFECTATION_RESULTAT',
                'notes': f"Perte reportée. {self.pv_ag}"
            })
            print(f"\n  → Report à nouveau (perte) : {abs(self.resultat_net):,.2f}€")
            print(f"    Débit 119 / Crédit 129")
        else:
            print("\n  ℹ️  Résultat nul, pas d'affectation")

        if execute and ecritures:
            # L'affectation du résultat se fait sur l'exercice N+1 (date de l'AG)
            # Créer l'exercice N+1 s'il n'existe pas
            if not self.exercice_suivant:
                self.exercice_suivant = ExerciceComptable(
                    annee=self.annee + 1,
                    date_debut=self.date_ouverture_suivant,
                    date_fin=date(self.annee + 1, 12, 31),
                    statut=STATUT_OUVERT,
                    description=f"Exercice {self.annee + 1}"
                )
                self.session.add(self.exercice_suivant)
                self.session.flush()
                print(f"\n  ✅ Exercice {self.annee + 1} créé pour l'affectation")

            print(f"\n  💾 Création des écritures d'affectation sur exercice {self.annee + 1}...")
            for ec in ecritures:
                # Date d'affectation = 01/01/N+1 (convention comptable)
                date_affectation = self.date_ouverture_suivant
                numero_affectation = ec['numero_ecriture'].replace(f"{self.annee}-1231", f"{self.annee + 1}-0101")

                ecriture = EcritureComptable(
                    exercice_id=self.exercice_suivant.id,  # CORRECTION : N+1 au lieu de N
                    numero_ecriture=numero_affectation,
                    date_ecriture=date_affectation,  # CORRECTION : 01/01/N+1 au lieu de 31/12/N
                    libelle_ecriture=ec['libelle_ecriture'],
                    compte_debit=ec['compte_debit'],
                    compte_credit=ec['compte_credit'],
                    montant=ec['montant'],
                    type_ecriture=ec['type_ecriture'],
                    notes=ec['notes']
                )
                self.session.add(ecriture)
                print(f"     ✅ {numero_affectation} (exercice {self.annee + 1})")
            self.session.commit()
        elif ecritures:
            print("\n  🔍 Mode simulation - Écritures non créées")
            print(f"     (Seront créées sur exercice {self.annee + 1})")

        return ecritures

    def etape3_geler_exercice(self, execute: bool = False) -> bool:
        """
        ÉTAPE 3: Geler l'exercice (passage en statut CLOTURE).

        Args:
            execute: Si True, modifie réellement le statut

        Returns:
            True si succès
        """
        print("\n" + "=" * 80)
        print("ÉTAPE 3 : GEL DE L'EXERCICE")
        print("=" * 80)

        print(f"\n  📋 Exercice {self.annee}")
        print(f"     Statut actuel : {self.exercice.statut}")
        print(f"     Nouveau statut: {STATUT_CLOTURE}")

        if execute:
            self.exercice.statut = STATUT_CLOTURE
            self.exercice.description = (
                f"{self.exercice.description or ''}\n"
                f"Clôturé le {datetime.now().strftime('%d/%m/%Y')} - {self.pv_ag}"
            ).strip()
            self.session.commit()
            print(f"\n  ✅ Exercice {self.annee} clôturé")
        else:
            print("\n  🔍 Mode simulation - Statut non modifié")

        return True

    def etape4_bilan_ouverture_suivant(self, execute: bool = False) -> Dict:
        """
        ÉTAPE 4: Créer/vérifier le bilan d'ouverture N+1.

        Le bilan d'ouverture reprend les soldes du bilan de clôture.

        Args:
            execute: Si True, crée réellement les écritures

        Returns:
            Informations sur le bilan d'ouverture
        """
        print("\n" + "=" * 80)
        print(f"ÉTAPE 4 : BILAN D'OUVERTURE {self.annee + 1}")
        print("=" * 80)

        # Créer exercice N+1 si nécessaire
        if not self.exercice_suivant:
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
        else:
            print(f"\n  ℹ️  Exercice {self.annee + 1} existe déjà (statut: {self.exercice_suivant.statut})")

        # Vérifier si des écritures d'ouverture existent déjà
        ecritures_ouverture_existantes = []
        if self.exercice_suivant:
            ecritures_ouverture_existantes = self.session.query(EcritureComptable).filter(
                EcritureComptable.exercice_id == self.exercice_suivant.id,
                EcritureComptable.type_ecriture.in_(['INIT_BILAN', 'BILAN_OUVERTURE'])
            ).all()

        if ecritures_ouverture_existantes:
            print(f"\n  ℹ️  {len(ecritures_ouverture_existantes)} écritures d'ouverture déjà présentes")
            print("     Le bilan d'ouverture semble déjà constitué")
            return {
                'status': 'EXISTE_DEJA',
                'nb_ecritures': len(ecritures_ouverture_existantes)
            }

        # Calculer les soldes de clôture de l'exercice N (AVANT affectation)
        # pour créer les écritures d'ouverture de l'exercice N+1
        print(f"\n  🔍 Calcul des soldes de clôture {self.annee} (état AVANT affectation)...")
        soldes_cloture = self._calculer_soldes_cloture()

        # Préparer les écritures d'ouverture (classes 1-5 uniquement)
        ecritures_ouverture = []
        compteur = 1

        print(f"\n  📝 Écritures d'ouverture à créer :")

        for num_compte, data in sorted(soldes_cloture.items()):
            classe = data['classe']
            solde = data['solde']

            # Ignorer compte 89, classes 6-7, et soldes nuls
            if num_compte == '89' or classe in [6, 7, 0] or abs(solde) < Decimal('0.01'):
                continue

            # Solde débiteur → ACTIF : Débit compte / Crédit 89
            # Solde créditeur → PASSIF : Débit 89 / Crédit compte
            if solde > 0:
                compte_debit = num_compte
                compte_credit = COMPTE_BILAN_OUVERTURE
            else:
                compte_debit = COMPTE_BILAN_OUVERTURE
                compte_credit = num_compte
                solde = abs(solde)

            ecriture = {
                'numero_ecriture': f"{self.annee + 1}-0101-OUV-{compteur:03d}",
                'date_ecriture': self.date_ouverture_suivant,
                'libelle_ecriture': f"Bilan d'ouverture {self.annee + 1} - {data['libelle'][:50]}",
                'compte_debit': compte_debit,
                'compte_credit': compte_credit,
                'montant': float(solde),
                'type_ecriture': 'BILAN_OUVERTURE',
                'notes': f"Reprise solde {self.annee} du compte {num_compte}"
            }
            ecritures_ouverture.append(ecriture)
            print(f"     {num_compte} ({data['libelle'][:30]}...) : {solde:,.2f}€")
            compteur += 1

        print(f"\n  📊 Total : {len(ecritures_ouverture)} écritures d'ouverture")

        if execute and self.exercice_suivant and ecritures_ouverture:
            print("\n  💾 Création des écritures d'ouverture...")
            for ec in ecritures_ouverture:
                ecriture = EcritureComptable(
                    exercice_id=self.exercice_suivant.id,
                    numero_ecriture=ec['numero_ecriture'],
                    date_ecriture=ec['date_ecriture'],
                    libelle_ecriture=ec['libelle_ecriture'],
                    compte_debit=ec['compte_debit'],
                    compte_credit=ec['compte_credit'],
                    montant=ec['montant'],
                    type_ecriture=ec['type_ecriture'],
                    notes=ec['notes']
                )
                self.session.add(ecriture)
            self.session.commit()
            print(f"  ✅ {len(ecritures_ouverture)} écritures d'ouverture créées")
        elif ecritures_ouverture:
            print("\n  🔍 Mode simulation - Écritures non créées")

        return {
            'status': 'CREE' if execute else 'A_CREER',
            'nb_ecritures': len(ecritures_ouverture),
            'ecritures': ecritures_ouverture
        }

    def etape5_verifier_extournes(self) -> Dict:
        """
        ÉTAPE 5: Vérifier les extournes automatiques.

        Les écritures de cutoff ont une extourne au 01/01/N+1.

        Returns:
            Informations sur les extournes
        """
        print("\n" + "=" * 80)
        print(f"ÉTAPE 5 : VÉRIFICATION EXTOURNES {self.annee + 1}")
        print("=" * 80)

        if not self.exercice_suivant:
            print("\n  ⚠️  Exercice suivant non créé, extournes non vérifiables")
            return {'status': 'EXERCICE_SUIVANT_MANQUANT'}

        # Chercher les extournes
        extournes = self.session.query(EcritureComptable).filter(
            EcritureComptable.exercice_id == self.exercice_suivant.id,
            EcritureComptable.type_ecriture == 'EXTOURNE_CUTOFF'
        ).all()

        print(f"\n  📋 Extournes trouvées : {len(extournes)}")

        if extournes:
            total = sum(Decimal(str(e.montant)) for e in extournes)
            print(f"     Total extourné : {total:,.2f}€")
            for e in extournes:
                print(f"     - {e.numero_ecriture} : {e.montant}€ ({e.libelle_ecriture[:40]}...)")
        else:
            print("     ℹ️  Aucune extourne (normal si pas de cutoff)")

        return {
            'status': 'OK',
            'nb_extournes': len(extournes),
            'extournes': [
                {
                    'numero': e.numero_ecriture,
                    'montant': float(e.montant),
                    'libelle': e.libelle_ecriture
                }
                for e in extournes
            ]
        }

    def etape6_generer_cerfa(self) -> Dict:
        """
        ÉTAPE 6: Générer les Cerfa (déclarations fiscales).

        PLACEHOLDER - À implémenter selon les besoins spécifiques.

        Cerfa potentiels pour une SCI à l'IS :
        - Formulaire 2065 : Déclaration IS
        - Formulaire 2033 : Bilan simplifié
        - Formulaire 2050-2059 : Liasse fiscale

        Returns:
            Informations sur les Cerfa à produire
        """
        print("\n" + "=" * 80)
        print("ÉTAPE 6 : GÉNÉRATION CERFA (DÉCLARATIONS FISCALES)")
        print("=" * 80)

        print("\n  ⚠️  PLACEHOLDER - Module Cerfa à développer")
        print("\n  📋 Déclarations fiscales SCI à l'IS :")
        print("     - Formulaire 2065 : Déclaration de résultat IS")
        print("     - Formulaire 2033-A à 2033-G : Liasse fiscale simplifiée")
        print("     - Relevé de frais généraux (si applicable)")

        cerfa_info = {
            'status': 'A_DEVELOPPER',
            'formulaires_requis': [
                {
                    'numero': '2065',
                    'nom': 'Déclaration de résultat IS',
                    'date_limite': f"15/05/{self.annee + 1}"
                },
                {
                    'numero': '2033',
                    'nom': 'Liasse fiscale simplifiée',
                    'date_limite': f"15/05/{self.annee + 1}"
                }
            ],
            'note': "Module Cerfa à implémenter - génération PDF automatique"
        }

        print(f"\n  📅 Date limite déclaration IS : 15/05/{self.annee + 1}")
        print("     (2ème jour ouvré suivant le 1er mai)")

        return cerfa_info

    def executer_cloture(self, execute: bool = False) -> Dict:
        """
        Exécute toutes les étapes de clôture définitive.

        Args:
            execute: Si True, effectue réellement les modifications

        Returns:
            Rapport complet de clôture
        """
        print("\n" + "=" * 80)
        print(f"🔒 CLÔTURE DÉFINITIVE EXERCICE {self.annee}")
        print("=" * 80)
        print(f"   Mode          : {'EXÉCUTION' if execute else 'SIMULATION'}")
        print(f"   Date clôture  : {self.date_cloture}")
        print(f"   Référence AG  : {self.pv_ag}")

        if not self.charger_exercices():
            return {'erreur': 'Exercice non trouvé ou déjà validé'}

        # Exécuter les étapes
        self.etape1_verifier_precloture()
        ecritures_affectation = self.etape2_affectation_resultat(execute)
        self.etape3_geler_exercice(execute)
        bilan_ouverture = self.etape4_bilan_ouverture_suivant(execute)
        extournes = self.etape5_verifier_extournes()
        cerfa = self.etape6_generer_cerfa()

        # Construire le rapport
        rapport = {
            'date_cloture': datetime.now().isoformat(),
            'exercice': self.annee,
            'pv_ag': self.pv_ag,
            'mode': 'EXECUTION' if execute else 'SIMULATION',
            'resultat_net': float(self.resultat_net),
            'affectation': {
                'nb_ecritures': len(ecritures_affectation),
                'ecritures': ecritures_affectation
            },
            'exercice_cloture': {
                'statut': STATUT_CLOTURE if execute else self.exercice.statut
            },
            'bilan_ouverture_suivant': bilan_ouverture,
            'extournes': extournes,
            'cerfa': cerfa,
            'actions_restantes': [
                "Télédéclarer le résultat sur impots.gouv.fr",
                "Payer l'IS si applicable (avant le 15/05)",
                "Archiver les documents comptables (10 ans)",
                "Mettre à jour le registre des décisions"
            ]
        }

        # Sauvegarder le rapport
        output_file = f"cloture_{self.annee}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(rapport, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)

        print("\n" + "=" * 80)
        print("✅ CLÔTURE TERMINÉE" if execute else "✅ SIMULATION TERMINÉE")
        print("=" * 80)
        print(f"\n   📁 Rapport sauvegardé : {output_file}")

        if execute:
            print(f"\n   🔒 Exercice {self.annee} est maintenant CLÔTURÉ")
            print(f"   📂 Exercice {self.annee + 1} est OUVERT")

        print("\n   🎯 ACTIONS RESTANTES :")
        for action in rapport['actions_restantes']:
            print(f"      - {action}")

        return rapport


# ==============================================================================
# POINT D'ENTRÉE
# ==============================================================================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Clôture définitive d'exercice comptable (après AG)"
    )
    parser.add_argument(
        '--exercice',
        type=int,
        required=True,
        help="Année de l'exercice à clôturer"
    )
    parser.add_argument(
        '--pv-ag',
        type=str,
        required=True,
        help="Référence du PV d'AG (ex: 'PV AG du 15/03/2025')"
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
        cloture = ClotureExercice(session, args.exercice, args.pv_ag)
        rapport = cloture.executer_cloture(execute=args.execute)

        if 'erreur' in rapport:
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ Erreur : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()
