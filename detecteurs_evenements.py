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
    - Libellé contient: COVEA RISKS, CACI, ASSURANCE PRET, COTISATION ASSURANCE
    - Montant: 87.57€ total (Emma 66.58€ + Pauline 20.99€) OU paiements séparés
    - Type: DEBIT
    - Fréquence: Mensuel (vers le 15 du mois)

    COMPTABILISATION:
    Débit 616 (Assurances emprunteur) : XX.XX€
    Crédit 512 (Banque LCL)             : XX.XX€

    NOTE IMPORTANTE:
    - Assurance UNIQUEMENT pour le prêt AMORTISSABLE (LCL - BRM0911AH)
    - PAS d'assurance pour le prêt IN FINE (INVESTIMUR - BRLZE11AQ)
    - Les paiements peuvent être groupés (87.57€) OU séparés (Emma ~66€, Pauline ~21€)
    """

    MONTANT_TOTAL = 87.57
    MONTANT_EMMA_MIN = 60.0
    MONTANT_EMMA_MAX = 75.0
    MONTANT_PAULINE_MIN = 15.0
    MONTANT_PAULINE_MAX = 25.0

    def detecter(self, evenement: Dict) -> bool:
        """Détecte une assurance emprunteur (groupée ou séparée)"""
        libelle_norm = evenement.get('libelle_normalise', '').lower()
        montant = float(evenement.get('montant', 0))
        type_op = evenement.get('type_operation', '')
        type_evt = evenement.get('type_evenement', '')

        # Vérifier le type détecté (prioritaire car déjà validé par gestionnaire)
        if type_evt == 'ASSURANCE_PRET':
            return True

        # Vérifier le pattern (fallback)
        patterns = ['covea', 'caci', 'assurance pret', 'cotisation assurance', 'prelevement assurance', 'garantie emprunteur']
        match_libelle = any(pattern in libelle_norm for pattern in patterns)

        # Vérifier le montant (accepter groupé OU séparé)
        match_montant = (
            abs(montant - self.MONTANT_TOTAL) <= 0.20 or  # Montant total ±20 centimes
            (self.MONTANT_EMMA_MIN <= montant <= self.MONTANT_EMMA_MAX) or  # Emma seule
            (self.MONTANT_PAULINE_MIN <= montant <= self.MONTANT_PAULINE_MAX)  # Pauline seule
        )

        # Vérifier que c'est un débit
        match_type = type_op == 'DEBIT'

        return match_libelle and match_montant and match_type

    def generer_proposition(self, evenement: Dict) -> Dict:
        """Génère la proposition d'écriture"""
        montant = float(evenement.get('montant', 0))
        date_op = evenement.get('date_operation')

        # Calculer niveau de confiance
        confiance = 1.0  # 100% si le pattern est reconnu
        if abs(montant - self.MONTANT_TOTAL) > 0.01:
            confiance = 0.9  # Légère variation de montant (paiement séparé ou variation mineure)

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


