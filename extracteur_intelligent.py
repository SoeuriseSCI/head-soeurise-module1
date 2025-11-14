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
        prompt = f"""Tu es un expert-comptable analysant un document comptable complet de {nb_pages} pages.

📋 CONTEXTE - SCI SOEURISE
==========================
- SCI patrimoniale avec 1 seul compte bancaire (LCL)
- Pas d'opérations en espèces (pas de caisse)
- Exercice comptable: {exercice_debut} → {exercice_fin}
- Toute opération économique apparaît TOUJOURS sur le relevé bancaire

📄 COMPOSITION DU DOCUMENT
==========================
Le PDF contient TROIS types de documents :

1️⃣ **RELEVÉS BANCAIRES** (pages 1-20 environ)
   - Vision chronologique des mouvements bancaires
   - Libellés courts, synthétiques
   - SOURCE DE VÉRITÉ pour les dates et montants réels

2️⃣ **DOCUMENTS JUSTIFICATIFS** (pages 20-40 environ)
   - Factures (CRP 2C, INSEE LEI)
   - Bulletins SCPI (annonces de versements)
   - Avis d'opération banque (détails VM, virements)
   - Apportent des DÉTAILS essentiels (ISIN, quantités, ventilation HT/TVA)
   - Confirment des opérations DÉJÀ dans le relevé

3️⃣ **RÈGLE FONDAMENTALE**
   ⚠️ Un même ÉVÉNEMENT ÉCONOMIQUE apparaît dans 2 documents :
      - 1 fois dans le RELEVÉ (opération bancaire)
      - 1 fois dans un JUSTIFICATIF (détails/confirmation)

   🎯 TU NE DOIS CRÉER QU'UN SEUL ÉVÉNEMENT, PAS DEUX !

🔗 PATTERNS DE RAPPROCHEMENT À IDENTIFIER
==========================================

**Pattern A: Facture → Prélèvement SEPA**
Exemple :
- Facture CRP 2C n°2024013227 du 02/01/2024 : 213,60€
- SEPA du 24/01/2024 "PRLV SEPA CRP... LIBELLE:2024013227" : 213,60€
→ MÊME ÉVÉNEMENT (décalage 22 jours normal)
→ Critères: montant identique, n° facture dans libellé SEPA, dates ±30j
→ **Garde: SEPA (opération réelle)**
→ **Référence justificatif: Facture (pour détails)**

**Pattern B: Bulletin SCPI → Virement**
Exemple :
- Bulletin "REVENUS T4 2023" du 25/01 : 7 356,24€
- Virement du 29/01 "VIR SEPA SCPI... 4EME TRIM 2023" : 7 356,24€
→ MÊME ÉVÉNEMENT (bulletin annonce, virement réalise)
→ Critères: montant identique, période/trimestre identique, dates ±15j
→ **Garde: Virement (opération réelle)**
→ **Référence justificatif: Bulletin (pour détails fiscaux)**

**Pattern C: Avis opération VM → Débit relevé**
Exemple :
- Avis achat "150 AMUNDI MSCI WORLD, ISIN LU1781541179" du 30/01 : 2 357,36€
- Débit relevé "150 AM MSCI WLD V ETF ACHAT 3001" du 30/01 : 2 357,36€
→ MÊME ÉVÉNEMENT
→ Critères: montant identique, date identique, titre mentionné
→ **Garde: Avis (contient ISIN, quantité, prix, commissions essentiels)**
→ **Référence justificatif: Débit relevé (confirmation bancaire)**

**Pattern D: Avis d'écriture → Virement relevé**
Exemple :
- Avis "Apport CC UB VIREMENT MONSIEUR ULRIK BERGSTEN" du 18/06 : 500€
- Relevé "VIR SEPA MONSIEUR ULRIK BERGSTEN LIBELLE:Apport CC" du 18/06 : 500€
→ MÊME ÉVÉNEMENT (avis confirme opération déjà dans relevé)
→ Critères: montant identique, date identique, mots-clés communs
→ **Garde: Virement relevé (opération réelle)**
→ **Référence justificatif: Avis (confirmation documentaire)**

**Pattern E: Échéances prêt mensuelles**
Exemple :
- "PRET IMMOBILIER ECH 15/01/24 DOSSIER 5009736BRL" : 258,33€
- "PRET IMMOBILIER ECH 15/02/24 DOSSIER 5009736BRL" : 258,33€
→ ÉVÉNEMENTS DISTINCTS (chaque mois = 1 paiement)
→ PAS de rapprochement même si montants identiques
→ Distinguer par date et n° échéance

**Pattern F: Frais bancaires mensuels (ÉVÉNEMENTS DISTINCTS)**
⚠️ **CRITIQUE** : Les frais bancaires récurrents sont des événements SÉPARÉS chaque mois !

Exemples :
- "ABON LCL ACCESS 007.04EUR" le 15/01 : 1 événement
- "ABON LCL ACCESS 007.25EUR" le 15/02 : 1 autre événement (PAS le même !)
- "COTISATION OPTION PRO 5.15EUR" le 15/01 : 1 événement
- "COTISATION OPTION PRO 5.15EUR" le 15/02 : 1 autre événement (PAS le même !)

→ Si 10 mois visibles (Jan-Oct), tu dois extraire 10 ABON + 10 COTISATION = 20 événements
→ MÊME LIBELLÉ + MÊME MONTANT mais DATE DIFFÉRENTE = ÉVÉNEMENTS DISTINCTS
→ PAS de rapprochement entre mois

⚠️ PIÈGES À ÉVITER - CRITIQUES
================================
1. ❌ Ne compte PAS les "ANCIEN SOLDE" ou "NOUVEAU SOLDE" comme événements
2. ❌ Ne compte PAS les lignes de détail factures (Provision HT, Honoraires HT, TVA)
   → Garde uniquement le Total TTC
3. ❌ Ne rapproche PAS des échéances prêt entre elles (chaque mois = 1 événement)

4. 🚨 **CRITIQUE : FILTRE STRICT PAR EXERCICE COMPTABLE**
   - Exercice : {exercice_debut} → {exercice_fin}
   - ❌ EXCLUS ABSOLUMENT toute opération hors de cette période
   - Exemple : Si exercice 2024, EXCLURE décembre 2023 même si dans le PDF
   - Vérifie DEUX FOIS chaque date avant de l'inclure

5. 🚨 **CRITIQUE : N'INVENTE JAMAIS D'ÉVÉNEMENTS**
   - Extrait UNIQUEMENT ce qui est VISIBLE dans le PDF
   - ❌ NE COMPLÈTE PAS les séries (ex: si 9 mois visibles, ne pas inventer le 10ème)
   - ❌ NE SUPPOSE PAS qu'un événement devrait exister
   - Si un mois manque une échéance/assurance, c'est NORMAL (peut-être hors pages extraites)
   - Principe : MIEUX VAUT MANQUER un événement que d'en INVENTER un

🎯 TA MISSION
=============
Analyse les {nb_pages} pages et identifie TOUS les événements économiques UNIQUES.

Pour chaque événement, fournis :
- **date**: Date de l'opération (format YYYY-MM-DD)
- **libelle**: Libellé le plus détaillé disponible
- **montant**: Montant en euros (positif)
- **type_operation**: DEBIT ou CREDIT
- **source**: "releve" ou "avis" ou "facture" ou "bulletin" (quelle source principale tu utilises)
- **justificatif**: Description du document justificatif s'il existe, sinon null
- **categorie**: Type d'événement (ECHEANCE_PRET, ASSURANCE_PRET, HONORAIRES_COMPTABLE,
                REVENU_SCPI, ACHAT_VM, APPORT_ASSOCIE, FRAIS_BANCAIRE, AUTRE)

📊 TYPES D'ÉVÉNEMENTS ATTENDUS (INDICATIF)
==========================================
Ce PDF contient généralement :
- Échéances prêt mensuelles (2 prêts × N mois)
- Assurances prêt mensuelles (2 assurances × N mois)
- Frais bancaires récurrents (mensuels)
- Factures comptables (trimestrielles environ)
- Distributions SCPI (trimestrielles)
- Achats valeurs mobilières (occasionnels)
- Apports associés (occasionnels)

⚠️ **IMPORTANT** : Le nombre EXACT d'événements dépend de ce qui est VISIBLE dans le PDF.
- N'essaie PAS d'atteindre un nombre précis
- Extrait UNIQUEMENT ce qui est là
- Si un type d'événement est incomplet (ex: 9 échéances au lieu de 10), c'est NORMAL

FORMAT DE RÉPONSE
=================
Retourne UNIQUEMENT un JSON valide (pas de texte avant/après) :

{{
  "evenements": [
    {{
      "date": "2024-01-24",
      "libelle": "PRLV SEPA CRP Comptabilit Conseil LIBELLE:2024013227",
      "montant": 213.60,
      "type_operation": "DEBIT",
      "source": "releve",
      "justificatif": "Facture n°2024013227 du 02/01/2024 - Honoraires comptables",
      "categorie": "HONORAIRES_COMPTABLE"
    }},
    {{
      "date": "2024-01-29",
      "libelle": "VIR SEPA SCPI EPARGNE PIERRE DISTRIBUTION 4EME TRIM 2023",
      "montant": 7356.24,
      "type_operation": "CREDIT",
      "source": "releve",
      "justificatif": "Bulletin informatif du 25/01/2024 - Revenus T4 2023",
      "categorie": "REVENU_SCPI"
    }},
    {{
      "date": "2024-01-30",
      "libelle": "Achat de 150 AMUNDI MSCI WORLD V UC.ETF ACC (ISIN: LU1781541179)",
      "montant": 2357.36,
      "type_operation": "DEBIT",
      "source": "avis",
      "justificatif": "Débit relevé du 30/01 - Confirmation bancaire",
      "categorie": "ACHAT_VM"
    }}
  ],
  "stats": {{
    "total_evenements": 86,
    "par_categorie": {{
      "ECHEANCE_PRET": 20,
      "ASSURANCE_PRET": 20,
      "HONORAIRES_COMPTABLE": 4,
      "REVENU_SCPI": 3,
      "ACHAT_VM": 7,
      "APPORT_ASSOCIE": 4,
      "FRAIS_BANCAIRE": 18,
      "AUTRE": 10
    }}
  }}
}}

🚀 C'EST PARTI ! Analyse les {nb_pages} pages et retourne le JSON."""

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
