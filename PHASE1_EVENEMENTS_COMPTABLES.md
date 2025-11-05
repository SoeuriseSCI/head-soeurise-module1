# Phase 1 - Gestion des Événements Comptables

**Date**: 05/11/2025
**Statut**: ✅ Implémenté (en attente de tests sur Render)
**Version**: 1.0

---

## 📋 Vue d'Ensemble

La Phase 1 du système de gestion des événements comptables implémente:

1. **Infrastructure de base** pour la gestion des événements comptables
2. **Détection de doublons** via fingerprinting MD5
3. **Nettoyage de base de données** pour le développement/debug
4. **Détecteurs simples** pour les événements récurrents (Phase 1)

---

## 🗂️ Fichiers Créés

### 1. `migration_evenements_comptables.py`

**Rôle**: Script de migration de base de données

**Modifications apportées**:
- Enrichissement table `evenements_comptables`:
  - `date_operation` (DATE): Date réelle de l'opération
  - `libelle` (VARCHAR(500)): Libellé extrait du relevé
  - `libelle_normalise` (VARCHAR(500)): Libellé normalisé
  - `montant` (NUMERIC(15,2)): Montant de l'opération
  - `type_operation` (VARCHAR(20)): DEBIT ou CREDIT
  - `fingerprint` (VARCHAR(64)): Empreinte MD5 unique
  - `phase_traitement` (INTEGER): Phase ayant traité l'événement

- Nouvelles tables créées:
  - `portefeuille_valeurs_mobilieres`: Positions ETF/Actions
  - `mouvements_portefeuille`: Historique achats/ventes
  - `comptes_courants_associes`: Comptes courants associés
  - `mouvements_comptes_courants`: Historique apports/retraits

**Utilisation**:
```bash
# Appliquer la migration
python migration_evenements_comptables.py

# Rollback (développement uniquement)
python migration_evenements_comptables.py --rollback
```

---

### 2. `detection_doublons.py`

**Rôle**: Détection des événements en doublon via fingerprinting

**Principe**:
- Calcul d'une empreinte MD5 unique: `MD5(date + libelle_normalise + montant + type)`
- Normalisation du libellé pour ignorer variations mineures
- Vérification avant insertion pour éviter doublons

**Classe principale**: `DetecteurDoublons`

**Méthodes clés**:
```python
DetecteurDoublons.normaliser_libelle(libelle: str) -> str
    # Normalise un libellé pour comparaison
    # "VIR SEPA RECU /DE ULRIK BERGSTEN /MOTIF Apport"
    # → "vir sepa recu de ulrik bergsten motif apport"

DetecteurDoublons.calculer_fingerprint(evenement: Dict) -> str
    # Calcule l'empreinte MD5 de l'événement
    # Returns: Hash hexadécimal (64 caractères)

DetecteurDoublons.verifier_doublon(session, evenement: Dict) -> Optional[Dict]
    # Vérifie si un événement existe déjà
    # Returns: Info du doublon si trouvé, None sinon
```

**Tests unitaires intégrés**:
```bash
python detection_doublons.py
```

---

### 3. `nettoyage_bd.py`

**Rôle**: Nettoyage de base de données pour développement/debug

**Fonctionnalités**:
- Analyse d'une période (sans modification)
- Nettoyage par période avec confirmation
- Nettoyage par phase de traitement
- Sauvegarde automatique avant suppression
- Mode dry_run pour simulation

**Classe principale**: `NettoyeurBD`

**Méthodes clés**:
```python
NettoyeurBD.analyser_periode(date_debut: str, date_fin: str) -> Dict
    # Analyse ce qui serait nettoyé (lecture seule)
    # Returns: Statistiques détaillées

NettoyeurBD.nettoyer_periode(date_debut: str, date_fin: str, dry_run: bool = True) -> Dict
    # Nettoie une période (avec confirmation)
    # dry_run=True: Simulation uniquement
    # dry_run=False: Suppression réelle avec sauvegarde

NettoyeurBD.nettoyer_par_phase(phase: int, dry_run: bool = True) -> Dict
    # Nettoie tous les événements d'une phase
```

