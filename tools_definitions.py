"""
Définitions des tools (Function Calling) pour Claude API

Architecture V6 : Claude appelle ces tools, Python les exécute
"""

# ============================================================================
# TOOLS POUR GESTION DES PRÊTS IMMOBILIERS
# ============================================================================

TOOL_EXTRACT_ALL_ECHEANCES = {
    "name": "extract_all_echeances_to_file",
    "description": """Extrait TOUTES les échéances d'un tableau d'amortissement PDF et les sauvegarde dans un fichier Markdown.

    IMPORTANT : Tu dois extraire la TOTALITÉ des échéances du PDF (entre 200 et 300 lignes généralement), pas seulement les 24 premières.

    Format de sortie attendu dans le fichier MD :
    date_echeance:montant_total:montant_capital:montant_interet:capital_restant_du

    Exemple :
    2023-05-15:258.33:0.00:258.33:250000.00
    2024-05-15:1166.59:955.68:210.91:240079.37

    Règles d'extraction :
    - IGNORER les lignes "DBL" (double month)
    - IGNORER la première ligne "ECH" avec frais de dossier
    - EXTRAIRE toutes les autres lignes d'échéances (ECH + lignes numérotées)
    - Format date : YYYY-MM-DD
    - Format montants : décimaux avec point (ex: 1166.59)
    """,
    "input_schema": {
        "type": "object",
        "properties": {
            "numero_pret": {
                "type": "string",
                "description": "Numéro du prêt (ex: '5009736BRM0911AH')"
            },
            "filename": {
                "type": "string",
                "description": "Nom du fichier MD à créer (ex: 'PRET_C_echeances.md')"
            },
            "echeances": {
                "type": "array",
                "description": "Tableau de TOUTES les échéances extraites du PDF",
                "items": {
                    "type": "object",
                    "properties": {
                        "date_echeance": {
                            "type": "string",
                            "description": "Date au format YYYY-MM-DD"
                        },
                        "montant_total": {
                            "type": "number",
                            "description": "Montant total de l'échéance en EUR"
                        },
                        "montant_capital": {
                            "type": "number",
                            "description": "Part de capital remboursé en EUR"
                        },
                        "montant_interet": {
                            "type": "number",
                            "description": "Part d'intérêts en EUR"
                        },
                        "capital_restant_du": {
                            "type": "number",
                            "description": "Capital restant dû APRÈS cette échéance en EUR"
                        }
                    },
                    "required": [
                        "date_echeance",
                        "montant_total",
                        "montant_capital",
                        "montant_interet",
                        "capital_restant_du"
                    ]
                }
            }
        },
        "required": ["numero_pret", "filename", "echeances"]
    }
}

TOOL_INSERT_PRET_FROM_FILE = {
    "name": "insert_pret_from_file",
    "description": """Insère un prêt immobilier et toutes ses échéances en base de données à partir d'un fichier MD.

    Le fichier MD doit contenir les échéances au format :
    date_echeance:montant_total:montant_capital:montant_interet:capital_restant_du

    Cette fonction :
    1. Crée l'enregistrement du prêt dans la table prets_immobiliers
    2. Insère toutes les échéances dans la table echeances_prets
    3. Valide la cohérence des données (dates chronologiques, montants positifs, etc.)
    4. Retourne un résumé de l'insertion
    """,
    "input_schema": {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Nom du fichier MD contenant les échéances (ex: 'PRET_C_echeances.md')"
            },
            "pret_params": {
                "type": "object",
                "description": "Paramètres du prêt à insérer",
                "properties": {
                    "numero_pret": {
                        "type": "string",
                        "description": "Numéro du prêt (ex: '5009736BRM0911AH')"
                    },
                    "intitule": {
                        "type": "string",
                        "description": "Nom du prêt (ex: 'SOLUTION P IMMO A TAUX FIXE')"
                    },
                    "banque": {
                        "type": "string",
                        "description": "Nom de la banque (ex: 'LCL')"
                    },
                    "montant_initial": {
                        "type": "number",
                        "description": "Montant emprunté en EUR (ex: 250000.00)"
                    },
                    "taux_annuel": {
                        "type": "number",
                        "description": "Taux d'intérêt annuel en % (ex: 1.05)"
                    },
                    "duree_mois": {
                        "type": "integer",
                        "description": "Durée totale en mois (ex: 252)"
                    },
                    "date_debut": {
                        "type": "string",
                        "description": "Date de début du prêt au format YYYY-MM-DD (ex: '2022-04-15')"
                    },
                    "date_debut_amortissement": {
                        "type": "string",
                        "description": "Date de début d'amortissement au format YYYY-MM-DD (ex: '2023-04-15')"
                    },
                    "type_pret": {
                        "type": "string",
                        "enum": ["AMORTISSEMENT_CONSTANT", "IN_FINE"],
                        "description": "Type de prêt"
                    }
                },
                "required": [
                    "numero_pret",
                    "intitule",
                    "banque",
                    "montant_initial",
                    "taux_annuel",
                    "duree_mois",
                    "date_debut",
                    "date_debut_amortissement",
                    "type_pret"
                ]
            }
        },
        "required": ["filename", "pret_params"]
    }
}

