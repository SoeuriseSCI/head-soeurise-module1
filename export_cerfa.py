#!/usr/bin/env python3
"""
EXPORT CERFA - SCI Soeurise
===========================
Génère les données pré-remplies pour les formulaires fiscaux :
- 2065 : Déclaration de résultats
- 2033-A : Bilan simplifié (Actif/Passif)
- 2033-B : Compte de résultat simplifié
- 2033-C : Immobilisations, amortissements
- 2033-D : Relevé des provisions
- 2033-F : Composition du capital
- 2033-G : Filiales et participations

Usage:
    python export_cerfa.py [annee]

Exemple:
    python export_cerfa.py 2024
"""

import sys
import os
import json
from datetime import datetime
from decimal import Decimal
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models_module2 import get_session, EcritureComptable, PlanCompte, ExerciceComptable

# ==============================================================================
# CONFIGURATION
# ==============================================================================

DATABASE_URL = os.getenv('DATABASE_URL')

# Informations SCI (extrait Kbis du 27/02/2022)
SCI_INFO = {
    "denomination": "SOEURISE",
    "forme_juridique": "Société civile",
    "siret": "91057486200010",
    "siren": "910574862",
    "rcs": "Paris",
    "adresse": "8 rue Déodat De Séverac",
    "code_postal": "75017",
    "ville": "Paris",
    "date_immatriculation": "21/02/2022",
    "date_cloture": "31/12",
    "regime_fiscal": "IS",  # Impôt sur les sociétés
    "regime_imposition": "RSI",  # Régime Simplifié d'Imposition
    "activite": "Détention de droits sociaux de sociétés ayant à leur actif des biens ou droits immobiliers",
    "code_ape": "6820B",  # Location de terrains et autres biens immobiliers
    "gerant": {
        "nom": "BERGSTEN",
        "prenom": "Ulrik",
        "date_naissance": "23/09/1957",
        "lieu_naissance": "Gammelstad (SUEDE)",
        "nationalite": "Suédoise",
        "adresse": "8 rue Déodat De Séverac 75017 Paris"
    },
    "associes": [
        {"nom": "Emma BERGSTEN", "parts": 49, "pourcentage": 49, "adresse": "3 rue Michal 75013 Paris"},
        {"nom": "Pauline BERGSTEN", "parts": 49, "pourcentage": 49, "adresse": "Vifilsgata 4 105 Reykjavik (Islande)"},
        {"nom": "Ulrik BERGSTEN", "parts": 2, "pourcentage": 2, "adresse": "8 rue Déodat De Séverac 75017 Paris"},
    ]
}

# ==============================================================================
# MAPPING COMPTES -> CASES CERFA 2033-A (BILAN ACTIF)
# ==============================================================================

MAPPING_2033A_ACTIF = {
    # ACTIF IMMOBILISE
    "immobilisations_incorporelles": {
        "case": "AA",
        "comptes": []
    },
    "terrains": {
        "case": "AB",
        "comptes": ["211"]
    },
    "constructions": {
        "case": "AC",
        "comptes": ["213"]
    },
    "installations_techniques": {
        "case": "AD",
        "comptes": []
    },
    "autres_immobilisations_corporelles": {
        "case": "AE",
        "comptes": []
    },
    "immobilisations_en_cours": {
        "case": "AF",
        "comptes": []
    },
    "participations": {
        "case": "AG",
        "comptes": ["271", "273", "2731"]
    },
    "autres_immobilisations_financieres": {
        "case": "AH",
        "comptes": []
    },
    "provisions_depreciation_immobilisations": {
        "case": "AH2",  # Déduction de l'actif immobilisé
        "comptes": ["290"],
        "signe": -1  # Montant négatif (déduction)
    },
    "total_actif_immobilise": {
        "case": "AI",
        "comptes": []  # Calculé
    },

    # ACTIF CIRCULANT
    "stocks_matieres_premieres": {
        "case": "AJ",
        "comptes": []
    },
    "stocks_encours_production": {
        "case": "AK",
        "comptes": []
    },
    "stocks_produits": {
        "case": "AL",
        "comptes": []
    },
    "avances_acomptes_verses": {
        "case": "AM",
        "comptes": []
    },
    "creances_clients": {
        "case": "AN",
        "comptes": ["412", "4181"]
    },
    "autres_creances": {
        "case": "AO",
        "comptes": []
    },
    "valeurs_mobilieres_placement": {
        "case": "AP",
        "comptes": ["503", "506"]
    },
    "disponibilites": {
        "case": "AQ",
        "comptes": ["512"]
    },
    "charges_constatees_avance": {
        "case": "AR",
        "comptes": []
    },
    "total_actif_circulant": {
        "case": "AS",
        "comptes": []  # Calculé
    },

    # TOTAL
    "total_actif": {
        "case": "AT",
        "comptes": []  # Calculé
    }
}