**Utilisation CLI**:
```bash
# Mode interactif
python nettoyage_bd.py

# Exemple de session:
# Date de début (YYYY-MM-DD): 2024-01-01
# Date de fin (YYYY-MM-DD): 2024-09-30
# [Analyse affichée]
# Confirmer le nettoyage? (oui/non): oui
```

**⚠️ ATTENTION**: Outil de développement uniquement. Utiliser avec précaution en production.

---

### 4. `gestionnaire_evenements.py`

**Rôle**: Gestionnaire central des événements comptables

**Responsabilités**:
1. Création d'événements dans la BD
2. Calcul et enregistrement du fingerprint
3. Détection automatique du type d'événement
4. Orchestration du traitement par phases
5. Mise à jour des statuts

**Classe principale**: `GestionnaireEvenements`

**Méthodes clés**:
```python
GestionnaireEvenements.creer_evenement(data: Dict) -> Optional[int]
    # Crée un événement (vérifie doublon automatiquement)
    # Returns: ID de l'événement créé, None si doublon

GestionnaireEvenements.creer_evenements_batch(evenements: List[Dict]) -> Dict
    # Crée plusieurs événements en batch
    # Returns: Statistiques (créés, doublons, erreurs)

GestionnaireEvenements.detecter_type_evenement(evenement_id: int) -> Optional[str]
    # Détecte automatiquement le type d'un événement
    # Returns: Type détecté ou None

GestionnaireEvenements.marquer_phase_traitement(evenement_id: int, phase: int)
    # Marque un événement comme traité par une phase

GestionnaireEvenements.obtenir_evenements_en_attente(limit: int = 100) -> List[Dict]
    # Récupère les événements en attente pour la phase courante

GestionnaireEvenements.obtenir_statistiques() -> Dict
    # Statistiques globales (par statut, phase, type)
```

**Utilisation**:
```python
from gestionnaire_evenements import GestionnaireEvenements
from models_module2 import get_session

session = get_session(DATABASE_URL)
gestionnaire = GestionnaireEvenements(session, phase=1)

# Créer un événement
evt_id = gestionnaire.creer_evenement({
    'date_operation': '2024-01-15',
    'libelle': 'PRLV SEPA COVEA RISKS',
    'montant': 87.57,
    'type_operation': 'DEBIT',
    'email_id': 'email_123',
    'email_from': 'banque@lcl.fr',
    'email_date': datetime.now(),
    'email_body': '...'
})

# Détecter le type
type_evt = gestionnaire.detecter_type_evenement(evt_id)
print(f"Type détecté: {type_evt}")  # "ASSURANCE_PRET"

# Marquer comme traité
gestionnaire.marquer_phase_traitement(evt_id, phase=1)
```

---

### 5. `detecteurs_evenements.py`

**Rôle**: Détecteurs spécialisés pour identifier les types d'événements

**Architecture**:
```
DetecteurBase (classe abstraite)
    ├── Phase 1 (Simples - patterns fixes)
    │   ├── DetecteurAssurancePret
    │   ├── DetecteurFraisBancaires
    │   └── DetecteurHonorairesComptable
    │
    ├── Phase 2 (Référence - lookup tables)
    │   ├── DetecteurRemboursementPret (à implémenter)
    │   └── DetecteurApportAssocie (à implémenter)
    │
    └── Phase 3 (Complexes - calculs)
        ├── DetecteurRevenuSCPI (à implémenter)
        └── DetecteurAchatValeursMobilieres (à implémenter)
```

#### Phase 1 - Détecteurs Implémentés

##### 1. `DetecteurAssurancePret`

**Pattern détecté**:
- Libellé: COVEA, ASSURANCE PRET, COTISATION ASSURANCE
- Montant: 87,57€ (±10 centimes)
- Type: DEBIT
- Fréquence: Mensuel (15 du mois)

**Comptabilisation**:
```
Débit 616 (Assurances emprunteur) : 87,57€
Crédit 512 (Banque LCL)            : 87,57€
```

