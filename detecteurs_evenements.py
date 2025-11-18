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

# Import rapprocheur cutoff
from rapprocheur_cutoff import RapprocheurCutoff


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
    Débit 164 (Emprunts établissements crédit) : CAPITAL€
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

        FIX 18/11/2025: Utilisation compte 164 au lieu de 161
        - Compte 161 = Emprunts obligataires (incorrect pour SCI)
        - Compte 164 = Emprunts établissements de crédit (correct)
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


class DetecteurDistributionSCPI(DetecteurBase):
    """
    Détecte les DISTRIBUTIONS SCPI (revenus trimestriels)

    PATTERN:
    - Libellé contient: SCPI + DISTRIBUTION (ou DISTRIB)
    - Type: CREDIT (entrée d'argent)
    - Montants observés: 6 346,56€ | 7 356,24€ | 601,00€ (capital)
    - Fréquence: Trimestriel

    COMPTABILISATION:
    Distribution classique (revenus):
      Débit 512 (Banque)                    : XX.XX€
      Crédit 761 (Produits participations)  : XX.XX€

    Distribution de capital (remboursement partiel):
      Débit 512 (Banque)          : XX.XX€
      Crédit 106 (Réserves)       : XX.XX€ (ou 280 - Réduction valeur titres)

    FIX 12/11/2025:
    - AVANT: Tout comptabilisé en 273 (Actif) même les revenus
    - APRÈS: Distinction CREDIT (revenus 761) vs DEBIT (achats 273)
    """

    def detecter(self, evenement: Dict) -> bool:
        """Détecte une distribution SCPI (revenus ou capital)"""
        libelle_norm = evenement.get('libelle_normalise', '').lower()
        type_op = evenement.get('type_operation', '')
        type_evt = evenement.get('type_evenement', '')

        # Vérifier le pattern SCPI + DISTRIBUTION + CREDIT
        match_libelle = ('scpi' in libelle_norm or 'epargne pierre' in libelle_norm) and 'distri' in libelle_norm
        match_type = type_op == 'CREDIT'

        # Vérifier le type détecté (si déjà marqué)
        match_evt = type_evt == 'REVENU_SCPI'

        return (match_libelle and match_type) or match_evt

    def generer_proposition(self, evenement: Dict) -> Dict:
        """
        Génère la proposition d'écriture selon le type de distribution

        WORKFLOW CUT-OFF (depuis 18/11/2025):
        -------------------------------------
        1. Vérifier si créance 4181 existe (produit à recevoir)
        2. Si OUI → Générer écriture de SOLDAGE (Débit 512 / Crédit 4181)
        3. Si NON → Générer écriture de PRODUIT (Débit 512 / Crédit 761)

        Cela évite le doublon:
        - Sans rapprochement: Créance 4181 + Produit 761 = revenus comptés 2 fois
        - Avec rapprochement: Créance 4181 soldée = revenus comptés 1 fois
        """
        montant = float(evenement.get('montant', 0))
        date_op = evenement.get('date_operation')
        libelle = evenement.get('libelle', '').lower()

        # Détecter si distribution de capital (mots-clés spécifiques)
        est_capital = 'capital' in libelle or 'numero 01' in libelle or montant < 1000

        if est_capital:
            # Distribution de capital (remboursement partiel / réserves)
            return {
                'type_evenement': 'DISTRIBUTION_CAPITAL_SCPI',
                'description': f'Distribution capital SCPI Épargne Pierre : {montant}€',
                'confiance': 0.9,
                'ecritures': [
                    {
                        'date_ecriture': date_op,
                        'libelle_ecriture': 'Distribution capital SCPI Épargne Pierre',
                        'compte_debit': '512',
                        'compte_credit': '106',  # Réserves (ou 280 si réduction valeur titres)
                        'montant': montant,
                        'type_ecriture': 'DISTRIBUTION_CAPITAL_SCPI',
                        'notes': 'Remboursement partiel capital ou prélèvement sur réserves'
                    }
                ]
            }
        else:
            # Distribution classique (revenus trimestriels)
            # ============================================

            # ÉTAPE 1: Tenter rapprochement avec créance existante
            # -----------------------------------------------------
            rapprocheur = RapprocheurCutoff(self.session)
            proposition_rapprochement = rapprocheur.rapprocher_encaissement(
                montant=montant,
                date_operation=date_op,
                libelle="SCPI Épargne Pierre",
                tolerance_montant=2.0,
                tolerance_pourcentage=0.02
            )

            # ÉTAPE 2: Si créance trouvée → Retourner proposition de soldage
            # ---------------------------------------------------------------
            if proposition_rapprochement:
                # Créance trouvée: On solde au lieu de créer nouveau produit
                return proposition_rapprochement

            # ÉTAPE 3: Sinon → Créer nouveau produit (comportement normal)
            # ------------------------------------------------------------
            # Aucune créance trouvée: Comptabilisation normale en produit
            return {
                'type_evenement': 'REVENU_SCPI',
                'description': f'Revenus SCPI Épargne Pierre (trimestre) : {montant}€',
                'confiance': 0.95,
                'ecritures': [
                    {
                        'date_ecriture': date_op,
                        'libelle_ecriture': 'Revenus trimestriels SCPI Épargne Pierre',
                        'compte_debit': '512',
                        'compte_credit': '761',  # Produits de participations
                        'montant': montant,
                        'type_ecriture': 'REVENU_SCPI',
                        'notes': 'Revenus SCPI (2404 parts détenues)'
                    }
                ]
            }


