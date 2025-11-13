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

        nb_operations_initiales = len(operations)
        print(f"📊 Opérations à analyser: {nb_operations_initiales}")

        # Étape 0: Filtrer les lignes de détail de factures (HT, TVA, etc.)
        operations = self._filtrer_details_factures(operations)
        details_filtres = nb_operations_initiales - len(operations)
        if details_filtres > 0:
            print(f"🧹 Lignes de détail factures filtrées: {details_filtres}")
            print(f"📊 Opérations après filtrage: {len(operations)}")

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
                # Traiter les sous-groupes identifiés
                sous_groupes = rapprochement.get('sous_groupes', [])
                ops_independantes = rapprochement.get('operations_independantes', [])

                if sous_groupes:
                    stats['groupes_analyses'] += 1
                    print(f"   ✅ {len(sous_groupes)} sous-groupe(s) détecté(s)")

                    for sg in sous_groupes:
                        # Ajouter opération principale
                        operations_finales.append(sg['operation_principale'])

                        # Stocker justificatifs
                        if sg['justificatifs']:
                            op_id = id(sg['operation_principale'])
                            justificatifs_map[op_id] = sg['justificatifs']
                            stats['doublons_detectes'] += len(sg['justificatifs'])

                        print(f"      → Principale: {sg['operation_principale']['libelle'][:50]}...")
                        print(f"        Justifs: {len(sg['justificatifs'])}")

                # Ajouter opérations indépendantes
                if ops_independantes:
                    operations_finales.extend(ops_independantes)
                    if len(ops_independantes) > 0:
                        print(f"   ℹ️  {len(ops_independantes)} opération(s) indépendante(s)")
            else:
                # Erreur API ou pas de réponse valide, garder toutes les opérations
                operations_finales.extend(ops)
                print(f"   ⚠️  Erreur rapprochement, garde toutes les opérations")

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

    def _filtrer_details_factures(self, operations: List[Dict]) -> List[Dict]:
        """
        Filtre les lignes de détail de factures (HT, TVA, Honoraires, Provision)
        et garde uniquement les lignes Total TTC.

        Contexte SCI Soeurise:
        - SCI non soumise à TVA
        - Détails HT/TVA inutiles pour comptabilité
        - Seul le montant TTC compte

        Args:
            operations: Liste des opérations

        Returns:
            Liste filtrée (sans les lignes de détail)
        """
        import re
        from collections import defaultdict

        # Grouper les opérations par (date, numéro de facture)
        groupes_factures = defaultdict(list)
        operations_non_factures = []

        for op in operations:
            libelle = op.get('libelle', '')
            date = op.get('date_operation', '')

            # Chercher numéro de facture dans le libellé
            match = re.search(r'(?:Facture|facture|FACTURE)\s*n[°o]?\s*(\d+)', libelle)

            if match:
                numero_facture = match.group(1)
                cle = (date, numero_facture)
                groupes_factures[cle].append(op)
            else:
                # Pas une facture, garder telle quelle
                operations_non_factures.append(op)

        # Pour chaque groupe de facture, garder uniquement le Total TTC
        operations_filtrees = operations_non_factures.copy()

        for (date, num_facture), ops_facture in groupes_factures.items():
            # Chercher la ligne Total TTC
            ligne_ttc = None
            lignes_details = []

            for op in ops_facture:
                libelle = op.get('libelle', '').upper()

                # Ligne Total TTC : contient "TOTAL TTC" ou "RÉGULÉE" ou montant le plus élevé
                if any(keyword in libelle for keyword in ['TOTAL TTC', 'RÉGULÉE', 'REGULEE']):
                    ligne_ttc = op
                else:
                    # Ligne de détail (Provision, Honoraires, TVA, etc.)
                    lignes_details.append(op)

            # Si pas de ligne TTC explicite, prendre celle avec le montant le plus élevé
            if not ligne_ttc and ops_facture:
                ligne_ttc = max(ops_facture, key=lambda x: float(x.get('montant', 0)))
                lignes_details = [op for op in ops_facture if op != ligne_ttc]

            # Ajouter uniquement la ligne TTC
            if ligne_ttc:
                operations_filtrees.append(ligne_ttc)

        return operations_filtrees

    def _rapprocher_groupe(self, operations: List[Dict], groupe_num: int) -> Optional[Dict]:
        """
        Rapproche un groupe d'opérations avec même montant via Claude API

        Gère PLUSIEURS paires distinctes dans le même groupe (ex: 4 factures + 4 SEPA)

        Args:
            operations: Liste d'opérations avec même montant
            groupe_num: Numéro du groupe (pour traçabilité)

        Returns:
            Dict {
                'sous_groupes': List[{
                    'operation_principale': Dict,
                    'justificatifs': List[Dict],
                    'raison': str
                }],
                'operations_independantes': List[Dict]
            } ou None si erreur
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

                    # Nouveau format avec sous-groupes multiples
                    sous_groupes_data = []
                    for sg in resultat.get('sous_groupes', []):
                        idx_principal = sg.get('operation_principale_index')
                        indices_justifs = sg.get('justificatifs_indices', [])

                        # Valider les indices
                        if idx_principal is not None and idx_principal < len(operations):
                            sous_groupes_data.append({
                                'operation_principale': operations[idx_principal],
                                'justificatifs': [operations[i] for i in indices_justifs if i < len(operations)],
                                'raison': sg.get('raison', '')
                            })

                    # Opérations indépendantes
                    indices_independants = resultat.get('operations_independantes_indices', [])
                    operations_independantes = [operations[i] for i in indices_independants if i < len(operations)]

                    return {
                        'sous_groupes': sous_groupes_data,
                        'operations_independantes': operations_independantes
                    }
                else:
                    print(f"   ⚠️  Pas de JSON trouvé dans la réponse")
                    return None

            except json.JSONDecodeError as e:
                print(f"   ⚠️  Erreur parsing JSON: {e}")
                print(f"   Réponse: {response_text[:200]}...")
                return None
            except (IndexError, KeyError) as e:
                print(f"   ⚠️  Erreur indices: {e}")
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
Identifie TOUS les sous-groupes d'opérations liées dans cet ensemble.
**ATTENTION** : Il peut y avoir PLUSIEURS paires distinctes dans le même groupe !

Exemple : 4 factures CRP 2C de 213.60€ à différentes dates + 4 SEPA correspondants
= 4 PAIRES distinctes à identifier (pas un seul groupe)

Pour chaque paire/sous-groupe lié :
1. Identifie l'opération principale (à utiliser pour l'écriture comptable)
2. Identifie les justificatifs (documents liés à conserver)
3. Explique le lien

CRITÈRES DE RAPPROCHEMENT:

A. **Factures → Prélèvements SEPA**
   - Même montant (évident ici)
   - Dates facture et SEPA ±30 jours
   - N° facture présent dans libellé SEPA (ex: "LIBELLE:2024013227")
   - MÊME client/fournisseur (ex: "CRP Comptabilit Conseil")
   → Utiliser: SEPA (opération bancaire réelle)
   → Justificatif: Facture (détails HT/TVA)

   EXEMPLE CONCRET:
   - Index 0: date "2024-01-02", libellé "Facture n° 2024013227..."
   - Index 1: date "2024-01-24", libellé "PRLV SEPA CRP... LIBELLE:2024013227"
   → Paire liée : principal=1, justifs=[0]

B. **Bulletins SCPI → Virements**
   - Même montant
   - Dates bulletin et virement ±15 jours
   - Même trimestre/période mentionné (ex: "4EME TRIM 2023", "1ER TRIM 2024")
   - MÊME SCPI (ex: "SCPI EPARGNE PIERRE")
   → Utiliser: Virement SEPA (opération réelle)
   → Justificatif: Bulletin (annonce)

C. **Avis opération → Débit/Crédit relevé**
   - Même montant
   - Date identique ou ±2 jours
   - Référence/ISIN présent (ex: "AMAZON COM", "AMUNDI MSCI")
   → Utiliser: Avis (détails ISIN, quantité, prix, commissions)
   → Justificatif: Relevé (confirmation bancaire)

D. **Doublons exacts** (même document extrait 2 fois)
   - Même montant
   - Même date exacte
   - Libellé très similaire (>80% identique)
   → Utiliser: Version relevé bancaire
   → Supprimer: Doublon

E. **Opérations indépendantes**
   - Si aucun critère ne matche
   - Dates trop éloignées
   - Pas de référence commune
   → Garder séparément

FORMAT DE RÉPONSE (JSON UNIQUEMENT):
{{
  "sous_groupes": [
    {{
      "operation_principale_index": 1,
      "justificatifs_indices": [0],
      "raison": "Facture CRP 2C du 02/01 (n°2024013227) et SEPA du 24/01 avec même n° → même opération"
    }},
    {{
      "operation_principale_index": 3,
      "justificatifs_indices": [2],
      "raison": "Facture CRP 2C du 04/01 (n°2024043519) et SEPA du 24/04 avec même n° → même opération"
    }}
  ],
  "operations_independantes_indices": [4, 5]
}}

Si AUCUNE opération liée:
{{
  "sous_groupes": [],
  "operations_independantes_indices": [0, 1, 2, 3, 4]
}}

IMPORTANT:
- Cherche TOUTES les paires possibles, pas juste la première
- Sois conservateur : en cas de doute, considère les opérations comme indépendantes
- Retourne UNIQUEMENT le JSON, pas de texte avant/après
- Les indices doivent référencer le tableau "operations" ci-dessus
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
