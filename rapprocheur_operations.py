#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAPPROCHEUR D'OPÉRATIONS - Déduplication Intelligente par Claude API
=====================================================================

Date: 13/11/2025
Auteur: Module Phase 1 - Accounting Events Enhancement

OBJECTIF:
---------
Rapprocher intelligemment les opérations extraites (relevés + factures + bulletins + avis)
pour identifier les doublons et choisir la meilleure source pour chaque opération économique.

STRATÉGIE:
----------
1. Grouper opérations par montant (±0.01€)
2. Pour chaque groupe, demander à Claude API d'identifier:
   - Quelles opérations sont liées (même événement économique)
   - Quelle source utiliser pour l'écriture comptable
   - Quelles sources garder comme justificatifs
3. Retourner opérations dédupliquées + références justificatifs

PATTERNS DE RAPPROCHEMENT:
--------------------------
A. Factures → Prélèvements SEPA (dates ±30j, n° facture dans libellé)
B. Bulletins SCPI → Virements (dates ±7j, trimestre/période identique)
C. Avis opération → Débit/Crédit relevé (date exacte, détails ISIN/quantité)
D. Doublons exacts (même date, même montant, même libellé)

WORKFLOW:
---------
extraire_evenements() → rapprocher_operations() → créer_evenements_dedupliques()
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from anthropic import Anthropic

# Configuration
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')


