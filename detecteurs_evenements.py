#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DÉTECTEURS D'ÉVÉNEMENTS COMPTABLES
===================================
Détecteurs spécialisés pour identifier automatiquement le type d'événement
et générer les propositions d'écritures comptables appropriées.

Date: 05/11/2025
Auteur: Module Phase 1 - Accounting Events

ORGANISATION PAR PHASES:
------------------------
PHASE 1 (Simple - patterns fixes):
  - DetecteurAssurancePret
  - DetecteurFraisBancaires
  - DetecteurHonorairesComptable

PHASE 2 (Référence - lookup tables):
  - DetecteurRemboursementPret (nécessite echeances_prets)
  - DetecteurApportAssocie

PHASE 3 (Complexe - calculs):
  - DetecteurRevenuSCPI (revenus vs capital)
  - DetecteurAchatValeursMobilieres (PRU, portefeuille)
"""

import re
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text


# ═══════════════════════════════════════════════════════════════════════════════
# BASE DÉTECTEUR
# ═══════════════════════════════════════════════════════════════════════════════

class DetecteurBase:
    """
    Classe de base pour tous les détecteurs d'événements
    """

    def __init__(self, session: Session):
        """
        Initialise le détecteur

        Args:
            session: Session SQLAlchemy
        """
        self.session = session

    def detecter(self, evenement: Dict) -> bool:
        """
        Détecte si l'événement correspond à ce type

        Args:
            evenement: Dictionnaire avec les données de l'événement

        Returns:
            True si le détecteur reconnaît ce type d'événement
        """
        raise NotImplementedError("Méthode à implémenter par les sous-classes")

    def generer_proposition(self, evenement: Dict) -> Dict:
        """
        Génère une proposition d'écritures comptables

        Args:
            evenement: Dictionnaire avec les données de l'événement

        Returns:
            Dictionnaire avec la proposition:
                - type_evenement: Type d'événement détecté
                - ecritures: Liste d'écritures à créer
                - description: Description textuelle
                - confiance: Niveau de confiance (0-1)
        """
        raise NotImplementedError("Méthode à implémenter par les sous-classes")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1 - DÉTECTEURS SIMPLES
# ═══════════════════════════════════════════════════════════════════════════════

class DetecteurAssurancePret(DetecteurBase):
    """
    Détecte les prélèvements d'assurance emprunteur

    PATTERN:
    - Libellé contient: COVEA RISKS, ASSURANCE PRET, COTISATION ASSURANCE
    - Montant: 87.57€ (Emma 66.58€ + Pauline 20.99€)
    - Type: DEBIT
    - Fréquence: Mensuel (vers le 15 du mois)

    COMPTABILISATION:
    Débit 616 (Assurances emprunteur) : 87.57€
    Crédit 512 (Banque LCL)             : 87.57€

    NOTE IMPORTANTE:
    - Assurance UNIQUEMENT pour le prêt AMORTISSABLE (LCL - BRM0911AH)
    - PAS d'assurance pour le prêt IN FINE (INVESTIMUR - BRLZE11AQ)
    """

    MONTANT_ATTENDU = 87.57
    TOLERANCE = 0.10  # 10 centimes de tolérance

    def detecter(self, evenement: Dict) -> bool:
        """Détecte une assurance emprunteur"""
        libelle_norm = evenement.get('libelle_normalise', '').lower()
        montant = float(evenement.get('montant', 0))
        type_op = evenement.get('type_operation', '')

        # Vérifier le pattern
        patterns = ['covea', 'assurance pret', 'cotisation assurance', 'prelevement assurance']
        match_libelle = any(pattern in libelle_norm for pattern in patterns)

        # Vérifier le montant (avec tolérance)
        match_montant = abs(montant - self.MONTANT_ATTENDU) <= self.TOLERANCE

        # Vérifier que c'est un débit
        match_type = type_op == 'DEBIT'

        return match_libelle and match_montant and match_type

    def generer_proposition(self, evenement: Dict) -> Dict:
        """Génère la proposition d'écriture"""
        montant = float(evenement.get('montant', 0))
        date_op = evenement.get('date_operation')

        # Calculer niveau de confiance
        confiance = 1.0  # 100% si le pattern est reconnu
        if abs(montant - self.MONTANT_ATTENDU) > 0.01:
            confiance = 0.9  # Légère variation de montant

        return {
            'type_evenement': 'ASSURANCE_PRET',
            'description': f'Assurance emprunteur (Emma 66,58€ + Pauline 20,99€)',
            'confiance': confiance,
            'ecritures': [
                {
                    'date_ecriture': date_op,
                    'libelle_ecriture': f'Assurance emprunteur prêt LCL',
                    'compte_debit': '616',
                    'compte_credit': '512',
                    'montant': montant,
                    'type_ecriture': 'ASSURANCE_PRET',
                    'notes': 'Assurance uniquement pour prêt amortissable LCL (BRM0911AH)'
                }
            ]
        }


