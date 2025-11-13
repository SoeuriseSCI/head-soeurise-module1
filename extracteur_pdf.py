#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EXTRACTEUR PDF - Relevés Bancaires (API PDF Native)
====================================================
Parse bank statements and extract individual accounting events using Claude's native PDF support.

Date: 06/11/2025
Auteur: Module Phase 1 - Accounting Events

RESPONSABILITÉS:
----------------
1. Lecture et parsing de PDF de relevés bancaires
2. Extraction des opérations individuelles via Claude API PDF native
3. Normalisation des données (dates, montants, libellés)
4. Détection du type d'opération (DEBIT/CREDIT)
5. Préparation des données pour création d'événements

FORMATS SUPPORTÉS:
-----------------
- Relevés bancaires LCL (format standard)
- Factures comptables
- Distributions SCPI
- Confirmations d'achat ETF/Actions
- Apports d'associés

WORKFLOW SIMPLIFIÉ:
------------------
1. Lecture du PDF (binaire)
2. Encode base64
3. Envoi direct à Claude API (type="document")
4. Analyse et extraction en une seule passe
5. Retour des événements structurés
"""

import os
import json
import base64
import gc  # Garbage collector pour libération mémoire explicite
from datetime import datetime
from typing import Dict, List, Optional
from anthropic import Anthropic
from rapprocheur_operations import RapprocheurOperations

# Configuration
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')


class ExtracteurPDF:
    """
    Extracteur d'événements comptables depuis PDF via Claude API native
    """

    def __init__(self, pdf_path: str, email_metadata: Optional[Dict] = None):
        """
        Initialise l'extracteur

        Args:
            pdf_path: Chemin vers le fichier PDF
            email_metadata: Métadonnées de l'email source (optionnel)
                - email_id: ID de l'email
                - email_from: Expéditeur
                - email_date: Date de l'email
                - email_subject: Sujet de l'email
        """
        self.pdf_path = pdf_path
        self.email_metadata = email_metadata or {}
        self.client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
        self._analyse_cache = None  # Cache pour éviter double analyse du document
        self._justificatifs_metadata = {}  # Métadonnées des justificatifs (Phase 2)

    def _lire_pdf_base64(self) -> str:
        """
        Lit le PDF et retourne son contenu encodé en base64

        Returns:
            Contenu du PDF en base64
        """
        with open(self.pdf_path, 'rb') as f:
            pdf_data = f.read()
        return base64.standard_b64encode(pdf_data).decode('utf-8')

    def _deduplicater_operations(self, operations: List[Dict]) -> List[Dict]:
        """
        Déduplication déterministe basée sur double fingerprint + score de qualité

        STRATÉGIE (FIX 12/11/2025):
        1. Calculer DEUX fingerprints pour chaque opération:
           - Fingerprint complet: date + libellé + montant + type
           - Fingerprint simplifié: date + montant + type (SANS libellé)
        2. Grouper d'abord par fingerprint complet (doublons exacts)
        3. Puis grouper par fingerprint simplifié (doublons SCPI/Apports)
        4. Dans chaque groupe, garder celle avec le score qualité le plus élevé

        FIX DOUBLONS SCPI/APPORTS (12/11/2025):
        - Même opération apparaît 2 fois: relevé bancaire + avis d'opération
        - Libellés différents → fingerprint complet différent
        - Mais même date + montant + type → fingerprint simplifié identique
        - Solution: Utiliser les DEUX fingerprints pour détecter tous les doublons

        Args:
            operations: Liste des opérations extraites

        Returns:
            Liste dédupliquée (garde version la plus détaillée de chaque groupe)
        """
        # TEST EXTRACTION COMPLÈTE: Désactiver déduplication temporairement
        print(f"⚠️  TEST: Déduplication DÉSACTIVÉE - Garde toutes les {len(operations)} opérations")
        return operations

        if len(operations) == 0:
            return operations

        try:
            from detection_doublons import DetecteurDoublons
            from collections import defaultdict

            # ÉTAPE 1: Grouper par fingerprint COMPLET (doublons exacts)
            groupes_complets = defaultdict(list)

            for op in operations:
                fingerprint = DetecteurDoublons.calculer_fingerprint(op)
                score_qualite = DetecteurDoublons.calculer_score_qualite(op)
                groupes_complets[fingerprint].append((op, score_qualite))

            # Garder la meilleure de chaque groupe (fingerprint complet)
            operations_apres_dedupe1 = []
            doublons_exacts = 0

            for fingerprint, ops_avec_score in groupes_complets.items():
                if len(ops_avec_score) > 1:
                    ops_avec_score.sort(key=lambda x: x[1], reverse=True)
                    doublons_exacts += len(ops_avec_score) - 1

                operations_apres_dedupe1.append((ops_avec_score[0][0], ops_avec_score[0][1]))

            # ÉTAPE 2: Grouper par fingerprint SIMPLIFIÉ (doublons SCPI/Apports)
            groupes_simplifies = defaultdict(list)

            for op, score in operations_apres_dedupe1:
                fingerprint_simple = DetecteurDoublons.calculer_fingerprint_simplifie(op)
                groupes_simplifies[fingerprint_simple].append((op, score))

            # Garder la meilleure de chaque groupe (fingerprint simplifié)
            operations_finales = []
            doublons_scpi_apports = 0

            for fingerprint_simple, ops_avec_score in groupes_simplifies.items():
                if len(ops_avec_score) > 1:
                    # Trier par score décroissant
                    ops_avec_score.sort(key=lambda x: x[1], reverse=True)
                    doublons_scpi_apports += len(ops_avec_score) - 1

                    # Debug: Afficher les doublons SCPI/Apports détectés
                    meilleure = ops_avec_score[0][0]
                    if doublons_scpi_apports <= 5:  # Limiter l'affichage
                        print(f"🔍 Doublon SCPI/Apport: {meilleure['date_operation']} - {meilleure['montant']}€")
                        print(f"   Gardé: {meilleure['libelle'][:70]}... (score: {ops_avec_score[0][1]})")
                        for op_dup, score_dup in ops_avec_score[1:]:
                            print(f"   Supprimé: {op_dup['libelle'][:70]}... (score: {score_dup})")

                # Garder la meilleure (ou la seule)
                operations_finales.append(ops_avec_score[0][0])

            total_doublons = doublons_exacts + doublons_scpi_apports
            if total_doublons > 0:
                print(f"✅ Déduplication: {len(operations)} → {len(operations_finales)} opérations")
                print(f"   • Doublons exacts: {doublons_exacts}")
                print(f"   • Doublons SCPI/Apports: {doublons_scpi_apports}")
            else:
                print(f"✅ Déduplication: {len(operations)} opérations (aucun doublon détecté)")

            return operations_finales

        except Exception as e:
            print(f"⚠️  Erreur déduplication déterministe (on garde toutes les opérations): {e}")
            import traceback
            traceback.print_exc()
            return operations

    def analyser_document(self) -> Dict:
        """
        Analyse le document pour extraire le type, la période ET les sections
        Utilise l'API PDF native de Claude

        Returns:
            Dictionnaire avec:
                - type_document: str (ex: "releve_bancaire", "facture_scpi", etc.)
                - date_debut: str (format YYYY-MM-DD)
                - date_fin: str (format YYYY-MM-DD)
                - description: str (résumé)
                - sections: dict (ex: {"releves": [1, 20], "avis_vm": [21, 41]})
        """
        if not self.client:
            raise ValueError("ANTHROPIC_API_KEY non définie")

        if not os.path.exists(self.pdf_path):
            raise FileNotFoundError(f"PDF non trouvé: {self.pdf_path}")

        print(f"🔍 Analyse du document: {os.path.basename(self.pdf_path)}")

        try:
            # Lire le PDF en base64
            pdf_base64 = self._lire_pdf_base64()

            # Analyser avec Claude (API PDF native)
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "document",
                            "source": {
                                "type": "base64",
                                "media_type": "application/pdf",
                                "data": pdf_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": """Analyse ce document comptable PDF et extrais les informations suivantes:

1. TYPE DE DOCUMENT PRINCIPAL:
   - releve_bancaire
   - facture_scpi
   - tableau_amortissement
   - facture_comptable
   - autre

2. PÉRIODE COUVERTE (pour les relevés bancaires):
   - Date de PREMIÈRE opération
   - Date de DERNIÈRE opération
   - Analyse TOUTES les pages

3. SECTIONS DU DOCUMENT:
   CRITIQUE: Identifie les différentes sections du PDF par numéro de page.

   Pour chaque type de contenu, indique:
   - page_debut: première page de cette section
   - page_fin: dernière page de cette section

   Types de sections à détecter:
   - "releves_bancaires": Pages avec colonnes (Date | Libellé | Débit | Crédit)
   - "avis_operations_vm": Avis d'achat/vente de titres (ETF, actions)
   - "tableaux_amortissement": Tableaux de prêt avec échéances
   - "factures": Factures diverses (comptable, LEI, etc.)
   - "autres": Autre contenu

4. DESCRIPTION:
   - Courte description du contenu global (1 phrase)

EXEMPLE DE RÉPONSE:
{
  "type_document": "releve_bancaire",
  "date_debut": "2023-12-05",
  "date_fin": "2024-10-04",
  "description": "Relevés LCL + avis d'opération sur valeurs mobilières",
  "sections": {
    "releves_bancaires": {"page_debut": 1, "page_fin": 20},
    "avis_operations_vm": {"page_debut": 21, "page_fin": 38},
    "factures": {"page_debut": 39, "page_fin": 41}
  }
}

