#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAPPROCHEUR AUTOMATIQUE DE CUT-OFFS
====================================
Module pour détecter et solder automatiquement les créances/dettes
lors de leur encaissement/paiement effectif.

CONTEXTE:
---------
En comptabilité d'engagement, les produits/charges sont comptabilisés
dans l'exercice où ils sont acquis, indépendamment de l'encaissement/paiement.

En fin d'année:
1. Produits acquis non encore encaissés → Compte 4181 "Produits à recevoir"
2. Charges engagées non encore payées → Compte 408 "Factures non parvenues"

Début d'année suivante:
- Encaissement du produit → Solder la créance (Débit 512 / Crédit 4181)
- Paiement de la charge → Solder la dette (Débit 408 / Crédit 512)

Ce module détecte automatiquement qu'une opération correspond à
une créance/dette existante et génère l'écriture de soldage appropriée
au lieu de créer un nouveau produit/charge.

EXEMPLE:
--------
31/12/2023: Revenus SCPI T4 à recevoir
  Débit 4181 : 7 356 €
  Crédit 761 : 7 356 €

29/01/2024: Encaissement SCPI (avec rapprochement)
  Débit 512 : 7 356 €
  Crédit 4181 : 7 356 € ← Solde la créance (au lieu de créer nouveau 761)

