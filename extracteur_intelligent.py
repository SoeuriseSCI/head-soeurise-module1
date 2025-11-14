#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EXTRACTEUR INTELLIGENT - Analyse Globale par Claude
====================================================

Date: 14/11/2025
Philosophie: S'appuyer sur Claude (intelligence) plutôt que sur du code (règles)

APPROCHE RADICALE:
------------------
Au lieu de :
  1. Extraire toutes les opérations (103)
  2. Grouper par montant
  3. Rapprocher avec règles Python
  4. Filtrer les doublons
  → Complexe, fragile, 78 événements au lieu de 86

On fait :
  1. Claude analyse le PDF COMPLET en une seule fois
  2. Claude identifie les ÉVÉNEMENTS ÉCONOMIQUES RÉELS
  3. Claude distingue automatiquement opération principale vs justificatif
  → Simple, intelligent, 86 événements attendus

PATTERNS QUE CLAUDE DOIT COMPRENDRE:
-------------------------------------
A. Facture + Prélèvement SEPA = 1 seul événement
   → Garde: SEPA (opération bancaire réelle)
   → Justificatif: Facture (détails HT/TVA)

B. Bulletin SCPI + Virement = 1 seul événement
   → Garde: Virement (opération bancaire réelle)
   → Justificatif: Bulletin (annonce)

C. Avis opération VM + Débit relevé = 1 seul événement
   → Garde: Avis (détails ISIN, quantité, prix, commissions)
   → Justificatif: Débit relevé (confirmation)

D. Avis d'écriture + Virement relevé = 1 seul événement
   → Garde: Virement relevé (opération réelle)
   → Justificatif: Avis (confirmation)

E. Échéances prêt mensuelles = événements distincts
   → Chaque mois = 1 événement (pas de rapprochement)

F. Frais bancaires mensuels = événements distincts
   → Chaque mois = 1 événement
