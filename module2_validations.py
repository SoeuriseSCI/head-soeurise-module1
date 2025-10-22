"""
MODULE 2 VALIDATIONS V2 - TRAITEMENT DES VALIDATIONS
====================================================

Phases 5ï¸âƒ£-9ï¸âƒ£ du workflow:
5ï¸âƒ£ DÃ©tection: cherche tag [_Head] VALIDE: dans emails
6ï¸âƒ£ Extraction: parse JSON depuis bloc ```json...```
7ï¸âƒ£ Validation: vÃ©rifie intÃ©gritÃ© + token MD5
8ï¸âƒ£ Insertion: crÃ©e EcritureComptable en BD
9ï¸âƒ£ Tracking: met Ã  jour EvenementComptable

RÃ´le: Valider les propositions avant insertion, avec audit trail complet
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


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 1. DÃ‰TECTEUR VALIDATIONS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class DetecteurValidations:
    """DÃ©tecte les validations dans les emails reÃ§us"""
    
    @staticmethod
    def detecter_validation(email: Dict) -> Dict:
        """
        DÃ©tecte si l'email contient une validation
        
        Cherche le tag: [_Head] VALIDE:
        
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
                "message": "Tag [_Head] VALIDE: non trouvÃ©"
            }
        
        # Tag trouvÃ© - extraire JSON
        parseur = ParseurMarkdownJSON()
        json_data = parseur.extraire_json(body)
        
        if not json_data:
            return {
                "validation_detectee": True,
                "json_markdown": None,
                "token_email": None,
                "message": "Tag [_Head] VALIDE: trouvÃ© MAIS aucun JSON valide"
            }
        
        # Extraire token depuis JSON
        token_email = json_data.get('token')
        
        return {
            "validation_detectee": True,
            "json_markdown": json_data,
            "token_email": token_email,
            "message": "Validation dÃ©tectÃ©e avec JSON valide"
        }


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 2. VALIDATEUR INTÃ‰GRITÃ‰ JSON
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class ValidateurIntegriteJSON:
    """Valide l'intÃ©gritÃ© des propositions et dÃ©tecte les tamperings"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def valider_propositions(self, propositions: List[Dict], token_email: str) -> Tuple[bool, str]:
        """
        Valide intÃ©gritÃ© des propositions
        
        VÃ©rifications:
        1. Token MD5 match (dÃ©tecte tampering)
        2. Tous les comptes existent
        3. Montants > 0
        4. Structure JSON valide
        
        Returns:
            (valide, message_erreur)
        """
        
        # 1. VÃ©rifier token MD5
        token_calculated = hashlib.md5(
            json.dumps(propositions, sort_keys=True).encode()
        ).hexdigest()
        
        if token_calculated != token_email:
            return False, f"âŒ Token MD5 invalide (tampering dÃ©tectÃ©?) - Attendu: {token_email}, CalculÃ©: {token_calculated}"
        
        # 2. VÃ©rifier chaque proposition
        for i, prop in enumerate(propositions):
            
            # VÃ©rifier structure
            required_keys = ['compte_debit', 'compte_credit', 'montant', 'numero_ecriture']
            for key in required_keys:
                if key not in prop:
                    return False, f"Proposition {i}: clÃ© '{key}' manquante"
            
            # VÃ©rifier montant
            try:
                montant = Decimal(str(prop['montant']))
                if montant <= 0:
                    return False, f"Proposition {i}: montant doit Ãªtre > 0 (trouvÃ©: {montant})"
            except (ValueError, TypeError):
                return False, f"Proposition {i}: montant invalide '{prop['montant']}'"
            
            # VÃ©rifier comptes existent
            compte_debit = self.session.query(PlanCompte).filter_by(
                numero_compte=str(prop['compte_debit'])
            ).first()
            
            if not compte_debit:
                return False, f"Proposition {i}: compte dÃ©bit '{prop['compte_debit']}' n'existe pas"
            
            compte_credit = self.session.query(PlanCompte).filter_by(
                numero_compte=str(prop['compte_credit'])
            ).first()
            
            if not compte_credit:
                return False, f"Proposition {i}: compte crÃ©dit '{prop['compte_credit']}' n'existe pas"
        
        return True, ""


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 3. PROCESSEUR INSERTION
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class ProcesseurInsertion:
    """InsÃ¨re les propositions validÃ©es en tant que EcritureComptable"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def inserer_propositions_simple(self, 
                                   propositions: List[Dict],
                                   evt_original_id: str,
                                   evt_validation_id: str,
                                   email_validation_from: str) -> Tuple[bool, str, List[int]]:
        """InsÃ¨re propositions Ã©vÃ©nement simple"""
        
        return self._inserer_propositions_generiques(
            propositions, evt_original_id, evt_validation_id, email_validation_from
        )
    
    def inserer_propositions_init_bilan(self,
                                        propositions: List[Dict],
                                        evt_original_id: str,
                                        evt_validation_id: str,
                                        email_validation_from: str) -> Tuple[bool, str, List[int]]:
        """InsÃ¨re propositions init bilan + crÃ©e ExerciceComptable 2023"""
        
        try:
            # D'abord crÃ©er l'exercice 2023 s'il n'existe pas
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
            
            # Puis insÃ©rer les propositions
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
        """InsÃ¨re propositions clÃ´ture + crÃ©e ExerciceComptable 2024"""
        
        try:
            # RÃ©cupÃ©rer exercice 2023
            exercice_2023 = self.session.query(ExerciceComptable).filter_by(annee=2023).first()
            if not exercice_2023:
                return False, "Exercice 2023 non trouvÃ© pour clÃ´ture", []
            
            # Marquer 2023 comme CLOTURE
            exercice_2023.statut = 'CLOTURE'
            
            # CrÃ©er exercice 2024 s'il n'existe pas
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
            
            # Puis insÃ©rer les propositions (sur 2023)
            return self._inserer_propositions_generiques(
                propositions, evt_original_id, evt_validation_id, email_validation_from,
                exercice_id=exercice_2023.id
            )
        
        except Exception as e:
            self.session.rollback()
            return False, f"Erreur clÃ´ture: {str(e)[:100]}", []
    
    def _inserer_propositions_generiques(self,
                                        propositions: List[Dict],
                                        evt_original_id: str,
                                        evt_validation_id: str,
                                        email_validation_from: str,
                                        exercice_id: int = None) -> Tuple[bool, str, List[int]]:
        """InsÃ¨re les propositions de faÃ§on gÃ©nÃ©rique"""
        
        try:
            # Si pas d'exercice spÃ©cifiÃ©, utiliser 2024
            if not exercice_id:
                exercice_2024 = self.session.query(ExerciceComptable).filter_by(annee=2024).first()
                if not exercice_2024:
                    return False, "Exercice 2024 non trouvÃ©", []
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
                        validee_by_email_id=evt_validation_id,
                        valide=True,
                        validee_at=datetime.now(),
                        notes=f"ValidÃ©e par Ulrik via email {evt_validation_id}"
                    )
                    
                    self.session.add(ecriture)
                    self.session.flush()
                    ecriture_ids.append(ecriture.id)
                
                except IntegrityError as ie:
                    self.session.rollback()
                    return False, f"Erreur intÃ©gritÃ© DB: {str(ie)[:100]}", ecriture_ids
                except Exception as e:
                    self.session.rollback()
                    return False, f"Erreur insertion Ã©criture: {str(e)[:100]}", ecriture_ids
            
            self.session.commit()
            return True, f"{len(ecriture_ids)} Ã©critures insÃ©rÃ©es avec succÃ¨s", ecriture_ids
        
        except Exception as e:
            self.session.rollback()
            return False, f"Erreur globale: {str(e)[:100]}", []


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# 4. ORCHESTRATOR VALIDATIONS
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

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
        5ï¸âƒ£ DÃ©tecte tag [_Head] VALIDE:
        6ï¸âƒ£ Extrait JSON du bloc ```json...```
        7ï¸âƒ£ Valide intÃ©gritÃ© + token MD5
        8ï¸âƒ£ InsÃ¨re les EcritureComptable
        9ï¸âƒ£ Update EvenementComptable
        
        Returns:
            {
              "validation_detectee": bool,
              "statut": "OK" | "ERREUR",
              "message": str,
              "ecritures_creees": int,
              "type_evenement": str
            }
        """
        
        # PHASE 5ï¸âƒ£: DÃ©tection
        result_detection = self.detecteur.detecter_validation(email)
        
        if not result_detection['validation_detectee']:
            return {
                "validation_detectee": False,
                "statut": "IGNORÃ‰",
                "message": result_detection['message'],
                "ecritures_creees": 0,
                "type_evenement": None
            }
        
        # RÃ©cupÃ©rer le JSON des propositions
        json_data = result_detection['json_markdown']
        token_email = result_detection['token_email']
        
        if not json_data:
            return {
                "validation_detectee": True,
                "statut": "ERREUR",
                "message": "Validation dÃ©tectÃ©e mais JSON invalide",
                "ecritures_creees": 0,
                "type_evenement": None
            }
        
        # PHASE 6ï¸âƒ£: Extraction JSON (dÃ©jÃ  faite)
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
        
        # PHASE 7ï¸âƒ£: Validation intÃ©gritÃ©
        valide, msg_erreur = self.validateur.valider_propositions(propositions, token_email)
        
        if not valide:
            # CrÃ©er EvenementComptable rejetÃ©
            evt_rejet = EvenementComptable(
                email_id=email.get('email_id'),
                email_from=email.get('from'),
                email_subject=email.get('subject', ''),
                email_body=email.get('body', '')[:1000],
                type_evenement=type_evenement,
                est_comptable=True,
                statut='REJETÃ‰',
                message_erreur=msg_erreur
            )
            self.session.add(evt_rejet)
            self.session.commit()
            
            return {
                "validation_detectee": True,
                "statut": "ERREUR",
                "message": f"Validation Ã©chouÃ©e: {msg_erreur}",
                "ecritures_creees": 0,
                "type_evenement": type_evenement
            }
        
        # PHASE 8ï¸âƒ£-9ï¸âƒ£: Insertion + Update
        
        # RÃ©cupÃ©rer l'email original (source des propositions)
        evt_original = self.session.query(EvenementComptable).filter_by(
            statut='EN_ATTENTE_VALIDATION',
            type_evenement=type_evenement
        ).order_by(EvenementComptable.email_date.desc()).first()
        
        if not evt_original:
            return {
                "validation_detectee": True,
                "statut": "ERREUR",
                "message": f"Impossible de trouver l'Ã©vÃ©nement original ({type_evenement})",
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
            succes, msg, ids = False, f"Type Ã©vÃ©nement inconnu: {type_evenement}", []
        
        if not succes:
            return {
                "validation_detectee": True,
                "statut": "ERREUR",
                "message": f"Erreur insertion: {msg}",
                "ecritures_creees": 0,
                "type_evenement": type_evenement
            }
        
        # Mettre Ã  jour l'Ã©vÃ©nement original
        evt_original.statut = 'INSEPE_EN_DB'
        evt_original.email_validation_id = email.get('email_id')
        evt_original.ecritures_creees = ids
        evt_original.traite_at = datetime.now()
        self.session.commit()
        
        return {
            "validation_detectee": True,
            "statut": "OK",
            "message": f"âœ“ {len(ids)} Ã©critures insÃ©rÃ©es avec succÃ¨s",
            "ecritures_creees": len(ids),
            "type_evenement": type_evenement
        }


if __name__ == "__main__":
    print("âœ… Module 2 Validations V2 chargÃ© et prÃªt")
