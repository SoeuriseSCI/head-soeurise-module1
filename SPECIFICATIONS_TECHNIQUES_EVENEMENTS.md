# Spécifications Techniques - Système de Gestion des Événements Comptables

**Version** : 1.0
**Date** : 05/11/2025
**Projet** : _Head.Soeurise - MODULE 2 - Événements Comptables

---

## 🎯 Objectif

Développer un système complet de gestion des événements comptables permettant :
1. Détection automatique d'événements depuis relevés bancaires et documents
2. Génération de propositions d'écritures comptables
3. Validation par l'utilisateur (Ulrik)
4. Création automatique des écritures comptables en base
5. Production de rapports (Grand Livre, Compte d'Exploitation, Bilan)

---

## 📐 Architecture Générale

```
┌─────────────────────────────────────────────────────────────────┐
│  1. INGESTION                                                    │
│     - PDF relevés bancaires + documents comptables              │
│     - OCR + parsing                                              │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. DÉTECTION                                                    │
│     - Détecteurs spécialisés par type d'événement               │
│     - Classification automatique                                 │
│     - Détection de doublons                                      │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. ENREGISTREMENT                                               │
│     - Table evenements_comptables                                │
│     - Statut: EN_ATTENTE                                         │
│     - Métadonnées: type, montant, date, source, fingerprint     │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. GÉNÉRATION PROPOSITIONS                                      │
│     - Règles comptables par type                                 │
│     - Validation cohérence                                       │
│     - Markdown + JSON + Token MD5                                │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  5. VALIDATION UTILISATEUR                                       │
│     - Email à Ulrik avec propositions                            │
│     - Attente tag [_Head] VALIDE: {token}                        │
│     - Possibilité de modification manuelle                       │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  6. CRÉATION ÉCRITURES                                           │
│     - Insertion dans ecritures_comptables                        │
│     - Mise à jour evenements_comptables (VALIDE)                 │
│     - Liaison événement ↔ écritures                              │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  7. RAPPORTS                                                     │
│     - Grand Livre (par compte)                                   │
│     - Compte d'Exploitation (produits/charges)                   │
│     - Bilan (actif/passif)                                       │
│     - Balance (soldes de tous les comptes)                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Modèle de Données

### Table `evenements_comptables` (ENRICHIE)

```sql
CREATE TABLE evenements_comptables (
    id SERIAL PRIMARY KEY,

    -- Identification unique (détection doublons)
    fingerprint VARCHAR(64) UNIQUE NOT NULL,  -- MD5(date + libelle_normalise + montant + type)

    -- Source email/document
    email_id VARCHAR(255),
    email_from VARCHAR(255),
    email_date TIMESTAMP,
    email_subject VARCHAR(255),
    email_body TEXT,
    document_source VARCHAR(500),  -- Nom fichier PDF source

    -- Données de l'événement
    date_operation DATE NOT NULL,
    libelle VARCHAR(500) NOT NULL,
    libelle_normalise VARCHAR(500),  -- Version nettoyée pour matching
    montant NUMERIC(12, 2) NOT NULL,
    type_operation VARCHAR(10) NOT NULL,  -- DEBIT ou CREDIT

    -- Classification
    type_evenement VARCHAR(100),  -- REMB_PRET, ASSURANCE, REVENU_SCPI, etc.
    categorie VARCHAR(50),  -- CHARGE, PRODUIT, INVESTISSEMENT, FINANCEMENT
    phase_traitement INTEGER,  -- 1, 2, 3 (phase de détection/traitement)

    -- Traitement
    statut VARCHAR(50) DEFAULT 'EN_ATTENTE',  -- EN_ATTENTE, VALIDE, REJETE, ERREUR
    est_comptable BOOLEAN,  -- NULL=non traité, TRUE/FALSE=résultat analyse
    message_erreur TEXT,

    -- Écritures créées
    ecritures_creees INTEGER[],  -- Array des IDs d'écritures comptables

    -- Métadonnées comptables suggérées
    proposition_compte_debit VARCHAR(10),
    proposition_compte_credit VARCHAR(10),
    proposition_libelle VARCHAR(255),

    -- Traçabilité
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    traite_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index
CREATE INDEX idx_evenements_date ON evenements_comptables(date_operation);
CREATE INDEX idx_evenements_statut ON evenements_comptables(statut);
CREATE INDEX idx_evenements_type ON evenements_comptables(type_evenement);
CREATE INDEX idx_evenements_phase ON evenements_comptables(phase_traitement);
CREATE UNIQUE INDEX idx_evenements_fingerprint ON evenements_comptables(fingerprint);
```

### Table `portefeuille_valeurs_mobilieres` (NOUVELLE)

```sql
CREATE TABLE portefeuille_valeurs_mobilieres (
    id SERIAL PRIMARY KEY,

    -- Identification
    code_isin VARCHAR(20),  -- LU1781541179, US0231351067
    libelle VARCHAR(255) NOT NULL,  -- "AMUNDI MSCI WORLD", "AMAZON COM"
    type_valeur VARCHAR(50) NOT NULL,  -- ETF, ACTION
    marche VARCHAR(50),  -- EURONEXT_PARIS, NASDAQ

    -- Position actuelle
    quantite NUMERIC(15, 4) NOT NULL,  -- Nombre de parts/actions
    prix_moyen_acquisition NUMERIC(15, 4) NOT NULL,  -- PRU (prix de revient unitaire)
    valeur_comptable NUMERIC(15, 2) NOT NULL,  -- quantite × prix_moyen_acquisition

    -- Informations marché (optionnel, pas comptabilisé)
    cours_actuel NUMERIC(15, 4),
    valeur_marche NUMERIC(15, 2),
    plus_value_latente NUMERIC(15, 2),
    date_maj_cours DATE,

    -- Métadonnées
    date_premiere_acquisition DATE NOT NULL,
    compte_comptable VARCHAR(10) DEFAULT '503',  -- Actions, parts sociales
    actif BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index
CREATE INDEX idx_portef_isin ON portefeuille_valeurs_mobilieres(code_isin);
CREATE INDEX idx_portef_actif ON portefeuille_valeurs_mobilieres(actif);
```

### Table `mouvements_portefeuille` (NOUVELLE)

```sql
CREATE TABLE mouvements_portefeuille (
    id SERIAL PRIMARY KEY,

    -- Lien avec valeur
    valeur_id INTEGER REFERENCES portefeuille_valeurs_mobilieres(id),

    -- Type de mouvement
    type_mouvement VARCHAR(20) NOT NULL,  -- ACHAT, VENTE

    -- Détail opération
    date_operation DATE NOT NULL,
    quantite NUMERIC(15, 4) NOT NULL,
    prix_unitaire NUMERIC(15, 4) NOT NULL,
    montant_brut NUMERIC(15, 2) NOT NULL,  -- quantite × prix_unitaire

    -- Frais
    commission NUMERIC(15, 2) DEFAULT 0,
    frais_divers NUMERIC(15, 2) DEFAULT 0,  -- Frais de change, etc.
    montant_total NUMERIC(15, 2) NOT NULL,  -- montant_brut + commission + frais

    -- Comptabilisation
    ecriture_comptable_id INTEGER REFERENCES ecritures_comptables(id),

    -- Source
    document_source VARCHAR(500),
    evenement_id INTEGER REFERENCES evenements_comptables(id),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index
CREATE INDEX idx_mvt_portef_valeur ON mouvements_portefeuille(valeur_id);
CREATE INDEX idx_mvt_portef_date ON mouvements_portefeuille(date_operation);
```

### Table `comptes_courants_associes` (NOUVELLE)

```sql
CREATE TABLE comptes_courants_associes (
    id SERIAL PRIMARY KEY,

    -- Identification associé
    nom_associe VARCHAR(255) NOT NULL,  -- "Ulrik Bergsten", "Emma Bergsten", "Pauline Bergsten"
    email_associe VARCHAR(255),
    role VARCHAR(50),  -- GERANT, ASSOCIE

    -- Solde
    solde_initial NUMERIC(15, 2) DEFAULT 0,  -- Au 01/01/exercice
    solde_actuel NUMERIC(15, 2) DEFAULT 0,

    -- Limites (optionnel)
    plafond_autorise NUMERIC(15, 2),  -- Montant max autorisé
    taux_remuneration NUMERIC(5, 4),  -- Taux d'intérêt annuel (ex: 0.01 = 1%)

    -- Métadonnées
    compte_comptable VARCHAR(10) DEFAULT '455',  -- Compte courant d'associés
    date_ouverture DATE NOT NULL,
    actif BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Table `mouvements_comptes_courants` (NOUVELLE)

```sql
CREATE TABLE mouvements_comptes_courants (
    id SERIAL PRIMARY KEY,

    -- Lien avec associé
    compte_courant_id INTEGER REFERENCES comptes_courants_associes(id),

    -- Type de mouvement
    type_mouvement VARCHAR(20) NOT NULL,  -- APPORT, REMBOURSEMENT

    -- Détail
    date_operation DATE NOT NULL,
    montant NUMERIC(15, 2) NOT NULL,
    libelle VARCHAR(255),

    -- Comptabilisation
    ecriture_comptable_id INTEGER REFERENCES ecritures_comptables(id),

    -- Source
    evenement_id INTEGER REFERENCES evenements_comptables(id),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🔧 Modules à Développer

### Module 1 : `gestionnaire_evenements.py`

**Responsabilité** : CRUD + workflow des événements comptables

```python
class GestionnaireEvenements:
    """Gestion centralisée des événements comptables"""

    def creer_evenement(self, data: Dict) -> int:
        """
        Crée un nouvel événement comptable

        Args:
            data: {
                'date_operation': '2024-01-15',
                'libelle': 'PRET IMMOBILIER ECH 15/01/24...',
                'montant': 258.33,
                'type_operation': 'DEBIT',
                'document_source': 'Releve_LCL_Jan2024.pdf'
            }

        Returns:
            event_id: ID de l'événement créé

        Process:
            1. Normaliser le libellé
            2. Calculer le fingerprint (unicité)
            3. Vérifier absence de doublon
            4. Insérer en BD
            5. Retourner l'ID
        """

    def detecter_type_evenement(self, evenement: Dict) -> str:
        """
        Détecte automatiquement le type d'événement

        Uses:
            - DetecteurRemboursementPret
            - DetecteurAssurance
            - DetecteurRevenuSCPI
            - DetecteurAchatValeurs
            - DetecteurApportAssocie
            - etc.

        Returns:
            Type détecté ou 'INCONNU'
        """

    def generer_propositions(self, event_id: int) -> Dict:
        """
        Génère les propositions d'écritures comptables

        Returns:
            {
                'markdown': '# Proposition...',
                'propositions': [{...}],
                'token': 'abc123...'
            }
        """

    def valider_evenement(self, event_id: int, ecritures_ids: List[int]) -> bool:
        """
        Marque un événement comme VALIDE et lie les écritures

        Args:
            event_id: ID événement
            ecritures_ids: IDs des écritures créées

        Returns:
            True si succès
        """

    def rejeter_evenement(self, event_id: int, raison: str) -> bool:
        """Marque un événement comme REJETÉ"""

    def est_deja_traite(self, fingerprint: str) -> bool:
        """Vérifie si un événement a déjà été traité"""

    def lister_evenements(
        self,
        statut: str = None,
        type_evt: str = None,
        date_debut: str = None,
        date_fin: str = None,
        phase: int = None
    ) -> List[Dict]:
        """Liste les événements avec filtres"""
```

### Module 2 : `detecteurs_evenements.py`

**Responsabilité** : Détection et classification par type

```python
class DetecteurBase:
    """Classe de base pour tous les détecteurs"""

    def detecter(self, evenement: Dict) -> bool:
        """Retourne True si l'événement correspond à ce type"""
        raise NotImplementedError

    def extraire_metadonnees(self, evenement: Dict) -> Dict:
        """Extrait les métadonnées spécifiques"""
        raise NotImplementedError


class DetecteurRemboursementPret(DetecteurBase):
    """
    Détecte : PRET IMMOBILIER ECH XX/XX/XX DOSSIER NO XXXXXXX

    Complexité: ÉLEVÉE
    - Nécessite lookup dans table echeances_prets
    - Ventilation intérêts/capital obligatoire
    """

    def detecter(self, evenement: Dict) -> bool:
        pattern = r'PRET IMMOBILIER ECH \d{2}/\d{2}/\d{2}'
        return bool(re.search(pattern, evenement['libelle']))

    def extraire_metadonnees(self, evenement: Dict) -> Dict:
        """
        Extrait:
        - numero_dossier (BRM0911AH ou BRLZE11AQ)
        - date_echeance
        - montant

        Lookup:
        - Trouve l'échéance correspondante dans echeances_prets
        - Retourne ventilation intérêts/capital
        """


class DetecteurAssurancePret(DetecteurBase):
    """
    Détecte : PRLV SEPA CACI NON LIFE LIMITED

    Complexité: FAIBLE
    - Montants fixes (66.58€ Emma, 20.99€ Pauline)
    - 1 seul prêt concerné (BRM0911AH)
    """

    def detecter(self, evenement: Dict) -> bool:
        return 'CACI NON LIFE LIMITED' in evenement['libelle']

    def extraire_metadonnees(self, evenement: Dict) -> Dict:
        """
        Identifie:
        - Emma (66.58€) vs Pauline (20.99€)
        - Numéro de contrat
        """


class DetecteurRevenuSCPI(DetecteurBase):
    """
    Détecte : VIR SEPA SCPI EPARGNE PIERRE DISTRIBUTION

    Complexité: MOYENNE
    - 2 types: Distribution revenus vs Distribution capital
    - Montants variables
    """

    def detecter(self, evenement: Dict) -> bool:
        return 'SCPI EPARGNE PIERRE' in evenement['libelle']

    def extraire_metadonnees(self, evenement: Dict) -> Dict:
        """
        Distingue:
        - Distribution revenus (compte 761)
        - Distribution capital (compte 777 - produit exceptionnel)
        """


class DetecteurAchatValeursMobilieres(DetecteurBase):
    """
    Détecte : Achats ETF/Actions

    Patterns:
    - "150 AM.MSCI WLD V UC.ETF ACC"
    - "6 AMAZON COM ACHAT 2108"

    Complexité: ÉLEVÉE
    - Extraction quantité, prix unitaire
    - Commissions + frais
    - Mise à jour portefeuille
    """


class DetecteurApportAssocie(DetecteurBase):
    """
    Détecte : Apport CC UB / Apport En Compte Courant

    Complexité: FAIBLE
    - Libellé clair
    - Montant variable
    - Associé identifiable (Ulrik Bergsten)
    """


class DetecteurHonorairesComptable(DetecteurBase):
    """
    Détecte : Factures CRP 2C

    Complexité: FAIBLE
    - Parsing du PDF facture
    - Montant TTC (pas de TVA déductible)
    """


class DetecteurFraisBancaires(DetecteurBase):
    """
    Détecte : LCL A LA CARTE PRO, COTISATION, ABON LCL ACCESS

    Complexité: FAIBLE
    - Montants fixes
    - Fréquence mensuelle
    """
```

### Module 3 : `generateur_propositions.py`

**Responsabilité** : Génération des propositions d'écritures

```python
class GenerateurPropositions:
    """Génère les propositions comptables selon le type d'événement"""

    @staticmethod
    def generer_remboursement_pret(evenement: Dict, ventilation: Dict) -> List[Dict]:
        """
        Génère 2 écritures:
        1. Charges d'intérêts
        2. Remboursement capital

        Exemple:
        [
            {
                'numero_ecriture': '2024-01-15-PRET-INT',
                'compte_debit': '661',  # Charges d'intérêts
                'compte_credit': '512',  # Banque
                'montant': 218.75,
                'libelle': 'Intérêts prêt LCL échéance 15/01/2024'
            },
            {
                'numero_ecriture': '2024-01-15-PRET-CAP',
                'compte_debit': '164',  # Emprunts
                'compte_credit': '512',  # Banque
                'montant': 39.58,
                'libelle': 'Remb capital prêt LCL échéance 15/01/2024'
            }
        ]
        """

    @staticmethod
    def generer_assurance_pret(evenement: Dict, assure: str) -> List[Dict]:
        """
        Génère 1 écriture:

        {
            'numero_ecriture': '2024-01-05-ASS-EMMA',
            'compte_debit': '616',  # Primes d'assurance
            'compte_credit': '512',  # Banque
            'montant': 66.58,
            'libelle': 'Assurance emprunteur Emma - Prêt LCL'
        }
        """

    @staticmethod
    def generer_revenu_scpi(evenement: Dict, type_distribution: str) -> List[Dict]:
        """
        Type = 'REVENUS' ou 'CAPITAL'

        REVENUS:
        {
            'compte_debit': '512',  # Banque
            'compte_credit': '761',  # Produits de participations
            'montant': 6346.56,
            'libelle': 'Revenus SCPI Épargne Pierre T1 2024'
        }

        CAPITAL:
        {
            'compte_debit': '512',  # Banque
            'compte_credit': '777',  # Produits exceptionnels
            'montant': 601.00,
            'libelle': 'Distribution capital SCPI Épargne Pierre'
        }
        """

    # ... autres générateurs
```

### Module 4 : `nettoyage_bd.py`

**Responsabilité** : Outils de nettoyage/rollback pour debugging

```python
class NettoyeurBD:
    """Outils de nettoyage de la base de données"""

    def nettoyer_periode(
        self,
        date_debut: str,
        date_fin: str,
        dry_run: bool = True
    ) -> Dict:
        """
        Supprime tous les événements et écritures d'une période

        Args:
            date_debut: '2024-01-01'
            date_fin: '2024-03-31'
            dry_run: Si True, simule sans supprimer

        Returns:
            {
                'evenements_supprimes': 45,
                'ecritures_supprimees': 67,
                'detail': [...]
            }

        Process:
            1. Lister tous les événements de la période
            2. Identifier toutes les écritures liées
            3. Si dry_run=False:
                - Supprimer écritures (cascade)
                - Supprimer événements
                - Logger l'action
            4. Retourner rapport
        """

    def nettoyer_phase(self, phase: int, dry_run: bool = True) -> Dict:
        """
        Supprime tous les événements d'une phase de traitement

        Args:
            phase: 1, 2 ou 3
            dry_run: Si True, simule sans supprimer
        """

    def restaurer_sauvegarde(self, backup_file: str) -> bool:
        """
        Restaure une sauvegarde de la BD

        Args:
            backup_file: 'backups/soeurise_bd_20241105.json'
        """
```

### Module 5 : `detection_doublons.py`

**Responsabilité** : Détection d'événements déjà traités

```python
class DetecteurDoublons:
    """Détecte les événements déjà traités"""

    @staticmethod
    def calculer_fingerprint(evenement: Dict) -> str:
        """
        Calcule un hash unique pour l'événement

        Args:
            evenement: {
                'date_operation': '2024-01-15',
                'libelle': 'PRET IMMOBILIER...',
                'montant': 258.33,
                'type_operation': 'DEBIT'
            }

        Returns:
            MD5(date + libelle_normalise + montant + type)

        Exemple:
            '3f5a8b2c1d9e7f6a4b3c2d1e0f9a8b7c'
        """
        libelle_norm = DetecteurDoublons.normaliser_libelle(evenement['libelle'])
        data = f"{evenement['date_operation']}{libelle_norm}{evenement['montant']}{evenement['type_operation']}"
        return hashlib.md5(data.encode()).hexdigest()

    @staticmethod
    def normaliser_libelle(libelle: str) -> str:
        """
        Normalise un libellé pour comparaison

        - Supprime espaces multiples
        - Minuscules
        - Supprime accents
        - Supprime caractères spéciaux

        Exemple:
            'PRET IMMOBILIER ECH 15/01/24'
            → 'pret immobilier ech'
        """

    def est_doublon(self, evenement: Dict) -> Tuple[bool, Optional[int]]:
        """
        Vérifie si un événement est un doublon

        Returns:
            (is_duplicate, event_id_existant)

        Exemple:
            (True, 123) → Doublon de l'événement #123
            (False, None) → Nouveau
        """
```

### Module 6 : `generateur_rapports.py`

**Responsabilité** : Production des rapports comptables

```python
class GenerateurRapports:
    """Génère les rapports comptables standard"""

    def generer_grand_livre(
        self,
        date_debut: str,
        date_fin: str,
        compte: str = None
    ) -> str:
        """
        Génère le Grand Livre comptable

        Args:
            date_debut: '2024-01-01'
            date_fin: '2024-09-30'
            compte: '512' (optionnel - filtre sur 1 compte)

        Returns:
            Texte formaté du Grand Livre (markdown ou CSV)

        Format:
            # GRAND LIVRE COMPTABLE
            ## Période: 01/01/2024 - 30/09/2024

            ### Compte 512 - Banque LCL
            | Date | N° | Libellé | Débit | Crédit | Solde |
            |------|-----|---------|-------|--------|-------|
            | 01/01 | - | Solde initial | | | 1 997,28 |
            | 15/01 | 001 | Prêt LCL | | 258,33 | 1 738,95 |
            ...
        """

    def generer_compte_exploitation(
        self,
        date_debut: str,
        date_fin: str
    ) -> Dict:
        """
        Génère le Compte d'Exploitation (Compte de Résultat)

        Returns:
            {
                'produits': {
                    '761': {'libelle': 'Revenus SCPI', 'montant': 19500.00},
                    '777': {'libelle': 'Produits exceptionnels', 'montant': 601.00}
                },
                'charges': {
                    '616': {'libelle': 'Assurances', 'montant': 788.13},
                    '622': {'libelle': 'Honoraires', 'montant': 1161.00},
                    '661': {'libelle': 'Charges d\'intérêts', 'montant': 3500.00}
                },
                'resultat': 14651.87
            }
        """

    def generer_balance(
        self,
        date_fin: str
    ) -> Dict:
        """
        Génère la Balance des comptes

        Returns:
            {
                '512': {
                    'libelle': 'Banque LCL',
                    'solde_debit': 25000.00,
                    'solde_credit': 20000.00,
                    'solde_net': 5000.00
                },
                ...
            }
        """
```

---

## 🔄 Workflow Complet

### Étape 1 : Ingestion du PDF

```python
# L'utilisateur fournit le PDF complet
pdf_path = "Elements Comptables des 1-2-3T2024.pdf"

# Parsing avec OCR
from parseur_documents import ParseurDocuments
parseur = ParseurDocuments(api_key=ANTHROPIC_API_KEY)
operations = parseur.extraire_operations(pdf_path)

# operations = [
#     {'date': '2024-01-15', 'libelle': 'PRET...', 'montant': 258.33, 'type': 'DEBIT'},
#     {'date': '2024-01-15', 'libelle': 'PRET...', 'montant': 1166.59, 'type': 'DEBIT'},
#     ...
# ]
```

### Étape 2 : Détection et Enregistrement

```python
from gestionnaire_evenements import GestionnaireEvenements
from detection_doublons import DetecteurDoublons

gestionnaire = GestionnaireEvenements(database_url=DB_URL)
detecteur_doublons = DetecteurDoublons(database_url=DB_URL)

evenements_crees = []
doublons_detectes = []

for op in operations:
    # Calculer fingerprint
    fingerprint = detecteur_doublons.calculer_fingerprint(op)

    # Vérifier doublon
    is_dup, existing_id = detecteur_doublons.est_doublon(op)

    if is_dup:
        doublons_detectes.append((op, existing_id))
        continue

    # Créer événement
    event_id = gestionnaire.creer_evenement({
        **op,
        'fingerprint': fingerprint,
        'document_source': pdf_path
    })

    # Détecter type
    type_evt = gestionnaire.detecter_type_evenement(event_id)

    # Mettre à jour
    gestionnaire.mettre_a_jour_type(event_id, type_evt)

    evenements_crees.append(event_id)

print(f"✅ {len(evenements_crees)} nouveaux événements créés")
print(f"⚠️ {len(doublons_detectes)} doublons ignorés")
```

### Étape 3 : Génération des Propositions

```python
from generateur_propositions import GenerateurPropositions

generateur = GenerateurPropositions()

for event_id in evenements_crees:
    # Générer propositions
    propositions = gestionnaire.generer_propositions(event_id)

    # Enregistrer dans propositions_en_attente
    token = propositions['token']
    gestionnaire.enregistrer_proposition(event_id, propositions, token)

print(f"✅ Propositions générées pour {len(evenements_crees)} événements")
```

### Étape 4 : Envoi Email à Ulrik

```python
from envoyeur_propositions import EnvoyeurPropositions

envoyeur = EnvoyeurPropositions(
    email_from=GMAIL_ACCOUNT,
    email_password=GMAIL_PASSWORD
)

# Regrouper par phase
propositions_phase_1 = gestionnaire.lister_evenements(phase=1, statut='EN_ATTENTE')

# Envoyer email récapitulatif
envoyeur.envoyer_batch_propositions(
    email_to="ulrik.c.s.be@gmail.com",
    evenements=propositions_phase_1,
    phase=1
)

print("✅ Email de propositions envoyé à Ulrik")
```

### Étape 5 : Validation et Création Écritures

```python
# Lors du prochain réveil, _Head.Soeurise détecte la réponse
# Recherche tag [_Head] VALIDE: {token}

from validateur_propositions import ValidateurPropositions

validateur = ValidateurPropositions(database_url=DB_URL)

# Token reçu dans l'email de réponse
token_valide = "3f5a8b2c1d9e7f6a4b3c2d1e0f9a8b7c"

# Créer les écritures
ecritures_ids = validateur.creer_ecritures_depuis_token(token_valide)

print(f"✅ {len(ecritures_ids)} écritures comptables créées")
```

### Étape 6 : Production des Rapports

```python
from generateur_rapports import GenerateurRapports

rapports = GenerateurRapports(database_url=DB_URL)

# Grand Livre
grand_livre = rapports.generer_grand_livre(
    date_debut='2024-01-01',
    date_fin='2024-09-30'
)

# Compte d'Exploitation
compte_exploitation = rapports.generer_compte_exploitation(
    date_debut='2024-01-01',
    date_fin='2024-09-30'
)

# Bilan
bilan = rapports.generer_bilan(date_fin='2024-09-30')

# Sauvegarder
with open('GRAND_LIVRE_2024_T1T2T3.md', 'w') as f:
    f.write(grand_livre)

print("✅ Rapports générés")
```

---

## 📅 Plan de Développement (Phases)

### PHASE 1 : Événements Simples (1-2 semaines)

**Objectif** : Valider l'architecture complète sur des cas simples

**Événements traités** :
- Assurances prêt (2/mois)
- Frais bancaires (3/mois)
- Honoraires comptable (trimestriel)

**Modules à développer** :
- ✅ `gestionnaire_evenements.py` (structure de base)
- ✅ `detecteurs_evenements.py` (3 détecteurs simples)
- ✅ `generateur_propositions.py` (3 générateurs simples)
- ✅ `detection_doublons.py`
- ✅ `nettoyage_bd.py`

**Résultat attendu** :
- ~30 événements/an automatisés
- Workflow complet validé

### PHASE 2 : Événements avec Données de Référence (2-3 semaines)

**Événements traités** :
- Remboursements prêts (avec ventilation)
- Apports associés

**Modules à développer** :
- ✅ `portefeuille_manager.py` (suivi CC associés)
- ✅ Détecteurs + générateurs prêts/apports
- ✅ Enrichissement table `echeances_prets` (si besoin)

**Résultat attendu** :
- ~50 événements/an supplémentaires
- Gestion comptable des financements

### PHASE 3 : Événements Complexes (3-4 semaines)

**Événements traités** :
- Revenus SCPI (revenus + capital)
- Achats valeurs mobilières
- Impôts/taxes

**Modules à développer** :
- ✅ `portefeuille_manager.py` (ETF/Actions)
- ✅ Détecteurs + générateurs complexes
- ✅ `generateur_rapports.py` (Grand Livre, Exploitation)

**Résultat attendu** :
- ~40 événements/an supplémentaires
- Système complet opérationnel

---

## ✅ Checklist de Développement

### Base de Données

- [ ] Enrichir table `evenements_comptables` (fingerprint, phase_traitement)
- [ ] Créer table `portefeuille_valeurs_mobilieres`
- [ ] Créer table `mouvements_portefeuille`
- [ ] Créer table `comptes_courants_associes`
- [ ] Créer table `mouvements_comptes_courants`
- [ ] Créer index et contraintes

### Modules Core

- [ ] `gestionnaire_evenements.py`
- [ ] `detecteurs_evenements.py` (tous les détecteurs)
- [ ] `generateur_propositions.py` (tous les générateurs)
- [ ] `detection_doublons.py`
- [ ] `nettoyage_bd.py`
- [ ] `portefeuille_manager.py`

### Rapports

- [ ] `generateur_rapports.py` (Grand Livre)
- [ ] `generateur_rapports.py` (Compte d'Exploitation)
- [ ] `generateur_rapports.py` (Bilan)
- [ ] `generateur_rapports.py` (Balance)

### Tests

- [ ] Tests unitaires détecteurs
- [ ] Tests générateurs propositions
- [ ] Tests détection doublons
- [ ] Tests nettoyage BD
- [ ] Tests end-to-end workflow complet

### Documentation

- [ ] Guide utilisateur
- [ ] Documentation technique complète
- [ ] Exemples d'utilisation
- [ ] FAQ / Troubleshooting

---

**Statut** : Spécifications validées - Prêt pour développement
**Prochaine étape** : Commencer PHASE 1
