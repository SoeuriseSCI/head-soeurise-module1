#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GESTIONNAIRE PRÊTS IMMOBILIERS - Ingestion et Lookup Échéances
================================================================

Fonctions :
1. Ingestion : Stocker tableaux d'amortissement en BD (données de référence)
2. Lookup : Retrouver ventilation intérêts/capital pour une échéance donnée

Usage :
- Email tableau amortissement → ingest_tableau_pret()
- Email relevé bancaire → lookup_echeance()

Tables utilisées :
- prets_immobiliers : Contrats
- echeances_prets : Échéancier ligne par ligne
"""

from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from models_module2 import PretImmobilier, EcheancePret


class PretsManager:
    """Gestionnaire des prêts immobiliers"""

    def __init__(self, session: Session):
        self.session = session

    def ingest_tableau_pret(self,
                           pret_data: Dict,
                           echeances_data: List[Dict],
                           source_email_id: str = None,
                           source_document: str = None) -> Tuple[bool, str, Optional[int]]:
        """
        Ingère un tableau d'amortissement complet en BD

        Args:
            pret_data: Données contrat (dict from ParseurTableauPret)
            echeances_data: Lignes échéancier (list of dicts)
            source_email_id: ID email source
            source_document: Nom fichier PDF source

        Returns:
            (success, message, pret_id)
        """
        try:
            # Vérifier si prêt existe déjà
            numero_pret = pret_data.get('numero_pret')
            if not numero_pret:
                return False, "Numéro de prêt manquant", None

            pret_existant = self.session.query(PretImmobilier).filter_by(
                numero_pret=numero_pret
            ).first()

            print(f"[PRETS_MGR] Recherche prêt existant '{numero_pret}': {'TROUVÉ' if pret_existant else 'NON TROUVÉ'}", flush=True)

            if pret_existant:
                print(f"[PRETS_MGR] Prêt existant ID={pret_existant.id}, suppression en cours...", flush=True)
                # Prêt existe déjà - vérifier si échéances sont complètes
                nb_echeances_existantes = self.session.query(EcheancePret).filter_by(
                    pret_id=pret_existant.id
                ).count()

                nb_echeances_attendues = len(echeances_data) if echeances_data else 0

                # Valider que les valeurs ne sont pas None
                if nb_echeances_existantes is None:
                    nb_echeances_existantes = 0
                if nb_echeances_attendues is None:
                    nb_echeances_attendues = 0

                if nb_echeances_existantes >= nb_echeances_attendues and nb_echeances_attendues > 0:
                    return True, f"Prêt {numero_pret} déjà complet en BD ({nb_echeances_existantes} échéances)", pret_existant.id
                else:
                    # Ingestion partielle précédente → supprimer et réinsérer
                    print(f"[PRETS_MGR] Ingestion partielle ({nb_echeances_existantes}/{nb_echeances_attendues}), suppression et réinsertion...", flush=True)
                    # Utiliser synchronize_session=False pour éviter erreurs
                    nb_echeances_supprimees = self.session.query(EcheancePret).filter_by(pret_id=pret_existant.id).delete(synchronize_session=False)
                    nb_prets_supprimes = self.session.query(PretImmobilier).filter_by(id=pret_existant.id).delete(synchronize_session=False)
                    self.session.flush()
                    print(f"[PRETS_MGR] Supprimés: {nb_echeances_supprimees} échéances, {nb_prets_supprimes} prêt(s)", flush=True)
                    # Continuer avec nouvelle insertion ci-dessous

            # Créer PretImmobilier
            pret = PretImmobilier(
                numero_pret=numero_pret,
                banque=pret_data.get('banque', 'INCONNU'),
                libelle=pret_data.get('libelle', f"Prêt {numero_pret}"),
                montant_initial=Decimal(str(pret_data.get('montant_initial', 0))),
                taux_annuel=Decimal(str(pret_data.get('taux_annuel', 0))),
                duree_mois=pret_data.get('duree_mois', 0),
                date_debut=self._parse_date(pret_data.get('date_debut')),
                date_fin=self._parse_date(pret_data.get('date_fin')),
                type_amortissement=pret_data.get('type_amortissement', 'AMORTISSEMENT_CONSTANT'),
                mois_franchise=pret_data.get('mois_franchise', 0),
                echeance_mensuelle=Decimal(str(pret_data.get('echeance_mensuelle', 0))) if pret_data.get('echeance_mensuelle') else None,
                interet_mensuel_franchise=Decimal(str(pret_data.get('interet_mensuel_franchise', 0))) if pret_data.get('interet_mensuel_franchise') else None,
                assurance_emprunteur=pret_data.get('assurance_emprunteur', False),
                assures=pret_data.get('assures'),
                source_email_id=source_email_id,
                source_document=source_document,
                actif=True
            )

            print(f"[PRETS_MGR] Création prêt {numero_pret}", flush=True)
            self.session.add(pret)
            self.session.flush()  # Pour obtenir pret.id
            print(f"[PRETS_MGR] Prêt créé avec ID={pret.id}", flush=True)

            # CRITIQUE: Nettoyer les échéances orphelines qui pourraient exister avec ce pret_id
            # (cas où un prêt précédent a été rollback mais ses échéances sont restées)
            nb_orphelines = self.session.query(EcheancePret).filter_by(pret_id=pret.id).count()
            if nb_orphelines > 0:
                print(f"[PRETS_MGR] ALERTE: {nb_orphelines} échéances orphelines détectées pour pret_id={pret.id}, suppression...", flush=True)
                self.session.query(EcheancePret).filter_by(pret_id=pret.id).delete(synchronize_session=False)
                self.session.flush()
                print(f"[PRETS_MGR] Échéances orphelines supprimées", flush=True)

            # Vérifier doublons dans echeances_data
            dates_vues = set()
            doublons = []
            echeances_dedupliquees = []

            for ech_data in echeances_data:
                date_str = ech_data.get('date_echeance')
                if date_str in dates_vues:
                    doublons.append(date_str)
                else:
                    dates_vues.add(date_str)
                    echeances_dedupliquees.append(ech_data)

            if doublons:
                print(f"[PRETS_MGR] ALERTE: {len(doublons)} dates en doublon détectées et SUPPRIMÉES: {doublons[:5]}", flush=True)
                print(f"[PRETS_MGR] Échéances après déduplication: {len(echeances_dedupliquees)}/{len(echeances_data)}", flush=True)
                echeances_data = echeances_dedupliquees

            # Créer EcheancePret pour chaque ligne
            nb_echeances = 0
            for ech_data in echeances_data:
                echeance = EcheancePret(
                    pret_id=pret.id,
                    numero_echeance=ech_data.get('numero_echeance'),
                    date_echeance=self._parse_date(ech_data.get('date_echeance')),
                    montant_total=Decimal(str(ech_data.get('montant_total', 0))),
                    montant_interet=Decimal(str(ech_data.get('montant_interet', 0))),
                    montant_capital=Decimal(str(ech_data.get('montant_capital', 0))),
                    capital_restant_du=Decimal(str(ech_data.get('capital_restant_du', 0))),
                    montant_assurance=Decimal(str(ech_data.get('montant_assurance', 0))) if ech_data.get('montant_assurance') else Decimal('0'),
                    comptabilise=False
                )
                self.session.add(echeance)
                nb_echeances += 1

            print(f"[PRETS_MGR] {nb_echeances} échéances créées, commit en cours...", flush=True)
            self.session.commit()
            print(f"[PRETS_MGR] COMMIT RÉUSSI pour prêt {numero_pret}", flush=True)

            message = f"Prêt {numero_pret} ingéré : {nb_echeances} échéances stockées"
            return True, message, pret.id

        except IntegrityError as e:
            print(f"[PRETS_MGR] ERREUR IntegrityError: {str(e)[:200]}", flush=True)
            self.session.rollback()
            return False, f"Erreur intégrité BD: {str(e)[:200]}", None

        except Exception as e:
            print(f"[PRETS_MGR] ERREUR Exception: {str(e)[:200]}", flush=True)
            self.session.rollback()
            return False, f"Erreur ingestion: {str(e)[:200]}", None

    def lookup_echeance(self,
                       numero_pret: str,
                       date_echeance: date,
                       tolerance_jours: int = 3) -> Optional[Dict]:
        """
        Recherche ventilation intérêts/capital pour une échéance donnée

        Args:
            numero_pret: Numéro du prêt (ex: "5009736BRM0911AH")
            date_echeance: Date de l'échéance (date object)
            tolerance_jours: Tolérance en jours pour trouver l'échéance

        Returns:
            {
              "echeance_id": 123,
              "pret_id": 1,
              "numero_pret": "5009736BRM0911AH",
              "numero_echeance": 5,
              "date_echeance": date(2023, 9, 15),
              "montant_total": 1166.59,
              "montant_interet": 215.32,
              "montant_capital": 951.27,
              "capital_restant_du": 245234.89,
              "montant_assurance": 0,
              "comptabilise": False
            }
            ou None si non trouvée
        """
        # Trouver le prêt
        pret = self.session.query(PretImmobilier).filter_by(
            numero_pret=numero_pret,
            actif=True
        ).first()

        if not pret:
            return None

        # Chercher échéance avec tolérance de date
        from sqlalchemy import and_, func

        # Chercher date exacte d'abord
        echeance = self.session.query(EcheancePret).filter(
            and_(
                EcheancePret.pret_id == pret.id,
                EcheancePret.date_echeance == date_echeance
            )
        ).first()

        # Si pas trouvée, chercher avec tolérance
        if not echeance and tolerance_jours > 0:
            from datetime import timedelta
            date_min = date_echeance - timedelta(days=tolerance_jours)
            date_max = date_echeance + timedelta(days=tolerance_jours)

            echeance = self.session.query(EcheancePret).filter(
                and_(
                    EcheancePret.pret_id == pret.id,
                    EcheancePret.date_echeance >= date_min,
                    EcheancePret.date_echeance <= date_max
                )
            ).order_by(
                # Trier par proximité de date
                func.abs(func.extract('epoch', EcheancePret.date_echeance - date_echeance))
            ).first()

        if not echeance:
            return None

        # Retourner données formatées
        return {
            "echeance_id": echeance.id,
            "pret_id": pret.id,
            "numero_pret": pret.numero_pret,
            "numero_echeance": echeance.numero_echeance,
            "date_echeance": echeance.date_echeance,
            "montant_total": float(echeance.montant_total),
            "montant_interet": float(echeance.montant_interet),
            "montant_capital": float(echeance.montant_capital),
            "capital_restant_du": float(echeance.capital_restant_du),
            "montant_assurance": float(echeance.montant_assurance) if echeance.montant_assurance else 0,
            "comptabilise": echeance.comptabilise
        }

    def marquer_echeance_comptabilisee(self,
                                      echeance_id: int,
                                      ecriture_comptable_id: int) -> bool:
        """
        Marque une échéance comme comptabilisée

        Args:
            echeance_id: ID de l'échéance
            ecriture_comptable_id: ID de l'écriture comptable créée

        Returns:
            success (bool)
        """
        try:
            echeance = self.session.query(EcheancePret).get(echeance_id)
            if not echeance:
                return False

            echeance.comptabilise = True
            echeance.ecriture_comptable_id = ecriture_comptable_id
            echeance.date_comptabilisation = datetime.utcnow()

            self.session.commit()
            return True

        except Exception:
            self.session.rollback()
            return False

    def get_pret_by_numero(self, numero_pret: str) -> Optional[Dict]:
        """
        Récupère les infos d'un prêt par son numéro

        Returns:
            dict ou None
        """
        pret = self.session.query(PretImmobilier).filter_by(
            numero_pret=numero_pret,
            actif=True
        ).first()

        if not pret:
            return None

        return {
            "id": pret.id,
            "numero_pret": pret.numero_pret,
            "banque": pret.banque,
            "montant_initial": float(pret.montant_initial),
            "taux_annuel": float(pret.taux_annuel),
            "duree_mois": pret.duree_mois,
            "date_debut": pret.date_debut,
            "date_fin": pret.date_fin,
            "type_amortissement": pret.type_amortissement,
            "echeance_mensuelle": float(pret.echeance_mensuelle) if pret.echeance_mensuelle else None,
            "actif": pret.actif
        }

    def list_prets_actifs(self) -> List[Dict]:
        """Liste tous les prêts actifs"""
        prets = self.session.query(PretImmobilier).filter_by(actif=True).all()

        return [{
            "id": p.id,
            "numero_pret": p.numero_pret,
            "banque": p.banque,
            "montant_initial": float(p.montant_initial),
            "echeance_mensuelle": float(p.echeance_mensuelle) if p.echeance_mensuelle else None
        } for p in prets]

    @staticmethod
    def _parse_date(date_str: any) -> Optional[date]:
        """Parse string ou date object vers date"""
        if not date_str:
            return None

        if isinstance(date_str, date):
            return date_str

        if isinstance(date_str, datetime):
            return date_str.date()

        # Parse string (format: YYYY-MM-DD)
        try:
            return datetime.strptime(str(date_str), '%Y-%m-%d').date()
        except ValueError:
            # Essayer DD/MM/YYYY
            try:
                return datetime.strptime(str(date_str), '%d/%m/%Y').date()
            except ValueError:
                return None


if __name__ == "__main__":
    print("OK: PretsManager prêt à l'emploi")
