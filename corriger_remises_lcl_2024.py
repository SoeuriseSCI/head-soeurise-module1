#!/usr/bin/env python3
"""
Correction des remises LCL 2024
Méthode : Contre-passation + Écriture correcte
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models_module2 import get_session, EcritureComptable, ExerciceComptable
from decimal import Decimal
from datetime import datetime

DATABASE_URL = os.getenv('DATABASE_URL')
session = get_session(DATABASE_URL)

print("="*80)
print("🔧 CORRECTION REMISES LCL 2024")
print("="*80)

# Récupérer l'exercice 2024
exercice_2024 = session.query(ExerciceComptable).filter_by(annee=2024).first()
if not exercice_2024:
    print("❌ Exercice 2024 non trouvé")
    sys.exit(1)

# Identifier les remises
ecritures_fb = session.query(EcritureComptable).filter_by(
    exercice_id=exercice_2024.id,
    type_ecriture='FRAIS_BANCAIRES'
).all()

remises = []
patterns_remises = ['REMISE', 'VOTRE REM', 'REM LCL', 'REMBT']

for e in ecritures_fb:
    libelle_upper = e.libelle_ecriture.upper()
    if any(pattern in libelle_upper for pattern in patterns_remises):
        remises.append(e)

print(f"\n📊 Remises LCL à corriger : {len(remises)}")

if not remises:
    print("\n✅ Aucune remise à corriger")
    session.close()
    sys.exit(0)

# Afficher détails
total_remises = sum(Decimal(str(e.montant)) for e in remises)
print(f"   Total remises : {total_remises:.2f}€")
print(f"   Impact résultat : +{total_remises * 2:.2f}€")

# Demander confirmation
print("\n" + "="*80)
print("⚠️  CONFIRMATION REQUISE")
print("="*80)
print(f"""
Cette opération va créer {len(remises) * 2} nouvelles écritures :
- {len(remises)} contre-passations (annulation écritures incorrectes)
- {len(remises)} écritures correctes (diminution charges)

Impact final :
- Résultat 2024 : +{total_remises * 2:.2f}€
- Charges (627) : -{total_remises * 2:.2f}€

