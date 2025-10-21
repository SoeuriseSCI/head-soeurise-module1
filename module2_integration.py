"""
MODULE 2 - INTÉGRATION AU WORKFLOW QUOTIDIEN
============================================
Comment Module 2 s'intègre dans le reveil_quotidien() de main_V4.0.py

WORKFLOW:
1. Email reçu (autorisé ou non)
2. Créer EvenementComptable EN_ATTENTE
3. Si autorisé + comptable → analyser et créer écritures
4. Générer rapports (Bilan 2024, Résultat...)
5. Inclure dans rapport quotidien
"""

from datetime import datetime, date
from decimal import Decimal
import json
import re
from typing import List, Dict, Tuple

from sqlalchemy.orm import Session

# Imports Module 2
from models_module2 import (
    ExerciceComptable, PlanCompte, EcritureComptable, EvenementComptable,
    Immobilisation, CalculAmortissement, BalanceMensuelle, RapportComptable,
    get_session, init_module2
)


# ═══════════════════════════════════════════════════════════════════════════════
# ÉTAPE 1: DÉTECTEUR D'ÉVÉNEMENTS COMPTABLES
# ═══════════════════════════════════════════════════════════════════════════════

class DetecteurEvenementsComptables:
    """
    Analyse un email pour détecter s'il contient des événements comptables
    """
    
    PATTERNS = {
        'loyer': {
            'keywords': ['loyer', 'paiement locataire', 'encaissement', 'location'],
            'type': 'LOYER',
            'compte_credit': '701',  # Loyers
        },
        'charge_entretien': {
            'keywords': ['entretien', 'réparation', 'maintenance', 'reparation'],
            'type': 'CHARGE',
            'compte_charge': '614',  # Entretien et réparations
        },
        'assurance': {
            'keywords': ['assurance', 'prime assurance', 'police'],
            'type': 'CHARGE',
            'compte_charge': '615',  # Assurances
        },
        'taxe': {
            'keywords': ['taxe foncière', 'tf', 'impôt', 'taxe'],
            'type': 'CHARGE',
            'compte_charge': '631',  # Impôts taxes
        },
        'charge_copropriete': {
            'keywords': ['charge copropriété', 'charges communes', 'syndic'],
            'type': 'CHARGE',
            'compte_charge': '614',  # Entretien et réparations (ou créer compte)
        },
        'amortissement': {
            'keywords': ['amortissement', 'dotation', 'immobilisation'],
            'type': 'AMORTISSEMENT',
        },
        'interet_emprunt': {
            'keywords': ['intérêt', 'emprunt', 'interet', 'pret'],
            'type': 'CHARGE',
            'compte_charge': '661',  # Intérêts emprunts
        }
    }
    
    def __init__(self, session: Session):
        self.session = session
    
    def analyser_email(self, body: str, date_email: date, from_email: str) -> List[Dict]:
        """
        Analyse un email et retourne les événements comptables détectés
        
        Returns:
            [
                {
                    'type': 'LOYER',
                    'montant': 1000.00,
                    'date': date,
                    'description': '...',
                    'pattern': 'loyer',
                    'confidence': 0.95
                }
            ]
        """
        events = []
        body_lower = body.lower()
        
        # Chercher montants
        montants = self._extraire_montants(body)
        
        # Chercher patterns
        for pattern_name, pattern_config in self.PATTERNS.items():
            keywords = pattern_config['keywords']
            if any(kw in body_lower for kw in keywords):
                
                # Pour loyer: chercher montant associé
                if pattern_name == 'loyer' and montants:
                    for montant in montants:
                        events.append({
                            'type': pattern_config['type'],
                            'montant': montant,
                            'date': date_email,
                            'description': f"Loyer {montant}€ - {from_email}",
                            'pattern': pattern_name,
                            'confidence': 0.9,
                        })
                
                # Pour charges: un seul montant généralement
                elif pattern_name in ['charge_entretien', 'assurance', 'taxe', 'charge_copropriete', 'interet_emprunt'] and montants:
                    montant = montants[0]  # Prendre le premier montant trouvé
                    events.append({
                        'type': pattern_config['type'],
                        'montant': montant,
                        'date': date_email,
                        'description': f"{pattern_name.replace('_', ' ').title()} - {montant}€",
                        'pattern': pattern_name,
                        'confidence': 0.85,
                        'compte_charge': pattern_config.get('compte_charge'),
                    })
        
        # Si aucun pattern trouvé mais il y a des montants → comptable?
        if not events and montants:
            events.append({
                'type': 'AUTRE',
                'montant': montants[0],
                'date': date_email,
                'description': f"Événement comptable potentiel - {montants[0]}€",
                'pattern': 'montant_seul',
                'confidence': 0.5,
            })
        
        return events
    
    @staticmethod
    def _extraire_montants(text: str) -> List[float]:
        """Extrait les montants (euros, montants numériques)"""
        # Patterns: "1000€", "1000 €", "1 000€", "1,00", "1.00"
        patterns = [
            r'(\d{1,3}(?:\s?\d{3})*(?:[.,]\d{2})?)\s?€',  # avec €
            r'€\s?(\d{1,3}(?:\s?\d{3})*(?:[.,]\d{2})?)',  # € avant
            r'(\d+[.,]\d{2})\s?€?',  # décimales
        ]
        
        montants = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # Nettoyer: remplacer , par . et supprimer espaces
                montant_str = match.replace(',', '.').replace(' ', '')
                try:
                    montant = float(montant_str)
                    if 0 < montant < 1_000_000:  # Filtre raisonnable
                        montants.append(montant)
                except ValueError:
                    continue
        
        return list(set(montants))  # Dédupliquer


