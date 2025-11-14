#!/usr/bin/env python3
"""
Réinitialisation Comptabilité 2024
===================================

Supprime TOUTES les écritures de flux 2024, mais conserve :
- Bilan d'ouverture 2024 (11 écritures type INIT_BILAN_2023)
- Prêts immobiliers (2 prêts + 468 échéances)

Permet de retraiter les PDFs avec les corrections :
- Remises LCL : Débit 512 / Crédit 627 (réduction charges)
- Remboursements capital : Débit 161 (au lieu de 164)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models_module2 import get_session, EcritureComptable, ExerciceComptable
from sqlalchemy import text

DATABASE_URL = os.getenv('DATABASE_URL')
session = get_session(DATABASE_URL)

print("="*80)
print("🔄 RÉINITIALISATION COMPTABILITÉ 2024")
print("="*80)

# Récupérer l'exercice 2024
exercice_2024 = session.query(ExerciceComptable).filter_by(annee=2024).first()
if not exercice_2024:
    print("❌ Exercice 2024 non trouvé")
    sys.exit(1)

print(f"\n📅 Exercice 2024 : ID={exercice_2024.id}, Statut={exercice_2024.statut}")

# Compter les écritures actuelles
nb_total = session.query(EcritureComptable).filter_by(exercice_id=exercice_2024.id).count()
nb_ouverture = session.query(EcritureComptable).filter_by(
    exercice_id=exercice_2024.id,
    type_ecriture='INIT_BILAN_2023'
).count()
nb_flux = nb_total - nb_ouverture

print(f"\n📊 État actuel :")
print(f"   Total écritures : {nb_total}")
print(f"   Bilan d'ouverture (INIT_BILAN_2023) : {nb_ouverture}")
print(f"   Flux 2024 : {nb_flux}")

# Compter les autres données
result = session.execute(text("""
    SELECT
        (SELECT COUNT(*) FROM evenements_comptables WHERE exercice_id = :ex_id) as nb_evt,
        (SELECT COUNT(*) FROM propositions_en_attente WHERE exercice_id = :ex_id) as nb_prop,
        (SELECT COUNT(*) FROM prets_immobiliers) as nb_prets,
        (SELECT COUNT(*) FROM echeances_prets) as nb_ech
"""), {'ex_id': exercice_2024.id})
row = result.fetchone()
nb_evt = row[0]
nb_prop = row[1]
nb_prets = row[2]
nb_ech = row[3]

print(f"\n📊 Autres données :")
print(f"   Événements comptables 2024 : {nb_evt}")
print(f"   Propositions en attente 2024 : {nb_prop}")
print(f"   Prêts immobiliers : {nb_prets}")
print(f"   Échéances prêts : {nb_ech}")

# Afficher détails par type d'écriture
print(f"\n📋 Détail écritures flux 2024 par type :")
result = session.execute(text("""
    SELECT type_ecriture, COUNT(*) as nb
    FROM ecritures_comptables
    WHERE exercice_id = :ex_id
      AND type_ecriture != 'INIT_BILAN_2023'
    GROUP BY type_ecriture
    ORDER BY nb DESC
"""), {'ex_id': exercice_2024.id})

for row in result:
    print(f"   {row[0]:30s} : {row[1]}")

# Demander confirmation
print("\n" + "="*80)
print("⚠️  CONFIRMATION REQUISE")
print("="*80)
print(f"""
Cette opération va SUPPRIMER :

✅ CONSERVER :
- Bilan d'ouverture 2024 : {nb_ouverture} écritures (INIT_BILAN_2023)
- Prêts immobiliers : {nb_prets} prêts + {nb_ech} échéances

❌ SUPPRIMER :
- Écritures de flux 2024 : {nb_flux} écritures
- Événements comptables 2024 : {nb_evt} événements
- Propositions en attente 2024 : {nb_prop} propositions

Après cette opération, vous devrez RETRAITER les PDFs T1-T3 2024.

