"""
MODULE 2 VALIDATIONS V2 - TRAITEMENT DES VALIDATIONS
====================================================

Phases 5-9 du workflow:
5) Detection: cherche tag [_Head] VALIDE: dans emails
6) Extraction: parse JSON depuis bloc ```json...```
7) Validation: verifie integrite + token MD5
8) Insertion: cree EcritureComptable en BD
9) Tracking: met a jour EvenementComptable

Role: Valider les propositions avant insertion, avec audit trail complet
"""

import json
import hashlib
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

from models_module2 import (
    EvenementComptable, EcritureComptable, ExerciceComptable,
    PlanCompte, BalanceMensuelle
)
from module2_workflow_v2 import ParseurMarkdownJSON
from propositions_manager import PropositionsManager
from prets_manager import PretsManager


# DETECTEUR VALIDATIONS

class DetecteurValidations:
    """Detecte les validations dans les emails recus"""
    
    @staticmethod
    def detecter_validations_multiples(email: Dict) -> Dict:
        """
        Detecte TOUS les tokens de validation dans un email

        Cherche tous les tags: [_Head] VALIDE: TOKEN

        Returns:
            {
              "validation_detectee": bool,
              "tokens": List[str],
              "message": str
            }
        """

        body = email.get('body', '')
        subject = email.get('subject', '')

        # Chercher tag [_Head] VALIDE: suivi du token
        # Pattern: [_Head] VALIDE: HEAD-XXXXXXXX ou [_Head] VALIDE:HEAD-XXXXXXXX
        pattern = r'\[_Head\]\s*VALIDE:\s*([A-Z0-9-]+)'

        # Chercher TOUTES les occurrences dans le body
        matches = re.findall(pattern, body, re.IGNORECASE)

        # Ajouter celles du subject si pas dans body
        if not matches:
            matches = re.findall(pattern, subject, re.IGNORECASE)

        if not matches:
            return {
                "validation_detectee": False,
                "tokens": [],
                "message": "Tag [_Head] VALIDE: TOKEN non trouve"
            }

        # Normaliser tous les tokens trouvés
        tokens_normalises = []
        for token in matches:
            token = token.strip()

            # Déterminer le format du token :
            # - Si 32 caractères hexadécimaux → MD5 complet (format workflow v2)
            # - Sinon → Token court avec préfixe HEAD-

            if len(token) == 32 and all(c in '0123456789abcdefABCDEF' for c in token):
                # MD5 complet : normaliser en lowercase (format BD)
                token = token.lower()
            else:
                # Token court : ajouter HEAD- si nécessaire et mettre en majuscules
                token = token.upper()
                if not token.startswith('HEAD-'):
                    token = f"HEAD-{token}"

            tokens_normalises.append(token)

        return {
            "validation_detectee": True,
            "tokens": tokens_normalises,
            "message": f"{len(tokens_normalises)} validation(s) detectee(s): {', '.join(tokens_normalises)}"
        }

    @staticmethod
    def detecter_validation(email: Dict) -> Dict:
        """
        Detecte UNE SEULE validation dans un email (pour compatibilité)

        Cherche le tag: [_Head] VALIDE: TOKEN

        Returns:
            {
              "validation_detectee": bool,
              "token_email": str ou None,
              "message": str
            }
        """
        # Utiliser la méthode multi et retourner le premier token
        result = DetecteurValidations.detecter_validations_multiples(email)

        if not result['validation_detectee']:
            return {
                "validation_detectee": False,
                "token_email": None,
                "message": result['message']
            }

        # Retourner le premier token pour compatibilité
        return {
            "validation_detectee": True,
            "token_email": result['tokens'][0],
            "message": f"Validation detectee avec token: {result['tokens'][0]}"
        }
    
    @staticmethod
    def _extraire_json_attachments(email: Dict, parseur) -> Optional[Dict]:
        """
        Cherche et parse JSON depuis les fichiers .md en piece jointe
        
        Returns:
            Dict du JSON trouve, ou None si aucun JSON valide
        """
        attachments = email.get('attachments', [])
        
        for attachment in attachments:
            filename = attachment.get('filename', '').lower()
            
            # Chercher les fichiers .md ou .txt
            if not (filename.endswith('.md') or filename.endswith('.txt')):
                continue
            
            try:
                filepath = attachment.get('filepath')
                if not filepath:
                    continue
                
                # Lire le fichier avec encodage UTF-8
                with open(filepath, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                # Essayer d'extraire le JSON
                json_data = parseur.extraire_json(file_content)
                if json_data:
                    return json_data
            
            except Exception as e:
                continue
        
        return None


# VALIDATEUR INTEGRITE JSON

class ValidateurIntegriteJSON:
    """Valide l'integrite des propositions et detecte les tamperings"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def valider_propositions(self, propositions: List[Dict], token_email: str, token_stocke: str) -> Tuple[bool, str]:
        """
        Valide integrite des propositions

        Verifications:
        1. Token email match token stocké (detecte tampering)
        2. Tous les comptes existent
        3. Montants > 0
        4. Structure JSON valide
        5. Champ date_ecriture present pour écritures comptables

        Types reconnus:
        - PRET_IMMOBILIER: ['type', 'action', 'pret', 'nb_echeances']
        - Autres (BILAN, CLOTURE, EVENEMENT, RELEVE, etc): ['compte_debit', 'compte_credit', 'montant', 'numero_ecriture', 'date_ecriture']

        Args:
            propositions: Liste des propositions d'écritures
            token_email: Token reçu dans l'email de validation
            token_stocke: Token stocké en base de données

        Returns:
            (valide, message_erreur)
        """

        # 1. Vérifier que le token reçu correspond au token stocké
        # Normaliser les deux tokens pour comparaison (enlever préfixe HEAD- si présent)
        token_email_norm = token_email.strip().upper()
        token_stocke_norm = token_stocke.strip().upper()

        # Retirer HEAD- si présent pour la comparaison
        if token_email_norm.startswith("HEAD-"):
            token_email_norm = token_email_norm[5:]  # Enlever "HEAD-"
        if token_stocke_norm.startswith("HEAD-"):
            token_stocke_norm = token_stocke_norm[5:]  # Enlever "HEAD-"

        if token_email_norm != token_stocke_norm:
            return False, f"Token invalide (tampering detecte?) - Attendu: {token_stocke}, Reçu: {token_email}"

        # 2. Verifier chaque proposition
        for i, prop in enumerate(propositions):

            # Gérer différents types de propositions
            prop_type = prop.get('type', '')

            if prop_type == 'PRET_IMMOBILIER':
                # Validation spécifique pour les prêts immobiliers
                required_keys_pret = ['type', 'action', 'pret', 'nb_echeances']
                for key in required_keys_pret:
                    if key not in prop:
                        return False, f"Proposition {i} (PRET): cle '{key}' manquante"

                # Vérifier que pret contient les données minimales
                pret_data = prop.get('pret', {})
                if not isinstance(pret_data, dict):
                    return False, f"Proposition {i} (PRET): 'pret' doit etre un dict"

                # Vérifier nb_echeances
                try:
                    nb_ech = int(prop.get('nb_echeances', 0))
                    if nb_ech <= 0:
                        return False, f"Proposition {i} (PRET): nb_echeances doit etre > 0 (trouve: {nb_ech})"
                except (ValueError, TypeError):
                    return False, f"Proposition {i} (PRET): nb_echeances invalide"

            else:
                # Validation pour écritures comptables classiques (BILAN, CLOTURE, EVENEMENT_SIMPLE, RELEVE, etc)
                # Verifier structure
                required_keys = ['compte_debit', 'compte_credit', 'montant', 'numero_ecriture', 'date_ecriture']
                for key in required_keys:
                    if key not in prop:
                        prop_type_info = f" (type={prop_type})" if prop_type else " (type=UNDEFINED)"
                        return False, f"Proposition {i}{prop_type_info}: cle '{key}' manquante"

                # FIX: Verifier que date_ecriture n'est pas NULL
                date_ecriture = prop.get('date_ecriture')
                if date_ecriture is None:
                    return False, f"Proposition {i}: date_ecriture ne peut pas etre None"

                # FIX: Parser et valider la date si elle est une string
                if isinstance(date_ecriture, str):
                    try:
                        from datetime import datetime as dt
                        dt.strptime(date_ecriture, '%Y-%m-%d')
                    except ValueError:
                        return False, f"Proposition {i}: date_ecriture invalide (format attendu: YYYY-MM-DD, recu: {date_ecriture})"

                # Verifier montant
                try:
                    montant = Decimal(str(prop['montant']))
                    # Accepter montant >= 0 (les montants = 0 sont valides pour bilans d'ouverture)
                    if montant < 0:
                        return False, f"Proposition {i}: montant ne peut pas etre negatif (trouve: {montant})"
                except (ValueError, TypeError):
                    return False, f"Proposition {i}: montant invalide '{prop['montant']}'"

                # Verifier comptes existent
                compte_debit = self.session.query(PlanCompte).filter_by(
                    numero_compte=str(prop['compte_debit'])
                ).first()

                if not compte_debit:
                    return False, f"Proposition {i}: compte debit '{prop['compte_debit']}' n'existe pas"

                compte_credit = self.session.query(PlanCompte).filter_by(
                    numero_compte=str(prop['compte_credit'])
                ).first()

                if not compte_credit:
                    return False, f"Proposition {i}: compte credit '{prop['compte_credit']}' n'existe pas"
        
        return True, ""


# PROCESSEUR INSERTION

class ProcesseurInsertion:
    """Insere les propositions validees en tant que EcritureComptable"""

    def __init__(self, session: Session):
        self.session = session
        self.prets_manager = PretsManager(session)
    
    def inserer_propositions_simple(self, 
                                   propositions: List[Dict],
                                   evt_original_id: str,
                                   evt_validation_id: str,
                                   email_validation_from: str) -> Tuple[bool, str, List[int]]:
        """Insere propositions evenement simple"""
        
        return self._inserer_propositions_generiques(
            propositions, evt_original_id, evt_validation_id, email_validation_from
        )
    
    def inserer_propositions_init_bilan(self,
                                        propositions: List[Dict],
                                        evt_original_id: str,
                                        evt_validation_id: str,
                                        email_validation_from: str) -> Tuple[bool, str, List[int]]:
        """Insere propositions init bilan + cree ExerciceComptable 2023"""
        
        try:
            # D'abord creer l'exercice 2023 s'il n'existe pas
            exercice_2023 = self.session.query(ExerciceComptable).filter_by(annee=2023).first()
            
            if not exercice_2023:
                from datetime import date
                exercice_2023 = ExerciceComptable(
                    annee=2023,
                    date_debut=date(2023, 1, 1),
                    date_fin=date(2023, 12, 31),
                    statut='OUVERT',
                    description='Exercice comptable 2023'
                )
                self.session.add(exercice_2023)
                self.session.flush()
            
            # Puis inserer les propositions
            return self._inserer_propositions_generiques(
                propositions, evt_original_id, evt_validation_id, email_validation_from,
                exercice_id=exercice_2023.id
            )
        
        except Exception as e:
            self.session.rollback()
            return False, f"Erreur init bilan: {str(e)[:100]}", []
    
    def inserer_propositions_cloture(self,
                                     propositions: List[Dict],
                                     evt_original_id: str,
                                     evt_validation_id: str,
                                     email_validation_from: str) -> Tuple[bool, str, List[int]]:
        """Insere propositions cloture + cree ExerciceComptable 2024"""
        
        try:
            # Recuperer exercice 2023
            exercice_2023 = self.session.query(ExerciceComptable).filter_by(annee=2023).first()
            if not exercice_2023:
                return False, "Exercice 2023 non trouve pour cloture", []
            
            # Marquer 2023 comme CLOTURE
            exercice_2023.statut = 'CLOTURE'
            
            # Creer exercice 2024 s'il n'existe pas
            exercice_2024 = self.session.query(ExerciceComptable).filter_by(annee=2024).first()
            if not exercice_2024:
                from datetime import date
                exercice_2024 = ExerciceComptable(
                    annee=2024,
                    date_debut=date(2024, 1, 1),
                    date_fin=date(2024, 12, 31),
                    statut='OUVERT',
                    description='Exercice comptable 2024'
                )
                self.session.add(exercice_2024)
                self.session.flush()
            
            # Puis inserer les propositions (sur 2023)
            return self._inserer_propositions_generiques(
                propositions, evt_original_id, evt_validation_id, email_validation_from,
                exercice_id=exercice_2023.id
            )
        
        except Exception as e:
            self.session.rollback()
            return False, f"Erreur cloture: {str(e)[:100]}", []
    
    def _inserer_propositions_generiques(self,
                                        propositions: List[Dict],
                                        evt_original_id: str,
                                        evt_validation_id: str,
                                        email_validation_from: str,
                                        exercice_id: int = None) -> Tuple[bool, str, List[int]]:
        """Insere les propositions de facon generique"""
        
        try:
            # Si pas d'exercice specifie, utiliser 2024
            if not exercice_id:
                exercice_2024 = self.session.query(ExerciceComptable).filter_by(annee=2024).first()
                if not exercice_2024:
                    return False, "Exercice 2024 non trouve", []
                exercice_id = exercice_2024.id
            
            ecriture_ids = []

            # Récupérer la liste des événements comptables source pour obtenir les dates si nécessaire
            evenements_map = {}
            if evt_original_id and evt_original_id != 'UNKNOWN':
                result_evts = self.session.execute(
                    text("""
                        SELECT id, date_operation, libelle
                        FROM evenements_comptables
                        WHERE email_id = :email_id
                    """),
                    {'email_id': evt_original_id}
                )
                for evt in result_evts:
                    evenements_map[evt[0]] = {'date_operation': evt[1], 'libelle': evt[2]}

            for i, prop in enumerate(propositions):
                try:
                    # CORRECTION: Utiliser date_ecriture de la proposition (date opération réelle)
                    # au lieu de datetime.now() (date de traitement)
                    date_ecriture_prop = prop.get('date_ecriture')

                    if isinstance(date_ecriture_prop, str):
                        # Parser si string (format ISO: 2024-10-15)
                        from datetime import datetime as dt
                        date_ecriture_prop = dt.strptime(date_ecriture_prop, '%Y-%m-%d').date()
                    elif date_ecriture_prop is None:
                        # FIX: Fallback robuste - ne jamais passer None à la BD
                        date_ecriture_prop = datetime.now().date()

                    # FALLBACK: Si date_ecriture manquante, essayer de récupérer depuis événement source
                    if date_ecriture_prop is None:
                        # Essayer d'extraire l'ID événement depuis le numero_ecriture (format: EVT-XXX-YYY)
                        numero = prop.get('numero_ecriture', '')
                        if numero.startswith('EVT-'):
                            parts = numero.split('-')
                            if len(parts) >= 2:
                                try:
                                    evt_id = int(parts[1])
                                    if evt_id in evenements_map:
                                        date_ecriture_prop = evenements_map[evt_id]['date_operation']
                                except (ValueError, IndexError):
                                    pass

                        # Si toujours None, lever une erreur explicite
                        if date_ecriture_prop is None:
                            raise ValueError(f"Proposition {i}: date_ecriture manquante et impossible à récupérer depuis événement source")

                    # ✅ FIX: Déterminer l'exercice_id en fonction de la date d'écriture
                    # (important pour les cutoffs/extournes qui chevauchent plusieurs exercices)
                    annee_ecriture = date_ecriture_prop.year
                    exercice_pour_ecriture = self.session.query(ExerciceComptable).filter_by(annee=annee_ecriture).first()
                    if not exercice_pour_ecriture:
                        # Si l'exercice n'existe pas, utiliser l'exercice par défaut
                        exercice_id_final = exercice_id
                    else:
                        exercice_id_final = exercice_pour_ecriture.id

                    ecriture = EcritureComptable(
                        exercice_id=exercice_id_final,
                        numero_ecriture=prop['numero_ecriture'],
                        date_ecriture=date_ecriture_prop,  # ✅ Date opération réelle
                        libelle_ecriture=prop.get('libelle', ''),
                        type_ecriture=prop.get('type', 'AUTRE'),
                        compte_debit=str(prop['compte_debit']),
                        compte_credit=str(prop['compte_credit']),
                        montant=Decimal(str(prop['montant'])),
                        source_email_id=evt_original_id,
                        source_email_from=email_validation_from,
                        validee_at=datetime.now(),
                        notes=f"Validee par Ulrik via email {evt_validation_id}"
                    )
                    
                    self.session.add(ecriture)
                    self.session.flush()
                    ecriture_ids.append(ecriture.id)
                
                except IntegrityError as ie:
                    self.session.rollback()
                    return False, f"Erreur integrite DB: {str(ie)[:100]}", ecriture_ids
                except Exception as e:
                    self.session.rollback()
                    return False, f"Erreur insertion ecriture: {str(e)[:100]}", ecriture_ids
            
            self.session.commit()
            return True, f"{len(ecriture_ids)} ecritures inserees avec succes", ecriture_ids
        
        except Exception as e:
            self.session.rollback()
            return False, f"Erreur globale: {str(e)[:100]}", []

    def inserer_propositions_pret(self,
                                  propositions: List[Dict],
                                  evt_original_id: str,
                                  evt_validation_id: str,
                                  email_validation_from: str) -> Tuple[bool, str, List[int]]:
        """
        Insère prêt immobilier et ses échéances en BD

        Args:
            propositions: Liste avec 1 proposition PRET_IMMOBILIER
            evt_original_id: ID email original
            evt_validation_id: ID email validation
            email_validation_from: Email valideur

        Returns:
            (success, message, [pret_id])
        """
        try:
            # Vérifier qu'il y a au moins 1 proposition
            if len(propositions) < 1:
                return False, "Aucune proposition PRET trouvée", []

            # Traiter TOUS les prêts (support multi-PDFs)
            prets_inseres = []
            messages = []

            for i, prop in enumerate(propositions, 1):
                # Extraire les données (V7: échéances dans le dict, pas de fichier MD)
                filename = prop.get('filename', '')
                pret_data = prop.get('pret', {})
                nb_echeances = prop.get('nb_echeances', 0)
                echeances_data = prop.get('echeances', [])

                if not pret_data:
                    return False, f"Données prêt manquantes dans proposition {i}", []

                if not echeances_data:
                    return False, f"Échéances manquantes dans proposition {i}", []

                # Insérer le prêt et ses échéances via PretsManager
                success, message, pret_id = self.prets_manager.inserer_pret_et_echeances(
                    pret_data=pret_data,
                    echeances_data=echeances_data
                )

                if not success:
                    # Rollback si un prêt échoue
                    self.session.rollback()
                    return False, f"Erreur insertion prêt {i}: {message}", []

                prets_inseres.append(pret_id)
                messages.append(f"Prêt {pret_data.get('numero_pret', '?')} ({len(echeances_data)} échéances)")

            # Message récapitulatif
            message_final = f"{len(prets_inseres)} prêt(s) inséré(s): {', '.join(messages)}"
            return True, message_final, prets_inseres

        except Exception as e:
            self.session.rollback()
            return False, f"Erreur insertion prêts: {str(e)[:100]}", []

    def inserer_cloture_definitive(self,
                                   rapport_cloture: Dict,
                                   evt_original_id: str,
                                   evt_validation_id: str,
                                   email_validation_from: str) -> Tuple[bool, str, List[int]]:
        """
        Insère clôture définitive d'exercice

        Crée directement les écritures d'affectation et marque l'exercice comme CLOTURE.

        Args:
            rapport_cloture: Rapport de pre-cloture avec métadonnées
            evt_original_id: ID email original
            evt_validation_id: ID email validation
            email_validation_from: Email valideur

        Returns:
            (success, message, [ecriture_ids])
        """
        try:
            from datetime import date
            from models_module2 import ExerciceComptable, EcritureComptable

            # Extraire métadonnées du rapport
            annee = rapport_cloture.get('_annee')
            pv_ag = rapport_cloture.get('_pv_ag', 'PV AG non spécifié')

            if not annee:
                return False, "Année exercice manquante dans rapport", []

            # Extraire données financières du rapport
            # Le resultat_net est directement à la racine du rapport (pas dans fiscalite)
            resultat_net = rapport_cloture.get('resultat_net', 0)

            # Le déficit reportable peut être dans affectation ou fiscalite
            affectation = rapport_cloture.get('affectation', {})
            deficit_reportable = affectation.get('deficit_reportable_avant', 0)

            # Vérifier exercice N
            exercice_n = self.session.query(ExerciceComptable).filter_by(annee=annee).first()
            if not exercice_n:
                return False, f"Exercice {annee} non trouvé", []

            # Vérifier/créer exercice N+1
            exercice_n1 = self.session.query(ExerciceComptable).filter_by(annee=annee + 1).first()
            if not exercice_n1:
                exercice_n1 = ExerciceComptable(
                    annee=annee + 1,
                    date_debut=date(annee + 1, 1, 1),
                    date_fin=date(annee + 1, 12, 31),
                    statut='OUVERT',
                    description=f'Exercice comptable {annee + 1}'
                )
                self.session.add(exercice_n1)
                self.session.flush()

            # Créer écritures d'affectation sur exercice N+1
            ecriture_ids = []
            date_affectation = date(annee + 1, 1, 1)

            # ÉTAPE 1 : Reprise du résultat N dans le bilan d'ouverture N+1
            # Cette écriture intègre le résultat de l'exercice N au bilan d'ouverture N+1
            # via le compte 89 (contrepartie bilan ouverture)
            if resultat_net != 0:
                ecriture_reprise = EcritureComptable(
                    exercice_id=exercice_n1.id,
                    numero_ecriture=f'{annee + 1}-0101-OUV-RES',
                    date_ecriture=date_affectation,
                    libelle_ecriture=f'Bilan d\'ouverture {annee + 1} - Résultat exercice {annee}',
                    type_ecriture='BILAN_OUVERTURE',
                    compte_debit='89' if resultat_net > 0 else '120',
                    compte_credit='120' if resultat_net > 0 else '89',
                    montant=Decimal(str(abs(resultat_net))),
                    source_email_id=evt_original_id,
                    source_email_from=email_validation_from,
                    validee_at=datetime.now(),
                    notes=f'Reprise résultat {annee} dans bilan ouverture {annee + 1}'
                )
                self.session.add(ecriture_reprise)
                self.session.flush()
                ecriture_ids.append(ecriture_reprise.id)

            # ÉTAPE 2 : Affectation du résultat
            if resultat_net > 0 and deficit_reportable > 0:
                # Absorption du déficit (partielle ou totale)
                absorption = min(deficit_reportable, resultat_net)

                ecriture = EcritureComptable(
                    exercice_id=exercice_n1.id,
                    numero_ecriture=f'{annee + 1}-0101-AFF-001',
                    date_ecriture=date_affectation,
                    libelle_ecriture=f'Affectation résultat {annee} - Absorption déficit antérieur ({pv_ag})',
                    type_ecriture='AFFECTATION_RESULTAT',
                    compte_debit='120',
                    compte_credit='119',
                    montant=Decimal(str(absorption)),
                    source_email_id=evt_original_id,
                    source_email_from=email_validation_from,
                    validee_at=datetime.now(),
                    notes=f'Validée par {email_validation_from} via email {evt_validation_id}'
                )
                self.session.add(ecriture)
                self.session.flush()
                ecriture_ids.append(ecriture.id)

                # Si reste après absorption → report à nouveau créditeur
                reste = resultat_net - absorption
                if reste > 0:
                    ecriture2 = EcritureComptable(
                        exercice_id=exercice_n1.id,
                        numero_ecriture=f'{annee + 1}-0101-AFF-002',
                        date_ecriture=date_affectation,
                        libelle_ecriture=f'Affectation résultat {annee} - Report à nouveau excédent ({pv_ag})',
                        type_ecriture='AFFECTATION_RESULTAT',
                        compte_debit='120',
                        compte_credit='110',
                        montant=Decimal(str(reste)),
                        source_email_id=evt_original_id,
                        source_email_from=email_validation_from,
                        validee_at=datetime.now(),
                        notes=f'Validée par {email_validation_from} via email {evt_validation_id}'
                    )
                    self.session.add(ecriture2)
                    self.session.flush()
                    ecriture_ids.append(ecriture2.id)

            elif resultat_net > 0:
                # Bénéfice sans déficit → report à nouveau créditeur
                ecriture = EcritureComptable(
                    exercice_id=exercice_n1.id,
                    numero_ecriture=f'{annee + 1}-0101-AFF-001',
                    date_ecriture=date_affectation,
                    libelle_ecriture=f'Affectation résultat {annee} - Report à nouveau ({pv_ag})',
                    type_ecriture='AFFECTATION_RESULTAT',
                    compte_debit='120',
                    compte_credit='110',
                    montant=Decimal(str(resultat_net)),
                    source_email_id=evt_original_id,
                    source_email_from=email_validation_from,
                    validee_at=datetime.now(),
                    notes=f'Validée par {email_validation_from} via email {evt_validation_id}'
                )
                self.session.add(ecriture)
                self.session.flush()
                ecriture_ids.append(ecriture.id)

            elif resultat_net < 0:
                # Perte → report à nouveau débiteur
                ecriture = EcritureComptable(
                    exercice_id=exercice_n1.id,
                    numero_ecriture=f'{annee + 1}-0101-AFF-001',
                    date_ecriture=date_affectation,
                    libelle_ecriture=f'Affectation résultat {annee} - Report à nouveau (perte) ({pv_ag})',
                    type_ecriture='AFFECTATION_RESULTAT',
                    compte_debit='119',
                    compte_credit='129',
                    montant=Decimal(str(abs(resultat_net))),
                    source_email_id=evt_original_id,
                    source_email_from=email_validation_from,
                    validee_at=datetime.now(),
                    notes=f'Validée par {email_validation_from} via email {evt_validation_id}'
                )
                self.session.add(ecriture)
                self.session.flush()
                ecriture_ids.append(ecriture.id)

            # Marquer exercice N comme CLOTURE
            if exercice_n.statut != 'CLOTURE':
                exercice_n.statut = 'CLOTURE'

            self.session.commit()

            message = f"Exercice {annee} clôturé - {len(ecriture_ids)} écriture(s) d'affectation créée(s)"
            return True, message, ecriture_ids

        except Exception as e:
            self.session.rollback()
            return False, f"Erreur clôture: {str(e)[:200]}", []


# ORCHESTRATOR VALIDATIONS

class OrchestratorValidations:
    """Orchestre le workflow complet de validation (phases 5-9)"""

    def __init__(self, session: Session):
        self.session = session
        self.detecteur = DetecteurValidations()
        self.validateur = ValidateurIntegriteJSON(session)
        self.processeur = ProcesseurInsertion(session)
        self.propositions_manager = PropositionsManager(session)

    def nettoyer_evenements_lies(self, token: str) -> int:
        """
        Supprime les événements comptables liés à une proposition validée

        Args:
            token: Token de la proposition

        Returns:
            Nombre d'événements supprimés
        """
        # Récupérer les propositions JSON depuis la table
        result = self.session.execute(text("""
            SELECT propositions_json
            FROM propositions_en_attente
            WHERE token = :token
        """), {'token': token})

        row = result.fetchone()
        if not row or not row[0]:
            return 0

        propositions = row[0]  # C'est déjà un dict/list grâce à JSONB

        # Extraire les IDs d'événements (format EVT-123) depuis le JSON
        ids_a_supprimer = []

        # Les propositions peuvent être une liste ou un dict avec une clé 'propositions'
        if isinstance(propositions, dict):
            propositions_list = propositions.get('propositions', [propositions])
        else:
            propositions_list = propositions

        for prop in propositions_list:
            if isinstance(prop, dict):
                numero = prop.get('numero_ecriture', '')
                if numero and numero.startswith('EVT-'):
                    try:
                        evt_id = int(numero.split('-')[1])
                        ids_a_supprimer.append(evt_id)
                    except (IndexError, ValueError):
                        pass

        if not ids_a_supprimer:
            return 0

        # Supprimer les événements
        placeholders = ','.join(str(id) for id in ids_a_supprimer)
        result = self.session.execute(text(f"""
            DELETE FROM evenements_comptables
            WHERE id IN ({placeholders})
        """))

        nb_supprimes = result.rowcount
        self.session.commit()

        return nb_supprimes
    
    def traiter_email_validation(self, email: Dict) -> Dict:
        """
        Traite un email de validation (phase 5-9)
        
        Workflow:
        5) Detecte tag [_Head] VALIDE:
        6) Extrait JSON du bloc ```json...```
        7) Valide integrite + token MD5
        8) Insere les EcritureComptable
        9) Update EvenementComptable
        
        Returns:
            {
              "validation_detectee": bool,
              "statut": "OK" | "ERREUR",
              "message": str,
              "ecritures_creees": int,
              "type_evenement": str
            }
        """
        
        # PHASE 5: Detection du token
        result_detection = self.detecteur.detecter_validation(email)

        if not result_detection['validation_detectee']:
            return {
                "validation_detectee": False,
                "statut": "IGNORE",
                "message": result_detection['message'],
                "ecritures_creees": 0,
                "type_evenement": None
            }

        # Récupérer le token
        token_email = result_detection['token_email']

        # PHASE 6: Récupération des propositions depuis la BD via le token
        proposition_data = self.propositions_manager.recuperer_proposition(token_email)

        if not proposition_data:
            return {
                "validation_detectee": True,
                "statut": "ERREUR",
                "message": f"Token {token_email} non trouvé en base de données",
                "ecritures_creees": 0,
                "type_evenement": None
            }

        # Vérifier que la proposition est en attente
        if proposition_data['statut'] != 'EN_ATTENTE':
            return {
                "validation_detectee": True,
                "statut": "ERREUR",
                "message": f"Proposition {token_email} déjà traitée (statut: {proposition_data['statut']})",
                "ecritures_creees": 0,
                "type_evenement": proposition_data['type_evenement']
            }

        # Extraction des données de la proposition
        propositions = proposition_data['propositions']
        type_evenement = proposition_data['type_evenement']
        token_stocke = proposition_data['token']

        # Pour CLOTURE_EXERCICE, propositions est une liste avec 1 élément (le rapport complet)
        # Il faut extraire le premier élément pour obtenir le dict rapport
        if type_evenement == 'CLOTURE_EXERCICE':
            if isinstance(propositions, list) and len(propositions) > 0:
                rapport_cloture = propositions[0]  # Extraire le rapport du wrapper liste
            else:
                rapport_cloture = propositions  # Fallback si pas une liste
        else:
            rapport_cloture = None

        if not propositions:
            return {
                "validation_detectee": True,
                "statut": "ERREUR",
                "message": "Liste 'propositions' vide dans JSON",
                "ecritures_creees": 0,
                "type_evenement": type_evenement
            }

        # PHASE 7: Validation integrite (skip pour CLOTURE_EXERCICE qui a une structure différente)
        if type_evenement == 'CLOTURE_EXERCICE':
            # Pour clôture, on valide juste le token
            token_email_norm = token_email.strip().upper()
            token_stocke_norm = token_stocke.strip().upper()

            # Retirer HEAD- si présent
            if token_email_norm.startswith("HEAD-"):
                token_email_norm = token_email_norm[5:]
            if token_stocke_norm.startswith("HEAD-"):
                token_stocke_norm = token_stocke_norm[5:]

            if token_email_norm != token_stocke_norm:
                valide = False
                msg_erreur = f"Token invalide - Attendu: {token_stocke}, Reçu: {token_email}"
            else:
                valide = True
                msg_erreur = ""
        else:
            # Validation standard pour les autres types
            valide, msg_erreur = self.validateur.valider_propositions(propositions, token_email, token_stocke)

        if not valide:
            # Creer EvenementComptable rejete
            # Parser la date email ou utiliser datetime.now() si absente
            from email.utils import parsedate_to_datetime
            email_date = None
            if email.get('date'):
                try:
                    email_date = parsedate_to_datetime(email.get('date'))
                except:
                    email_date = datetime.now()
            else:
                email_date = datetime.now()

            evt_rejet = EvenementComptable(
                email_id=email.get('email_id'),
                email_from=email.get('from'),
                email_date=email_date,
                email_subject=email.get('subject', ''),
                email_body=email.get('body', '')[:1000],
                type_evenement=type_evenement,
                est_comptable=True,
                statut='REJETE',
                message_erreur=msg_erreur
            )
            self.session.add(evt_rejet)
            self.session.commit()

            return {
                "validation_detectee": True,
                "statut": "ERREUR",
                "message": f"Validation echouee: {msg_erreur}",
                "ecritures_creees": 0,
                "type_evenement": type_evenement
            }
        
        # PHASE 8-9: Insertion + Update

        # Utiliser les données de la proposition (pas besoin de chercher EvenementComptable)
        # Dans l'architecture V2, on ne crée pas d'EvenementComptable lors de la génération
        # On a déjà toutes les infos dans proposition_data

        email_original_id = proposition_data.get('email_id') or 'UNKNOWN'

        # Choisir la fonction d'insertion selon le type
        if type_evenement == 'EVENEMENT_SIMPLE' or type_evenement == 'RELEVE_BANCAIRE':
            succes, msg, ids = self.processeur.inserer_propositions_simple(
                propositions, email_original_id, email.get('email_id'), email.get('from')
            )
        elif type_evenement == 'INIT_BILAN_2023':
            succes, msg, ids = self.processeur.inserer_propositions_init_bilan(
                propositions, email_original_id, email.get('email_id'), email.get('from')
            )
        elif type_evenement == 'CLOTURE_EXERCICE':
            # Traitement spécial pour clôture (structure différente, exécute cloture_exercice.py)
            succes, msg, ids = self.processeur.inserer_cloture_definitive(
                rapport_cloture, email_original_id, email.get('email_id'), email.get('from')
            )
        elif type_evenement == 'PRET_IMMOBILIER':
            succes, msg, ids = self.processeur.inserer_propositions_pret(
                propositions, email_original_id, email.get('email_id'), email.get('from')
            )
        elif type_evenement in ['CUTOFF', 'CUTOFF_HONORAIRES', 'CUTOFF_PRODUIT_A_RECEVOIR_SCPI']:
            # Cutoffs utilisent la même logique que les événements simples
            succes, msg, ids = self.processeur.inserer_propositions_simple(
                propositions, email_original_id, email.get('email_id'), email.get('from')
            )
        else:
            succes, msg, ids = False, f"Type evenement inconnu: {type_evenement}", []
        
        if not succes:
            # Marquer la proposition comme ERREUR (échec technique d'insertion)
            try:
                self.session.execute(text("""
                    UPDATE propositions_en_attente
                    SET statut = 'ERREUR',
                        notes = :erreur
                    WHERE token = :token
                """), {'token': token_email, 'erreur': f"Erreur insertion: {msg}"})
                self.session.commit()
                print(f"⚠️  Proposition {token_email} marquée ERREUR: {msg[:100]}")
            except Exception as e:
                print(f"⚠️  Erreur lors du marquage ERREUR: {e}")
                self.session.rollback()

            return {
                "validation_detectee": True,
                "statut": "ERREUR",
                "message": f"Erreur insertion: {msg}",
                "ecritures_creees": 0,
                "type_evenement": type_evenement
            }

        # Message spécifique selon le type
        if type_evenement == 'PRET_IMMOBILIER':
            item_label = "prêt(s)"
            notes_msg = f"{len(ids)} prêt(s) inséré(s)"
        else:
            item_label = "écriture(s)"
            notes_msg = f"{len(ids)} écriture(s) insérée(s)"

        # Marquer la proposition comme validée dans la table propositions_en_attente
        self.propositions_manager.valider_proposition(
            token=token_email,
            validee_par=email.get('from'),
            notes=f"Validée via email le {datetime.now()}, {notes_msg}"
        )

        # Nettoyer les événements temporaires liés à cette proposition
        nb_evt_supprimes = self.nettoyer_evenements_lies(token_email)
        if nb_evt_supprimes > 0:
            print(f"🗑️  {nb_evt_supprimes} événements temporaires nettoyés")

        self.session.commit()

        return {
            "validation_detectee": True,
            "statut": "OK",
            "message": f"OK: {len(ids)} {item_label} insérée(s) avec succès",
            "ecritures_creees": len(ids),
            "type_evenement": type_evenement
        }

    def traiter_email_validations_multiples(self, email: Dict) -> List[Dict]:
        """
        Traite TOUTES les validations dans un email (support multi-tokens)

        Returns:
            Liste de résultats (un par token détecté)
        """
        # Détecter tous les tokens dans l'email
        result_detection = self.detecteur.detecter_validations_multiples(email)

        if not result_detection['validation_detectee']:
            return [{
                "validation_detectee": False,
                "statut": "IGNORE",
                "message": result_detection['message'],
                "ecritures_creees": 0,
                "type_evenement": None
            }]

        # Traiter chaque token individuellement
        resultats = []
        tokens = result_detection['tokens']

        print(f"🔍 {len(tokens)} validation(s) détectée(s) dans l'email")

        for token in tokens:
            print(f"\n🔄 Traitement de {token}...")

            # Créer un email temporaire avec un seul token pour la compatibilité
            email_single = email.copy()
            email_single['body'] = f"[_Head] VALIDE: {token}"

            # Traiter ce token
            result = self.traiter_email_validation(email_single)
            resultats.append(result)

            # Afficher le résultat
            if result['statut'] == 'OK':
                type_evt = result.get('type_evenement', '')
                nb_items = result['ecritures_creees']

                if type_evt == 'PRET_IMMOBILIER':
                    print(f"   ✅ {nb_items} prêt(s) inséré(s)")
                else:
                    print(f"   ✅ {nb_items} écriture(s) insérée(s)")
            else:
                print(f"   ❌ {result['message']}")

        print(f"\n📊 Résumé: {len(resultats)} validation(s) traitée(s)")
        return resultats


if __name__ == "__main__":
    print("OK: Module 2 Validations V2 charge et pret")