class DetecteurFraisBancaires(DetecteurBase):
    """
    Détecte les frais bancaires (tenue de compte, gestion)

    PATTERN:
    - Libellé contient: FRAIS, TENUE DE COMPTE, GESTION COMPTE, COTISATION CARTE
    - Montant variable (généralement < 20€)
    - Type: DEBIT
    - Fréquence: Mensuel ou trimestriel

    COMPTABILISATION:
    Débit 627 (Frais bancaires) : XX.XX€ TTC
    Crédit 512 (Banque LCL)      : XX.XX€

    NOTE IMPORTANTE:
    - Soeurise NON soumise à TVA
    - Enregistrement au TTC intégral (pas de compte 4456)
    """

    MONTANTS_TYPIQUES = [12.18, 15.00, 18.00, 20.00]  # Frais mensuels typiques

    def detecter(self, evenement: Dict) -> bool:
        """Détecte des frais bancaires"""
        libelle_norm = evenement.get('libelle_normalise', '').lower()
        montant = float(evenement.get('montant', 0))
        type_op = evenement.get('type_operation', '')

        # Vérifier le pattern
        patterns = ['frais', 'tenue de compte', 'gestion compte', 'cotisation carte', 'commission']
        match_libelle = any(pattern in libelle_norm for pattern in patterns)

        # Vérifier que le montant est raisonnable pour des frais
        match_montant = 0 < montant < 50  # Frais généralement < 50€

        # Vérifier que c'est un débit
        match_type = type_op == 'DEBIT'

        return match_libelle and match_montant and match_type

    def generer_proposition(self, evenement: Dict) -> Dict:
        """Génère la proposition d'écriture"""
        montant = float(evenement.get('montant', 0))
        date_op = evenement.get('date_operation')
        libelle = evenement.get('libelle', '')

        # Calculer niveau de confiance
        confiance = 0.95
        if any(abs(montant - m) < 0.50 for m in self.MONTANTS_TYPIQUES):
            confiance = 1.0  # 100% si montant reconnu

        return {
            'type_evenement': 'FRAIS_BANCAIRES',
            'description': f'Frais bancaires: {libelle[:50]}',
            'confiance': confiance,
            'ecritures': [
                {
                    'date_ecriture': date_op,
                    'libelle_ecriture': f'Frais bancaires - {libelle[:30]}',
                    'compte_debit': '627',
                    'compte_credit': '512',
                    'montant': montant,
                    'type_ecriture': 'FRAIS_BANCAIRES',
                    'notes': 'Montant TTC (pas de TVA déductible - Soeurise non soumise à TVA)'
                }
            ]
        }


