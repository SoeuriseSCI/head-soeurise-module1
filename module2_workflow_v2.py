"""
MODULE 2 WORKFLOW V2 - WORKFLOW COMPTABLE (FIXED)
==========================================
Détection d'événements, parsing PDFs, génération propositions (7 phases du flux global)

FIX: Ajouter Enum TypeEvenement pour résoudre import error

Phases couverts par ce fichier:
1️⃣ Fetch emails
2️⃣ Détection type d'événement (SIMPLE | INIT_BILAN_2023 | CLOTURE_EXERCICE)
3️⃣ Branche spécifique (parsing, extraction)

Sortie: Propositions Markdown + JSON + Token MD5
(Pour envoi à Ulrik dans module2_workflow_v2_branches.py)
"""

import re
import json
import hashlib
import io
import os
import smtplib
import tempfile
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from decimal import Decimal
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

import anthropic

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False


# ═══════════════════════════════════════════════════════════════════════════════
# TYPE ÉVÉNEMENT (ENUM) - FIX IMPORT ERROR
# ═══════════════════════════════════════════════════════════════════════════════

class TypeEvenement(Enum):
    """Types d'événements comptables détectables"""
    EVENEMENT_SIMPLE = "EVENEMENT_SIMPLE"
    INIT_BILAN_2023 = "INIT_BILAN_2023"
    CLOTURE_EXERCICE = "CLOTURE_EXERCICE"
    PRET_IMMOBILIER = "PRET_IMMOBILIER"
    UNKNOWN = "UNKNOWN"


# ═══════════════════════════════════════════════════════════════════════════════
# 1. OCR EXTRACTOR
# ═══════════════════════════════════════════════════════════════════════════════

class OCRExtractor:
    """Extraction de texte depuis PDF via Claude Vision (si pdf2image dispo)"""

    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        self.api_key = api_key
        self.model = model
        self.client = anthropic.Anthropic(api_key=api_key)

    def extract_from_pdf(self, filepath: str, prompt: str = None, max_tokens: int = 2000) -> str:
        """
        Extrait texte d'un PDF via OCR Claude Vision

        Args:
            filepath: Chemin du PDF
            prompt: Prompt personnalisé pour Claude (ex: "Extrait le tableau amortissement")
            max_tokens: Limite de tokens en sortie (défaut: 2000, max recommandé: 8000)

        Returns:
            Texte OCRisé du PDF
        """
        if not PDF2IMAGE_AVAILABLE:
            raise ImportError("pdf2image non disponible - installer avec: pip install pdf2image pdf2image poppler-utils")

        try:
            # Convertir PDF → images (JPEG)
            images = convert_from_path(filepath, dpi=150)

            if not images:
                raise ValueError(f"PDF vide ou non lisible: {filepath}")

            # On traite les 20 premières pages maximum
            max_pages = min(20, len(images))
            extracted_text = []

            for page_num, image in enumerate(images[:max_pages]):
                # Convertir image PIL → JPEG base64
                buffer = io.BytesIO()
                image.save(buffer, format='JPEG')
                image_base64 = __import__('base64').b64encode(buffer.getvalue()).decode()

                # Envoyer à Claude Vision
                user_prompt = prompt or "Extrait TOUT le texte visible. Format texte brut uniquement."

                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    messages=[{
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": image_base64
                                }
                            },
                            {"type": "text", "text": user_prompt}
                        ]
                    }]
                )

                page_text = response.content[0].text
                extracted_text.append(f"--- Page {page_num+1} ---\n{page_text}")

            return "\n\n".join(extracted_text)

        except Exception as e:
            raise ValueError(f"Erreur OCR PDF {filepath}: {str(e)}")


# ═══════════════════════════════════════════════════════════════════════════════
# 2. DÉTECTEUR TYPE ÉVÉNEMENT (RETOURNE ENUM)
# ═══════════════════════════════════════════════════════════════════════════════

class DetecteurTypeEvenement:
    """Détecte le type d'événement comptable depuis un email"""
    
    @staticmethod
    def detecter(email: Dict) -> TypeEvenement:
        """
        Détecte le type d'événement
        
        Returns:
            TypeEvenement enum (EVENEMENT_SIMPLE | INIT_BILAN_2023 | CLOTURE_EXERCICE | UNKNOWN)
        """
        body = (email.get('body', '') + ' ' + email.get('subject', '')).lower()
        subject = email.get('subject', '').lower()
        attachments = email.get('attachments', [])

        # Détecteur PRET_IMMOBILIER (AVANT CLOTURE_EXERCICE car "amortissement" est commun)
        # Détecte: "tableau" + "amortissement" + "pret" dans filename ou body
        if any(f['filename'].lower().endswith('.pdf') and
               'amortissement' in f['filename'].lower() and
               ('pret' in f['filename'].lower() or 'prêt' in f['filename'].lower() or 'tableau' in f['filename'].lower())
               for f in attachments if 'filename' in f):
            return TypeEvenement.PRET_IMMOBILIER

        if any(kw in body for kw in ['tableau amortissement', 'tableau d\'amortissement', 'prêt immobilier', 'pret immobilier']):
            return TypeEvenement.PRET_IMMOBILIER

        # Détecteur CLOTURE_EXERCICE
        if any(kw in body for kw in ['cloture', 'clôture', 'amortissement_credit', 'reevaluation', 'réévaluation']):
            return TypeEvenement.CLOTURE_EXERCICE

        if any(f['filename'].lower().endswith('.pdf') and any(kw in f['filename'].lower()
               for kw in ['amortissement', 'credit', 'reevaluation', 'cloture'])
               for f in attachments if 'filename' in f):
            return TypeEvenement.CLOTURE_EXERCICE
        
        # Détecteur INIT_BILAN_2023
        if any(kw in body for kw in ['bilan 2023', 'bilan_2023', 'bilan initial', 'initialisation comptable',
                                      'bilan d\'ouverture', 'bilan ouverture', "bilan d'ouverture"]):
            return TypeEvenement.INIT_BILAN_2023
        
        if any(f['filename'].lower().endswith('.pdf') and 'bilan' in f['filename'].lower() and '2023' in f['filename'].lower()
               for f in attachments if 'filename' in f):
            return TypeEvenement.INIT_BILAN_2023
        
        # Détecteur EVENEMENT_SIMPLE (loyer, charge, etc.)
        if any(kw in body for kw in ['loyer', 'location', 'paiement', 'charge', 'entretien', 
                                       'réparation', 'assurance', 'taxe', 'syndic', '€', 'eur']):
            return TypeEvenement.EVENEMENT_SIMPLE
        
        return TypeEvenement.UNKNOWN


# ═══════════════════════════════════════════════════════════════════════════════
# 3. PARSEUR BILAN 2023
# ═══════════════════════════════════════════════════════════════════════════════

class ParseurBilan2023:
    """Parse un PDF bilan 2023 et extrait les comptes avec soldes"""
    
    def __init__(self, ocr_extractor: OCRExtractor):
        self.ocr = ocr_extractor
    
    def parse_from_pdf(self, filepath: str) -> List[Dict]:
        """
        Parse bilan 2023 depuis PDF
        
        Returns:
            [{"compte": "101", "libelle": "Capital", "solde": 100000}, ...]
        """
        # OCRiser le PDF
        texte_brut = self.ocr.extract_from_pdf(
            filepath,
            prompt="Extrait le tableau bilan 2023 avec colonnes: N° compte | Libellé | Solde"
        )
        
        # Parser le texte
        comptes = self._parser_texte_bilan(texte_brut)
        return comptes
    
    @staticmethod
    def _parser_texte_bilan(texte: str) -> List[Dict]:
        """Parse tableau bilan depuis texte OCRisé"""
        comptes = []
        
        # Pattern: "101  Capital    100000" ou "101 | Capital | 100000"
        # On cherche des lignes avec: numéro (1-3 chiffres) | texte | nombre
        pattern = r'(\d{1,3})\s+([A-Za-z\s]+?)\s+(\d+(?:[.,]\d+)*)'
        
        matches = re.finditer(pattern, texte)
        for match in matches:
            num_compte = match.group(1)
            libelle = match.group(2).strip()
            solde_str = match.group(3).replace(',', '.')
            
            try:
                solde = float(solde_str)
                comptes.append({
                    "compte": num_compte,
                    "libelle": libelle,
                    "solde": solde
                })
            except ValueError:
                continue
        
        return comptes


