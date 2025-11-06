#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DÉTECTION DE DOUBLONS - Événements Comptables
==============================================
Mécanisme de détection des événements déjà traités pour éviter les doublons
lors du traitement par phases.

Date: 05/11/2025
Auteur: Module Phase 1 - Accounting Events

PRINCIPE:
---------
Chaque événement comptable reçoit une empreinte digitale (fingerprint) unique
calculée à partir de:
- Date d'opération
- Libellé normalisé
- Montant
- Type d'opération (DEBIT/CREDIT)

Si un événement avec le même fingerprint existe déjà, il est considéré comme doublon.

NORMALISATION DU LIBELLÉ:
-------------------------
Le libellé est normalisé pour ignorer les variations mineures:
- Conversion en minuscules
- Suppression des espaces multiples
- Suppression des caractères spéciaux
- Suppression des dates intégrées
- Suppression des références de transaction
"""

import hashlib
import re
from typing import Dict, Optional
from datetime import datetime
from sqlalchemy import text


class DetecteurDoublons:
    """
    Détecteur de doublons d'événements comptables
    """

    @staticmethod
    def normaliser_libelle(libelle: str) -> str:
        """
        Normalise un libellé pour la comparaison

        Args:
            libelle: Libellé brut extrait du relevé

        Returns:
            Libellé normalisé

        Exemple:
            "VIR SEPA RECU  /DE ULRIK BERGSTEN  /MOTIF Apport compte courant"
            → "vir sepa recu de ulrik bergsten motif apport compte courant"
        """
        if not libelle:
            return ""

        # Conversion en minuscules
        normalized = libelle.lower()

        # Suppression des dates (format JJ/MM/AAAA ou JJ-MM-AAAA)
        normalized = re.sub(r'\d{2}[/-]\d{2}[/-]\d{4}', '', normalized)

        # Suppression des références de transaction (ex: REF:12345678)
        normalized = re.sub(r'ref\s*:\s*\w+', '', normalized)
        normalized = re.sub(r'n[°o]\s*\d+', '', normalized)

        # Suppression des caractères spéciaux sauf espaces
        normalized = re.sub(r'[^\w\s]', ' ', normalized)

        # Suppression des espaces multiples
        normalized = re.sub(r'\s+', ' ', normalized)

        # Trim
        normalized = normalized.strip()

        return normalized

    @staticmethod
    def calculer_score_qualite(evenement: Dict) -> int:
        """
        Calcule un score de qualité pour un événement
        Plus le score est élevé, plus l'événement contient de détails

        Args:
            evenement: Dictionnaire contenant au moins 'libelle'

        Returns:
            Score de qualité (0-100)

        Critères:
            - Longueur du libellé (max 40 points)
            - Présence de codes ISIN (20 points)
            - Présence de références numériques (10 points)
            - Mots-clés de détail (30 points max):
                * "au cours de" : 10 points
                * "code" : 5 points
                * "achat de" : 5 points
                * "frais" : 5 points
                * "reference" / "ref" : 5 points
        """
        libelle = evenement.get('libelle', '').lower()
        score = 0

        # 1. Longueur du libellé (max 40 points)
        #    0-50 chars: 10 pts, 51-100: 20 pts, 101-150: 30 pts, 150+: 40 pts
        longueur = len(libelle)
        if longueur > 150:
            score += 40
        elif longueur > 100:
            score += 30
        elif longueur > 50:
            score += 20
        else:
            score += 10

        # 2. Présence de code ISIN (format: 2 lettres + 10 chiffres, ex: LU1781541179)
        if re.search(r'\b[A-Z]{2}\d{10}\b', libelle.upper()):
            score += 20

        # 3. Présence de références numériques longues (8+ chiffres)
        if re.search(r'\d{8,}', libelle):
            score += 10

        # 4. Mots-clés de détail
        if 'au cours de' in libelle:
            score += 10
        if 'code' in libelle:
            score += 5
        if 'achat de' in libelle or 'vente de' in libelle:
            score += 5
        if 'frais' in libelle:
            score += 5
        if 'reference' in libelle or 'ref' in libelle:
            score += 5

        return min(score, 100)  # Limiter à 100

    @staticmethod
    def calculer_fingerprint(evenement: Dict) -> str:
        """
        Calcule l'empreinte digitale (fingerprint) d'un événement

        Args:
            evenement: Dictionnaire contenant:
                - date_operation (str ou date): Date de l'opération
                - libelle (str): Libellé de l'opération
                - montant (float ou Decimal): Montant
                - type_operation (str): DEBIT ou CREDIT

        Returns:
            Empreinte MD5 en hexadécimal (64 caractères)

        Exemple:
            {
                'date_operation': '2024-01-15',
                'libelle': 'PRLV SEPA COVEA RISKS',
                'montant': 87.57,
                'type_operation': 'DEBIT'
            }
            → "a3f5e9c2d1b4..."
        """
        # Extraire les données
        date_op = evenement.get('date_operation', '')
        if isinstance(date_op, datetime):
            date_op = date_op.strftime('%Y-%m-%d')
        elif hasattr(date_op, 'isoformat'):
            date_op = date_op.isoformat()

        libelle = evenement.get('libelle', '')
        montant = float(evenement.get('montant', 0))
        type_op = evenement.get('type_operation', '')

        # Normaliser le libellé
        libelle_norm = DetecteurDoublons.normaliser_libelle(libelle)

        # Construire la chaîne à hasher
        # Format: date|libelle_norm|montant|type
        data = f"{date_op}|{libelle_norm}|{montant:.2f}|{type_op}"

        # Calculer le MD5
        fingerprint = hashlib.md5(data.encode('utf-8')).hexdigest()

        return fingerprint

    @staticmethod
    def verifier_doublon(session, evenement: Dict) -> Optional[Dict]:
        """
        Vérifie si un événement est un doublon d'un événement déjà traité

        STRATÉGIE:
        1. Vérification stricte par fingerprint (date+libellé+montant+type)
        2. Si pas trouvé: vérification souple par date+montant (pour SCPI, virements, etc.)

        Args:
            session: Session SQLAlchemy
            evenement: Dictionnaire de l'événement à vérifier

        Returns:
            Dict avec informations du doublon si trouvé, None sinon

        Exemple retour si doublon trouvé:
            {
                'est_doublon': True,
                'evenement_id': 42,
                'fingerprint': 'a3f5e9c2...',
                'phase_traitement': 1,
                'date_traitement': datetime(2024, 11, 5, 10, 30),
                'methode': 'fingerprint' ou 'date_montant'
            }
        """
        # 1. Vérification stricte par fingerprint
        fingerprint = DetecteurDoublons.calculer_fingerprint(evenement)

        result = session.execute(
            text("""
                SELECT id, fingerprint, phase_traitement, traite_at
                FROM evenements_comptables
                WHERE fingerprint = :fingerprint
                LIMIT 1
            """),
            {'fingerprint': fingerprint}
        )

        row = result.fetchone()

        if row:
            return {
                'est_doublon': True,
                'evenement_id': row[0],
                'fingerprint': row[1],
                'phase_traitement': row[2],
                'date_traitement': row[3],
                'methode': 'fingerprint'
            }

        # 2. Vérification souple par date+montant (pour doublons avec libellés différents)
        date_op = evenement.get('date_operation', '')
        if isinstance(date_op, datetime):
            date_op = date_op.strftime('%Y-%m-%d')
        elif hasattr(date_op, 'isoformat'):
            date_op = date_op.isoformat()

        montant = float(evenement.get('montant', 0))
        type_op = evenement.get('type_operation', '')

        result = session.execute(
            text("""
                SELECT id, fingerprint, phase_traitement, traite_at
                FROM evenements_comptables
                WHERE date_operation = :date_op::date
                  AND ABS(montant - :montant) < 0.01
                  AND type_operation = :type_op
                ORDER BY created_at ASC
                LIMIT 1
            """),
            {
                'date_op': date_op,
                'montant': montant,
                'type_op': type_op
            }
        )

        row = result.fetchone()

        if row:
            return {
                'est_doublon': True,
                'evenement_id': row[0],
                'fingerprint': row[1],
                'phase_traitement': row[2],
                'date_traitement': row[3],
                'methode': 'date_montant'
            }

        return None

    @staticmethod
    def marquer_evenement(session, evenement_id: int, fingerprint: str, phase: int):
        """
        Marque un événement comme traité avec son fingerprint et sa phase

        Args:
            session: Session SQLAlchemy
            evenement_id: ID de l'événement
            fingerprint: Empreinte calculée
            phase: Numéro de phase (1, 2, 3)
        """
        session.execute(
            text("""
                UPDATE evenements_comptables
                SET fingerprint = :fingerprint,
                    phase_traitement = :phase,
                    traite_at = NOW(),
                    updated_at = NOW()
                WHERE id = :id
            """),
            {
                'fingerprint': fingerprint,
                'phase': phase,
                'id': evenement_id
            }
        )
        session.commit()

    @staticmethod
    def obtenir_statistiques_doublons(session) -> Dict:
        """
        Obtient des statistiques sur les doublons détectés

        Args:
            session: Session SQLAlchemy

        Returns:
            Dictionnaire avec les statistiques
        """
        # Compter les événements par phase
        result = session.execute(text("""
            SELECT
                phase_traitement,
                COUNT(*) as nb_evenements
            FROM evenements_comptables
            WHERE fingerprint IS NOT NULL
            GROUP BY phase_traitement
            ORDER BY phase_traitement
        """))

        stats_phases = {}
        for row in result:
            phase = row[0]
            count = row[1]
            if phase:
                stats_phases[f"Phase {phase}"] = count
            else:
                stats_phases["Non traités"] = count

        # Compter les événements sans fingerprint
        result = session.execute(text("""
            SELECT COUNT(*)
            FROM evenements_comptables
            WHERE fingerprint IS NULL
        """))
        count_sans_fingerprint = result.fetchone()[0]

        # Vérifier s'il y a des doublons (même fingerprint, même phase)
        result = session.execute(text("""
            SELECT fingerprint, COUNT(*) as nb
            FROM evenements_comptables
            WHERE fingerprint IS NOT NULL
            GROUP BY fingerprint
            HAVING COUNT(*) > 1
        """))
        doublons_detectes = result.fetchall()

        return {
            'total_evenements': sum(stats_phases.values()) + count_sans_fingerprint,
            'par_phase': stats_phases,
            'sans_fingerprint': count_sans_fingerprint,
            'doublons_potentiels': len(doublons_detectes)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# TESTS UNITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def test_normalisation():
    """Tests de la fonction de normalisation"""
    print("🧪 Tests de normalisation du libellé")
    print()

    tests = [
        (
            "VIR SEPA RECU  /DE ULRIK BERGSTEN  /MOTIF Apport compte courant",
            "vir sepa recu de ulrik bergsten motif apport compte courant"
        ),
        (
            "PRLV SEPA COVEA RISKS REF:12345",
            "prlv sepa covea risks"
        ),
        (
            "FRAIS TENUE DE COMPTE 01/01/2024",
            "frais tenue de compte"
        ),
        (
            "CB MONOPRIX    N°123456",
            "cb monoprix"
        ),
    ]

    for libelle_brut, attendu in tests:
        resultat = DetecteurDoublons.normaliser_libelle(libelle_brut)
        status = "✅" if resultat == attendu else "❌"
        print(f"{status} '{libelle_brut[:50]}'")
        print(f"   → '{resultat}'")
        if resultat != attendu:
            print(f"   Attendu: '{attendu}'")
        print()


def test_fingerprint():
    """Tests du calcul de fingerprint"""
    print("🧪 Tests de calcul de fingerprint")
    print()

    # Deux événements identiques doivent avoir le même fingerprint
    event1 = {
        'date_operation': '2024-01-15',
        'libelle': 'PRLV SEPA COVEA RISKS',
        'montant': 87.57,
        'type_operation': 'DEBIT'
    }

    event2 = {
        'date_operation': '2024-01-15',
        'libelle': 'PRLV SEPA COVEA RISKS REF:12345',  # Référence différente
        'montant': 87.57,
        'type_operation': 'DEBIT'
    }

    fp1 = DetecteurDoublons.calculer_fingerprint(event1)
    fp2 = DetecteurDoublons.calculer_fingerprint(event2)

    print(f"Event 1 fingerprint: {fp1}")
    print(f"Event 2 fingerprint: {fp2}")
    print()

    if fp1 == fp2:
        print("✅ Les deux événements ont le même fingerprint (normal, REF ignorée)")
    else:
        print("❌ Les fingerprints sont différents (anormal)")

    print()

    # Deux événements différents doivent avoir des fingerprints différents
    event3 = {
        'date_operation': '2024-01-16',  # Date différente
        'libelle': 'PRLV SEPA COVEA RISKS',
        'montant': 87.57,
        'type_operation': 'DEBIT'
    }

    fp3 = DetecteurDoublons.calculer_fingerprint(event3)
    print(f"Event 3 fingerprint: {fp3}")
    print()

    if fp1 != fp3:
        print("✅ Les fingerprints sont différents (normal, dates différentes)")
    else:
        print("❌ Les fingerprints sont identiques (anormal)")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("=" * 80)
    print("DÉTECTION DE DOUBLONS - Tests Unitaires")
    print("=" * 80)
    print()

    test_normalisation()
    print("─" * 80)
    print()
    test_fingerprint()

    print("=" * 80)
    print("Tests terminés")
    print("=" * 80)