class RapprocheurOperations:
    """
    Rapprochement intelligent d'opérations bancaires/comptables
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialise le rapprocheur

        Args:
            api_key: Clé API Anthropic (si None, utilise ANTHROPIC_API_KEY env var)
        """
        self.api_key = api_key or ANTHROPIC_API_KEY
        self.client = Anthropic(api_key=self.api_key) if self.api_key else None

    def rapprocher(self, operations: List[Dict]) -> Tuple[List[Dict], Dict]:
        """
        Rapproche les opérations et élimine les doublons

        Args:
            operations: Liste des opérations extraites (sans filtrage)

        Returns:
            Tuple (operations_dedupliquees, metadata)
            - operations_dedupliquees: Liste des opérations à utiliser pour écritures
            - metadata: Statistiques de rapprochement
        """
        print(f"\n{'='*80}")
        print("RAPPROCHEMENT INTELLIGENT DES OPÉRATIONS")
        print(f"{'='*80}\n")
        print(f"📊 Opérations à analyser: {len(operations)}")

        # Étape 1: Grouper par montant
        groupes_montant = self._grouper_par_montant(operations)
        print(f"📦 Groupes de montants identiques: {len(groupes_montant)}")

        # Identifier groupes avec potentiels doublons
        groupes_suspects = {
            montant: ops for montant, ops in groupes_montant.items()
            if len(ops) > 1
        }
        print(f"🔍 Groupes suspects (≥2 opérations): {len(groupes_suspects)}")

        # Étape 2: Rapprocher chaque groupe suspect via Claude API
        operations_finales = []
        justificatifs_map = {}  # {id_operation: [ids_justificatifs]}
        stats = {
            'total_operations': len(operations),
            'groupes_analyses': 0,
            'doublons_detectes': 0,
            'operations_finales': 0
        }

        # Opérations seules (pas de doublon potentiel)
        for montant, ops in groupes_montant.items():
            if len(ops) == 1:
                operations_finales.append(ops[0])

        # Groupes à analyser
        for idx, (montant, ops) in enumerate(groupes_suspects.items(), 1):
            print(f"\n--- Groupe {idx}/{len(groupes_suspects)}: {montant}€ ({len(ops)} opérations) ---")

            rapprochement = self._rapprocher_groupe(ops, idx)

            if rapprochement:
                # Ajouter opération principale
                operations_finales.append(rapprochement['operation_principale'])

                # Stocker justificatifs
                if rapprochement['justificatifs']:
                    op_id = id(rapprochement['operation_principale'])
                    justificatifs_map[op_id] = rapprochement['justificatifs']

                stats['groupes_analyses'] += 1
                stats['doublons_detectes'] += len(rapprochement['justificatifs'])

                print(f"   ✅ Source choisie: {rapprochement['operation_principale']['libelle'][:60]}...")
                print(f"   📎 Justificatifs: {len(rapprochement['justificatifs'])}")
            else:
                # Pas de rapprochement trouvé, garder toutes les opérations
                operations_finales.extend(ops)
                print(f"   ℹ️  Pas de rapprochement détecté, garde toutes les opérations")

        stats['operations_finales'] = len(operations_finales)

        print(f"\n{'='*80}")
        print("RÉSUMÉ DU RAPPROCHEMENT")
        print(f"{'='*80}")
        print(f"Opérations initiales    : {stats['total_operations']}")
        print(f"Groupes analysés        : {stats['groupes_analyses']}")
        print(f"Doublons détectés       : {stats['doublons_detectes']}")
        print(f"Opérations finales      : {stats['operations_finales']}")
        print(f"Réduction               : -{stats['doublons_detectes']} opérations\n")

        metadata = {
            'stats': stats,
            'justificatifs': justificatifs_map
        }

        return operations_finales, metadata

    def _grouper_par_montant(self, operations: List[Dict]) -> Dict[float, List[Dict]]:
        """
        Groupe les opérations par montant (arrondi à 0.01€)

        Args:
            operations: Liste des opérations

        Returns:
            Dict {montant: [operations]}
        """
        groupes = defaultdict(list)

        for op in operations:
            montant = float(op.get('montant', 0))
            # Arrondir à 0.01€ pour gérer les différences d'arrondi
            montant_arrondi = round(montant, 2)
            groupes[montant_arrondi].append(op)

        return dict(groupes)

    def _rapprocher_groupe(self, operations: List[Dict], groupe_num: int) -> Optional[Dict]:
        """
        Rapproche un groupe d'opérations avec même montant via Claude API

        Args:
            operations: Liste d'opérations avec même montant
            groupe_num: Numéro du groupe (pour traçabilité)

        Returns:
            Dict {
                'operation_principale': Dict,
                'justificatifs': List[Dict],
                'raison': str
            } ou None si pas de rapprochement
        """
        if not self.client:
            print("   ⚠️  ANTHROPIC_API_KEY non définie - pas de rapprochement")
            return None

        # Préparer les données pour Claude
        operations_json = []
        for idx, op in enumerate(operations):
            operations_json.append({
                'index': idx,
                'date': op.get('date_operation', ''),
                'libelle': op.get('libelle', '')[:200],  # Limiter pour token usage
                'montant': op.get('montant', 0),
                'type': op.get('type_operation', '')
            })

        prompt = self._construire_prompt_rapprochement(operations_json, groupe_num)

        try:
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            response_text = response.content[0].text.strip()

            # Parser la réponse JSON
            try:
                # Trouver le JSON dans la réponse
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_text = response_text[start_idx:end_idx]
                    resultat = json.loads(json_text)

                    # Valider le résultat
                    if 'operation_principale_index' in resultat:
                        idx_principal = resultat['operation_principale_index']
                        indices_justificatifs = resultat.get('justificatifs_indices', [])

                        return {
                            'operation_principale': operations[idx_principal],
                            'justificatifs': [operations[i] for i in indices_justificatifs if i < len(operations)],
                            'raison': resultat.get('raison', '')
                        }
                else:
                    print(f"   ⚠️  Pas de JSON trouvé dans la réponse")
                    return None

            except json.JSONDecodeError as e:
                print(f"   ⚠️  Erreur parsing JSON: {e}")
                print(f"   Réponse: {response_text[:200]}...")
                return None

        except Exception as e:
            print(f"   ⚠️  Erreur API Claude: {e}")
            return None

    def _construire_prompt_rapprochement(self, operations: List[Dict], groupe_num: int) -> str:
        """
        Construit le prompt pour Claude API

        Args:
            operations: Liste d'opérations formatées
            groupe_num: Numéro du groupe

        Returns:
            Prompt texte
        """
        operations_str = json.dumps(operations, indent=2, ensure_ascii=False)

        prompt = f"""Tu es un expert comptable spécialisé dans le rapprochement bancaire.

CONTEXTE:
Lors de l'extraction de documents comptables (relevés bancaires, factures, avis d'opération, bulletins),
une MÊME opération économique peut apparaître dans PLUSIEURS documents :
- Une facture annonce un futur paiement
- Le prélèvement SEPA correspondant apparaît dans le relevé bancaire
- Un bulletin SCPI annonce un versement futur
- Le virement effectif apparaît dans le relevé

Ces documents sont COMPLÉMENTAIRES (pas des erreurs) mais on ne doit créer qu'UNE SEULE écriture comptable.

GROUPE #{groupe_num} À ANALYSER:
Voici {len(operations)} opérations avec le MÊME montant :

{operations_str}

TA MISSION:
1. Détermine si ces opérations sont liées (même événement économique) ou indépendantes
2. Si liées, identifie :
   - L'opération à utiliser pour l'écriture comptable (la plus complète/précise)
   - Les autres comme justificatifs (preuves à conserver)

CRITÈRES DE RAPPROCHEMENT:
A. **Factures → Prélèvements SEPA**
   - Même montant (évident ici)
   - Dates ±30 jours
   - N° facture présent dans libellé du prélèvement
   → Utiliser: SEPA (opération bancaire réelle)
   → Justificatif: Facture (détails HT/TVA)

B. **Bulletins SCPI → Virements**
   - Même montant
   - Dates ±7 jours
   - Même trimestre/période mentionné
   → Utiliser: Virement SEPA (opération réelle)
   → Justificatif: Bulletin (annonce)

C. **Avis opération → Débit/Crédit relevé**
   - Même montant
   - Date identique ou très proche
   - Référence/n° opération
   → Utiliser: Avis (détails ISIN, quantité, prix, commissions)
   → Justificatif: Relevé (confirmation bancaire)

D. **Doublons exacts** (même document en 2 formats)
   - Même montant
   - Même date
   - Même libellé
   → Utiliser: Relevé bancaire
   → Supprimer: Avis d'écriture (doublon)

E. **Opérations indépendantes**
   - Si aucun critère ne matche
   → Garder TOUTES les opérations séparément

FORMAT DE RÉPONSE (JSON UNIQUEMENT):
{{
  "sont_liees": true/false,
  "operation_principale_index": 0,
  "justificatifs_indices": [1, 2],
  "raison": "Facture CRP 2C du 02/01 et SEPA du 24/01 avec n° facture 2024013227 dans libellé → même opération, utilise SEPA car opération bancaire réelle"
}}

Si opérations NON liées:
{{
  "sont_liees": false,
  "raison": "Pas de lien détecté - dates trop éloignées, pas de référence commune"
}}

IMPORTANT:
- Sois conservateur : en cas de doute, considère les opérations comme indépendantes
- La "raison" doit expliquer clairement ton choix
- Retourne UNIQUEMENT le JSON, pas de texte avant/après
"""

        return prompt