"""

import os
import json
import base64
import io
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from anthropic import Anthropic
from pdf2image import convert_from_path


class ExtracteurIntelligent:
    """
    Extracteur qui délègue TOUTE l'analyse à Claude
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialise l'extracteur

        Args:
            api_key: Clé API Anthropic
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.client = Anthropic(api_key=self.api_key)

    def analyser_pdf(self, pdf_path: str, exercice_debut: str, exercice_fin: str) -> Tuple[List[Dict], Dict]:
        """
        Analyse complète du PDF par Claude en une seule fois

        Args:
            pdf_path: Chemin du PDF
            exercice_debut: Date début exercice (format YYYY-MM-DD)
            exercice_fin: Date fin exercice (format YYYY-MM-DD)

        Returns:
            Tuple (evenements, metadata)
            - evenements: Liste des événements économiques uniques
            - metadata: Statistiques d'analyse
        """
        print(f"\n{'='*80}")
        print("ANALYSE INTELLIGENTE DU PDF PAR CLAUDE")
        print(f"{'='*80}\n")

        print(f"📄 PDF: {pdf_path}")
        print(f"📅 Exercice: {exercice_debut} → {exercice_fin}")

        # Convertir PDF en images
        print(f"\n🔄 Conversion PDF → images...")
        images = convert_from_path(pdf_path, dpi=100)
        print(f"   ✓ {len(images)} pages converties")

        # Construire le prompt global
        prompt = self._construire_prompt_global(exercice_debut, exercice_fin, len(images))

        # Préparer les images pour Claude
        content_blocks = [{"type": "text", "text": prompt}]

        for idx, image in enumerate(images, 1):
            # Convertir image PIL → JPEG base64
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=85, optimize=True)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()

            content_blocks.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": image_base64
                }
            })

        # Appel API Claude
        print(f"\n🧠 Envoi à Claude pour analyse globale...")
        print(f"   (cela peut prendre 30-60 secondes)")

        try:
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",  # Haiku 4.5 (cohérence avec le reste du projet)
                max_tokens=16000,  # Besoin de beaucoup de tokens pour 86 événements
                messages=[{
                    "role": "user",
                    "content": content_blocks
                }]
            )

            response_text = response.content[0].text.strip()

            # Parser le JSON
            evenements = self._parser_reponse(response_text)

            print(f"\n✅ Analyse terminée:")
            print(f"   Événements identifiés: {len(evenements)}")

            metadata = {
                'nb_pages': len(images),
                'nb_evenements': len(evenements),
                'model': 'claude-haiku-4-5-20251001',
                'tokens_input': response.usage.input_tokens,
                'tokens_output': response.usage.output_tokens
            }

            print(f"   Tokens: {metadata['tokens_input']} in / {metadata['tokens_output']} out")

            return evenements, metadata

        except Exception as e:
            print(f"\n❌ Erreur API Claude: {e}")
            raise

    def _construire_prompt_global(self, exercice_debut: str, exercice_fin: str, nb_pages: int) -> str:
        """
        Construit le prompt global pour l'analyse complète

        Args:
            exercice_debut: Date début exercice
            exercice_fin: Date fin exercice
            nb_pages: Nombre de pages du PDF

        Returns:
            Prompt texte
        """
        prompt = f"""Tu analyseras un PDF de {nb_pages} pages contenant des éléments destinés à la comptabilité.

📋 COMPOSITION DU DOCUMENT
==========================
- **Relevés bancaires** : mouvements de débit et crédit
- **Documents connexes** : factures, bulletins, avis d'opération, etc.

🎯 RÈGLE FONDAMENTALE
=====================
Il n'y a pas d'opérations en cash. De ce fait, **100% des événements comptables correspondent à des débits ou crédits des relevés**.

Tu devras générer **UN ET UN SEUL événement comptable par opération** de débit ou crédit.

⚠️ Précisions :
- Les **soldes** qui apparaissent sur les relevés ne sont PAS des événements comptables → à ignorer
- Toute opération **en dehors de l'exercice comptable** ({exercice_debut} → {exercice_fin}) doit être ignorée

🔗 RAPPROCHEMENT DES DOCUMENTS CONNEXES
========================================
Tu devras tenter de rapprocher chaque document connexe d'un ou plusieurs événements comptables.

**Critères de rapprochement** :
1. **Montant** de l'opération (égalité stricte)
2. **Date** de l'opération (flexibilité possible de ±1 mois)
3. En cas de doute : **référence** commune (ex: n° de facture dans le libellé du relevé et dans le document)

**Rôle des documents connexes** :
- À conserver comme **justificatifs** (traçabilité et preuve)
- Apportent parfois un éclairage **indispensable** (détails non présents dans le relevé)

**Exemple** : Opération sur valeurs mobilières
- Extraire : nom et ISIN des titres, prix unitaire, quantité
- Décomposer le montant : prix des titres vs commissions/frais

📊 FORMAT DE RÉPONSE
====================
Retourne UNIQUEMENT un JSON valide :

{{
  "evenements": [
    {{
      "date": "2024-01-15",
      "libelle": "Libellé de l'opération bancaire",
      "montant": 200.00,
      "type_operation": "DEBIT",
      "source": "releve",
      "justificatif": "Description du document connexe rapproché (ou null)",
      "categorie": "Type d'événement",
      "details": "Détails supplémentaires si pertinent (ex: ISIN, quantité, décomposition montant)"
    }}
  ],
  "alertes": [
    "Document connexe page X non rapproché à un événement (montant Y, date Z)"
  ]
}}

🚨 RÈGLES CRITIQUES
===================
1. **N'extraire que ce qui est présent** dans le PDF
2. **Ne jamais inventer** d'événement
3. En cas de **difficulté de rapprochement** d'un document connexe : le signaler dans "alertes"

🚀 Analyse les {nb_pages} pages et retourne le JSON."""

        return prompt

    def _parser_reponse(self, response_text: str) -> List[Dict]:
        """
        Parse la réponse JSON de Claude

        Args:
            response_text: Texte de réponse de Claude

        Returns:
            Liste des événements
        """
        # Trouver le JSON dans la réponse
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1

        if start_idx < 0 or end_idx <= start_idx:
            raise ValueError("Pas de JSON trouvé dans la réponse de Claude")

        json_text = response_text[start_idx:end_idx]
        data = json.loads(json_text)

        evenements = data.get('evenements', [])

        # Afficher les stats si disponibles
        if 'stats' in data:
            stats = data['stats']
            print(f"\n📊 Statistiques Claude:")
            print(f"   Total événements: {stats.get('total_evenements', 0)}")
            if 'par_categorie' in stats:
                print(f"   Par catégorie:")
                for cat, count in stats['par_categorie'].items():
                    print(f"      • {cat}: {count}")

        return evenements


def test_extracteur_intelligent():
    """
    Test de l'extracteur intelligent sur le PDF T1-T3 2024
    """
    print("="*80)
    print("TEST EXTRACTEUR INTELLIGENT - PDF T1-T3 2024")
    print("="*80)

    pdf_path = "Elements Comptables des 1-2-3T2024.pdf"

    if not os.path.exists(pdf_path):
        print(f"\n❌ PDF non trouvé: {pdf_path}")
        return

    extracteur = ExtracteurIntelligent()

    evenements, metadata = extracteur.analyser_pdf(
        pdf_path=pdf_path,
        exercice_debut="2024-01-01",
        exercice_fin="2024-12-31"
    )

    print(f"\n{'='*80}")
    print("RÉSULTATS")
    print(f"{'='*80}")
    print(f"\nÉvénements extraits: {len(evenements)}")
    print(f"Attendu: 86")
    print(f"Écart: {abs(len(evenements) - 86)}")

    if abs(len(evenements) - 86) <= 3:
        print(f"\n✅ SUCCÈS - Résultat cohérent avec analyse manuelle!")
    else:
        print(f"\n⚠️ ATTENTION - Écart significatif, vérification requise")

    # Sauvegarder les résultats
    output_file = "resultats_extracteur_intelligent.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'evenements': evenements,
            'metadata': metadata
        }, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Résultats sauvegardés: {output_file}")


if __name__ == '__main__':
    test_extracteur_intelligent()