class DetecteurRemboursementPret(DetecteurBase):
    """
    Détecte les remboursements de prêt immobilier

    PATTERN:
    - Libellé contient: PRET IMMOBILIER, ECH, DOSSIER NO
    - Montant: 1166.59€ (prêt LCL amortissable) OU 258.33€ (prêt INVESTIMUR in fine)
    - Type: DEBIT
    - Fréquence: Mensuel (15 du mois)

    COMPTABILISATION:
    Débit 661 (Charges d'intérêts)  : INTERETS€
    Débit 164 (Emprunts)            : CAPITAL€
    Crédit 512 (Banque LCL)         : TOTAL€

    NOTE IMPORTANTE:
    - Lookup dans echeances_prets par date pour obtenir ventilation exacte
    - Si échéance trouvée: génère 2 écritures (intérêts + capital)
    - Si non trouvée: génère 1 écriture temporaire (à corriger manuellement)
    """

    MONTANT_ATTENDU = 1166.59
    TOLERANCE = 0.10

    def detecter(self, evenement: Dict) -> bool:
        """Détecte un remboursement de prêt"""
        libelle_norm = evenement.get('libelle_normalise', '').lower()
        montant = float(evenement.get('montant', 0))
        type_op = evenement.get('type_operation', '')
        type_evt = evenement.get('type_evenement', '')

        # Vérifier le pattern
        patterns = ['pret immobilier', 'echeance pret', 'dossier no']
        match_libelle = any(pattern in libelle_norm for pattern in patterns)

        # Vérifier le type détecté
        match_type = type_evt == 'REMBOURSEMENT_PRET'

        # Vérifier que c'est un débit
        match_debit = type_op == 'DEBIT'

        return (match_libelle or match_type) and match_debit

    def generer_proposition(self, evenement: Dict) -> Dict:
        """
        Génère la proposition d'écriture avec décomposition intérêts/capital

        Recherche l'échéance correspondante dans echeances_prets pour ventiler
        automatiquement entre compte 661 (intérêts) et 164 (capital).
        """
        montant = float(evenement.get('montant', 0))
        date_op = evenement.get('date_operation')

        # Rechercher l'échéance correspondante dans la table echeances_prets
        echeance = None
        try:
            result = self.session.execute(
                text("""
                    SELECT ep.montant_interet, ep.montant_capital, ep.montant_total,
                           pi.numero_pret, pi.banque, ep.numero_echeance
                    FROM echeances_prets ep
                    JOIN prets_immobiliers pi ON ep.pret_id = pi.id
                    WHERE ep.date_echeance = :date_op
                      AND ABS(ep.montant_total - :montant) < 0.10
                    LIMIT 1
                """),
                {'date_op': date_op, 'montant': montant}
            )
            row = result.fetchone()
            if row:
                echeance = {
                    'montant_interet': float(row[0]),
                    'montant_capital': float(row[1]),
                    'montant_total': float(row[2]),
                    'numero_pret': row[3],
                    'banque': row[4],
                    'numero_echeance': row[5]
                }
        except Exception as e:
            print(f"⚠️  Erreur lookup échéance prêt: {e}")
            echeance = None

        # CAS 1: Échéance trouvée → Décomposition intérêts/capital
        if echeance:
            return {
                'type_evenement': 'REMBOURSEMENT_PRET',
                'description': f'Échéance #{echeance["numero_echeance"]} prêt {echeance["banque"]} ({echeance["numero_pret"][:10]}...)',
                'confiance': 1.0,  # Confiance maximale car données vérifiées
                'ecritures': [
                    {
                        'date_ecriture': date_op,
                        'libelle_ecriture': f'Intérêts échéance #{echeance["numero_echeance"]} prêt {echeance["banque"]}',
                        'compte_debit': '661',
                        'compte_credit': '512',
                        'montant': echeance['montant_interet'],
                        'type_ecriture': 'INTERET_PRET',
                        'notes': f'Prêt {echeance["numero_pret"]} - Échéance {echeance["numero_echeance"]}'
                    },
                    {
                        'date_ecriture': date_op,
                        'libelle_ecriture': f'Remboursement capital échéance #{echeance["numero_echeance"]} prêt {echeance["banque"]}',
                        'compte_debit': '164',
                        'compte_credit': '512',
                        'montant': echeance['montant_capital'],
                        'type_ecriture': 'REMBOURSEMENT_CAPITAL',
                        'notes': f'Prêt {echeance["numero_pret"]} - Échéance {echeance["numero_echeance"]}'
                    }
                ]
            }

        # CAS 2: Échéance NON trouvée → Écriture temporaire (fallback)
        else:
            return {
                'type_evenement': 'REMBOURSEMENT_PRET',
                'description': f'Remboursement prêt (échéance non trouvée dans BD)',
                'confiance': 0.5,  # Confiance réduite car décomposition impossible
                'ecritures': [
                    {
                        'date_ecriture': date_op,
                        'libelle_ecriture': f'Échéance prêt (TEMPORAIRE - échéance non trouvée)',
                        'compte_debit': '164',
                        'compte_credit': '512',
                        'montant': montant,
                        'type_ecriture': 'REMBOURSEMENT_PRET',
                        'notes': f'ATTENTION: Échéance non trouvée dans echeances_prets pour date {date_op} montant {montant}€. Nécessite correction manuelle pour ventiler intérêts (661) / capital (164).'
                    }
                ]
            }