class DetecteurHonorairesComptable(DetecteurBase):
    """
    Détecte les paiements d'honoraires d'expert-comptable

    PATTERN:
    - Libellé contient: COMPTABLE, EXPERT COMPTABLE, CABINET, HONORAIRES
    - Montant variable (généralement 100-500€)
    - Type: DEBIT
    - Fréquence: Trimestriel ou annuel

    COMPTABILISATION:
    Débit 622 (Honoraires expert-comptable) : XXX.XX€ TTC
    Crédit 512 (Banque LCL)                  : XXX.XX€

    NOTE IMPORTANTE:
    - Soeurise NON soumise à TVA
    - Enregistrement au TTC intégral (pas de compte 4456)

    EXEMPLES RÉELS 2024:
    - 26/03/2024: 213,60€ (Comptabilité 2023)
    - 28/06/2024: 273,60€ (Liasse fiscale 2023)
    - 29/08/2024: 273,60€ (Liasse fiscale 2024)
    """

    def detecter(self, evenement: Dict) -> bool:
        """Détecte des honoraires comptables"""
        libelle_norm = evenement.get('libelle_normalise', '').lower()
        montant = float(evenement.get('montant', 0))
        type_op = evenement.get('type_operation', '')

        # Vérifier le pattern
        patterns = [
            'comptable', 'expert comptable', 'cabinet comptable',
            'honoraires', 'comptabilite', 'liasse fiscale'
        ]
        match_libelle = any(pattern in libelle_norm for pattern in patterns)

        # Vérifier que le montant est raisonnable pour des honoraires
        match_montant = 50 < montant < 1000  # Entre 50€ et 1000€

        # Vérifier que c'est un débit
        match_type = type_op == 'DEBIT'

        return match_libelle and match_montant and match_type

    def generer_proposition(self, evenement: Dict) -> Dict:
        """Génère la proposition d'écriture"""
        montant = float(evenement.get('montant', 0))
        date_op = evenement.get('date_operation')
        libelle = evenement.get('libelle', '')

        # Déterminer la nature de la prestation
        libelle_lower = libelle.lower()
        if 'liasse' in libelle_lower or 'fiscale' in libelle_lower:
            nature = 'Liasse fiscale'
            confiance = 1.0
        elif 'comptabilite' in libelle_lower or 'tenue' in libelle_lower:
            nature = 'Tenue comptabilité'
            confiance = 1.0
        else:
            nature = 'Honoraires comptables'
            confiance = 0.95

        return {
            'type_evenement': 'HONORAIRES_COMPTABLE',
            'description': f'{nature}: {montant}€',
            'confiance': confiance,
            'ecritures': [
                {
                    'date_ecriture': date_op,
                    'libelle_ecriture': f'{nature}',
                    'compte_debit': '622',
                    'compte_credit': '512',
                    'montant': montant,
                    'type_ecriture': 'HONORAIRES_COMPTABLE',
                    'notes': 'Montant TTC (pas de TVA déductible - Soeurise non soumise à TVA)'
                }
            ]
        }


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY DE DÉTECTEURS
# ═══════════════════════════════════════════════════════════════════════════════

