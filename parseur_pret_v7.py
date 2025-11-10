"""
PARSEUR TABLEAU PRÊT V7 - APPROCHE SIMPLIFIÉE
===============================================

Architecture V7 : Claude analyse directement et retourne JSON (SANS Function Calling)

Différences vs V6 :
- V6 : Function Calling → Claude appelle tools → Complexité
- V7 : JSON direct → Claude retourne tout d'un coup → Simple

Avantages V7 :
- Prompt simple et universel (pas spécifique LCL)
- Pas de limitation à 10 pages
- Flux naturel (comme Claude chat)
- Validation Python stricte post-extraction
- Fonctionne avec n'importe quelle banque
"""

import io
import json
import base64
import os
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
from decimal import Decimal

import anthropic

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False


class ParseurTableauPretV7:
    """
    Parse tableau d'amortissement avec approche simplifiée (V7)

    Claude :
    1. Analyse TOUTES les pages du PDF
    2. Retourne JSON directement avec métadonnées + échéances
    3. Python valide la cohérence
    4. Sauvegarde MD + BD
    """

    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        self.api_key = api_key
        self.model = model
        self.client = anthropic.Anthropic(api_key=api_key)

    def parse_from_pdf(self, filepath: str, auto_insert_bd: bool = True) -> Dict:
        """
        Parse tableau amortissement avec prompt simple

        Args:
            filepath: Chemin vers PDF tableau amortissement
            auto_insert_bd: Si True, insère en BD après validation

        Returns:
            {
                "success": True,
                "pret": {...},
                "echeances": [...],
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
            # 1. Convertir TOUTES les pages du PDF (pas de limitation)
            print(f"[PARSEUR V7] Conversion PDF → Images (DPI 150)...", flush=True)
            images = convert_from_path(filepath, dpi=150)  # Qualité supérieure vs V6 (100)

            if not images:
                return {
                    "success": False,
                    "error": "PDF vide ou illisible",
                    "message": f"Impossible de convertir {filepath} en images"
                }

            print(f"[PARSEUR V7] {len(images)} pages converties (TOUTES traitées)", flush=True)

            # 2. Préparer les images pour Claude (TOUTES, pas max 10 comme V6)
            image_contents = []

            for page_num, image in enumerate(images):
                buffer = io.BytesIO()
                # Qualité 90 (vs 85 en V6) pour meilleure précision
                image.save(buffer, format='JPEG', quality=90, optimize=True)
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
                del image

            del images

            print(f"[PARSEUR V7] {len(image_contents)} pages préparées pour Claude", flush=True)

            # 3. Appel Claude avec prompt SIMPLE et UNIVERSEL
            result = self._call_claude_simple(image_contents, filepath)

            if not result.get('success'):
                return result

            # 4. Validation Python stricte
            print(f"[PARSEUR V7] Validation des données extraites...", flush=True)
            validation_errors = self._validate_pret_data(result['data'])

            if validation_errors:
                return {
                    "success": False,
                    "error": "Validation échouée",
                    "errors": validation_errors[:10],  # Max 10 erreurs
                    "message": f"{len(validation_errors)} erreur(s) détectée(s)"
                }

            # 5. Sauvegarde fichier MD
            filename = self._save_to_md_file(result['data'])
            result['filename'] = filename

            # 6. Insertion BD (optionnel)
            if auto_insert_bd:
                pret_id = self._save_to_database(result['data'], filename)
                result['pret_id'] = pret_id

            return {
                "success": True,
                "pret": result['data']['pret'],
                "echeances": result['data']['echeances'],
                "filename": filename,
                "nb_echeances": len(result['data']['echeances']),
                "pret_id": result.get('pret_id')
            }

        except Exception as e:
            print(f"[PARSEUR V7 ERROR] {str(e)}", flush=True)
            import traceback
            traceback.print_exc()

            return {
                "success": False,
                "error": str(e),
                "message": f"Erreur lors du parsing: {str(e)}"
            }

    def _call_claude_simple(self, image_contents: List[Dict], filepath: str) -> Dict:
        """
        Appelle Claude API SANS Function Calling (prompt simple)

        Claude retourne directement un JSON avec toutes les données
        """

        # Prompt SIMPLE et UNIVERSEL (pas spécifique à une banque)
        prompt = """Analyse ce tableau d'amortissement de prêt immobilier.