def test_rapprocheur():
    """
    Test du rapprocheur avec données fictives
    """
    print("TEST DU RAPPROCHEUR D'OPÉRATIONS\n")

    # Données de test
    operations_test = [
        # Groupe 1: Facture + SEPA (doublons)
        {
            'date_operation': '2024-01-02',
            'libelle': 'Facture CRP 2C n°2024013227 - Comptabilité',
            'montant': 213.60,
            'type_operation': 'DEBIT'
        },
        {
            'date_operation': '2024-01-24',
            'libelle': 'PRLV SEPA CRP Comptabilit Conseil LIBELLE:2024013227',
            'montant': 213.60,
            'type_operation': 'DEBIT'
        },
        # Groupe 2: Bulletin SCPI + Virement (doublons)
        {
            'date_operation': '2024-01-25',
            'libelle': 'BULLETIN SCPI REVENUS T4 2023 - 7356.24€',
            'montant': 7356.24,
            'type_operation': 'CREDIT'
        },
        {
            'date_operation': '2024-01-29',
            'libelle': 'VIR SEPA SCPI EPARGNE PIERRE DISTRIBUTION 4EME TRIM 2023',
            'montant': 7356.24,
            'type_operation': 'CREDIT'
        },
        # Opération unique
        {
            'date_operation': '2024-02-15',
            'libelle': 'PRET IMMOBILIER ECH 15/02/24',
            'montant': 258.33,
            'type_operation': 'DEBIT'
        }
    ]

    rapprocheur = RapprocheurOperations()
    operations_finales, metadata = rapprocheur.rapprocher(operations_test)

    print(f"\nRÉSULTATS:")
    print(f"Operations finales: {len(operations_finales)}")
    print(f"Metadata: {json.dumps(metadata['stats'], indent=2)}")


if __name__ == '__main__':
    test_rapprocheur()
