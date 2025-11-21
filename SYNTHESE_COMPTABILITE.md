# Synthèse Solution Comptable - SCI Soeurise

**Version** : 1.0
**Date** : 21 novembre 2025
**Auteur** : _Head.Soeurise / Claude Code

---

## 1. Principes Comptables

### 1.1 Contexte de la SCI

| Élément | Valeur |
|---------|--------|
| Dénomination | SOEURISE |
| Forme juridique | Société Civile |
| SIRET | 910 574 862 00010 |
| Régime fiscal | **IS** (Impôt sur les Sociétés) |
| Régime d'imposition | RSI (Régime Simplifié) |
| Capital | 1 000 € |
| Clôture | 31 décembre |

### 1.2 Plan Comptable Utilisé

La SCI utilise un plan comptable simplifié adapté à son activité :

| Classe | Usage | Comptes principaux |
|--------|-------|-------------------|
| 1 | Capitaux | 101 (Capital), 119 (RAN débiteur), 164 (Emprunts) |
| 2 | Immobilisations | 271, 273 (Titres SCPI) |
| 4 | Tiers | 455 (CC Associés), 4081 (FNP), 4181 (PAR) |
| 5 | Financiers | 512 (Banque) |
| 6 | Charges | 616 (Assurance), 6226 (Honoraires), 661 (Intérêts) |
| 7 | Produits | 761 (Participations SCPI), 768 (Autres produits) |

### 1.3 Conventions Comptables

#### Compte 89 - Bilan d'Ouverture
- Utilisé comme contrepartie universelle pour initialiser le bilan
- Doit être soldé (débit = crédit) après écritures d'ouverture

#### Report à Nouveau
- **Compte 110** : Report à nouveau créditeur (bénéfices antérieurs)
- **Compte 119** : Report à nouveau débiteur (déficits antérieurs)
- **Compte 120** : Résultat de l'exercice (bénéfice)
- **Compte 129** : Résultat de l'exercice (perte)

#### Déficit Reportable et IS
Le résultat fiscal est calculé ainsi :
```
Résultat fiscal = Résultat comptable - Déficit reportable
Si Résultat fiscal ≤ 0 → IS = 0
Sinon → IS = 15% (jusqu'à 42 500€) + 25% (au-delà)
```

### 1.4 Règles d'Affectation du Résultat

**IMPORTANT** : L'affectation du résultat par l'AG est comptabilisée sur l'exercice **N+1**, pas N.

| Situation | Écriture | Exercice |
|-----------|----------|----------|
| Bénéfice absorbant déficit | Débit 120 / Crédit 119 | N+1 |
| Bénéfice en report | Débit 120 / Crédit 110 | N+1 |
| Perte | Débit 119 / Crédit 129 | N+1 |

---

## 2. Architecture des Traitements

### 2.1 Vue d'Ensemble

```
┌─────────────────────────────────────────────────────────────────┐
│                     FLUX DE TRAITEMENT                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  EMAILS (Gmail)                                                 │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────────┐                                           │
│  │ main.py         │  Réveil quotidien 08:00 UTC               │
│  │ (Flask + Sched) │                                           │
│  └────────┬────────┘                                           │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐     ┌─────────────────┐                   │
│  │ Détection       │────▶│ Propositions    │                   │
│  │ événements      │     │ en attente      │                   │
│  └─────────────────┘     └────────┬────────┘                   │
│                                   │                             │
│                          Validation Ulrik                       │
│                                   │                             │
│                                   ▼                             │
│  ┌─────────────────┐     ┌─────────────────┐                   │
│  │ PostgreSQL      │◀────│ Écritures       │                   │
│  │ (données)       │     │ comptables      │                   │
│  └────────┬────────┘     └─────────────────┘                   │
│           │                                                     │
│           ▼                                                     │
│  ┌─────────────────┐     ┌─────────────────┐                   │
│  │ export_cerfa.py │────▶│ JSON + PDF      │                   │
│  │                 │     │ (déclarations)  │                   │
│  └─────────────────┘     └─────────────────┘                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Modules Principaux

| Module | Rôle |
|--------|------|
| `main.py` | Application Flask, réveil quotidien, traitement emails |
| `models_module2.py` | Modèles SQLAlchemy (ORM) |
| `module2_workflow_v2.py` | Workflow comptabilité automatisée |
| `cloture_exercice.py` | Clôture d'exercice (5 étapes) |
| `export_cerfa.py` | Génération données Cerfa (JSON) |
| `generer_cerfa_pdf.py` | Génération PDF des formulaires |
| `construire_etats_financiers_2024.py` | Bilan + Compte de résultat |

### 2.3 Tables PostgreSQL

| Table | Contenu |
|-------|---------|
| `exercices_comptables` | Exercices (2023, 2024, 2025...) |
| `plans_comptes` | Plan comptable SCI |
| `ecritures_comptables` | Journal des écritures |
| `prets_immobiliers` | Données des prêts (capital, taux, durée) |
| `echeances_prets` | Échéancier détaillé (intérêts/capital) |
| `evenements_comptables` | Queue de traitement emails |
| `propositions_en_attente` | Écritures à valider par Ulrik |

### 2.4 Processus de Clôture (cloture_exercice.py)

```
ÉTAPE 1 : Calcul du résultat
    └─▶ Somme produits - Somme charges
    └─▶ Identification déficit reportable

ÉTAPE 2 : Affectation du résultat (sur N+1)
    └─▶ Protection anti-doublon ✓
    └─▶ Création écriture affectation
    └─▶ Date : 01/01/N+1

