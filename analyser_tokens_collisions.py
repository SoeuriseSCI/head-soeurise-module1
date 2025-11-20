#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANALYSE DES TOKENS ET COLLISIONS
=================================
Vérifie si les tokens stockés en BD correspondent au MD5 des propositions
et identifie les collisions potentielles (même MD5 court pour différentes propositions)
"""

from sqlalchemy import create_engine, text
import os
import json
import hashlib

def analyser_tokens_collisions():
    """
    Analyse toutes les propositions EN_ATTENTE pour :
    1. Vérifier que le token stocké correspond au MD5 des propositions
    2. Identifier les collisions de tokens (même MD5 sur 8 chars)
    """

    # Connexion à la base de données
    DATABASE_URL = os.environ.get('DATABASE_URL', '').replace('postgres://', 'postgresql://')
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        result = conn.execute(text('''
            SELECT id, token, type_evenement, email_subject, propositions_json, created_at
            FROM propositions_en_attente
            WHERE statut = 'EN_ATTENTE'
            ORDER BY created_at DESC
        '''))

        print('═══════════════════════════════════════════════════════════')
        print('ANALYSE DES PROPOSITIONS EN_ATTENTE')
        print('═══════════════════════════════════════════════════════════\n')

        tokens_md5 = {}  # {token_md5: [id1, id2, ...]}
        tokens_invalides = []

        for row in result:
            propositions = row[4]['propositions']

            # Recalculer le MD5
            token_calculated_full = hashlib.md5(
                json.dumps(propositions, sort_keys=True).encode()
            ).hexdigest()
            token_calculated_short = token_calculated_full[:8].upper()

            print(f'ID: {row[0]}')
            print(f'  Token stocké     : {row[1]}')
            print(f'  Token recalculé  : HEAD-{token_calculated_short}')
            print(f'  MD5 complet      : {token_calculated_full}')
            print(f'  Type événement   : {row[2]}')
            print(f'  Sujet email      : {row[3][:60]}...' if row[3] and len(row[3]) > 60 else f'  Sujet email      : {row[3]}')
            print(f'  Créé le          : {row[5]}')
            print(f'  Nb propositions  : {len(propositions)}')

            # Vérifier si match
            token_stocke_normalise = row[1].upper() if row[1] else ''
            token_attendu = f'HEAD-{token_calculated_short}'

            if token_stocke_normalise == token_attendu:
                print(f'  ✅ Token VALIDE (match MD5)')
            else:
                print(f'  ❌ Token INVALIDE (ne match pas MD5)')
                tokens_invalides.append({
                    'id': row[0],
                    'token_stocke': row[1],
                    'token_attendu': token_attendu,
                    'type': row[2]
                })

            # Identifier les collisions potentielles
            if token_calculated_short in tokens_md5:
                print(f'  ⚠️  COLLISION détectée avec ID(s) {tokens_md5[token_calculated_short]}')
                tokens_md5[token_calculated_short].append(row[0])
            else:
                tokens_md5[token_calculated_short] = [row[0]]

            print()

        # Résumé
        print('═══════════════════════════════════════════════════════════')
        print('RÉSUMÉ')
        print('═══════════════════════════════════════════════════════════\n')

        print(f'Total propositions EN_ATTENTE : {len(tokens_md5)}')
        print(f'Tokens invalides : {len(tokens_invalides)}')

        if tokens_invalides:
            print('\n❌ TOKENS INVALIDES DÉTECTÉS :')
            for t in tokens_invalides:
                print(f'  - ID {t["id"]} ({t["type"]}): stocké={t["token_stocke"]}, attendu={t["token_attendu"]}')

        # Identifier les collisions réelles
        collisions_reelles = {k: v for k, v in tokens_md5.items() if len(v) > 1}

        if collisions_reelles:
            print(f'\n⚠️  COLLISIONS DÉTECTÉES : {len(collisions_reelles)}')
            for token, ids in collisions_reelles.items():
                print(f'  - Token HEAD-{token} : {len(ids)} propositions (IDs: {ids})')

                # Afficher les MD5 complets pour voir si vraiment différents
                print(f'    Analyse détaillée :')
                for prop_id in ids:
                    result2 = conn.execute(text('''
                        SELECT propositions_json FROM propositions_en_attente WHERE id = :id
                    '''), {'id': prop_id})
                    row2 = result2.fetchone()
                    if row2:
                        propositions = row2[0]['propositions']
                        md5_complet = hashlib.md5(
                            json.dumps(propositions, sort_keys=True).encode()
                        ).hexdigest()
                        print(f'      ID {prop_id}: MD5 complet = {md5_complet}')
        else:
            print('\n✅ Aucune collision détectée (tous les tokens MD5 sont uniques)')

if __name__ == '__main__':
    analyser_tokens_collisions()