Extrait et retourne UN SEUL objet JSON avec cette structure exacte :

{
  "pret": {
    "numero_pret": "Numéro du contrat (string)",
    "intitule": "Nom du produit (ex: SOLUTION P IMMO, INVESTIMUR, etc.)",
    "banque": "Nom de la banque (ex: LCL, Crédit Agricole, etc.)",
    "montant_initial": Montant emprunté en EUR (number),
    "taux_annuel": Taux d'intérêt annuel en % (number, ex: 1.05 pour 1.05%),
    "duree_mois": Durée totale en mois (integer),
    "date_debut": "Date de début du prêt au format YYYY-MM-DD",
    "date_debut_amortissement": "Date de début d'amortissement au format YYYY-MM-DD",
    "type_pret": "AMORTISSEMENT_CONSTANT" ou "IN_FINE"
  },
  "echeances": [
    {
      "date_echeance": "Date au format YYYY-MM-DD",
      "montant_total": Montant de l'échéance en EUR (number),
      "montant_capital": Part de capital remboursé en EUR (number),
      "montant_interet": Part d'intérêts en EUR (number),
      "capital_restant_du": Capital restant après cette échéance en EUR (number)
    },
    // ... toutes les échéances (généralement 200-300 lignes)
  ]
}

INSTRUCTIONS :

1. **Métadonnées du prêt** (généralement page 1) :
   - Cherche les informations du contrat en haut du document
   - Le type de prêt :
     * "IN_FINE" : capital remboursé = 0 pendant presque toute la durée, puis ballon final
     * "AMORTISSEMENT_CONSTANT" : capital remboursé augmente progressivement

2. **Tableau des échéances** (pages suivantes) :
   - Extrait CHAQUE ligne du tableau d'amortissement
   - Ne saute AUCUNE page
   - Pour chaque échéance, identifie les 5 valeurs :
     * Date de l'échéance
     * Montant total de l'échéance (mensualité payée)
     * Capital amorti/remboursé
     * Intérêts payés
     * Capital restant dû APRÈS cette échéance

3. **Règles importantes** :
   - Ignore les lignes de frais de dossier ou doublons éventuels
   - Vérifie que : montant_total ≈ montant_capital + montant_interet
   - Tu dois obtenir environ 200-300 échéances selon le prêt
   - Dates doivent être chronologiques (mensualités)

4. **Format de sortie** :
   - Retourne UNIQUEMENT le JSON, rien d'autre
   - Pas de texte avant ou après
   - Pas de ```json``` ou de markdown
   - JSON valide et complet

