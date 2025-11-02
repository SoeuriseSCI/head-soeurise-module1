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

from models_module2 import (
    EvenementComptable, EcritureComptable, ExerciceComptable,
    PlanCompte, BalanceMensuelle
)
from module2_workflow_v2 import ParseurMarkdownJSON
from propositions_manager import PropositionsManager


# DETECTEUR VALIDATIONS

class DetecteurValidations:
    """Detecte les validations dans les emails recus"""
    
    @staticmethod
    def detecter_validation(email: Dict) -> Dict:
        """
        Detecte si l'email contient une validation avec TOKEN

        Cherche le tag: [_Head] VALIDE: TOKEN

        Returns:
            {
              "validation_detectee": bool,
              "token_email": str ou None,
              "message": str
            }
        """

        body = email.get('body', '')
        subject = email.get('subject', '')

        # Chercher tag [_Head] VALIDE: suivi du token
        # Pattern: [_Head] VALIDE: HEAD-XXXXXXXX ou [_Head] VALIDE:HEAD-XXXXXXXX
        pattern = r'\[_Head\]\s*VALIDE:\s*([A-Z0-9-]+)'

        # Chercher dans le body
        match = re.search(pattern, body, re.IGNORECASE)
        if not match:
            # Chercher dans le subject
            match = re.search(pattern, subject, re.IGNORECASE)

        if not match:
            return {
                "validation_detectee": False,
                "token_email": None,
                "message": "Tag [_Head] VALIDE: TOKEN non trouve"
            }

        # Token trouvé
        token_email = match.group(1).strip()

        # Déterminer le format du token :
        # - Si 32 caractères hexadécimaux → MD5 complet (format workflow v2)
        # - Sinon → Token court avec préfixe HEAD-

        if len(token_email) == 32 and all(c in '0123456789abcdefABCDEF' for c in token_email):
            # MD5 complet : normaliser en lowercase (format BD)
            token_email = token_email.lower()
        else:
            # Token court : ajouter HEAD- si nécessaire et mettre en majuscules
            token_email = token_email.upper()
            if not token_email.startswith('HEAD-'):
                token_email = f"HEAD-{token_email}"

        return {
            "validation_detectee": True,
            "token_email": token_email,
            "message": f"Validation detectee avec token: {token_email}"
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
    
    def valider_propositions(self, propositions: List[Dict], token_email: str) -> Tuple[bool, str]:
        """
        Valide integrite des propositions
        
        Verifications:
        1. Token MD5 match (detecte tampering)
        2. Tous les comptes existent
        3. Montants > 0
        4. Structure JSON valide
        
        Returns:
            (valide, message_erreur)
        """
        
        # 1. Verifier token MD5
        token_calculated = hashlib.md5(
            json.dumps(propositions, sort_keys=True).encode()
        ).hexdigest()
        
        if token_calculated != token_email:
            return False, f"Token MD5 invalide (tampering detecte?) - Attendu: {token_email}, Calcule: {token_calculated}"
        
        # 2. Verifier chaque proposition
        for i, prop in enumerate(propositions):
            
            # Verifier structure
            required_keys = ['compte_debit', 'compte_credit', 'montant', 'numero_ecriture']
            for key in required_keys:
                if key not in prop:
                    return False, f"Proposition {i}: cle '{key}' manquante"
            
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
            
            for prop in propositions:
                try:
                    ecriture = EcritureComptable(
                        exercice_id=exercice_id,
                        numero_ecriture=prop['numero_ecriture'],
                        date_ecriture=datetime.now().date(),
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


# ORCHESTRATOR VALIDATIONS

class OrchestratorValidations:
    """Orchestre le workflow complet de validation (phases 5-9)"""
    
    def __init__(self, session: Session):
        self.session = session
        self.detecteur = DetecteurValidations()
        self.validateur = ValidateurIntegriteJSON(session)
        self.processeur = ProcesseurInsertion(session)
        self.propositions_manager = PropositionsManager(session)
    
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
        
        if not propositions:
            return {
                "validation_detectee": True,
                "statut": "ERREUR",
                "message": "Liste 'propositions' vide dans JSON",
                "ecritures_creees": 0,
                "type_evenement": type_evenement
            }
        
        # PHASE 7: Validation integrite
        valide, msg_erreur = self.validateur.valider_propositions(propositions, token_email)

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
        if type_evenement == 'EVENEMENT_SIMPLE':
            succes, msg, ids = self.processeur.inserer_propositions_simple(
                propositions, email_original_id, email.get('email_id'), email.get('from')
            )
        elif type_evenement == 'INIT_BILAN_2023':
            succes, msg, ids = self.processeur.inserer_propositions_init_bilan(
                propositions, email_original_id, email.get('email_id'), email.get('from')
            )
        elif type_evenement == 'CLOTURE_EXERCICE':
            succes, msg, ids = self.processeur.inserer_propositions_cloture(
                propositions, email_original_id, email.get('email_id'), email.get('from')
            )
        else:
            succes, msg, ids = False, f"Type evenement inconnu: {type_evenement}", []
        
        if not succes:
            return {
                "validation_detectee": True,
                "statut": "ERREUR",
                "message": f"Erreur insertion: {msg}",
                "ecritures_creees": 0,
                "type_evenement": type_evenement
            }

        # Marquer la proposition comme validée dans la table propositions_en_attente
        self.propositions_manager.valider_proposition(
            token=token_email,
            validee_par=email.get('from'),
            notes=f"Validée via email le {datetime.now()}, {len(ids)} écritures insérées"
        )

        self.session.commit()
        
        return {
            "validation_detectee": True,
            "statut": "OK",
            "message": f"OK: {len(ids)} ecritures inserees avec succes",
            "ecritures_creees": len(ids),
            "type_evenement": type_evenement
        }


if __name__ == "__main__":
    print("OK: Module 2 Validations V2 charge et pret")
