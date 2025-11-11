#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VÉRIFICATION PRÊTS APRÈS RENUMÉROTOATION
========================================
Vérifie que les prêts et échéances sont intacts après renumérotoation exercices
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models_module2 import PretImmobilier, EcheancePret

def verifier_prets():
    """Vérifie l'intégrité des prêts et échéances"""

    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL non définie")
        return False

    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        print("\n" + "="*70)
        print("VÉRIFICATION PRÊTS ET ÉCHÉANCES")
        print("="*70)

        # Compter les prêts
        nb_prets = session.query(PretImmobilier).count()
        print(f"\n📊 Prêts immobiliers : {nb_prets}")

        # Détail des prêts
        prets = session.query(PretImmobilier).all()
        for pret in prets:
            nb_echeances = session.query(EcheancePret).filter_by(pret_id=pret.id).count()
            print(f"\n   🏦 {pret.numero_pret} ({pret.banque})")
            print(f"      - Montant initial : {pret.montant_initial:,.2f} €")
            print(f"      - Durée : {pret.duree_mois} mois")
            print(f"      - Échéances : {nb_echeances}")

        # Compter les échéances
        nb_echeances_total = session.query(EcheancePret).count()
        print(f"\n📅 Total échéances : {nb_echeances_total}")

        # Vérifier intégrité FK pret_id
        print("\n🔍 Vérification intégrité référentielle...")
        result = session.execute(text("""
            SELECT COUNT(*) as orphelines
            FROM echeances_prets ep
            LEFT JOIN prets_immobiliers pi ON ep.pret_id = pi.id
            WHERE pi.id IS NULL
        """))
        nb_orphelines = result.fetchone()[0]

        if nb_orphelines > 0:
            print(f"   ❌ {nb_orphelines} échéances orphelines détectées")
            return False
        else:
            print(f"   ✅ Aucune échéance orpheline")

        # Résultat final
        print("\n" + "="*70)
        if nb_prets == 2 and nb_echeances_total == 468 and nb_orphelines == 0:
            print("✅ VALIDATION COMPLÈTE")
            print("="*70)
            print("\n📊 Résumé :")
            print(f"   - Prêts : {nb_prets} / 2 attendus ✅")
            print(f"   - Échéances : {nb_echeances_total} / 468 attendues ✅")
            print(f"   - Intégrité FK : Aucune orpheline ✅")
            print("\n✅ Les prêts n'ont PAS été affectés par la renumérotoation")
            return True
        else:
            print("❌ ANOMALIE DÉTECTÉE")
            print("="*70)
            print(f"\n   - Prêts : {nb_prets} (attendu: 2)")
            print(f"   - Échéances : {nb_echeances_total} (attendu: 468)")
            return False

    except Exception as e:
        print(f"\n❌ ERREUR : {e}")
        return False
    finally:
        session.close()

if __name__ == '__main__':
    succes = verifier_prets()
    sys.exit(0 if succes else 1)
