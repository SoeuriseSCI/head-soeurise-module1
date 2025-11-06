#!/usr/bin/env python3
"""
Script pour reclassifier les événements existants avec les nouveaux patterns améliorés
"""

import os
import sys
from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from models_module2 import get_session

def reclassifier_evenements():
    """Reclassifie tous les événements avec les patterns améliorés"""

    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("❌ Erreur: DATABASE_URL non définie")
        sys.exit(1)

    session = get_session(db_url)

    try:
        # Récupérer tous les événements à reclassifier (id >= 239)
        print("=" * 80)
        print("RECLASSIFICATION DES ÉVÉNEMENTS COMPTABLES")
        print("=" * 80)
        print()

        result = session.execute(
            text("SELECT id, libelle FROM evenements_comptables WHERE id >= 239 ORDER BY id")
        )
        events = result.fetchall()

        print(f"📊 {len(events)} événements à reclassifier")
        print()

        stats = {}

        for event in events:
            event_id = event[0]
            libelle = event[1]
            libelle_norm = libelle.lower()

            # Détection avec patterns améliorés (même logique que gestionnaire_evenements.py)
            type_evt = None

            # Solde d'ouverture
            if any(pattern in libelle_norm for pattern in [
                'ancien solde', 'solde reporte', 'solde precedent', 'report solde'
            ]):
                type_evt = 'SOLDE_OUVERTURE'

            # Assurance emprunteur (AVANT remboursement car contient "echeance")
            elif ('covea' in libelle_norm or 'assurance pret' in libelle_norm or
                  'caci' in libelle_norm or 'garantie emprunteur' in libelle_norm):
                type_evt = 'ASSURANCE_PRET'

            # Frais bancaires
            elif ('frais' in libelle_norm or 'cotisation' in libelle_norm or
                  'abon' in libelle_norm or 'abonnement' in libelle_norm):
                type_evt = 'FRAIS_BANCAIRES'

            # Honoraires comptable
            elif 'crp' in libelle_norm or 'comptabilit' in libelle_norm or 'expert comptable' in libelle_norm:
                type_evt = 'HONORAIRES_COMPTABLE'

            # Remboursement prêt (plus précis)
            elif ('pret immobilier' in libelle_norm and 'ech' in libelle_norm) or 'dossier no' in libelle_norm:
                type_evt = 'REMBOURSEMENT_PRET'

            # Apport associé
            elif ('vir sepa' in libelle_norm and 'bergsten' in libelle_norm) or 'apport' in libelle_norm:
                type_evt = 'APPORT_ASSOCIE'

            # Revenu SCPI
            elif 'scpi' in libelle_norm or 'epargne pierre' in libelle_norm:
                type_evt = 'REVENU_SCPI'

            # Achat ETF
            elif 'am msci' in libelle_norm or 'etf' in libelle_norm:
                type_evt = 'ACHAT_ETF'

            # Achat Amazon
            elif 'amazon' in libelle_norm and 'achat' in libelle_norm:
                type_evt = 'ACHAT_AMAZON'

            # Achat valeurs mobilières
            elif 'degiro' in libelle_norm or 'interactive brokers' in libelle_norm:
                type_evt = 'ACHAT_VALEURS_MOBILIERES'

            # Mettre à jour
            session.execute(
                text("""
                    UPDATE evenements_comptables
                    SET type_evenement = :type_evt,
                        updated_at = NOW()
                    WHERE id = :id
                """),
                {'type_evt': type_evt, 'id': event_id}
            )

            # Stats
            if type_evt:
                stats[type_evt] = stats.get(type_evt, 0) + 1
            else:
                stats['NON_CLASSIFIE'] = stats.get('NON_CLASSIFIE', 0) + 1

        session.commit()

        # Afficher statistiques
        print("=" * 80)
        print("✅ RECLASSIFICATION TERMINÉE")
        print("=" * 80)
        print()
        print("Statistiques par type:")
        for type_evt, count in sorted(stats.items(), key=lambda x: -x[1]):
            print(f"  {type_evt:30s} : {count:3d}")
        print()

        # Vérification détaillée
        print("=" * 80)
        print("VÉRIFICATIONS ATTENDUES")
        print("=" * 80)
        print()

        # REMBOURSEMENT_PRET
        result = session.execute(
            text("SELECT COUNT(*) FROM evenements_comptables WHERE type_evenement = 'REMBOURSEMENT_PRET' AND id >= 239")
        )
        count = result.fetchone()[0]
        print(f"  REMBOURSEMENT_PRET : {count:3d} (attendu: 18 - 9 mois × 2 prêts)")

        # ASSURANCE_PRET
        result = session.execute(
            text("SELECT COUNT(*) FROM evenements_comptables WHERE type_evenement = 'ASSURANCE_PRET' AND id >= 239")
        )
        count = result.fetchone()[0]
        print(f"  ASSURANCE_PRET     : {count:3d} (attendu: 12 - assurances CACI)")

        # REVENU_SCPI
        result = session.execute(
            text("SELECT COUNT(*) FROM evenements_comptables WHERE type_evenement = 'REVENU_SCPI' AND id >= 239")
        )
        count = result.fetchone()[0]
        print(f"  REVENU_SCPI        : {count:3d} (attendu: 4 - mais 8 avec doublons)")

        # ACHAT_ETF
        result = session.execute(
            text("SELECT COUNT(*) FROM evenements_comptables WHERE type_evenement = 'ACHAT_ETF' AND id >= 239")
        )
        count = result.fetchone()[0]
        print(f"  ACHAT_ETF          : {count:3d} (attendu: 3)")

        # ACHAT_AMAZON
        result = session.execute(
            text("SELECT COUNT(*) FROM evenements_comptables WHERE type_evenement = 'ACHAT_AMAZON' AND id >= 239")
        )
        count = result.fetchone()[0]
        print(f"  ACHAT_AMAZON       : {count:3d} (attendu: 4)")

        # APPORT_ASSOCIE
        result = session.execute(
            text("SELECT COUNT(*) FROM evenements_comptables WHERE type_evenement = 'APPORT_ASSOCIE' AND id >= 239")
        )
        count = result.fetchone()[0]
        print(f"  APPORT_ASSOCIE     : {count:3d} (attendu: 4)")

        # FRAIS_BANCAIRES
        result = session.execute(
            text("SELECT COUNT(*) FROM evenements_comptables WHERE type_evenement = 'FRAIS_BANCAIRES' AND id >= 239")
        )
        count = result.fetchone()[0]
        print(f"  FRAIS_BANCAIRES    : {count:3d}")

        # HONORAIRES_COMPTABLE
        result = session.execute(
            text("SELECT COUNT(*) FROM evenements_comptables WHERE type_evenement = 'HONORAIRES_COMPTABLE' AND id >= 239")
        )
        count = result.fetchone()[0]
        print(f"  HONORAIRES_COMPTABLE: {count:3d} (attendu: 4)")

        print()

    except Exception as e:
        session.rollback()
        print()
        print("=" * 80)
        print("❌ ERREUR")
        print("=" * 80)
        print(f"Erreur: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    reclassifier_evenements()
