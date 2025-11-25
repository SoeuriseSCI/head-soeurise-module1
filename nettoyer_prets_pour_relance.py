#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NETTOYAGE PRÊTS POUR RELANCE COMPLÈTE
======================================

Supprime les données incorrectes suite aux bugs détectés :
- 2 prêts avec type_amortissement incorrect
- 468 échéances associées
- Proposition HEAD-F0DA3815

Permet de relancer le processus complet avec code corrigé.
"""

import os
import sys
from models_module2 import get_session, PretImmobilier, EcheancePret, PropositionEnAttente
from sqlalchemy import text

def nettoyer_prets():
    """Nettoie la base pour relance complète"""

    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        print("❌ DATABASE_URL non définie")
        sys.exit(1)

    session = get_session(DATABASE_URL)

    print("=" * 80)
    print("🧹 NETTOYAGE BASE POUR RELANCE")
    print("=" * 80)

    try:
        # 1. Supprimer les échéances (avant les prêts à cause des FK)
        print("\n1️⃣ Suppression échéances...")
        nb_echeances = session.query(EcheancePret).count()
        if nb_echeances > 0:
            session.query(EcheancePret).delete()
            print(f"   ✅ {nb_echeances} échéances supprimées")
        else:
            print("   ℹ️  Aucune échéance à supprimer")

        # 2. Supprimer les prêts
        print("\n2️⃣ Suppression prêts...")
        prets = session.query(PretImmobilier).all()
        if prets:
            for pret in prets:
                print(f"   • Suppression prêt {pret.numero_pret} ({pret.banque})")
                session.delete(pret)
            print(f"   ✅ {len(prets)} prêt(s) supprimé(s)")
        else:
            print("   ℹ️  Aucun prêt à supprimer")

        # 3. Supprimer la proposition HEAD-F0DA3815
        print("\n3️⃣ Suppression proposition HEAD-F0DA3815...")
        result = session.execute(text("""
            DELETE FROM propositions_en_attente
            WHERE token = 'HEAD-F0DA3815'
            RETURNING id
        """))
        deleted = result.fetchone()
        if deleted:
            print(f"   ✅ Proposition supprimée (ID: {deleted[0]})")
        else:
            print("   ℹ️  Proposition non trouvée (déjà supprimée)")

        # 4. Commit
        session.commit()
        print("\n" + "=" * 80)
        print("✅ NETTOYAGE TERMINÉ")
        print("=" * 80)

        print("\n🎯 Base prête pour relance complète :")
        print("   1. Déployer code corrigé (modèle + parseur)")
        print("   2. Exécuter migration SQL (ajout colonne type_taux)")
        print("   3. Renvoyer les 2 PDFs prêts (LCL + INVESTIMUR)")
        print("   4. Vérifier extraction correcte :")
        print("      • Prêt LCL SOLUTION : FIXE + AMORTISSABLE")
        print("      • Prêt LCL INVESTIMUR : FIXE + IN_FINE")
        print("   5. Valider et insérer")
        print()

    except Exception as e:
        session.rollback()
        print(f"\n❌ ERREUR : {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()

if __name__ == '__main__':
    print("\n⚠️  ATTENTION : Cette opération va SUPPRIMER :")
    print("   - Tous les prêts immobiliers")
    print("   - Toutes les échéances")
    print("   - La proposition HEAD-F0DA3815")
    print()
    confirmation = input("Taper 'NETTOYER' pour confirmer : ")

    if confirmation == 'NETTOYER':
        nettoyer_prets()
    else:
        print("\n❌ Abandon : confirmation non reçue")
        sys.exit(1)