Date: 18/11/2025
Auteur: _Head.Soeurise
"""

import psycopg2
from typing import Dict, List, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import text


# ═══════════════════════════════════════════════════════════════════════════════
# CLASSE PRINCIPALE
# ═══════════════════════════════════════════════════════════════════════════════

class RapprocheurCutoff:
    """
    Rapprocheur automatique de cut-offs comptables
    """

    def __init__(self, session: Session):
        """
        Initialise le rapprocheur

        Args:
            session: Session SQLAlchemy
        """
        self.session = session

    # ───────────────────────────────────────────────────────────────────────
    # RECHERCHE DE CRÉANCES (Produits à recevoir)
    # ───────────────────────────────────────────────────────────────────────

    def chercher_creance(
        self,
        montant: float,
        exercice_id: Optional[int] = None,
        tolerance_montant: float = 2.0,
        tolerance_pourcentage: float = 0.02
    ) -> Optional[Dict]:
        """
        Cherche une créance (compte 4181) existante correspondant au montant

        Args:
            montant: Montant encaissé à rapprocher
            exercice_id: ID exercice où chercher (si None, cherche exercice précédent)
            tolerance_montant: Tolérance absolue en euros (défaut: 2€)
            tolerance_pourcentage: Tolérance relative en % (défaut: 2%)

        Returns:
            Dictionnaire avec info créance trouvée, ou None si aucune
            {
                'id': ID écriture,
                'date_ecriture': Date écriture,
                'montant': Montant créance,
                'libelle': Libellé écriture,
                'exercice_id': ID exercice,
                'ecart': Écart en euros,
                'ecart_pourcent': Écart en %
            }

        LOGIQUE:
        --------
        1. Cherche écritures avec compte_debit = 4181 (créances)
        2. Filtre exercice précédent (si non spécifié)
        3. Vérifie que montant dans tolérance (absolue ET relative)
        4. Vérifie que créance non encore soldée (pas de crédit 4181 correspondant)
        5. Retourne la créance la plus proche en montant

        TOLÉRANCE:
        ----------
        Créance acceptée si:
        - Écart absolu <= tolerance_montant (défaut 2€)
        - OU Écart relatif <= tolerance_pourcentage (défaut 2%)

        Exemple:
        - Créance: 7 356 € | Paiement: 7 360 € → Écart 4€ (0.05%) → ACCEPTÉ
        - Créance: 7 356 € | Paiement: 7 500 € → Écart 144€ (1.96%) → REFUSÉ
        """
        # Déterminer l'exercice où chercher
        if exercice_id is None:
            # Chercher dans l'exercice précédent l'exercice courant
            query_exercice = text("""
                SELECT id
                FROM exercices_comptables
                WHERE date_fin < (
                    SELECT date_debut
                    FROM exercices_comptables
                    WHERE statut = 'OUVERT'
                    ORDER BY date_debut DESC
                    LIMIT 1
                )
                ORDER BY date_fin DESC
                LIMIT 1
            """)
            result = self.session.execute(query_exercice).fetchone()
            if not result:
                return None
            exercice_id = result[0]

        # Calculer bornes de tolérance
        borne_inf = montant - tolerance_montant
        borne_sup = montant + tolerance_montant
        tolerance_pourcent_abs = montant * tolerance_pourcentage

        # Chercher créances existantes non soldées
        query = text("""
            SELECT
                e.id,
                e.date_ecriture,
                e.montant,
                e.libelle_ecriture,
                e.exercice_id,
                ABS(e.montant - :montant) as ecart_absolu,
                ABS((e.montant - :montant) / e.montant * 100) as ecart_pourcent
            FROM ecritures_comptables e
            WHERE e.compte_debit = '4181'
              AND e.exercice_id = :exercice_id
              AND (
                  -- Tolérance absolue
                  ABS(e.montant - :montant) <= :tolerance_montant
                  -- OU Tolérance relative
                  OR ABS((e.montant - :montant) / e.montant) <= :tolerance_pourcentage
              )
              -- Vérifier que pas déjà soldée
              AND NOT EXISTS (
                  SELECT 1
                  FROM ecritures_comptables e2
                  WHERE e2.compte_credit = '4181'
                    AND ABS(e2.montant - e.montant) < 0.01
                    AND e2.date_ecriture >= e.date_ecriture
              )
            ORDER BY ABS(e.montant - :montant)
            LIMIT 1
        """)

        result = self.session.execute(
            query,
            {
                'montant': montant,
                'exercice_id': exercice_id,
                'tolerance_montant': tolerance_montant,
                'tolerance_pourcentage': tolerance_pourcentage
            }
        ).fetchone()

        if not result:
            return None

        # Convertir en dictionnaire
        return {
            'id': result[0],
            'date_ecriture': result[1],
            'montant': float(result[2]),
            'libelle': result[3],
            'exercice_id': result[4],
            'ecart': float(result[5]),
            'ecart_pourcent': float(result[6])
        }

    # ───────────────────────────────────────────────────────────────────────
    # RECHERCHE DE DETTES (Factures non parvenues)
    # ───────────────────────────────────────────────────────────────────────

    def chercher_dette(
        self,
        montant: float,
        exercice_id: Optional[int] = None,
        tolerance_montant: float = 2.0,
        tolerance_pourcentage: float = 0.02
    ) -> Optional[Dict]:
        """
        Cherche une dette (compte 408) existante correspondant au montant

        Args:
            montant: Montant payé à rapprocher
            exercice_id: ID exercice où chercher (si None, cherche exercice précédent)
            tolerance_montant: Tolérance absolue en euros (défaut: 2€)
            tolerance_pourcentage: Tolérance relative en % (défaut: 2%)

        Returns:
            Dictionnaire avec info dette trouvée, ou None si aucune

        LOGIQUE:
        --------
        Similaire à chercher_creance() mais pour compte 408 (factures non parvenues)
        """
        # Déterminer l'exercice où chercher
        if exercice_id is None:
            query_exercice = text("""
                SELECT id
                FROM exercices_comptables
                WHERE date_fin < (
                    SELECT date_debut
                    FROM exercices_comptables
                    WHERE statut = 'OUVERT'
                    ORDER BY date_debut DESC
                    LIMIT 1
                )
                ORDER BY date_fin DESC
                LIMIT 1
            """)
            result = self.session.execute(query_exercice).fetchone()
            if not result:
                return None
            exercice_id = result[0]

        # Chercher dettes existantes non soldées
        query = text("""
            SELECT
                e.id,
                e.date_ecriture,
                e.montant,
                e.libelle_ecriture,
                e.exercice_id,
                ABS(e.montant - :montant) as ecart_absolu,
                ABS((e.montant - :montant) / e.montant * 100) as ecart_pourcent
            FROM ecritures_comptables e
            WHERE e.compte_credit = '408'
              AND e.exercice_id = :exercice_id
              AND (
                  ABS(e.montant - :montant) <= :tolerance_montant
                  OR ABS((e.montant - :montant) / e.montant) <= :tolerance_pourcentage
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM ecritures_comptables e2
                  WHERE e2.compte_debit = '408'
                    AND ABS(e2.montant - e.montant) < 0.01
                    AND e2.date_ecriture >= e.date_ecriture
              )
            ORDER BY ABS(e.montant - :montant)
            LIMIT 1
        """)

        result = self.session.execute(
            query,
            {
                'montant': montant,
                'exercice_id': exercice_id,
                'tolerance_montant': tolerance_montant,
                'tolerance_pourcentage': tolerance_pourcentage
            }
        ).fetchone()

        if not result:
            return None

        return {
            'id': result[0],
            'date_ecriture': result[1],
            'montant': float(result[2]),
            'libelle': result[3],
            'exercice_id': result[4],
            'ecart': float(result[5]),
            'ecart_pourcent': float(result[6])
        }

    # ───────────────────────────────────────────────────────────────────────
    # GÉNÉRATION ÉCRITURES DE SOLDAGE
    # ───────────────────────────────────────────────────────────────────────

    def generer_ecriture_soldage_creance(
        self,
        creance: Dict,
        montant_encaisse: float,
        date_encaissement: str,
        libelle_base: str = "SCPI Épargne Pierre"
    ) -> List[Dict]:
        """
        Génère les écritures de soldage d'une créance (produit à recevoir)

        Args:
            creance: Dictionnaire retourné par chercher_creance()
            montant_encaisse: Montant réellement encaissé
            date_encaissement: Date encaissement (format YYYY-MM-DD)
            libelle_base: Libellé de base pour l'écriture

        Returns:
            Liste d'écritures à créer:
            - Si montant exact: 1 écriture de soldage
            - Si écart: 2 écritures (soldage + ajustement)

        CAS 1: Montant exact (ou écart < 0.01€)
        ----------------------------------------
        Créance: 7 356 € | Encaissement: 7 356 €
        → 1 écriture:
            Débit 512 Banque           7 356 €
            Crédit 4181 Produits       7 356 €

        CAS 2: Écart positif (encaissement > créance)
        ----------------------------------------------
        Créance: 7 356 € | Encaissement: 7 360 € (écart +4€)
        → 2 écritures:
            1. Soldage:
               Débit 512 Banque        7 356 €
               Crédit 4181 Produits    7 356 €

            2. Ajustement:
               Débit 512 Banque        4 €
               Crédit 761 Revenus      4 €
               Libellé: "Ajustement revenus T4 (écart annonce/réel)"

        CAS 3: Écart négatif (encaissement < créance)
        ----------------------------------------------
        Créance: 7 356 € | Encaissement: 7 350 € (écart -6€)
        → 2 écritures:
            1. Soldage:
               Débit 512 Banque        7 350 €
               Crédit 4181 Produits    7 350 €

            2. Ajustement:
               Débit 6XX Charge        6 €
               Crédit 4181 Produits    6 €
               Libellé: "Correction produit à recevoir (écart annonce/réel)"
        """
        ecritures = []
        ecart = montant_encaisse - creance['montant']

        # Écriture 1: Soldage de la créance (montant min)
        montant_soldage = min(montant_encaisse, creance['montant'])

        ecritures.append({
            'date_ecriture': date_encaissement,
            'libelle_ecriture': f'{libelle_base} - Encaissement revenus T4 (soldage créance)',
            'compte_debit': '512',
            'compte_credit': '4181',
            'montant': montant_soldage,
            'type_ecriture': 'ENCAISSEMENT_PRODUIT_A_RECEVOIR',
            'notes': f'Solde créance ID {creance["id"]} du {creance["date_ecriture"]}'
        })

        # Écriture 2: Ajustement si écart significatif (> 0.01€)
        if abs(ecart) > 0.01:
            if ecart > 0:
                # Encaissement supérieur → Produit complémentaire
                ecritures.append({
                    'date_ecriture': date_encaissement,
                    'libelle_ecriture': f'{libelle_base} - Ajustement revenus T4 (écart annonce/réel: +{ecart:.2f}€)',
                    'compte_debit': '512',
                    'compte_credit': '761',
                    'montant': abs(ecart),
                    'type_ecriture': 'AJUSTEMENT_PRODUIT_A_RECEVOIR',
                    'notes': f'Complément par rapport à annonce ({creance["montant"]:.2f}€)'
                })
            else:
                # Encaissement inférieur → Correction créance
                ecritures.append({
                    'date_ecriture': date_encaissement,
                    'libelle_ecriture': f'{libelle_base} - Correction produit à recevoir (écart annonce/réel: {ecart:.2f}€)',
                    'compte_debit': '6788',  # Charges exceptionnelles diverses
                    'compte_credit': '4181',
                    'montant': abs(ecart),
                    'type_ecriture': 'CORRECTION_PRODUIT_A_RECEVOIR',
                    'notes': f'Réduction par rapport à annonce ({creance["montant"]:.2f}€)'
                })

        return ecritures

    def generer_ecriture_soldage_dette(
        self,
        dette: Dict,
        montant_paye: float,
        date_paiement: str,
        libelle_base: str = "Honoraires comptables"
    ) -> List[Dict]:
        """
        Génère les écritures de soldage d'une dette (facture non parvenue)

        Args:
            dette: Dictionnaire retourné par chercher_dette()
            montant_paye: Montant réellement payé
            date_paiement: Date paiement (format YYYY-MM-DD)
            libelle_base: Libellé de base pour l'écriture

        Returns:
            Liste d'écritures à créer

        LOGIQUE:
        --------
        Similaire à generer_ecriture_soldage_creance() mais inversé
        (débit 408 / crédit 512 pour soldage)
        """
        ecritures = []
        ecart = montant_paye - dette['montant']

        # Écriture 1: Soldage de la dette
        montant_soldage = min(montant_paye, dette['montant'])

        ecritures.append({
            'date_ecriture': date_paiement,
            'libelle_ecriture': f'{libelle_base} - Paiement (soldage dette)',
            'compte_debit': '408',
            'compte_credit': '512',
            'montant': montant_soldage,
            'type_ecriture': 'PAIEMENT_FACTURE_NON_PARVENUE',
            'notes': f'Solde dette ID {dette["id"]} du {dette["date_ecriture"]}'
        })

        # Écriture 2: Ajustement si écart
        if abs(ecart) > 0.01:
            if ecart > 0:
                # Paiement supérieur → Charge complémentaire
                ecritures.append({
                    'date_ecriture': date_paiement,
                    'libelle_ecriture': f'{libelle_base} - Complément (écart annonce/réel: +{ecart:.2f}€)',
                    'compte_debit': '6226',  # Honoraires (ou autre compte charge selon nature)
                    'compte_credit': '512',
                    'montant': abs(ecart),
                    'type_ecriture': 'AJUSTEMENT_FACTURE_NON_PARVENUE',
                    'notes': f'Complément par rapport à provision ({dette["montant"]:.2f}€)'
                })
            else:
                # Paiement inférieur → Correction dette
                ecritures.append({
                    'date_ecriture': date_paiement,
                    'libelle_ecriture': f'{libelle_base} - Correction provision (écart: {ecart:.2f}€)',
                    'compte_debit': '408',
                    'compte_credit': '7788',  # Produits exceptionnels divers
                    'montant': abs(ecart),
                    'type_ecriture': 'CORRECTION_FACTURE_NON_PARVENUE',
                    'notes': f'Réduction par rapport à provision ({dette["montant"]:.2f}€)'
                })

        return ecritures

    # ───────────────────────────────────────────────────────────────────────
    # RAPPROCHEMENT AUTOMATIQUE (High-level)
    # ───────────────────────────────────────────────────────────────────────

    def rapprocher_encaissement(
        self,
        montant: float,
        date_operation: str,
        libelle: str = "SCPI Épargne Pierre",
        tolerance_montant: float = 2.0,
        tolerance_pourcentage: float = 0.02
    ) -> Optional[Dict]:
        """
        Tente de rapprocher un encaissement avec une créance existante

        Args:
            montant: Montant encaissé
            date_operation: Date encaissement
            libelle: Libellé pour écritures générées
            tolerance_montant: Tolérance absolue (€)
            tolerance_pourcentage: Tolérance relative (%)

        Returns:
            Proposition d'écritures si créance trouvée, None sinon
            {
                'type_evenement': 'ENCAISSEMENT_PRODUIT_A_RECEVOIR',
                'description': '...',
                'confiance': 0.95,
                'ecritures': [...],
                'metadata': {
                    'creance_id': ID créance soldée,
                    'creance_montant': Montant initial créance,
                    'ecart': Écart constaté
                }
            }
        """
        # Chercher créance correspondante
        creance = self.chercher_creance(
            montant=montant,
            tolerance_montant=tolerance_montant,
            tolerance_pourcentage=tolerance_pourcentage
        )

        if not creance:
            return None

        # Générer écritures de soldage
        ecritures = self.generer_ecriture_soldage_creance(
            creance=creance,
            montant_encaisse=montant,
            date_encaissement=date_operation,
            libelle_base=libelle
        )

        # Construire proposition
        ecart = montant - creance['montant']
        description = f"Encaissement {libelle} (soldage créance"
        if abs(ecart) > 0.01:
            description += f", écart {ecart:+.2f}€"
        description += ")"

        return {
            'type_evenement': 'ENCAISSEMENT_PRODUIT_A_RECEVOIR',
            'description': description,
            'confiance': 0.95,
            'ecritures': ecritures,
            'metadata': {
                'creance_id': creance['id'],
                'creance_montant': creance['montant'],
                'creance_date': str(creance['date_ecriture']),
                'ecart': ecart,
                'ecart_pourcent': creance['ecart_pourcent']
            }
        }

    def rapprocher_paiement(
        self,
        montant: float,
        date_operation: str,
        libelle: str = "Honoraires comptables",
        tolerance_montant: float = 2.0,
        tolerance_pourcentage: float = 0.02
    ) -> Optional[Dict]:
        """
        Tente de rapprocher un paiement avec une dette existante

        Args:
            montant: Montant payé
            date_operation: Date paiement
            libelle: Libellé pour écritures générées
            tolerance_montant: Tolérance absolue (€)
            tolerance_pourcentage: Tolérance relative (%)

        Returns:
            Proposition d'écritures si dette trouvée, None sinon
        """
        # Chercher dette correspondante
        dette = self.chercher_dette(
            montant=montant,
            tolerance_montant=tolerance_montant,
            tolerance_pourcentage=tolerance_pourcentage
        )

        if not dette:
            return None

        # Générer écritures de soldage
        ecritures = self.generer_ecriture_soldage_dette(
            dette=dette,
            montant_paye=montant,
            date_paiement=date_operation,
            libelle_base=libelle
        )

        # Construire proposition
        ecart = montant - dette['montant']
        description = f"Paiement {libelle} (soldage dette"
        if abs(ecart) > 0.01:
            description += f", écart {ecart:+.2f}€"
        description += ")"

        return {
            'type_evenement': 'PAIEMENT_FACTURE_NON_PARVENUE',
            'description': description,
            'confiance': 0.95,
            'ecritures': ecritures,
            'metadata': {
                'dette_id': dette['id'],
                'dette_montant': dette['montant'],
                'dette_date': str(dette['date_ecriture']),
                'ecart': ecart,
                'ecart_pourcent': dette['ecart_pourcent']
            }
        }


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_rapprocheur():
    """Tests unitaires du rapprocheur (à exécuter avec vraie BD)"""
    print("=" * 80)
    print("TESTS RAPPROCHEUR CUTOFF")
    print("=" * 80)
    print()

    # Note: Tests nécessitent connexion BD réelle
    # TODO: Implémenter tests avec fixtures

    print("✅ Module chargé avec succès")
    print()


if __name__ == '__main__':
    test_rapprocheur()