NE retourne QUE le JSON, sans texte avant ou après."""
                        }
                    ]
                }]
            )

            response_text = response.content[0].text

            # Nettoyer la réponse
            json_text = response_text.strip()
            if json_text.startswith('```json'):
                json_text = json_text[7:]
            if json_text.startswith('```'):
                json_text = json_text[3:]
            if json_text.endswith('```'):
                json_text = json_text[:-3]
            json_text = json_text.strip()

            # Parser le JSON
            data = json.loads(json_text)

            print(f"   Type: {data.get('type_document', 'inconnu')}")
            print(f"   Période: {data.get('date_debut', '?')} → {data.get('date_fin', '?')}")
            print(f"   Description: {data.get('description', '')}")

            # Afficher les sections détectées
            sections = data.get('sections', {})
            if sections:
                print(f"   📑 Sections détectées:")
                for section_type, pages in sections.items():
                    if isinstance(pages, dict):
                        print(f"      • {section_type}: pages {pages.get('page_debut', '?')}-{pages.get('page_fin', '?')}")

            # Mettre en cache pour éviter double analyse
            self._analyse_cache = data

            return data

        except json.JSONDecodeError as e:
            print(f"⚠️  Erreur parsing JSON: {e}")
            print(f"   Réponse: {response_text[:200]}...")
            return {
                'type_document': 'inconnu',
                'date_debut': None,
                'date_fin': None,
                'description': 'Analyse échouée'
            }
        except Exception as e:
            print(f"⚠️  Erreur analyse document: {e}")
            import traceback
            traceback.print_exc()
            return {
                'type_document': 'inconnu',
                'date_debut': None,
                'date_fin': None,
                'description': f'Erreur: {str(e)}'
            }

    def _extraire_operations_chunk(self, pdf_base64: str, chunk_num: int, total_chunks: int) -> List[Dict]:
        """
        Extrait les opérations d'un chunk de PDF

        Args:
            pdf_base64: PDF encodé en base64
            chunk_num: Numéro du chunk (1-based)
            total_chunks: Nombre total de chunks

        Returns:
            Liste des opérations extraites
        """
        if chunk_num > 1:
            print(f"🔄 Chunk {chunk_num}/{total_chunks}: Envoi à Claude pour extraction...")
        else:
            print(f"🔄 Envoi du PDF à Claude pour extraction... ({total_chunks} lot{'s' if total_chunks > 1 else ''})")

        response = self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=64000,  # Augmenté pour éviter troncature (jusqu'à 30 opérations/chunk)
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": """Tu es un extracteur d'opérations bancaires. Ton objectif est d'extraire TOUTES les opérations bancaires de CHAQUE page de ce relevé bancaire.

INSTRUCTIONS CRITIQUES:
1. LIS ATTENTIVEMENT CHAQUE PAGE du début à la fin
2. CHAQUE page contient généralement 10-25 opérations bancaires
3. Ne t'arrête PAS tant que tu n'as pas lu la DERNIÈRE page
4. Si tu vois moins de 10 opérations dans un relevé de plusieurs pages, tu as probablement manqué des pages

