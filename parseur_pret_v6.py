"""
PARSEUR TABLEAU PRÊT V6 - AVEC FUNCTION CALLING
================================================

Architecture V6 : Claude extrait TOUTES les échéances et appelle des tools

Différences vs V5 :
- V5 : Extrait 24 échéances → Génère le reste
- V6 : Extrait TOUTES les échéances (216-252) → Tools pour fichier MD + BD

Avantages V6 :
- Aucune génération = Aucune erreur de calcul
- Données 100% depuis PDF (source de vérité)
- Traçabilité (fichier MD versionné sur GitHub)
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

from tools_definitions import ALL_TOOLS
from tools_executor import execute_tool


class ParseurTableauPretV6:
    """
    Parse tableau d'amortissement complet avec Function Calling (V6)

    Claude :
    1. Analyse le PDF
    2. Extrait TOUTES les échéances (216-252 lignes)
    3. Appelle extract_all_echeances_to_file()
    4. Appelle insert_pret_from_file()
    5. Met à jour mémoire courte
    """

    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        self.api_key = api_key
        self.model = model
        self.client = anthropic.Anthropic(api_key=api_key)

    def parse_from_pdf(self, filepath: str, auto_insert_bd: bool = True) -> Dict:
        """
        Parse tableau amortissement complet avec Function Calling

        Args:
            filepath: Chemin vers PDF tableau amortissement
            auto_insert_bd: Si True, appelle automatiquement insert_pret_from_file

        Returns:
            {
                "success": True,
                "pret": {...},
                "filename": "PRET_X_echeances.md",
                "nb_echeances": 252,
                "pret_id": 3
            }
        """
        if not PDF2IMAGE_AVAILABLE:
            return {
                "success": False,
                "error": "pdf2image non disponible",
                "message": "Installer avec: pip install pdf2image poppler-utils"
            }

        try:
            # 1. Convertir PDF → Images
            images = convert_from_path(filepath, dpi=150)

            if not images:
                return {
                    "success": False,
                    "error": "PDF vide ou illisible",
                    "message": f"Impossible de convertir {filepath} en images"
                }

            print(f"[PARSEUR V6] PDF converti : {len(images)} pages", flush=True)

            # 2. Préparer les images pour Claude
            image_contents = []
            # On traite toutes les pages nécessaires (max 20)
            max_pages = min(20, len(images))

            for page_num, image in enumerate(images[:max_pages]):
                buffer = io.BytesIO()
                image.save(buffer, format='JPEG')
                image_base64 = base64.b64encode(buffer.getvalue()).decode()

                image_contents.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_base64
                    }
                })

            print(f"[PARSEUR V6] {len(image_contents)} pages préparées pour Claude", flush=True)

            # 3. Appel Claude API avec Function Calling
            result = self._call_claude_with_tools(image_contents, filepath, auto_insert_bd)

            return result

        except Exception as e:
            print(f"[PARSEUR V6 ERROR] {str(e)}", flush=True)
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
                                 auto_insert_bd: bool) -> Dict:
        """
        Appelle Claude API avec Function Calling activé

        Claude va analyser les images et appeler les tools :
        1. extract_all_echeances_to_file() - Sauvegarde fichier MD
        2. insert_pret_from_file() - Insertion en BD (si auto_insert_bd=True)
        """

        # Prompt système
        system_prompt = """Tu es un expert en extraction de tableaux d'amortissement de prêts immobiliers LCL/Crédit Lyonnais.

