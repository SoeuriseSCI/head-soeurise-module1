#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WORKFLOW ÉVÉNEMENTS COMPTABLES
==============================
Orchestration complète du traitement des événements comptables.

Date: 05/11/2025
Auteur: Module Phase 1 - Accounting Events

WORKFLOW COMPLET:
-----------------
1. EXTRACTION: PDF → Événements bruts
2. CRÉATION: Événements → Base de données (avec détection de doublons)
3. DÉTECTION: Classification automatique du type d'événement
4. PROPOSITION: Génération des écritures comptables suggérées
5. VALIDATION: (manuel - externe à ce module)
6. COMPTABILISATION: Création des écritures définitives

Ce module gère les étapes 1-4 automatiquement.
"""

import os
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from extracteur_pdf import ExtracteurPDF
from gestionnaire_evenements import GestionnaireEvenements, afficher_statistiques
from detecteurs_evenements import FactoryDetecteurs
from models_module2 import get_session


class WorkflowEvenements:
    """
    Orchestrateur du workflow complet de traitement des événements
    """

    def __init__(self, database_url: str, phase: int = 1):
        """
        Initialise le workflow

        Args:
            database_url: URL de connexion PostgreSQL
            phase: Phase de traitement (1, 2, 3)
        """
        self.database_url = database_url
        self.phase = phase
        self.session = get_session(database_url)
        self.gestionnaire = GestionnaireEvenements(self.session, phase=phase)

    def __del__(self):
        """Ferme la session à la destruction"""
        if hasattr(self, 'session'):
            self.session.close()

    def traiter_pdf(
        self,
        pdf_path: str,
        email_metadata: Optional[Dict] = None,
        auto_detect: bool = True
    ) -> Dict:
        """
        Traite un PDF complet: analyse → validation → extraction → création → détection

        Args:
            pdf_path: Chemin vers le PDF
            email_metadata: Métadonnées de l'email source
            auto_detect: Si True, lance la détection automatique des types

        Returns:
            Dictionnaire avec résultats:
                - total_operations: Nombre d'opérations extraites
                - evenements_crees: Nombre d'événements créés
                - doublons_detectes: Nombre de doublons ignorés
                - erreurs: Nombre d'erreurs
                - types_detectes: Nombre de types détectés
                - ids_crees: Liste des IDs créés
                - periode_document: Période détectée
                - exercice_valide: Boolean
        """
        print()
        print("=" * 80)
        print(f"WORKFLOW ÉVÉNEMENTS - PDF: {os.path.basename(pdf_path)}")
        print("=" * 80)
        print()

        # ÉTAPE 0: ANALYSE DU DOCUMENT
        print("🔍 ÉTAPE 0/4: ANALYSE DU DOCUMENT")
        print("-" * 80)

        extracteur = ExtracteurPDF(pdf_path, email_metadata)
        analyse = extracteur.analyser_document()

        # Récupérer l'exercice comptable en cours
        from sqlalchemy import text
        result = self.session.execute(text("""
            SELECT date_debut, date_fin, statut
            FROM exercices_comptables
            WHERE statut = 'OUVERT'
            ORDER BY date_debut DESC
            LIMIT 1
        """))
        exercice = result.fetchone()

        if not exercice:
            print("⚠️  Aucun exercice comptable ouvert")
            return {'total_operations': 0, 'evenements_crees': 0, 'doublons_detectes': 0,
                    'erreurs': 1, 'types_detectes': 0, 'ids_crees': [],
                    'periode_document': f"{analyse.get('date_debut')} → {analyse.get('date_fin')}",
                    'exercice_valide': False, 'message_erreur': 'Aucun exercice ouvert'}

        exercice_debut = str(exercice[0])
        exercice_fin = str(exercice[1])

        print(f"   Exercice: {exercice_debut} → {exercice_fin}")
        print(f"   Document: {analyse.get('date_debut', '?')} → {analyse.get('date_fin', '?')}")

        doc_debut = analyse.get('date_debut')
        doc_fin = analyse.get('date_fin')

        if not doc_debut or not doc_fin:
            print("⚠️  Période indéterminée - Traitement refusé")
            return {'total_operations': 0, 'evenements_crees': 0, 'doublons_detectes': 0,
                    'erreurs': 1, 'types_detectes': 0, 'ids_crees': [],
                    'periode_document': 'Indéterminée', 'exercice_valide': False,
                    'message_erreur': 'Période indéterminée'}

        # Vérifier s'il y a un CHEVAUCHEMENT entre document et exercice
        # Chevauchement existe si: doc_debut <= exercice_fin ET doc_fin >= exercice_debut
        # Pas de chevauchement si: doc_fin < exercice_debut OU doc_debut > exercice_fin
        if doc_fin < exercice_debut or doc_debut > exercice_fin:
            print(f"❌ DOCUMENT HORS EXERCICE - Aucun chevauchement")
            print(f"   Document: {doc_debut} → {doc_fin}")
            print(f"   Exercice: {exercice_debut} → {exercice_fin}")
            return {'total_operations': 0, 'evenements_crees': 0, 'doublons_detectes': 0,
                    'erreurs': 1, 'types_detectes': 0, 'ids_crees': [],
                    'periode_document': f"{doc_debut} → {doc_fin}", 'exercice_valide': False,
                    'message_erreur': 'Document hors exercice - aucun chevauchement'}

        # Document chevauche l'exercice (au moins partiellement) → OK
        if doc_debut < exercice_debut or doc_fin > exercice_fin:
            print(f"⚠️  Document chevauche l'exercice partiellement")
            print(f"   Les opérations hors exercice seront filtrées automatiquement")
        else:
            print(f"✅ Document entièrement dans l'exercice")
        print()

        # ÉTAPE 1: EXTRACTION
        print("📄 ÉTAPE 1/4: EXTRACTION DU PDF")
        print("-" * 80)

        operations = extracteur.extraire_evenements(
            date_debut=exercice_debut,
            date_fin=exercice_fin
        )

        print(f"✅ {len(operations)} opérations extraites")
        print()

        # ÉTAPE 2: CRÉATION DES ÉVÉNEMENTS
        print("💾 ÉTAPE 2/3: CRÉATION DES ÉVÉNEMENTS")
        print("-" * 80)

        stats_creation = self.gestionnaire.creer_evenements_batch(operations)

        print()
        print(f"✅ Événements créés: {stats_creation['crees']}")
        print(f"⚠️  Doublons détectés: {stats_creation['doublons']}")
        print(f"❌ Erreurs: {stats_creation['erreurs']}")
        print()

        # ÉTAPE 3: DÉTECTION DES TYPES
        types_detectes = 0
        if auto_detect and stats_creation['crees'] > 0:
            print("🔍 ÉTAPE 3/3: DÉTECTION DES TYPES D'ÉVÉNEMENTS")
            print("-" * 80)

            for evt_id in stats_creation['ids_crees']:
                type_evt = self.gestionnaire.detecter_type_evenement(evt_id)
                if type_evt:
                    types_detectes += 1
                    print(f"✅ Événement #{evt_id}: {type_evt}")
                    # Marquer la phase de traitement
                    self.gestionnaire.marquer_phase_traitement(evt_id, self.phase)

            print()
            print(f"✅ Types détectés: {types_detectes}/{stats_creation['crees']}")
            print()

        # RÉSUMÉ
        print("=" * 80)
        print("RÉSUMÉ")
        print("=" * 80)
        print()
        print(f"📊 Opérations extraites: {len(operations)}")
        print(f"✅ Événements créés: {stats_creation['crees']}")
        print(f"🔍 Types détectés: {types_detectes}")
        print(f"⚠️  Doublons ignorés: {stats_creation['doublons']}")
        print(f"❌ Erreurs: {stats_creation['erreurs']}")
        print()

        return {
            'total_operations': len(operations),
            'evenements_crees': stats_creation['crees'],
            'doublons_detectes': stats_creation['doublons'],
            'erreurs': stats_creation['erreurs'],
            'types_detectes': types_detectes,
            'ids_crees': stats_creation['ids_crees']
        }

    def generer_propositions(self, evenement_ids: Optional[List[int]] = None) -> List[Dict]:
        """
        Génère les propositions d'écritures comptables pour des événements

        Args:
            evenement_ids: Liste d'IDs d'événements (None = tous les événements en attente)

        Returns:
            Liste de propositions
        """
        print()
        print("=" * 80)
        print("GÉNÉRATION DES PROPOSITIONS COMPTABLES")
        print("=" * 80)
        print()

        # Si aucun ID fourni, récupérer les événements en attente
        if evenement_ids is None:
            evenements = self.gestionnaire.obtenir_evenements_en_attente()
            evenement_ids = [evt['id'] for evt in evenements]

        if not evenement_ids:
            print("ℹ️  Aucun événement en attente")
            return []

        print(f"🔍 Analyse de {len(evenement_ids)} événements...")
        print()

        propositions = []
        for evt_id in evenement_ids:
            # Récupérer l'événement
            from sqlalchemy import text
            result = self.session.execute(
                text("""
                    SELECT id, date_operation, libelle, libelle_normalise,
                           montant, type_operation, type_evenement
                    FROM evenements_comptables
                    WHERE id = :id
                """),
                {'id': evt_id}
            )
            row = result.fetchone()
            if not row:
                continue

            evenement = {
                'id': row[0],
                'date_operation': row[1],
                'libelle': row[2],
                'libelle_normalise': row[3],
                'montant': float(row[4]) if row[4] else None,
                'type_operation': row[5],
                'type_evenement': row[6]
            }

            # EXCLURE les soldes d'ouverture (non comptabilisables)
            if evenement['type_evenement'] == 'SOLDE_OUVERTURE':
                print(f"⏭️  Événement #{evt_id} ignoré (SOLDE_OUVERTURE - non comptabilisable)")
                continue

            # Générer la proposition
            proposition = FactoryDetecteurs.detecter_et_proposer(
                self.session,
                evenement,
                phase=self.phase
            )

            if proposition:
                propositions.append({
                    'evenement_id': evt_id,
                    'proposition': proposition
                })

                print(f"✅ Événement #{evt_id}: {proposition['type_evenement']}")
                print(f"   Confiance: {proposition['confiance']}")
                print(f"   Écritures: {len(proposition['ecritures'])}")
                for ecriture in proposition['ecritures']:
                    print(f"     • {ecriture['compte_debit']} → {ecriture['compte_credit']}: "
                          f"{ecriture['montant']:.2f}€")
                print()

        print("=" * 80)
        print(f"✅ {len(propositions)} propositions générées")
        print("=" * 80)
        print()

        return propositions

    def afficher_stats(self):
        """Affiche les statistiques globales"""
        afficher_statistiques(self.gestionnaire)


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def traiter_pdf_complet(pdf_path: str, database_url: str, email_metadata: Optional[Dict] = None) -> Dict:
    """
    Fonction helper pour traiter un PDF en une seule commande

    Args:
        pdf_path: Chemin vers le PDF
        database_url: URL de la base de données
        email_metadata: Métadonnées de l'email (optionnel)

    Returns:
        Résultats du traitement
    """
    workflow = WorkflowEvenements(database_url, phase=1)
    resultats = workflow.traiter_pdf(pdf_path, email_metadata, auto_detect=True)
    return resultats


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN (CLI)
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import sys

    DATABASE_URL = os.getenv('DATABASE_URL')
    if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

    if not DATABASE_URL:
        print("❌ Variable DATABASE_URL non définie")
        sys.exit(1)

    print("=" * 80)
    print("WORKFLOW ÉVÉNEMENTS COMPTABLES")
    print("=" * 80)
    print()

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python workflow_evenements.py <pdf_path>           # Traiter un PDF")
        print("  python workflow_evenements.py --stats              # Afficher statistiques")
        print("  python workflow_evenements.py --propositions       # Générer propositions")
        print()
        print("Exemples:")
        print("  python workflow_evenements.py 'Elements Comptables des 1-2-3T2024.pdf'")
        print("  python workflow_evenements.py --stats")
        sys.exit(1)

    workflow = WorkflowEvenements(DATABASE_URL, phase=1)

    if sys.argv[1] == '--stats':
        # Afficher les statistiques
        workflow.afficher_stats()

    elif sys.argv[1] == '--propositions':
        # Générer les propositions pour les événements en attente
        propositions = workflow.generer_propositions()
        print(f"✅ {len(propositions)} propositions générées")

    else:
        # Traiter un PDF
        pdf_path = sys.argv[1]

        if not os.path.exists(pdf_path):
            print(f"❌ Fichier non trouvé: {pdf_path}")
            sys.exit(1)

        # Métadonnées fictives pour test
        email_metadata = {
            'email_id': f'email_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            'email_from': 'comptabilite@lcl.fr',
            'email_date': datetime.now(),
            'email_subject': 'Éléments comptables'
        }

        resultats = workflow.traiter_pdf(pdf_path, email_metadata, auto_detect=True)

        print()
        print("🎉 Traitement terminé!")
        print()
        print("Prochaines étapes:")
        print("  1. Vérifier les événements: python check_evenements.py")
        print("  2. Générer les propositions: python workflow_evenements.py --propositions")
        print("  3. Valider les propositions (manuel)")
        print("  4. Créer les écritures comptables")
