#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EXTRACTEUR PDF - Relevés Bancaires
==================================
Parse bank statements and extract individual accounting events.

Date: 05/11/2025
Auteur: Module Phase 1 - Accounting Events

RESPONSABILITÉS:
----------------
1. Lecture et parsing de PDF de relevés bancaires
2. Extraction des opérations individuelles
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

WORKFLOW:
---------
1. Lecture du PDF
2. Identification du type de document par page
3. Extraction selon le format approprié
4. Normalisation des données
5. Retour d'une liste d'événements prêts à être créés
"""

import os
import re
import json
import io
import base64
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from anthropic import Anthropic

# Imports pour conversion PDF
try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

# Configuration
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')


class ExtracteurPDF:
    """
    Extracteur d'événements comptables depuis PDF de relevés bancaires
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

    def analyser_document(self) -> Dict:
        """
        Analyse le document pour extraire le type et la période couverte
        Utilise Claude Vision sur les 2 premières pages

        Returns:
            Dictionnaire avec:
                - type_document: str (ex: "releve_bancaire", "facture_scpi", etc.)
                - date_debut: str (format YYYY-MM-DD)
                - date_fin: str (format YYYY-MM-DD)
                - description: str (résumé)
        """
        if not self.client:
            raise ValueError("ANTHROPIC_API_KEY non définie")

        if not PDF2IMAGE_AVAILABLE:
            raise ImportError("pdf2image non disponible")

        if not os.path.exists(self.pdf_path):
            raise FileNotFoundError(f"PDF non trouvé: {self.pdf_path}")

        print(f"🔍 Analyse du document: {os.path.basename(self.pdf_path)}")

        try:
            # Convertir les 2 premières pages pour analyse
            images = convert_from_path(self.pdf_path, dpi=100, first_page=1, last_page=2)

            # Préparer les images pour Claude
            image_contents = []
            for image in images:
                buffer = io.BytesIO()
                image.save(buffer, format='JPEG', quality=85, optimize=True)
                image_base64 = base64.b64encode(buffer.getvalue()).decode()

                image_contents.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_base64
                    }
                })
                buffer.close()

            # Analyser avec Claude
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": image_contents + [{
                        "type": "text",
                        "text": """Analyse ce document comptable et extrais les informations suivantes:

1. TYPE DE DOCUMENT:
   - releve_bancaire
   - facture_scpi
   - tableau_amortissement
   - facture_comptable
   - autre

2. PÉRIODE COUVERTE:
   - Date de début (première opération ou date de début mentionnée)
   - Date de fin (dernière opération ou date de fin mentionnée)
   - Si le document couvre plusieurs mois, donne la période complète

3. DESCRIPTION:
   - Courte description du contenu (1 phrase)

Retourne un JSON avec cette structure exacte:
{
  "type_document": "releve_bancaire",
  "date_debut": "2024-01-01",
  "date_fin": "2024-03-31",
  "description": "Relevé bancaire LCL du 1er trimestre 2024"
}

IMPORTANT:
- Les dates doivent être au format YYYY-MM-DD
- Si impossible de déterminer une date, utilise null
- Sois précis sur les dates réelles du document

NE retourne QUE le JSON, sans texte avant ou après."""
                    }]
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
            return {
                'type_document': 'inconnu',
                'date_debut': None,
                'date_fin': None,
                'description': f'Erreur: {str(e)}'
            }

    def extraire_evenements(self, batch_size: int = 10, date_debut: str = None, date_fin: str = None) -> List[Dict]:
        """
        Extrait tous les événements du PDF par batch pour éviter les limites de tokens

        Args:
            batch_size: Nombre de pages à traiter par batch (défaut: 10)
            date_debut: Date de début de période (format YYYY-MM-DD, optionnel)
            date_fin: Date de fin de période (format YYYY-MM-DD, optionnel)

        Returns:
            Liste de dictionnaires d'événements prêts pour GestionnaireEvenements
        """
        if not self.client:
            raise ValueError("ANTHROPIC_API_KEY non définie - impossible d'extraire les PDF")

        if not PDF2IMAGE_AVAILABLE:
            raise ImportError("pdf2image non disponible - installer avec: pip install pdf2image")

        if not os.path.exists(self.pdf_path):
            raise FileNotFoundError(f"PDF non trouvé: {self.pdf_path}")

        print(f"📄 Extraction du PDF: {os.path.basename(self.pdf_path)}")

        try:
            # Obtenir le nombre total de pages sans charger toutes les images
            print("🔄 Analyse du PDF...")
            from pdf2image.pdf2image import pdfinfo_from_path
            info = pdfinfo_from_path(self.pdf_path)
            total_pages = info.get('Pages', 0)

            if total_pages == 0:
                print("❌ Impossible de déterminer le nombre de pages")
                return []

            print(f"📄 {total_pages} pages détectées (batch de {batch_size} pages)")

            all_evenements = []

            # Traiter par batch de pages (conversion à la volée)
            for batch_start in range(1, total_pages + 1, batch_size):
                batch_end = min(batch_start + batch_size - 1, total_pages)

                print(f"🔍 Batch {(batch_start-1)//batch_size + 1}/{(total_pages-1)//batch_size + 1}: "
                      f"pages {batch_start}-{batch_end}")

                # Convertir SEULEMENT ce batch (économie mémoire critique)
                batch_images = convert_from_path(
                    self.pdf_path,
                    dpi=100,
                    first_page=batch_start,
                    last_page=batch_end
                )

                # Préparer les images pour Claude
                image_contents = []
                for image in batch_images:
                    buffer = io.BytesIO()
                    image.save(buffer, format='JPEG', quality=85, optimize=True)
                    image_base64 = base64.b64encode(buffer.getvalue()).decode()

                    image_contents.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_base64
                        }
                    })
                    buffer.close()
                    del buffer, image

                # Libérer batch images immédiatement
                del batch_images

                # Analyser ce batch avec Claude
                operations = self._extraire_batch(image_contents, batch_start, batch_end)

                # Libérer image_contents immédiatement
                del image_contents

                # Enrichir avec métadonnées email
                for op in operations:
                    # FILTRE 1: Vérifier la période
                    date_op = op['date_operation']
                    if date_debut and date_op < date_debut:
                        continue  # Ignorer les opérations avant la période
                    if date_fin and date_op > date_fin:
                        continue  # Ignorer les opérations après la période

                    # FILTRE 2: Détecter les soldes d'ouverture (non comptabilisables)
                    libelle_norm = op['libelle'].upper().strip()
                    est_solde_ouverture = any(pattern in libelle_norm for pattern in [
                        'ANCIEN SOLDE',
                        'SOLDE REPORTE',
                        'SOLDE REPORTÉ',
                        'SOLDE PRECEDENT',
                        'SOLDE PRÉCÉDENT',
                        'REPORT SOLDE'
                    ])

                    evenement = {
                        'date_operation': op['date_operation'],
                        'libelle': op['libelle'],
                        'montant': float(op['montant']),
                        'type_operation': op['type_operation'],
                        'est_solde_ouverture': est_solde_ouverture,  # Flag pour exclusion
                        'email_id': self.email_metadata.get('email_id'),
                        'email_from': self.email_metadata.get('email_from', 'pdf_manuel'),
                        'email_date': self.email_metadata.get('email_date', datetime.now()),
                        'email_subject': self.email_metadata.get('email_subject'),
                        'email_body': self.email_metadata.get('email_body', '')
                    }
                    all_evenements.append(evenement)

                print(f"   ✅ {len(operations)} opérations extraites de ce batch")

            print()
            print(f"✅ TOTAL: {len(all_evenements)} opérations extraites")

            # Afficher info sur le filtrage de période
            if date_debut or date_fin:
                periode = f"{date_debut or '...'} → {date_fin or '...'}"
                print(f"📅 Période appliquée: {periode}")

            return all_evenements

        except Exception as e:
            print(f"❌ Erreur extraction PDF: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _extraire_batch(self, image_contents: List[Dict], start_page: int, end_page: int) -> List[Dict]:
        """
        Extrait les opérations d'un batch de pages

        Args:
            image_contents: Liste d'images en base64
            start_page: Numéro de page de début
            end_page: Numéro de page de fin

        Returns:
            Liste d'opérations extraites
        """
        try:
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=8000,
                messages=[{
                    "role": "user",
                    "content": image_contents + [{
                        "type": "text",
                        "text": """Analyse ces pages de relevés bancaires et extrais TOUTES les opérations bancaires individuelles.

Pour CHAQUE opération, extrais:
- date_operation (format YYYY-MM-DD)
- libelle (texte complet de l'opération, regroupé sur une ligne)
- montant (nombre décimal positif)
- type_operation (DEBIT ou CREDIT)

IMPORTANT:
- Certaines opérations s'étalent sur plusieurs lignes (ex: prêt avec numéro de dossier)
- Regroupe les lignes qui forment une seule opération
- Utilise la colonne DEBIT ou CREDIT pour déterminer le type
- Ignore les en-têtes, totaux, et lignes de description
- Convertis TOUTES les dates en format YYYY-MM-DD (ajoute l'année si manquante)

Retourne un JSON valide avec cette structure:
{
  "operations": [
    {
      "date_operation": "2024-01-15",
      "libelle": "PRLV SEPA COVEA RISKS",
      "montant": 87.57,
      "type_operation": "DEBIT"
    }
  ]
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
            operations = data.get('operations', [])

            return operations

        except json.JSONDecodeError as e:
            print(f"   ⚠️  Erreur parsing JSON pour pages {start_page}-{end_page}: {e}")
            print(f"   Réponse brute: {response_text[:300]}...")
            return []
        except Exception as e:
            print(f"   ⚠️  Erreur batch pages {start_page}-{end_page}: {e}")
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
    print("EXTRACTEUR PDF - Test")
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
