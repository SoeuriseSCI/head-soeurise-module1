#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour examiner les données des prêts en base de données
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_utils import get_session
from models_module2 import PretImmobilier, EcheancePret
from sqlalchemy import func

def examiner_prets():
    """Examine les prêts et échéances en BD"""
    session = get_session()

    print("=" * 80)
    print("EXAMEN BASE DE DONNÉES - PRÊTS IMMOBILIERS")
    print("=" * 80)
    print()

    # Lister tous les prêts
    prets = session.query(PretImmobilier).filter_by(actif=True).all()

    if not prets:
        print("❌ Aucun prêt trouvé en base de données")
        return

    print(f"✓ {len(prets)} prêt(s) trouvé(s)\n")

    for pret in prets:
        print("-" * 80)
        print(f"📊 PRÊT: {pret.numero_pret} ({pret.banque})")
        print("-" * 80)
        print(f"  ID               : {pret.id}")
        print(f"  Libellé          : {pret.libelle}")
        print(f"  Montant initial  : {pret.montant_initial:,.2f} €")
        print(f"  Taux annuel      : {pret.taux_annuel:.3f}%")
        print(f"  Durée            : {pret.duree_mois} mois")
        print(f"  Date début       : {pret.date_debut}")
        print(f"  Date fin         : {pret.date_fin}")
        print(f"  Échéance mensuelle: {pret.echeance_mensuelle:,.2f} € (si constant)")
        print(f"  Franchise        : {pret.mois_franchise} mois")
        print()

        # Compter échéances
        nb_echeances = session.query(EcheancePret).filter_by(pret_id=pret.id).count()
        print(f"  ✓ {nb_echeances} échéances en BD")

        # Récupérer première et dernière échéance
        premiere = session.query(EcheancePret).filter_by(
            pret_id=pret.id
        ).order_by(EcheancePret.date_echeance.asc()).first()

        derniere = session.query(EcheancePret).filter_by(
            pret_id=pret.id
        ).order_by(EcheancePret.date_echeance.desc()).first()

        if premiere and derniere:
            print(f"  📅 Première échéance : {premiere.date_echeance} (#{premiere.numero_echeance})")
            print(f"     Capital restant   : {premiere.capital_restant_du:,.2f} €")
            print(f"  📅 Dernière échéance : {derniere.date_echeance} (#{derniere.numero_echeance})")
            print(f"     Capital restant   : {derniere.capital_restant_du:,.2f} €")

        # Afficher les 10 premières échéances pour diagnostic
        print()
        print(f"  📋 10 PREMIÈRES ÉCHÉANCES:")
        premieres_echeances = session.query(EcheancePret).filter_by(
            pret_id=pret.id
        ).order_by(EcheancePret.date_echeance.asc()).limit(10).all()

        for ech in premieres_echeances:
            print(f"     #{ech.numero_echeance:3d} | {ech.date_echeance} | "
                  f"Total: {ech.montant_total:>8.2f}€ | "
                  f"Int: {ech.montant_interet:>7.2f}€ | "
                  f"Cap: {ech.montant_capital:>8.2f}€ | "
                  f"Restant: {ech.capital_restant_du:>11,.2f}€")

        # Afficher les 5 dernières échéances
        print()
        print(f"  📋 5 DERNIÈRES ÉCHÉANCES:")
        dernieres_echeances = session.query(EcheancePret).filter_by(
            pret_id=pret.id
        ).order_by(EcheancePret.date_echeance.desc()).limit(5).all()

        for ech in reversed(dernieres_echeances):
            print(f"     #{ech.numero_echeance:3d} | {ech.date_echeance} | "
                  f"Total: {ech.montant_total:>8.2f}€ | "
                  f"Int: {ech.montant_interet:>7.2f}€ | "
                  f"Cap: {ech.montant_capital:>8.2f}€ | "
                  f"Restant: {ech.capital_restant_du:>11,.2f}€")

        print()

    print("=" * 80)
    print("FIN EXAMEN")
    print("=" * 80)

if __name__ == "__main__":
    try:
        examiner_prets()
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