**Note**: Assurance UNIQUEMENT pour le prêt AMORTISSABLE (LCL - BRM0911AH)

##### 2. `DetecteurFraisBancaires`

**Pattern détecté**:
- Libellé: FRAIS, TENUE DE COMPTE, GESTION COMPTE, COTISATION CARTE
- Montant: < 50€
- Type: DEBIT
- Fréquence: Mensuel ou trimestriel

**Comptabilisation**:
```
Débit 627 (Frais bancaires) : XX,XX€ TTC
Crédit 512 (Banque LCL)      : XX,XX€
```

**Note**: Montant TTC intégral (Soeurise NON soumise à TVA)

##### 3. `DetecteurHonorairesComptable`

**Pattern détecté**:
- Libellé: COMPTABLE, EXPERT COMPTABLE, HONORAIRES, LIASSE FISCALE
- Montant: 50€ - 1000€
- Type: DEBIT
- Fréquence: Trimestriel ou annuel

**Comptabilisation**:
```
Débit 622 (Honoraires expert-comptable) : XXX,XX€ TTC
Crédit 512 (Banque LCL)                  : XXX,XX€
```

**Note**: Montant TTC intégral (Soeurise NON soumise à TVA)

**Utilisation**:
```python
from detecteurs_evenements import FactoryDetecteurs
from models_module2 import get_session

session = get_session(DATABASE_URL)

evenement = {
    'date_operation': '2024-01-15',
    'libelle': 'PRLV SEPA COVEA RISKS',
    'libelle_normalise': 'prlv sepa covea risks',
    'montant': 87.57,
    'type_operation': 'DEBIT'
}

# Détecter et générer proposition
proposition = FactoryDetecteurs.detecter_et_proposer(session, evenement, phase=1)

if proposition:
    print(f"Type: {proposition['type_evenement']}")
    print(f"Confiance: {proposition['confiance']}")
    print(f"Écritures: {len(proposition['ecritures'])}")
    for ecriture in proposition['ecritures']:
        print(f"  {ecriture['compte_debit']} → {ecriture['compte_credit']}: {ecriture['montant']}€")
```

**Tests unitaires intégrés**:
```bash
python detecteurs_evenements.py
```

---

### 6. `models_module2.py` (mis à jour)

**Modifications**:
- Ajout de 4 nouvelles classes ORM:
  - `PortefeuilleValeursMobilieres`
  - `MouvementPortefeuille`
  - `ComptesCourantsAssocies`
  - `MouvementCompteCourant`

- Relations bidirectionnelles configurées
- Indexes créés pour performance

---

## 🔄 Workflow Complet Phase 1

```
1. EXTRACTION (externe)
   ↓
   PDF relevés bancaires → Extraction événements

2. CRÉATION
   ↓
   Pour chaque événement extrait:
     - Calculer fingerprint
     - Vérifier doublon
     - Si nouveau: Insérer en BD

3. DÉTECTION
   ↓
   Pour chaque événement en attente:
     - Tester détecteurs Phase 1
     - Si reconnu: Générer proposition
     - Marquer type d'événement

4. VALIDATION (externe)
   ↓
   Utilisateur valide/rejette les propositions

5. CRÉATION ÉCRITURES
   ↓
   Pour chaque proposition validée:
     - Créer écriture(s) comptable(s)
     - Marquer événement comme VALIDE
     - Marquer phase_traitement = 1
```

---

## 🧪 Tests et Validation

### Tests unitaires disponibles:

1. **Détection de doublons**:
   ```bash
   python detection_doublons.py
   ```

2. **Détecteurs Phase 1**:
   ```bash
   python detecteurs_evenements.py
   ```

### Tests d'intégration (sur Render):

1. **Appliquer la migration**:
   ```bash
   python migration_evenements_comptables.py
   ```

2. **Vérifier les nouvelles colonnes**:
   ```sql
   SELECT column_name, data_type
   FROM information_schema.columns
   WHERE table_name = 'evenements_comptables'
   ORDER BY ordinal_position;
   ```