class DetecteurRevenuSCPI(DetecteurBase):
    """
    Détecte les revenus SCPI (Société Civile de Placement Immobilier)

    PATTERN:
    - Libellé contient: SCPI, EPARGNE PIERRE
    - Montant variable (revenus trimestriels)
    - Type: DEBIT (virement sortant vers placement)
    - Fréquence: Trimestriel

    COMPTABILISATION:
    Débit 273 (Titres immobilisés - SCPI) : XX.XX€
    Crédit 512 (Banque LCL)                : XX.XX€

    NOTE:
    - Les achats de parts SCPI sont des immobilisations financières
    - Les revenus futurs seront en 761 (Produits de participations)
    """

    def detecter(self, evenement: Dict) -> bool:
        """Détecte un achat/revenu SCPI"""
        libelle_norm = evenement.get('libelle_normalise', '').lower()
        type_evt = evenement.get('type_evenement', '')

        # Vérifier le pattern
        patterns = ['scpi', 'epargne pierre']
        match_libelle = any(pattern in libelle_norm for pattern in patterns)

        # Vérifier le type détecté
        match_type = type_evt == 'REVENU_SCPI'

        return match_libelle or match_type

    def generer_proposition(self, evenement: Dict) -> Dict:
        """Génère la proposition d'écriture"""
        montant = float(evenement.get('montant', 0))
        date_op = evenement.get('date_operation')

        return {
            'type_evenement': 'REVENU_SCPI',
            'description': f'Achat parts SCPI Épargne Pierre',
            'confiance': 0.9,
            'ecritures': [
                {
                    'date_ecriture': date_op,
                    'libelle_ecriture': f'Acquisition parts SCPI Épargne Pierre',
                    'compte_debit': '273',
                    'compte_credit': '512',
                    'montant': montant,
                    'type_ecriture': 'ACHAT_SCPI',
                    'notes': 'Immobilisation financière - Parts SCPI'
                }
            ]
        }


class DetecteurAchatETF(DetecteurBase):
    """
    Détecte les achats d'ETF (Exchange Traded Funds)

    PATTERN:
    - Libellé contient: AM MSCI, ETF, ACHAT
    - Montant variable (achats d'ETF)
    - Type: DEBIT
    - Fréquence: Occasionnel

    COMPTABILISATION:
    Débit 273 (Titres immobilisés - ETF) : XX.XX€
    Crédit 512 (Banque LCL)               : XX.XX€

    EXEMPLE RÉEL:
    - 24/07/2024: "100 AM.MSCI WLD V ETF ACHAT 2407 17,260000 EUR" - 1735.53€

    NOTE:
    - Les ETF sont des valeurs mobilières de placement
    - Compte 273 (immobilisation) car stratégie buy & hold long terme
    """

    def detecter(self, evenement: Dict) -> bool:
        """Détecte un achat d'ETF"""
        libelle_norm = evenement.get('libelle_normalise', '').lower()
        type_evt = evenement.get('type_evenement', '')

        # Vérifier le type détecté (prioritaire car déjà validé par gestionnaire)
        if type_evt == 'ACHAT_ETF':
            return True

        # Vérifier le pattern (fallback)
        patterns = ['am msci', 'etf', 'msci world']
        match_libelle = any(pattern in libelle_norm for pattern in patterns)

        return match_libelle

    def generer_proposition(self, evenement: Dict) -> Dict:
        """Génère la proposition d'écriture"""
        montant = float(evenement.get('montant', 0))
        date_op = evenement.get('date_operation')
        libelle = evenement.get('libelle', '')

        # Extraire le nombre de parts si possible
        import re
        match = re.search(r'^(\d+)\s+(?:AM[.\s])?MSCI', libelle, re.IGNORECASE)
        nb_parts = match.group(1) if match else '?'

        # Extraire le nom de l'ETF
        if 'msci' in libelle.lower():
            nom_etf = 'MSCI World'
        else:
            nom_etf = 'ETF'

        return {
            'type_evenement': 'ACHAT_ETF',
            'description': f'Achat {nb_parts} parts ETF {nom_etf}',
            'confiance': 0.9,
            'ecritures': [
                {
                    'date_ecriture': date_op,
                    'libelle_ecriture': f'Acquisition {nb_parts} parts ETF {nom_etf}',
                    'compte_debit': '273',
                    'compte_credit': '512',
                    'montant': montant,
                    'type_ecriture': 'ACHAT_ETF',
                    'notes': f'Titres immobilisés - {nb_parts} parts ETF {nom_etf}'
                }
            ]
        }