# ═══════════════════════════════════════════════════════════════════════════════
# ÉTAPE 2: PROCESSEUR D'ÉVÉNEMENTS (EMAIL → ÉCRITURES)
# ═══════════════════════════════════════════════════════════════════════════════

class ProcesseurEvenementsComptables:
    """
    Convertit les événements détectés en écritures comptables
    """
    
    COMPTEUR_ECRITURES = {}  # Mémoriser compteur par exercice
    
    def __init__(self, session: Session):
        self.session = session
        self.exercice_2024 = session.query(ExerciceComptable).filter_by(annee=2024).first()
        if not self.exercice_2024:
            raise ValueError("Exercice 2024 non trouvé!")
    
    def traiter_evenement(self, event: Dict, email_id: str, email_from: str, 
                         email_date: datetime) -> Tuple[bool, str, List[int]]:
        """
        Traite un événement et crée les écritures correspondantes
        
        Returns:
            (succès, message, [ids écritures créées])
        """
        try:
            type_event = event['type']
            montant = Decimal(str(event['montant']))
            description = event.get('description', 'Opération comptable')
            
            # Créer numéro écriture unique
            compteur = self.COMPTEUR_ECRITURES.get(self.exercice_2024.id, 0)
            compteur += 1
            self.COMPTEUR_ECRITURES[self.exercice_2024.id] = compteur
            numero_ecriture = f"2024-{compteur:04d}"
            
            ecriture_ids = []
            
            if type_event == 'LOYER':
                # Doublement: Débit 511 (Banques) - Crédit 701 (Loyers)
                ecriture = EcritureComptable(
                    exercice_id=self.exercice_2024.id,
                    numero_ecriture=numero_ecriture,
                    date_ecriture=event['date'],
                    libelle_ecriture=f"Encaissement loyer - {description}",
                    type_ecriture='LOYER',
                    compte_debit='511',  # Banques
                    compte_credit='701',  # Loyers
                    montant=montant,
                    source_email_id=email_id,
                    source_email_date=email_date,
                    source_email_from=email_from,
                )
                self.session.add(ecriture)
                self.session.flush()
                ecriture_ids.append(ecriture.id)
            
            elif type_event == 'CHARGE':
                # Doublement: Débit compte charge - Crédit 401 (Fournisseurs)
                compte_charge = event.get('compte_charge', '614')
                ecriture = EcritureComptable(
                    exercice_id=self.exercice_2024.id,
                    numero_ecriture=numero_ecriture,
                    date_ecriture=event['date'],
                    libelle_ecriture=f"Charge - {description}",
                    type_ecriture='CHARGE',
                    compte_debit=compte_charge,
                    compte_credit='401',  # Fournisseurs
                    montant=montant,
                    source_email_id=email_id,
                    source_email_date=email_date,
                    source_email_from=email_from,
                )
                self.session.add(ecriture)
                self.session.flush()
                ecriture_ids.append(ecriture.id)
            
            elif type_event == 'AMORTISSEMENT':
                # Traité séparément (voir calculer_amortissements)
                return True, f"Amortissement détecté (traitement spécialisé)", []
            
            else:
                return False, f"Type événement {type_event} non traité", []
            
            self.session.commit()
            return True, f"Écritures créées: {numero_ecriture}", ecriture_ids
        
        except Exception as e:
            self.session.rollback()
            return False, f"Erreur traitement: {str(e)}", []