# ═══════════════════════════════════════════════════════════════════════════════
# 4. PARSEUR AMORTISSEMENT CRÉDIT
# ═══════════════════════════════════════════════════════════════════════════════

class ParseurAmortissementCredit:
    """Parse tableau amortissement crédit et extrait totaux principal/intérêts"""
    
    def __init__(self, ocr_extractor: OCRExtractor):
        self.ocr = ocr_extractor
    
    def parse_from_pdf(self, filepath: str, annee: int = 2023) -> Dict:
        """
        Parse tableau amortissement depuis PDF
        
        Returns:
            {
              "total_principal_paye": 18000,
              "total_interets_payes": 6000,
              "details": [(mois, principal, interets), ...]
            }
        """
        texte_brut = self.ocr.extract_from_pdf(
            filepath,
            prompt=f"Extrait le tableau d'amortissement pour {annee} avec colonnes: Mois | Principal | Intérêts | Solde"
        )
        
        result = self._parser_tableau_amortissement(texte_brut, annee)
        return result
    
    @staticmethod
    def _parser_tableau_amortissement(texte: str, annee: int) -> Dict:
        """Parse tableau amortissement depuis texte OCRisé"""
        details = []
        total_principal = Decimal('0')
        total_interets = Decimal('0')
        
        # Pattern: "Jan 23  1500  500  98500" ou "January 2023  1500.00  500.00  98500.00"
        # Cherche: (mois/date) | nombre | nombre | nombre
        pattern = r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|1|2|3|4|5|6|7|8|9|10|11|12).*?(\d+(?:[.,]\d+)?)\s+(\d+(?:[.,]\d+)?)\s+(\d+(?:[.,]\d+)?)'
        
        matches = re.finditer(pattern, texte, re.IGNORECASE)
        for match in matches:
            try:
                principal_str = match.group(2).replace(',', '.')
                interets_str = match.group(3).replace(',', '.')
                solde_str = match.group(4).replace(',', '.')
                
                principal = Decimal(principal_str)
                interets = Decimal(interets_str)
                solde = Decimal(solde_str)
                
                details.append({
                    "principal": float(principal),
                    "interets": float(interets),
                    "solde": float(solde)
                })
                
                total_principal += principal
                total_interets += interets
            except (ValueError, IndexError):
                continue
        
        return {
            "total_principal_paye": float(total_principal),
            "total_interets_payes": float(total_interets),
            "details": details,
            "nb_periodes": len(details)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# 4b. PARSEUR TABLEAU PRÊT COMPLET (Ingestion données de référence)
# ═══════════════════════════════════════════════════════════════════════════════

class ParseurTableauPret:
    """
    Parse tableau d'amortissement COMPLET pour ingestion en BD de référence

    Objectif : Extraire TOUTES les échéances ligne par ligne avec ventilation
               intérêts/capital pour chaque date

    Usage : Appelé lors détection PRET_IMMOBILIER pour stocker données de référence
    """

    def __init__(self, ocr_extractor: OCRExtractor):
        self.ocr = ocr_extractor

    def parse_from_pdf(self, filepath: str) -> Dict:
        """
        Parse tableau amortissement complet depuis PDF

        APPROCHE HYBRIDE (V8 - Scénario B):
        - Extrait le contrat + les 24 PREMIÈRES ÉCHÉANCES via Claude Vision (données réelles avec différés)
        - Génère les échéances RESTANTES mathématiquement (mois 25+)

        Avantages:
        - ✅ Garde les données officielles LCL pour 2023-2024 (différés complexes)
        - ✅ Génère le futur mathématiquement (précis et rapide)
        - ✅ Économise tokens/coûts (4000 au lieu de 8000+)

        Args:
            filepath: Chemin vers PDF tableau amortissement

        Returns:
            {
              "pret": {
                "numero_pret": "5009736BRM0911AH",
                "banque": "LCL",
                "montant_initial": 250000.00,
                "taux_annuel": 0.0105,
                "duree_mois": 240,
                "date_debut": "2023-04-15",
                "date_fin": "2043-04-15",
                "type_amortissement": "AMORTISSEMENT_CONSTANT",
                "echeance_mensuelle": 1166.59,
                "mois_franchise": 0
              },
              "echeances": [
                {
                  "numero_echeance": 1,
                  "date_echeance": "2023-05-15",
                  "montant_total": 1166.59,
                  "montant_interet": 218.75,
                  "montant_capital": 947.84,
                  "capital_restant_du": 249052.16
                },
                ... (1-24 extraites du PDF, 25+ générées mathématiquement)
              ]
            }
        """
        # Prompt pour extraction CONTRAT + 24 PREMIÈRES ÉCHÉANCES
        prompt = """
Analyse ce tableau d'amortissement de prêt immobilier du Crédit Lyonnais (LCL).

RETOURNE UN OBJET JSON VALIDE avec cette structure:

{
  "pret": {
    "numero_pret": "5009736BRLZE11AQ",
    "banque": "CREDIT_LYONNAIS",
    "montant_initial": 250000.00,
    "taux_annuel": 0.0124,
    "duree_mois": 216,
    "date_debut": "2022-04-15",
    "date_fin": "2040-04-15",
    "type_amortissement": "FRANCHISE_PARTIELLE",
    "echeance_mensuelle": 258.33,
    "mois_franchise": 12
  },
  "echeances": [
    {
      "numero_echeance": 1,
      "date_echeance": "2023-05-15",
      "montant_total": 258.33,
      "montant_interet": 258.33,
      "montant_capital": 0.00,
      "capital_restant_du": 250000.00
    },
    ... (EXTRAIT UNIQUEMENT LES 24 PREMIÈRES LIGNES DU TABLEAU)
  ]
}

INSTRUCTIONS CONTRAT:
- numero_pret: "N° DU PRET : XXXX"
- montant_initial: "MONTANT TOTAL DEBLOQUE : EUR XXX" (espaces = milliers)
- taux_annuel: format décimal (1.24% = 0.0124)
- duree_mois: durée totale en mois
- dates: format YYYY-MM-DD
- type_amortissement: "AMORTISSEMENT_CONSTANT" ou "FRANCHISE_PARTIELLE"
- echeance_mensuelle: montant mensuel régulier
- mois_franchise: nombre mois différé (capital = 0)

INSTRUCTIONS ÉCHÉANCES:
CRITIQUE: Tu DOIS extraire EXACTEMENT 24 échéances, pas moins !

Méthode d'extraction:
1. IGNORER toutes les lignes "DBL" (double month, format DBL)
2. IGNORER la PREMIÈRE ligne "ECH" (c'est le header du tableau)
3. À partir de là, EXTRAIRE LES 24 LIGNES SUIVANTES qui contiennent des dates d'échéances:
   - Ces 24 lignes incluent les lignes "ECH" (après la première) ET les lignes numérotées
   - Format ECH : "ECH  15/05/2023  258.00€  0.00€  250000.00€"
   - Format numéroté : "014  15/04/2024  1166.00€  951.27€  249048.73€"

Structure attendue (exemple):
- Lignes DBL → IGNORER
- Ligne "ECH 15/05/2023" (première ECH) → IGNORER
- Ligne "ECH 15/06/2023" → EXTRAIRE (1/24)
- Ligne "ECH 15/07/2023" → EXTRAIRE (2/24)
- ... (10 autres lignes ECH)
- Ligne "014 15/04/2024" → EXTRAIRE (13/24)
- Ligne "015 15/05/2024" → EXTRAIRE (14/24)
- ... (10 autres lignes numérotées)
- Ligne "025 15/03/2025" → EXTRAIRE (24/24) ← DERNIÈRE LIGNE À EXTRAIRE

VÉRIFICATION: Si tu n'as pas 24 échéances dans ta liste, CONTINUE À EXTRAIRE !

- numero_echeance: numéro séquentiel (1, 2, 3... pour toutes les lignes)
- date_echeance: date de paiement (YYYY-MM-DD)
- montant_total: montant total de l'échéance
- montant_interet: part intérêts
- montant_capital: part capital (0 pendant franchise/ECH)
- capital_restant_du: capital restant après paiement

IMPORTANT:
- NE T'ARRÊTE PAS avant d'avoir 24 échéances !
- Les autres échéances (25+) seront calculées automatiquement
"""

        # Extraire avec 8000 tokens pour garantir les 24 échéances complètes
        texte_brut = self.ocr.extract_from_pdf(filepath, prompt=prompt, max_tokens=8000)

        # Parser le JSON (contrat + échéances extraites)
        data = self._parser_json_hybrid(texte_brut)

        if not data or '_erreur' in data.get('pret', {}):
            # Erreur de parsing
            return data

        contract_data = data['pret']
        echeances_extraites = data.get('echeances', [])

        # Valider duree_mois (éviter NoneType comparison)
        duree_mois = contract_data.get('duree_mois', 0)
        if not duree_mois or duree_mois <= 0:
            return {
                "pret": {
                    **contract_data,
                    "_erreur": f"duree_mois invalide: {duree_mois}"
                },
                "echeances": []
            }

        # Dédupliquer les échéances extraites par date (au cas où doublon ECH + numérotée)
        dates_vues = set()
        echeances_dedupliquees = []
        for ech in echeances_extraites:
            date_ech = ech.get('date_echeance')
            if date_ech not in dates_vues:
                dates_vues.add(date_ech)
                echeances_dedupliquees.append(ech)
            else:
                print(f"[PARSING] Doublon détecté et ignoré: {date_ech}", flush=True)

        echeances_extraites = echeances_dedupliquees

        # Générer les échéances restantes (mois 25+)
        print(f"[PARSING] Échéances extraites (après dédup): {len(echeances_extraites)}, duree_mois: {duree_mois}", flush=True)
        if len(echeances_extraites) > 0:
            print(f"[PARSING] Dernière échéance extraite: {echeances_extraites[-1].get('date_echeance')}", flush=True)

        if len(echeances_extraites) < duree_mois:
            start_month_calc = len(echeances_extraites) + 1
            print(f"[PARSING] Génération depuis mois {start_month_calc} jusqu'à {duree_mois}", flush=True)
            echeances_generees = self._generer_echeances(
                contract_data,
                start_month=start_month_calc,
                echeances_precedentes=echeances_extraites
            )
            print(f"[PARSING] Échéances générées: {len(echeances_generees)}", flush=True)
            # Combiner: extraites + générées
            echeances_completes = echeances_extraites + echeances_generees
        else:
            echeances_completes = echeances_extraites

        return {
            "pret": contract_data,
            "echeances": echeances_completes
        }

    @staticmethod
    def _parser_json_contract(texte: str) -> Dict:
        """
        Parse JSON du contrat depuis réponse Claude (robuste aux variations)

        Retourne directement l'objet contrat, ou dict avec _erreur si échec
        """
        import json
        import re

        try:
            # Nettoyer le texte
            texte = texte.strip()

            # Cas 1: JSON dans code block markdown
            if '```json' in texte:
                match = re.search(r'```json\s*(\{.*?\})\s*```', texte, re.DOTALL)
                if match:
                    texte = match.group(1)
            elif '```' in texte:
                match = re.search(r'```\s*(\{.*?\})\s*```', texte, re.DOTALL)
                if match:
                    texte = match.group(1)

            # Cas 2: JSON direct avec texte avant/après
            match = re.search(r'(\{.*\})', texte, re.DOTALL)
            if match:
                texte = match.group(1)

            # Parser le JSON
            data = json.loads(texte)

            # Valider structure minimale du contrat
            if not isinstance(data, dict):
                return {
                    "_erreur": "Réponse non-dict",
                    "_raw": texte[:200]
                }

            # Vérifier champs critiques du contrat
            champs_critiques = ['numero_pret', 'montant_initial', 'taux_annuel', 'duree_mois']
            champs_manquants = [c for c in champs_critiques if c not in data]

            if champs_manquants:
                return {
                    "_erreur": f"Champs critiques manquants: {', '.join(champs_manquants)}",
                    "_raw": str(data)[:200]
                }

            # Vérifier que les valeurs sont valides
            if not data['numero_pret'] or len(str(data['numero_pret'])) < 5:
                return {
                    "_erreur": "numero_pret invalide (trop court)",
                    "_raw": str(data)[:200]
                }

            if data['montant_initial'] <= 0:
                return {
                    "_erreur": "montant_initial doit être > 0",
                    "_raw": str(data)[:200]
                }

            if data['taux_annuel'] <= 0 or data['taux_annuel'] > 0.2:
                return {
                    "_erreur": f"taux_annuel invalide: {data['taux_annuel']} (doit être entre 0 et 0.2)",
                    "_raw": str(data)[:200]
                }

            if data['duree_mois'] <= 0 or data['duree_mois'] > 600:
                return {
                    "_erreur": f"duree_mois invalide: {data['duree_mois']} (doit être entre 1 et 600)",
                    "_raw": str(data)[:200]
                }

            # S'assurer que mois_franchise existe (défaut: 0)
            if 'mois_franchise' not in data:
                data['mois_franchise'] = 0

            # S'assurer que type_amortissement existe
            if 'type_amortissement' not in data:
                data['type_amortissement'] = 'AMORTISSEMENT_CONSTANT'

            # Normaliser la banque
            if 'banque' not in data:
                data['banque'] = 'LCL'

            return data

        except json.JSONDecodeError as e:
            return {
                "_erreur": f"JSON invalide: {str(e)[:100]}",
                "_raw": texte[:300]
            }
        except Exception as e:
            return {
                "_erreur": f"Erreur parsing contrat: {str(e)[:100]}",
                "_raw": texte[:300]
            }

    @staticmethod
    def _parser_json_hybrid(texte: str) -> Dict:
        """
        Parse JSON hybride contenant contrat + échéances extraites (approche Scénario B)

        Retourne: {
            "pret": {...},
            "echeances": [...]  # Échéances extraites (1-24)
        }
        """
        import json
        import re

        try:
            # Nettoyer le texte
            texte = texte.strip()

            # Cas 1: JSON dans code block markdown
            if '```json' in texte:
                match = re.search(r'```json\s*(\{.*?\})\s*```', texte, re.DOTALL)
                if match:
                    texte = match.group(1)
            elif '```' in texte:
                match = re.search(r'```\s*(\{.*?\})\s*```', texte, re.DOTALL)
                if match:
                    texte = match.group(1)

            # Cas 2: JSON direct avec texte avant/après
            match = re.search(r'(\{.*\})', texte, re.DOTALL)
            if match:
                texte = match.group(1)

            # Parser le JSON
            data = json.loads(texte)

            # Valider structure
            if not isinstance(data, dict):
                return {
                    "pret": {"_erreur": "Réponse non-dict", "_raw": texte[:200]},
                    "echeances": []
                }

            if 'pret' not in data:
                return {
                    "pret": {"_erreur": "Clé 'pret' manquante", "_raw": texte[:200]},
                    "echeances": []
                }

            pret = data['pret']
            echeances = data.get('echeances', [])

            # Valider champs critiques du contrat
            champs_critiques = ['numero_pret', 'montant_initial', 'taux_annuel', 'duree_mois']
            champs_manquants = [c for c in champs_critiques if c not in pret]

            if champs_manquants:
                return {
                    "pret": {
                        "_erreur": f"Champs critiques manquants: {', '.join(champs_manquants)}",
                        "_raw": str(pret)[:200]
                    },
                    "echeances": []
                }

            # Valider valeurs
            if pret['montant_initial'] <= 0:
                return {
                    "pret": {"_erreur": "montant_initial doit être > 0", "_raw": str(pret)[:200]},
                    "echeances": []
                }

            if pret['taux_annuel'] <= 0 or pret['taux_annuel'] > 0.2:
                return {
                    "pret": {
                        "_erreur": f"taux_annuel invalide: {pret['taux_annuel']}",
                        "_raw": str(pret)[:200]
                    },
                    "echeances": []
                }

            # Assurer valeurs par défaut
            if 'mois_franchise' not in pret:
                pret['mois_franchise'] = 0
            if 'type_amortissement' not in pret:
                pret['type_amortissement'] = 'AMORTISSEMENT_CONSTANT'
            if 'banque' not in pret:
                pret['banque'] = 'LCL'

            # Valider échéances si présentes
            if not isinstance(echeances, list):
                echeances = []

            return {
                "pret": pret,
                "echeances": echeances
            }

        except json.JSONDecodeError as e:
            return {
                "pret": {
                    "_erreur": f"JSON invalide: {str(e)[:100]}",
                    "_raw": texte[:300]
                },
                "echeances": []
            }
        except Exception as e:
            return {
                "pret": {
                    "_erreur": f"Erreur parsing hybride: {str(e)[:100]}",
                    "_raw": texte[:300]
                },
                "echeances": []
            }

    @staticmethod
    def _generer_echeances(contrat: Dict, start_month: int = 1, echeances_precedentes: List[Dict] = None) -> List[Dict]:
        """
        Génère les échéances mathématiquement selon formule amortissement

        APPROCHE HYBRIDE (V8):
        - Si start_month=1: génère toutes les échéances
        - Si start_month>1: génère échéances à partir de start_month (complète les extraites)

        Args:
            contrat: Dict avec clés:
                - montant_initial: Capital emprunté
                - taux_annuel: Taux annuel décimal (ex: 0.0124 pour 1.24%)
                - duree_mois: Durée totale en mois
                - date_debut: Date première échéance (YYYY-MM-DD)
                - mois_franchise: Nombre de mois franchise (0 si aucune)
                - type_amortissement: "AMORTISSEMENT_CONSTANT" ou "FRANCHISE_PARTIELLE"
                - echeance_mensuelle: Montant mensuel (optionnel, calculé si absent)
            start_month: Numéro du premier mois à générer (défaut: 1)
            echeances_precedentes: Liste des échéances déjà extraites (pour récupérer capital_restant)

        Returns:
            Liste échéances avec: numero_echeance, date_echeance, montant_total, montant_interet,
            montant_capital, capital_restant_du
        """
        from datetime import datetime
        from dateutil.relativedelta import relativedelta
        from decimal import Decimal, ROUND_HALF_UP

        # Extraire les paramètres
        capital_initial = Decimal(str(contrat['montant_initial']))
        taux_annuel = Decimal(str(contrat['taux_annuel']))
        duree_mois = int(contrat['duree_mois'])
        date_debut = datetime.strptime(contrat['date_debut'], '%Y-%m-%d')
        mois_franchise = int(contrat.get('mois_franchise', 0))
        type_amort = contrat.get('type_amortissement', 'AMORTISSEMENT_CONSTANT')

        # Taux mensuel
        taux_mensuel = taux_annuel / Decimal('12')

        # Capital restant dû ET date de départ : récupérer de la dernière échéance extraite si existe
        if echeances_precedentes and len(echeances_precedentes) > 0:
            derniere = echeances_precedentes[-1]
            capital_restant = Decimal(str(derniere.get('capital_restant_du', capital_initial)))
            # Date de départ = date de la dernière échéance extraite
            date_reference = datetime.strptime(derniere['date_echeance'], '%Y-%m-%d')
        else:
            capital_restant = capital_initial
            date_reference = None  # Pas utilisé si pas de précédentes

        # Calculer mensualité si non fournie (formule amortissement constant)
        if 'echeance_mensuelle' in contrat and contrat['echeance_mensuelle'] > 0:
            mensualite = Decimal(str(contrat['echeance_mensuelle']))
        else:
            # Formule: M = C × (t / (1 - (1 + t)^(-n)))
            # Pour période amortissement uniquement (après franchise)
            duree_amortissement = duree_mois - mois_franchise
            if duree_amortissement > 0 and taux_mensuel > 0:
                try:
                    diviseur = Decimal('1') - (Decimal('1') + taux_mensuel) ** (-duree_amortissement)
                    mensualite = capital_initial * (taux_mensuel / diviseur)
                except:
                    # Fallback: calculer simplement
                    mensualite = capital_initial / Decimal(str(duree_amortissement))
            else:
                mensualite = Decimal('0')

        echeances = []
        compteur_mois = 1  # Compteur pour les mois à ajouter à date_reference

        for i in range(start_month, duree_mois + 1):
            # Date de l'échéance
            if echeances_precedentes and len(echeances_precedentes) > 0:
                # Partir de la dernière échéance extraite + compteur mois
                date_echeance = date_reference + relativedelta(months=compteur_mois)
                compteur_mois += 1
            else:
                # Partir de date_debut (génération complète)
                date_echeance = date_debut + relativedelta(months=i-1)

            # Calculer intérêt et capital selon période
            if i <= mois_franchise:
                # PÉRIODE DE FRANCHISE: intérêts seulement, pas de capital
                interet = (capital_restant * taux_mensuel).quantize(Decimal('0.01'), ROUND_HALF_UP)
                capital = Decimal('0')
                montant_total = interet

            elif type_amort == "FRANCHISE_PARTIELLE" and i == duree_mois:
                # FRANCHISE PARTIELLE: Dernier mois = pic (tout le capital restant)
                interet = (capital_restant * taux_mensuel).quantize(Decimal('0.01'), ROUND_HALF_UP)
                capital = capital_restant
                montant_total = interet + capital

            else:
                # AMORTISSEMENT CONSTANT: mensualité fixe
                interet = (capital_restant * taux_mensuel).quantize(Decimal('0.01'), ROUND_HALF_UP)
                capital = (mensualite - interet).quantize(Decimal('0.01'), ROUND_HALF_UP)

                # S'assurer que capital ne dépasse pas capital_restant
                if capital > capital_restant:
                    capital = capital_restant

                montant_total = interet + capital

            # Mise à jour capital restant
            capital_restant -= capital
            # Éviter négatifs dus aux arrondis
            if capital_restant < Decimal('0.01'):
                capital_restant = Decimal('0')

            # Ajouter l'échéance
            echeances.append({
                "numero_echeance": i,
                "date_echeance": date_echeance.strftime('%Y-%m-%d'),
                "montant_total": float(montant_total),
                "montant_interet": float(interet),
                "montant_capital": float(capital),
                "capital_restant_du": float(capital_restant)
            })

        return echeances


# ═══════════════════════════════════════════════════════════════════════════════
# 5. PARSEUR RÉÉVALUATION SCPI
# ═══════════════════════════════════════════════════════════════════════════════

class ParseurReevalorationSCPI:
    """Parse tableau réévaluations SCPI et extrait gains/pertes par semestre"""
    
    def __init__(self, ocr_extractor: OCRExtractor):
        self.ocr = ocr_extractor
    
    def parse_from_pdf(self, filepath: str, annee: int = 2023) -> List[Dict]:
        """
        Parse réévaluations SCPI depuis PDF
        
        Returns:
            [
              {"semestre": 1, "date": "juin 2023", "prix_marche": 120, "prix_comptable": 118, "gain": 2000},
              {"semestre": 2, "date": "décembre 2023", "prix_marche": 119, "prix_comptable": 120, "perte": 1000}
            ]
        """
        texte_brut = self.ocr.extract_from_pdf(
            filepath,
            prompt=f"Extrait réévaluations SCPI {annee} avec colonnes: Date | Prix Marché | Prix Comptable | Gain/Perte"
        )
        
        result = self._parser_reevaluations(texte_brut, annee)
        return result
    
    @staticmethod
    def _parser_reevaluations(texte: str, annee: int) -> List[Dict]:
        """Parse tableau réévaluations depuis texte OCRisé"""
        reevals = []
        
        # Pattern: "Juin 2023  120  118  2000" ou "Juni June  120€  118€  (2€ × 1000 parts)"
        # Cherche: (date/mois) | prix1 | prix2 | montant
        pattern = r'(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre|january|...|june|december|S1|S2|Semestre|1|2).*?(\d+(?:[.,]\d+)?)\s+(\d+(?:[.,]\d+)?)\s+([+-]?\d+(?:[.,]\d+)?)?'
        
        semestre_num = 1
        matches = re.finditer(pattern, texte, re.IGNORECASE)
        for match in matches:
            try:
                prix_marche_str = match.group(2).replace(',', '.')
                prix_comptable_str = match.group(3).replace(',', '.')
                
                prix_marche = Decimal(prix_marche_str)
                prix_comptable = Decimal(prix_comptable_str)
                
                # Calcul: (prix_marche - prix_comptable) × nombre de parts
                # Supposer 1000 parts par défaut
                nb_parts = 1000
                difference_unitaire = prix_marche - prix_comptable
                montant_total = difference_unitaire * nb_parts
                
                reevals.append({
                    "semestre": semestre_num,
                    "prix_marche": float(prix_marche),
                    "prix_comptable": float(prix_comptable),
                    "montant": float(abs(montant_total)),
                    "type": "GAIN" if montant_total > 0 else "PERTE"
                })
                
                semestre_num = (semestre_num % 2) + 1
            except (ValueError, IndexError):
                continue
        
        return reevals


# ═══════════════════════════════════════════════════════════════════════════════
# 6. GÉNÉRATEUR PROPOSITIONS
# ═══════════════════════════════════════════════════════════════════════════════

class GenerateurPropositions:
    """Génère propositions Markdown + JSON + Token MD5"""
    
    @staticmethod
    def generer_propositions_evenement_simple(email: Dict, montant: float, type_evt: str) -> Tuple[str, Dict, str]:
        """
        Génère propositions pour événement simple (loyer/charge)
        
        Returns:
            (markdown_propre, propositions_dict, token_md5)
        """
        # Mapper type → comptes
        mapping = {
            'LOYER': {'debit': '511', 'credit': '701', 'libelle': 'Encaissement loyer'},
            'CHARGE': {'debit': '614', 'credit': '401', 'libelle': 'Charge'},
        }
        
        config = mapping.get(type_evt, mapping['CHARGE'])
        
        propositions = [
            {
                "numero_ecriture": f"2024-{datetime.now().strftime('%m%d')}-001",
                "type": type_evt,
                "compte_debit": config['debit'],
                "compte_credit": config['credit'],
                "montant": montant,
                "libelle": f"{config['libelle']} - {montant}€"
            }
        ]
        
        # Générer token
        token = hashlib.md5(json.dumps(propositions, sort_keys=True).encode()).hexdigest()
        
        # Générer Markdown
        markdown = GenerateurPropositions._generer_markdown_propositions(propositions, type_evt)
        
        return markdown, {"propositions": propositions, "token": token}, token
    
    @staticmethod
    def generer_propositions_init_bilan_2023(comptes: List[Dict]) -> Tuple[str, Dict, str]:
        """
        Génère propositions pour initialisation bilan 2023

        CORRECTION V6: Génère écritures correctes avec distinction Actif/Passif
        - Compte 89 "Bilan d'ouverture" comme contrepartie
        - Respect du sens comptable (débit/crédit)
        """

        propositions = []
        compte_ouverture = "89"  # Compte standard bilan d'ouverture (sera soldé automatiquement)

        for i, compte in enumerate(comptes, 1):
            num_compte = compte["compte"]
            libelle = compte["libelle"]
            solde = abs(compte["solde"])  # Valeur absolue
            sens = compte.get("sens", GenerateurPropositions._determiner_sens_compte(num_compte, compte.get("type_bilan", "")))

            if sens == "DEBIT":
                # Compte à l'actif ou capitaux propres négatifs
                propositions.append({
                    "numero_ecriture": f"2023-INIT-{i:04d}",
                    "type": "INIT_BILAN_2023",
                    "compte_debit": num_compte,
                    "compte_credit": compte_ouverture,
                    "montant": solde,
                    "libelle": f"Ouverture: {libelle}"
                })
            else:
                # Compte au passif ou provisions/amortissements
                propositions.append({
                    "numero_ecriture": f"2023-INIT-{i:04d}",
                    "type": "INIT_BILAN_2023",
                    "compte_debit": compte_ouverture,
                    "compte_credit": num_compte,
                    "montant": solde,
                    "libelle": f"Ouverture: {libelle}"
                })

        token = hashlib.md5(json.dumps(propositions, sort_keys=True).encode()).hexdigest()
        markdown = GenerateurPropositions._generer_markdown_init_bilan(propositions, comptes)

        return markdown, {"propositions": propositions, "token": token}, token

    @staticmethod
    def _determiner_sens_compte(num_compte: str, type_bilan: str = "") -> str:
        """
        Détermine si un compte doit être débité ou crédité à l'ouverture

        Args:
            num_compte: Numéro du compte (ex: "280", "101")
            type_bilan: "ACTIF" ou "PASSIF" (si disponible)

        Returns:
            "DEBIT" ou "CREDIT"
        """
        # Si on a l'info directe, l'utiliser
        if type_bilan == "ACTIF":
            return "DEBIT"
        elif type_bilan == "PASSIF":
            return "CREDIT"

        # Sinon, déterminer selon le numéro de compte (Plan Comptable Général français)
        premiere_classe = num_compte[0] if num_compte else "0"

        # Classe 1 : Capitaux propres
        if premiere_classe == "1":
            # 12x Report à nouveau peut être débiteur si négatif (traité au cas par cas)
            if num_compte.startswith("12"):
                return "DEBIT"  # RAN négatif dans bilan SCI Soeurise
            return "CREDIT"  # Capital, réserves, résultat, emprunts

        # Classe 2 : Immobilisations
        elif premiere_classe == "2":
            if num_compte.startswith("28") or num_compte.startswith("29"):
                return "CREDIT"  # Amortissements et provisions
            return "DEBIT"  # Immobilisations brutes

        # Classe 3 : Stocks (généralement débit)
        elif premiere_classe == "3":
            return "DEBIT"

        # Classe 4 : Comptes de tiers
        elif premiere_classe == "4":
            if num_compte.startswith("40") or num_compte.startswith("42") or \
               num_compte.startswith("43") or num_compte.startswith("44"):
                return "CREDIT"  # Fournisseurs, dettes diverses
            return "DEBIT"  # Clients et créances (41x)

        # Classe 5 : Comptes financiers (trésorerie)
        elif premiere_classe == "5":
            return "DEBIT"

        # Par défaut (ne devrait pas arriver pour un bilan)
        return "DEBIT"
    
    @staticmethod
    def generer_propositions_cloture_2023(credit_data: Dict, scpi_data: List[Dict]) -> Tuple[str, Dict, str]:
        """Génère propositions pour clôture exercice 2023"""
        
        propositions = []
        
        # Intérêts crédit
        if credit_data.get('total_interets_payes', 0) > 0:
            propositions.append({
                "numero_ecriture": "2023-CLOTURE-INTERETS",
                "type": "INTÉRÊTS_CRÉDIT",
                "compte_debit": "661",
                "compte_credit": "401",
                "montant": credit_data['total_interets_payes'],
                "libelle": f"Intérêts crédits 2023: {credit_data['total_interets_payes']}€"
            })
        
        # Réévaluations SCPI
        for i, reevals in enumerate(scpi_data, 1):
            if reevals['type'] == 'GAIN':
                propositions.append({
                    "numero_ecriture": f"2023-CLOTURE-SCPI-GAIN-{i}",
                    "type": "RÉÉVALUATION_SCPI_GAIN",
                    "compte_debit": "440",
                    "compte_credit": "754",
                    "montant": reevals['montant'],
                    "libelle": f"Rééval SCPI gain S{reevals['semestre']}: {reevals['montant']}€"
                })
            else:
                propositions.append({
                    "numero_ecriture": f"2023-CLOTURE-SCPI-PERTE-{i}",
                    "type": "RÉÉVALUATION_SCPI_PERTE",
                    "compte_debit": "654",
                    "compte_credit": "440",
                    "montant": reevals['montant'],
                    "libelle": f"Rééval SCPI perte S{reevals['semestre']}: {reevals['montant']}€"
                })
        
        token = hashlib.md5(json.dumps(propositions, sort_keys=True).encode()).hexdigest()
        markdown = GenerateurPropositions._generer_markdown_cloture(propositions, credit_data, scpi_data)
        
        return markdown, {"propositions": propositions, "token": token}, token

    @staticmethod
    def generer_propositions_pret_immobilier(pret_data: Dict, nb_echeances: int, filename: str) -> Tuple[str, Dict, str]:
        """
        Génère propositions pour insertion prêt immobilier

        Args:
            pret_data: Données du prêt extraites
            nb_echeances: Nombre d'échéances extraites
            filename: Nom du fichier MD contenant les échéances

        Returns:
            (markdown, propositions_dict, token)
        """
        propositions = [{
            "type": "PRET_IMMOBILIER",
            "action": "INSERER_PRET",
            "filename": filename,
            "pret": pret_data,
            "nb_echeances": nb_echeances
        }]

        token = hashlib.md5(json.dumps(propositions, sort_keys=True).encode()).hexdigest()
        markdown = GenerateurPropositions._generer_markdown_pret(pret_data, nb_echeances, filename, token)

        return markdown, {"propositions": propositions, "token": token}, token

    @staticmethod
    def _generer_markdown_pret(pret_data: Dict, nb_echeances: int, filename: str, token: str) -> str:
        """Génère Markdown pour proposition prêt immobilier"""

        md = f"""# Proposition Prêt Immobilier

**Date:** {datetime.now().strftime('%d/%m/%Y %H:%M')}
**Token:** `{token}`

## 📋 Données du Prêt

| Champ | Valeur |
|-------|--------|
| Numéro prêt | {pret_data.get('numero_pret', 'N/A')} |
| Banque | {pret_data.get('banque', 'N/A')} |
| Montant initial | {pret_data.get('montant_initial', 0):,.2f} € |
| Taux annuel | {pret_data.get('taux_annuel', 0):.4f} % |
| Durée | {pret_data.get('duree_mois', 0)} mois |
| Date début | {pret_data.get('date_debut', 'N/A')} |
| Type | {pret_data.get('type_amortissement', 'N/A')} |

## 📊 Échéances Extraites

- **Nombre total** : {nb_echeances} échéances
- **Fichier** : `{filename}`

## ✅ Action Proposée

Insertion du prêt et de ses {nb_echeances} échéances en base de données.

Pour valider, répondez : `[_Head] VALIDE: {token}`

"""
        return md

    @staticmethod
    def _generer_markdown_propositions(propositions: List[Dict], type_evt: str) -> str:
        """Génère Markdown propre pour propositions simples"""
        
        md = f"""# Propositions Comptables - {type_evt}

**Date:** {datetime.now().strftime('%d/%m/%Y %H:%M')}

## Propositions

| N° Écriture | Type | D/C | Compte | Montant | Libellé |
|-------------|------|-----|--------|---------|---------|
"""
        
        for prop in propositions:
            md += f"| {prop['numero_ecriture']} | {prop['type']} | "
            md += f"D: {prop['compte_debit']} / C: {prop['compte_credit']} | "
            md += f"{prop['montant']}€ | {prop['libelle']} |\n"
        
        md += """

## JSON Structure

```json
"""
        md += json.dumps({
            "propositions": propositions,
            "token": hashlib.md5(json.dumps(propositions, sort_keys=True).encode()).hexdigest(),
            "type_evenement": type_evt,
            "generee_at": datetime.now().isoformat()
        }, indent=2)
        md += "\n```\n"
        
        return md
    
    @staticmethod
    def _generer_markdown_init_bilan(propositions: List[Dict], comptes: List[Dict]) -> str:
        """Génère Markdown pour initialisation bilan 2023"""

        md = """# Initialisation Bilan 2023

**Date:** """ + datetime.now().strftime('%d/%m/%Y %H:%M') + """

## Comptes Importés

| Compte | Libellé | Solde |
|--------|---------|-------|
"""

        for compte in comptes:
            md += f"| {compte['compte']} | {compte['libelle']} | {compte['solde']}€ |\n"

        md += f"\n**Total:** {sum(c['solde'] for c in comptes)}€\n"
        md += f"**Nombre de comptes:** {len(comptes)}\n"

        # Analyse ACTIF/PASSIF
        total_debit = sum(p['montant'] for p in propositions if p['compte_debit'] != '89')
        total_credit = sum(p['montant'] for p in propositions if p['compte_credit'] != '89')

        md += f"\n## Écritures d'Ouverture\n\n"
        md += f"**ACTIF (débits)**: {total_debit:.2f}€\n"
        md += f"**PASSIF (crédits)**: {total_credit:.2f}€\n"
        md += f"**Équilibre**: {'✓ OK' if abs(total_debit - total_credit) < 0.01 else '✗ ERREUR'}\n\n"

        # Détail par type
        md += "### Détail des écritures\n\n"
        md += "**Comptes à l'ACTIF (débit):**\n"
        for prop in propositions:
            if prop['compte_debit'] != '89':
                md += f"- {prop['compte_debit']} : {prop['montant']}€ (contrepartie crédit 89)\n"

        md += "\n**Comptes au PASSIF (crédit):**\n"
        for prop in propositions:
            if prop['compte_credit'] != '89':
                md += f"- {prop['compte_credit']} : {prop['montant']}€ (contrepartie débit 89)\n"

        md += f"\n**Compte 89 (bilan d'ouverture)**: se solde automatiquement à 0€\n"

        md += "\n## JSON Structure\n\n```json\n"
        md += json.dumps({
            "propositions": propositions,
            "token": hashlib.md5(json.dumps(propositions, sort_keys=True).encode()).hexdigest(),
            "type_evenement": "INIT_BILAN_2023",
            "generee_at": datetime.now().isoformat()
        }, indent=2)
        md += "\n```\n"

        return md
    
    @staticmethod
    def _generer_markdown_cloture(propositions: List[Dict], credit_data: Dict, scpi_data: List[Dict]) -> str:
        """Génère Markdown pour clôture exercice 2023"""
        
        md = """# Clôture Exercice 2023

**Date:** """ + datetime.now().strftime('%d/%m/%Y %H:%M') + """

## Éléments de Clôture

### Crédits
- Intérêts payés 2023: """
        
        md += f"{credit_data.get('total_interets_payes', 0)}€\n"
        md += f"- Principal payé 2023: {credit_data.get('total_principal_paye', 0)}€\n"
        
        md += "\n### Réévaluations SCPI\n\n"
        for reevals in scpi_data:
            md += f"- S{reevals['semestre']}: "
            md += f"Marché {reevals['prix_marche']}€ vs Comptable {reevals['prix_comptable']}€ "
            md += f"({reevals['type']}: {reevals['montant']}€)\n"
        
        md += "\n## Propositions\n\n"
        for prop in propositions:
            md += f"- {prop['numero_ecriture']}: {prop['libelle']}\n"
        
        md += "\n## JSON Structure\n\n```json\n"
        md += json.dumps({
            "propositions": propositions,
            "token": hashlib.md5(json.dumps(propositions, sort_keys=True).encode()).hexdigest(),
            "type_evenement": "CLOTURE_EXERCICE",
            "generee_at": datetime.now().isoformat()
        }, indent=2)
        md += "\n```\n"
        
        return md


# ═══════════════════════════════════════════════════════════════════════════════
# 7. WORKFLOW MODULE 2 V2 - ORCHESTRATEUR PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class WorkflowModule2V2:
    """Orchestre le workflow complet: détection → parsing → génération propositions"""
    
    def __init__(self, api_key: str, database_url: str):
        self.api_key = api_key
        self.database_url = database_url
        self.ocr = OCRExtractor(api_key)
        self.parseur_bilan = ParseurBilan2023(self.ocr)
        self.parseur_credit = ParseurAmortissementCredit(self.ocr)
        self.parseur_scpi = ParseurReevalorationSCPI(self.ocr)
    
    def traiter_email(self, email: Dict) -> Dict:
        """
        Traite un email et retourne propositions

        Returns:
            {
              "type_detecte": TypeEvenement,
              "statut": "OK" | "ERREUR",
              "markdown": "...",
              "propositions": {...},
              "token": "...",
              "message": "..."
            }
        """

        type_evt = DetecteurTypeEvenement.detecter(email)

        if type_evt == TypeEvenement.EVENEMENT_SIMPLE:
            return self._traiter_evenement_simple(email)
        elif type_evt == TypeEvenement.INIT_BILAN_2023:
            return self._traiter_init_bilan_2023(email)
        elif type_evt == TypeEvenement.PRET_IMMOBILIER:
            return self._traiter_pret_immobilier(email)
        elif type_evt == TypeEvenement.CLOTURE_EXERCICE:
            return self._traiter_cloture_2023(email)
        else:
            return {
                "type_detecte": TypeEvenement.UNKNOWN,
                "statut": "ERREUR",
                "message": "Impossible de détecter le type d'événement",
                "markdown": "",
                "propositions": {},
                "token": ""
            }
    
    def _traiter_evenement_simple(self, email: Dict) -> Dict:
        """Traite événement simple (loyer/charge)"""
        try:
            body = email.get('body', '')
            
            # Détecter type
            type_evt = 'LOYER' if 'loyer' in body.lower() else 'CHARGE'
            
            # Extraire montant
            montant_match = re.search(r'(\d+(?:[.,]\d+)?)\s*€', body)
            if not montant_match:
                montant_match = re.search(r'(\d+(?:[.,]\d+)?)', body)
            
            if not montant_match:
                return {
                    "type_detecte": TypeEvenement.EVENEMENT_SIMPLE,
                    "statut": "ERREUR",
                    "message": "Impossible d'extraire le montant",
                    "markdown": "",
                    "propositions": {},
                    "token": ""
                }
            
            montant = float(montant_match.group(1).replace(',', '.'))
            
            # Générer propositions
            markdown, props, token = GenerateurPropositions.generer_propositions_evenement_simple(
                email, montant, type_evt
            )
            
            return {
                "type_detecte": TypeEvenement.EVENEMENT_SIMPLE,
                "type_specifique": type_evt,
                "statut": "OK",
                "markdown": markdown,
                "propositions": props,
                "token": token,
                "message": f"1 proposition générée ({type_evt}: {montant}€)"
            }
        
        except Exception as e:
            return {
                "type_detecte": TypeEvenement.EVENEMENT_SIMPLE,
                "statut": "ERREUR",
                "message": f"Erreur traitement: {str(e)[:100]}",
                "markdown": "",
                "propositions": {},
                "token": ""
            }
    
    def _traiter_init_bilan_2023(self, email: Dict) -> Dict:
        """
        Traite initialisation bilan 2023

        Accepte 2 formats:
        1. PDF en pièce jointe (parsing automatique via OCR)
        2. JSON dans le corps de l'email avec format:
           ```json
           {
             "comptes": [
               {"compte": "280", "libelle": "SCPI", "solde": 500032, "type_bilan": "ACTIF"},
               {"compte": "101", "libelle": "Capital", "solde": 1000, "type_bilan": "PASSIF"}
             ]
           }
           ```
        """
        try:
            comptes = None
            source = None

            # Option 1: Chercher JSON dans le corps de l'email
            body = email.get('body', '')
            if '```json' in body or '"comptes"' in body:
                try:
                    # Extraire JSON du corps (peut être dans un bloc markdown)
                    json_match = body
                    if '```json' in body:
                        json_match = body.split('```json')[1].split('```')[0]
                    elif '```' in body:
                        json_match = body.split('```')[1].split('```')[0]

                    data = json.loads(json_match.strip())
                    if 'comptes' in data and isinstance(data['comptes'], list):
                        comptes = data['comptes']
                        source = "JSON email"
                except (json.JSONDecodeError, IndexError) as e:
                    pass  # Si parsing JSON échoue, tenter PDF

            # Option 2: Parser PDF si pas de JSON valide
            if not comptes:
                attachments = email.get('attachments', [])
                pdf_files = [a for a in attachments if a.get('content_type') == 'application/pdf']

                if not pdf_files:
                    return {
                        "type_detecte": TypeEvenement.INIT_BILAN_2023,
                        "statut": "ERREUR",
                        "message": "Aucun PDF trouvé et aucun JSON valide dans le corps de l'email",
                        "markdown": "",
                        "propositions": {},
                        "token": ""
                    }

                # Parser le premier PDF (bilan 2023)
                filepath = pdf_files[0].get('filepath')
                comptes = self.parseur_bilan.parse_from_pdf(filepath)
                source = f"PDF {pdf_files[0].get('filename', 'inconnu')}"

            if not comptes:
                return {
                    "type_detecte": TypeEvenement.INIT_BILAN_2023,
                    "statut": "ERREUR",
                    "message": "Impossible d'extraire les comptes du bilan",
                    "markdown": "",
                    "propositions": {},
                    "token": ""
                }

            # Générer propositions
            markdown, props, token = GenerateurPropositions.generer_propositions_init_bilan_2023(comptes)

            return {
                "type_detecte": TypeEvenement.INIT_BILAN_2023,
                "statut": "OK",
                "markdown": markdown,
                "propositions": props,
                "token": token,
                "message": f"{len(comptes)} comptes importés depuis {source}"
            }

        except Exception as e:
            return {
                "type_detecte": TypeEvenement.INIT_BILAN_2023,
                "statut": "ERREUR",
                "message": f"Erreur traitement bilan: {str(e)[:100]}",
                "markdown": "",
                "propositions": {},
                "token": ""
            }

    def _traiter_pret_immobilier(self, email: Dict) -> Dict:
        """
        Traite prêt immobilier avec parseur V6 (Function Calling)

        Extrait le PDF et utilise le parseur V6 pour extraction complète
        des échéances via Function Calling Claude
        """
        try:
            attachments = email.get('attachments', [])
            pdf_files = [a for a in attachments if a.get('content_type') == 'application/pdf']

            if not pdf_files:
                return {
                    "type_detecte": TypeEvenement.PRET_IMMOBILIER,
                    "statut": "ERREUR",
                    "message": "Aucun PDF de tableau d'amortissement trouvé",
                    "markdown": "",
                    "propositions": {},
                    "token": ""
                }

            # Importer et initialiser le parseur V6
            try:
                from parseur_pret_v6 import ParseurTableauPretV6
                api_key = os.environ.get('ANTHROPIC_API_KEY')
                if not api_key:
                    return {
                        "type_detecte": TypeEvenement.PRET_IMMOBILIER,
                        "statut": "ERREUR",
                        "message": "ANTHROPIC_API_KEY non définie",
                        "markdown": "",
                        "propositions": {},
                        "token": ""
                    }

                parseur_v6 = ParseurTableauPretV6(api_key=api_key)
            except ImportError as e:
                return {
                    "type_detecte": TypeEvenement.PRET_IMMOBILIER,
                    "statut": "ERREUR",
                    "message": f"Impossible d'importer parseur_pret_v6: {str(e)}",
                    "markdown": "",
                    "propositions": {},
                    "token": ""
                }

            # Parser le PDF avec V6 (auto_insert_bd=False pour générer propositions)
            filepath = pdf_files[0].get('filepath')
            result = parseur_v6.parse_from_pdf(filepath, auto_insert_bd=False)

            if not result.get('success'):
                return {
                    "type_detecte": TypeEvenement.PRET_IMMOBILIER,
                    "statut": "ERREUR",
                    "message": result.get('message', 'Erreur parsing'),
                    "markdown": "",
                    "propositions": {},
                    "token": ""
                }

            # Extraire les données
            filename = result.get('filename')
            nb_echeances = result.get('nb_echeances', 0)

            # Lire le fichier MD pour extraire les données du prêt
            pret_data = self._extraire_donnees_pret_depuis_md(filename)

            if not pret_data:
                return {
                    "type_detecte": TypeEvenement.PRET_IMMOBILIER,
                    "statut": "ERREUR",
                    "message": "Impossible d'extraire les données du prêt",
                    "markdown": "",
                    "propositions": {},
                    "token": ""
                }

            # Générer propositions
            markdown, props, token = GenerateurPropositions.generer_propositions_pret_immobilier(
                pret_data, nb_echeances, filename
            )

            return {
                "type_detecte": TypeEvenement.PRET_IMMOBILIER,
                "statut": "OK",
                "markdown": markdown,
                "propositions": props,
                "token": token,
                "message": f"Prêt {pret_data.get('numero_pret')} : {nb_echeances} échéances extraites"
            }

        except Exception as e:
            import traceback
            return {
                "type_detecte": TypeEvenement.PRET_IMMOBILIER,
                "statut": "ERREUR",
                "message": f"Erreur traitement prêt: {str(e)[:200]}",
                "markdown": f"```\n{traceback.format_exc()}\n```",
                "propositions": {},
                "token": ""
            }

    def _extraire_donnees_pret_depuis_md(self, filename: str) -> Optional[Dict]:
        """
        Extrait les données du prêt depuis le fichier MD

        Le fichier MD contient un header avec les métadonnées du prêt.
        On parse ce header pour extraire les infos nécessaires.
        """
        try:
            if not os.path.exists(filename):
                return None

            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parser le nom du fichier pour le numéro de prêt
            # Format: PRET_XXXXXX_echeances.md
            import re
            match = re.search(r'PRET_([A-Z0-9]+)_echeances\.md', filename)
            numero_pret = match.group(1) if match else "INCONNU"

            # Pour l'instant, retourner les données minimales
            # TODO: Parser le header du fichier MD pour extraire les vraies données
            return {
                "numero_pret": numero_pret,
                "banque": "LCL",
                "montant_initial": 250000.00,
                "taux_annuel": 1.05,
                "duree_mois": 240,
                "date_debut": "2022-04-15",
                "type_amortissement": "AMORTISSEMENT_CONSTANT",
                "fichier_reference": filename
            }

        except Exception as e:
            print(f"[ERREUR] Extraction données prêt depuis MD: {e}")
            return None

    def _traiter_cloture_2023(self, email: Dict) -> Dict:
        """Traite clôture exercice 2023"""
        try:
            attachments = email.get('attachments', [])
            pdf_files = [a for a in attachments if a.get('content_type') == 'application/pdf']
            
            if len(pdf_files) < 2:
                return {
                    "type_detecte": TypeEvenement.CLOTURE_EXERCICE,
                    "statut": "ERREUR",
                    "message": f"Besoin au minimum 2 PDFs (crédit + SCPI), trouvé: {len(pdf_files)}",
                    "markdown": "",
                    "propositions": {},
                    "token": ""
                }
            
            # Parser amortissements et réévaluations
            credit_data = {}
            scpi_data = []
            
            for pdf in pdf_files:
                filename = pdf.get('filename', '').lower()
                filepath = pdf.get('filepath')
                
                if 'credit' in filename or 'amortissement' in filename:
                    credit_data = self.parseur_credit.parse_from_pdf(filepath, 2023)
                elif 'scpi' in filename or 'reevaluation' in filename:
                    scpi_data = self.parseur_scpi.parse_from_pdf(filepath, 2023)
            
            if not credit_data and not scpi_data:
                return {
                    "type_detecte": TypeEvenement.CLOTURE_EXERCICE,
                    "statut": "ERREUR",
                    "message": "Impossible d'extraire les données de clôture",
                    "markdown": "",
                    "propositions": {},
                    "token": ""
                }
            
            # Générer propositions
            markdown, props, token = GenerateurPropositions.generer_propositions_cloture_2023(
                credit_data, scpi_data
            )
            
            return {
                "type_detecte": TypeEvenement.CLOTURE_EXERCICE,
                "statut": "OK",
                "markdown": markdown,
                "propositions": props,
                "token": token,
                "message": f"Clôture 2023: {len(props.get('propositions', []))} propositions générées"
            }
        
        except Exception as e:
            return {
                "type_detecte": TypeEvenement.CLOTURE_EXERCICE,
                "statut": "ERREUR",
                "message": f"Erreur traitement clôture: {str(e)[:100]}",
                "markdown": "",
                "propositions": {},
                "token": ""
            }



# ═══════════════════════════════════════════════════════════════════════════════
# ENVOYEUR MARKDOWN
# ═══════════════════════════════════════════════════════════════════════════════

class EnvoyeurMarkdown:
    """Envoie les propositions par email en Markdown formaté + pièce jointe"""
    
    def __init__(self, email_from: str, email_password: str, email_to: str = None):
        self.email_from = email_from
        self.email_password = email_password
        self.email_to = email_to
    
    def envoyer_propositions(
        self,
        email_to: str,
        type_evt: str,
        markdown: str,
        token: str,
        subject_suffix: str = ""
    ) -> bool:
        """
        Envoie les propositions à Ulrik pour validation
        
        ✅ FIX: Accepte email_to, subject_suffix, attache Markdown
        
        Sujet: [_Head] PROPOSITIONS - Type d'événement [suffix]
        Body: JSON avec token + instructions
        Pièce jointe: Markdown avec propositions
        
        Instructions: Tag [_Head] VALIDE: dans la réponse pour valider
        """
        
        try:
            msg = MIMEMultipart('mixed')
            msg['Subject'] = f"[_Head] PROPOSITIONS - {type_evt} {subject_suffix}".strip()
            msg['From'] = self.email_from
            msg['To'] = email_to
            
            # 1. BODY TEXTE: JSON + Token + Instructions
            
            body_text = f"""
Propositions comptables pour validation

**Type d'événement:** {type_evt}
**Date de génération:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
**Token MD5 de sécurité:** {token}

---

## STRUCTURE JSON DES PROPOSITIONS

```json
{json.dumps(
    {
        "type_evenement": type_evt,
        "token": token,
        "generee_at": datetime.now().isoformat()
    },
    indent=2
)}
```

---

## INSTRUCTIONS POUR VALIDATION

1. **Examinez les propositions** dans le fichier Markdown ci-joint
2. **Vérifiez l'exactitude** des comptes, montants, dates
3. **Pour valider**, répondez à cet email avec le tag suivant dans votre message:

   **[_Head] VALIDE:**

4. Vous pouvez modifier le fichier Markdown avant de répondre (optionnel)
5. Joignez le fichier modifié si vous avez apporté des corrections

---

**⏰ _Head attendra votre réponse au prochain réveil automatique.**

Merci,
_Head.Soeurise
"""
            
            msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
            
            # 2. PIÈCE JOINTE: Markdown avec propositions ✅ FIX
            
            try:
                # Créer fichier Markdown temporaire
                md_filename = f"propositions_{type_evt}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
                md_filepath = os.path.join(tempfile.gettempdir(), md_filename)
                
                with open(md_filepath, 'w', encoding='utf-8') as f:
                    f.write(markdown)
                
                # Attacher le fichier
                with open(md_filepath, 'rb') as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename= {md_filename}')
                    msg.attach(part)
                
                # Nettoyer le fichier temporaire
                try:
                    os.remove(md_filepath)
                except:
                    pass
            
            except Exception as e:
                print(f"⚠️ Erreur création pièce jointe Markdown: {str(e)[:100]}")
                # Continuer sans pièce jointe si erreur
            
            # 3. ENVOYER L'EMAIL
            
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(self.email_from, self.email_password)
                server.send_message(msg)
            
            print(f"✅ Email de propositions envoyé à {email_to} ({type_evt})")
            return True
        
        except Exception as e:
            print(f"❌ Erreur envoi email propositions: {str(e)[:100]}")
            return False
    
    @staticmethod
    def _markdown_to_html(markdown: str) -> str:
        """Conversion simple Markdown → HTML"""
        
        html = markdown
        
        # Headers
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        
        # Bold/Italic
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        
        # Listes
        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'(<li>.+</li>)', r'<ul>\1</ul>', html, flags=re.DOTALL)
        
        # Code blocks
        html = re.sub(r'```(.+?)```', r'<pre><code>\1</code></pre>', html, flags=re.DOTALL)
        
        # Paragraphes
        html = re.sub(r'\n\n', r'</p><p>', html)
        html = f"<p>{html}</p>"
        
        return html



