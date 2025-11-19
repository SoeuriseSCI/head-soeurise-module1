#!/usr/bin/env python3
"""
Système de Cutoff par Extourne - Revenus SCPI (761)
====================================================

PRINCIPE DE L'EXTOURNE :

1. FIN ANNÉE N (31/12/N) - Email Ulrik janvier N+1 annonçant distribution T4 :
   Création écritures DATÉES 31/12/N :
   - Débit 4181 (Produits à recevoir)  7356€
   - Crédit 761 (Produits SCPI)         7356€

2. DÉBUT ANNÉE N+1 (01/01/N+1) - EXTOURNE AUTOMATIQUE :
   - Débit 761   7356€  ← Annule produit année N
   - Crédit 4181  7356€  ← Annule créance

3. PAIEMENT RÉEL (Janvier N+1) :
   - Débit 512  7356€
   - Crédit 761  7356€  ← Produit année N+1

AVANTAGES :
- Simple : Pas de rapprochement complexe
- Standard : Pratique comptable courante
- Robuste : Fonctionne même si montants différents

CLASSES :
- DetecteurAnnonceProduitARecevoir : Détecte email Ulrik + crée écritures 31/12/N
- GenerateurExtournes : Génère automatiquement extournes au 01/01/N+1
"""

from typing import Dict, List, Optional
from datetime import datetime, date
from decimal import Decimal
import re


class DetecteurAnnonceProduitARecevoir:
    """
    Détecte emails d'Ulrik annonçant produits à recevoir (cutoff)

    Email attendu :
    - De : ulrik.c.s.be@gmail.com
    - Objet : SCPI [Nom] - Distribution T4 [année]
    - Corps : Montant X € sera versé le JJ/MM/AAAA

    Crée écritures DATÉES 31/12/année (création rétroactive) :
    - Débit 4181 / Crédit 761
    - Type : CUTOFF_PRODUIT_A_RECEVOIR
    - Marqué pour extourne automatique
    """

    def __init__(self):
        self.name = "DetecteurAnnonceProduitARecevoir"

    def detecter(self, evenement: Dict) -> bool:
        """Vérifie si l'événement est une annonce de produit à recevoir"""

        # 1. Vérifier que c'est un email
        if evenement.get('type') != 'email':
            return False

        # 2. CRITIQUE : Vérifier émetteur = Ulrik (gérant SCI)
        emetteur = evenement.get('email_emetteur', '').lower().strip()
        if emetteur != 'ulrik.c.s.be@gmail.com':
            return False

        # 3. Vérifier objet contient "distribution" et "T4"
        objet = evenement.get('email_objet', '').lower()
        if 'distribution' not in objet or 't4' not in objet:
            return False

        # 4. Vérifier corps contient montant et "sera versé"
        corps = evenement.get('email_corps', '').lower()
        if 'sera vers' not in corps:  # "sera versé" ou "sera versée"
            return False

        return True

    def extraire_donnees(self, evenement: Dict) -> Optional[Dict]:
        """Extrait montant, année, date paiement de l'email"""

        objet = evenement.get('email_objet', '')
        corps = evenement.get('email_corps', '')

        # Extraire l'année (de l'objet ou du corps)
        # Ex: "Distribution T4 2024" ou "T4 année 2024"
        match_annee = re.search(r'(?:T4|année)\s+(\d{4})', objet + ' ' + corps, re.IGNORECASE)
        if not match_annee:
            return None
        annee = int(match_annee.group(1))

        # Extraire le montant
        # Ex: "7 356,00 €" ou "7356.00€" ou "7356 euros"
        match_montant = re.search(r'(\d[\d\s,\.]+)\s*(?:€|euros?)', corps, re.IGNORECASE)
        if not match_montant:
            return None

        montant_str = match_montant.group(1)
        # Nettoyer : supprimer espaces, remplacer virgule par point
        montant_str = montant_str.replace(' ', '').replace(',', '.')
        montant = float(montant_str)

        # Extraire date de paiement (optionnel)
        # Ex: "29 janvier 2025" ou "29/01/2025"
        date_paiement = None
        match_date = re.search(r'(\d{1,2})[/\s](\d{1,2})[/\s](\d{4})', corps)
        if match_date:
            jour = int(match_date.group(1))
            mois = int(match_date.group(2))
            annee_paiement = int(match_date.group(3))
            date_paiement = date(annee_paiement, mois, jour)

        # Extraire nom SCPI de l'objet
        # Ex: "SCPI Épargne Pierre - Distribution T4 2024"
        match_scpi = re.search(r'SCPI\s+([^-]+)', objet, re.IGNORECASE)
        nom_scpi = match_scpi.group(1).strip() if match_scpi else "SCPI"

        return {
            'annee': annee,
            'montant': montant,
            'date_paiement': date_paiement,
            'nom_scpi': nom_scpi
        }

    def generer_proposition(self, evenement: Dict) -> Optional[Dict]:
        """Génère proposition d'écritures de cutoff"""

        if not self.detecter(evenement):
            return None

        donnees = self.extraire_donnees(evenement)
        if not donnees:
            return None

        annee = donnees['annee']
        montant = donnees['montant']
        nom_scpi = donnees['nom_scpi']
        date_paiement = donnees['date_paiement']

        # Date de l'écriture : 31/12 de l'année concernée
        date_ecriture = date(annee, 12, 31)

        # Libellé
        libelle = f"Cutoff {annee} - Distribution T4 {nom_scpi}"
        if date_paiement:
            libelle += f" (paiement {date_paiement.strftime('%d/%m/%Y')})"

        # Génération des 2 écritures (partie double)
        return {
            'type_evenement': 'CUTOFF_PRODUIT_A_RECEVOIR',
            'description': f'Cutoff revenus {nom_scpi} T4 {annee}: {montant}€',
            'confiance': 0.95,  # Haute confiance (email Ulrik)
            'ecritures': [
                {
                    'date_ecriture': date_ecriture,
                    'libelle_ecriture': libelle,
                    'compte_debit': '4181',   # Produits à recevoir (ACTIF)
                    'compte_credit': '761',    # Produits de participations
                    'montant': montant,
                    'type_ecriture': 'CUTOFF_PRODUIT_A_RECEVOIR',
                    'extourne': True,          # MARQUEUR : Extourne au 01/01/N+1
                    'notes': f'Créé rétroactivement en {datetime.now().strftime("%m/%Y")} suite email Ulrik. '
                             f'Extourne automatique au 01/01/{annee+1}.'
                }
            ]
        }


