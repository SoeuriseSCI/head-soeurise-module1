#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Affichage détaillé des bilans 2024 (clôture) et 2025 (ouverture)
"""

import os
from datetime import date
from decimal import Decimal
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models_module2 import Base, ExerciceComptable, EcritureComptable, PlanCompte

# Connexion BD
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("❌ DATABASE_URL non définie")
    exit(1)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()


def calculer_solde_compte(session, compte_numero, exercice_id, date_limite=None):
    """
    Calcule le solde d'un compte pour un exercice donné

    Returns:
        (solde_debit, solde_credit, solde_net)
    """
    query = session.query(EcritureComptable).filter_by(exercice_id=exercice_id)

    if date_limite:
        query = query.filter(EcritureComptable.date_ecriture <= date_limite)

    ecritures = query.all()

    total_debit = Decimal('0')
    total_credit = Decimal('0')

    for ecriture in ecritures:
        if ecriture.compte_debit == compte_numero:
            total_debit += ecriture.montant
        if ecriture.compte_credit == compte_numero:
            total_credit += ecriture.montant

    solde_net = total_debit - total_credit

    return total_debit, total_credit, solde_net


def afficher_bilan_detaille(session, annee, date_bilan=None):
    """
    Affiche le bilan détaillé pour une année donnée
    """
    exercice = session.query(ExerciceComptable).filter_by(annee=annee).first()

    if not exercice:
        print(f"❌ Exercice {annee} non trouvé")
        return

    if not date_bilan:
        date_bilan = exercice.date_fin

    print(f"\n{'='*100}")
    print(f"BILAN DÉTAILLÉ - EXERCICE {annee} - AU {date_bilan.strftime('%d/%m/%Y')}")
    print(f"Statut: {exercice.statut}")
    print(f"{'='*100}\n")

    # Récupérer tous les comptes de classe 1-5 (bilan)
    comptes_bilan = session.query(PlanCompte).filter(
        PlanCompte.classe.in_([1, 2, 3, 4, 5])
    ).order_by(PlanCompte.numero_compte).all()

    # Séparer ACTIF et PASSIF
    actif_comptes = {}
    passif_comptes = {}

    for compte in comptes_bilan:
        debit, credit, solde = calculer_solde_compte(
            session, compte.numero_compte, exercice.id, date_bilan
        )

        # Ne garder que les comptes avec solde non nul
        if solde != 0:
            if compte.type_compte in ['ACTIF']:
                # ACTIF : solde débiteur normal
                actif_comptes[compte.numero_compte] = {
                    'libelle': compte.libelle,
                    'solde': solde,
                    'debit': debit,
                    'credit': credit
                }
            else:  # PASSIF
                # PASSIF : solde créditeur normal (on inverse le signe pour affichage)
                passif_comptes[compte.numero_compte] = {
                    'libelle': compte.libelle,
                    'solde': -solde,  # Inverser pour affichage positif au passif
                    'debit': debit,
                    'credit': credit
                }

    # Afficher ACTIF
    print("┌" + "─"*98 + "┐")
    print("│ " + "ACTIF".center(96) + " │")
    print("├" + "─"*98 + "┤")
    print(f"│ {'Compte':<10} │ {'Libellé':<50} │ {'Débit':<15} │ {'Crédit':<15} │")
    print("├" + "─"*98 + "┤")

    total_actif = Decimal('0')

    # Regrouper par classe
    for classe in [1, 2, 3, 4, 5]:
        comptes_classe = {k: v for k, v in actif_comptes.items() if k.startswith(str(classe))}

        if comptes_classe:
            print(f"│ CLASSE {classe} {' '*88}│")

            for numero, data in sorted(comptes_classe.items()):
                solde_display = data['solde']
                total_actif += solde_display

                print(f"│ {numero:<10} │ {data['libelle'][:50]:<50} │ {solde_display:>13,.2f} € │ {'':<15} │")

            print("│" + " "*98 + "│")

    print("├" + "─"*98 + "┤")
    print(f"│ {'TOTAL ACTIF':<62} │ {total_actif:>13,.2f} € │ {'':<15} │")
    print("└" + "─"*98 + "┘")

    # Afficher PASSIF
    print("\n┌" + "─"*98 + "┐")
    print("│ " + "PASSIF".center(96) + " │")
    print("├" + "─"*98 + "┤")
    print(f"│ {'Compte':<10} │ {'Libellé':<50} │ {'Crédit':<15} │ {'Débit':<15} │")
    print("├" + "─"*98 + "┤")

    total_passif = Decimal('0')

    # Regrouper par classe
    for classe in [1, 2, 3, 4, 5]:
        comptes_classe = {k: v for k, v in passif_comptes.items() if k.startswith(str(classe))}

        if comptes_classe:
            print(f"│ CLASSE {classe} {' '*88}│")

            for numero, data in sorted(comptes_classe.items()):
                solde_display = data['solde']
                total_passif += solde_display

                print(f"│ {numero:<10} │ {data['libelle'][:50]:<50} │ {solde_display:>13,.2f} € │ {'':<15} │")

            print("│" + " "*98 + "│")

    print("├" + "─"*98 + "┤")
    print(f"│ {'TOTAL PASSIF':<62} │ {total_passif:>13,.2f} € │ {'':<15} │")
    print("└" + "─"*98 + "┘")

    # Vérification équilibre
    print(f"\n{'='*100}")
    print(f"VÉRIFICATION ÉQUILIBRE")
    print(f"{'='*100}")
    print(f"Total ACTIF  : {total_actif:>15,.2f} €")
    print(f"Total PASSIF : {total_passif:>15,.2f} €")
    print(f"Différence   : {total_actif - total_passif:>15,.2f} €")

    if abs(total_actif - total_passif) < Decimal('0.01'):
        print("✅ BILAN ÉQUILIBRÉ")
    else:
        print("❌ BILAN DÉSÉQUILIBRÉ")

    print(f"{'='*100}\n")


# Afficher les deux bilans
print("\n" + "="*100)
print("BILANS COMPTABLES SCI SOEURISE".center(100))
print("="*100)

# Bilan de clôture 2024
afficher_bilan_detaille(session, 2024, date(2024, 12, 31))

# Bilan d'ouverture 2025
afficher_bilan_detaille(session, 2025, date(2025, 1, 1))

session.close()
