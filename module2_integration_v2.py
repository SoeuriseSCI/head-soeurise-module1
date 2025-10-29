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
    TypeEvenement,
    OCRExtractor,
    EnvoyeurMarkdown
)
from module2_validations import OrchestratorValidations
from propositions_manager import PropositionsManager


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
        self.propositions_manager = PropositionsManager(self.session)
        self.envoyeur = EnvoyeurMarkdown(email_soeurise, password_soeurise, email_ulrik)
        self.ocr = OCRExtractor(anthropic_api_key)

        # Import PretsManager et ParseurTableauPret pour ingestion prêts
        from prets_manager import PretsManager
        from module2_workflow_v2 import ParseurTableauPret
        self.prets_manager = PretsManager(self.session)
        self.parseur_pret = ParseurTableauPret(self.ocr)

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

                # ✅ Traitement PRET_IMMOBILIER (Ingestion tableaux amortissement)
                if type_evt == TypeEvenement.PRET_IMMOBILIER:
                    try:
                        # Traiter chaque PDF d'attachments
                        attachments = email.get('attachments', [])
                        prets_ingeres = 0
                        echeances_totales = 0
                        erreurs_parsing_detaillees = []

                        for attachment in attachments:
                            if not attachment.get('filename', '').lower().endswith('.pdf'):
                                continue

                            # Parser tableau amortissement
                            filepath = attachment.get('filepath')
                            if not filepath:
                                continue

                            data = self.parseur_pret.parse_from_pdf(filepath)

                            if not data or not data.get('pret'):
                                self.erreurs.append(f"Parsing échoué pour {attachment.get('filename')}: données manquantes")
                                continue

                            pret_info = data.get('pret', {})
                            echeances_data = data.get('echeances', [])

                            # Vérifier champs critiques
                            champs_critiques = ['numero_pret', 'montant_initial', 'taux_annuel', 'duree_mois']
                            champs_manquants = [c for c in champs_critiques if not pret_info.get(c)]

                            if champs_manquants:
                                msg_erreur = f"{attachment.get('filename')}: Champs manquants: {', '.join(champs_manquants)}"
                                erreurs_parsing_detaillees.append(msg_erreur)
                                self.erreurs.append(msg_erreur)

                                # Ajouter erreurs de parsing si présentes
                                if '_erreurs_parsing' in pret_info:
                                    erreurs_parsing_detaillees.append(f"  Détails: {'; '.join(pret_info['_erreurs_parsing'])}")
                                continue

                            if not echeances_data or len(echeances_data) == 0:
                                msg_erreur = f"{attachment.get('filename')}: Aucune échéance extraite du PDF"
                                erreurs_parsing_detaillees.append(msg_erreur)
                                self.erreurs.append(msg_erreur)
                                continue

                            # Ingérer en BD
                            success, msg, pret_id = self.prets_manager.ingest_tableau_pret(
                                pret_data=pret_info,
                                echeances_data=echeances_data,
                                source_email_id=email.get('id'),
                                source_document=attachment.get('filename')
                            )

                            if success:
                                prets_ingeres += 1
                                echeances_totales += len(echeances_data)
                            else:
                                self.erreurs.append(msg)

                        # Résultat ingestion
                        if prets_ingeres > 0:
                            msg_resultat = f'{prets_ingeres} prêt(s) ingéré(s), {echeances_totales} échéances stockées'
                            if erreurs_parsing_detaillees:
                                msg_resultat += f" (avec {len(erreurs_parsing_detaillees)} erreur(s) de parsing)"

                            resultats['details'].append({
                                'type': type_evt.value,
                                'propositions': 0,  # Pas de propositions comptables
                                'status': 'ingestion_reussie',
                                'message': msg_resultat,
                                'prets_ingeres': prets_ingeres,
                                'echeances_stockees': echeances_totales
                            })
                        else:
                            self.erreurs.append("Aucun prêt ingéré depuis les PDF")
                            resultats['details'].append({
                                'type': type_evt.value,
                                'propositions': 0,
                                'status': 'ingestion_echec',
                                'message': 'Échec ingestion tableaux amortissement - Voir erreurs détaillées'
                            })

                        continue

                    except Exception as e:
                        self.erreurs.append(f"Erreur ingestion prêts: {str(e)[:200]}")
                        resultats['details'].append({
                            'type': type_evt.value,
                            'propositions': 0,
                            'status': 'erreur',
                            'message': f'Erreur: {str(e)[:100]}'
                        })
                        continue

                # Générer propositions via workflow
                result = self.workflow_generation.traiter_email(email)
                
                # Traiter le résultat
                if result.get('statut') == 'OK':

                    # Stocker les propositions en BD avec token
                    propositions_list = result.get('propositions', {}).get('propositions', [])

                    # ⚠️ FIX BUG #2: Ne pas envoyer d'email si 0 propositions
                    if len(propositions_list) == 0:
                        self.erreurs.append(f"Détection {type_evt.value} mais 0 propositions générées - Email non envoyé")
                        resultats['details'].append({
                            'type': type_evt.value,
                            'propositions': 0,
                            'status': 'detection_vide',
                            'message': 'Aucune proposition générée'
                        })
                        continue

                    token_stocke, prop_id = self.propositions_manager.stocker_proposition(
                        type_evenement=type_evt.value,
                        propositions=propositions_list,
                        email_id=email.get('id'),
                        email_from=email.get('from'),
                        email_date=email.get('date'),
                        email_subject=email.get('subject'),
                        token=result['token']
                    )

                    # Envoyer email à Ulrik avec propositions ✅ FIX: Passer email_to en premier
                    email_envoye = self.envoyeur.envoyer_propositions(
                        self.email_ulrik,  # ✅ email_to
                        type_evt.value,  # ✅ type_evt
                        result['markdown'],  # ✅ markdown
                        token_stocke,  # ✅ token (utiliser token_stocke au lieu de result['token'])
                        subject_suffix=f"- {len(propositions_list)} proposition(s)"
                    )

                    if email_envoye:
                        resultats['emails_envoyes'] += 1
                        self.propositions_generees += len(propositions_list)
                    else:
                        self.erreurs.append(f"Impossible d'envoyer email pour {type_evt.value}")

                    resultats['propositions_generees'] += len(propositions_list)
                    resultats['details'].append({
                        'type': type_evt.value,
                        'propositions': len(propositions_list),
                        'status': 'en_attente_validation',
                        'token': token_stocke,
                        'proposition_id': prop_id
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