class GenerateurExtournes:
    """
    Génère automatiquement les extournes au 01/01/N+1

    Recherche toutes les écritures marquées 'extourne: True'
    de l'exercice N et génère les contre-passations au 01/01/N+1.

    UTILISATION :
    - Exécuté lors de la clôture de l'exercice N
    - Ou au début de l'exercice N+1
    """

    def __init__(self, session):
        """
        Args:
            session: Session SQLAlchemy
        """
        self.session = session

    def generer_extournes_exercice(self, exercice_id: int) -> List[Dict]:
        """
        Génère les extournes pour un exercice

        Args:
            exercice_id: ID de l'exercice à extourn er

        Returns:
            Liste de propositions d'écritures d'extourne
        """
        from models_module2 import EcritureComptable, ExerciceComptable

        # 1. Récupérer l'exercice
        exercice = self.session.query(ExerciceComptable).filter_by(id=exercice_id).first()
        if not exercice:
            return []

        annee = exercice.annee
        date_extourne = date(annee + 1, 1, 1)

        # 2. Chercher toutes les écritures marquées pour extourne
        # Note: Le champ 'extourne' devrait être dans la table ecritures_comptables
        # Pour l'instant, on utilise le type_ecriture comme marqueur

        ecritures_cutoff = self.session.query(EcritureComptable).filter(
            EcritureComptable.exercice_id == exercice_id,
            EcritureComptable.type_ecriture.in_(['CUTOFF_PRODUIT_A_RECEVOIR'])
        ).all()

        if not ecritures_cutoff:
            return []

        # 3. Générer les extournes (inverse exact)
        propositions = []

        for ecriture in ecritures_cutoff:
            # Extourne = inversion débit ↔ crédit
            proposition = {
                'type_evenement': 'EXTOURNE_CUTOFF',
                'description': f'Extourne cutoff {annee}: {ecriture.libelle_ecriture}',
                'confiance': 1.0,  # Automatique
                'ecritures': [
                    {
                        'date_ecriture': date_extourne,
                        'libelle_ecriture': f'Extourne - {ecriture.libelle_ecriture}',
                        'compte_debit': ecriture.compte_credit,   # INVERSION
                        'compte_credit': ecriture.compte_debit,    # INVERSION
                        'montant': ecriture.montant,
                        'type_ecriture': 'EXTOURNE_CUTOFF',
                        'notes': f'Contre-passation automatique écriture ID {ecriture.id}'
                    }
                ]
            }
            propositions.append(proposition)

        return propositions


# EXEMPLE D'UTILISATION
if __name__ == '__main__':
    # Test détecteur
    detecteur = DetecteurAnnonceProduitARecevoir()

    # Email valide d'Ulrik
    email_test = {
        'type': 'email',
        'email_emetteur': 'ulrik.c.s.be@gmail.com',
        'email_objet': 'SCPI Épargne Pierre - Distribution T4 2024',
        'email_corps': '''Distribution T4 2024 - SCPI Épargne Pierre

Montant : 7 356,00 €
Date versement : 29 janvier 2025

Cette information permet à _Head de créer le cut-off comptable
pour clôture exercice 2024.
'''
    }

    # Test détection
    if detecteur.detecter(email_test):
        print("✅ Email détecté comme annonce cutoff")

        # Test extraction
        proposition = detecteur.generer_proposition(email_test)
        if proposition:
            print(f"\n📋 Proposition générée :")
            print(f"   Type : {proposition['type_evenement']}")
            print(f"   Description : {proposition['description']}")
            print(f"\n   Écritures :")
            for ec in proposition['ecritures']:
                print(f"     {ec['date_ecriture']} - {ec['libelle_ecriture']}")
                print(f"     Débit {ec['compte_debit']} / Crédit {ec['compte_credit']} : {ec['montant']}€")
                print(f"     Extourne : {ec.get('extourne', False)}")
    else:
        print("❌ Email non détecté")
