#!/usr/bin/env python3
"""
TRAITEMENT MANUEL DES PDFs - RELEVÉS BANCAIRES
==============================================

Script pour traiter manuellement les PDFs de relevés bancaires déjà présents
dans le repository GitHub (non reçus par email).

USAGE:
    # Traiter un PDF spécifique
    python traiter_pdf_manuel.py "Elements Comptables du 4T2024.pdf"

    # Traiter tous les PDFs "Elements Comptables" du répertoire
    python traiter_pdf_manuel.py --all

    # Mode dry-run (sans envoi email)
    python traiter_pdf_manuel.py "Elements Comptables du 4T2024.pdf" --dry-run

WORKFLOW:
1. Extraction événements du PDF via WorkflowEvenements
2. Génération propositions comptables
3. Stockage en BD avec token MD5
4. Envoi email validation à Ulrik

Date: 09/11/2025
Auteur: Claude Code (correction régression)
"""

import os
import sys
import argparse
from datetime import datetime
from typing import List, Dict, Optional

# Imports locaux
from workflow_evenements import WorkflowEvenements
from propositions_manager import PropositionsManager
from module2_workflow_v2 import EnvoyeurMarkdown
from models_module2 import get_session


class TraiteurPDFManuel:
    """Traite manuellement des PDFs de relevés bancaires"""

    def __init__(self, database_url: str, api_key: str, email_soeurise: str,
                 password_soeurise: str, email_ulrik: str):
        self.database_url = database_url
        self.api_key = api_key
        self.email_soeurise = email_soeurise
        self.password_soeurise = password_soeurise
        self.email_ulrik = email_ulrik

        # Composants
        self.session = get_session(database_url)
        self.propositions_manager = PropositionsManager(self.session)
        self.envoyeur = EnvoyeurMarkdown(email_soeurise, password_soeurise, email_ulrik)

    def __del__(self):
        """Ferme la session"""
        if hasattr(self, 'session'):
            self.session.close()

    def traiter_pdf(self, pdf_path: str, dry_run: bool = False) -> Dict:
        """
        Traite un PDF de relevé bancaire

        Args:
            pdf_path: Chemin absolu vers le PDF
            dry_run: Si True, ne génère pas de propositions (juste extraction)

        Returns:
            Dictionnaire avec résultats
        """
        print()
        print("=" * 80)
        print(f"TRAITEMENT MANUEL PDF: {os.path.basename(pdf_path)}")
        print("=" * 80)
        print()

        if not os.path.exists(pdf_path):
            return {
                'success': False,
                'error': f'Fichier non trouvé: {pdf_path}'
            }

        # Métadonnées simulées (pas d'email source)
        email_metadata = {
            'email_id': None,
            'email_from': 'manuel@traitement.local',
            'email_date': datetime.now().isoformat(),
            'email_subject': f'Traitement manuel: {os.path.basename(pdf_path)}',
            'email_body': f'PDF traité manuellement depuis le repository GitHub le {datetime.now().strftime("%d/%m/%Y %H:%M")}'
        }

        try:
            # ÉTAPE 1: Extraction événements via WorkflowEvenements
            print("📄 ÉTAPE 1/4: EXTRACTION DES ÉVÉNEMENTS")
            print("-" * 80)

            workflow = WorkflowEvenements(self.database_url, phase=1)
            result = workflow.traiter_pdf(pdf_path, email_metadata, auto_detect=True)

            if result.get('evenements_crees', 0) == 0:
                print()
                print(f"⚠️  Aucun événement créé")
                if result.get('message_erreur'):
                    print(f"    Raison: {result['message_erreur']}")
                return {
                    'success': False,
                    'error': result.get('message_erreur', 'Aucun événement créé'),
                    'extraction': result
                }

            print()
            print(f"✅ {result['evenements_crees']} événements créés")
            print(f"   IDs: {result.get('ids_crees', [])}")
            print()

            # ÉTAPE 2: Génération propositions
            if dry_run:
                print("🔍 MODE DRY-RUN - Arrêt avant génération propositions")
                return {
                    'success': True,
                    'dry_run': True,
                    'extraction': result
                }

            print("📝 ÉTAPE 2/4: GÉNÉRATION DES PROPOSITIONS")
            print("-" * 80)

            # Générer propositions pour les événements créés
            propositions = workflow.generer_propositions(evenement_ids=result.get('ids_crees', []))

            if not propositions:
                print()
                print("⚠️  Aucune proposition générée")
                return {
                    'success': False,
                    'error': 'Aucune proposition générée',
                    'extraction': result
                }

            print()
            print(f"✅ {len(propositions)} propositions générées")
            print()

            # ÉTAPE 3: Stockage en BD avec token
            print("💾 ÉTAPE 3/4: STOCKAGE DES PROPOSITIONS")
            print("-" * 80)

            # Convertir format propositions
            propositions_list = []
            for prop_data in propositions:
                proposition = prop_data['proposition']
                for ecriture in proposition.get('ecritures', []):
                    # Convertir date_ecriture en string si nécessaire
                    date_ecriture = ecriture.get('date_ecriture')
                    if date_ecriture and hasattr(date_ecriture, 'isoformat'):
                        date_ecriture = date_ecriture.isoformat()

                    propositions_list.append({
                        'numero_ecriture': f"EVT-{prop_data['evenement_id']}",
                        'type': proposition['type_evenement'],
                        'compte_debit': ecriture['compte_debit'],
                        'compte_credit': ecriture['compte_credit'],
                        'montant': ecriture['montant'],
                        'libelle': ecriture.get('libelle_ecriture', proposition['description']),
                        'date_ecriture': date_ecriture
                    })

            # Stocker avec token
            token_stocke, prop_id = self.propositions_manager.stocker_proposition(
                type_evenement='RELEVE_BANCAIRE',
                propositions=propositions_list,
                email_id=None,  # Pas d'email source
                email_from='manuel@traitement.local',
                email_date=datetime.now().isoformat(),
                email_subject=f'Traitement manuel: {os.path.basename(pdf_path)}'
            )

            print()
            print(f"✅ Propositions stockées avec token: {token_stocke}")
            print(f"   Proposition ID: {prop_id}")
            print()

            # ÉTAPE 4: Génération email validation
            print("📧 ÉTAPE 4/4: GÉNÉRATION EMAIL VALIDATION")
            print("-" * 80)

            # Générer Markdown récapitulatif
            markdown_recap = self._generer_markdown(
                propositions,
                token_stocke,
                os.path.basename(pdf_path),
                result
            )

            # Envoyer email
            email_envoye = self.envoyeur.envoyer_propositions(
                self.email_ulrik,
                'RELEVE_BANCAIRE',
                markdown_recap,
                token_stocke,
                subject_suffix=f"- {len(propositions)} proposition(s) - Traitement manuel"
            )

            if email_envoye:
                print()
                print(f"✅ Email de validation envoyé à {self.email_ulrik}")
                print()
            else:
                print()
                print(f"⚠️  Échec envoi email")
                print()

            return {
                'success': True,
                'extraction': result,
                'propositions': len(propositions),
                'token': token_stocke,
                'proposition_id': prop_id,
                'email_envoye': email_envoye
            }

        except Exception as e:
            print()
            print(f"❌ ERREUR: {e}")
            print()
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }

    def _generer_markdown(self, propositions: List[Dict], token: str,
                         pdf_name: str, extraction_result: Dict) -> str:
        """Génère le Markdown pour l'email de validation"""

        markdown = f"""# Propositions Comptables - Relevés Bancaires (Traitement Manuel)

**Date:** {datetime.now().strftime('%d/%m/%Y %H:%M')}
**PDF:** {pdf_name}
**Token:** `{token}`

## Résumé Extraction

- **{extraction_result.get('total_operations', 0)} opérations** extraites du PDF
- **{extraction_result.get('evenements_crees', 0)} événements** créés en base de données
- **{extraction_result.get('doublons_detectes', 0)} doublons** ignorés
- **{len(propositions)} propositions** générées

"""

        if extraction_result.get('periode_document'):
            markdown += f"- **Période:** {extraction_result['periode_document']}\n"

        markdown += "\n## Détails des Propositions\n\n"

        for i, prop_data in enumerate(propositions, 1):
            proposition = prop_data['proposition']
            markdown += f"### Proposition {i}: {proposition['type_evenement']}\n\n"
            markdown += f"**Événement ID**: #{prop_data['evenement_id']}\n"
            markdown += f"**Confiance**: {proposition['confiance']*100:.0f}%\n"
            markdown += f"**Description**: {proposition['description']}\n\n"
            markdown += "**Écritures proposées:**\n\n"

            for ecriture in proposition.get('ecritures', []):
                markdown += f"- Débit {ecriture['compte_debit']} / Crédit {ecriture['compte_credit']} : {ecriture['montant']:.2f}€\n"
                markdown += f"  - Libellé: {ecriture.get('libelle_ecriture', 'N/A')}\n"

            markdown += "\n"

        markdown += f"""
## Validation

Pour valider ces propositions, répondez à cet email avec le tag:

**[_Head] VALIDE: {token}**

---

_Head.Soeurise - Traitement manuel - {datetime.now().strftime('%d/%m/%Y %H:%M')}
"""

        return markdown