# ==============================================================================
# MAPPING COMPTES -> CASES CERFA 2033-A (BILAN PASSIF)
# ==============================================================================

MAPPING_2033A_PASSIF = {
    # CAPITAUX PROPRES
    "capital_social": {
        "case": "BA",
        "comptes": ["101"]
    },
    "primes_emission": {
        "case": "BB",
        "comptes": []
    },
    "reserves_legale": {
        "case": "BC",
        "comptes": ["106"]
    },
    "reserves_reglementees": {
        "case": "BD",
        "comptes": []
    },
    "autres_reserves": {
        "case": "BE",
        "comptes": []
    },
    "report_a_nouveau": {
        "case": "BF",
        "comptes": ["110", "119", "120"]  # Solde peut être positif ou négatif
    },
    "resultat_exercice": {
        "case": "BG",
        "comptes": []  # Calculé à partir du compte de résultat
    },
    "subventions_investissement": {
        "case": "BH",
        "comptes": []
    },
    "provisions_reglementees": {
        "case": "BI",
        "comptes": []
    },
    "total_capitaux_propres": {
        "case": "BJ",
        "comptes": []  # Calculé
    },

    # PROVISIONS
    "provisions_risques_charges": {
        "case": "BK",
        "comptes": []  # 290 déplacé à l'actif (déduction immobilisations)
    },

    # DETTES
    "emprunts_etablissements_credit": {
        "case": "BL",
        "comptes": ["164", "1688"]
    },
    "emprunts_dettes_financieres_diverses": {
        "case": "BM",
        "comptes": []
    },
    "avances_acomptes_recus": {
        "case": "BN",
        "comptes": []
    },
    "dettes_fournisseurs": {
        "case": "BO",
        "comptes": ["401", "4081"]
    },
    "dettes_fiscales_sociales": {
        "case": "BP",
        "comptes": ["444"]
    },
    "dettes_immobilisations": {
        "case": "BQ",
        "comptes": []
    },
    "autres_dettes": {
        "case": "BR",
        "comptes": ["455", "4551", "4552", "4553", "467"]
    },
    "produits_constates_avance": {
        "case": "BS",
        "comptes": []
    },
    "total_dettes": {
        "case": "BT",
        "comptes": []  # Calculé
    },

    # TOTAL
    "total_passif": {
        "case": "BU",
        "comptes": []  # Calculé
    }
}

# ==============================================================================
# MAPPING COMPTES -> CASES CERFA 2033-B (COMPTE DE RESULTAT)
# ==============================================================================

