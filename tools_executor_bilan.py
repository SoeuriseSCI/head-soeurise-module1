"""
Exécuteur de tools pour extraction bilans comptables
"""

from typing import Dict, Any

def execute_extract_bilan_comptes(tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Extrait les comptes du bilan et les valide"""
    try:
        exercice = tool_input['exercice']
        date_bilan = tool_input['date_bilan']
        comptes = tool_input['comptes']

        if not comptes or len(comptes) == 0:
            return {"success": False, "error": "Aucun compte extrait"}

        # Calcul totaux ACTIF et PASSIF
        total_actif = sum(c['solde'] for c in comptes if c['type_bilan'] == 'ACTIF')
        total_passif = sum(c['solde'] for c in comptes if c['type_bilan'] == 'PASSIF')

        total_actif = round(total_actif, 2)
        total_passif = round(total_passif, 2)

        equilibre = abs(total_actif - total_passif) <= 1.0

        return {
            "success": True,
            "exercice": exercice,
            "date_bilan": date_bilan,
            "nb_comptes": len(comptes),
            "total_actif": total_actif,
            "total_passif": total_passif,
            "equilibre": equilibre,
            "comptes": comptes,
            "message": f"{len(comptes)} comptes extraits, équilibre: {'✓' if equilibre else '✗'}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def execute_tool_bilan(tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    """Route vers le bon executor"""
    if tool_name == "extract_bilan_comptes":
        return execute_extract_bilan_comptes(tool_input)
    else:
        return {"success": False, "error": f"Tool inconnu: {tool_name}"}