class DetecteurAchatSCPI(DetecteurBase):
    """
    Détecte les ACHATS de parts SCPI (immobilisations)

    PATTERN:
    - Libellé contient: SCPI + (ACHAT ou SOUSCRIPTION)
    - Type: DEBIT (sortie d'argent)
    - Montants variables

    COMPTABILISATION:
    Débit 273 (Titres immobilisés - SCPI) : XX.XX€
    Crédit 512 (Banque LCL)                : XX.XX€

    NOTE:
    - Les parts SCPI sont des immobilisations financières
    - Détention long terme (pas de trading)
    """

    def detecter(self, evenement: Dict) -> bool:
        """Détecte un achat de parts SCPI"""
        libelle_norm = evenement.get('libelle_normalise', '').lower()
        type_op = evenement.get('type_operation', '')

        # Vérifier le pattern SCPI + ACHAT/SOUSCRIPTION + DEBIT
        match_libelle = (
            ('scpi' in libelle_norm or 'epargne pierre' in libelle_norm) and
            ('achat' in libelle_norm or 'souscription' in libelle_norm)
        )
        match_type = type_op == 'DEBIT'

        return match_libelle and match_type

    def generer_proposition(self, evenement: Dict) -> Dict:
        """Génère la proposition d'écriture"""
        montant = float(evenement.get('montant', 0))
        date_op = evenement.get('date_operation')

        return {
            'type_evenement': 'ACHAT_SCPI',
            'description': f'Acquisition parts SCPI Épargne Pierre : {montant}€',
            'confiance': 0.95,
            'ecritures': [
                {
                    'date_ecriture': date_op,
                    'libelle_ecriture': 'Acquisition parts SCPI Épargne Pierre',
                    'compte_debit': '273',
                    'compte_credit': '512',
                    'montant': montant,
                    'type_ecriture': 'ACHAT_SCPI',
                    'notes': 'Titres de participation immobilisés - Détention long terme'
                }
            ]
        }


