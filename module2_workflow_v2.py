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
    
    def extract_from_pdf(self, filepath: str, prompt: str = None) -> str:
        """
        Extrait texte d'un PDF via OCR Claude Vision
        
        Args:
            filepath: Chemin du PDF
            prompt: Prompt personnalisé pour Claude (ex: "Extrait le tableau amortissement")
        
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
                    max_tokens=2000,
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
        
        # Détecteur CLOTURE_EXERCICE
        if any(kw in body for kw in ['cloture', 'clôture', 'amortissement_credit', 'reevaluation', 'réévaluation']):
            return TypeEvenement.CLOTURE_EXERCICE
        
        if any(f['filename'].lower().endswith('.pdf') and any(kw in f['filename'].lower() 
               for kw in ['amortissement', 'credit', 'reevaluation', 'cloture'])
               for f in attachments if 'filename' in f):
            return TypeEvenement.CLOTURE_EXERCICE
        
        # Détecteur INIT_BILAN_2023
        if any(kw in body for kw in ['bilan 2023', 'bilan_2023', 'bilan initial', 'initialisation comptable']):
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
