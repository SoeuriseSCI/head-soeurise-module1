"""
MODULE 2 - INTÃ‰GRATION V2 (FIXED)
=========================
Point d'entrÃ©e unique pour intÃ©grer le workflow complet dans reveil_quotidien()

FIX: Adapter les comparaisons avec TypeEvenement Enum

GÃ¨re:
1. DÃ©tection emails comptables â†’ gÃ©nÃ©ration propositions
2. DÃ©tection validations â†’ insertion en DB
3. Rapport formatÃ© pour inclusion dans rapport quotidien
"""

import json
import os
from typing import Dict, List, Tuple
from datetime import datetime

from sqlalchemy.orm import Session

# Imports workflows
from module2_workflow_v2 import (
    WorkflowModule2V2,
    DetecteurTypeEvenement,
    TypeEvenement,
    OCRExtractor,
    EnvoyeurMarkdown
)
from module2_validations import OrchestratorValidations


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# ORCHESTRATEUR PRINCIPAL
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

class IntegratorModule2:
    """
    IntÃ©grateur principal pour module 2 dans le reveil quotidien
    
    GÃ¨re:
    - Traitement emails entrants (gÃ©nÃ©ration propositions)
    - Traitement emails validations (insertion DB)
    - GÃ©nÃ©ration rapport quotidien
    """
    
    def __init__(
        self,
        database_url: str,
        anthropic_api_key: str,
        email_soeurise: str,
        password_soeurise: str,
        email_ulrik: str
    ):
        self.database_url = database_url
        self.api_key = anthropic_api_key
        self.email_soeurise = email_soeurise
        self.password_soeurise = password_soeurise
        self.email_ulrik = email_ulrik
        
        # Initialiser composants
        self.session = self._get_session()
        self.workflow_generation = WorkflowModule2V2(anthropic_api_key, database_url)
        self.workflow_validation = OrchestratorValidations(self.session)
        self.envoyeur = EnvoyeurMarkdown(email_soeurise, password_soeurise, email_ulrik)
        self.ocr = OCRExtractor(anthropic_api_key)
        
        # Ã‰tat du traitement
        self.emails_traites = 0
        self.propositions_generees = 0
        self.validations_traitees = 0
        self.ecritures_inserees = 0
        self.erreurs = []
        self.actions_email = []  # Emails Ã  envoyer
    
    def _get_session(self) -> Session:
        """RÃ©cupÃ¨re une session DB"""
        from models_module2 import get_session
        return get_session(self.database_url)
    
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # PHASE 1: TRAITEMENT EMAILS ENTRANTS
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    
    def traiter_emails_entrants(self, emails: List[Dict]) -> Dict:
        """
        Traite les emails entrants pour dÃ©tecter Ã©vÃ©nements comptables
        
        Returns:
            {
                'propositions_generees': int,
                'details': [...]
            }
        """
        
        resultats = {
            'propositions_generees': 0,
            'details': [],
            'emails_envoyes': 0
        }
        
        for email in emails:
            # Skip si non autorisÃ©
            if not email.get('is_authorized') or not email.get('action_allowed'):
                continue
            
            try:
                # DÃ©tecter type
                type_evt = DetecteurTypeEvenement.detecter(email)
                
                if type_evt == TypeEvenement.UNKNOWN:  # âœ… COMPARAISON ENUM FIX
                    continue
                
                # GÃ©nÃ©rer propositions via workflow
                result = self.workflow_generation.traiter_email(email)
                
                # Traiter le rÃ©sultat
                if result.get('statut') == 'OK':
                    
                    # Envoyer email Ã  Ulrik avec propositions âœ… FIX: Passer email_to en premier
                    email_envoye = self.envoyeur.envoyer_propositions(
                        self.email_ulrik,  # âœ… email_to
                        type_evt.value,  # âœ… type_evt
                        result['markdown'],  # âœ… markdown
                        result['token'],  # âœ… token
                        subject_suffix=f"- {len(result.get('propositions', {}).get('propositions', []))} proposition(s)"
                    )
                    
                    if email_envoye:
                        resultats['emails_envoyes'] += 1
                        self.propositions_generees += len(result.get('propositions', {}).get('propositions', []))
                    else:
                        self.erreurs.append(f"Impossible d'envoyer email pour {type_evt.value}")
                    
                    resultats['propositions_generees'] += len(result.get('propositions', {}).get('propositions', []))
                    resultats['details'].append({
                        'type': type_evt.value,
                        'propositions': len(result.get('propositions', {}).get('propositions', [])),
                        'status': 'en_attente_validation'
                    })
                
                else:
                    self.erreurs.append(result.get('message', 'Erreur inconnue'))
                
                self.emails_traites += 1
            
            except Exception as e:
                self.erreurs.append(f"Erreur traitement email: {str(e)[:100]}")
        
        return resultats
    
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # PHASE 2: TRAITEMENT VALIDATIONS
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    
    def traiter_validations(self, emails: List[Dict]) -> Dict:
        """
        Traite les rÃ©ponses de validation [_Head] VALIDE:
        
        Returns:
            {
                'validations_traitees': int,
                'ecritures_inserees': int,
                'details': [...]
            }
        """
        
        resultats = {
            'validations_traitees': 0,
            'ecritures_inserees': 0,
            'details': []
        }
        
        for email in emails:
            # Chercher tag [_Head] VALIDE:
            if '[_head] valide:' not in email.get('body', '').lower():
                continue
            
            try:
                result = self.workflow_validation.traiter_email_validation(email)
                
                if result.get('validation_detectee'):
                    
                    if result.get('statut') == 'OK':
                        self.validations_traitees += 1
                        self.ecritures_inserees += result.get('ecritures_inserees', 0)
                        
                        resultats['validations_traitees'] += 1
                        resultats['ecritures_inserees'] += result.get('ecritures_inserees', 0)
                        
                        resultats['details'].append({
                            'type': result.get('type_proposition', ''),
                            'ecritures_inserees': result.get('ecritures_inserees', 0),
                            'status': 'insere_en_db'
                        })
                    
                    else:
                        self.erreurs.append(f"Validation Ã©chouÃ©e: {result.get('message')}")
                        resultats['details'].append({
                            'status': 'erreur',
                            'message': result.get('message')
                        })
            
            except Exception as e:
                self.erreurs.append(f"Erreur traitement validation: {str(e)[:100]}")
        
        return resultats
    
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    # GÃ‰NÃ‰RATION RAPPORT
    # â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
    
    def generer_rapport(
        self,
        resultats_entrants: Dict,
        resultats_validations: Dict
    ) -> str:
        """GÃ©nÃ¨re le rapport pour inclusion dans rapport quotidien"""
        
        rapport = """
## ðŸ“Š MODULE 2 - COMPTABILITÃ‰

### Ã‰tat du traitement

**Emails entrants traitÃ©s:** {}
- Propositions gÃ©nÃ©rÃ©es: {}
- Emails de validation envoyÃ©s: {}

**Validations reÃ§ues:** {}
- Ã‰critures insÃ©rÃ©es en BD: {}

""".format(
            self.emails_traites,
            resultats_entrants.get('propositions_generees', 0),
            resultats_entrants.get('emails_envoyes', 0),
            resultats_validations.get('validations_traitees', 0),
            resultats_validations.get('ecritures_inserees', 0)
        )
        
        # DÃ©tails des propositions gÃ©nÃ©rÃ©es
        if resultats_entrants.get('details'):
            rapport += "### ðŸ“ Propositions gÃ©nÃ©rÃ©es\n\n"
            for detail in resultats_entrants['details']:
                rapport += f"- **{detail['type']}**: {detail['propositions']} proposition(s) â†’ En attente de validation\n"
        
        # DÃ©tails des validations traitÃ©es
        if resultats_validations.get('details'):
            rapport += "\n### âœ… Validations traitÃ©es\n\n"
            for detail in resultats_validations['details']:
                if detail.get('status') == 'insere_en_db':
                    rapport += f"- **{detail['type']}**: {detail['ecritures_inserees']} Ã©criture(s) insÃ©rÃ©e(s)\n"
                elif detail.get('status') == 'erreur':
                    rapport += f"- âŒ {detail.get('message', 'Erreur')}\n"
        
        # RÃ©sumÃ© erreurs
        if self.erreurs:
            rapport += f"\n### âš ï¸ Erreurs ({len(self.erreurs)})\n\n"
            for erreur in self.erreurs[:5]:  # Limiter Ã  5
                rapport += f"- {erreur}\n"
            if len(self.erreurs) > 5:
                rapport += f"- ... et {len(self.erreurs) - 5} autre(s) erreur(s)\n"
        
        # RÃ©sumÃ© final
        rapport += f"\n### ðŸ“Š RÃ©sumÃ©\n\n"
        rapport += f"- Total emails traitÃ©s: {self.emails_traites}\n"
        rapport += f"- Total propositions: {self.propositions_generees}\n"
        rapport += f"- Total validations: {self.validations_traitees}\n"
        rapport += f"- Total Ã©critures insÃ©rÃ©es: {self.ecritures_inserees}\n"
        
        return rapport


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# POINT D'ENTRÃ‰E UNIQUE POUR reveil_quotidien()
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