class DetecteurAnnonceProduitARecevoir(DetecteurBase):
    """
    Détecte les ANNONCES de revenus SCPI à recevoir (cut-off fin d'année)

    CONTEXTE:
    - En fin d'année, les revenus SCPI du 4T sont acquis mais non encore versés
    - Le versement intervient généralement en janvier N+1
    - Principe comptabilité d'engagement: produits comptabilisés dans exercice où acquis

    PATTERN EMAIL:
    - Objet contient: SCPI + (DISTRIBUTION ou REVENUS) + T4/4T/4ème trimestre/Q4
    - Corps contient: Montant + Date versement future
    - Émetteur: SCPI identifiable (domaine ou nom)
    - Mots-clés intention: "prévisionnelle", "prévue", "sera versée", "interviendra"
    - OU Bulletin annuel avec ligne "versement prévu" pour T4

    DATE DÉTECTION:
    - Priorité 1: Email reçu entre 15/12 et 31/12
    - Priorité 2: Email mentionne "T4" + "prévue"/"versement futur"

    COMPTABILISATION:
    Date écriture: 31/12/N (toujours fin exercice)
      Débit 4181 (Produits à recevoir)     : XX.XX€
      Crédit 761 (Revenus SCPI)            : XX.XX€

    EXEMPLE:
    Email du 20/12/2024:
      "Distribution T4 2024 de 7 356,00 € sera versée le 29/01/2025"

    Génère écriture au 31/12/2024:
      Débit 4181 : 7 356,00 €
      Crédit 761 : 7 356,00 €

    NOTE IMPORTANTE:
    - Cette écriture sera SOLDÉE en janvier lors de l'encaissement réel
    - Le DetecteurDistributionSCPI devra utiliser le rapprocheur_cutoff
      pour détecter qu'une créance existe et la solder (Débit 512 / Crédit 4181)
      au lieu de créer un nouveau produit (Débit 512 / Crédit 761)

    Date création: 18/11/2025
    """

    def detecter(self, evenement: Dict) -> bool:
        """
        Détecte une annonce de produit à recevoir SCPI

        Args:
            evenement: Dictionnaire contenant:
                - type_source: 'EMAIL' (requis)
                - objet_email: Objet de l'email
                - corps_email: Corps de l'email
                - date_reception: Date réception email
                - libelle / libelle_normalise: Pour compatibilité

        Returns:
            True si annonce de produit à recevoir détectée
        """
        # Vérifier que c'est un email (pas un relevé bancaire)
        type_source = evenement.get('type_source', '').upper()
        if type_source != 'EMAIL':
            return False

        # Récupérer les champs email
        objet = evenement.get('objet_email', '').lower()
        corps = evenement.get('corps_email', '').lower()
        date_reception_str = evenement.get('date_reception', evenement.get('date_operation', ''))

        # Combiner objet + corps pour analyse
        texte_complet = f"{objet} {corps}"

        # Vérifier pattern SCPI
        match_scpi = 'scpi' in texte_complet or 'epargne pierre' in texte_complet
        if not match_scpi:
            return False

        # Vérifier pattern T4 / 4ème trimestre / Q4
        match_t4 = any(pattern in texte_complet for pattern in [
            't4', '4t', '4ème trimestre', '4eme trimestre',
            'quatrième trimestre', 'quatrieme trimestre', 'q4'
        ])
        if not match_t4:
            return False

        # Vérifier pattern distribution/revenus
        match_distribution = any(pattern in texte_complet for pattern in [
            'distribution', 'distrib', 'revenus', 'versement'
        ])
        if not match_distribution:
            return False

        # Vérifier montant présent (pattern monétaire)
        import re
        pattern_montant = r'(\d{1,3}(?:\s?\d{3})*[,\.]\d{2})\s*€'
        match_montant = re.search(pattern_montant, texte_complet)
        if not match_montant:
            return False

        # Vérifier intention future (fort indicateur)
        match_futur = any(mot in texte_complet for mot in [
            'prévisionnelle', 'previsionnelle', 'prévue', 'prevue',
            'sera versée', 'sera verse', 'interviendra',
            'versement prévu', 'versement prevu', 'à venir', 'a venir'
        ])

        # Vérifier période de fin d'année (fort indicateur)
        match_periode = False
        if date_reception_str:
            try:
                if isinstance(date_reception_str, str):
                    date_reception = datetime.strptime(date_reception_str, '%Y-%m-%d').date()
                else:
                    date_reception = date_reception_str

                # Email reçu entre 15/12 et 31/12
                match_periode = (date_reception.month == 12 and date_reception.day >= 15)
            except:
                pass

        # Vérifier anti-patterns (ne PAS traiter)
        anti_pattern = any(mot in texte_complet for mot in [
            'versement effectué', 'versement effectue',
            'a été versée', 'a ete verse'
        ])

        if anti_pattern:
            return False

        # Décision finale: Futur OU Période fin d'année
        return match_futur or match_periode

    def generer_proposition(self, evenement: Dict) -> Dict:
        """
        Génère la proposition d'écriture de produit à recevoir

        Returns:
            Proposition avec écriture au 31/12/N
        """
        # Extraire le montant
        import re
        corps = evenement.get('corps_email', '')
        objet = evenement.get('objet_email', '')
        texte_complet = f"{objet} {corps}"

        pattern_montant = r'(\d{1,3}(?:\s?\d{3})*)[,\.](\d{2})\s*€'
        match = re.search(pattern_montant, texte_complet)

        if match:
            montant_str = match.group(1).replace(' ', '') + '.' + match.group(2)
            montant = float(montant_str)
        else:
            montant = 0.0

        # Extraire l'année (chercher 20XX dans le texte)
        match_annee = re.search(r'20(\d{2})', texte_complet)
        if match_annee:
            annee = int(match_annee.group(0))
        else:
            # Par défaut: année de réception email
            date_reception_str = evenement.get('date_reception', evenement.get('date_operation', ''))
            try:
                if isinstance(date_reception_str, str):
                    date_reception = datetime.strptime(date_reception_str, '%Y-%m-%d').date()
                else:
                    date_reception = date_reception_str
                annee = date_reception.year
            except:
                annee = datetime.now().year

        # Date d'écriture: TOUJOURS 31/12/N (fin exercice)
        date_ecriture = f"{annee}-12-31"

        # Extraire date versement prévue (si mentionnée)
        date_versement_prevue = None
        pattern_date = r'(\d{1,2})[/-](\d{1,2})[/-](20\d{2})'
        match_date = re.search(pattern_date, texte_complet)
        if match_date:
            jour, mois, annee_versement = match_date.groups()
            date_versement_prevue = f"{annee_versement}-{mois.zfill(2)}-{jour.zfill(2)}"

        return {
            'type_evenement': 'ANNONCE_PRODUIT_A_RECEVOIR_SCPI',
            'description': f'Revenus SCPI T4 {annee} à recevoir (annoncés) : {montant}€',
            'confiance': 0.90,
            'ecritures': [
                {
                    'date_ecriture': date_ecriture,
                    'libelle_ecriture': f'SCPI Épargne Pierre - Revenus T4 {annee} à recevoir',
                    'compte_debit': '4181',
                    'compte_credit': '761',
                    'montant': montant,
                    'type_ecriture': 'PRODUIT_A_RECEVOIR_SCPI',
                    'notes': f'Cut-off fin exercice {annee} - Versement prévu {date_versement_prevue or "janvier " + str(annee + 1)}'
                }
            ],
            'metadata': {
                'email_date': evenement.get('date_reception', evenement.get('date_operation', '')),
                'scpi_name': 'Épargne Pierre',
                'trimestre': 'T4',
                'annee': annee,
                'date_versement_prevue': date_versement_prevue
            }
        }