MAPPING_2033B = {
    # PRODUITS D'EXPLOITATION
    "ventes_marchandises": {
        "case": "FA",
        "comptes": []
    },
    "production_vendue_biens": {
        "case": "FB",
        "comptes": ["701"]
    },
    "production_vendue_services": {
        "case": "FC",
        "comptes": ["706"]
    },
    "production_stockee": {
        "case": "FD",
        "comptes": []
    },
    "production_immobilisee": {
        "case": "FE",
        "comptes": []
    },
    "subventions_exploitation": {
        "case": "FF",
        "comptes": []
    },
    "autres_produits": {
        "case": "FG",
        "comptes": ["752"]
    },
    "total_produits_exploitation": {
        "case": "FH",
        "comptes": []  # Calculé
    },

    # CHARGES D'EXPLOITATION
    "achats_marchandises": {
        "case": "FI",
        "comptes": []
    },
    "variation_stock_marchandises": {
        "case": "FJ",
        "comptes": []
    },
    "achats_matieres_premieres": {
        "case": "FK",
        "comptes": ["601", "606"]
    },
    "variation_stock_matieres": {
        "case": "FL",
        "comptes": []
    },
    "autres_achats_charges_externes": {
        "case": "FM",
        "comptes": ["613", "616", "6226", "623", "625", "626", "627"]  # 622 supprimé (obsolète, remplacé par 6226)
    },
    "impots_taxes": {
        "case": "FN",
        "comptes": ["6354"]
    },
    "salaires_traitements": {
        "case": "FO",
        "comptes": []
    },
    "charges_sociales": {
        "case": "FP",
        "comptes": []
    },
    "dotations_amortissements_immobilisations": {
        "case": "FQ",
        "comptes": ["6811"]
    },
    "dotations_provisions_actif_circulant": {
        "case": "FR",
        "comptes": []
    },
    "dotations_provisions_risques": {
        "case": "FS",
        "comptes": []
    },
    "autres_charges": {
        "case": "FT",
        "comptes": []
    },
    "total_charges_exploitation": {
        "case": "FU",
        "comptes": []  # Calculé
    },

    # RESULTAT D'EXPLOITATION
    "resultat_exploitation": {
        "case": "FV",
        "comptes": []  # Calculé
    },

    # PRODUITS FINANCIERS
    "produits_financiers_participations": {
        "case": "GA",
        "comptes": ["761"]
    },
    "produits_autres_valeurs_mobilieres": {
        "case": "GB",
        "comptes": ["764"]
    },
    "autres_interets_produits": {
        "case": "GC",
        "comptes": ["768"]
    },
    "reprises_provisions_financieres": {
        "case": "GD",
        "comptes": []
    },
    "differences_change_positives": {
        "case": "GE",
        "comptes": []
    },
    "produits_nets_cessions_vmp": {
        "case": "GF",
        "comptes": []
    },
    "total_produits_financiers": {
        "case": "GG",
        "comptes": []  # Calculé
    },

    # CHARGES FINANCIERES
    "dotations_provisions_financieres": {
        "case": "GH",
        "comptes": []
    },
    "interets_charges": {
        "case": "GI",
        "comptes": ["661"]
    },
    "differences_change_negatives": {
        "case": "GJ",
        "comptes": []
    },
    "charges_nettes_cessions_vmp": {
        "case": "GK",
        "comptes": []
    },
    "total_charges_financieres": {
        "case": "GL",
        "comptes": []  # Calculé
    },

    # RESULTAT FINANCIER
    "resultat_financier": {
        "case": "GM",
        "comptes": []  # Calculé
    },

    # RESULTAT COURANT
    "resultat_courant_avant_impots": {
        "case": "GN",
        "comptes": []  # Calculé
    },

    # PRODUITS EXCEPTIONNELS
    "produits_exceptionnels_operations_gestion": {
        "case": "HA",
        "comptes": []
    },
    "produits_exceptionnels_operations_capital": {
        "case": "HB",
        "comptes": []
    },
    "reprises_provisions_exceptionnelles": {
        "case": "HC",
        "comptes": []
    },
    "total_produits_exceptionnels": {
        "case": "HD",
        "comptes": []  # Calculé
    },

    # CHARGES EXCEPTIONNELLES
    "charges_exceptionnelles_operations_gestion": {
        "case": "HE",
        "comptes": []
    },
    "charges_exceptionnelles_operations_capital": {
        "case": "HF",
        "comptes": []
    },
    "dotations_provisions_exceptionnelles": {
        "case": "HG",
        "comptes": []
    },
    "total_charges_exceptionnelles": {
        "case": "HH",
        "comptes": []  # Calculé
    },

    # RESULTAT EXCEPTIONNEL
    "resultat_exceptionnel": {
        "case": "HI",
        "comptes": []  # Calculé
    },

    # IMPOTS
    "participation_salaries": {
        "case": "HJ",
        "comptes": []
    },
    "impots_benefices": {
        "case": "HK",
        "comptes": ["444"]
    },

    # RESULTAT NET
    "benefice_ou_perte": {
        "case": "HL",
        "comptes": []  # Calculé
    }
}