Analyse maintenant le document et retourne le JSON."""

        try:
            # Appel API SANS tools (réponse JSON directe)
            print(f"[PARSEUR V7] Appel Claude API (max_tokens=64000)...", flush=True)

            response = self.client.messages.create(
                model=self.model,
                max_tokens=64000,  # Limite max Haiku 4.5 (vs V6: 20000)
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        *image_contents
                    ]
                }],
                timeout=600.0  # 10 minutes
            )

            print(f"[PARSEUR V7] Réponse reçue (stop_reason: {response.stop_reason})", flush=True)

            # Extraire le texte de la réponse
            response_text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    response_text = block.text
                    break

            if not response_text:
                return {
                    "success": False,
                    "error": "Réponse vide",
                    "message": "Claude n'a pas retourné de texte"
                }

            # Parser le JSON
            # Claude peut parfois entourer le JSON de ```json ... ```
            response_text = response_text.strip()
            if response_text.startswith('```'):
                # Extraire le JSON du code block
                lines = response_text.split('\n')
                response_text = '\n'.join(lines[1:-1])  # Enlever première et dernière ligne

            data = json.loads(response_text)

            # Vérifier structure minimale
            if 'pret' not in data or 'echeances' not in data:
                return {
                    "success": False,
                    "error": "Structure JSON invalide",
                    "message": "JSON doit contenir 'pret' et 'echeances'"
                }

            print(f"[PARSEUR V7] JSON parsé : {len(data['echeances'])} échéances extraites", flush=True)

            return {
                "success": True,
                "data": data
            }

        except json.JSONDecodeError as e:
            print(f"[PARSEUR V7 ERROR] JSON invalide : {str(e)}", flush=True)
            return {
                "success": False,
                "error": "JSON invalide",
                "message": f"Impossible de parser le JSON retourné par Claude : {str(e)}"
            }
        except Exception as e:
            print(f"[PARSEUR V7 ERROR] {str(e)}", flush=True)
            return {
                "success": False,
                "error": str(e),
                "message": f"Erreur lors de l'appel Claude : {str(e)}"
            }

    def _validate_pret_data(self, data: Dict) -> List[str]:
        """
        Valide la cohérence des données extraites (validation Python stricte)

        Returns:
            Liste des erreurs (vide si OK)
        """
        errors = []

        # Validation métadonnées prêt
        pret = data.get('pret', {})

        if not pret.get('numero_pret'):
            errors.append("Métadonnée manquante : numero_pret")

        if not pret.get('banque'):
            errors.append("Métadonnée manquante : banque")

        if not pret.get('montant_initial') or pret['montant_initial'] <= 0:
            errors.append("Métadonnée invalide : montant_initial doit être > 0")

        if not pret.get('taux_annuel') or pret['taux_annuel'] <= 0:
            errors.append("Métadonnée invalide : taux_annuel doit être > 0")

        if not pret.get('duree_mois') or pret['duree_mois'] <= 0:
            errors.append("Métadonnée invalide : duree_mois doit être > 0")

        # Validation échéances
        echeances = data.get('echeances', [])

        if len(echeances) < 100:
            errors.append(f"Trop peu d'échéances : {len(echeances)} (attendu 200-300)")

        if len(echeances) > 500:
            errors.append(f"Trop d'échéances : {len(echeances)} (attendu 200-300)")

        # Validation ligne par ligne (max 10 erreurs pour ne pas surcharger)
        nb_errors_max = 10

        for i, ech in enumerate(echeances):
            if len(errors) >= nb_errors_max:
                errors.append(f"... ({len(echeances) - i} échéances non vérifiées)")
                break

            # Vérif champs requis
            if not ech.get('date_echeance'):
                errors.append(f"Échéance {i+1} : date_echeance manquante")
                continue

            # Vérif cohérence montant (tolérance 0.01€ pour arrondis)
            montant_total = ech.get('montant_total', 0)
            montant_capital = ech.get('montant_capital', 0)
            montant_interet = ech.get('montant_interet', 0)

            total_calc = montant_capital + montant_interet

            if abs(total_calc - montant_total) > 0.01:
                errors.append(
                    f"Échéance {i+1} ({ech['date_echeance']}) : "
                    f"incohérence montant (total={montant_total:.2f} != capital+intérêt={total_calc:.2f})"
                )

            # Vérif capital restant diminue (ou constant pour IN_FINE)
            if i > 0:
                capital_precedent = echeances[i-1].get('capital_restant_du', 0)
                capital_actuel = ech.get('capital_restant_du', 0)

                if capital_actuel > capital_precedent + 0.01:  # Tolérance arrondi
                    errors.append(
                        f"Échéance {i+1} ({ech['date_echeance']}) : "
                        f"capital restant AUGMENTE ({capital_precedent:.2f} → {capital_actuel:.2f})"
                    )

        return errors

    def _save_to_md_file(self, data: Dict) -> str:
        """
        Sauvegarde les données dans un fichier MD

        Returns:
            Nom du fichier créé
        """
        pret = data['pret']
        echeances = data['echeances']

        # Nom du fichier
        numero_pret = pret['numero_pret'].replace('/', '_').replace(' ', '_')
        filename = f"PRET_{numero_pret}_echeances.md"

        # Construction du contenu
        lines = [
            f"# Échéances Prêt {pret['numero_pret']}",
            "",
            f"**Intitulé** : {pret['intitule']}",
            f"**Banque** : {pret['banque']}",
            f"**Montant initial** : {pret['montant_initial']:.2f} EUR",
            f"**Taux annuel** : {pret['taux_annuel']}%",
            f"**Durée** : {pret['duree_mois']} mois",
            f"**Date début** : {pret['date_debut']}",
            f"**Date début amortissement** : {pret.get('date_debut_amortissement', 'N/A')}",
            f"**Type** : {pret['type_pret']}",
            "",
            f"**Extraction** : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Nombre d'échéances** : {len(echeances)}",
            "",
            "---",
            "",
            "**Format** : date_echeance:montant_total:montant_capital:montant_interet:capital_restant_du",
            ""
        ]

        # Ajouter les échéances
        for ech in echeances:
            line = (
                f"{ech['date_echeance']}:"
                f"{ech['montant_total']:.2f}:"
                f"{ech['montant_capital']:.2f}:"
                f"{ech['montant_interet']:.2f}:"
                f"{ech['capital_restant_du']:.2f}"
            )
            lines.append(line)

        content = "\n".join(lines)

        # Écriture du fichier
        filepath = os.path.join(os.getcwd(), filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"[PARSEUR V7] Fichier créé : {filename}", flush=True)

        return filename

    def _save_to_database(self, data: Dict, filename: str) -> int:
        """
        Sauvegarde le prêt et les échéances en base de données

        Returns:
            ID du prêt créé
        """
        from prets_manager import PretsManager
        from models_module2 import get_session

        # Récupérer la DATABASE_URL
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            raise ValueError("DATABASE_URL non définie")

        session = get_session(database_url)

        try:
            manager = PretsManager(session)

            pret = data['pret']
            echeances = data['echeances']

            # Préparer données prêt
            pret_data = {
                'numero_pret': pret['numero_pret'],
                'intitule': pret['intitule'],
                'banque': pret['banque'],
                'montant_initial': Decimal(str(pret['montant_initial'])),
                'taux_annuel': Decimal(str(pret['taux_annuel'])),
                'duree_mois': pret['duree_mois'],
                'date_debut': datetime.strptime(pret['date_debut'], '%Y-%m-%d').date(),
                'date_debut_amortissement': datetime.strptime(
                    pret.get('date_debut_amortissement', pret['date_debut']),
                    '%Y-%m-%d'
                ).date(),
                'type_pret': pret['type_pret'],
                'fichier_reference': filename
            }

            # Préparer données échéances
            echeances_data = []
            for ech in echeances:
                echeances_data.append({
                    'date_echeance': ech['date_echeance'],
                    'montant_total': float(ech['montant_total']),
                    'montant_capital': float(ech['montant_capital']),
                    'montant_interet': float(ech['montant_interet']),
                    'capital_restant_du': float(ech['capital_restant_du'])
                })

            # Insertion
            success, message, pret_id = manager.inserer_pret_et_echeances(
                pret_data,
                echeances_data
            )

            if success:
                session.commit()
                print(f"[PARSEUR V7] Prêt inséré en BD (ID: {pret_id})", flush=True)
                return pret_id
            else:
                session.rollback()
                raise ValueError(f"Erreur insertion BD : {message}")

        finally:
            session.close()


if __name__ == "__main__":
    print("ParseurTableauPretV7 - Approche simplifiée (JSON direct)")