# ═══════════════════════════════════════════════════════════════════════════════
# PARSEUR MARKDOWN JSON (déplacé de module2_workflow_v2_branches.py)
# ═══════════════════════════════════════════════════════════════════════════════

class ParseurMarkdownJSON:
    """Parse JSON depuis bloc ```json...``` dans Markdown"""
    
    @staticmethod
    def extraire_json(markdown_text: str) -> Optional[Dict]:
        """
        Extrait le bloc JSON ```json...```
        
        Returns:
            Dict du JSON ou None si introuvable/invalide
        """
        
        # Pattern: ```json...```
        pattern = r'```json\s*\n(.*?)\n```'
        match = re.search(pattern, markdown_text, re.DOTALL)
        
        if not match:
            # Essayer sans backticks
            if '{' in markdown_text and '}' in markdown_text:
                # Chercher {...}
                start = markdown_text.rfind('{')
                end = markdown_text.find('}', start) + 1
                if start >= 0 and end > start:
                    try:
                        return json.loads(markdown_text[start:end])
                    except json.JSONDecodeError:
                        pass
            return None
        
        try:
            json_str = match.group(1)
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"❌ Erreur parsing JSON: {str(e)}")
            return None
    
    @staticmethod
    def valider_structure_json(data: Dict, type_evt: str) -> Tuple[bool, str]:
        """
        Valide la structure JSON
        
        Returns:
            (valide, message_erreur)
        """
        
        # Vérifier présence clés obligatoires
        if 'propositions' not in data:
            return False, "Clé 'propositions' manquante"
        
        if 'token' not in data:
            return False, "Clé 'token' manquante"
        
        if not isinstance(data['propositions'], list):
            return False, "'propositions' doit être une liste"
        
        if len(data['propositions']) == 0:
            return False, "Liste 'propositions' vide"
        
        # Valider chaque proposition
        for i, prop in enumerate(data['propositions']):
            if not isinstance(prop, dict):
                return False, f"Proposition {i} n'est pas un dict"
            
            required_keys = ['numero_ecriture', 'type', 'compte_debit', 'compte_credit', 'montant', 'libelle']
            for key in required_keys:
                if key not in prop:
                    return False, f"Proposition {i}: clé '{key}' manquante"
            
            # Valider montant
            try:
                montant = float(prop['montant'])
                if montant <= 0:
                    return False, f"Proposition {i}: montant doit être > 0"
            except (ValueError, TypeError):
                return False, f"Proposition {i}: montant invalide"
        
        return True, ""


if __name__ == "__main__":
    import os
    
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    db_url = os.environ.get('DATABASE_URL')
    
    if not api_key or not db_url:
        print("❌ ANTHROPIC_API_KEY ou DATABASE_URL non définis")
        exit(1)
    
    workflow = WorkflowModule2V2(api_key, db_url)
    print("✅ Module 2 Workflow V2 chargé et prêt")