# ==============================================================================
# FONCTIONS DE CALCUL
# ==============================================================================

def calculer_soldes(session, exercice_id):
    """Calcule les soldes de tous les comptes pour un exercice"""
    ecritures = session.query(EcritureComptable).filter_by(exercice_id=exercice_id).all()

    soldes = defaultdict(lambda: {'debit': Decimal('0'), 'credit': Decimal('0')})

    for e in ecritures:
        montant = Decimal(str(e.montant))
        soldes[e.compte_debit]['debit'] += montant
        soldes[e.compte_credit]['credit'] += montant

    # Calculer solde net
    for compte, data in soldes.items():
        data['solde'] = data['debit'] - data['credit']

    return soldes


def remplir_cases(mapping, soldes, type_bilan="actif"):
    """Remplit les cases Cerfa à partir des soldes

    IMPORTANT : Arrondi à l'euro (pratique comptable standard pour Cerfa)
    """
    cases = {}

    for nom, config in mapping.items():
        case = config["case"]
        comptes = config["comptes"]
        signe_forcé = config.get("signe", 1)  # Par défaut +1, peut être -1 pour déductions

        if not comptes:
            cases[case] = {"nom": nom, "montant": 0, "comptes": []}
            continue

        montant_total = Decimal('0')
        comptes_utilises = []

        for num_compte in comptes:
            # Chercher le compte exact ou les sous-comptes
            for compte, data in soldes.items():
                if compte == num_compte or compte.startswith(num_compte):
                    solde = data['solde']

                    # Pour le passif, inverser le signe (créditeur = positif)
                    if type_bilan == "passif":
                        solde = -solde

                    # Pour l'actif, le solde reste tel quel (débiteur = positif)
                    # SAUF si signe_forcé = -1 (comptes correcteurs d'actif)
                    # Dans ce cas, on garde le solde brut (créditeur négatif)
                    elif type_bilan == "actif" and signe_forcé == -1:
                        # Ne pas inverser : solde créditeur reste négatif
                        pass

                    # Pour les charges, le solde débiteur est positif
                    # Pour les produits, inverser (créditeur = positif)
                    if type_bilan == "produit":
                        solde = -solde

                    if abs(solde) >= Decimal('0.01'):
                        montant_total += solde
                        comptes_utilises.append({"compte": compte, "solde": int(round(solde))})

        # ARRONDI À L'EURO pour déclarations fiscales
        montant_arrondi = int(round(montant_total))

        cases[case] = {
            "nom": nom,
            "montant": montant_arrondi,
            "comptes": comptes_utilises
        }

    return cases


def generer_2033a(soldes, resultat_exercice):
    """Génère le formulaire 2033-A (Bilan)"""
    actif = remplir_cases(MAPPING_2033A_ACTIF, soldes, "actif")
    passif = remplir_cases(MAPPING_2033A_PASSIF, soldes, "passif")

    # Calculer les totaux ACTIF (y compris provisions en déduction)
    actif_immobilise = sum(
        float(actif[c]["montant"]) for c in ["AA", "AB", "AC", "AD", "AE", "AF", "AG", "AH", "AH2"]
    )
    actif["AI"]["montant"] = int(round(actif_immobilise))

    actif_circulant = sum(
        float(actif[c]["montant"]) for c in ["AJ", "AK", "AL", "AM", "AN", "AO", "AP", "AQ", "AR"]
    )
    actif["AS"]["montant"] = int(round(actif_circulant))

    actif["AT"]["montant"] = int(round(actif_immobilise + actif_circulant))

    # Ajouter le résultat au passif (arrondi à l'euro)
    passif["BG"]["montant"] = int(round(resultat_exercice))

    # Calculer les totaux PASSIF (arrondi à l'euro)
    capitaux_propres = sum(
        float(passif[c]["montant"]) for c in ["BA", "BB", "BC", "BD", "BE", "BF", "BG", "BH", "BI"]
    )
    passif["BJ"]["montant"] = int(round(capitaux_propres))

    total_dettes = sum(
        float(passif[c]["montant"]) for c in ["BL", "BM", "BN", "BO", "BP", "BQ", "BR", "BS"]
    )
    passif["BT"]["montant"] = int(round(total_dettes))

    passif["BU"]["montant"] = int(round(capitaux_propres + float(passif["BK"]["montant"]) + total_dettes))

    return {"actif": actif, "passif": passif}


