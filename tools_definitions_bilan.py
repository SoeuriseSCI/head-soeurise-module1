"""
Définitions des tools (Function Calling) pour extraction de bilans comptables
"""

TOOL_EXTRACT_BILAN_COMPTES = {
    "name": "extract_bilan_comptes",
    "description": """Extrait TOUS les comptes d'un bilan comptable avec leur solde net.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "exercice": {"type": "string", "description": "Année de l'exercice comptable (ex: '2023')"},
            "date_bilan": {"type": "string", "description": "Date du bilan au format YYYY-MM-DD (ex: '2023-12-31')"},
            "comptes": {
                "type": "array",
                "description": "Liste de TOUS les comptes du bilan (ACTIF + PASSIF)",
                "items": {
                    "type": "object",
                    "properties": {
                        "numero": {"type": "string", "description": "Numéro de compte (ex: '280', '101', '512')"},
                        "libelle": {"type": "string", "description": "Libellé complet du compte"},
                        "solde": {"type": "number", "description": "Montant NET (peut être négatif)"},
                        "type_bilan": {"type": "string", "enum": ["ACTIF", "PASSIF"], "description": "Position dans le bilan"}
                    },
                    "required": ["numero", "libelle", "solde", "type_bilan"]
                }
            }
        },
        "required": ["exercice", "date_bilan", "comptes"]
    }
}

ALL_TOOLS_BILAN = [TOOL_EXTRACT_BILAN_COMPTES]
