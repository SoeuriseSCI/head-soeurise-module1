"""
MODULE 2 - INTÉGRATION V2 (FIXED)
=========================
Point d'entrée unique pour intégrer le workflow complet dans reveil_quotidien()

FIX: Adapter les comparaisons avec TypeEvenement Enum

Gère:
1. Détection emails comptables → génération propositions
2. Détection validations → insertion en DB
3. Rapport formaté pour inclusion dans rapport quotidien
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
    TypeEvenement,  # ✅ IMPORT FIX
    OCRExtractor
)
from module2_workflow_v2_branches import (
    EnvoyeurMarkdown,
    BrancheEvenementSimple,
    BrancheInitBilan2023,
    BrancheCloture2023
)
from module2_validations import (
    OrchestratorValidations,
    DetecteurValidations
)


# ═══════════════════════════════════════════════════════════════════════════════
# ORCHESTRATEUR PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class IntegratorModule2:
    """
    Intégrateur principal pour module 2 dans le reveil quotidien
    
    Gère:
    - Traitement emails entrants (génération propositions)
    - Traitement emails validations (insertion DB)
    - Génération rapport quotidien
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
        
        # État du traitement
        self.emails_traites = 0
        self.propositions_generees = 0
        self.validations_traitees = 0
        self.ecritures_inserees = 0
        self.erreurs = []
        self.actions_email = []  # Emails à envoyer
    
    def _get_session(self) -> Session:
        """Récupère une session DB"""
        from models_module2 import get_session
        return get_session(self.database_url)
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # PHASE 1: TRAITEMENT EMAILS ENTRANTS
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def traiter_emails_entrants(self, emails: List[Dict]) -> Dict:
        """
        Traite les emails entrants pour détecter événements comptables
        
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
            # Skip si non autorisé
            if not email.get('is_authorized') or not email.get('action_allowed'):
                continue
            
            try:
                # Détecter type
                type_evt = DetecteurTypeEvenement.detecter(email)
                
                if type_evt == TypeEvenement.UNKNOWN:  # ✅ COMPARAISON ENUM FIX
                    continue
                
                # Générer propositions via workflow
                result = self.workflow_generation.traiter_email(email)
                
                # Traiter le résultat
                if result.get('statut') == 'OK':
                    
                    # Envoyer email à Ulrik avec propositions ✅ FIX: Passer email_to en premier
                    email_envoye = self.envoyeur.envoyer_propositions(
                        self.email_ulrik,  # ✅ email_to
                        type_evt.value,  # ✅ type_evt
                        result['markdown'],  # ✅ markdown
                        result['token'],  # ✅ token
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
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # PHASE 2: TRAITEMENT VALIDATIONS
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def traiter_validations(self, emails: List[Dict]) -> Dict:
        """
        Traite les réponses de validation [_Head] VALIDE:
        
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
                        self.erreurs.append(f"Validation échouée: {result.get('message')}")
                        resultats['details'].append({
                            'status': 'erreur',
                            'message': result.get('message')
                        })
            
            except Exception as e:
                self.erreurs.append(f"Erreur traitement validation: {str(e)[:100]}")
        
        return resultats
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # GÉNÉRATION RAPPORT
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def generer_rapport(
        self,
        resultats_entrants: Dict,
        resultats_validations: Dict
    ) -> str:
        """Génère le rapport pour inclusion dans rapport quotidien"""
        
        rapport = """
## 📊 MODULE 2 - COMPTABILITÉ

### État du traitement

**Emails entrants traités:** {}
- Propositions générées: {}
- Emails de validation envoyés: {}

**Validations reçues:** {}
- Écritures insérées en BD: {}

""".format(
            self.emails_traites,
            resultats_entrants.get('propositions_generees', 0),
            resultats_entrants.get('emails_envoyes', 0),
            resultats_validations.get('validations_traitees', 0),
            resultats_validations.get('ecritures_inserees', 0)
        )
        
        # Détails des propositions générées
        if resultats_entrants.get('details'):
            rapport += "### 📝 Propositions générées\n\n"
            for detail in resultats_entrants['details']:
                rapport += f"- **{detail['type']}**: {detail['propositions']} proposition(s) → En attente de validation\n"
        
        # Détails des validations traitées
        if resultats_validations.get('details'):
            rapport += "\n### ✅ Validations traitées\n\n"
            for detail in resultats_validations['details']:
                if detail.get('status') == 'insere_en_db':
                    rapport += f"- **{detail['type']}**: {detail['ecritures_inserees']} écriture(s) insérée(s)\n"
                elif detail.get('status') == 'erreur':
                    rapport += f"- ❌ {detail.get('message', 'Erreur')}\n"
        
        # Résumé erreurs
        if self.erreurs:
            rapport += f"\n### ⚠️ Erreurs ({len(self.erreurs)})\n\n"
            for erreur in self.erreurs[:5]:  # Limiter à 5
                rapport += f"- {erreur}\n"
            if len(self.erreurs) > 5:
                rapport += f"- ... et {len(self.erreurs) - 5} autre(s) erreur(s)\n"
        
        # Résumé final
        rapport += f"\n### 📊 Résumé\n\n"
        rapport += f"- Total emails traités: {self.emails_traites}\n"
        rapport += f"- Total propositions: {self.propositions_generees}\n"
        rapport += f"- Total validations: {self.validations_traitees}\n"
        rapport += f"- Total écritures insérées: {self.ecritures_inserees}\n"
        
        return rapport


# ═══════════════════════════════════════════════════════════════════════════════
# POINT D'ENTRÉE UNIQUE POUR reveil_quotidien()
# ═══════════════════════════════════════════════════════════════════════════════

def integrer_module2_v2(
    emails: List[Dict],
    database_url: str,
    anthropic_api_key: str,
    email_soeurise: str,
    password_soeurise: str,
    email_ulrik: str
) -> Dict:
    """
    Point d'entrée unique à appeler depuis reveil_quotidien()
    
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
            'rapport': str (à inclure dans rapport_quotidien),
            'stats': {
                'emails_traites': int,
                'propositions_generees': int,
                'validations_traitees': int,
                'ecritures_inserees': int
            }
        }
    """
    
    try:
        # Initialiser intégrateur
        integrator = IntegratorModule2(
            database_url,
            anthropic_api_key,
            email_soeurise,
            password_soeurise,
            email_ulrik
        )
        
        # Phase 1: Traiter emails entrants (génération propositions)
        resultats_entrants = integrator.traiter_emails_entrants(emails)
        
        # Phase 2: Traiter validations (insertion BD)
        resultats_validations = integrator.traiter_validations(emails)
        
        # Générer rapport
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
            'rapport': f"\n## ❌ MODULE 2 - ERREUR\n\n{str(e)}\n",
            'stats': {
                'emails_traites': 0,
                'propositions_generees': 0,
                'validations_traitees': 0,
                'ecritures_inserees': 0,
                'erreurs': 1
            },
            'success': False
        }


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    'IntegratorModule2',
    'integrer_module2_v2',
]