Êtes-vous sûr de vouloir continuer ?
""")

reponse = input("Tapez 'OUI' pour confirmer : ")
if reponse.upper() != 'OUI':
    print("\n❌ Opération annulée par l'utilisateur")
    session.close()
    sys.exit(0)

print("\n" + "="*80)
print("🔧 CRÉATION DES ÉCRITURES DE CORRECTION")
print("="*80)

ecritures_creees = []
erreurs = []

for i, e_orig in enumerate(remises, 1):
    print(f"\n📌 Traitement remise #{i}/{len(remises)} : {e_orig.numero_ecriture}")

    try:
        montant = Decimal(str(e_orig.montant))

        # ÉCRITURE #1 : CONTRE-PASSATION
        print(f"   1. Contre-passation...")

        e_annul = EcritureComptable(
            exercice_id=exercice_2024.id,
            numero_ecriture=f"{e_orig.numero_ecriture}-ANNUL",
            date_ecriture=e_orig.date_ecriture,
            libelle_ecriture=f"Annulation écriture incorrecte - {e_orig.libelle_ecriture}",
            compte_debit=e_orig.compte_credit,  # Inversion
            compte_credit=e_orig.compte_debit,   # Inversion
            montant=float(montant),
            type_ecriture='CORRECTION',
            source_email_id=e_orig.source_email_id
        )
        session.add(e_annul)
        ecritures_creees.append(e_annul)
        print(f"      ✅ Débit {e_orig.compte_credit} / Crédit {e_orig.compte_debit} : {montant:.2f}€")

        # ÉCRITURE #2 : ÉCRITURE CORRECTE
        print(f"   2. Écriture correcte...")

        e_corr = EcritureComptable(
            exercice_id=exercice_2024.id,
            numero_ecriture=f"{e_orig.numero_ecriture}-CORR",
            date_ecriture=e_orig.date_ecriture,
            libelle_ecriture=f"Correction - {e_orig.libelle_ecriture}",
            compte_debit=e_orig.compte_credit,   # Normalement 512 (Banque)
            compte_credit=e_orig.compte_debit,   # Normalement 627 (Frais bancaires)
            montant=float(montant),
            type_ecriture='FRAIS_BANCAIRES',
            source_email_id=e_orig.source_email_id
        )
        session.add(e_corr)
        ecritures_creees.append(e_corr)
        print(f"      ✅ Débit {e_orig.compte_credit} / Crédit {e_orig.compte_debit} : {montant:.2f}€")

        print(f"   ✅ Remise corrigée")

    except Exception as ex:
        erreur_msg = f"Remise {e_orig.numero_ecriture} : {str(ex)}"
        erreurs.append(erreur_msg)
        print(f"   ❌ ERREUR : {str(ex)}")
        continue

# Commit ou rollback
if erreurs:
    print("\n" + "="*80)
    print(f"❌ ERREURS DÉTECTÉES ({len(erreurs)})")
    print("="*80)
    for err in erreurs:
        print(f"  - {err}")

    print("\n⚠️  Transaction annulée (rollback)")
    session.rollback()
    session.close()
    sys.exit(1)

else:
    print("\n" + "="*80)
    print("✅ TOUTES LES CORRECTIONS CRÉÉES AVEC SUCCÈS")
    print("="*80)

    print(f"\nÉcritures créées : {len(ecritures_creees)}")
    print(f"  - Contre-passations : {len(remises)}")
    print(f"  - Écritures correctes : {len(remises)}")

    print("\n⚠️  Commit en cours...")
    session.commit()
    print("✅ Commit réussi")

print("\n" + "="*80)
print("📊 VÉRIFICATION POST-CORRECTION")
print("="*80)

# Vérifier que toutes les écritures sont bien en base
nb_ecritures_apres = session.query(EcritureComptable).filter_by(exercice_id=exercice_2024.id).count()
print(f"\nNombre d'écritures 2024 après correction : {nb_ecritures_apres}")

# Vérifier les écritures de correction
nb_corrections = session.query(EcritureComptable).filter_by(
    exercice_id=exercice_2024.id,
    type_ecriture='CORRECTION'
).count()
print(f"Écritures de correction (CORRECTION) : {nb_corrections}")

print("\n" + "="*80)
print("✅ CORRECTION TERMINÉE")
print("="*80)

print(f"""
Impact final :
- Résultat 2024 : +{total_remises * 2:.2f}€
- Charges (627) : -{total_remises * 2:.2f}€

Prochaines étapes :
1. Reconstruire les états financiers 2024 :
   python construire_etats_financiers_2024.py

2. Vérifier le nouveau résultat

3. Corriger le traitement des événements pour le futur :
   Modifier gestionnaire_evenements.py (voir instructions ci-dessous)
""")

print("\n" + "="*80)
print("📋 CORRECTION DU TRAITEMENT FUTUR")
print("="*80)

print("""
Pour éviter que ce problème se reproduise, il faut modifier le traitement
des remises dans le gestionnaire d'événements.

Fichier à modifier : gestionnaire_evenements.py

Actuellement (ligne ~228-231) :
  elif ('frais' in libelle_norm or 'cotisation' in libelle_norm or
        'abon' in libelle_norm or 'abonnement' in libelle_norm or
        'remise' in libelle_norm or 'lcl a la carte' in libelle_norm):
      type_evt = 'FRAIS_BANCAIRES'

Solution 1 : Séparer les remises en type distinct
  elif 'remise' in libelle_norm or 'votre rem' in libelle_norm:
      type_evt = 'REMISE_FRAIS_BANCAIRES'  # Nouveau type
  elif ('frais' in libelle_norm or 'cotisation' in libelle_norm or ...):
      type_evt = 'FRAIS_BANCAIRES'

Ensuite, dans la génération des propositions, traiter REMISE_FRAIS_BANCAIRES
comme une diminution de charge (même écriture que FRAIS_BANCAIRES mais avec
montant qui sera traité comme diminution).

Solution 2 (plus simple) : Inverser l'écriture dans extracteur_intelligent.py
Dans le prompt universel, ajouter une règle :
  "Pour les remises bancaires (libellé contient REMISE), l'écriture doit être :
   Débit 512 (Banque) / Crédit 627 (Frais bancaires) au lieu de l'inverse"

Recommandation : Solution 2 (plus simple, pas de nouveau type d'événement)
""")

session.close()