def integrer_module2_v2(
    emails: List[Dict],
    database_url: str,
    anthropic_api_key: str,
    email_soeurise: str,
    password_soeurise: str,
    email_ulrik: str
) -> Dict:
    """
    Point d'entrÃ©e unique Ã  appeler depuis reveil_quotidien()
    
    Usage dans main_V4_2.py:
        
        rapport_module2 = integrer_module2_v2(
            emails,
            os.environ['DATABASE_URL'],
            os.environ['ANTHROPIC_API_KEY'],
            os.environ['SOEURISE_EMAIL'],
            os.environ['SOEURISE_PASSWORD'],
            os.environ['NOTIF_EMAIL']
        )
        
        # Inclure dans rapport quotidien:
        rapport_quotidien += rapport_module2['rapport']
    
    Returns:
        {
            'rapport': str (Ã  inclure dans rapport_quotidien),
            'stats': {
                'emails_traites': int,
                'propositions_generees': int,
                'validations_traitees': int,
                'ecritures_inserees': int
            }
        }
    """
    
    try:
        # Initialiser intÃ©grateur
        integrator = IntegratorModule2(
            database_url,
            anthropic_api_key,
            email_soeurise,
            password_soeurise,
            email_ulrik
        )
        
        # Phase 1: Traiter emails entrants (gÃ©nÃ©ration propositions)
        resultats_entrants = integrator.traiter_emails_entrants(emails)
        
        # Phase 2: Traiter validations (insertion BD)
        resultats_validations = integrator.traiter_validations(emails)
        
        # GÃ©nÃ©rer rapport
        rapport = integrator.generer_rapport(resultats_entrants, resultats_validations)
        
        return {
            'rapport': rapport,
            'stats': {
                'emails_traites': integrator.emails_traites,
                'propositions_generees': integrator.propositions_generees,
                'validations_traitees': integrator.validations_traitees,
                'ecritures_inserees': integrator.ecritures_inserees,
                'erreurs': len(integrator.erreurs)
            },
            'success': True
        }
    
    except Exception as e:
        return {
            'rapport': f"\n## âŒ MODULE 2 - ERREUR\n\n{str(e)}\n",
            'stats': {
                'emails_traites': 0,
                'propositions_generees': 0,
                'validations_traitees': 0,
                'ecritures_inserees': 0,
                'erreurs': 1
            },
            'success': False
        }


# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
# EXPORT
# â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

__all__ = [
    'IntegratorModule2',
    'integrer_module2_v2',
]