class FactoryDetecteurs:
    """
    Factory pour instancier les détecteurs par phase
    """

    @staticmethod
    def creer_detecteurs_phase1(session: Session) -> List[DetecteurBase]:
        """
        Crée les détecteurs de la Phase 1

        Args:
            session: Session SQLAlchemy

        Returns:
            Liste des détecteurs Phase 1
        """
        return [
            DetecteurAssurancePret(session),
            DetecteurFraisBancaires(session),
            DetecteurHonorairesComptable(session)
        ]

    @staticmethod
    def detecter_et_proposer(session: Session, evenement: Dict, phase: int = 1) -> Optional[Dict]:
        """
        Tente de détecter le type d'événement et génère une proposition

        Args:
            session: Session SQLAlchemy
            evenement: Dictionnaire de l'événement
            phase: Numéro de phase (1, 2, 3)

        Returns:
            Proposition d'écritures si détecté, None sinon
        """
        # Obtenir les détecteurs de la phase
        if phase == 1:
            detecteurs = FactoryDetecteurs.creer_detecteurs_phase1(session)
        else:
            # Phases 2 et 3 à implémenter
            return None

        # Tester chaque détecteur
        for detecteur in detecteurs:
            if detecteur.detecter(evenement):
                proposition = detecteur.generer_proposition(evenement)
                return proposition

        return None


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS UNITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def test_detecteurs():
    """Tests des détecteurs Phase 1"""
    print("=" * 80)
    print("TESTS DES DÉTECTEURS - Phase 1")
    print("=" * 80)
    print()

    # Mock session (pas besoin de DB pour ces tests)
    class MockSession:
        pass

    session = MockSession()

    # Test 1: Assurance emprunteur
    print("🧪 Test 1: Assurance emprunteur")
    evt_assurance = {
        'date_operation': '2024-01-15',
        'libelle': 'PRLV SEPA COVEA RISKS',
        'libelle_normalise': 'prlv sepa covea risks',
        'montant': 87.57,
        'type_operation': 'DEBIT'
    }

    detecteur_assurance = DetecteurAssurancePret(session)
    if detecteur_assurance.detecter(evt_assurance):
        print("✅ Assurance détectée")
        proposition = detecteur_assurance.generer_proposition(evt_assurance)
        print(f"   Type: {proposition['type_evenement']}")
        print(f"   Confiance: {proposition['confiance']}")
        print(f"   Écriture: 616 → 512: {proposition['ecritures'][0]['montant']}€")
    else:
        print("❌ Assurance non détectée")
    print()

    # Test 2: Frais bancaires
    print("🧪 Test 2: Frais bancaires")
    evt_frais = {
        'date_operation': '2024-01-31',
        'libelle': 'FRAIS TENUE DE COMPTE',
        'libelle_normalise': 'frais tenue de compte',
        'montant': 12.18,
        'type_operation': 'DEBIT'
    }

    detecteur_frais = DetecteurFraisBancaires(session)
    if detecteur_frais.detecter(evt_frais):
        print("✅ Frais bancaires détectés")
        proposition = detecteur_frais.generer_proposition(evt_frais)
        print(f"   Type: {proposition['type_evenement']}")
        print(f"   Confiance: {proposition['confiance']}")
        print(f"   Écriture: 627 → 512: {proposition['ecritures'][0]['montant']}€")
    else:
        print("❌ Frais bancaires non détectés")
    print()

    # Test 3: Honoraires comptable
    print("🧪 Test 3: Honoraires comptable")
    evt_comptable = {
        'date_operation': '2024-03-26',
        'libelle': 'VIR CABINET COMPTABLE LIASSE FISCALE 2023',
        'libelle_normalise': 'vir cabinet comptable liasse fiscale 2023',
        'montant': 273.60,
        'type_operation': 'DEBIT'
    }

    detecteur_comptable = DetecteurHonorairesComptable(session)
    if detecteur_comptable.detecter(evt_comptable):
        print("✅ Honoraires comptables détectés")
        proposition = detecteur_comptable.generer_proposition(evt_comptable)
        print(f"   Type: {proposition['type_evenement']}")
        print(f"   Confiance: {proposition['confiance']}")
        print(f"   Écriture: 622 → 512: {proposition['ecritures'][0]['montant']}€")
    else:
        print("❌ Honoraires comptables non détectés")
    print()

    # Test 4: Événement non reconnu
    print("🧪 Test 4: Événement non reconnu")
    evt_inconnu = {
        'date_operation': '2024-05-10',
        'libelle': 'CB RESTAURANT PARIS',
        'libelle_normalise': 'cb restaurant paris',
        'montant': 45.00,
        'type_operation': 'DEBIT'
    }

    proposition = FactoryDetecteurs.detecter_et_proposer(session, evt_inconnu, phase=1)
    if proposition:
        print(f"❌ Événement reconnu (ne devrait pas): {proposition['type_evenement']}")
    else:
        print("✅ Événement non reconnu (comportement attendu)")
    print()

    print("=" * 80)
    print("Tests terminés")
    print("=" * 80)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    test_detecteurs()