class DetecteurApportAssocie(DetecteurBase):
    """
    Détecte les apports en compte courant des associés (Ulrik Bergsten)

    PATTERN:
    - Libellé contient: APPORT + (COMPTE COURANT ou CC) + BERGSTEN
    - Type: CREDIT (entrée d'argent)
    - Montants variables (500€ à 5 000€)

    COMPTABILISATION:
    Débit 512 (Banque)                      : XX.XX€
    Crédit 455 (Compte courant Ulrik)       : XX.XX€

    NOTE:
    - Apports remboursables à tout moment
    - Pas d'intérêts sauf convention contraire
    - Constitue une dette de la SCI envers l'associé

    FIX 12/11/2025:
    - AVANT: Détecté mais pas de générateur de propositions
    - APRÈS: Détecteur complet avec proposition 512/455
    """

    def detecter(self, evenement: Dict) -> bool:
        """Détecte un apport en compte courant d'associé"""
        libelle_norm = evenement.get('libelle_normalise', '').lower()
        type_op = evenement.get('type_operation', '')
        type_evt = evenement.get('type_evenement', '')

        # Vérifier le type détecté (prioritaire)
        if type_evt == 'APPORT_ASSOCIE':
            return True

        # Vérifier le pattern APPORT + BERGSTEN + CREDIT
        match_apport = 'apport' in libelle_norm
        match_bergsten = 'bergsten' in libelle_norm
        match_cc = 'compte courant' in libelle_norm or ' cc ' in libelle_norm
        match_type = type_op == 'CREDIT'

        return (match_apport and match_bergsten and match_type) or (match_apport and match_cc and match_type)

    def generer_proposition(self, evenement: Dict) -> Dict:
        """Génère la proposition d'écriture"""
        montant = float(evenement.get('montant', 0))
        date_op = evenement.get('date_operation')

        return {
            'type_evenement': 'APPORT_ASSOCIE',
            'description': f'Apport compte courant Ulrik Bergsten : {montant}€',
            'confiance': 0.95,
            'ecritures': [
                {
                    'date_ecriture': date_op,
                    'libelle_ecriture': 'Apport en compte courant - Ulrik Bergsten',
                    'compte_debit': '512',  # Banque
                    'compte_credit': '455',  # Compte courant associé
                    'montant': montant,
                    'type_ecriture': 'APPORT_ASSOCIE',
                    'notes': 'Apport remboursable sans intérêts (sauf convention contraire)'
                }
            ]
        }