# ═══════════════════════════════════════════════════════════════════════════════
# ÉTAPE 3: GESTIONNAIRE WORKFLOW MODULE 2
# ═══════════════════════════════════════════════════════════════════════════════

class WorkflowModule2:
    """
    Orchestre le workflow complet:
    Email (autorisé) → Détection événements → Écritures → Rapports
    """
    
    def __init__(self, database_url: str):
        self.session = get_session(database_url)
        self.detecteur = DetecteurEvenementsComptables(self.session)
        self.processeur = ProcesseurEvenementsComptables(self.session)
    
    def traiter_emails(self, emails: List[Dict]) -> Dict:
        """
        Traite une liste d'emails (issues de fetch_emails_with_auth)
        
        emails: [
            {
                'subject': '...',
                'from': '...',
                'date': '2024-10-21T10:30:00',
                'body': '...',
                'is_authorized': True,
                'action_allowed': True,
                ...
            }
        ]
        """
        rapport_module2 = {
            'nb_emails_traites': 0,
            'nb_evenements_detectes': 0,
            'nb_ecritures_creees': 0,
            'erreurs': [],
            'evenements': [],
            'ecritures_creees': [],
        }
        
        for email in emails:
            if not email.get('is_authorized') or not email.get('action_allowed'):
                continue  # Ignorer non-autorisés
            
            try:
                # Créer événement comptable EN_ATTENTE
                email_date = datetime.fromisoformat(email['date'].replace('Z', '+00:00'))
                
                evenement = EvenementComptable(
                    email_id=email.get('email_id'),
                    email_from=email['from'],
                    email_date=email_date,
                    email_subject=email.get('subject', ''),
                    email_body=email['body'],
                    statut='EN_ATTENTE',
                )
                self.session.add(evenement)
                self.session.flush()
                
                # Détecter événements
                events_detectes = self.detecteur.analyser_email(
                    email['body'],
                    email_date.date(),
                    email['from']
                )
                
                if events_detectes:
                    evenement.est_comptable = True
                    evenement.type_evenement = ','.join(e['type'] for e in events_detectes)
                    
                    # Traiter chaque événement
                    ecritures_ids = []
                    for event in events_detectes:
                        succes, msg, ecriture_ids = self.processeur.traiter_evenement(
                            event, 
                            evenement.email_id,
                            evenement.email_from,
                            evenement.email_date
                        )
                        
                        if succes:
                            ecritures_ids.extend(ecriture_ids)
                            rapport_module2['evenements'].append({
                                'type': event['type'],
                                'montant': float(event['montant']),
                                'confidence': event['confidence'],
                            })
                        else:
                            rapport_module2['erreurs'].append(msg)
                    
                    # Marquer comme VALIDÉ
                    evenement.statut = 'VALIDÉ'
                    evenement.ecritures_creees = ecritures_ids
                    rapport_module2['nb_ecritures_creees'] += len(ecritures_ids)
                
                else:
                    evenement.est_comptable = False
                
                self.session.commit()
                rapport_module2['nb_emails_traites'] += 1
                rapport_module2['nb_evenements_detectes'] += len(events_detectes)
            
            except Exception as e:
                self.session.rollback()
                rapport_module2['erreurs'].append(f"Erreur email {email.get('subject')}: {str(e)}")
        
        return rapport_module2
    
    def generer_rapports_2024(self) -> Dict:
        """
        Génère les rapports comptables 2024 (Bilan, Compte de résultat)
        """
        rapports = {
            'bilan': self._generer_bilan_2024(),
            'resultat': self._generer_resultat_2024(),
        }
        return rapports
    
    def _generer_bilan_2024(self) -> str:
        """Génère le bilan 2024 simplifié"""
        # Récupérer les soldes finaux
        ecritures = self.session.query(EcritureComptable).join(
            ExerciceComptable
        ).filter(ExerciceComptable.annee == 2024).all()
        
        # Calculer par compte
        soldes = {}
        for ec in ecritures:
            if ec.compte_debit not in soldes:
                soldes[ec.compte_debit] = {'debit': Decimal(0), 'credit': Decimal(0)}
            if ec.compte_credit not in soldes:
                soldes[ec.compte_credit] = {'debit': Decimal(0), 'credit': Decimal(0)}
            
            soldes[ec.compte_debit]['debit'] += ec.montant
            soldes[ec.compte_credit]['credit'] += ec.montant
        
        # Formater
        bilan = "BILAN SCI SOEURISE - 2024\n"
        bilan += "=" * 50 + "\n\n"
        bilan += "ACTIF\n"
        bilan += "-" * 50 + "\n"
        
        for compte_num, solde in sorted(soldes.items()):
            compte = self.session.query(PlanCompte).filter_by(numero_compte=compte_num).first()
            if compte and compte.type_compte == 'ACTIF':
                montant_net = solde['debit'] - solde['credit']
                if montant_net > 0:
                    bilan += f"{compte.numero_compte} {compte.libelle:40} {montant_net:15,.2f}\n"
        
        bilan += "\nPASSIF\n"
        bilan += "-" * 50 + "\n"
        
        for compte_num, solde in sorted(soldes.items()):
            compte = self.session.query(PlanCompte).filter_by(numero_compte=compte_num).first()
            if compte and compte.type_compte == 'PASSIF':
                montant_net = solde['credit'] - solde['debit']
                if montant_net > 0:
                    bilan += f"{compte.numero_compte} {compte.libelle:40} {montant_net:15,.2f}\n"
        
        return bilan
    
    def _generer_resultat_2024(self) -> str:
        """Génère le compte de résultat 2024"""
        ecritures = self.session.query(EcritureComptable).join(
            ExerciceComptable
        ).filter(ExerciceComptable.annee == 2024).all()
        
        # Calculer par compte
        soldes = {}
        for ec in ecritures:
            if ec.compte_debit not in soldes:
                soldes[ec.compte_debit] = {'debit': Decimal(0), 'credit': Decimal(0)}
            if ec.compte_credit not in soldes:
                soldes[ec.compte_credit] = {'debit': Decimal(0), 'credit': Decimal(0)}
            
            soldes[ec.compte_debit]['debit'] += ec.montant
            soldes[ec.compte_credit]['credit'] += ec.montant
        
        # Formater
        resultat = "COMPTE DE RÉSULTAT SCI SOEURISE - 2024\n"
        resultat += "=" * 50 + "\n\n"
        resultat += "PRODUITS\n"
        resultat += "-" * 50 + "\n"
        
        total_produits = Decimal(0)
        for compte_num, solde in sorted(soldes.items()):
            compte = self.session.query(PlanCompte).filter_by(numero_compte=compte_num).first()
            if compte and compte.type_compte == 'PRODUIT':
                montant = solde['credit'] - solde['debit']
                if montant > 0:
                    resultat += f"{compte.numero_compte} {compte.libelle:40} {montant:15,.2f}\n"
                    total_produits += montant
        
        resultat += "\nCHARGES\n"
        resultat += "-" * 50 + "\n"
        
        total_charges = Decimal(0)
        for compte_num, solde in sorted(soldes.items()):
            compte = self.session.query(PlanCompte).filter_by(numero_compte=compte_num).first()
            if compte and compte.type_compte == 'CHARGE':
                montant = solde['debit'] - solde['credit']
                if montant > 0:
                    resultat += f"{compte.numero_compte} {compte.libelle:40} {montant:15,.2f}\n"
                    total_charges += montant
        
        resultat += "\n" + "=" * 50 + "\n"
        resultat += f"RÉSULTAT EXERCICE: {total_produits - total_charges:15,.2f}\n"
        
        return resultat