3. **Tester la création d'événements**:
   ```python
   from gestionnaire_evenements import GestionnaireEvenements
   from models_module2 import get_session
   import os

   session = get_session(os.getenv('DATABASE_URL'))
   gestionnaire = GestionnaireEvenements(session, phase=1)

   # Test événement
   evt_id = gestionnaire.creer_evenement({
       'date_operation': '2024-01-15',
       'libelle': 'TEST PRLV SEPA COVEA RISKS',
       'montant': 87.57,
       'type_operation': 'DEBIT',
       'email_from': 'test@test.com',
       'email_body': 'Test'
   })

   print(f"✅ Événement créé: #{evt_id}")

   # Test doublon
   evt_id2 = gestionnaire.creer_evenement({
       'date_operation': '2024-01-15',
       'libelle': 'TEST PRLV SEPA COVEA RISKS',
       'montant': 87.57,
       'type_operation': 'DEBIT',
       'email_from': 'test@test.com',
       'email_body': 'Test'
   })

   if evt_id2 is None:
       print("✅ Doublon détecté correctement")
   ```

---

## 📊 Statistiques et Monitoring

### Obtenir statistiques globales:

```python
from gestionnaire_evenements import GestionnaireEvenements, afficher_statistiques
from models_module2 import get_session
import os

session = get_session(os.getenv('DATABASE_URL'))
gestionnaire = GestionnaireEvenements(session, phase=1)

# Afficher statistiques
afficher_statistiques(gestionnaire)
```

**Sortie exemple**:
```
================================================================================
STATISTIQUES ÉVÉNEMENTS COMPTABLES
================================================================================

📊 Total événements: 150

Par statut:
  - EN_ATTENTE: 120
  - VALIDE: 25
  - ERREUR: 5

Par phase:
  - Phase 1: 25

Par type:
  - ASSURANCE_PRET: 9
  - FRAIS_BANCAIRES: 9
  - HONORAIRES_COMPTABLE: 3
```

---

## 🚀 Prochaines Étapes

### Phase 2 (Référence - lookup tables):
- [ ] `DetecteurRemboursementPret`: Ventilation intérêts/capital via `echeances_prets`
- [ ] `DetecteurApportAssocie`: Identification apports Ulrik
- [ ] Générateurs de propositions Phase 2

### Phase 3 (Complexe - calculs):
- [ ] `DetecteurRevenuSCPI`: Différenciation revenus/capital
- [ ] `DetecteurAchatValeursMobilieres`: Calcul PRU, mise à jour portefeuille
- [ ] `GenerateurRapports`: Grand Livre, Compte d'Exploitation, Balance

### Intégration Module 2:
- [ ] Connecter avec `module2_workflow_v2.py`
- [ ] Workflow complet: PDF → Événements → Propositions → Écritures
- [ ] Email validation workflow

---

## 🛡️ Sécurité et Bonnes Pratiques

### ✅ Implémenté:
- Détection de doublons via fingerprinting
- Mode dry_run pour nettoyage
- Sauvegardes automatiques avant suppression
- Validation des données avant insertion
- Transactions avec rollback en cas d'erreur

### ⚠️ À faire attention:
- Toujours tester sur environnement de développement d'abord
- Sauvegarder la base avant toute migration en production
- Utiliser `nettoyage_bd.py` UNIQUEMENT en développement
- Vérifier les propositions avant validation définitive

---

## 📚 Documentation Connexe

- `SPECIFICATIONS_TECHNIQUES_EVENEMENTS.md`: Spécifications complètes
- `CORRECTIONS_ANALYSE_EVENEMENTS_2024.md`: Corrections et clarifications
- `ANALYSE_EVENEMENTS_COMPTABLES_2024.md`: Analyse des événements Q1-Q3 2024
- `ARCHITECTURE.md`: Architecture globale du système

---

**Auteur**: Claude Code Assistant
**Date de création**: 05/11/2025
**Dernière mise à jour**: 05/11/2025
**Statut**: ✅ Phase 1 implémentée - En attente de tests sur Render