def generer_2033b(soldes):
    """Génère le formulaire 2033-B (Compte de résultat)"""
    # Produits (créditeurs = positifs)
    produits_exploitation = remplir_cases({k: v for k, v in MAPPING_2033B.items()
                                           if v["case"].startswith("F") and v["case"] < "FI"},
                                          soldes, "produit")

    # Charges (débiteurs = positifs)
    charges_exploitation = remplir_cases({k: v for k, v in MAPPING_2033B.items()
                                          if v["case"].startswith("F") and v["case"] >= "FI" and v["case"] <= "FT"},
                                         soldes, "charge")

    # Produits financiers
    produits_financiers = remplir_cases({k: v for k, v in MAPPING_2033B.items()
                                         if v["case"].startswith("G") and v["case"] <= "GF"},
                                        soldes, "produit")

    # Charges financières
    charges_financieres = remplir_cases({k: v for k, v in MAPPING_2033B.items()
                                         if v["case"].startswith("G") and v["case"] >= "GH" and v["case"] <= "GK"},
                                        soldes, "charge")

    # Fusionner
    resultat = {}
    resultat.update(produits_exploitation)
    resultat.update(charges_exploitation)
    resultat.update(produits_financiers)
    resultat.update(charges_financieres)

    # Calculer les totaux
    total_produits_exploitation = sum(
        float(resultat.get(c, {"montant": 0})["montant"])
        for c in ["FA", "FB", "FC", "FD", "FE", "FF", "FG"]
    )
    resultat["FH"] = {"nom": "total_produits_exploitation", "montant": total_produits_exploitation, "comptes": []}

    total_charges_exploitation = sum(
        float(resultat.get(c, {"montant": 0})["montant"])
        for c in ["FI", "FJ", "FK", "FL", "FM", "FN", "FO", "FP", "FQ", "FR", "FS", "FT"]
    )
    resultat["FU"] = {"nom": "total_charges_exploitation", "montant": total_charges_exploitation, "comptes": []}

    resultat_exploitation = round(total_produits_exploitation - total_charges_exploitation, 2)
    resultat["FV"] = {"nom": "resultat_exploitation", "montant": resultat_exploitation, "comptes": []}

    total_produits_financiers = sum(
        float(resultat.get(c, {"montant": 0})["montant"])
        for c in ["GA", "GB", "GC", "GD", "GE", "GF"]
    )
    resultat["GG"] = {"nom": "total_produits_financiers", "montant": total_produits_financiers, "comptes": []}

    total_charges_financieres = sum(
        float(resultat.get(c, {"montant": 0})["montant"])
        for c in ["GH", "GI", "GJ", "GK"]
    )
    resultat["GL"] = {"nom": "total_charges_financieres", "montant": total_charges_financieres, "comptes": []}

    resultat_financier = round(total_produits_financiers - total_charges_financieres, 2)
    resultat["GM"] = {"nom": "resultat_financier", "montant": resultat_financier, "comptes": []}

    resultat_courant = round(resultat_exploitation + resultat_financier, 2)
    resultat["GN"] = {"nom": "resultat_courant_avant_impots", "montant": resultat_courant, "comptes": []}

    # Résultat net (sans exceptionnel pour l'instant)
    resultat["HL"] = {"nom": "benefice_ou_perte", "montant": resultat_courant, "comptes": []}

    return resultat


def generer_2033f():
    """Génère le formulaire 2033-F (Composition du capital)"""
    return {
        "capital_social": 1000.00,
        "nombre_parts": 100,
        "valeur_nominale": 10.00,
        "associes": SCI_INFO["associes"]
    }