Pour CHAQUE opération trouvée, extrais:
- date_operation (format YYYY-MM-DD obligatoire)
- libelle (texte complet sur une ligne)
- montant (nombre décimal positif)
- type_operation (DEBIT ou CREDIT selon la colonne)

RÈGLES:
- Regroupe les opérations multi-lignes (ex: "PRET IMMOBILIER ECH 15/01/24 DOSSIER NO 5009736")
- Ignore: en-têtes, totaux, soldes d'ouverture/clôture, numéros de relevé
- Convertis les dates au format YYYY-MM-DD (déduis l'année du contexte si absente)
- Continue jusqu'à la dernière page, même si tu penses avoir fini

EXTRACTION COMPLÈTE (TEST):
- Extrais TOUTES les opérations, y compris:
  * Relevés de compte (libellés courts du relevé bancaire)
  * Factures (avec n° facture si présent, montant TTC)
  * Avis d'opération (avec tous les détails: ISIN, nombre titres, prix, commissions)
  * Bulletins informatifs (SCPI, etc.)
- Pour chaque opération, capture le MAXIMUM de détails disponibles:
  * Numéro de facture / référence (si présent dans le libellé ou document)
  * Détails de ventilation (intérêts/capital, commissions/brut, HT/TVA/TTC)
  * Identifiants (ISIN pour valeurs mobilières)
- Ne filtre RIEN : nous ferons le rapprochement après extraction

FORMAT DE SORTIE (JSON uniquement, sans texte avant/après):
{
  "operations": [
    {
      "date_operation": "2024-01-15",
      "libelle": "PRLV SEPA CACI NON LIFE LIMITED",
      "montant": 87.57,
      "type_operation": "DEBIT"
    }
  ]
}

ATTENTION: Ce chunk peut contenir 20-50 opérations. Extrais-les TOUTES avant de terminer."""
                    }
                ]
            }]
        )

        # DEBUG: Vérifier pourquoi l'extraction s'arrête
        stop_reason = response.stop_reason
        response_text = response.content[0].text

        print(f"   🔍 DEBUG Chunk {chunk_num}: stop_reason={stop_reason}, taille_réponse={len(response_text)} chars")

        # Nettoyer la réponse
        json_text = response_text.strip()
        if json_text.startswith('```json'):
            json_text = json_text[7:]
        if json_text.startswith('```'):
            json_text = json_text[3:]
        if json_text.endswith('```'):
            json_text = json_text[:-3]
        json_text = json_text.strip()

        # Parser le JSON - extraction robuste
        try:
            data = json.loads(json_text)
            operations = data.get('operations', [])
        except json.JSONDecodeError as e:
            # Tentative d'extraction robuste : trouver le JSON valide
            # Claude ajoute parfois du texte explicatif après le JSON
            try:
                # Trouver le premier { et essayer de parser jusqu'à trouver un JSON valide
                start_idx = json_text.find('{')
                if start_idx == -1:
                    raise ValueError("Pas de JSON trouvé dans la réponse")

                # Essayer de trouver la fin du JSON en comptant les accolades
                brace_count = 0
                end_idx = start_idx
                for i in range(start_idx, len(json_text)):
                    if json_text[i] == '{':
                        brace_count += 1
                    elif json_text[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break

                # Extraire et parser le JSON
                clean_json = json_text[start_idx:end_idx]
                data = json.loads(clean_json)
                operations = data.get('operations', [])
                print(f"   ✓ JSON extrait avec succès après nettoyage (texte supplémentaire ignoré)")
            except Exception as e2:
                print(f"   ⚠️  ERREUR JSON Chunk {chunk_num}: {e}")
                print(f"   ⚠️  Extraction robuste échouée: {e2}")
                print(f"   📄 Début JSON: {json_text[:200]}...")
                print(f"   📄 Fin JSON: ...{json_text[-200:]}")
                return []

        # Vérifier si la réponse semble tronquée
        if stop_reason == 'max_tokens' and len(operations) < 10:
            print(f"   ⚠️  TRONCATURE DÉTECTÉE Chunk {chunk_num}: stop_reason=max_tokens mais seulement {len(operations)} opérations")

        # Afficher le nombre d'opérations extraites pour TOUS les chunks
        if chunk_num > 1:
            print(f"   ✓ Chunk {chunk_num}/{total_chunks}: {len(operations)} opérations extraites")
        else:
            print(f"   ✓ Chunk {chunk_num}/{total_chunks}: {len(operations)} opérations extraites")

        # TRAÇABILITÉ: Afficher détails des opérations extraites (pour debug)
        if operations:
            print(f"   📋 Détails extractions chunk {chunk_num}:")
            for op in operations:
                date = op.get('date_operation', 'N/A')
                montant = op.get('montant', 0)
                libelle_court = op.get('libelle', '')[:60] + ('...' if len(op.get('libelle', '')) > 60 else '')
                print(f"      • {date} - {montant}€ - {libelle_court}")

        return operations

    def _diviser_pdf_en_chunks(self, max_pages_per_chunk: int = 5, page_debut: int = None, page_fin: int = None) -> List[str]:
        """
        Divise un PDF en plusieurs chunks de pages (fichiers temporaires)

        Args:
            max_pages_per_chunk: Nombre maximum de pages par chunk
            page_debut: Première page à inclure (1-based, optionnel)
            page_fin: Dernière page à inclure (1-based, optionnel)

        Returns:
            Liste des chemins des PDFs temporaires créés
        """
        try:
            import PyPDF2
            import tempfile

            # Ouvrir le PDF
            with open(self.pdf_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                total_pages = len(pdf_reader.pages)

                # Déterminer la plage de pages à traiter
                first_page = (page_debut - 1) if page_debut else 0  # Convert 1-based to 0-based
                last_page = page_fin if page_fin else total_pages
                pages_to_process = last_page - first_page

                if page_debut or page_fin:
                    print(f"📄 PDF: extraction pages {page_debut or 1}-{page_fin or total_pages} (sur {total_pages} totales)")

                # Si petit PDF ou petite section, pas besoin de diviser
                if pages_to_process <= max_pages_per_chunk:
                    # Créer un PDF temporaire avec seulement les pages demandées
                    if page_debut or page_fin:
                        pdf_writer = PyPDF2.PdfWriter()
                        for page_num in range(first_page, last_page):
                            pdf_writer.add_page(pdf_reader.pages[page_num])

                        temp_file = tempfile.NamedTemporaryFile(
                            delete=False,
                            suffix=f'_pages_{page_debut or 1}-{page_fin or total_pages}.pdf'
                        )
                        with open(temp_file.name, 'wb') as out_f:
                            pdf_writer.write(out_f)
                        return [temp_file.name]
                    else:
                        return [self.pdf_path]

                print(f"📄 PDF pages {page_debut or 1}-{page_fin or total_pages} → Division en chunks de {max_pages_per_chunk} pages")

                # Créer les chunks pour la plage spécifiée
                chunk_paths = []
                for start_page in range(first_page, last_page, max_pages_per_chunk):
                    end_page = min(start_page + max_pages_per_chunk, last_page)

                    # Créer un nouveau PDF avec ce chunk
                    pdf_writer = PyPDF2.PdfWriter()
                    for page_num in range(start_page, end_page):
                        pdf_writer.add_page(pdf_reader.pages[page_num])

                    # Écrire dans un fichier temporaire
                    temp_file = tempfile.NamedTemporaryFile(
                        delete=False,
                        suffix=f'_chunk_{start_page+1}-{end_page}.pdf'
                    )
                    with open(temp_file.name, 'wb') as out_f:
                        pdf_writer.write(out_f)

                    chunk_paths.append(temp_file.name)
                    print(f"   ✓ Chunk créé: pages {start_page+1}-{end_page} → {os.path.basename(temp_file.name)}")

                return chunk_paths

        except ImportError:
            # PyPDF2 non disponible, retourner le PDF complet
            print("⚠️  PyPDF2 non disponible - traitement du PDF complet (risque de troncature)")
            return [self.pdf_path]
        except Exception as e:
            print(f"⚠️  Erreur division PDF: {e} - traitement du PDF complet")
            return [self.pdf_path]

    def extraire_evenements(self, date_debut: str = None, date_fin: str = None) -> List[Dict]:
        """
        Extrait tous les événements du PDF via l'API PDF native de Claude

        STRATÉGIE ANTI-TRONCATURE:
        - Si PDF > 5 pages: Division en chunks de 5 pages
        - Extraction séparée de chaque chunk
        - Fusion des résultats + déduplication

        Args:
            date_debut: Date de début de période (format YYYY-MM-DD, optionnel)
            date_fin: Date de fin de période (format YYYY-MM-DD, optionnel)

        Returns:
            Liste de dictionnaires d'événements prêts pour GestionnaireEvenements
        """
        if not self.client:
            raise ValueError("ANTHROPIC_API_KEY non définie - impossible d'extraire les PDF")

        if not os.path.exists(self.pdf_path):
            raise FileNotFoundError(f"PDF non trouvé: {self.pdf_path}")

        print(f"📄 Extraction du PDF: {os.path.basename(self.pdf_path)}")

        try:
            # Utiliser l'analyse en cache ou analyser si pas déjà fait
            if self._analyse_cache:
                analyse = self._analyse_cache
            else:
                analyse = self.analyser_document()

            sections = analyse.get('sections', {})

            # Déterminer les pages à extraire (TOUTES les sections avec opérations)
            page_debut = None
            page_fin = None

            # FIX: Extraire TOUTES les sections, pas seulement releves_bancaires
            # Les sections à inclure : releves_bancaires, avis_operations_vm, factures
            sections_a_extraire = ['releves_bancaires', 'avis_operations_vm', 'factures']

            pages_min = []
            pages_max = []

            for section_name in sections_a_extraire:
                if section_name in sections:
                    section_info = sections[section_name]
                    if isinstance(section_info, dict):
                        debut = section_info.get('page_debut')
                        fin = section_info.get('page_fin')
                        if debut and fin:
                            pages_min.append(debut)
                            pages_max.append(fin)
                            print(f"📋 Section '{section_name}': pages {debut}-{fin}")

            if pages_min and pages_max:
                page_debut = min(pages_min)
                page_fin = max(pages_max)
                print(f"✅ Extraction globale: pages {page_debut}-{page_fin} (toutes sections)")
            else:
                print(f"⚠️  Aucune section détectée - extraction complète du PDF")

            # Diviser le PDF en chunks si nécessaire (5 pages pour extraction complète garantie)
            chunk_paths = self._diviser_pdf_en_chunks(
                max_pages_per_chunk=5,
                page_debut=page_debut,
                page_fin=page_fin
            )
            total_chunks = len(chunk_paths)

            # Extraire chaque chunk
            all_operations = []
            for i, chunk_path in enumerate(chunk_paths, 1):
                # Lire le chunk en base64
                with open(chunk_path, 'rb') as f:
                    pdf_data = f.read()
                chunk_base64 = base64.standard_b64encode(pdf_data).decode('utf-8')

                # Extraire les opérations du chunk
                operations = self._extraire_operations_chunk(chunk_base64, i, total_chunks)
                all_operations.extend(operations)

                # LIBÉRATION MÉMOIRE EXPLICITE (crucial sur Render 512MB)
                del pdf_data
                del chunk_base64
                del operations
                gc.collect()  # Force garbage collection

                # Nettoyer le fichier temporaire (sauf si c'est le PDF original)
                if chunk_path != self.pdf_path:
                    try:
                        os.unlink(chunk_path)
                    except:
                        pass

            operations = all_operations

            print(f"✅ {len(operations)} opérations extraites du PDF")

            # RAPPROCHEMENT INTELLIGENT PAR CLAUDE API (Phase 2)
            if len(operations) > 0:
                rapprocheur = RapprocheurOperations()
                operations, metadata = rapprocheur.rapprocher(operations)
                # Stocker les justificatifs dans les métadonnées pour audit
                self._justificatifs_metadata = metadata.get('justificatifs', {})
                print(f"✅ {len(operations)} opérations après rapprochement intelligent")

            # Enrichir et filtrer les opérations
            all_evenements = []
            nb_filtres_periode = 0
            nb_soldes_ouverture = 0

            for op in operations:
                # FILTRE 1: Vérifier la période
                date_op = op['date_operation']
                if date_debut and date_op < date_debut:
                    nb_filtres_periode += 1
                    continue  # Ignorer les opérations avant la période
                if date_fin and date_op > date_fin:
                    nb_filtres_periode += 1
                    continue  # Ignorer les opérations après la période

                # FILTRE 2: Exclure les soldes d'ouverture (non comptabilisables)
                libelle_norm = op['libelle'].upper().strip()
                est_solde_ouverture = any(pattern in libelle_norm for pattern in [
                    'ANCIEN SOLDE',
                    'SOLDE REPORTE',
                    'SOLDE REPORTÉ',
                    'SOLDE PRECEDENT',
                    'SOLDE PRÉCÉDENT',
                    'REPORT SOLDE'
                ])

                # SKIP les soldes d'ouverture - ne pas les créer en BD
                if est_solde_ouverture:
                    nb_soldes_ouverture += 1
                    continue

                evenement = {
                    'date_operation': op['date_operation'],
                    'libelle': op['libelle'],
                    'montant': float(op['montant']),
                    'type_operation': op['type_operation'],
                    'email_id': self.email_metadata.get('email_id'),
                    'email_from': self.email_metadata.get('email_from', 'pdf_manuel'),
                    'email_date': self.email_metadata.get('email_date', datetime.now()),
                    'email_subject': self.email_metadata.get('email_subject'),
                    'email_body': self.email_metadata.get('email_body', '')
                }
                all_evenements.append(evenement)

            print(f"✅ TOTAL: {len(all_evenements)} événements après filtrage")
            if nb_filtres_periode > 0 or nb_soldes_ouverture > 0:
                filtres = []
                if nb_filtres_periode > 0:
                    filtres.append(f"{nb_filtres_periode} opérations hors période")
                if nb_soldes_ouverture > 0:
                    filtres.append(f"{nb_soldes_ouverture} soldes d'ouverture")
                print(f"   ({' + '.join(filtres)} exclus)")

            # Afficher info sur le filtrage de période
            if date_debut or date_fin:
                periode = f"{date_debut or '...'} → {date_fin or '...'}"
                print(f"📅 Période appliquée: {periode}")

            return all_evenements

        except json.JSONDecodeError as e:
            print(f"❌ Erreur parsing JSON: {e}")
            print(f"   Réponse brute: {response_text[:500]}...")
            return []
        except Exception as e:
            print(f"❌ Erreur extraction PDF: {e}")
            import traceback
            traceback.print_exc()
            return []


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def extraire_et_afficher(pdf_path: str, email_metadata: Optional[Dict] = None) -> List[Dict]:
    """
    Extrait et affiche les événements d'un PDF

    Args:
        pdf_path: Chemin vers le PDF
        email_metadata: Métadonnées de l'email (optionnel)

    Returns:
        Liste des événements extraits
    """
    extracteur = ExtracteurPDF(pdf_path, email_metadata)
    evenements = extracteur.extraire_evenements()

    print()
    print("=" * 80)
    print("ÉVÉNEMENTS EXTRAITS")
    print("=" * 80)
    print()

    for i, evt in enumerate(evenements, 1):
        print(f"Événement #{i}")
        print(f"  Date: {evt['date_operation']}")
        print(f"  Libellé: {evt['libelle']}")
        print(f"  Montant: {evt['montant']}€")
        print(f"  Type: {evt['type_operation']}")
        print()

    print(f"📊 Total: {len(evenements)} événements")

    return evenements


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN (TESTS)
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import sys

    print("=" * 80)
    print("EXTRACTEUR PDF - Test (API PDF Native)")
    print("=" * 80)
    print()

    if len(sys.argv) < 2:
        print("Usage: python extracteur_pdf.py <chemin_pdf>")
        print()
        print("Exemple:")
        print("  python extracteur_pdf.py 'Elements Comptables des 1-2-3T2024.pdf'")
        sys.exit(1)

    pdf_path = sys.argv[1]

    # Test avec métadonnées fictives
    email_metadata = {
        'email_id': 'test_email_001',
        'email_from': 'comptabilite@test.com',
        'email_date': datetime.now(),
        'email_subject': 'Éléments comptables Q1-Q3 2024'
    }

    evenements = extraire_et_afficher(pdf_path, email_metadata)

    # Sauvegarder dans un fichier JSON pour inspection
    output_file = 'evenements_extraits.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(evenements, f, indent=2, ensure_ascii=False, default=str)

    print()
    print(f"💾 Événements sauvegardés dans: {output_file}")