Êtes-vous sûr de vouloir continuer ?
""")

reponse = input("Tapez 'OUI' pour confirmer : ")
if reponse.upper() != 'OUI':
    print("\n❌ Opération annulée par l'utilisateur")
    session.close()
    sys.exit(0)

print("\n" + "="*80)
print("🗑️  SUPPRESSION EN COURS")
print("="*80)

try:
    # 1. Supprimer écritures de flux 2024 (sauf INIT_BILAN_2023)
    print(f"\n1️⃣ Suppression écritures de flux 2024...")
    nb_deleted = session.execute(text("""
        DELETE FROM ecritures_comptables
        WHERE exercice_id = :ex_id
          AND type_ecriture != 'INIT_BILAN_2023'
    """), {'ex_id': exercice_2024.id}).rowcount
    print(f"   ✅ {nb_deleted} écritures supprimées")

    # 2. Supprimer événements comptables 2024
    print(f"\n2️⃣ Suppression événements comptables 2024...")
    nb_deleted = session.execute(text("""
        DELETE FROM evenements_comptables
        WHERE exercice_id = :ex_id
    """), {'ex_id': exercice_2024.id}).rowcount
    print(f"   ✅ {nb_deleted} événements supprimés")

    # 3. Supprimer propositions en attente 2024
    print(f"\n3️⃣ Suppression propositions en attente 2024...")
    nb_deleted = session.execute(text("""
        DELETE FROM propositions_en_attente
        WHERE exercice_id = :ex_id
    """), {'ex_id': exercice_2024.id}).rowcount
    print(f"   ✅ {nb_deleted} propositions supprimées")

    # Commit
    print(f"\n⚠️  Commit en cours...")
    session.commit()
    print("✅ Commit réussi")

except Exception as ex:
    print(f"\n❌ ERREUR : {ex}")
    print("⚠️  Rollback en cours...")
    session.rollback()
    session.close()
    sys.exit(1)

# Vérification post-suppression
print("\n" + "="*80)
print("📊 VÉRIFICATION POST-SUPPRESSION")
print("="*80)

nb_total_apres = session.query(EcritureComptable).filter_by(exercice_id=exercice_2024.id).count()
nb_ouverture_apres = session.query(EcritureComptable).filter_by(
    exercice_id=exercice_2024.id,
    type_ecriture='INIT_BILAN_2023'
).count()

result = session.execute(text("""
    SELECT
        (SELECT COUNT(*) FROM evenements_comptables WHERE exercice_id = :ex_id) as nb_evt,
        (SELECT COUNT(*) FROM propositions_en_attente WHERE exercice_id = :ex_id) as nb_prop
"""), {'ex_id': exercice_2024.id})
row = result.fetchone()
nb_evt_apres = row[0]
nb_prop_apres = row[1]

print(f"\nÉcritures comptables 2024 : {nb_total_apres}")
print(f"  - Bilan d'ouverture : {nb_ouverture_apres}")
print(f"  - Flux : {nb_total_apres - nb_ouverture_apres}")
print(f"\nÉvénements comptables 2024 : {nb_evt_apres}")
print(f"Propositions en attente 2024 : {nb_prop_apres}")

if nb_total_apres == nb_ouverture_apres and nb_evt_apres == 0 and nb_prop_apres == 0:
    print("\n✅ Réinitialisation réussie !")
else:
    print("\n⚠️  Attention : Il reste des données !")

print("\n" + "="*80)
print("✅ RÉINITIALISATION TERMINÉE")
print("="*80)

print(f"""
État final :
- Bilan d'ouverture 2024 : {nb_ouverture_apres} écritures ✅
- Flux 2024 : {nb_total_apres - nb_ouverture_apres} écritures (attendu : 0)
- Événements comptables : {nb_evt_apres} (attendu : 0)
- Propositions en attente : {nb_prop_apres} (attendu : 0)

📋 PROCHAINES ÉTAPES :

1. Retraiter les PDFs T1-T3 2024 :
   python extracteur_intelligent.py

   OU via l'interface web (si disponible)

2. Vérifier les nouvelles écritures :
   - Remises LCL : Débit 512 / Crédit 627 ✅
   - Remboursements capital : Débit 161 / Crédit 512 ✅

3. Reconstruire les états financiers :
   python construire_etats_financiers_2024.py

4. Vérifier l'équilibre du bilan
""")

session.close()
