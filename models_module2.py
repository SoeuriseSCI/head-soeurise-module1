#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MODULE 2 - MODELES SQLALCHEMY (ORM)
===============================
Représente les tables comptables en Python

CORRECTION: Encodage UTF-8 + noms de tables vérifiés
"""

from sqlalchemy import (
    Column, Integer, String, Numeric, Date, DateTime, Boolean,
    Text, ForeignKey, Enum, CheckConstraint, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine
from datetime import datetime
import enum

Base = declarative_base()


# ═══════════════════════════════════════════════════════════════════════════════
# EXERCICES COMPTABLES
# ═══════════════════════════════════════════════════════════════════════════════

class ExerciceComptable(Base):
    __tablename__ = 'exercices_comptables'
    
    id = Column(Integer, primary_key=True)
    annee = Column(Integer, nullable=False, unique=True)
    date_debut = Column(Date, nullable=False)
    date_fin = Column(Date, nullable=False)
    statut = Column(String(50), default='OUVERT')  # OUVERT, CLOTURE, VALIDE
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    ecritures = relationship("EcritureComptable", back_populates="exercice")
    calculs_amortissements = relationship("CalculAmortissement", back_populates="exercice")
    balances = relationship("BalanceMensuelle", back_populates="exercice")
    rapports = relationship("RapportComptable", back_populates="exercice")
    
    def __repr__(self):
        return f"<ExerciceComptable(annee={self.annee}, statut={self.statut})>"


# ═══════════════════════════════════════════════════════════════════════════════
# PLAN DE COMPTES
# ═══════════════════════════════════════════════════════════════════════════════

class PlanCompte(Base):
    __tablename__ = 'plans_comptes'
    
    id = Column(Integer, primary_key=True)
    numero_compte = Column(String(10), nullable=False, unique=True)
    libelle = Column(String(255), nullable=False)
    type_compte = Column(String(50), nullable=False)  # ACTIF, PASSIF, PRODUIT, CHARGE, DIFF
    classe = Column(Integer)  # 1-9
    description = Column(Text)
    actif = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    ecritures_debit = relationship("EcritureComptable", foreign_keys="EcritureComptable.compte_debit", back_populates="compte_debit_ref")
    ecritures_credit = relationship("EcritureComptable", foreign_keys="EcritureComptable.compte_credit", back_populates="compte_credit_ref")
    immobilisations = relationship("Immobilisation", foreign_keys="Immobilisation.compte_immobilisation", back_populates="compte_immo")
    
    def __repr__(self):
        return f"<PlanCompte({self.numero_compte}: {self.libelle})>"


# ═══════════════════════════════════════════════════════════════════════════════
# ECRITURES COMPTABLES
# ═══════════════════════════════════════════════════════════════════════════════

class EcritureComptable(Base):
    __tablename__ = 'ecritures_comptables'
    
    id = Column(Integer, primary_key=True)
    exercice_id = Column(Integer, ForeignKey('exercices_comptables.id'), nullable=False)
    
    # Identifiant unique
    numero_ecriture = Column(String(50), nullable=False)
    date_ecriture = Column(Date, nullable=False)
    date_enregistrement = Column(DateTime, default=datetime.utcnow)
    
    # Traçabilité EMAIL (DEBUG)
    source_email_id = Column(String(255))
    source_email_date = Column(DateTime)
    source_email_from = Column(String(255))
    
    # Contenu
    libelle_ecriture = Column(String(255), nullable=False)
    type_ecriture = Column(String(50))  # LOYER, CHARGE, AMORTISSEMENT, PAIEMENT, ENCAISSEMENT, AUTRE
    
    # Comptes
    compte_debit = Column(String(10), ForeignKey('plans_comptes.numero_compte'), nullable=False)
    compte_credit = Column(String(10), ForeignKey('plans_comptes.numero_compte'), nullable=False)
    montant = Column(Numeric(12, 2), nullable=False)
    
    # Metadata
    piece_jointe = Column(String(255))
    notes = Column(Text)
    valide = Column(Boolean, default=False)
    validee_par = Column(String(255))
    validee_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    exercice = relationship("ExerciceComptable", back_populates="ecritures")
    compte_debit_ref = relationship("PlanCompte", foreign_keys=[compte_debit], back_populates="ecritures_debit")
    compte_credit_ref = relationship("PlanCompte", foreign_keys=[compte_credit], back_populates="ecritures_credit")
    
    def __repr__(self):
        return f"<EcritureComptable({self.numero_ecriture}: {self.montant} {self.compte_debit}->{self.compte_credit})>"


# ═══════════════════════════════════════════════════════════════════════════════
# IMMOBILISATIONS (BIENS A AMORTIR)
# ═══════════════════════════════════════════════════════════════════════════════

class Immobilisation(Base):
    __tablename__ = 'immobilisations'
    
    id = Column(Integer, primary_key=True)
    
    # Identification
    numero_immobilisation = Column(String(50), nullable=False, unique=True)
    libelle = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Classification
    compte_immobilisation = Column(String(10), ForeignKey('plans_comptes.numero_compte'), nullable=False)
    compte_amortissement = Column(String(10), ForeignKey('plans_comptes.numero_compte'), nullable=False)
    
    # Valeurs
    valeur_brute = Column(Numeric(12, 2), nullable=False)
    date_acquisition = Column(Date, nullable=False)
    
    # Amortissement
    methode_amortissement = Column(String(50), nullable=False)  # LINEAIRE, DEGRESSIF
    duree_amortissement = Column(Integer, nullable=False)  # en annees
    taux_degressif = Column(Numeric(5, 2))  # si methode degressive
    
    # Traçabilité
    source_email_id = Column(String(255))
    source_email_date = Column(DateTime)
    
    actif = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    compte_immo = relationship("PlanCompte", foreign_keys=[compte_immobilisation], back_populates="immobilisations")
    calculs = relationship("CalculAmortissement", back_populates="immobilisation")
    
    def __repr__(self):
        return f"<Immobilisation({self.numero_immobilisation}: {self.libelle})>"


# ═══════════════════════════════════════════════════════════════════════════════
# CALCULS D'AMORTISSEMENTS (AUDIT TRAIL)
# ═══════════════════════════════════════════════════════════════════════════════

class CalculAmortissement(Base):
    __tablename__ = 'calculs_amortissements'
    
    id = Column(Integer, primary_key=True)
    
    immobilisation_id = Column(Integer, ForeignKey('immobilisations.id'), nullable=False)
    exercice_id = Column(Integer, ForeignKey('exercices_comptables.id'), nullable=False)
    
    # Traçabilité
    source_email_id = Column(String(255))
    source_calcul_date = Column(DateTime)
    
    # Calcul
    base_amortissable = Column(Numeric(12, 2), nullable=False)
    taux_applique = Column(Numeric(5, 2), nullable=False)
    montant_amortissement = Column(Numeric(12, 2), nullable=False)
    
    # Ecriture generee
    ecriture_id = Column(Integer, ForeignKey('ecritures_comptables.id'))
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    immobilisation = relationship("Immobilisation", back_populates="calculs")
    exercice = relationship("ExerciceComptable", back_populates="calculs_amortissements")
    
    def __repr__(self):
        return f"<CalculAmortissement(immo={self.immobilisation_id}, montant={self.montant_amortissement})>"


# ═══════════════════════════════════════════════════════════════════════════════
# QUEUE D'EVENEMENTS COMPTABLES (EMAIL -> TRAITEMENT)
# ═══════════════════════════════════════════════════════════════════════════════

class EvenementComptable(Base):
    __tablename__ = 'evenements_comptables'

    id = Column(Integer, primary_key=True)

    # Source email
    email_id = Column(String(255), unique=True)
    email_from = Column(String(255), nullable=False)
    email_date = Column(DateTime, nullable=False)
    email_subject = Column(String(255))
    email_body = Column(Text, nullable=False)

    # Classification
    type_evenement = Column(String(100))
    est_comptable = Column(Boolean)  # NULL = non traite, TRUE/FALSE = resultat

    # Traitement
    statut = Column(String(50), default='EN_ATTENTE')  # EN_ATTENTE, VALIDE, REJETE, ERREUR
    message_erreur = Column(Text)

    # Ecritures creees
    ecritures_creees = Column(ARRAY(Integer))

    created_at = Column(DateTime, default=datetime.utcnow)
    traite_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<EvenementComptable(email={self.email_id}, statut={self.statut})>"


# ═══════════════════════════════════════════════════════════════════════════════
# PROPOSITIONS EN ATTENTE DE VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class PropositionEnAttente(Base):
    __tablename__ = 'propositions_en_attente'

    id = Column(Integer, primary_key=True)

    # Token unique pour validation
    token = Column(String(50), unique=True, nullable=False)

    # Type d'événement
    type_evenement = Column(String(100), nullable=False)

    # Source email
    email_id = Column(String(255))
    email_from = Column(String(255))
    email_date = Column(DateTime)
    email_subject = Column(String(255))

    # Propositions au format JSON
    propositions_json = Column(JSONB, nullable=False)

    # Statut
    # EN_ATTENTE : Proposition créée, en attente de validation par Ulrik
    # VALIDEE : Proposition validée et écritures insérées avec succès (gardée pour audit trail)
    # ERREUR : Validation tentée mais insertion échouée (erreur technique)
    statut = Column(String(50), default='EN_ATTENTE')

    # Validation
    created_at = Column(DateTime, default=datetime.utcnow)
    validee_at = Column(DateTime)
    validee_par = Column(String(255))
    notes = Column(Text)

    def __repr__(self):
        return f"<PropositionEnAttente(token={self.token}, statut={self.statut})>"


# ═══════════════════════════════════════════════════════════════════════════════
# BALANCES MENSUELLES (CACHE POUR PERF)
# ═══════════════════════════════════════════════════════════════════════════════

class BalanceMensuelle(Base):
    __tablename__ = 'balances_mensuelles'
    
    id = Column(Integer, primary_key=True)
    
    exercice_id = Column(Integer, ForeignKey('exercices_comptables.id'), nullable=False)
    mois = Column(Integer, nullable=False)  # 1-12
    
    compte_numero = Column(String(10), ForeignKey('plans_comptes.numero_compte'), nullable=False)
    
    # Soldes
    solde_debit = Column(Numeric(12, 2), default=0)
    solde_credit = Column(Numeric(12, 2), default=0)
    solde_net = Column(Numeric(12, 2), default=0)
    
    # Meta
    nb_operations = Column(Integer, default=0)
    derniere_operation = Column(DateTime)
    recalcule_at = Column(DateTime, default=datetime.utcnow)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    exercice = relationship("ExerciceComptable", back_populates="balances")
    
    def __repr__(self):
        return f"<BalanceMensuelle(2024-{self.mois:02d} {self.compte_numero}: {self.solde_net})>"


# ═══════════════════════════════════════════════════════════════════════════════
# RAPPORTS GENERES
# ═══════════════════════════════════════════════════════════════════════════════

class RapportComptable(Base):
    __tablename__ = 'rapports_comptables'
    
    id = Column(Integer, primary_key=True)
    
    exercice_id = Column(Integer, ForeignKey('exercices_comptables.id'), nullable=False)
    type_rapport = Column(String(100), nullable=False)  # BILAN, COMPTE_RESULTAT, BALANCE, GRAND_LIVRE, AMORTISSEMENTS
    
    # Contenu
    contenu_texte = Column(Text, nullable=False)
    contenu_json = Column(JSONB)
    
    # Meta
    genere_par = Column(String(255))
    genere_at = Column(DateTime, default=datetime.utcnow)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    exercice = relationship("ExerciceComptable", back_populates="rapports")
    
    def __repr__(self):
        return f"<RapportComptable({self.type_rapport} 2024)>"


# ═══════════════════════════════════════════════════════════════════════════════
# DONNÉES DE RÉFÉRENCE - PRÊTS IMMOBILIERS
# ═══════════════════════════════════════════════════════════════════════════════

class PretImmobilier(Base):
    """
    Table de référence : Prêts immobiliers (données contractuelles)
    Source : Tableaux d'amortissement fournis par la banque
    Usage : Ventilation intérêts/capital lors comptabilisation relevés bancaires
    """
    __tablename__ = 'prets_immobiliers'

    id = Column(Integer, primary_key=True)

    # Identification
    numero_pret = Column(String(50), unique=True, nullable=False)  # Ex: 5009736BRM0911AH
    banque = Column(String(100), nullable=False)  # Ex: LCL
    libelle = Column(String(255))  # Ex: "Prêt acquisition SCPI"

    # Montants
    montant_initial = Column(Numeric(15, 2), nullable=False)  # Ex: 250000.00
    taux_annuel = Column(Numeric(6, 4), nullable=False)  # Ex: 0.0105 (1.05%)

    # Durée
    duree_mois = Column(Integer, nullable=False)  # Ex: 240 mois
    date_debut = Column(Date, nullable=False)  # Ex: 2023-04-15
    date_fin = Column(Date, nullable=False)  # Ex: 2043-04-15

    # Type amortissement
    type_amortissement = Column(String(50), nullable=False)  # AMORTISSEMENT_CONSTANT | FRANCHISE_PARTIELLE | FRANCHISE_TOTALE
    mois_franchise = Column(Integer, default=0)  # Ex: 180 mois (15 ans) pour prêt BRLZE

    # Montants mensuels
    echeance_mensuelle = Column(Numeric(15, 2))  # Ex: 1166.59 (prêt BRM)
    interet_mensuel_franchise = Column(Numeric(15, 2))  # Ex: 258.33 (prêt BRLZE pendant franchise)

    # Assurance (optionnel)
    assurance_emprunteur = Column(Boolean, default=False)
    assures = Column(String(255))  # Ex: "Emma Bergsten (50%), Pauline Bergsten (50%)"

    # Source document
    source_email_id = Column(String(255))
    source_document = Column(String(500))  # Nom fichier PDF
    date_ingestion = Column(DateTime, default=datetime.utcnow)

    # Métadonnées
    actif = Column(Boolean, default=True)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    echeances = relationship("EcheancePret", back_populates="pret", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PretImmobilier({self.numero_pret} {self.banque} {self.montant_initial}€)>"


class EcheancePret(Base):
    """
    Table de référence : Échéancier détaillé des prêts (ligne par ligne)
    Source : Parsing tableaux d'amortissement
    Usage : Lookup pour ventiler intérêts/capital lors comptabilisation
    """
    __tablename__ = 'echeances_prets'

    id = Column(Integer, primary_key=True)

    # Lien avec le prêt
    pret_id = Column(Integer, ForeignKey('prets_immobiliers.id'), nullable=False)

    # Identifiants échéance
    numero_echeance = Column(Integer, nullable=False)  # 1, 2, 3... 240
    date_echeance = Column(Date, nullable=False)  # Ex: 2023-05-15, 2023-06-15...

    # Ventilation financière
    montant_total = Column(Numeric(15, 2), nullable=False)  # Montant prélevé
    montant_interet = Column(Numeric(15, 2), nullable=False)  # Partie intérêts (compte 661)
    montant_capital = Column(Numeric(15, 2), nullable=False)  # Partie capital (compte 164)
    capital_restant_du = Column(Numeric(15, 2), nullable=False)  # Capital restant après échéance

    # Assurance (si applicable)
    montant_assurance = Column(Numeric(15, 2), default=0)  # Assurance emprunteur

    # Statut comptabilisation
    comptabilise = Column(Boolean, default=False)
    ecriture_comptable_id = Column(Integer, ForeignKey('ecritures_comptables.id'))
    date_comptabilisation = Column(DateTime)

    # Métadonnées
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    pret = relationship("PretImmobilier", back_populates="echeances")
    ecriture = relationship("EcritureComptable")

    # Contrainte unicité (un prêt ne peut avoir qu'une seule ligne pour une date donnée)
    __table_args__ = (
        UniqueConstraint('pret_id', 'date_echeance', name='uq_pret_date_echeance'),
    )

    def __repr__(self):
        return f"<EcheancePret(Prêt #{self.pret_id} #{self.numero_echeance} {self.date_echeance} {self.montant_total}€)>"


# ═══════════════════════════════════════════════════════════════════════════════
# PORTEFEUILLE VALEURS MOBILIÈRES (ETF, ACTIONS)
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

    # Relations
    mouvements = relationship("MouvementPortefeuille", back_populates="titre")

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

    # Relations
    titre = relationship("PortefeuilleValeursMobilieres", back_populates="mouvements")

    __table_args__ = (
        Index('idx_portefeuille_date', 'portefeuille_id', 'date_operation'),
    )

    def __repr__(self):
        return f"<MouvementPortefeuille({self.type_mouvement} {self.quantite} @ {self.prix_unitaire}€)>"


# ═══════════════════════════════════════════════════════════════════════════════
# COMPTES COURANTS D'ASSOCIÉS
# ═══════════════════════════════════════════════════════════════════════════════

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

    # Relations
    mouvements = relationship("MouvementCompteCourant", back_populates="compte_courant")

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

    # Relations
    compte_courant = relationship("ComptesCourantsAssocies", back_populates="mouvements")

    __table_args__ = (
        Index('idx_cc_date', 'compte_courant_id', 'date_operation'),
    )

    def __repr__(self):
        return f"<MouvementCompteCourant({self.type_mouvement} {self.montant}€ → {self.nouveau_solde}€)>"


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

def get_session(database_url):
    """
    Cree une session SQLAlchemy
    
    Usage:
        session = get_session("postgresql://...")
        user = session.query(EcritureComptable).first()
    """
    engine = create_engine(database_url, echo=False)
    Session = sessionmaker(bind=engine)
    return Session()

def init_module2(database_url):
    """
    Initialise les tables Module 2 (si elles n'existent pas)
    """
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    print("✅ Tables Module 2 creees/verifiees")


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    'ExerciceComptable',
    'PlanCompte',
    'EcritureComptable',
    'Immobilisation',
    'CalculAmortissement',
    'EvenementComptable',
    'PropositionEnAttente',
    'BalanceMensuelle',
    'RapportComptable',
    'PretImmobilier',
    'EcheancePret',
    'PortefeuilleValeursMobilieres',
    'MouvementPortefeuille',
    'ComptesCourantsAssocies',
    'MouvementCompteCourant',
    'get_session',
    'init_module2',
]