def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(
        description='Traite manuellement des PDFs de relevés bancaires'
    )
    parser.add_argument(
        'pdf_path',
        nargs='?',
        help='Chemin vers le PDF à traiter (ou --all pour tous les PDFs)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Traiter tous les PDFs "Elements Comptables" du répertoire'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Mode dry-run: extraction uniquement, sans propositions'
    )

    args = parser.parse_args()

    # Vérifier environnement
    required_env = ['DATABASE_URL', 'ANTHROPIC_API_KEY', 'SOEURISE_EMAIL',
                   'SOEURISE_PASSWORD', 'NOTIF_EMAIL']

    missing = [env for env in required_env if not os.environ.get(env)]
    if missing:
        print(f"❌ Variables d'environnement manquantes: {', '.join(missing)}")
        print("   Exécute ce script sur Render shell ou configure les variables localement")
        sys.exit(1)

    # Initialiser traiteur
    traiteur = TraiteurPDFManuel(
        os.environ['DATABASE_URL'],
        os.environ['ANTHROPIC_API_KEY'],
        os.environ['SOEURISE_EMAIL'],
        os.environ['SOEURISE_PASSWORD'],
        os.environ['NOTIF_EMAIL']
    )

    # Déterminer PDFs à traiter
    pdfs = []

    if args.all:
        # Traiter tous les PDFs "Elements Comptables"
        import glob
        pdfs = glob.glob("Elements Comptables*.pdf")
        if not pdfs:
            print("❌ Aucun PDF 'Elements Comptables*.pdf' trouvé dans le répertoire")
            sys.exit(1)

        print(f"📂 {len(pdfs)} PDF(s) trouvé(s):")
        for pdf in pdfs:
            print(f"   - {pdf}")
        print()

    elif args.pdf_path:
        # Traiter un PDF spécifique
        pdf_path = args.pdf_path
        if not os.path.isabs(pdf_path):
            pdf_path = os.path.abspath(pdf_path)
        pdfs = [pdf_path]

    else:
        parser.print_help()
        sys.exit(1)

    # Traiter chaque PDF
    resultats = []

    for pdf_path in pdfs:
        result = traiteur.traiter_pdf(pdf_path, dry_run=args.dry_run)
        resultats.append({
            'pdf': os.path.basename(pdf_path),
            'result': result
        })

    # Résumé final
    print()
    print("=" * 80)
    print("RÉSUMÉ DU TRAITEMENT")
    print("=" * 80)
    print()

    total_propositions = 0
    total_evenements = 0
    total_success = 0
    total_errors = 0

    for res in resultats:
        pdf_name = res['pdf']
        result = res['result']

        if result.get('success'):
            total_success += 1
            if not result.get('dry_run'):
                props = result.get('propositions', 0)
                evts = result.get('extraction', {}).get('evenements_crees', 0)
                total_propositions += props
                total_evenements += evts
                print(f"✅ {pdf_name}: {evts} événements, {props} propositions")
                print(f"   Token: {result.get('token', 'N/A')}")
            else:
                evts = result.get('extraction', {}).get('evenements_crees', 0)
                total_evenements += evts
                print(f"🔍 {pdf_name}: {evts} événements (dry-run)")
        else:
            total_errors += 1
            print(f"❌ {pdf_name}: {result.get('error', 'Erreur inconnue')}")

    print()
    print(f"Total: {total_success} succès, {total_errors} erreurs")
    if not args.dry_run:
        print(f"Événements créés: {total_evenements}")
        print(f"Propositions générées: {total_propositions}")
    else:
        print(f"Événements créés (dry-run): {total_evenements}")
    print()


if __name__ == '__main__':
    main()