class DetecteurAchatAmazon(DetecteurBase):
    """
    Détecte les achats d'actions Amazon

    PATTERN:
    - Libellé contient: AMAZON COM ACHAT
    - Montant variable (achats d'actions)
    - Type: DEBIT
    - Fréquence: Occasionnel

    COMPTABILISATION:
    Débit 273 (Titres immobilisés - Actions) : XX.XX€
    Crédit 512 (Banque LCL)                   : XX.XX€

    NOTE:
    - Les actions Amazon sont des valeurs mobilières de placement
    - Compte 273 ou 503 selon stratégie (immobilisation vs placement)
    - Ici traité comme immobilisation (détention long terme)
    """

    def detecter(self, evenement: Dict) -> bool:
        """Détecte un achat Amazon"""
        libelle_norm = evenement.get('libelle_normalise', '').lower()
        type_evt = evenement.get('type_evenement', '')

        # Vérifier le type détecté (prioritaire)
        if type_evt == 'ACHAT_AMAZON':
            return True

        # Vérifier le pattern (fallback)
        patterns = ['amazon com achat', 'amazon achat']
        match_libelle = any(pattern in libelle_norm for pattern in patterns)

        return match_libelle

    def generer_proposition(self, evenement: Dict) -> Dict:
        """Génère la proposition d'écriture"""
        montant = float(evenement.get('montant', 0))
        date_op = evenement.get('date_operation')
        libelle = evenement.get('libelle', '')

        # Extraire le nombre d'actions si possible
        import re
        match = re.search(r'^(\d+)\s+AMAZON', libelle)
        nb_actions = match.group(1) if match else '?'

        return {
            'type_evenement': 'ACHAT_AMAZON',
            'description': f'Achat {nb_actions} actions Amazon',
            'confiance': 0.9,
            'ecritures': [
                {
                    'date_ecriture': date_op,
                    'libelle_ecriture': f'Acquisition {nb_actions} actions Amazon.com Inc.',
                    'compte_debit': '273',
                    'compte_credit': '512',
                    'montant': montant,
                    'type_ecriture': 'ACHAT_ACTIONS',
                    'notes': f'Titres immobilisés - {nb_actions} actions Amazon'
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
        type_evt = evenement.get('type_evenement', '')

        # Si le type est déjà détecté, on l'accepte directement
        if type_evt == 'FRAIS_BANCAIRES':
            return True

        # Sinon, vérification par patterns (fallback)
        libelle_norm = evenement.get('libelle_normalise', '').lower()
        montant = float(evenement.get('montant', 0))
        type_op = evenement.get('type_operation', '')

        patterns = ['frais', 'tenue de compte', 'gestion compte', 'cotisation carte', 'commission', 'abon', 'abonnement']
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
    - Libellé contient: CRP, COMPTABLE, COMPTABILIT, EXPERT COMPTABLE, CABINET, HONORAIRES
    - Montant variable (généralement 100-600€)
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
    - Libellé typique: "PRLV SEPA CRP Comptabilit Conseil LIBELLE:20240XXX"
    """

    def detecter(self, evenement: Dict) -> bool:
        """Détecte des honoraires comptables"""
        type_evt = evenement.get('type_evenement', '')

        # Si le type est déjà détecté, on l'accepte directement
        if type_evt == 'HONORAIRES_COMPTABLE':
            return True

        # Sinon, vérification par patterns (fallback)
        libelle_norm = evenement.get('libelle_normalise', '').lower()
        montant = float(evenement.get('montant', 0))
        type_op = evenement.get('type_operation', '')
        type_evt = evenement.get('type_evenement', '')

        # Vérifier le type détecté (prioritaire car déjà validé par gestionnaire)
        if type_evt == 'HONORAIRES_COMPTABLE':
            return True

        # Vérifier le pattern (fallback)
        patterns = [
            'crp',  # CRP Comptabilit Conseil
            'comptable', 'comptabilit',  # Formes complète et tronquée
            'expert comptable', 'cabinet comptable',
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
            DetecteurRemboursementPret(session),
            DetecteurRevenuSCPI(session),
            DetecteurAchatETF(session),  # NOUVEAU: Détecteur ETF (MSCI World, etc.)
            DetecteurAchatAmazon(session),
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
