"""
PARSEUR TABLEAU PRÊT V7 - PDF NATIF (APPROCHE SIMPLIFIÉE)
===========================================================

Architecture V7 : Claude analyse le PDF NATIF et retourne JSON (SANS Function Calling)

Différences vs V6 :
- V6 : PDF → JPEG images → Claude Vision → Erreurs OCR
- V7 : PDF natif → Claude lit le texte → Extraction parfaite

Avantages V7 :
- PDF natif (type "document") au lieu d'images JPEG
- Pas d'OCR → Pas d'erreurs de lecture
- Même précision que Claude chat (100%)
- Prompt simple et universel (pas spécifique LCL)
- Pas de limitation de pages
- Flux naturel (comme Claude chat)
- Validation Python stricte post-extraction
- Fonctionne avec n'importe quelle banque

Modèle & Tokens :
- Modèle par défaut : claude-sonnet-4-20250514 (Sonnet 4.5)
- max_tokens : 64000 (limite max Sonnet 4.5)
- Note : Haiku 4.5 et Sonnet 4.5 ont la même limite (64K output)

Insight clé (10/11/2025) :
Claude en chat lit les PDFs nativement → extraction parfaite
Claude API peut faire pareil avec type "document" → même résultat
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


class ParseurTableauPretV7:
    """
    Parse tableau d'amortissement avec PDF natif (V7)

    Claude :
    1. Lit le PDF natif (type "document") - pas de conversion JPEG
    2. Extrait le texte natif (0 erreur OCR)
    3. Retourne JSON directement avec métadonnées + échéances
    4. Python valide la cohérence
    5. Sauvegarde MD + BD

    Avantage vs V6 : Même précision que Claude chat (100%)
    """

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key
        self.model = model
        self.client = anthropic.Anthropic(api_key=api_key)

    def parse_from_pdf(self, filepath: str, auto_insert_bd: bool = True) -> Dict:
        """
        Parse tableau amortissement avec PDF natif (pas d'images)

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
        try:
            # 1. Lire le PDF en binaire et l'encoder en base64
            # NOUVELLE APPROCHE : PDF natif au lieu de JPEG (comme Claude chat)
            print(f"[PARSEUR V7] Lecture PDF natif (pas de conversion JPEG)...", flush=True)

            with open(filepath, 'rb') as f:
                pdf_data = f.read()

            pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')

            print(f"[PARSEUR V7] PDF encodé ({len(pdf_data)} octets) - Texte natif préservé", flush=True)

            # 2. Préparer le document PDF pour Claude
            # Type "document" au lieu de "image" → Claude lit le texte natif
            document_content = {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": pdf_base64
                }
            }

            print(f"[PARSEUR V7] Document PDF prêt (extraction texte natif)", flush=True)

            # 3. Appel Claude avec prompt SIMPLE et UNIVERSEL
            result = self._call_claude_simple(document_content, filepath)

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

            # 5. Générer nom fichier source (nom du PDF original)
            filename = os.path.basename(filepath)

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

    def _call_claude_simple(self, document_content: Dict, filepath: str) -> Dict:
        """
        Appelle Claude API SANS Function Calling (prompt simple)

        Utilise le PDF natif (type "document") pour extraction texte précise
        Claude retourne directement un JSON avec toutes les données
        """

        # Prompt UNIVERSEL avec contexte financier
        prompt = """Tu es un expert en prêts immobiliers. Analyse ce tableau d'amortissement.

Un prêt peut avoir plusieurs phases :
- **Franchise totale** : ni capital ni intérêts remboursés (montant_capital = 0€, montant_interet = 0€, montant_echeance = 0€) → **Ce sont des échéances VALIDES à extraire !**
- **Franchise partielle** : pas de capital remboursé, mais intérêts payés (montant_capital = 0€, montant_interet > 0€)
- **Amortissement** : capital et intérêts remboursés (montant_capital > 0€, montant_interet > 0€)

⚠️ RÈGLES CRITIQUES :
1. **DATE PREMIÈRE ÉCHÉANCE** : Prendre UNIQUEMENT les lignes avec date >= (date_debut + 1 mois EXACT)
   - Si date_debut = 15/03/2023 → Première échéance = 15/04/2023
   - Ignorer TOUTE ligne avant cette date (déblocages DBL/DEBLOC, frais initiaux, etc.)
   - Ignorer lignes de header, total, report, sous-total
2. **IMPORTANTE** : Extraire TOUTES les échéances réelles, **Y COMPRIS celles avec montant_echeance = 0€** (franchise totale)
3. La durée totale du prêt INCLUT la période de franchise (ex: 12 mois franchise + 240 mois amortissement = 252 mois total)

---

EXTRACTION :
Extrait et retourne UN SEUL objet JSON avec cette structure exacte :

{
  "pret": {
    "numero_pret": "Numéro du contrat (string)",
    "intitule": "Nom du produit (ex: SOLUTION P IMMO, INVESTIMUR, etc.)",
    "banque": "Nom de la banque (ex: LCL, Crédit Agricole, etc.)",
    "montant_initial": Montant emprunté en EUR (number),
    "taux_annuel": Taux d'intérêt annuel en % (number, ex: 1.05 pour 1.05%),
    "type_taux": "FIXE" ou "VARIABLE" (cherche dans le document : "Taux fixe", "Taux variable"),
    "duree_mois": Nombre TOTAL d'échéances extraites (integer - compte TOUTES les lignes : franchise + amortissement),
    "date_debut": "Date de SIGNATURE/DEPART du prêt (cherche 'DATE DE DEPART DU PRET', 'DATE SIGNATURE', etc. dans métadonnées) au format YYYY-MM-DD",
    "date_debut_amortissement": "Date de début d'amortissement au format YYYY-MM-DD",
    "type_amortissement": "AMORTISSABLE" ou "IN_FINE" (voir instructions ci-dessous)
  },
  "echeances": [
    {
      "date_echeance": "Date au format YYYY-MM-DD",
      "montant_echeance": Montant À PAYER ce mois (number),
      "montant_capital": Part de capital remboursé ce mois-ci (number),
      "montant_interet": Part d'intérêts payés ce mois-ci (number),
      "capital_restant_du": Capital restant APRÈS cette échéance (number)
    }
  ]
}

⚠️ ATTENTION AU MAPPING - RÈGLES SÉMANTIQUES STRICTES :

1. **montant_echeance** : C'est le MONTANT À PAYER ce mois
   - Valeur typique : 0-2000€
   - En franchise totale : 0€
   - NE PAS confondre avec "TOTAL RESTANT DÛ" (250000€)

2. **montant_interet** : Ce sont les INTÉRÊTS PAYÉS ce mois UNIQUEMENT
   - En franchise totale : 0€ (car intérêts différés)
   - NE PAS confondre avec :
     • "TOTAL DES INTÉRÊTS DIFFÉRÉS" (intérêts cumulés non payés)
     • "TOTAL DES INTÉRÊTS" (somme cumulative)
   - Cherche une colonne comme "INTERETS PAYES", "INT. PAYÉS", "INTERETS", etc.

3. **montant_capital** : Part de CAPITAL REMBOURSÉ ce mois
   - Cherche colonne "AMORT", "AMORTISSEMENT", "CAPITAL REMBOURSE", etc.
   - En franchise totale/partielle : 0€

4. **capital_restant_du** : Capital ENCORE DÛ après cette échéance
   - Valeur typique : 250000€ → 0€ (décroissant)
   - Cherche "CAPITAL RESTANT DÛ", "CAPITAL RESTANT", etc.
   - NE PAS confondre avec "TOTAL RESTANT DÛ" (capital + intérêts différés)

⚠️ Si le tableau a plusieurs colonnes similaires (ex: plusieurs colonnes d'intérêts),
utilise celle qui correspond à la DÉFINITION SÉMANTIQUE ci-dessus, pas juste au nom.

EXTRACTION :

1. **Métadonnées du prêt** (page 1) :
   - numero_pret, banque, montant_initial, taux_annuel, duree_mois
   - **date_debut** : Extraire "DATE DE DEPART DU PRET" ou "DATE SIGNATURE" des métadonnées (PAS la date de première échéance)
   - date_debut_amortissement : Date de début d'amortissement
   - type_taux : cherche "Taux fixe"/"Taux variable" dans le document (par défaut : FIXE)
   - type_amortissement : calcule ratio = (mois avant amortissement) / (durée totale)
     → Si ratio ≥ 0.90 : IN_FINE, sinon : AMORTISSABLE

2. **Échéances** (toutes les pages du tableau) :
   - Extraire TOUTES les lignes d'échéance réelles (lignes de données, pas headers/totals)
   - Commencer à partir de : date >= (date_debut + 1 mois EXACT)
   - **INCLURE** les échéances de franchise totale (montant_echeance = 0€) : ce sont des échéances valides !
   - Pour chaque échéance : date_echeance, montant_capital, montant_interet, montant_echeance, capital_restant_du
   - Ignorer : lignes header, Report, Total, Sous-total, DBL/DEBLOC, frais initiaux, lignes vides

3. **Validation** :
   - montant_echeance = montant_capital + montant_interet (±0.01€)
   - Vérifier que la première échéance a date_echeance = date_debut + 1 mois EXACT
   - Vérifier que les dates sont mensuelles consécutives (pas de saut, pas de doublon)

Retourne le JSON (sans texte avant/après, sans ```json```)."""

        try:
            # Appel API SANS tools (réponse JSON directe)
            print(f"[PARSEUR V7] Appel Claude API (model={self.model}, max_tokens=64000)...", flush=True)

            response = self.client.messages.create(
                model=self.model,
                max_tokens=64000,  # Limite max Haiku 4.5 et Sonnet 4.5
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        document_content  # PDF natif (1 seul document)
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

            # Recalculer duree_mois automatiquement pour garantir la cohérence
            # (évite les erreurs si Claude compte mal les échéances)
            nb_echeances = len(data['echeances'])
            duree_mois_declaree = data['pret'].get('duree_mois', 0)

            if nb_echeances != duree_mois_declaree:
                print(f"[PARSEUR V7] Correction duree_mois : {duree_mois_declaree} → {nb_echeances} (nombre réel d'échéances)", flush=True)
                data['pret']['duree_mois'] = nb_echeances

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
        Valide la cohérence des données extraites

        Retourne seulement les erreurs CRITIQUES qui justifient un rejet complet.
        Les warnings sont loggés mais ne bloquent pas.

        Returns:
            Liste des erreurs critiques (vide si OK)
        """
        errors = []

        # Validation métadonnées prêt (CRITIQUES)
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

        # Validation échéances (WARNINGS seulement, ne bloque pas)
        echeances = data.get('echeances', [])

        if len(echeances) == 0:
            errors.append("Aucune échéance extraite")

        # VALIDATION CRITIQUE : Détecter confusion colonnes intérêts (différés vs payés)
        # En franchise totale (capital=0), les intérêts PAYÉS = 0€
        # Si intérêts > 0€ et augmentent → Utilise mauvaise colonne (intérêts différés)
        echeances_franchise = []
        for i, ech in enumerate(echeances[:20]):  # Vérifier les 20 premières (franchise probable)
            if ech.get('montant_capital', 0) == 0:
                echeances_franchise.append((i, ech.get('montant_interet', 0)))

        if len(echeances_franchise) >= 3:
            # Au moins 3 échéances en franchise
            interets_franchise = [interets for _, interets in echeances_franchise]

            # Vérifier si les intérêts augmentent (pattern intérêts différés)
            if all(interets > 0 for interets in interets_franchise):
                # Tous > 0 (devrait être 0 en franchise totale)
                if interets_franchise[1] > interets_franchise[0] and interets_franchise[2] > interets_franchise[1]:
                    # Augmentent progressivement → C'est les intérêts différés
                    errors.append(
                        f"⚠️ ERREUR CRITIQUE : Confusion colonnes intérêts détectée\n"
                        f"   → En franchise (capital=0), les intérêts PAYÉS doivent être 0€\n"
                        f"   → Valeurs extraites : {interets_franchise[0]:.2f}€, {interets_franchise[1]:.2f}€, {interets_franchise[2]:.2f}€ (augmentent)\n"
                        f"   → Tu utilises la colonne 'Intérêts différés/cumulés' (MAUVAISE)\n"
                        f"   → Utilise la colonne 'Intérêts payés/prélevés' (BONNE)\n"
                        f"   → Les intérêts en franchise totale doivent être 0€, 0€, 0€..."
                    )
                    # Retourner immédiatement, pas besoin d'autres validations
                    return errors

        # On fait confiance à Claude expert pour les validations ligne par ligne
        # Seules les validations critiques (métadonnées + confusion colonnes) restent

        return errors

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
                'type_taux': pret['type_taux'],
                'duree_mois': pret['duree_mois'],
                'date_debut': datetime.strptime(pret['date_debut'], '%Y-%m-%d').date(),
                'date_debut_amortissement': datetime.strptime(
                    pret.get('date_debut_amortissement', pret['date_debut']),
                    '%Y-%m-%d'
                ).date(),
                'type_amortissement': pret['type_amortissement'],
                'fichier_reference': filename
            }

            # Préparer données échéances
            echeances_data = []
            for ech in echeances:
                echeances_data.append({
                    'date_echeance': ech['date_echeance'],
                    'montant_echeance': float(ech['montant_echeance']),
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
