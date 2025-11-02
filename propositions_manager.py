#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MODULE 2 - GESTIONNAIRE PROPOSITIONS EN ATTENTE
================================================
Gère le stockage et la récupération des propositions d'écritures comptables
en attente de validation.

Permet la validation par token uniquement (sans renvoyer le JSON complet).
"""

import hashlib
import json
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from models_module2 import PropositionEnAttente


# ═══════════════════════════════════════════════════════════════════════════════
# GESTIONNAIRE PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class PropositionsManager:
    """
    Gère le stockage et la récupération des propositions en attente de validation
    """

    def __init__(self, session: Session):
        self.session = session

    # ═══════════════════════════════════════════════════════════════════════════
    # GÉNÉRATION TOKEN
    # ═══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def generer_token_securise(propositions: List[Dict]) -> str:
        """
        Génère un token sécurisé pour les propositions

        Args:
            propositions: Liste des propositions d'écritures

        Returns:
            Token unique (format: PREFIX-HASH8)
            Exemple: HEAD-A3F2B9D1
        """
        # Générer hash MD5 des propositions
        hash_md5 = hashlib.md5(
            json.dumps(propositions, sort_keys=True).encode()
        ).hexdigest()[:8].upper()

        # Ajouter préfixe pour identification facile
        return f"HEAD-{hash_md5}"

    @staticmethod
    def generer_token_aleatoire() -> str:
        """
        Génère un token complètement aléatoire (fallback)

        Returns:
            Token aléatoire (format: HEAD-XXXXXXXX)
        """
        random_hex = secrets.token_hex(4).upper()
        return f"HEAD-{random_hex}"

    # ═══════════════════════════════════════════════════════════════════════════
    # STOCKAGE PROPOSITIONS
    # ═══════════════════════════════════════════════════════════════════════════

    def stocker_proposition(
        self,
        type_evenement: str,
        propositions: List[Dict],
        email_id: Optional[str] = None,
        email_from: Optional[str] = None,
        email_date: Optional[datetime] = None,
        email_subject: Optional[str] = None,
        token: Optional[str] = None
    ) -> Tuple[str, int]:
        """
        Stocke une proposition en base de données

        Args:
            type_evenement: Type d'événement (LOYER, CHARGE, INIT_BILAN_2023, etc.)
            propositions: Liste des propositions d'écritures
            email_id: ID de l'email source (optionnel)
            email_from: Expéditeur de l'email (optionnel)
            email_date: Date de l'email (optionnel)
            email_subject: Sujet de l'email (optionnel)
            token: Token personnalisé (optionnel, sinon généré automatiquement)

        Returns:
            (token, proposition_id)
        """

        # Générer token si non fourni
        if not token:
            token = self.generer_token_securise(propositions)

        # Vérifier si le token existe déjà
        existing = self.session.query(PropositionEnAttente).filter_by(token=token).first()
        if existing:
            # Token existe déjà, générer un nouveau token aléatoire
            token = self.generer_token_aleatoire()

        # Créer la proposition
        proposition = PropositionEnAttente(
            token=token,
            type_evenement=type_evenement,
            email_id=email_id,
            email_from=email_from,
            email_date=email_date,
            email_subject=email_subject,
            propositions_json={"propositions": propositions},
            statut="EN_ATTENTE",
            created_at=datetime.utcnow()
        )

        self.session.add(proposition)
        self.session.commit()

        return token, proposition.id

    # ═══════════════════════════════════════════════════════════════════════════
    # RÉCUPÉRATION PROPOSITIONS
    # ═══════════════════════════════════════════════════════════════════════════

    def recuperer_proposition(self, token: str) -> Optional[Dict]:
        """
        Récupère une proposition par son token

        Args:
            token: Token de la proposition (ex: HEAD-A3F2B9D1)

        Returns:
            {
                'id': int,
                'token': str,
                'type_evenement': str,
                'propositions': [...],
                'statut': str,
                'email_from': str,
                'created_at': datetime
            }
            ou None si non trouvée
        """

        # Normaliser le token selon le format
        token = token.strip()

        # Déterminer le format du token :
        # - Si 32 caractères hexadécimaux → MD5 complet (format workflow v2)
        # - Sinon → Token court avec préfixe HEAD-

        if len(token) == 32 and all(c in '0123456789abcdefABCDEF' for c in token):
            # MD5 complet : normaliser en lowercase (format BD)
            token = token.lower()
        else:
            # Token court : mettre en majuscules et ajouter HEAD- si nécessaire
            token = token.upper()
            if not token.startswith("HEAD-"):
                token = f"HEAD-{token}"

        # Chercher la proposition
        proposition = self.session.query(PropositionEnAttente).filter_by(token=token).first()

        if not proposition:
            return None

        return {
            'id': proposition.id,
            'token': proposition.token,
            'type_evenement': proposition.type_evenement,
            'propositions': proposition.propositions_json.get('propositions', []),
            'statut': proposition.statut,
            'email_from': proposition.email_from,
            'email_subject': proposition.email_subject,
            'created_at': proposition.created_at,
            'validee_at': proposition.validee_at
        }

    def recuperer_propositions_en_attente(self, limit: int = 50) -> List[Dict]:
        """
        Récupère toutes les propositions en attente

        Args:
            limit: Nombre maximum de propositions à récupérer

        Returns:
            Liste de propositions
        """

        propositions = (
            self.session.query(PropositionEnAttente)
            .filter_by(statut='EN_ATTENTE')
            .order_by(PropositionEnAttente.created_at.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                'id': p.id,
                'token': p.token,
                'type_evenement': p.type_evenement,
                'propositions': p.propositions_json.get('propositions', []),
                'email_from': p.email_from,
                'created_at': p.created_at
            }
            for p in propositions
        ]

    # ═══════════════════════════════════════════════════════════════════════════
    # VALIDATION PROPOSITIONS
    # ═══════════════════════════════════════════════════════════════════════════

    def valider_proposition(
        self,
        token: str,
        validee_par: Optional[str] = None,
        notes: Optional[str] = None
    ) -> bool:
        """
        Marque une proposition comme validée

        Args:
            token: Token de la proposition
            validee_par: Email de la personne qui valide (optionnel)
            notes: Notes de validation (optionnel)

        Returns:
            True si validée avec succès, False sinon
        """

        # Normaliser le token selon le format
        token = token.strip()

        if len(token) == 32 and all(c in '0123456789abcdefABCDEF' for c in token):
            # MD5 complet : normaliser en lowercase
            token = token.lower()
        else:
            # Token court : mettre en majuscules et ajouter HEAD- si nécessaire
            token = token.upper()
            if not token.startswith("HEAD-"):
                token = f"HEAD-{token}"

        # Chercher la proposition
        proposition = self.session.query(PropositionEnAttente).filter_by(token=token).first()

        if not proposition:
            return False

        # Marquer comme validée
        proposition.statut = "VALIDEE"
        proposition.validee_at = datetime.utcnow()
        proposition.validee_par = validee_par
        if notes:
            proposition.notes = notes

        self.session.commit()
        return True

    def rejeter_proposition(
        self,
        token: str,
        raison: Optional[str] = None
    ) -> bool:
        """
        Marque une proposition comme rejetée

        Args:
            token: Token de la proposition
            raison: Raison du rejet (optionnel)

        Returns:
            True si rejetée avec succès, False sinon
        """

        # Normaliser le token selon le format
        token = token.strip()

        if len(token) == 32 and all(c in '0123456789abcdefABCDEF' for c in token):
            # MD5 complet : normaliser en lowercase
            token = token.lower()
        else:
            # Token court : mettre en majuscules et ajouter HEAD- si nécessaire
            token = token.upper()
            if not token.startswith("HEAD-"):
                token = f"HEAD-{token}"

        # Chercher la proposition
        proposition = self.session.query(PropositionEnAttente).filter_by(token=token).first()

        if not proposition:
            return False

        # Marquer comme rejetée
        proposition.statut = "REJETEE"
        proposition.validee_at = datetime.utcnow()
        if raison:
            proposition.notes = raison

        self.session.commit()
        return True

    # ═══════════════════════════════════════════════════════════════════════════
    # NETTOYAGE
    # ═══════════════════════════════════════════════════════════════════════════

    def nettoyer_propositions_expirees(self, jours: int = 30) -> int:
        """
        Supprime ou marque comme expirées les propositions anciennes

        Args:
            jours: Âge minimum en jours pour considérer une proposition comme expirée

        Returns:
            Nombre de propositions nettoyées
        """

        date_limite = datetime.utcnow() - timedelta(days=jours)

        # Marquer comme expirées les propositions en attente anciennes
        propositions_expirees = (
            self.session.query(PropositionEnAttente)
            .filter_by(statut='EN_ATTENTE')
            .filter(PropositionEnAttente.created_at < date_limite)
            .all()
        )

        count = 0
        for prop in propositions_expirees:
            prop.statut = "EXPIREE"
            prop.notes = f"Expirée automatiquement après {jours} jours"
            count += 1

        self.session.commit()
        return count

    # ═══════════════════════════════════════════════════════════════════════════
    # STATISTIQUES
    # ═══════════════════════════════════════════════════════════════════════════

    def statistiques(self) -> Dict:
        """
        Retourne des statistiques sur les propositions

        Returns:
            {
                'en_attente': int,
                'validees': int,
                'rejetees': int,
                'expirees': int,
                'total': int
            }
        """

        from sqlalchemy import func

        stats = (
            self.session.query(
                PropositionEnAttente.statut,
                func.count(PropositionEnAttente.id)
            )
            .group_by(PropositionEnAttente.statut)
            .all()
        )

        result = {
            'en_attente': 0,
            'validees': 0,
            'rejetees': 0,
            'expirees': 0,
            'total': 0
        }

        for statut, count in stats:
            if statut == 'EN_ATTENTE':
                result['en_attente'] = count
            elif statut == 'VALIDEE':
                result['validees'] = count
            elif statut == 'REJETEE':
                result['rejetees'] = count
            elif statut == 'EXPIREE':
                result['expirees'] = count
            result['total'] += count

        return result


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = ['PropositionsManager']
