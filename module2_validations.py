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


# DETECTEUR VALIDATIONS

class DetecteurValidations:
    """Detecte les validations dans les emails recus"""
    
    @staticmethod
    def detecter_validation(email: Dict) -> Dict:
        """
        Detecte si l'email contient une validation
        
        Cherche le tag: [_Head] VALIDE:
        Et extrait le JSON soit du body, soit des attachments .md
        
        Returns:
            {
              "validation_detectee": bool,
              "json_markdown": Dict ou None,
              "token_email": str ou None,
              "message": str
            }
        """
        
        body = email.get('body', '')
        subject = email.get('subject', '')
        
        # Chercher tag [_Head] VALIDE:
        if '[_Head] VALIDE:' not in body and '[_Head] VALIDE:' not in subject:
            return {
                "validation_detectee": False,
                "json_markdown": None,
                "token_email": None,
                "message": "Tag [_Head] VALIDE: non trouve"
            }
        
        # Tag trouve - extraire JSON
        parseur = ParseurMarkdownJSON()
        json_data = parseur.extraire_json(body)
        
        # Si JSON pas trouve dans le body, chercher dans les attachments
        if not json_data:
            json_data = DetecteurValidations._extraire_json_attachments(email, parseur)
        
        if not json_data:
            return {
                "validation_detectee": True,
                "json_markdown": None,
                "token_email": None,
                "message": "Tag [_Head] VALIDE: trouve MAIS aucun JSON valide"
            }
        
        # Extraire token depuis JSON
        token_email = json_data.get('token')
        
        return {
            "validation_detectee": True,
            "json_markdown": json_data,
            "token_email": token_email,
            "message": "Validation detectee avec JSON valide"
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
                if montant <= 0:
                    return False, f"Proposition {i}: montant doit etre > 0 (trouve: {montant})"
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
        
        # PHASE 5: Detection
        result_detection = self.detecteur.detecter_validation(email)
        
        if not result_detection['validation_detectee']:
            return {
                "validation_detectee": False,
                "statut": "IGNORE",
                "message": result_detection['message'],
                "ecritures_creees": 0,
                "type_evenement": None
            }
        
        # Recuperer le JSON des propositions
        json_data = result_detection['json_markdown']
        token_email = result_detection['token_email']
        
        if not json_data:
            return {
                "validation_detectee": True,
                "statut": "ERREUR",
                "message": "Validation detectee mais JSON invalide",
                "ecritures_creees": 0,
                "type_evenement": None
            }
        
        # PHASE 6: Extraction JSON (deja faite)
        propositions = json_data.get('propositions', [])
        type_evenement = json_data.get('type_evenement', 'UNKNOWN')
        
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
            evt_rejet = EvenementComptable(
                email_id=email.get('email_id'),
                email_from=email.get('from'),
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
        
        # Recuperer l'email original (source des propositions)
        evt_original = self.session.query(EvenementComptable).filter_by(
            statut='EN_ATTENTE_VALIDATION',
            type_evenement=type_evenement
        ).order_by(EvenementComptable.email_date.desc()).first()
        
        if not evt_original:
            return {
                "validation_detectee": True,
                "statut": "ERREUR",
                "message": f"Impossible de trouver l'evenement original ({type_evenement})",
                "ecritures_creees": 0,
                "type_evenement": type_evenement
            }
        
        # Choisir la fonction d'insertion selon le type
        if type_evenement == 'EVENEMENT_SIMPLE':
            succes, msg, ids = self.processeur.inserer_propositions_simple(
                propositions, evt_original.email_id, email.get('email_id'), email.get('from')
            )
        elif type_evenement == 'INIT_BILAN_2023':
            succes, msg, ids = self.processeur.inserer_propositions_init_bilan(
                propositions, evt_original.email_id, email.get('email_id'), email.get('from')
            )
        elif type_evenement == 'CLOTURE_EXERCICE':
            succes, msg, ids = self.processeur.inserer_propositions_cloture(
                propositions, evt_original.email_id, email.get('email_id'), email.get('from')
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
        
        # Mettre a jour l'evenement original
        evt_original.statut = 'INSERE_EN_DB'
        evt_original.email_validation_id = email.get('email_id')
        evt_original.ecritures_creees = ids
        evt_original.traite_at = datetime.now()
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