# ═══════════════════════════════════════════════════════════════════════════════
# INTÉGRATION DANS main_V4.0.py
# ═══════════════════════════════════════════════════════════════════════════════

def integrer_module2_dans_reveil(emails, database_url):
    """
    À appeler DANS reveil_quotidien() de main_V4.0.py, APRÈS fetch_emails_with_auth()
    
    # Dans main_V4.0.py:
    
    def reveil_quotidien():
        emails = fetch_emails_with_auth()
        
        # ← AJOUTER ICI:
        rapport_module2 = integrer_module2_dans_reveil(emails, os.environ['DATABASE_URL'])
        
        # Inclure rapport_module2 dans le rapport quotidien...
    """
    try:
        workflow = WorkflowModule2(database_url)
        
        # Traiter les emails
        rapport = workflow.traiter_emails(emails)
        
        # Générer rapports comptables
        rapports_comptables = workflow.generer_rapports_2024()
        
        # Formater pour inclusion dans rapport quotidien
        rapport_formaté = f"""
### MODULE 2 - COMPTABILITÉ

**Emails traités:** {rapport['nb_emails_traites']}
**Événements détectés:** {rapport['nb_evenements_detectes']}
**Écritures créées:** {rapport['nb_ecritures_creees']}

#### Événements traités:
"""
        for evt in rapport['evenements']:
            rapport_formaté += f"- {evt['type']}: {evt['montant']}€ (confiance {evt['confidence']:.0%})\n"
        
        if rapport['erreurs']:
            rapport_formaté += "\n#### ⚠️ Erreurs:\n"
            for erreur in rapport['erreurs']:
                rapport_formaté += f"- {erreur}\n"
        
        rapport_formaté += "\n#### Bilan 2024:\n```\n"
        rapport_formaté += rapports_comptables['bilan']
        rapport_formaté += "\n```\n"
        
        rapport_formaté += "\n#### Compte de Résultat 2024:\n```\n"
        rapport_formaté += rapports_comptables['resultat']
        rapport_formaté += "\n```\n"
        
        return {
            'rapport': rapport_formaté,
            'data': rapport,
            'rapports_comptables': rapports_comptables
        }
    
    except Exception as e:
        return {
            'rapport': f"❌ Module 2 - Erreur: {str(e)}",
            'data': {},
            'rapports_comptables': {}
        }


if __name__ == "__main__":
    # Test
    import os
    
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("DATABASE_URL non défini!")
        exit(1)
    
    init_module2(db_url)
    
    # Exemple
    workflow = WorkflowModule2(db_url)
    print("✅ Module 2 initialisé et prêt")