# ============================================================================
# TOOLS POUR CONSULTATION DES ÉCHÉANCES
# ============================================================================

TOOL_QUERY_PRET_ECHEANCE = {
    "name": "query_pret_echeance",
    "description": """Récupère les détails d'une échéance de prêt pour une date donnée.

    Utilisé pour décomposer un virement bancaire en capital + intérêts.

    Exemple : Un virement de 1166.59€ le 15/05/2024 correspond à quelle échéance ?
    → Retourne : capital=955.68€, intérêt=210.91€
    """,
    "input_schema": {
        "type": "object",
        "properties": {
            "numero_pret": {
                "type": "string",
                "description": "Numéro du prêt (ex: '5009736BRM0911AH')"
            },
            "date_echeance": {
                "type": "string",
                "description": "Date de l'échéance au format YYYY-MM-DD"
            }
        },
        "required": ["numero_pret", "date_echeance"]
    }
}

# ============================================================================
# TOOLS POUR BILAN D'OUVERTURE
# ============================================================================

TOOL_EXTRACT_BILAN_ACCOUNTS = {
    "name": "extract_bilan_accounts",
    "description": """Extrait TOUS les comptes du bilan d'ouverture depuis un PDF de bilan comptable.

    IMPORTANT : Extraire les comptes des pages BILAN - ACTIF DÉTAILLÉ et BILAN - PASSIF DÉTAILLÉ.

    Format attendu :
    - Les montants peuvent contenir des espaces (ex: "500 032" → 500032.00)
    - Les montants peuvent être négatifs (ex: "-50 003" → -50003.00)
    - Ignorer les lignes de totaux intermédiaires (TOTAL ACTIF IMMOBILISÉ, etc.)
    - Extraire uniquement les comptes avec numéros de 1 à 3 chiffres (101, 120, 161, 280, etc.)

    Comptes ACTIF (débit au bilan d'ouverture) :
    - 280 : Titres immobilisés (SCPI)
    - 290 : Provisions (montant NÉGATIF)
    - 412 : Créances
    - 502 : Valeurs mobilières
    - 512 : Banque

    Comptes PASSIF (crédit au bilan d'ouverture) :
    - 101 : Capital social
    - 120 : Report à nouveau (peut être négatif si déficitaire)
    - 130 : Résultat de l'exercice (peut être négatif si perte)
    - 161 : Emprunts
    - 401 : Dettes fournisseurs
    - 444 : Comptes courants associés

    Validation :
    - Total ACTIF doit = Total PASSIF
    - Si Report à nouveau (120) est négatif, c'est normal (déficit cumulé)
    """,
    "input_schema": {
        "type": "object",
        "properties": {
            "exercice": {
                "type": "string",
                "description": "Année de l'exercice comptable (ex: '2023')"
            },
            "date_bilan": {
                "type": "string",
                "description": "Date du bilan au format YYYY-MM-DD (ex: '2023-12-31')"
            },
            "comptes_actif": {
                "type": "array",
                "description": "Tous les comptes de l'ACTIF du bilan",
                "items": {
                    "type": "object",
                    "properties": {
                        "numero_compte": {
                            "type": "string",
                            "description": "Numéro de compte (ex: '280', '512')"
                        },
                        "libelle": {
                            "type": "string",
                            "description": "Libellé du compte (ex: 'Titres immobilisés SCPI', 'Banque LCL')"
                        },
                        "montant": {
                            "type": "number",
                            "description": "Montant en EUR (peut être négatif pour provisions)"
                        }
                    },
                    "required": ["numero_compte", "libelle", "montant"]
                }
            },
            "comptes_passif": {
                "type": "array",
                "description": "Tous les comptes du PASSIF du bilan",
                "items": {
                    "type": "object",
                    "properties": {
                        "numero_compte": {
                            "type": "string",
                            "description": "Numéro de compte (ex: '101', '161', '120')"
                        },
                        "libelle": {
                            "type": "string",
                            "description": "Libellé du compte (ex: 'Capital', 'Emprunts LCL', 'Report à nouveau')"
                        },
                        "montant": {
                            "type": "number",
                            "description": "Montant en EUR (peut être négatif pour report à nouveau déficitaire)"
                        }
                    },
                    "required": ["numero_compte", "libelle", "montant"]
                }
            },
            "total_actif": {
                "type": "number",
                "description": "Total de l'actif en EUR (doit être égal au total passif)"
            },
            "total_passif": {
                "type": "number",
                "description": "Total du passif en EUR (doit être égal au total actif)"
            }
        },
        "required": ["exercice", "date_bilan", "comptes_actif", "comptes_passif", "total_actif", "total_passif"]
    }
}

