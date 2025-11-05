#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIGRATION - Enrichissement Événements Comptables
================================================
Ajoute les colonnes nécessaires pour la gestion complète des événements comptables
et crée les nouvelles tables pour le portefeuille et comptes courants.

Date: 05/11/2025
Auteur: Module Phase 1 - Accounting Events

MODIFICATIONS:
- Enrichissement table evenements_comptables
- Création table portefeuille_valeurs_mobilieres
- Création table mouvements_portefeuille
- Création table comptes_courants_associes
- Création table mouvements_comptes_courants
"""

import os
import sys
from sqlalchemy import (
    Column, Integer, String, Numeric, Date, DateTime, Boolean,
    Text, ForeignKey, UniqueConstraint, Index, text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from datetime import datetime

# Configuration
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("❌ ERREUR: Variable d'environnement DATABASE_URL non définie")
    sys.exit(1)

# Fix Render PostgreSQL URL
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

Base = declarative_base()

# ═══════════════════════════════════════════════════════════════════════════════
# NOUVELLES TABLES
# ═══════════════════════════════════════════════════════════════════════════════

class PortefeuilleValeursMobilieres(Base):
    """
    Suivi du portefeuille de valeurs mobilières (ETF, Actions)
    Enregistre les positions et leur valeur comptable (coût d'acquisition)
    """
    __tablename__ = 'portefeuille_valeurs_mobilieres'

    id = Column(Integer, primary_key=True)

    # Identification titre
    code_isin = Column(String(20))  # Code ISIN international
    code_ticker = Column(String(20))  # Ticker (ex: AMZN, IWDA.AS)
    libelle = Column(String(255), nullable=False)  # Nom complet
    type_valeur = Column(String(50), nullable=False)  # ETF, ACTION, OBLIGATION

    # Position actuelle
    quantite = Column(Numeric(15, 4), nullable=False, default=0)  # Nombre de titres
    prix_moyen_acquisition = Column(Numeric(15, 4), nullable=False)  # PRU (Prix de Revient Unitaire)
    valeur_comptable = Column(Numeric(15, 2), nullable=False)  # Quantité × PRU

    # Compte comptable
    compte_comptable = Column(String(10), nullable=False)  # Ex: 503 (Actions), 506 (ETF)

    # Métadonnées
    date_premiere_acquisition = Column(Date, nullable=False)
    date_derniere_operation = Column(Date)
    courtier = Column(String(100))  # Ex: Degiro, Interactive Brokers

    actif = Column(Boolean, default=True)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<PortefeuilleVM({self.libelle}: {self.quantite} × {self.prix_moyen_acquisition}€)>"


class MouvementPortefeuille(Base):
    """
    Historique des mouvements sur valeurs mobilières (achats/ventes)
    Permet de tracer toutes les opérations et de recalculer le PRU
    """
    __tablename__ = 'mouvements_portefeuille'

    id = Column(Integer, primary_key=True)

    # Lien avec le titre
    portefeuille_id = Column(Integer, ForeignKey('portefeuille_valeurs_mobilieres.id'), nullable=False)

    # Type d'opération
    type_mouvement = Column(String(20), nullable=False)  # ACHAT, VENTE, SPLIT, FUSION
    date_operation = Column(Date, nullable=False)

    # Détails opération
    quantite = Column(Numeric(15, 4), nullable=False)  # Positif pour achat, négatif pour vente
    prix_unitaire = Column(Numeric(15, 4), nullable=False)  # Prix d'exécution
    montant_total = Column(Numeric(15, 2), nullable=False)  # Quantité × Prix + Frais
    frais = Column(Numeric(15, 2), default=0)  # Frais de courtage

    # Impact comptable
    nouveau_pru = Column(Numeric(15, 4))  # PRU après cette opération
    nouvelle_quantite = Column(Numeric(15, 4))  # Quantité totale après opération
    plus_ou_moins_value = Column(Numeric(15, 2))  # Si vente: réalisé

    # Source
    source_evenement_id = Column(Integer, ForeignKey('evenements_comptables.id'))
    ecriture_comptable_id = Column(Integer, ForeignKey('ecritures_comptables.id'))

    # Métadonnées
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_portefeuille_date', 'portefeuille_id', 'date_operation'),
    )

    def __repr__(self):
        return f"<MouvementPortefeuille({self.type_mouvement} {self.quantite} @ {self.prix_unitaire}€)>"


class ComptesCourantsAssocies(Base):
    """
    Suivi des comptes courants d'associés
    Enregistre les apports et retraits des associés
    """
    __tablename__ = 'comptes_courants_associes'

    id = Column(Integer, primary_key=True)

    # Identification associé
    nom_associe = Column(String(255), nullable=False, unique=True)  # Ex: "Ulrik Bergsten"
    compte_comptable = Column(String(10), nullable=False)  # Ex: 455100 (CC Ulrik)

    # Solde actuel
    solde_actuel = Column(Numeric(15, 2), nullable=False, default=0)

    # Historique
    date_ouverture = Column(Date, nullable=False)
    date_derniere_operation = Column(Date)

    # Métadonnées
    actif = Column(Boolean, default=True)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<ComptesCourantsAssocies({self.nom_associe}: {self.solde_actuel}€)>"


class MouvementCompteCourant(Base):
    """
    Historique des mouvements sur comptes courants d'associés
    """
    __tablename__ = 'mouvements_comptes_courants'

    id = Column(Integer, primary_key=True)

    # Lien avec le compte courant
    compte_courant_id = Column(Integer, ForeignKey('comptes_courants_associes.id'), nullable=False)

    # Type d'opération
    type_mouvement = Column(String(20), nullable=False)  # APPORT, RETRAIT, REMUNERATION, REMBOURSEMENT
    date_operation = Column(Date, nullable=False)

    # Montant
    montant = Column(Numeric(15, 2), nullable=False)
    nouveau_solde = Column(Numeric(15, 2), nullable=False)  # Solde après opération

    # Source
    source_evenement_id = Column(Integer, ForeignKey('evenements_comptables.id'))
    ecriture_comptable_id = Column(Integer, ForeignKey('ecritures_comptables.id'))

    # Métadonnées
    libelle = Column(String(255))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_cc_date', 'compte_courant_id', 'date_operation'),
    )

    def __repr__(self):
        return f"<MouvementCompteCourant({self.type_mouvement} {self.montant}€ → {self.nouveau_solde}€)>"


# ═══════════════════════════════════════════════════════════════════════════════
# FONCTION DE MIGRATION
# ═══════════════════════════════════════════════════════════════════════════════

def migrate_database():
    """
    Applique les migrations à la base de données
    """
    print("🔧 DÉBUT DE LA MIGRATION")
    print(f"📊 Base de données: {DATABASE_URL[:50]}...")
    print()

    engine = create_engine(DATABASE_URL, echo=False)

    with engine.connect() as conn:
        # ═══════════════════════════════════════════════════════════════
        # ÉTAPE 1: Enrichir la table evenements_comptables
        # ═══════════════════════════════════════════════════════════════
        print("📝 ÉTAPE 1: Enrichissement table evenements_comptables")

        # Vérifier si les colonnes existent déjà
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'evenements_comptables'
        """))
        existing_columns = [row[0] for row in result]

        # Ajouter les nouvelles colonnes si elles n'existent pas
        new_columns = [
            ("date_operation", "DATE", "Date réelle de l'opération (extraite du PDF)"),
            ("libelle", "VARCHAR(500)", "Libellé de l'opération (extrait du relevé)"),
            ("libelle_normalise", "VARCHAR(500)", "Libellé normalisé pour comparaison"),
            ("montant", "NUMERIC(15, 2)", "Montant de l'opération"),
            ("type_operation", "VARCHAR(20)", "Type: DEBIT ou CREDIT"),
            ("fingerprint", "VARCHAR(64)", "Empreinte MD5 pour détection doublons"),
            ("phase_traitement", "INTEGER", "Phase ayant traité l'événement (1, 2, 3)"),
        ]

        for col_name, col_type, col_desc in new_columns:
            if col_name not in existing_columns:
                try:
                    conn.execute(text(f"ALTER TABLE evenements_comptables ADD COLUMN {col_name} {col_type}"))
                    conn.commit()
                    print(f"  ✅ Colonne '{col_name}' ajoutée ({col_desc})")
                except Exception as e:
                    print(f"  ⚠️  Colonne '{col_name}' non ajoutée: {e}")
            else:
                print(f"  ℹ️  Colonne '{col_name}' existe déjà")

        # Ajouter contrainte unique sur fingerprint
        try:
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_fingerprint_unique ON evenements_comptables(fingerprint)"))
            conn.commit()
            print("  ✅ Index unique sur 'fingerprint' créé")
        except Exception as e:
            print(f"  ⚠️  Index fingerprint non créé: {e}")

        # Ajouter index sur phase_traitement
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_phase_traitement ON evenements_comptables(phase_traitement)"))
            conn.commit()
            print("  ✅ Index sur 'phase_traitement' créé")
        except Exception as e:
            print(f"  ⚠️  Index phase_traitement non créé: {e}")

        print()

        # ═══════════════════════════════════════════════════════════════
        # ÉTAPE 2: Créer les nouvelles tables
        # ═══════════════════════════════════════════════════════════════
        print("📝 ÉTAPE 2: Création des nouvelles tables")

        # Créer toutes les nouvelles tables
        Base.metadata.create_all(engine)
        print("  ✅ Tables créées/vérifiées:")
        print("     - portefeuille_valeurs_mobilieres")
        print("     - mouvements_portefeuille")
        print("     - comptes_courants_associes")
        print("     - mouvements_comptes_courants")
        print()

    print("✅ MIGRATION TERMINÉE")
    print()

    # Afficher statistiques
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM evenements_comptables"))
        count_events = result.fetchone()[0]
        print(f"📊 Statistiques:")
        print(f"   - Événements comptables: {count_events}")
        print()