class DetecteurAchatValeursMobilieres(DetecteurBase):
    """
    Détecteur unifié pour tous les achats de valeurs mobilières
    (ETF, Actions, Obligations, etc.)

    PATTERN:
    - Libellé contient: AM MSCI, ETF, AMAZON, ACHAT + nom ticker/ISIN
    - Type: DEBIT (sortie d'argent)
    - Montants variables

    TYPES SUPPORTÉS:
    - ETF (MSCI World, etc.)
    - Actions (Amazon, etc.)
    - Autres valeurs mobilières

    COMPTABILISATION:
    Débit 273 (Titres immobilisés - VM) : XX.XX€
    Crédit 512 (Banque LCL)              : XX.XX€

    NOTE:
    - Compte 273 (immobilisation) car stratégie buy & hold long terme
    - Si trading actif: utiliser compte 503 (VMP)

    FIX 12/11/2025:
    - AVANT: 2 détecteurs séparés (ETF + Amazon)
    - APRÈS: Détecteur unifié ACHAT_VM
    """

    def detecter(self, evenement: Dict) -> bool:
        """Détecte un achat de valeurs mobilières"""
        libelle_norm = evenement.get('libelle_normalise', '').lower()
        type_evt = evenement.get('type_evenement', '')
        type_op = evenement.get('type_operation', '')

        # Vérifier les types détectés (prioritaire)
        if type_evt in ['ACHAT_ETF', 'ACHAT_AMAZON', 'ACHAT_VALEURS_MOBILIERES']:
            return True

        # Vérifier les patterns (fallback)
        patterns_vm = [
            'am msci', 'etf', 'msci world',  # ETF
            'amazon com achat', 'amazon achat',  # Amazon
            'degiro', 'interactive brokers',  # Courtiers
            'achat' and ('action' in libelle_norm or 'titre' in libelle_norm)
        ]
        match_libelle = any(pattern in libelle_norm for pattern in patterns_vm if isinstance(pattern, str))

        # Vérifier que c'est un DEBIT
        match_type = type_op == 'DEBIT'

        return match_libelle and match_type

    def generer_proposition(self, evenement: Dict) -> Dict:
        """Génère la proposition d'écriture"""
        montant = float(evenement.get('montant', 0))
        date_op = evenement.get('date_operation')
        libelle = evenement.get('libelle', '')

        # Identifier le type de valeur mobilière
        import re
        libelle_lower = libelle.lower()

        if 'msci' in libelle_lower or 'etf' in libelle_lower:
            # ETF
            match_parts = re.search(r'^(\d+)\s+(?:AM[.\s])?MSCI', libelle, re.IGNORECASE)
            nb_titres = match_parts.group(1) if match_parts else '?'
            type_vm = 'ETF'
            nom_vm = 'MSCI World' if 'msci' in libelle_lower else 'ETF'

        elif 'amazon' in libelle_lower:
            # Actions Amazon
            match_actions = re.search(r'^(\d+)\s+AMAZON', libelle, re.IGNORECASE)
            nb_titres = match_actions.group(1) if match_actions else '?'
            type_vm = 'Actions'
            nom_vm = 'Amazon.com Inc.'

        else:
            # Autres valeurs mobilières
            nb_titres = '?'
            type_vm = 'Valeurs Mobilières'
            nom_vm = 'Titres'

        return {
            'type_evenement': 'ACHAT_VM',
            'description': f'Achat {nb_titres} {type_vm} {nom_vm}',
            'confiance': 0.9,
            'ecritures': [
                {
                    'date_ecriture': date_op,
                    'libelle_ecriture': f'Acquisition {nb_titres} {type_vm} {nom_vm}',
                    'compte_debit': '273',  # Titres immobilisés (ou 503 si VMP)
                    'compte_credit': '512',
                    'montant': montant,
                    'type_ecriture': 'ACHAT_VM',
                    'notes': f'Titres immobilisés - {nb_titres} {type_vm} {nom_vm}'
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

        # ⚠️ REMISES LCL : Inverser l'écriture (diminution charges, pas augmentation)
        libelle_norm = libelle.upper()
        patterns_remises = ['REMISE', 'VOTRE REM', 'REM LCL', 'REMBT']
        est_remise = any(pattern in libelle_norm for pattern in patterns_remises)

        if est_remise:
            # REMISE : Débit 512 (Banque) / Crédit 627 (Frais) → Diminue les charges
            compte_debit = '512'
            compte_credit = '627'
            description = f'Remise frais bancaires: {libelle[:50]}'
            libelle_ecriture = f'Remise frais bancaires - {libelle[:30]}'
            notes = 'Remise LCL - Diminution des charges (Débit 512 / Crédit 627)'
        else:
            # FRAIS NORMAUX : Débit 627 (Frais) / Crédit 512 (Banque) → Augmente les charges
            compte_debit = '627'
            compte_credit = '512'
            description = f'Frais bancaires: {libelle[:50]}'
            libelle_ecriture = f'Frais bancaires - {libelle[:30]}'
            notes = 'Montant TTC (pas de TVA déductible - Soeurise non soumise à TVA)'

        return {
            'type_evenement': 'FRAIS_BANCAIRES',
            'description': description,
            'confiance': confiance,
            'ecritures': [
                {
                    'date_ecriture': date_op,
                    'libelle_ecriture': libelle_ecriture,
                    'compte_debit': compte_debit,
                    'compte_credit': compte_credit,
                    'montant': montant,
                    'type_ecriture': 'FRAIS_BANCAIRES',
                    'notes': notes
                }
            ]
        }


class DetecteurFraisAdministratifs(DetecteurBase):
    """
    Détecte les frais administratifs (LEI, certificats, immatriculations)

    PATTERN:
    - Libellé contient: LEI, LEGAL ENTITY IDENTIFIER, REGIE RECETTES INSEE, CERTIFICAT, IMMATRICULATION
    - Montant variable (généralement 50-100€)
    - Type: DEBIT

    COMPTABILISATION:
    Débit 627 (Frais bancaires/administratifs) : XX.XX€ TTC
    Crédit 512 (Banque LCL)                    : XX.XX€

    NOTE IMPORTANTE:
    - Soeurise NON soumise à TVA
    - Enregistrement au TTC intégral (pas de compte 4456)
    """

    def detecter(self, evenement: Dict) -> bool:
        """Détecte des frais administratifs"""
        type_evt = evenement.get('type_evenement', '')

        # Si le type est déjà détecté, on l'accepte directement
        if type_evt == 'FRAIS_ADMINISTRATIFS':
            return True

        # Sinon, vérification par patterns (fallback)
        libelle_norm = evenement.get('libelle_normalise', '').lower()
        type_op = evenement.get('type_operation', '')

        patterns = ['lei', 'legal entity identifier', 'regie recettes insee', 'certificat', 'immatriculation']
        match_libelle = any(pattern in libelle_norm for pattern in patterns)

        # Vérifier que c'est un débit
        match_type = type_op == 'DEBIT'

        return match_libelle and match_type

    def generer_proposition(self, evenement: Dict) -> Dict:
        """Génère la proposition d'écriture"""
        montant = float(evenement.get('montant', 0))
        date_op = evenement.get('date_operation')
        libelle = evenement.get('libelle', '')

        return {
            'type_evenement': 'FRAIS_ADMINISTRATIFS',
            'description': f'Frais administratifs: {libelle[:50]}',
            'confiance': 0.95,
            'ecritures': [
                {
                    'date_ecriture': date_op,
                    'libelle_ecriture': f'Frais administratifs - {libelle[:30]}',
                    'compte_debit': '627',
                    'compte_credit': '512',
                    'montant': montant,
                    'type_ecriture': 'FRAIS_ADMINISTRATIFS',
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
                    'compte_debit': '6226',  # Honoraires
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

        ORDRE IMPORTANT:
        - Détecteurs les plus spécifiques en premier
        - Détecteurs génériques en dernier
        - Permet d'éviter qu'un détecteur générique capture un événement spécifique

        FIX 12/11/2025:
        - DetecteurRevenuSCPI → Scindé en DetecteurDistributionSCPI + DetecteurAchatSCPI
        - DetecteurAchatETF + DetecteurAchatAmazon → Fusionnés en DetecteurAchatValeursMobilieres
        - Ajout DetecteurApportAssocie
        """
        return [
            # Détecteurs de charges récurrentes (priorité haute - patterns spécifiques)
            DetecteurAssurancePret(session),
            DetecteurRemboursementPret(session),  # Lookup table echeances_prets
            DetecteurFraisBancaires(session),
            DetecteurFraisAdministratifs(session),  # LEI, certificats, etc.
            DetecteurHonorairesComptable(session),

            # Détecteurs d'investissements (priorité moyenne - patterns multiples)
            DetecteurAnnonceProduitARecevoir(session),  # EMAIL: Annonce revenus T4 à recevoir (cut-off)
            DetecteurDistributionSCPI(session),  # CRÉDIT: Revenus 761
            DetecteurAchatSCPI(session),  # DÉBIT: Achats 273
            DetecteurAchatValeursMobilieres(session),  # ETF + Amazon + autres VM

            # Détecteurs de trésorerie (priorité basse - patterns génériques)
            DetecteurApportAssocie(session),  # CRÉDIT: Apports 455
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
