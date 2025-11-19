#!/usr/bin/env python3
"""
Système Cutoff par Extourne - Honoraires Comptables
====================================================

PRINCIPE:
1. Fin décembre N : Estimation honoraires comptables pour année N
2. Email/notification → Création cutoff daté 31/12/N
3. Extourne automatique au 01/01/N+1
4. Paiement réel facture en N+1

ÉCRITURES:

31/12/N - Cutoff (estimation) :
    Débit 6226 (Honoraires)                  1200€
    Crédit 4081 (Factures non parvenues)     1200€

01/01/N+1 - Extourne automatique :
    Débit 4081                               1200€
    Crédit 6226                              1200€

Mars N+1 - Paiement facture réelle :
    Débit 6226                               1250€
    Crédit 512                               1250€

RÉSULTAT:
- Exercice N : Charge 6226 = 1200€ (estimation)
- Exercice N+1 : Charge 6226 = 50€ (écart)
"""

import re
from typing import Dict, Optional
from datetime import datetime, date


class DetecteurAnnonceHonorairesARegler:
    """
    Détecte annonces d'honoraires comptables à provisionner (cutoff)

    SOURCES POSSIBLES:
    1. Email Ulrik : "Provisionner honoraires comptables [année] : X €"
    2. Email comptable : "Estimation honoraires [année] : X €"
    3. Manuel : Proposition cutoff fin décembre

    SÉCURITÉ:
    - Émetteur doit être Ulrik ou comptable connu
    - Validation du montant et de l'année
    """

    def __init__(self):
        self.name = "DetecteurAnnonceHonorairesARegler"
        # Liste des émetteurs autorisés (à adapter)
        self.emetteurs_autorises = [
            'ulrik.c.s.be@gmail.com',
            # Ajouter email comptable si besoin
        ]

    def detecter(self, evenement: Dict) -> bool:
        """Vérifie si c'est une annonce d'honoraires à provisionner"""

        # 1. Vérifier que c'est un email
        if evenement.get('type') != 'email':
            return False

        # 2. Vérifier émetteur autorisé
        emetteur = evenement.get('email_emetteur', '').lower().strip()
        if emetteur not in self.emetteurs_autorises:
            return False

        # 3. Vérifier objet/corps contient "honoraires" + "provisionner" ou "cutoff"
        objet = evenement.get('email_objet', '').lower()
        corps = evenement.get('email_corps', '').lower()
        texte_complet = objet + ' ' + corps

        if 'honoraires' not in texte_complet:
            return False

        if not ('provisionner' in texte_complet or 'cutoff' in texte_complet or 'estimation' in texte_complet):
            return False

        return True

    def generer_proposition(self, evenement: Dict) -> Optional[Dict]:
        """Génère proposition d'écritures de cutoff honoraires"""

        if not self.detecter(evenement):
            return None

        objet = evenement.get('email_objet', '')
        corps = evenement.get('email_corps', '')
        texte_complet = objet + ' ' + corps

        # Extraire l'année
        match_annee = re.search(r'(?:année|exercice|honoraires)\s+(\d{4})', texte_complet, re.IGNORECASE)
        if not match_annee:
            # Par défaut : année en cours
            annee = datetime.now().year
        else:
            annee = int(match_annee.group(1))

        # Extraire le montant
        match_montant = re.search(r'(\d[\d\s,\.]+)\s*(?:€|euros?)', texte_complet, re.IGNORECASE)
        if not match_montant:
            return None

        montant_str = match_montant.group(1)
        montant_str = montant_str.replace(' ', '').replace(',', '.')
        montant = float(montant_str)

        # Date de l'écriture : 31/12 de l'année concernée
        date_ecriture = date(annee, 12, 31)

        # Libellé
        libelle = f"Cutoff {annee} - Honoraires comptables (estimation)"

        note_extourne = (f'Créé en {datetime.now().strftime("%m/%Y")} suite email. '
                        f'Extourne automatique au 01/01/{annee+1}.')

        return {
            'type_evenement': 'CUTOFF_HONORAIRES',
            'description': f'Cutoff honoraires comptables {annee}: {montant}€',
            'confiance': 0.95,
            'ecritures': [
                {
                    'date_ecriture': date_ecriture,
                    'libelle_ecriture': libelle,
                    'compte_debit': '6226',   # Honoraires
                    'compte_credit': '4081',   # Factures non parvenues
                    'montant': montant,
                    'type_ecriture': 'CUTOFF_HONORAIRES',
                    'notes': note_extourne
                }
            ]
        }


# EXEMPLE D'UTILISATION
if __name__ == '__main__':
    detecteur = DetecteurAnnonceHonorairesARegler()

    # Email test
    email_test = {
        'type': 'email',
        'email_emetteur': 'ulrik.c.s.be@gmail.com',
        'email_objet': 'Cutoff honoraires comptables 2024',
        'email_corps': '''Provisionner honoraires comptables exercice 2024

Montant estimé : 1 200,00 €

Pour clôture comptable 2024.
'''
    }

    if detecteur.detecter(email_test):
        print("✅ Email détecté comme cutoff honoraires")

        proposition = detecteur.generer_proposition(email_test)
        if proposition:
            print(f"\n📋 Proposition générée :")
            print(f"   Type : {proposition['type_evenement']}")
            print(f"   Description : {proposition['description']}")
            print(f"\n   Écritures :")
            for ec in proposition['ecritures']:
                print(f"     {ec['date_ecriture']} - {ec['libelle_ecriture']}")
                print(f"     Débit {ec['compte_debit']} / Crédit {ec['compte_credit']} : {ec['montant']}€")
    else:
        print("❌ Email non détecté")