def rollback_migration():
    """
    ROLLBACK: Annule les migrations (pour tests)
    ⚠️ ATTENTION: Cette fonction supprime les colonnes et tables créées
    """
    print("⚠️  ROLLBACK DE LA MIGRATION")
    print()

    response = input("Êtes-vous sûr de vouloir annuler la migration? (oui/non): ")
    if response.lower() != 'oui':
        print("❌ Rollback annulé")
        return

    engine = create_engine(DATABASE_URL, echo=False)

    with engine.connect() as conn:
        print("🗑️  Suppression des colonnes ajoutées...")

        columns_to_drop = [
            'date_operation',
            'libelle',
            'libelle_normalise',
            'montant',
            'type_operation',
            'fingerprint',
            'phase_traitement'
        ]

        for col_name in columns_to_drop:
            try:
                conn.execute(text(f"ALTER TABLE evenements_comptables DROP COLUMN IF EXISTS {col_name}"))
                conn.commit()
                print(f"  ✅ Colonne '{col_name}' supprimée")
            except Exception as e:
                print(f"  ⚠️  Colonne '{col_name}' non supprimée: {e}")

        print()
        print("🗑️  Suppression des nouvelles tables...")

        tables_to_drop = [
            'mouvements_comptes_courants',
            'mouvements_portefeuille',
            'comptes_courants_associes',
            'portefeuille_valeurs_mobilieres'
        ]

        for table_name in tables_to_drop:
            try:
                conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
                conn.commit()
                print(f"  ✅ Table '{table_name}' supprimée")
            except Exception as e:
                print(f"  ⚠️  Table '{table_name}' non supprimée: {e}")

        print()

    print("✅ ROLLBACK TERMINÉ")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--rollback':
        rollback_migration()
    else:
        migrate_database()
