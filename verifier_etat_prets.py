#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VÉRIFICATION ÉTAT PRÊTS ET ÉCHÉANCES
=====================================

Vérifie l'état actuel de la base après tentatives d'insertion prêts
"""

import os
import sys
from models_module2 import get_session, PretImmobilier, EcheancePret, PropositionEnAttente
from sqlalchemy import text

def verifier_etat_prets():
    """Vérifie l'état complet des prêts et propositions"""

    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        print("❌ DATABASE_URL non définie")
        sys.exit(1)

    session = get_session(DATABASE_URL)

    print("=" * 80)
    print("📊 VÉRIFICATION ÉTAT BASE - PRÊTS")
    print("=" * 80)

    # 1. Compter les prêts
    print("\n1️⃣ PRÊTS IMMOBILIERS")
    print("-" * 80)

    prets = session.query(PretImmobilier).all()
    print(f"\n📋 Nombre total de prêts : {len(prets)}")

    if prets:
        for pret in prets:
            print(f"\n   Prêt ID {pret.id} :")
            print(f"   • Numéro : {pret.numero_pret}")
            print(f"   • Banque : {pret.banque}")
            print(f"   • Montant : {pret.montant_initial:,.2f} €")
            print(f"   • Taux : {pret.taux_annuel} %")
            print(f"   • Durée : {pret.duree_mois} mois")
            print(f"   • Date début : {pret.date_debut}")
            print(f"   • Type : {pret.type_amortissement}")
    else:
        print("   ℹ️  Aucun prêt en base")

    # 2. Compter les échéances
    print("\n\n2️⃣ ÉCHÉANCES")
    print("-" * 80)

    echeances = session.query(EcheancePret).all()
    print(f"\n📋 Nombre total d'échéances : {len(echeances)}")

    if prets:
        for pret in prets:
            nb_echeances = session.query(EcheancePret).filter(
                EcheancePret.pret_id == pret.id
            ).count()
            print(f"   • Prêt {pret.numero_pret} : {nb_echeances} échéances")

    # 3. Vérifier la proposition HEAD-F0DA3815
    print("\n\n3️⃣ PROPOSITION HEAD-F0DA3815")
    print("-" * 80)

    result = session.execute(text("""
        SELECT id, statut, type_evenement, created_at, updated_at, notes
        FROM propositions_en_attente
        WHERE token = 'HEAD-F0DA3815'
    """))

    prop = result.fetchone()

    if prop:
        print(f"\n   ✅ Proposition trouvée (ID: {prop[0]})")
        print(f"   • Statut : {prop[1]}")
        print(f"   • Type : {prop[2]}")
        print(f"   • Créée le : {prop[3]}")
        print(f"   • MAJ le : {prop[4]}")
        print(f"   • Notes : {prop[5]}")
    else:
        print("\n   ℹ️  Proposition non trouvée")

    # 4. Résumé et diagnostic
    print("\n\n4️⃣ DIAGNOSTIC")
    print("-" * 80)

    if len(prets) == 0 and len(echeances) == 0:
        print("\n   ⚠️  ÉTAT : Base vide (aucun prêt, aucune échéance)")
        print("   📋 ACTION : Pas de nettoyage nécessaire, relancer directement")

    elif len(prets) == 1:
        print("\n   ⚠️  ÉTAT : 1 seul prêt inséré (bug multi-PDFs)")
        print(f"   📋 DÉTAILS : {prets[0].numero_pret} avec {len(echeances)} échéances")
        print("   🧹 ACTION : Nettoyage requis avant relance")

    elif len(prets) == 2 and len(echeances) == 468:
        print("\n   ✅ ÉTAT : 2 prêts + 468 échéances (CORRECT)")
        print("   📋 DÉTAILS :")
        for pret in prets:
            nb_ech = session.query(EcheancePret).filter(
                EcheancePret.pret_id == pret.id
            ).count()
            print(f"      • {pret.numero_pret} ({pret.banque}) : {nb_ech} échéances")
        print("   ✅ ACTION : Base correcte, prêt pour relevés bancaires !")

    elif len(prets) == 2:
        print(f"\n   ⚠️  ÉTAT : 2 prêts mais {len(echeances)} échéances (attendu: 468)")
        print("   🧹 ACTION : Nettoyage requis avant relance")

    else:
        print(f"\n   ❌ ÉTAT : Incohérent ({len(prets)} prêts, {len(echeances)} échéances)")
        print("   🧹 ACTION : Nettoyage requis avant relance")

    print("\n" + "=" * 80)

    session.close()

if __name__ == '__main__':
    verifier_etat_prets()