Ton rôle :
1. Analyser le PDF (tableau d'amortissement LCL)
2. Extraire les paramètres du prêt (numéro, montant, taux, durée, dates)
3. Extraire TOUTES les échéances ligne par ligne (généralement 200-300 lignes)
4. Sauvegarder avec le tool extract_all_echeances_to_file
5. Insérer en BD avec le tool insert_pret_from_file (OBLIGATOIRE après l'extraction)

FORMAT DU TABLEAU LCL (colonnes à lire de gauche à droite) :
┌────────┬──────────┬────────────┬────────────┬────────────┬───────────────┐
│ Type   │   Date   │ Montant    │ Capital    │ Intérêts   │ Capital Restant│
│ Ligne  │          │ Échéance   │ Amorti     │ Payés      │ Dû            │
├────────┼──────────┼────────────┼────────────┼────────────┼───────────────┤
│ DBL    │15/04/2022│    0,00    │    0,00    │  250 000,00│     0,00      │ ← IGNORER (double month)
│ ECH    │15/04/2022│    0,00    │    0,00    │    0,00    │    250,00     │ ← IGNORER (frais dossier)
│ ECH    │15/05/2022│    0,00    │    0,00    │  250 000,00│     0,00      │ ← EXTRAIRE
│ ECH    │15/06/2022│    0,00    │    0,00    │  250 000,00│     0,00      │ ← EXTRAIRE
│ ...    │   ...    │    ...     │    ...     │    ...     │     ...       │
│ 014    │15/05/2023│ 1 166,59   │    0,00    │  250 000,00│  1 494,37     │ ← EXTRAIRE (ligne numérotée)
│ 015    │15/06/2023│ 1 166,59   │    0,00    │  250 000,00│  1 494,37     │ ← EXTRAIRE
└────────┴──────────┴────────────┴────────────┴────────────┴───────────────┘

RÈGLES D'EXTRACTION STRICTES :
✅ EXTRAIRE :
   - Lignes "ECH" SAUF la toute première (frais de dossier)
   - Lignes numérotées (001, 002, ..., 240)

❌ IGNORER :
   - Lignes "DBL" (double month)
   - Première ligne "ECH" (frais de dossier)

⚠️ MAPPING DES COLONNES (VÉRIFIE LE PDF) :
Dans le tableau LCL, tu trouveras ces colonnes dans cet ordre :
1. Type de ligne (ECH, DBL, numéro)
2. Date
3-6. Les 4 valeurs numériques qui correspondent à :
   - Montant échéance (mensualité payée, peut être 0 pendant franchise)
   - Capital amorti (remboursé, souvent 0 en début de prêt IN FINE)
   - Intérêts payés POUR CETTE ÉCHÉANCE (pas cumulatif, ex: 258.33)
   - Capital restant dû APRÈS cette échéance (ex: 250000.00)

ATTENTION: Les colonnes peuvent varier selon le format LCL. Identifie-les en regardant :
- Pendant la franchise : capital amorti = 0, intérêts = petit montant ou 0
- Pendant amortissement : capital amorti augmente progressivement
- Capital restant dû diminue progressivement (sauf IN FINE où il reste constant)

Pour chaque ligne extraite, tu dois déterminer :
- date_echeance : Date (format YYYY-MM-DD)
- montant_total : Montant de l'échéance/mensualité
- montant_capital : Capital amorti
- montant_interet : Intérêts payés pour CETTE échéance uniquement
- capital_restant_du : Capital restant dû APRÈS cette échéance

EXEMPLES ATTENDUS (format sortie) :
Franchise totale → 2022-05-15:0.00:0.00:0.00:250000.00
IN FINE (intérêts seuls) → 2023-05-15:258.33:0.00:258.33:250000.00
Amortissement constant → 2024-05-15:1166.59:955.68:210.91:240079.37
"""

        # Message utilisateur avec images
        user_message = {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": """Analyse ce tableau d'amortissement de prêt immobilier LCL.

📋 ÉTAPE 1 : EXTRACTION PARAMÈTRES DU PRÊT (Page 1)
Extrait :
- Numéro du prêt (ex: "N° DU PRET : 5009736BRM0911AH")
- Intitulé (ex: "SOLUTION P IMMO A TAUX FIXE" ou "INVESTIMUR")
- Banque : "LCL"
- Montant initial (ex: "MONTANT TOTAL DEBLOQUE : EUR 250 000,00")
- Taux annuel (ex: "TAUX DEBITEUR EN COURS : 1,050000 %")
- Durée totale (ex: "DUREE TOTALE DU PRET : 252 MOIS")
- Date de début (ex: "DATE DE DEPART DU PRET : 15.04.2022")
- Date début amortissement (ex: "DATE DEBUT AMORTISSEMENT : 15.04.2023")

Détermine le type de prêt :
- "IN_FINE" : Si capital remboursé = 0 pendant presque toute la durée, puis ballon final
- "AMORTISSEMENT_CONSTANT" : Si capital remboursé augmente progressivement chaque mois

📊 ÉTAPE 2 : EXTRACTION DE **TOUTES** LES ÉCHÉANCES (Pages 2+)
Va page par page et extrait CHAQUE ligne d'échéance du tableau.

RÈGLES STRICTES D'EXTRACTION :
✅ À EXTRAIRE (devrait donner 216-252 lignes au total) :
   - Lignes "ECH" sauf la toute première
   - Lignes numérotées (001, 002, 003, ...)

❌ À IGNORER :
   - Lignes "DBL" (double month - indiquées par "DBL")
   - Première ligne "ECH" uniquement (frais de dossier)

⚠️ VÉRIFICATION :
- Assure-toi d'avoir extrait TOUTES les pages du tableau (pas juste 2-3 pages)
- Vérifie que les dates sont séquentielles (15/05/2022, 15/06/2022, 15/07/2022, ...)
- Compte : tu dois obtenir entre 216 et 252 échéances selon le prêt

💾 ÉTAPE 3 : SAUVEGARDE (OBLIGATOIRE)
Appelle le tool :
extract_all_echeances_to_file(
    numero_pret="...",
    filename="PRET_{numero}_echeances.md",
    echeances=[...toutes les 216-252 échéances...]
)

🗄️ ÉTAPE 4 : INSERTION EN BASE DE DONNÉES (OBLIGATOIRE)
Immédiatement après l'étape 3, appelle le tool :
insert_pret_from_file(
    filename="PRET_{numero}_echeances.md",
    pret_params={
        "numero_pret": "...",
        "intitule": "...",
        "banque": "LCL",
        "montant_initial": ...,
        "taux_annuel": ...,
        "duree_mois": ...,
        "date_debut": "YYYY-MM-DD",
        "date_debut_amortissement": "YYYY-MM-DD",
        "type_pret": "IN_FINE" ou "AMORTISSEMENT_CONSTANT"
    }
)

Tu DOIS appeler ces 2 tools dans l'ordre pour compléter la tâche.
"""
                },
                *image_contents
            ]
        }

        # Boucle de conversation avec tools
        messages = [user_message]
        result_data = {}

        max_turns = 10  # Maximum 10 tours de conversation
        turn = 0

        while turn < max_turns:
            turn += 1
            print(f"\n[PARSEUR V6] Tour {turn}/{max_turns}", flush=True)

            # Appel API avec tools
            response = self.client.messages.create(
                model=self.model,
                max_tokens=32000,  # Augmenté pour gérer 252 échéances (était 16000)
                system=system_prompt,
                messages=messages,
                tools=ALL_TOOLS
            )

            print(f"[PARSEUR V6] Stop reason: {response.stop_reason}", flush=True)

            # Analyser la réponse
            if response.stop_reason == "end_turn":
                # Claude a terminé sans appeler de tool
                # Récupérer le texte final
                for block in response.content:
                    if hasattr(block, 'text'):
                        result_data['message'] = block.text
                        break

                print("[PARSEUR V6] Conversation terminée", flush=True)
                break

            elif response.stop_reason == "tool_use":
                # Claude a appelé un ou plusieurs tools
                assistant_message = {
                    "role": "assistant",
                    "content": response.content
                }
                messages.append(assistant_message)

                # Exécuter les tools
                tool_results = []

                for block in response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        tool_use_id = block.id

                        print(f"[PARSEUR V6] Exécution tool: {tool_name}", flush=True)

                        # Exécuter le tool
                        tool_result = execute_tool(tool_name, tool_input)

                        # Stocker les résultats importants
                        if tool_name == "extract_all_echeances_to_file" and tool_result.get('success'):
                            result_data['filename'] = tool_result['filename']
                            result_data['nb_echeances'] = tool_result['nb_echeances']

                        if tool_name == "insert_pret_from_file" and tool_result.get('success'):
                            result_data['pret_id'] = tool_result['pret_id']

                        # Ajouter le résultat pour Claude
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": json.dumps(tool_result, default=str)
                        })

                # Envoyer les résultats des tools à Claude
                user_message_with_results = {
                    "role": "user",
                    "content": tool_results
                }
                messages.append(user_message_with_results)

            else:
                # Autre raison d'arrêt (max_tokens, erreur, etc.)
                print(f"[PARSEUR V6] Arrêt inattendu: {response.stop_reason}", flush=True)
                break

        # Retourner le résultat
        if 'filename' in result_data:
            return {
                "success": True,
                **result_data
            }
        else:
            return {
                "success": False,
                "error": "Aucun fichier créé",
                "message": "Claude n'a pas appelé extract_all_echeances_to_file"
            }


if __name__ == "__main__":
    print("ParseurTableauPretV6 - Function Calling activé")
