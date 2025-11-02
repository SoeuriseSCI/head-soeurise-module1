"""
PARSEUR BILAN V6 - AVEC FUNCTION CALLING
=========================================

Architecture V6 : Claude extrait TOUS les comptes du bilan d'ouverture

Différences vs V5 :
- V5 : Regex simple → Échoue avec espaces dans montants, négatifs, etc.
- V6 : Function Calling → Extraction structurée JSON complète

Avantages V6 :
- Gère les montants avec espaces ("500 032" → 500032.00)
- Gère les montants négatifs ("-50 003" → -50003.00)
- Extraction complète des comptes ACTIF + PASSIF
- Validation équilibre automatique
"""

import io
import json
import base64
from typing import Dict, List, Optional
from pathlib import Path

import anthropic

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

from tools_definitions import TOOL_EXTRACT_BILAN_ACCOUNTS
from tools_executor import execute_tool


class ParseurBilan2023V6:
    """
    Parse bilan d'ouverture complet avec Function Calling (V6)

    Claude :
    1. Analyse le PDF (pages 7-8: BILAN ACTIF/PASSIF DÉTAILLÉ)
    2. Extrait TOUS les comptes (actif + passif)
    3. Appelle extract_bilan_accounts()
    4. Retourne le résultat structuré
    """

    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        self.api_key = api_key
        self.model = model
        self.client = anthropic.Anthropic(api_key=api_key)

    def parse_from_pdf(self, filepath: str, exercice: str = "2023") -> Dict:
        """
        Parse bilan d'ouverture complet avec Function Calling

        Args:
            filepath: Chemin vers PDF bilan comptable
            exercice: Année de l'exercice (ex: "2023")

        Returns:
            {
                "success": True,
                "exercice": "2023",
                "date_bilan": "2023-12-31",
                "nb_comptes": 10,
                "comptes_actif": [...],
                "comptes_passif": [...],
                "total_actif": 463618.00,
                "total_passif": 463618.00,
                "equilibre": True
            }
        """
        if not PDF2IMAGE_AVAILABLE:
            return {
                "success": False,
                "error": "pdf2image non disponible",
                "message": "Installer avec: pip install pdf2image poppler-utils"
            }

        try:
            # 1. Convertir PDF → Images (DPI réduit pour économiser mémoire)
            images = convert_from_path(filepath, dpi=100)  # Même optimisation que parseur prêt V6

            if not images:
                return {
                    "success": False,
                    "error": "PDF vide ou illisible",
                    "message": f"Impossible de convertir {filepath} en images"
                }

            print(f"[PARSEUR BILAN V6] PDF converti : {len(images)} pages", flush=True)

            # 2. Préparer les images pour Claude
            # Pages 7-8 contiennent le bilan détaillé (mais on envoie toutes les pages pour être sûr)
            image_contents = []
            # Limiter à 15 pages pour avoir assez de contexte (bilan détaillé)
            max_pages = min(15, len(images))

            for page_num, image in enumerate(images[:max_pages]):
                buffer = io.BytesIO()
                # Compression JPEG qualité 85 (au lieu de 95 par défaut)
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

                # Libérer mémoire image PIL
                buffer.close()
                del image

            # Libérer liste images complète
            del images

            print(f"[PARSEUR BILAN V6] {len(image_contents)} pages préparées pour Claude (mémoire optimisée)", flush=True)

            # 3. Appel Claude API avec Function Calling
            result = self._call_claude_with_tools(image_contents, filepath, exercice)

            return result

        except Exception as e:
            print(f"[PARSEUR BILAN V6 ERROR] {str(e)}", flush=True)
            import traceback
            traceback.print_exc()

            return {
                "success": False,
                "error": str(e),
                "message": f"Erreur lors du parsing: {str(e)}"
            }

    def _call_claude_with_tools(self,
                                 image_contents: List[Dict],
                                 filepath: str,
                                 exercice: str) -> Dict:
        """
        Appelle Claude API avec Function Calling activé

        Claude va analyser les images et appeler le tool :
        1. extract_bilan_accounts() - Extraction des comptes du bilan
        """

        # Prompt système
        system_prompt = f"""Tu es un expert en extraction de bilans comptables.

Ton rôle :
1. Analyser le PDF de bilan comptable (comptes annuels {exercice})
2. Trouver les pages "BILAN - ACTIF DÉTAILLÉ" et "BILAN - PASSIF DÉTAILLÉ"
3. Extraire TOUS les comptes du bilan avec leurs montants
4. Appeler le tool extract_bilan_accounts avec les données extraites

PAGES IMPORTANTES :
- Généralement pages 7-8 : BILAN - ACTIF DÉTAILLÉ / BILAN - PASSIF DÉTAILLÉ
- Ces pages contiennent les comptes détaillés avec numéros et montants

FORMAT DES MONTANTS :
- Les montants peuvent contenir des ESPACES : "500 032" → 500032.00
- Les montants peuvent être NÉGATIFS : "-50 003" → -50003.00
- Utiliser le point comme séparateur décimal (ex: 463618.00)

COMPTES À EXTRAIRE :

**ACTIF (comptes débiteurs au bilan) :**
- 280 : Titres immobilisés (SCPI, participations)
- 290 : Provisions (montant NÉGATIF - ex: Provision epargne pierre)
- 412 : Autres créances
- 502 : Actions / Valeurs mobilières
- 512 : Banque / Disponibilités

**PASSIF (comptes créditeurs au bilan) :**
- 101 : Capital social
- 120 : Report à nouveau (peut être NÉGATIF si déficit cumulé)
- 130 : Résultat de l'exercice (peut être NÉGATIF si perte)
- 161 : Emprunts / Dettes financières
- 401 : Dettes fournisseurs
- 444 : Comptes courants d'associés

RÈGLES D'EXTRACTION :
1. IGNORER les lignes de totaux intermédiaires (TOTAL ACTIF IMMOBILISÉ, TOTAL ACTIF CIRCULANT, etc.)
2. EXTRAIRE uniquement les comptes avec numéros de 1 à 3 chiffres
3. Pour les montants avec espaces : "500 032" → convertir en 500032.00
4. Pour les montants négatifs : "-50 003" → convertir en -50003.00
5. Conserver les libellés complets (ex: "Titres immobilisés - epargne pierre", "Banque LCL")

VALIDATION :
- Total ACTIF doit = Total PASSIF
- Si différence > 0.01€ → ERREUR dans l'extraction

EXEMPLES DE CONVERSION :
- "500 032" → 500032.00
- "-50 003" → -50003.00
- "7 356" → 7356.00
- "1 000" → 1000.00

Après extraction complète, appelle le tool extract_bilan_accounts avec :
- exercice: "{exercice}"
- date_bilan: "YYYY-MM-DD" (date de fin d'exercice, généralement 31/12/{exercice})
- comptes_actif: [liste complète des comptes ACTIF]
- comptes_passif: [liste complète des comptes PASSIF]
- total_actif: somme des comptes ACTIF (attention aux négatifs!)
- total_passif: somme des comptes PASSIF (attention aux négatifs!)
"""

        # Construction du message utilisateur
        user_message = [
            {
                "type": "text",
                "text": f"Extrait le bilan d'ouverture {exercice} depuis ce PDF de comptes annuels. Trouve les pages 'BILAN - ACTIF DÉTAILLÉ' et 'BILAN - PASSIF DÉTAILLÉ' et extrait tous les comptes."
            }
        ] + image_contents

        print(f"[PARSEUR BILAN V6] Appel Claude API avec Function Calling...", flush=True)

        # Appel Claude avec tools
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=8000,  # Bilan moins complexe que prêt → moins de tokens
                system=system_prompt,
                tools=[TOOL_EXTRACT_BILAN_ACCOUNTS],
                messages=[
                    {
                        "role": "user",
                        "content": user_message
                    }
                ]
            )

            print(f"[PARSEUR BILAN V6] Réponse Claude reçue (stop_reason: {response.stop_reason})", flush=True)

            # Traiter la réponse
            result = self._process_claude_response(response, exercice)

            return result

        except Exception as e:
            print(f"[PARSEUR BILAN V6 ERROR] Erreur appel Claude: {str(e)}", flush=True)
            import traceback
            traceback.print_exc()

            return {
                "success": False,
                "error": str(e),
                "message": f"Erreur lors de l'appel Claude API: {str(e)}"
            }

    def _process_claude_response(self, response, exercice: str) -> Dict:
        """
        Traite la réponse de Claude et exécute les tool calls
        """
        result = {
            "success": False,
            "message": "Aucun tool call reçu"
        }

        # Parcourir les content blocks
        for block in response.content:
            if block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input

                print(f"[PARSEUR BILAN V6] Tool call reçu: {tool_name}", flush=True)

                if tool_name == "extract_bilan_accounts":
                    # Exécuter le tool
                    result = execute_tool(tool_name, tool_input)

        return result


# ============================================================================
# FONCTION HELPER POUR INTÉGRATION
# ============================================================================

def parse_bilan_v6(filepath: str, api_key: str, exercice: str = "2023") -> Dict:
    """
    Helper function pour parser un bilan avec V6

    Args:
        filepath: Chemin vers PDF bilan
        api_key: Clé API Anthropic
        exercice: Année de l'exercice

    Returns:
        Dict avec résultat de l'extraction
    """
    parser = ParseurBilan2023V6(api_key=api_key)
    return parser.parse_from_pdf(filepath, exercice)
