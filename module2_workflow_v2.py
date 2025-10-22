"""
MODULE 2 WORKFLOW V2 - WORKFLOW COMPTABLE
==========================================
Détection d'événements, parsing PDFs, génération propositions (7 phases du flux global)

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
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from decimal import Decimal

import anthropic

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False


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
# 2. DÉTECTEUR TYPE ÉVÉNEMENT
# ═══════════════════════════════════════════════════════════════════════════════

class DetecteurTypeEvenement:
    """Détecte le type d'événement comptable depuis un email"""
    
    @staticmethod
    def detecter(email: Dict) -> str:
        """
        Détecte le type d'événement
        
        Returns:
            EVENEMENT_SIMPLE | INIT_BILAN_2023 | CLOTURE_EXERCICE | UNKNOWN
        """
        body = (email.get('body', '') + ' ' + email.get('subject', '')).lower()
        subject = email.get('subject', '').lower()
        attachments = email.get('attachments', [])
        
        # Détecteur CLOTURE_EXERCICE
        if any(kw in body for kw in ['cloture', 'clôture', 'amortissement_credit', 'reevaluation', 'réévaluation']):
            return 'CLOTURE_EXERCICE'
        
        if any(f['filename'].lower().endswith('.pdf') and any(kw in f['filename'].lower() 
               for kw in ['amortissement', 'credit', 'reevaluation', 'cloture'])
               for f in attachments if 'filename' in f):
            return 'CLOTURE_EXERCICE'
        
        # Détecteur INIT_BILAN_2023
        if any(kw in body for kw in ['bilan 2023', 'bilan_2023', 'bilan initial', 'initialisation comptable']):
            return 'INIT_BILAN_2023'
        
        if any(f['filename'].lower().endswith('.pdf') and 'bilan' in f['filename'].lower() and '2023' in f['filename'].lower()
               for f in attachments if 'filename' in f):
            return 'INIT_BILAN_2023'
        
        # Détecteur EVENEMENT_SIMPLE (loyer, charge, etc.)
        if any(kw in body for kw in ['loyer', 'location', 'paiement', 'charge', 'entretien', 
                                       'réparation', 'assurance', 'taxe', 'syndic', '€', 'eur']):
            return 'EVENEMENT_SIMPLE'
        
        return 'UNKNOWN'


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
        """Génère propositions pour initialisation bilan 2023"""
        
        propositions = []
        for i, compte in enumerate(comptes, 1):
            propositions.append({
                "numero_ecriture": f"2023-INIT-{i:04d}",
                "type": "INIT_BILAN_2023",
                "compte_debit": compte["compte"],
                "compte_credit": "899",  # Compte équilibre temporaire
                "montant": compte["solde"],
                "libelle": f"Ouverture: {compte['libelle']}"
            })
        
        token = hashlib.md5(json.dumps(propositions, sort_keys=True).encode()).hexdigest()
        markdown = GenerateurPropositions._generer_markdown_init_bilan(propositions, comptes)
        
        return markdown, {"propositions": propositions, "token": token}, token
    
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
        md += "\n## Écritures d'Ouverture\n\n"
        
        for prop in propositions[:5]:  # Montrer les 5 premières
            md += f"- {prop['numero_ecriture']}: {prop['libelle']}\n"
        
        if len(propositions) > 5:
            md += f"- ... et {len(propositions) - 5} autres écritures\n"
        
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
              "type_detecte": "EVENEMENT_SIMPLE" | "INIT_BILAN_2023" | "CLOTURE_EXERCICE",
              "statut": "OK" | "ERREUR",
              "markdown": "...",
              "propositions": {...},
              "token": "...",
              "message": "..."
            }
        """
        
        type_evt = DetecteurTypeEvenement.detecter(email)
        
        if type_evt == 'EVENEMENT_SIMPLE':
            return self._traiter_evenement_simple(email)
        elif type_evt == 'INIT_BILAN_2023':
            return self._traiter_init_bilan_2023(email)
        elif type_evt == 'CLOTURE_EXERCICE':
            return self._traiter_cloture_2023(email)
        else:
            return {
                "type_detecte": "UNKNOWN",
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
                    "type_detecte": "EVENEMENT_SIMPLE",
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
                "type_detecte": "EVENEMENT_SIMPLE",
                "type_specifique": type_evt,
                "statut": "OK",
                "markdown": markdown,
                "propositions": props,
                "token": token,
                "message": f"1 proposition générée ({type_evt}: {montant}€)"
            }
        
        except Exception as e:
            return {
                "type_detecte": "EVENEMENT_SIMPLE",
                "statut": "ERREUR",
                "message": f"Erreur traitement: {str(e)[:100]}",
                "markdown": "",
                "propositions": {},
                "token": ""
            }
    
    def _traiter_init_bilan_2023(self, email: Dict) -> Dict:
        """Traite initialisation bilan 2023"""
        try:
            attachments = email.get('attachments', [])
            pdf_files = [a for a in attachments if a.get('content_type') == 'application/pdf']
            
            if not pdf_files:
                return {
                    "type_detecte": "INIT_BILAN_2023",
                    "statut": "ERREUR",
                    "message": "Aucun PDF trouvé en pièce jointe",
                    "markdown": "",
                    "propositions": {},
                    "token": ""
                }
            
            # Parser le premier PDF (bilan 2023)
            filepath = pdf_files[0].get('filepath')
            comptes = self.parseur_bilan.parse_from_pdf(filepath)
            
            if not comptes:
                return {
                    "type_detecte": "INIT_BILAN_2023",
                    "statut": "ERREUR",
                    "message": "Impossible d'extraire les comptes du bilan",
                    "markdown": "",
                    "propositions": {},
                    "token": ""
                }
            
            # Générer propositions
            markdown, props, token = GenerateurPropositions.generer_propositions_init_bilan_2023(comptes)
            
            return {
                "type_detecte": "INIT_BILAN_2023",
                "statut": "OK",
                "markdown": markdown,
                "propositions": props,
                "token": token,
                "message": f"{len(comptes)} comptes importés pour initialisation bilan 2023"
            }
        
        except Exception as e:
            return {
                "type_detecte": "INIT_BILAN_2023",
                "statut": "ERREUR",
                "message": f"Erreur parsing bilan: {str(e)[:100]}",
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
                    "type_detecte": "CLOTURE_EXERCICE",
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
                    "type_detecte": "CLOTURE_EXERCICE",
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
                "type_detecte": "CLOTURE_EXERCICE",
                "statut": "OK",
                "markdown": markdown,
                "propositions": props,
                "token": token,
                "message": f"Clôture 2023: {len(props.get('propositions', []))} propositions générées"
            }
        
        except Exception as e:
            return {
                "type_detecte": "CLOTURE_EXERCICE",
                "statut": "ERREUR",
                "message": f"Erreur traitement clôture: {str(e)[:100]}",
                "markdown": "",
                "propositions": {},
                "token": ""
            }


if __name__ == "__main__":
    import os
    
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    db_url = os.environ.get('DATABASE_URL')
    
    if not api_key or not db_url:
        print("❌ ANTHROPIC_API_KEY ou DATABASE_URL non définis")
        exit(1)
    
    workflow = WorkflowModule2V2(api_key, db_url)
    print("✅ Module 2 Workflow V2 chargé et prêt")
