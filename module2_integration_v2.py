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

                # ⚠️ DÉSACTIVÉ: Ingestion directe prêts (remplacé par workflow V6 avec propositions)
                # Pour réactiver l'ingestion directe, décommenter le bloc ci-dessous
                if False and type_evt == TypeEvenement.PRET_IMMOBILIER:
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

                            # Vérifier erreurs de parsing JSON
                            if '_erreur' in data:
                                msg_erreur = f"{attachment.get('filename')}: {data['_erreur']}"
                                erreurs_parsing_detaillees.append(msg_erreur)
                                self.erreurs.append(msg_erreur)

                                # Ajouter raw pour debug
                                if '_raw' in data:
                                    erreurs_parsing_detaillees.append(f"  Raw: {data['_raw'][:200]}")
                                continue

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
                            print(f"[DEBUG] Ingestion prêt {pret_info.get('numero_pret')} avec {len(echeances_data)} échéances", flush=True)

                            success, msg, pret_id = self.prets_manager.ingest_tableau_pret(
                                pret_data=pret_info,
                                echeances_data=echeances_data,
                                source_email_id=email.get('id'),
                                source_document=attachment.get('filename')
                            )

                            print(f"[DEBUG] Résultat ingestion: success={success}, msg={msg}, pret_id={pret_id}", flush=True)

                            if success:
                                prets_ingeres += 1
                                echeances_totales += len(echeances_data)
                                print(f"[DEBUG] SUCCÈS: {prets_ingeres} prêt(s), {echeances_totales} échéances", flush=True)
                            else:
                                print(f"[DEBUG] ÉCHEC: {msg}", flush=True)
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

                # ═══════════════════════════════════════════════════════════════
                # TRAITEMENT RELEVE_BANCAIRE - PHASE 1
                # ═══════════════════════════════════════════════════════════════
                if type_evt == TypeEvenement.RELEVE_BANCAIRE:
                    try:
                        from workflow_evenements import WorkflowEvenements

                        # Traiter chaque PDF d'attachments
                        attachments = email.get('attachments', [])
                        total_operations = 0
                        total_evenements_crees = 0
                        total_types_detectes = 0
                        all_ids_crees = []  # Accumuler les IDs créés
                        periode_document = None  # Période détectée du document

                        for attachment in attachments:
                            if not attachment.get('filename', '').lower().endswith('.pdf'):
                                continue

                            filepath = attachment.get('filepath')
                            if not filepath:
                                continue

                            # Métadonnées email
                            email_metadata = {
                                'email_id': email.get('email_id'),
                                'email_from': email.get('from'),
                                'email_date': email.get('date'),
                                'email_subject': email.get('subject'),
                                'email_body': email.get('body', '')
                            }

                            # Lancer le workflow d'extraction
                            # Note: La période est détectée automatiquement par analyse du PDF
                            #       et validée contre l'exercice comptable en cours
                            workflow = WorkflowEvenements(self.database_url, phase=1)
                            workflow_result = workflow.traiter_pdf(
                                filepath,
                                email_metadata,
                                auto_detect=True
                            )

                            total_operations += workflow_result.get('total_operations', 0)
                            total_evenements_crees += workflow_result.get('evenements_crees', 0)
                            total_types_detectes += workflow_result.get('types_detectes', 0)
                            all_ids_crees.extend(workflow_result.get('ids_crees', []))  # Accumuler IDs

                            # Capturer la période du document
                            if workflow_result.get('periode_document'):
                                periode_document = workflow_result.get('periode_document')

                            self.emails_traites += 1

                        # NOUVEAU : Générer les propositions comptables automatiquement
                        total_propositions = 0
                        if total_evenements_crees > 0:
                            try:
                                import sys
                                print()
                                print("📝 GÉNÉRATION AUTOMATIQUE DES PROPOSITIONS")
                                print("-" * 80)
                                print(f"🔍 IDs événements créés: {all_ids_crees}")
                                print(f"🔍 Total événements: {total_evenements_crees}")
                                sys.stdout.flush()

                                # Créer une nouvelle instance du workflow pour générer propositions
                                workflow = WorkflowEvenements(self.database_url, phase=1)
                                # CRITIQUE: Passer explicitement les IDs pour contourner le filtre phase
                                propositions = workflow.generer_propositions(evenement_ids=all_ids_crees)
                                total_propositions = len(propositions)

                                print(f"✅ {total_propositions} propositions générées")
                                print()
                                sys.stdout.flush()

                                self.propositions_generees += total_propositions

                                # NOUVEAU: Stocker et envoyer les propositions par email
                                if total_propositions > 0:
                                    try:
                                        # Convertir le format de propositions pour le stockage
                                        propositions_list = []
                                        for prop_data in propositions:
                                            proposition = prop_data['proposition']
                                            for ecriture in proposition.get('ecritures', []):
                                                # Convertir date_ecriture en string si c'est un objet date
                                                date_ecriture = ecriture.get('date_ecriture')
                                                if date_ecriture and hasattr(date_ecriture, 'isoformat'):
                                                    date_ecriture = date_ecriture.isoformat()

                                                propositions_list.append({
                                                    'numero_ecriture': f"EVT-{prop_data['evenement_id']}",
                                                    'type': proposition['type_evenement'],
                                                    'compte_debit': ecriture['compte_debit'],
                                                    'compte_credit': ecriture['compte_credit'],
                                                    'montant': ecriture['montant'],
                                                    'libelle': ecriture.get('libelle_ecriture', proposition['description']),
                                                    'date_ecriture': date_ecriture
                                                })

                                        # Stocker les propositions en BD avec token
                                        token_stocke, prop_id = self.propositions_manager.stocker_proposition(
                                            type_evenement='RELEVE_BANCAIRE',
                                            propositions=propositions_list,
                                            email_id=email.get('id'),
                                            email_from=email.get('from'),
                                            email_date=email.get('date'),
                                            email_subject=email.get('subject')
                                        )

                                        # Générer un Markdown récapitulatif
                                        from datetime import datetime as dt
                                        markdown_recap = f"""# Propositions Comptables - Relevés Bancaires

**Date:** {dt.now().strftime('%d/%m/%Y %H:%M')}
**Token:** `{token_stocke}`

## Résumé

- **{total_propositions} propositions générées** depuis les relevés bancaires
- **{total_evenements_crees} événements comptables** créés

## Détails des Propositions

"""
                                        for i, prop_data in enumerate(propositions, 1):
                                            proposition = prop_data['proposition']
                                            markdown_recap += f"### Proposition {i}: {proposition['type_evenement']}\n\n"
                                            markdown_recap += f"**Événement ID**: #{prop_data['evenement_id']}\n"
                                            markdown_recap += f"**Confiance**: {proposition['confiance']*100:.0f}%\n"
                                            markdown_recap += f"**Description**: {proposition['description']}\n\n"
                                            markdown_recap += "**Écritures proposées:**\n\n"
                                            for ecriture in proposition.get('ecritures', []):
                                                markdown_recap += f"- Débit {ecriture['compte_debit']} / Crédit {ecriture['compte_credit']} : {ecriture['montant']:.2f}€\n"
                                                markdown_recap += f"  - Libellé: {ecriture.get('libelle_ecriture', 'N/A')}\n"
                                            markdown_recap += "\n"

                                        markdown_recap += f"""
## Validation

Pour valider ces propositions, répondez à cet email avec le tag:

**[_Head] VALIDE: {token_stocke}**

---

_Head.Soeurise - {dt.now().strftime('%d/%m/%Y %H:%M')}
"""

                                        # Envoyer email à Ulrik avec propositions
                                        email_envoye = self.envoyeur.envoyer_propositions(
                                            self.email_ulrik,
                                            'RELEVE_BANCAIRE',
                                            markdown_recap,
                                            token_stocke,
                                            subject_suffix=f"- {total_propositions} proposition(s)"
                                        )

                                        if email_envoye:
                                            resultats['emails_envoyes'] += 1
                                            print(f"📧 Email de propositions envoyé à {self.email_ulrik}")
                                        else:
                                            print(f"⚠️  Échec envoi email de propositions")

                                    except Exception as e:
                                        print(f"⚠️  Erreur stockage/envoi propositions: {e}")
                                        import traceback
                                        traceback.print_exc()

                            except Exception as e:
                                import sys
                                self.erreurs.append(f"Erreur génération propositions: {str(e)[:200]}")
                                print(f"❌ Erreur génération propositions: {e}")
                                sys.stdout.flush()
                                import traceback
                                traceback.print_exc()

                        # Ajouter résultats
                        if total_evenements_crees > 0:
                            message = f'{total_operations} opérations extraites, {total_evenements_crees} événements créés, {total_types_detectes} types détectés, {total_propositions} propositions générées'
                            if periode_document:
                                message += f' | Période: {periode_document}'

                            resultats['details'].append({
                                'type': type_evt.value,
                                'propositions': total_propositions,
                                'status': 'extraction_reussie',
                                'message': message,
                                'operations_extraites': total_operations,
                                'evenements_crees': total_evenements_crees,
                                'types_detectes': total_types_detectes,
                                'periode_document': periode_document
                            })

                            resultats['propositions_generees'] += total_propositions
                        else:
                            self.erreurs.append("Aucun événement créé depuis les relevés bancaires")
                            resultats['details'].append({
                                'type': type_evt.value,
                                'propositions': 0,
                                'status': 'extraction_echec',
                                'message': 'Échec extraction relevés bancaires'
                            })

                        continue

                    except Exception as e:
                        self.erreurs.append(f"Erreur extraction relevés: {str(e)[:200]}")
                        import traceback
                        traceback.print_exc()
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
                # Utiliser la méthode multi-tokens qui retourne une liste
                results = self.workflow_validation.traiter_email_validations_multiples(email)

                # Traiter chaque résultat
                for result in results:
                    if result.get('validation_detectee'):

                        if result.get('statut') == 'OK':
                            self.validations_traitees += 1
                            self.ecritures_inserees += result.get('ecritures_creees', 0)

                            resultats['validations_traitees'] += 1
                            resultats['ecritures_inserees'] += result.get('ecritures_creees', 0)

                            resultats['details'].append({
                                'type': result.get('type_evenement', ''),
                                'ecritures_inserees': result.get('ecritures_creees', 0),
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
