#!/usr/bin/env python3
"""
Identification précise des remises LCL à corriger
Affiche les écritures exactes et le plan de correction
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models_module2 import get_session, EcritureComptable, PlanCompte, ExerciceComptable
from decimal import Decimal

DATABASE_URL = os.getenv('DATABASE_URL')
session = get_session(DATABASE_URL)

print("="*80)
print("🔍 IDENTIFICATION REMISES LCL À CORRIGER")
print("="*80)

# Récupérer l'exercice 2024
exercice_2024 = session.query(ExerciceComptable).filter_by(annee=2024).first()
if not exercice_2024:
    print("❌ Exercice 2024 non trouvé")
    sys.exit(1)

# Rechercher toutes les écritures de type FRAIS_BANCAIRES
ecritures_fb = session.query(EcritureComptable).filter_by(
    exercice_id=exercice_2024.id,
    type_ecriture='FRAIS_BANCAIRES'
).all()

print(f"\n📊 Total FRAIS_BANCAIRES : {len(ecritures_fb)} écritures")

# Identifier les remises (patterns connus)
remises = []
patterns_remises = ['REMISE', 'VOTRE REM', 'REM LCL', 'REMBT']

for e in ecritures_fb:
    libelle_upper = e.libelle_ecriture.upper()
    if any(pattern in libelle_upper for pattern in patterns_remises):
        remises.append(e)

print(f"\n🎯 Remises LCL identifiées : {len(remises)} écritures")

if not remises:
    print("\n✅ Aucune remise LCL détectée - Rien à corriger")
    sys.exit(0)

# Afficher chaque remise avec détails
print("\n" + "="*80)
print("DÉTAIL DES REMISES À CORRIGER")
print("="*80)

total_remises = Decimal('0')

for i, e in enumerate(remises, 1):
    print(f"\n📌 REMISE #{i}")
    print("-"*80)
    print(f"  ID écriture      : {e.id}")
    print(f"  Numéro           : {e.numero_ecriture}")
    print(f"  Date             : {e.date_ecriture}")
    print(f"  Libellé          : {e.libelle_ecriture}")
    print(f"  Montant          : {e.montant:.2f}€")
    print(f"  Type écriture    : {e.type_ecriture}")

    # Détails des comptes
    cpte_d = session.query(PlanCompte).filter_by(numero_compte=e.compte_debit).first()
    cpte_c = session.query(PlanCompte).filter_by(numero_compte=e.compte_credit).first()

    print(f"\n  Écriture actuelle (INCORRECTE) :")
    print(f"    Débit  {e.compte_debit} ({cpte_d.libelle if cpte_d else '?'})")
    print(f"    Crédit {e.compte_credit} ({cpte_c.libelle if cpte_c else '?'})")
    print(f"    Montant : {e.montant:.2f}€")

    print(f"\n  Écriture correcte (à appliquer) :")
    print(f"    Débit  {e.compte_credit} ({cpte_c.libelle if cpte_c else '?'})")
    print(f"    Crédit {e.compte_debit} ({cpte_d.libelle if cpte_d else '?'})")
    print(f"    Montant : {e.montant:.2f}€")
    print(f"    → Impact : Diminue CHARGES de {e.montant:.2f}€")

    total_remises += Decimal(str(e.montant))

print("\n" + "="*80)
print("📊 SYNTHÈSE")
print("="*80)
print(f"\nNombre de remises  : {len(remises)}")
print(f"Total remises      : {total_remises:.2f}€")
print(f"Impact résultat    : +{total_remises * 2:.2f}€")
print(f"  (car charges diminuent de 2× le montant)")

# Diagnostic de l'écriture actuelle
if remises:
    e_exemple = remises[0]
    cpte_d = session.query(PlanCompte).filter_by(numero_compte=e_exemple.compte_debit).first()

    print("\n" + "="*80)
    print("🔍 DIAGNOSTIC")
    print("="*80)

    if cpte_d and cpte_d.type_compte == 'CHARGE':
        print(f"\n❌ PROBLÈME CONFIRMÉ :")
        print(f"   Les remises sont au débit du compte {e_exemple.compte_debit} ({cpte_d.libelle})")
        print(f"   Type : {cpte_d.type_compte}")
        print(f"   → Cela AUGMENTE les charges au lieu de les DIMINUER")

        print(f"\n✅ CORRECTION REQUISE :")
        print(f"   Inverser l'écriture : Débit 512 / Crédit 627")
        print(f"   → Impact : Solde compte 627 diminue de {total_remises * 2:.2f}€")
        print(f"   → Résultat 2024 augmente de {total_remises * 2:.2f}€")

print("\n" + "="*80)
print("🔧 PLAN DE CORRECTION")
print("="*80)

print("""
MÉTHODE : Contre-passation + Écriture correcte

Pour chaque remise identifiée :

1. CONTRE-PASSATION (annule l'écriture incorrecte)
   - Numéro : {original}-ANNUL
   - Libellé : "Annulation écriture incorrecte - {libellé original}"
   - Débit {compte_credit} / Crédit {compte_debit}
   - Montant : {montant}
   - Type : CORRECTION

2. ÉCRITURE CORRECTE (écriture qui aurait dû être faite)
   - Numéro : {original}-CORR
   - Libellé : "Correction - {libellé original}"
   - Débit 512 / Crédit 627
   - Montant : {montant}
   - Type : FRAIS_BANCAIRES

Résultat net :
- Solde 512 (Banque) : inchangé (débit annulé puis re-débité)
- Solde 627 (Frais bancaires) : diminue de 2× le montant
  (crédit annulé + nouveau crédit = diminution des charges)
- Résultat : augmente de 2× le total des remises
""")

print("\n" + "="*80)
print("📋 ÉCRITURES DE CORRECTION À CRÉER")
print("="*80)

for i, e in enumerate(remises, 1):
    montant = Decimal(str(e.montant))

    print(f"\n--- REMISE #{i} : {e.numero_ecriture} ---")

    print(f"\nÉcriture #1 : CONTRE-PASSATION")
    print(f"  Numéro   : {e.numero_ecriture}-ANNUL")
    print(f"  Date     : {e.date_ecriture}")
    print(f"  Libellé  : Annulation écriture incorrecte - {e.libelle_ecriture}")
    print(f"  Débit    : {e.compte_credit}")
    print(f"  Crédit   : {e.compte_debit}")
    print(f"  Montant  : {montant:.2f}€")
    print(f"  Type     : CORRECTION")

    print(f"\nÉcriture #2 : ÉCRITURE CORRECTE")
    print(f"  Numéro   : {e.numero_ecriture}-CORR")
    print(f"  Date     : {e.date_ecriture}")
    print(f"  Libellé  : Correction - {e.libelle_ecriture}")
    print(f"  Débit    : {e.compte_credit}")  # Normalement 512
    print(f"  Crédit   : {e.compte_debit}")   # Normalement 627
    print(f"  Montant  : {montant:.2f}€")
    print(f"  Type     : FRAIS_BANCAIRES")

print("\n" + "="*80)
print("✅ ANALYSE TERMINÉE")
print("="*80)

print(f"""
Prochaine étape :
  Exécuter le script de correction : python corriger_remises_lcl_2024.py

  Ce script créera {len(remises) * 2} écritures (2 par remise) :
  - {len(remises)} contre-passations
  - {len(remises)} écritures correctes

  Impact final :
  - Résultat 2024 : +{total_remises * 2:.2f}€
  - Charges : -{total_remises * 2:.2f}€
""")

session.close()
