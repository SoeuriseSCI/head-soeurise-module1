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
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from anthropic import Anthropic

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

    def extraire_evenements(self) -> List[Dict]:
        """
        Extrait tous les événements du PDF

        Returns:
            Liste de dictionnaires d'événements prêts pour GestionnaireEvenements
        """
        if not self.client:
            raise ValueError("ANTHROPIC_API_KEY non définie - impossible d'extraire les PDF")

        if not os.path.exists(self.pdf_path):
            raise FileNotFoundError(f"PDF non trouvé: {self.pdf_path}")

        print(f"📄 Extraction du PDF: {os.path.basename(self.pdf_path)}")

        # Lire le PDF en base64
        with open(self.pdf_path, 'rb') as f:
            pdf_data = f.read()

        import base64
        pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')

        # Analyser le PDF avec Claude Vision
        print("🔍 Analyse du PDF avec Claude Vision...")

        try:
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=8000,
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
                            "text": """Analyse ce PDF de relevés bancaires et extrais TOUTES les opérations bancaires individuelles.

Pour CHAQUE opération, extrais:
- date_operation (format YYYY-MM-DD)
- libelle (texte complet de l'opération, sur une ou plusieurs lignes)
- montant (nombre décimal positif)
- type_operation (DEBIT ou CREDIT)

IMPORTANT:
- Certaines opérations s'étalent sur plusieurs lignes (ex: prêt immobilier avec numéro de dossier)
- Regroupe les lignes qui forment une seule opération
- Utilise la colonne DEBIT ou CREDIT pour déterminer le type
- Ignore les en-têtes, totaux, et lignes de description
- Convertis TOUTES les dates en format YYYY-MM-DD (ajoute l'année appropriée si manquante)

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

            # Extraire le JSON de la réponse
            response_text = response.content[0].text

            # Nettoyer la réponse (enlever les balises markdown si présentes)
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

            print(f"✅ {len(operations)} opérations extraites")

            # Enrichir avec les métadonnées de l'email
            evenements = []
            for op in operations:
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
                evenements.append(evenement)

            return evenements

        except json.JSONDecodeError as e:
            print(f"❌ Erreur parsing JSON: {e}")
            print(f"Réponse brute: {response_text[:500]}")
            return []
        except Exception as e:
            print(f"❌ Erreur extraction PDF: {e}")
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