# ============================================================================
# TOOLS POUR COMPTABILITÉ
# ============================================================================

TOOL_CREATE_ECRITURE_COMPTABLE = {
    "name": "create_ecriture_comptable",
    "description": """Crée une écriture comptable en partie double.

    Règles de la partie double :
    - Somme des débits = Somme des crédits
    - Au moins 2 lignes
    - Chaque ligne doit avoir un compte et un montant > 0

    Exemple - Échéance prêt (capital 955.68€ + intérêt 210.91€) :
    Débit 164100 (Emprunt) : 955.68€
    Débit 661000 (Intérêts) : 210.91€
    Crédit 512000 (Banque) : 1166.59€
    """,
    "input_schema": {
        "type": "object",
        "properties": {
            "date": {
                "type": "string",
                "description": "Date de l'écriture au format YYYY-MM-DD"
            },
            "libelle": {
                "type": "string",
                "description": "Libellé de l'écriture (ex: 'Échéance prêt LCL - mai 2024')"
            },
            "lignes": {
                "type": "array",
                "description": "Lignes de l'écriture (débit/crédit)",
                "items": {
                    "type": "object",
                    "properties": {
                        "compte": {
                            "type": "string",
                            "description": "Numéro de compte PCG (ex: '164100')"
                        },
                        "debit": {
                            "type": "number",
                            "description": "Montant au débit (0 si crédit)"
                        },
                        "credit": {
                            "type": "number",
                            "description": "Montant au crédit (0 si débit)"
                        }
                    },
                    "required": ["compte"]
                },
                "minItems": 2
            }
        },
        "required": ["date", "libelle", "lignes"]
    }
}

# ============================================================================
# TOOLS POUR GESTION DES MÉMOIRES
# ============================================================================

TOOL_UPDATE_MEMOIRE = {
    "name": "update_memoire",
    "description": """Met à jour une des mémoires de _Head.Soeurise (courte/moyenne/longue).

    Hiérarchie des mémoires :
    - courte : Observations des 7 derniers jours (mise à jour quotidienne)
    - moyenne : Synthèses des 4 dernières semaines (mise à jour hebdomadaire)
    - longue : Connaissances établies (mise à jour mensuelle)
    - fondatrice : Identité permanente (modifications rares, réservées aux évolutions majeures)

    Le contenu doit être au format Markdown.
    """,
    "input_schema": {
        "type": "object",
        "properties": {
            "type_memoire": {
                "type": "string",
                "enum": ["courte", "moyenne", "longue"],
                "description": "Type de mémoire à mettre à jour"
            },
            "content": {
                "type": "string",
                "description": "Nouveau contenu de la mémoire en Markdown"
            },
            "commit_message": {
                "type": "string",
                "description": "Message de commit Git (ex: '🧠 Réveil 01/11/2025 - Nouveau prêt ingéré')"
            }
        },
        "required": ["type_memoire", "content", "commit_message"]
    }
}

# ============================================================================
# LISTE COMPLÈTE DES TOOLS
# ============================================================================

ALL_TOOLS = [
    TOOL_EXTRACT_ALL_ECHEANCES,
    TOOL_INSERT_PRET_FROM_FILE,
    TOOL_QUERY_PRET_ECHEANCE,
    TOOL_EXTRACT_BILAN_ACCOUNTS,
    TOOL_CREATE_ECRITURE_COMPTABLE,
    TOOL_UPDATE_MEMOIRE
]