ÉTAPE 3 : Gel de l'exercice
    └─▶ Passage statut CLOTURE

ÉTAPE 4 : Bilan d'ouverture N+1
    └─▶ Reprise des soldes

ÉTAPE 5 : Vérification extournes
    └─▶ Contrôle cut-off
```

---

## 3. Limites d'Utilisation

### 3.1 Ce que le système FAIT

- ✅ Comptabilisation des opérations bancaires (relevés)
- ✅ Ventilation automatique intérêts/capital des prêts
- ✅ Calcul du résultat comptable
- ✅ Calcul de l'IS avec déficit reportable
- ✅ Génération des états financiers (Bilan, Compte de résultat)
- ✅ Génération des formulaires Cerfa pré-remplis (2065, 2033-A/B/F)
- ✅ Clôture d'exercice avec affectation du résultat

### 3.2 Ce que le système NE FAIT PAS

- ❌ Télédéclaration automatique sur impots.gouv.fr
- ❌ Gestion de la TVA (SCI non assujettie)
- ❌ Gestion des immobilisations avec amortissements
- ❌ Rapprochement bancaire automatique complet
- ❌ Multi-devises
- ❌ Gestion des notes de frais
- ❌ Interface utilisateur graphique (CLI uniquement)

### 3.3 Prérequis Techniques

| Élément | Requis |
|---------|--------|
| Python | 3.10+ |
| PostgreSQL | 13+ |
| Dépendances | sqlalchemy, psycopg2-binary, reportlab |
| Hébergement | Render.com (ou équivalent) |
| Variable d'environnement | `DATABASE_URL` |

### 3.4 Points d'Attention

#### Doublons
- Protection anti-doublon sur les écritures d'affectation
- Garbage collection automatique (7 jours) sur événements/propositions

#### Exercices Comptables
- L'affectation du résultat se fait sur N+1, PAS sur N
- Les Cerfa sont établis AVANT affectation

#### Précision Numérique
- Utiliser `Decimal` pour les montants (pas `float`)
- Arrondir à 2 décimales pour l'affichage

---

## 4. Guide d'Utilisation

### 4.1 Configuration Initiale

```bash
# 1. Cloner le repository
git clone https://github.com/SoeuriseSCI/head-soeurise-module1.git
cd head-soeurise-module1

# 2. Créer le fichier .env
echo 'DATABASE_URL=postgresql://user:password@host/dbname' > .env

# 3. Installer les dépendances
pip install sqlalchemy psycopg2-binary reportlab
```

### 4.2 Commandes Courantes

#### Générer les états financiers

```bash
# États financiers complets (Bilan + Compte de résultat)
DATABASE_URL="..." python construire_etats_financiers_2024.py
```

#### Générer les Cerfa

```bash
# Étape 1 : Générer le JSON
DATABASE_URL="..." python export_cerfa.py 2024

# Étape 2 : Générer le PDF
python generer_cerfa_pdf.py cerfa_2024_XXXXXX.json
```

#### Clôturer un exercice

```bash
# Mode simulation (dry-run)
DATABASE_URL="..." python cloture_exercice.py 2024 --pv-ag "[PV AG]"

# Exécution réelle
DATABASE_URL="..." python cloture_exercice.py 2024 --pv-ag "[PV AG]" --execute
```

#### Sauvegarder la base

```bash
# Format JSON
python sauvegarder_base.py

# Format SQL dump
bash sauvegarder_base.sh
```

#### Vérifier la cohérence

```bash
# Vérifier le bilan 2023
python verifier_bilan_2023.py

# Analyser l'exercice 2024
DATABASE_URL="..." python analyser_exercice_2024.py
```

### 4.3 Formulaires Cerfa Générés

| Formulaire | Fichier | Contenu |
|------------|---------|---------|
| 2065 | Page 1 du PDF | Déclaration de résultats IS |
| 2033-A | Page 2 du PDF | Bilan simplifié (Actif/Passif) |
| 2033-B | Page 3 du PDF | Compte de résultat simplifié |
| 2033-F | Page 4 du PDF | Composition du capital |

### 4.4 Workflow Annuel Recommandé

```
JANVIER N+1
├── Vérifier écritures de l'exercice N
├── Générer états financiers provisoires
└── Identifier anomalies éventuelles

FÉVRIER-MARS N+1
├── Corriger les anomalies
├── Passer les écritures de régularisation (cut-off)
└── Générer états financiers définitifs

AVRIL N+1
├── Tenir l'AG (approbation des comptes)
├── Clôturer l'exercice N (cloture_exercice.py --execute)
└── Affectation du résultat (automatique sur N+1)

MAI N+1 (avant le 15)
├── Générer les Cerfa (export_cerfa.py + generer_cerfa_pdf.py)
├── Télédéclarer sur impots.gouv.fr
└── Payer l'IS si applicable
```

---

## 5. Évolutions Futures

### Court terme
- [ ] Amélioration du rapprochement bancaire automatique
- [ ] Gestion des plus/moins-values sur titres

### Moyen terme
- [ ] Interface web pour validation des propositions
- [ ] Export EDI-TDFC (télétransmission directe)

### Long terme
- [ ] Module de gestion du portefeuille de valeurs mobilières
- [ ] Tableaux de bord et analytics

---

## 6. Contacts et Support

- **Email SCI** : u6334452013@gmail.com
- **Gérant** : Ulrik BERGSTEN
- **Repository** : https://github.com/SoeuriseSCI/head-soeurise-module1

---

*Document généré automatiquement par _Head.Soeurise*