def generer_2065(resultat_comptable, deficit_reportable, annee):
    """Génère le formulaire 2065 (Déclaration de résultats)

    Args:
        resultat_comptable: Bénéfice de l'exercice (produits - charges)
        deficit_reportable: Déficit des exercices antérieurs (valeur positive)
        annee: Année de l'exercice
    """
    # Calcul du résultat fiscal : résultat comptable - déficit reportable
    resultat_fiscal = resultat_comptable - deficit_reportable

    # Si résultat fiscal négatif, pas d'IS (déficit reportable pour l'année suivante)
    if resultat_fiscal <= 0:
        is_du = Decimal('0')
        nouveau_deficit = abs(resultat_fiscal)  # Déficit à reporter
        resultat_fiscal_imposable = Decimal('0')
    else:
        nouveau_deficit = Decimal('0')
        resultat_fiscal_imposable = resultat_fiscal
        # Taux IS 2024 : 15% jusqu'à 42 500€, puis 25%
        if resultat_fiscal_imposable <= 42500:
            is_du = resultat_fiscal_imposable * Decimal('0.15')
        else:
            is_du = Decimal('42500') * Decimal('0.15') + (resultat_fiscal_imposable - Decimal('42500')) * Decimal('0.25')

    # ARRONDI À L'EURO pour toutes les valeurs fiscales
    return {
        "exercice": {
            "annee": annee,
            "date_debut": f"01/01/{annee}",
            "date_fin": f"31/12/{annee}"
        },
        "resultat_comptable": int(round(resultat_comptable)),
        "deficit_reportable_utilise": int(round(min(deficit_reportable, resultat_comptable))) if resultat_comptable > 0 else 0,
        "resultat_fiscal": int(round(max(resultat_fiscal, Decimal('0')))),
        "is_taux_reduit_15": int(round(min(resultat_fiscal_imposable, Decimal('42500')) * Decimal('0.15'))) if resultat_fiscal_imposable > 0 else 0,
        "is_taux_normal_25": int(round((resultat_fiscal_imposable - Decimal('42500')) * Decimal('0.25'))) if resultat_fiscal_imposable > 42500 else 0,
        "is_total": int(round(is_du)),
        "resultat_net_apres_is": int(round(resultat_comptable - is_du)),
        "nouveau_deficit_reportable": int(round(nouveau_deficit))
    }


# ==============================================================================
# FONCTION PRINCIPALE
# ==============================================================================

