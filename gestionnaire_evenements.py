#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GESTIONNAIRE D'ÉVÉNEMENTS COMPTABLES
====================================
Gestionnaire central pour la création, classification et traitement
des événements comptables extraits des relevés bancaires.

Date: 05/11/2025
Auteur: Module Phase 1 - Accounting Events

RESPONSABILITÉS:
----------------
1. Création d'événements comptables dans la base de données
2. Calcul et enregistrement du fingerprint pour détection de doublons
3. Détection automatique du type d'événement
4. Orchestration du traitement par phases
5. Mise à jour du statut et de la phase de traitement

WORKFLOW:
---------
1. Extraction événements depuis PDF (via module externe)
2. Pour chaque événement:
   a. Calculer le fingerprint
   b. Vérifier si doublon
   c. Si nouveau: créer l'événement en BD
   d. Détecter le type d'événement
   e. Marquer avec la phase de traitement
3. Génération des propositions d'écritures (via module externe)
4. Validation et création des écritures définitives
"""

import os
from datetime import datetime, date
from typing import Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

from detection_doublons import DetecteurDoublons


class GestionnaireEvenements:
    """
    Gestionnaire central des événements comptables
    """

    def __init__(self, session: Session, phase: int = 1):
        """
        Initialise le gestionnaire

        Args:
            session: Session SQLAlchemy
            phase: Numéro de phase de traitement (1, 2, 3)
        """
        self.session = session
        self.phase = phase
        self.detecteur_doublons = DetecteurDoublons()

    def creer_evenement(self, data: Dict) -> Optional[int]:
        """
        Crée un nouvel événement comptable dans la base de données

        Args:
            data: Dictionnaire contenant:
                - date_operation (str): Date de l'opération
                - libelle (str): Libellé de l'opération
                - montant (float): Montant
                - type_operation (str): DEBIT ou CREDIT
                - email_id (str, optional): ID de l'email source
                - email_from (str, optional): Expéditeur de l'email
                - email_date (datetime, optional): Date de l'email
                - email_subject (str, optional): Sujet de l'email
                - email_body (str, optional): Corps de l'email

        Returns:
            ID de l'événement créé, ou None si doublon détecté

        Raises:
            ValueError: Si données manquantes ou invalides
        """
        # Valider les données obligatoires
        required_fields = ['date_operation', 'libelle', 'montant', 'type_operation']
        for field in required_fields:
            if field not in data or data[field] is None:
                raise ValueError(f"Champ obligatoire manquant: {field}")

        # Calculer le fingerprint
        fingerprint = self.detecteur_doublons.calculer_fingerprint(data)

        # Vérifier si doublon
        doublon = self.detecteur_doublons.verifier_doublon(self.session, data)
        if doublon:
            methode = doublon.get('methode', 'fingerprint')
            if methode == 'date_montant':
                print(f"⏭️  Doublon souple (date+montant): événement #{doublon['evenement_id']} ignoré")
            else:
                print(f"⏭️  Doublon strict (fingerprint): événement #{doublon['evenement_id']} ignoré")
            return None

        # Normaliser le libellé
        libelle_normalise = self.detecteur_doublons.normaliser_libelle(data['libelle'])

        # Préparer les données pour insertion
        insert_data = {
            'date_operation': data['date_operation'],
            'libelle': data['libelle'],
            'libelle_normalise': libelle_normalise,
            'montant': float(data['montant']),
            'type_operation': data['type_operation'],
            'fingerprint': fingerprint,
            'email_id': data.get('email_id'),
            'email_from': data.get('email_from', 'manuel'),
            'email_date': data.get('email_date', datetime.now()),
            'email_subject': data.get('email_subject'),
            'email_body': data.get('email_body', ''),
            'statut': 'EN_ATTENTE',
            'created_at': datetime.now()
        }

        # Insérer l'événement
        result = self.session.execute(
            text("""
                INSERT INTO evenements_comptables (
                    date_operation, libelle, libelle_normalise, montant, type_operation,
                    fingerprint, email_id, email_from, email_date, email_subject,
                    email_body, statut, created_at
                )
                VALUES (
                    :date_operation, :libelle, :libelle_normalise, :montant, :type_operation,
                    :fingerprint, :email_id, :email_from, :email_date, :email_subject,
                    :email_body, :statut, :created_at
                )
                RETURNING id
            """),
            insert_data
        )

        self.session.commit()
        evenement_id = result.fetchone()[0]

        print(f"✅ Événement créé: #{evenement_id} - {data['libelle'][:50]} - {data['montant']}€")
        return evenement_id

    def creer_evenements_batch(self, evenements: List[Dict]) -> Dict:
        """
        Crée plusieurs événements en batch

        Args:
            evenements: Liste de dictionnaires d'événements

        Returns:
            Dictionnaire avec statistiques:
                - total: Nombre total d'événements
                - crees: Nombre d'événements créés
                - doublons: Nombre de doublons détectés
                - erreurs: Nombre d'erreurs
                - ids_crees: Liste des IDs créés
        """
        stats = {
            'total': len(evenements),
            'crees': 0,
            'doublons': 0,
            'erreurs': 0,
            'ids_crees': []
        }

        for evt in evenements:
            try:
                evt_id = self.creer_evenement(evt)
                if evt_id:
                    stats['crees'] += 1
                    stats['ids_crees'].append(evt_id)
                else:
                    stats['doublons'] += 1
            except Exception as e:
                stats['erreurs'] += 1
                print(f"❌ Erreur création événement: {e}")
                # Rollback pour éviter "current transaction is aborted"
                self.session.rollback()

        return stats

    def detecter_type_evenement(self, evenement_id: int) -> Optional[str]:
        """
        Détecte automatiquement le type d'un événement

        Args:
            evenement_id: ID de l'événement

        Returns:
            Type d'événement détecté, ou None si non identifié

        Note:
            Cette méthode sera étendue pour utiliser les détecteurs spécialisés
            (DetecteurAssurancePret, DetecteurFraisBancaires, etc.)
        """
        # Récupérer l'événement
        result = self.session.execute(
            text("""
                SELECT libelle_normalise, montant, type_operation
                FROM evenements_comptables
                WHERE id = :id
            """),
            {'id': evenement_id}
        )

        row = result.fetchone()
        if not row:
            return None

        libelle_norm = row[0]
        montant = float(row[1])
        type_op = row[2]

        # Détection simple par patterns (sera remplacé par détecteurs spécialisés)
        type_evt = None

        # Solde d'ouverture (non comptabilisable)
        if any(pattern in libelle_norm for pattern in [
            'ancien solde', 'solde reporte', 'solde precedent', 'report solde'
        ]):
            type_evt = 'SOLDE_OUVERTURE'

        # Assurance emprunteur (DOIT être avant REMBOURSEMENT_PRET car contient "echeance")
        elif ('covea' in libelle_norm or 'assurance pret' in libelle_norm or
              'caci' in libelle_norm or 'garantie emprunteur' in libelle_norm):
            type_evt = 'ASSURANCE_PRET'

        # Frais bancaires (élargir patterns)
        elif ('frais' in libelle_norm or 'cotisation' in libelle_norm or
              'abon' in libelle_norm or 'abonnement' in libelle_norm):
            type_evt = 'FRAIS_BANCAIRES'

        # Honoraires comptable
        elif 'crp' in libelle_norm or 'comptabilit' in libelle_norm or 'expert comptable' in libelle_norm:
            type_evt = 'HONORAIRES_COMPTABLE'

        # Remboursement prêt (plus précis pour éviter confusion avec assurances)
        elif ('pret immobilier' in libelle_norm and 'ech' in libelle_norm) or 'dossier no' in libelle_norm:
            type_evt = 'REMBOURSEMENT_PRET'

        # Apport associé (élargir pour capter tous les virements Ulrik)
        elif ('vir sepa' in libelle_norm and 'bergsten' in libelle_norm) or 'apport' in libelle_norm:
            type_evt = 'APPORT_ASSOCIE'

        # Revenu SCPI
        elif 'scpi' in libelle_norm or 'epargne pierre' in libelle_norm:
            type_evt = 'REVENU_SCPI'

        # Achat ETF (nouveau)
        elif 'am msci' in libelle_norm or 'etf' in libelle_norm:
            type_evt = 'ACHAT_ETF'

        # Achat Amazon (nouveau)
        elif 'amazon' in libelle_norm and 'achat' in libelle_norm:
            type_evt = 'ACHAT_AMAZON'

        # Achat valeurs mobilières (autres)
        elif 'degiro' in libelle_norm or 'interactive brokers' in libelle_norm:
            type_evt = 'ACHAT_VALEURS_MOBILIERES'

        # Mettre à jour le type
        if type_evt:
            self.session.execute(
                text("""
                    UPDATE evenements_comptables
                    SET type_evenement = :type_evt,
                        updated_at = NOW()
                    WHERE id = :id
                """),
                {'type_evt': type_evt, 'id': evenement_id}
            )
            self.session.commit()

        return type_evt

    def marquer_phase_traitement(self, evenement_id: int, phase: int):
        """
        Marque un événement comme traité par une phase

        Args:
            evenement_id: ID de l'événement
            phase: Numéro de phase (1, 2, 3)
        """
        self.session.execute(
            text("""
                UPDATE evenements_comptables
                SET phase_traitement = :phase,
                    traite_at = NOW(),
                    updated_at = NOW()
                WHERE id = :id
            """),
            {'phase': phase, 'id': evenement_id}
        )
        self.session.commit()

    def marquer_valide(self, evenement_id: int, ecritures_ids: List[int]):
        """
        Marque un événement comme validé avec les écritures créées

        Args:
            evenement_id: ID de l'événement
            ecritures_ids: Liste des IDs des écritures créées
        """
        self.session.execute(
            text("""
                UPDATE evenements_comptables
                SET statut = 'VALIDE',
                    ecritures_creees = :ecritures_ids,
                    traite_at = NOW(),
                    updated_at = NOW()
                WHERE id = :id
            """),
            {'ecritures_ids': ecritures_ids, 'id': evenement_id}
        )
        self.session.commit()

    def marquer_erreur(self, evenement_id: int, message_erreur: str):
        """
        Marque un événement en erreur

        Args:
            evenement_id: ID de l'événement
            message_erreur: Description de l'erreur
        """
        self.session.execute(
            text("""
                UPDATE evenements_comptables
                SET statut = 'ERREUR',
                    message_erreur = :message_erreur,
                    updated_at = NOW()
                WHERE id = :id
            """),
            {'message_erreur': message_erreur, 'id': evenement_id}
        )
        self.session.commit()

    def obtenir_evenements_en_attente(self, limit: int = 100) -> List[Dict]:
        """
        Récupère les événements en attente de traitement

        Args:
            limit: Nombre maximum d'événements à récupérer

        Returns:
            Liste de dictionnaires d'événements
        """
        result = self.session.execute(
            text("""
                SELECT id, date_operation, libelle, montant, type_operation,
                       type_evenement, fingerprint
                FROM evenements_comptables
                WHERE statut = 'EN_ATTENTE'
                  AND (phase_traitement IS NULL OR phase_traitement < :phase)
                ORDER BY date_operation, id
                LIMIT :limit
            """),
            {'phase': self.phase, 'limit': limit}
        )

        evenements = []
        for row in result:
            evenements.append({
                'id': row[0],
                'date_operation': row[1],
                'libelle': row[2],
                'montant': float(row[3]) if row[3] else None,
                'type_operation': row[4],
                'type_evenement': row[5],
                'fingerprint': row[6]
            })

        return evenements

    def obtenir_statistiques(self) -> Dict:
        """
        Obtient des statistiques sur les événements

        Returns:
            Dictionnaire avec statistiques
        """
        # Compter par statut
        result = self.session.execute(text("""
            SELECT statut, COUNT(*) as nb
            FROM evenements_comptables
            GROUP BY statut
        """))
        stats_statut = {row[0]: row[1] for row in result}

        # Compter par phase
        result = self.session.execute(text("""
            SELECT phase_traitement, COUNT(*) as nb
            FROM evenements_comptables
            WHERE phase_traitement IS NOT NULL
            GROUP BY phase_traitement
        """))
        stats_phase = {f"Phase {row[0]}": row[1] for row in result}

        # Compter par type
        result = self.session.execute(text("""
            SELECT type_evenement, COUNT(*) as nb
            FROM evenements_comptables
            WHERE type_evenement IS NOT NULL
            GROUP BY type_evenement
        """))
        stats_type = {row[0]: row[1] for row in result}

        # Total
        result = self.session.execute(text("""
            SELECT COUNT(*) FROM evenements_comptables
        """))
        total = result.fetchone()[0]

        return {
            'total': total,
            'par_statut': stats_statut,
            'par_phase': stats_phase,
            'par_type': stats_type
        }


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def afficher_statistiques(gestionnaire: GestionnaireEvenements):
    """Affiche les statistiques de manière formatée"""
    stats = gestionnaire.obtenir_statistiques()

    print("=" * 80)
    print("STATISTIQUES ÉVÉNEMENTS COMPTABLES")
    print("=" * 80)
    print()
    print(f"📊 Total événements: {stats['total']}")
    print()

    if stats['par_statut']:
        print("Par statut:")
        for statut, count in stats['par_statut'].items():
            print(f"  - {statut}: {count}")
        print()

    if stats['par_phase']:
        print("Par phase:")
        for phase, count in stats['par_phase'].items():
            print(f"  - {phase}: {count}")
        print()

    if stats['par_type']:
        print("Par type:")
        for type_evt, count in stats['par_type'].items():
            print(f"  - {type_evt}: {count}")
        print()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN (TESTS)
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("=" * 80)
    print("GESTIONNAIRE D'ÉVÉNEMENTS - Module de test")
    print("=" * 80)
    print()
    print("Ce module doit être importé et utilisé par d'autres modules.")
    print("Pour tester, utiliser le module de traitement principal.")
    print()
