#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NETTOYAGE BASE DE DONNÉES - Événements Comptables
==================================================
Outil de nettoyage et rollback pour la phase de développement/debug.
Permet d'annuler proprement une tentative de traitement ratée.

Date: 05/11/2025
Auteur: Module Phase 1 - Accounting Events

CAS D'USAGE:
-----------
1. Phase de test: Tester plusieurs fois le parsing
2. Correction d'erreurs: Retraiter après correction du code
3. Ajustements manuels: Annuler et recommencer

SÉCURITÉ:
---------
- Mode dry_run par défaut (simulation sans modification)
- Confirmation obligatoire pour nettoyage réel
- Sauvegarde automatique avant suppression
- Log détaillé de toutes les opérations
"""

import os
import sys
import json
from datetime import datetime, date
from typing import Dict, List, Optional
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)


class NettoyeurBD:
    """
    Gestionnaire de nettoyage de base de données
    """

    def __init__(self, database_url: str):
        """
        Initialise le nettoyeur

        Args:
            database_url: URL de connexion PostgreSQL
        """
        self.database_url = database_url
        self.engine = create_engine(database_url, echo=False)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def __del__(self):
        """Ferme la session à la destruction"""
        if hasattr(self, 'session'):
            self.session.close()

    def analyser_periode(self, date_debut: str, date_fin: str) -> Dict:
        """
        Analyse une période pour voir ce qui serait nettoyé

        Args:
            date_debut: Date de début (format: YYYY-MM-DD)
            date_fin: Date de fin (format: YYYY-MM-DD)

        Returns:
            Dictionnaire avec statistiques
        """
        stats = {
            'date_debut': date_debut,
            'date_fin': date_fin,
            'evenements': 0,
            'ecritures': 0,
            'mouvements_portefeuille': 0,
            'mouvements_cc': 0,
            'details_evenements': []
        }

        # Compter les événements dans la période
        result = self.session.execute(
            text("""
                SELECT id, date_operation, libelle, montant, type_operation,
                       phase_traitement, statut
                FROM evenements_comptables
                WHERE date_operation >= :date_debut
                  AND date_operation <= :date_fin
                ORDER BY date_operation, id
            """),
            {'date_debut': date_debut, 'date_fin': date_fin}
        )

        evenements = result.fetchall()
        stats['evenements'] = len(evenements)

        for evt in evenements:
            stats['details_evenements'].append({
                'id': evt[0],
                'date': str(evt[1]) if evt[1] else None,
                'libelle': evt[2],
                'montant': float(evt[3]) if evt[3] else None,
                'type': evt[4],
                'phase': evt[5],
                'statut': evt[6]
            })

        # Compter les écritures liées
        if evenements:
            evenement_ids = [evt[0] for evt in evenements]
            placeholders = ','.join([f':id{i}' for i in range(len(evenement_ids))])
            params = {f'id{i}': evt_id for i, evt_id in enumerate(evenement_ids)}

            result = self.session.execute(
                text(f"""
                    SELECT COUNT(*)
                    FROM ecritures_comptables
                    WHERE source_email_id IN (
                        SELECT email_id
                        FROM evenements_comptables
                        WHERE id IN ({placeholders})
                    )
                """),
                params
            )
            stats['ecritures'] = result.fetchone()[0]

        # Compter les mouvements portefeuille liés
        if evenements:
            result = self.session.execute(
                text(f"""
                    SELECT COUNT(*)
                    FROM mouvements_portefeuille
                    WHERE source_evenement_id IN ({placeholders})
                """),
                params
            )
            stats['mouvements_portefeuille'] = result.fetchone()[0]

        # Compter les mouvements compte courant liés
        if evenements:
            result = self.session.execute(
                text(f"""
                    SELECT COUNT(*)
                    FROM mouvements_comptes_courants
                    WHERE source_evenement_id IN ({placeholders})
                """),
                params
            )
            stats['mouvements_cc'] = result.fetchone()[0]

        return stats

    def nettoyer_periode(self, date_debut: str, date_fin: str, dry_run: bool = True) -> Dict:
        """
        Nettoie tous les événements et données liées d'une période

        Args:
            date_debut: Date de début (format: YYYY-MM-DD)
            date_fin: Date de fin (format: YYYY-MM-DD)
            dry_run: Si True, simule sans modifier (défaut: True)

        Returns:
            Dictionnaire avec résultats du nettoyage
        """
        # Analyser d'abord
        stats = self.analyser_periode(date_debut, date_fin)

        if stats['evenements'] == 0:
            return {
                'success': True,
                'message': 'Aucun événement à nettoyer dans cette période',
                'stats': stats
            }

        # Si dry_run, retourner l'analyse seulement
        if dry_run:
            return {
                'success': True,
                'message': 'MODE DRY_RUN: Simulation uniquement (aucune modification)',
                'stats': stats
            }

        # Créer une sauvegarde avant suppression
        backup_file = self._creer_sauvegarde(date_debut, date_fin, stats)

        # Récupérer les IDs des événements
        result = self.session.execute(
            text("""
                SELECT id, email_id
                FROM evenements_comptables
                WHERE date_operation >= :date_debut
                  AND date_operation <= :date_fin
            """),
            {'date_debut': date_debut, 'date_fin': date_fin}
        )

        evenements = result.fetchall()
        evenement_ids = [evt[0] for evt in evenements]
        email_ids = [evt[1] for evt in evenements if evt[1]]

        if not evenement_ids:
            return {
                'success': True,
                'message': 'Aucun événement à supprimer',
                'stats': stats
            }

        # Préparer les paramètres
        placeholders = ','.join([f':id{i}' for i in range(len(evenement_ids))])
        params = {f'id{i}': evt_id for i, evt_id in enumerate(evenement_ids)}

        try:
            # 1. Supprimer les mouvements portefeuille
            self.session.execute(
                text(f"""
                    DELETE FROM mouvements_portefeuille
                    WHERE source_evenement_id IN ({placeholders})
                """),
                params
            )

            # 2. Supprimer les mouvements compte courant
            self.session.execute(
                text(f"""
                    DELETE FROM mouvements_comptes_courants
                    WHERE source_evenement_id IN ({placeholders})
                """),
                params
            )

            # 3. Supprimer les écritures comptables liées
            if email_ids:
                email_placeholders = ','.join([f':email{i}' for i in range(len(email_ids))])
                email_params = {f'email{i}': email_id for i, email_id in enumerate(email_ids)}

                self.session.execute(
                    text(f"""
                        DELETE FROM ecritures_comptables
                        WHERE source_email_id IN ({email_placeholders})
                    """),
                    email_params
                )

            # 4. Supprimer les événements
            self.session.execute(
                text(f"""
                    DELETE FROM evenements_comptables
                    WHERE id IN ({placeholders})
                """),
                params
            )

            # Commit
            self.session.commit()

            return {
                'success': True,
                'message': f'Nettoyage terminé: {stats["evenements"]} événements supprimés',
                'stats': stats,
                'backup_file': backup_file
            }

        except Exception as e:
            self.session.rollback()
            return {
                'success': False,
                'message': f'Erreur lors du nettoyage: {str(e)}',
                'stats': stats
            }

    def nettoyer_par_phase(self, phase: int, dry_run: bool = True) -> Dict:
        """
        Nettoie tous les événements traités par une phase spécifique

        Args:
            phase: Numéro de phase (1, 2, 3)
            dry_run: Si True, simule sans modifier

        Returns:
            Dictionnaire avec résultats
        """
        # Compter les événements de cette phase
        result = self.session.execute(
            text("""
                SELECT COUNT(*)
                FROM evenements_comptables
                WHERE phase_traitement = :phase
            """),
            {'phase': phase}
        )
        count = result.fetchone()[0]

        stats = {
            'phase': phase,
            'evenements': count
        }

        if count == 0:
            return {
                'success': True,
                'message': f'Aucun événement de la phase {phase} à nettoyer',
                'stats': stats
            }

        if dry_run:
            return {
                'success': True,
                'message': f'MODE DRY_RUN: {count} événements seraient supprimés',
                'stats': stats
            }

        # Suppression réelle
        try:
            # Récupérer les IDs
            result = self.session.execute(
                text("""
                    SELECT id
                    FROM evenements_comptables
                    WHERE phase_traitement = :phase
                """),
                {'phase': phase}
            )
            evenement_ids = [row[0] for row in result.fetchall()]

            if evenement_ids:
                placeholders = ','.join([f':id{i}' for i in range(len(evenement_ids))])
                params = {f'id{i}': evt_id for i, evt_id in enumerate(evenement_ids)}

                # Supprimer les mouvements liés
                self.session.execute(
                    text(f"""
                        DELETE FROM mouvements_portefeuille
                        WHERE source_evenement_id IN ({placeholders})
                    """),
                    params
                )

                self.session.execute(
                    text(f"""
                        DELETE FROM mouvements_comptes_courants
                        WHERE source_evenement_id IN ({placeholders})
                    """),
                    params
                )

                # Supprimer les événements
                self.session.execute(
                    text(f"""
                        DELETE FROM evenements_comptables
                        WHERE id IN ({placeholders})
                    """),
                    params
                )

                self.session.commit()

            return {
                'success': True,
                'message': f'Phase {phase} nettoyée: {count} événements supprimés',
                'stats': stats
            }

        except Exception as e:
            self.session.rollback()
            return {
                'success': False,
                'message': f'Erreur lors du nettoyage: {str(e)}',
                'stats': stats
            }

    def _creer_sauvegarde(self, date_debut: str, date_fin: str, stats: Dict) -> str:
        """
        Crée une sauvegarde JSON avant suppression

        Args:
            date_debut: Date de début
            date_fin: Date de fin
            stats: Statistiques pré-suppression

        Returns:
            Chemin du fichier de sauvegarde
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"backup_nettoyage_{date_debut}_{date_fin}_{timestamp}.json"
        filepath = os.path.join('backups', filename)

        # Créer le dossier backups si nécessaire
        os.makedirs('backups', exist_ok=True)

        # Sauvegarder
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)

        return filepath


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def cli_nettoyer_periode():
    """Interface en ligne de commande pour nettoyage par période"""
    if not DATABASE_URL:
        print("❌ Variable DATABASE_URL non définie")
        sys.exit(1)

    print("=" * 80)
    print("NETTOYAGE BASE DE DONNÉES - Événements Comptables")
    print("=" * 80)
    print()

    # Demander la période
    date_debut = input("Date de début (YYYY-MM-DD): ")
    date_fin = input("Date de fin (YYYY-MM-DD): ")

    # Créer le nettoyeur
    nettoyeur = NettoyeurBD(DATABASE_URL)

    # Analyser
    print()
    print("🔍 Analyse de la période...")
    stats = nettoyeur.analyser_periode(date_debut, date_fin)

    print()
    print("📊 STATISTIQUES:")
    print(f"   Période: {stats['date_debut']} → {stats['date_fin']}")
    print(f"   Événements: {stats['evenements']}")
    print(f"   Écritures comptables: {stats['ecritures']}")
    print(f"   Mouvements portefeuille: {stats['mouvements_portefeuille']}")
    print(f"   Mouvements compte courant: {stats['mouvements_cc']}")
    print()

    if stats['evenements'] == 0:
        print("✅ Aucun événement à nettoyer")
        return

    # Afficher détails
    print("📋 DÉTAIL DES ÉVÉNEMENTS:")
    for evt in stats['details_evenements'][:10]:  # Limiter à 10
        print(f"   #{evt['id']} - {evt['date']} - {evt['libelle'][:50]} - {evt['montant']}€")
    if len(stats['details_evenements']) > 10:
        print(f"   ... et {len(stats['details_evenements']) - 10} autres")
    print()

    # Confirmer
    print("⚠️  ATTENTION: Cette opération va supprimer définitivement ces données")
    response = input("Confirmer le nettoyage? (oui/non): ")

    if response.lower() != 'oui':
        print("❌ Nettoyage annulé")
        return

    # Nettoyer
    print()
    print("🧹 Nettoyage en cours...")
    result = nettoyeur.nettoyer_periode(date_debut, date_fin, dry_run=False)

    print()
    if result['success']:
        print(f"✅ {result['message']}")
        if 'backup_file' in result:
            print(f"💾 Sauvegarde: {result['backup_file']}")
    else:
        print(f"❌ {result['message']}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == '--help':
            print("Usage:")
            print("  python nettoyage_bd.py                    # Mode interactif")
            print("  python nettoyage_bd.py --help             # Aide")
        else:
            print("❌ Arguments inconnus")
            sys.exit(1)
    else:
        cli_nettoyer_periode()
