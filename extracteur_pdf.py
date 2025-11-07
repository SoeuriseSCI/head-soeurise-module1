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
        Utilise Claude pour déduplicater intelligemment les opérations

        PRINCIPE:
        Certaines opérations apparaissent en double dans les relevés avec des libellés
        légèrement différents. Claude identifie ces doublons (même date + même montant)
        et garde LA VERSION LA PLUS DÉTAILLÉE.

        Exemple:
        - "VIR SEPA SCPI EPARGNE PIERRE LIBELLE:SCPI..." (détaillé ✓)
        - "SCPI EPARGNE PIERRE DISTRIBUTION 4EME..." (moins détaillé ✗)
        → Claude garde le premier

        Args:
            operations: Liste des opérations extraites

        Returns:
            Liste dédupliquée (opérations uniques avec les versions les plus détaillées)
        """
        if not self.client or len(operations) == 0:
            return operations

        try:
            # Préparer les opérations pour Claude
            operations_json = json.dumps(operations, indent=2, ensure_ascii=False)

            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=16000,
                messages=[{
                    "role": "user",
                    "content": f"""Voici {len(operations)} opérations bancaires extraites d'un relevé.

PROBLÈME: Certaines opérations apparaissent EN DOUBLE avec des libellés différents.

EXEMPLES DE DOUBLONS À DÉTECTER:
1. Même date + même montant + types similaires (SCPI, virements, etc.)
2. Une version détaillée vs une version courte
3. Même opération décrite différemment selon la page du relevé

TÂCHE:
1. Analyse TOUTES les opérations
2. Identifie les doublons (même date + même montant ± 0.01€)
3. Pour chaque groupe de doublons, garde LA VERSION LA PLUS DÉTAILLÉE (libellé le plus long et informatif)
4. Retourne la liste dédupliquée

OPÉRATIONS:
```json
{operations_json}
```

Retourne un JSON avec cette structure exacte:
{{
  "operations_uniques": [
    {{
      "date_operation": "2024-01-29",
      "libelle": "VIR SEPA SCPI EPARGNE PIERRE LIBELLE:SCPI...",
      "montant": 7356.24,
      "type_operation": "CREDIT"
    }}
  ],
  "nb_doublons_supprimes": 4,
  "details_doublons": [
    {{
      "date": "2024-01-29",
      "montant": 7356.24,
      "garde": "VIR SEPA SCPI EPARGNE PIERRE...",
      "supprime": "SCPI EPARGNE PIERRE DISTRIBUTION..."
    }}
  ]
}}

NE retourne QUE le JSON, sans texte avant ou après."""
                }]
            )

            response_text = response.content[0].text.strip()

            # Nettoyer la réponse
            json_text = response_text
            if json_text.startswith('```json'):
                json_text = json_text[7:]
            if json_text.startswith('```'):
                json_text = json_text[3:]
            if json_text.endswith('```'):
                json_text = json_text[:-3]
            json_text = json_text.strip()

            # Parser le JSON
            result = json.loads(json_text)
            operations_dedupliquees = result.get('operations_uniques', operations)
            nb_doublons = result.get('nb_doublons_supprimes', 0)

            if nb_doublons > 0:
                print(f"🔍 Doublons détectés par Claude: {nb_doublons} opérations éliminées")
                details = result.get('details_doublons', [])
                for detail in details[:3]:  # Afficher max 3 exemples
                    print(f"   - {detail.get('date')} {detail.get('montant')}€: gardé version détaillée")

            return operations_dedupliquees

        except Exception as e:
            print(f"⚠️  Erreur déduplication (on garde toutes les opérations): {e}")
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

        # Parser le JSON
        try:
            data = json.loads(json_text)
            operations = data.get('operations', [])
        except json.JSONDecodeError as e:
            print(f"   ⚠️  ERREUR JSON Chunk {chunk_num}: {e}")
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

            # Déterminer les pages à extraire (uniquement les relevés bancaires)
            page_debut = None
            page_fin = None

            if 'releves_bancaires' in sections:
                releves = sections['releves_bancaires']
                page_debut = releves.get('page_debut')
                page_fin = releves.get('page_fin')
                print(f"📋 Extraction ciblée: pages {page_debut}-{page_fin} (relevés bancaires uniquement)")
            else:
                print(f"⚠️  Aucune section 'releves_bancaires' détectée - extraction complète du PDF")

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

            # DÉDUPLICATION PAR CLAUDE (nouvelle étape)
            if len(operations) > 0:
                operations = self._deduplicater_operations(operations)
                print(f"✅ {len(operations)} opérations après déduplication intelligente")

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
