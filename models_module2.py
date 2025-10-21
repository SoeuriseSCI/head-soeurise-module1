"""
MODULE 2 - MODÈLES SQLALCHEMY (ORM)
===============================
Représente les tables comptables en Python
"""

from sqlalchemy import (
    Column, Integer, String, Numeric, Date, DateTime, Boolean, 
    Text, ForeignKey, Enum, CheckConstraint, UniqueConstraint
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
# ÉCRITURES COMPTABLES
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
        return f"<EcritureComptable({self.numero_ecriture}: {self.montant} {self.compte_debit}→{self.compte_credit})>"


# ═══════════════════════════════════════════════════════════════════════════════
# IMMOBILISATIONS (BIENS À AMORTIR)
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
    duree_amortissement = Column(Integer, nullable=False)  # en années
    taux_degressif = Column(Numeric(5, 2))  # si méthode dégressive
    
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
    
    # Écriture générée
    ecriture_id = Column(Integer, ForeignKey('ecritures_comptables.id'))
    
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    immobilisation = relationship("Immobilisation", back_populates="calculs")
    exercice = relationship("ExerciceComptable", back_populates="calculs_amortissements")
    
    def __repr__(self):
        return f"<CalculAmortissement(immo={self.immobilisation_id}, montant={self.montant_amortissement})>"


# ═══════════════════════════════════════════════════════════════════════════════
# QUEUE D'ÉVÉNEMENTS COMPTABLES (EMAIL → TRAITEMENT)
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
    est_comptable = Column(Boolean)  # NULL = non traité, TRUE/FALSE = résultat
    
    # Traitement
    statut = Column(String(50), default='EN_ATTENTE')  # EN_ATTENTE, VALIDÉ, REJETÉ, ERREUR
    message_erreur = Column(Text)
    
    # Écritures créées
    ecritures_creees = Column(ARRAY(Integer))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    traite_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<EvenementComptable(email={self.email_id}, statut={self.statut})>"


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
# RAPPORTS GÉNÉRÉS
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
# SESSION FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

def get_session(database_url):
    """
    Crée une session SQLAlchemy
    
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
    print("✅ Tables Module 2 créées/vérifiées")


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
    'BalanceMensuelle',
    'RapportComptable',
    'get_session',
    'init_module2',
]
