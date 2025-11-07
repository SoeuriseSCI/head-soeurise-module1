#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nettoie les événements orphelins (sans propositions en attente)

LOGIQUE:
- Les événements ne sont qu'un cache temporaire
- On garde SEULEMENT ceux liés aux propositions en attente
- Dès validation/rejet → suppression
"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

if not DATABASE_URL:
    print("❌ Variable DATABASE_URL non définie")
    exit(1)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

print("=" * 80)
print("NETTOYAGE ÉVÉNEMENTS ORPHELINS")
print("=" * 80)
print()

# 1. Compter les événements actuels
result = session.execute(text("SELECT COUNT(*) FROM evenements_comptables"))
total_avant = result.fetchone()[0]
print(f"📊 Événements avant nettoyage: {total_avant}")

# 2. Récupérer les IDs d'événements liés aux propositions en attente
result = session.execute(text("""
    SELECT DISTINCT numero_ecriture
    FROM propositions_en_attente
"""))
numeros_evenements = [row[0] for row in result.fetchall()]

print(f"⏳ Propositions en attente: {len(set(numeros_evenements))}")

# Extraire les IDs d'événements depuis les numeros (format: EVT-123)
ids_a_garder = []
for numero in numeros_evenements:
    if numero.startswith('EVT-'):
        try:
            evt_id = int(numero.split('-')[1])
            ids_a_garder.append(evt_id)
        except:
            pass

ids_a_garder = list(set(ids_a_garder))
print(f"🔒 Événements à conserver: {len(ids_a_garder)}")
print()

# 3. Supprimer les événements orphelins
if ids_a_garder:
    placeholders = ','.join(str(id) for id in ids_a_garder)
    query = f"""
        DELETE FROM evenements_comptables
        WHERE id NOT IN ({placeholders})
    """
else:
    # Si aucune proposition, supprimer TOUT
    query = "DELETE FROM evenements_comptables"

result = session.execute(text(query))
session.commit()

nb_supprimes = result.rowcount

print(f"🗑️  Événements supprimés: {nb_supprimes}")

# 4. Vérification finale
result = session.execute(text("SELECT COUNT(*) FROM evenements_comptables"))
total_apres = result.fetchone()[0]
print(f"✅ Événements après nettoyage: {total_apres}")

# 5. Détails des événements conservés
if total_apres > 0:
    print()
    print("📋 Événements conservés:")
    result = session.execute(text("""
        SELECT id, date_operation, libelle, montant, type_evenement
        FROM evenements_comptables
        ORDER BY id
    """))
    for row in result.fetchall():
        print(f"   #{row[0]}: {row[1]} | {row[4]} | {row[2][:50]} | {row[3]}€")

print()
print("=" * 80)
print(f"✅ NETTOYAGE TERMINÉ: {nb_supprimes} supprimés, {total_apres} conservés")
print("=" * 80)

session.close()