def exporter_cerfa(annee=2024):
    """Exporte tous les formulaires Cerfa pour une année"""

    session = get_session(DATABASE_URL)

    print("=" * 80)
    print(f"EXPORT CERFA - EXERCICE {annee}")
    print("=" * 80)

    # Récupérer l'exercice
    exercice = session.query(ExerciceComptable).filter_by(annee=annee).first()
    if not exercice:
        print(f"Exercice {annee} non trouvé")
        return None

    print(f"\nExercice : {exercice.date_debut} -> {exercice.date_fin}")
    print(f"Statut : {exercice.statut}")

    # Calculer les soldes
    soldes = calculer_soldes(session, exercice.id)
    print(f"Comptes mouvementés : {len(soldes)}")

    # Calculer le résultat
    total_charges = sum(
        data['solde'] for compte, data in soldes.items()
        if compte.startswith('6') and compte != '89'
    )
    total_produits = sum(
        -data['solde'] for compte, data in soldes.items()
        if compte.startswith('7') and compte != '89'
    )
    resultat_exercice = total_produits - total_charges

    # Calcul du déficit reportable (comptes 119 et 120 débiteurs = déficit)
    # 119 = Report à nouveau débiteur (déficit)
    # 120 = Résultat de l'exercice précédent (si débiteur = déficit)
    deficit_reportable = Decimal('0')
    if '119' in soldes:
        solde_119 = soldes['119']['debit'] - soldes['119']['credit']
        if solde_119 > 0:  # Solde débiteur = déficit
            deficit_reportable += solde_119
    if '120' in soldes:
        solde_120 = soldes['120']['debit'] - soldes['120']['credit']
        if solde_120 > 0:  # Solde débiteur = déficit (résultat négatif affecté)
            deficit_reportable += solde_120

    print(f"\nRésultat comptable de l'exercice : {float(resultat_exercice):,.2f} €")
    print(f"Déficit reportable des exercices antérieurs : {float(deficit_reportable):,.2f} €")
    if deficit_reportable >= resultat_exercice:
        print(f"→ Résultat fiscal : 0,00 € (déficit absorbe le bénéfice)")
        print(f"→ IS à payer : 0,00 €")
    else:
        print(f"→ Résultat fiscal imposable : {float(resultat_exercice - deficit_reportable):,.2f} €")

    # Générer les formulaires
    print("\n" + "-" * 80)
    print("Génération des formulaires...")
    print("-" * 80)

    cerfa_2033a = generer_2033a(soldes, float(resultat_exercice))
    print("  2033-A (Bilan) : OK")

    cerfa_2033b = generer_2033b(soldes)
    print("  2033-B (Compte de résultat) : OK")

    cerfa_2033f = generer_2033f()
    print("  2033-F (Composition capital) : OK")

    cerfa_2065 = generer_2065(resultat_exercice, deficit_reportable, annee)
    print("  2065 (Déclaration résultats) : OK")

    # Assembler l'export
    export = {
        "meta": {
            "date_generation": datetime.now().isoformat(),
            "exercice": annee,
            "societe": SCI_INFO
        },
        "formulaires": {
            "2065": cerfa_2065,
            "2033-A": cerfa_2033a,
            "2033-B": cerfa_2033b,
            "2033-F": cerfa_2033f
        },
        "resume": {
            "total_actif": cerfa_2033a["actif"]["AT"]["montant"],
            "total_passif": cerfa_2033a["passif"]["BU"]["montant"],
            "resultat_comptable": float(resultat_exercice),
            "deficit_reportable": float(deficit_reportable),
            "resultat_fiscal": cerfa_2065["resultat_fiscal"],
            "is_a_payer": cerfa_2065["is_total"],
            "resultat_net": cerfa_2065["resultat_net_apres_is"],
            "nouveau_deficit_reportable": cerfa_2065["nouveau_deficit_reportable"]
        }
    }

    # Sauvegarder
    output_file = f"cerfa_{annee}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export, f, indent=2, ensure_ascii=False, default=str)

    print(f"\nExport sauvegardé : {output_file}")

    # Afficher le résumé
    print("\n" + "=" * 80)
    print("RÉSUMÉ FISCAL")
    print("=" * 80)
    print(f"""
    BILAN AU 31/12/{annee}
    ─────────────────────────────────────
    Total ACTIF  : {export['resume']['total_actif']:>14,.2f} €
    Total PASSIF : {export['resume']['total_passif']:>14,.2f} €

    COMPTE DE RÉSULTAT {annee}
    ─────────────────────────────────────
    Résultat comptable : {float(resultat_exercice):>14,.2f} €

    CALCUL DE L'IS
    ─────────────────────────────────────
    Résultat comptable     : {cerfa_2065['resultat_comptable']:>11,.2f} €
    Déficit reportable     : {cerfa_2065['deficit_reportable_utilise']:>11,.2f} €
    ─────────────────────────────────────
    Résultat fiscal        : {cerfa_2065['resultat_fiscal']:>11,.2f} €
    IS taux réduit (15%)   : {cerfa_2065['is_taux_reduit_15']:>11,.2f} €
    IS taux normal (25%)   : {cerfa_2065['is_taux_normal_25']:>11,.2f} €
    ─────────────────────────────────────
    IS TOTAL À PAYER       : {cerfa_2065['is_total']:>11,.2f} €

    RÉSULTAT NET APRÈS IS  : {cerfa_2065['resultat_net_apres_is']:>12,.2f} €
    Nouveau déficit report.: {cerfa_2065['nouveau_deficit_reportable']:>12,.2f} €
    """)

    session.close()
    return export


# ==============================================================================
# POINT D'ENTRÉE
# ==============================================================================

if __name__ == "__main__":
    annee = int(sys.argv[1]) if len(sys.argv) > 1 else 2024
    exporter_cerfa(annee)
