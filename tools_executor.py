"""
Exécuteur de tools pour Architecture V6 (Function Calling)

Claude appelle les tools, ce module les exécute
"""

import os
import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List
import subprocess

# ============================================================================
# TOOL EXECUTORS - GESTION DES PRÊTS
# ============================================================================

def execute_extract_all_echeances_to_file(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrait toutes les échéances et les sauvegarde dans un fichier MD

    Args:
        tool_input: {
            "numero_pret": "5009736BRM0911AH",
            "filename": "PRET_C_echeances.md",
            "echeances": [...]
        }

    Returns:
        {
            "success": True,
            "filename": "PRET_C_echeances.md",
            "nb_echeances": 252,
            "message": "252 échéances extraites et sauvegardées"
        }
    """
    try:
        numero_pret = tool_input['numero_pret']
        filename = tool_input['filename']
        echeances = tool_input['echeances']

        # Chemin absolu du fichier
        filepath = os.path.join(os.getcwd(), filename)

        # Construction du contenu MD
        lines = []
        for ech in echeances:
            line = f"{ech['date_echeance']}:{ech['montant_total']:.2f}:{ech['montant_capital']:.2f}:{ech['montant_interet']:.2f}:{ech['capital_restant_du']:.2f}"
            lines.append(line)

        content = "\n".join(lines)

        # Écriture du fichier
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# Échéances Prêt {numero_pret}\n\n")
            f.write(f"**Format**: date_echeance:montant_total:montant_capital:montant_interet:capital_restant_du\n\n")
            f.write(f"**Extraction**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            f.write(content)

        print(f"[TOOL] Fichier créé: {filename} avec {len(echeances)} échéances", flush=True)

        return {
            "success": True,
            "filename": filename,
            "nb_echeances": len(echeances),
            "message": f"{len(echeances)} échéances extraites et sauvegardées dans {filename}"
        }

    except Exception as e:
        print(f"[TOOL ERROR] extract_all_echeances_to_file: {str(e)}", flush=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Erreur lors de l'extraction: {str(e)}"
        }


def execute_insert_pret_from_file(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Insère un prêt et ses échéances en BD depuis un fichier MD

    Args:
        tool_input: {
            "filename": "PRET_C_echeances.md",
            "pret_params": {...}
        }

    Returns:
        {
            "success": True,
            "pret_id": 3,
            "nb_echeances": 252,
            "message": "Prêt inséré avec succès"
        }
    """
    try:
        from prets_manager import PretsManager
        from models_module2 import SessionLocal

        filename = tool_input['filename']
        pret_params = tool_input['pret_params']

        # Lecture du fichier MD
        filepath = os.path.join(os.getcwd(), filename)
        if not os.path.exists(filepath):
            return {
                "success": False,
                "error": f"Fichier {filename} introuvable",
                "message": f"Le fichier {filename} n'existe pas"
            }

        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Parse des échéances (format: date:montant_total:montant_capital:montant_interet:capital_restant_du)
        echeances_data = []
        for line in lines:
            line = line.strip()
            # Ignorer les lignes vides, headers MD, etc.
            if not line or line.startswith('#') or line.startswith('**') or line.startswith('---'):
                continue

            parts = line.split(':')
            if len(parts) == 5:
                try:
                    echeances_data.append({
                        'date_echeance': parts[0],
                        'montant_total': float(parts[1]),
                        'montant_capital': float(parts[2]),
                        'montant_interet': float(parts[3]),
                        'capital_restant_du': float(parts[4])
                    })
                except ValueError:
                    continue  # Ligne mal formée, on ignore

        print(f"[TOOL] Fichier {filename} parsé: {len(echeances_data)} échéances", flush=True)

        # Insertion en BD
        session = SessionLocal()
        try:
            manager = PretsManager(session)

            # Création de l'enregistrement prêt
            pret_data = {
                'numero_pret': pret_params['numero_pret'],
                'intitule': pret_params['intitule'],
                'banque': pret_params['banque'],
                'montant_initial': Decimal(str(pret_params['montant_initial'])),
                'taux_annuel': Decimal(str(pret_params['taux_annuel'])),
                'duree_mois': pret_params['duree_mois'],
                'date_debut': datetime.strptime(pret_params['date_debut'], '%Y-%m-%d').date(),
                'date_debut_amortissement': datetime.strptime(pret_params['date_debut_amortissement'], '%Y-%m-%d').date(),
                'type_pret': pret_params['type_pret'],
                'fichier_reference': filename
            }

            # Insérer prêt + échéances
            success, message, pret_id = manager.inserer_pret_et_echeances(
                pret_data,
                echeances_data
            )

            if success:
                session.commit()
                print(f"[TOOL] Prêt {pret_params['numero_pret']} inséré avec succès (ID: {pret_id})", flush=True)
                return {
                    "success": True,
                    "pret_id": pret_id,
                    "nb_echeances": len(echeances_data),
                    "message": f"Prêt {pret_params['numero_pret']} inséré avec {len(echeances_data)} échéances"
                }
            else:
                session.rollback()
                return {
                    "success": False,
                    "error": message,
                    "message": f"Erreur lors de l'insertion: {message}"
                }

        finally:
            session.close()

    except Exception as e:
        print(f"[TOOL ERROR] insert_pret_from_file: {str(e)}", flush=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Erreur lors de l'insertion: {str(e)}"
        }


def execute_query_pret_echeance(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Récupère une échéance de prêt pour une date donnée

    Args:
        tool_input: {
            "numero_pret": "5009736BRM0911AH",
            "date_echeance": "2024-05-15"
        }

    Returns:
        {
            "success": True,
            "echeance": {
                "date_echeance": "2024-05-15",
                "montant_total": 1166.59,
                "montant_capital": 955.68,
                "montant_interet": 210.91,
                "capital_restant_du": 240079.37
            }
        }
    """
    try:
        from prets_manager import PretsManager
        from models_module2 import SessionLocal

        numero_pret = tool_input['numero_pret']
        date_echeance = tool_input['date_echeance']

        session = SessionLocal()
        try:
            manager = PretsManager(session)

            # Récupérer l'échéance
            echeance = manager.get_echeance(numero_pret, date_echeance)

            if echeance:
                return {
                    "success": True,
                    "echeance": {
                        "date_echeance": echeance.date_echeance.strftime('%Y-%m-%d'),
                        "montant_total": float(echeance.montant_total),
                        "montant_capital": float(echeance.montant_capital),
                        "montant_interet": float(echeance.montant_interet),
                        "capital_restant_du": float(echeance.capital_restant_du)
                    }
                }
            else:
                return {
                    "success": False,
                    "error": "Échéance introuvable",
                    "message": f"Aucune échéance trouvée pour le prêt {numero_pret} à la date {date_echeance}"
                }

        finally:
            session.close()

    except Exception as e:
        print(f"[TOOL ERROR] query_pret_echeance: {str(e)}", flush=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Erreur lors de la consultation: {str(e)}"
        }


# ============================================================================
# TOOL EXECUTORS - COMPTABILITÉ
# ============================================================================

def execute_create_ecriture_comptable(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crée une écriture comptable en partie double

    Args:
        tool_input: {
            "date": "2024-05-15",
            "libelle": "Échéance prêt LCL - mai 2024",
            "lignes": [
                {"compte": "164100", "debit": 955.68, "credit": 0},
                {"compte": "661000", "debit": 210.91, "credit": 0},
                {"compte": "512000", "debit": 0, "credit": 1166.59}
            ]
        }

    Returns:
        {
            "success": True,
            "ecriture_id": 42,
            "message": "Écriture créée avec succès"
        }
    """
    try:
        from models_module2 import SessionLocal, EcritureComptable, LigneEcriture

        date_ecriture = datetime.strptime(tool_input['date'], '%Y-%m-%d').date()
        libelle = tool_input['libelle']
        lignes = tool_input['lignes']

        # Validation partie double
        total_debit = sum(Decimal(str(ligne.get('debit', 0))) for ligne in lignes)
        total_credit = sum(Decimal(str(ligne.get('credit', 0))) for ligne in lignes)

        if abs(total_debit - total_credit) > Decimal('0.01'):
            return {
                "success": False,
                "error": "Partie double non équilibrée",
                "message": f"Total débit ({total_debit}) ≠ Total crédit ({total_credit})"
            }

        session = SessionLocal()
        try:
            # Créer l'écriture
            ecriture = EcritureComptable(
                date=date_ecriture,
                libelle=libelle
            )
            session.add(ecriture)
            session.flush()  # Pour obtenir l'ID

            # Créer les lignes
            for ligne_data in lignes:
                ligne = LigneEcriture(
                    ecriture_id=ecriture.id,
                    compte=ligne_data['compte'],
                    debit=Decimal(str(ligne_data.get('debit', 0))),
                    credit=Decimal(str(ligne_data.get('credit', 0)))
                )
                session.add(ligne)

            session.commit()

            print(f"[TOOL] Écriture comptable créée (ID: {ecriture.id}): {libelle}", flush=True)

            return {
                "success": True,
                "ecriture_id": ecriture.id,
                "message": f"Écriture comptable créée avec succès (ID: {ecriture.id})"
            }

        except Exception as e:
            session.rollback()
            raise e

        finally:
            session.close()

    except Exception as e:
        print(f"[TOOL ERROR] create_ecriture_comptable: {str(e)}", flush=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Erreur lors de la création de l'écriture: {str(e)}"
        }


# ============================================================================
# TOOL EXECUTORS - MÉMOIRES
# ============================================================================

def execute_update_memoire(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Met à jour une mémoire (courte/moyenne/longue)

    Args:
        tool_input: {
            "type_memoire": "courte",
            "content": "# Mémoire Courte\\n\\n...",
            "commit_message": "🧠 Réveil 01/11/2025"
        }

    Returns:
        {
            "success": True,
            "message": "Mémoire courte mise à jour"
        }
    """
    try:
        type_memoire = tool_input['type_memoire']
        content = tool_input['content']
        commit_message = tool_input['commit_message']

        # Mapping des types de mémoire
        filenames = {
            'courte': 'memoire_courte.md',
            'moyenne': 'memoire_moyenne.md',
            'longue': 'memoire_longue.md'
        }

        if type_memoire not in filenames:
            return {
                "success": False,
                "error": f"Type de mémoire inconnu: {type_memoire}",
                "message": "Type de mémoire doit être: courte, moyenne ou longue"
            }

        filename = filenames[type_memoire]
        filepath = os.path.join(os.getcwd(), filename)

        # Écriture du fichier
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        # Commit Git
        try:
            subprocess.run(['git', 'add', filename], check=True, cwd=os.getcwd())
            subprocess.run(['git', 'commit', '-m', commit_message], check=True, cwd=os.getcwd())
            subprocess.run(['git', 'push'], check=True, cwd=os.getcwd())

            print(f"[TOOL] Mémoire {type_memoire} mise à jour et commitée", flush=True)

            return {
                "success": True,
                "message": f"Mémoire {type_memoire} mise à jour avec succès"
            }

        except subprocess.CalledProcessError as e:
            return {
                "success": False,
                "error": f"Erreur Git: {str(e)}",
                "message": f"Fichier mis à jour localement mais erreur lors du commit Git"
            }

    except Exception as e:
        print(f"[TOOL ERROR] update_memoire: {str(e)}", flush=True)
        return {
            "success": False,
            "error": str(e),
            "message": f"Erreur lors de la mise à jour de la mémoire: {str(e)}"
        }


# ============================================================================
# DISPATCHER PRINCIPAL
# ============================================================================

TOOL_EXECUTORS = {
    "extract_all_echeances_to_file": execute_extract_all_echeances_to_file,
    "insert_pret_from_file": execute_insert_pret_from_file,
    "query_pret_echeance": execute_query_pret_echeance,
    "create_ecriture_comptable": execute_create_ecriture_comptable,
    "update_memoire": execute_update_memoire
}


def execute_tool(tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dispatcher principal qui route les appels de tools vers les bonnes fonctions

    Args:
        tool_name: Nom du tool à exécuter
        tool_input: Paramètres du tool

    Returns:
        Résultat de l'exécution du tool
    """
    print(f"\n[TOOL CALL] {tool_name}", flush=True)
    print(f"[TOOL INPUT] {json.dumps(tool_input, indent=2, default=str)}", flush=True)

    if tool_name not in TOOL_EXECUTORS:
        error_msg = f"Tool inconnu: {tool_name}"
        print(f"[TOOL ERROR] {error_msg}", flush=True)
        return {
            "success": False,
            "error": error_msg,
            "message": f"Le tool '{tool_name}' n'existe pas"
        }

    try:
        # Exécuter le tool
        result = TOOL_EXECUTORS[tool_name](tool_input)

        print(f"[TOOL RESULT] {json.dumps(result, indent=2, default=str)}", flush=True)

        return result

    except Exception as e:
        error_msg = f"Erreur lors de l'exécution du tool {tool_name}: {str(e)}"
        print(f"[TOOL ERROR] {error_msg}", flush=True)
        import traceback
        traceback.print_exc()

        return {
            "success": False,
            "error": str(e),
            "message": error_msg
        }
