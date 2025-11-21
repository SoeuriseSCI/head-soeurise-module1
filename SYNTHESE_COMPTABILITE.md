# Synthèse Solution Comptable - SCI Soeurise

**Version** : 1.1
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

### 1.5 Principe Simplificateur : Cut-off et Extourne

La SCI applique un **principe de cut-off simplifié** avec extourne systématique :

#### Écritures de cut-off (fin d'exercice N)
À la clôture, on comptabilise les produits et charges rattachables à l'exercice N même si leur facturation ou règlement n'intervient qu'en N+1 :

| Type | Compte | Exemple |
|------|--------|---------|
| **Produits à recevoir (PAR)** | 4181 | Dividendes SCPI déclarés mais non versés |
| **Charges à payer (CAP)** | 4081 | Honoraires comptables, intérêts courus |
| **Charges constatées d'avance (CCA)** | 486 | Assurance payée d'avance |
| **Produits constatés d'avance (PCA)** | 487 | Loyers perçus d'avance |

#### Extourne (début d'exercice N+1)
Les écritures de cut-off sont **systématiquement extournées** au 1er janvier N+1 :
- L'écriture initiale est passée en sens inverse
- Cela évite les doubles comptabilisations lors du règlement effectif

**Avantage** : Ce mécanisme automatique simplifie le rapprochement car chaque règlement bancaire en N+1 génère une écriture "normale" sans avoir à vérifier si elle a déjà été provisionnée.

### 1.6 Rapprochement Simplifié : Relevés Bancaires comme Source

#### Contexte favorable de la SCI
La SCI Soeurise bénéficie d'un contexte simplifiant :
- **Pas de caisse** : Aucune opération en espèces
- **Compte bancaire unique** : Toutes les opérations passent par le compte 512
- → **Conséquence** : Chaque événement comptable apparaît sur le relevé bancaire

#### Principe : Le relevé bancaire fait foi
```
┌─────────────────────────────────────────────────────────────────┐
│                    HIÉRARCHIE DES SOURCES                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  RELEVÉ BANCAIRE (source primaire)                             │
│       │                                                         │
│       │  → Génère les écritures comptables                     │
│       │  → Date, montant, sens (débit/crédit)                  │
│       │                                                         │
│       ▼                                                         │
│  DOCUMENTS JUSTIFICATIFS (enrichissement)                       │
│       │                                                         │
│       │  → Conservés pour traçabilité et preuve                │
│       │  → Permettent la ventilation détaillée                 │
│       │                                                         │
│       ▼                                                         │
│  ÉCRITURE COMPTABLE (résultat)                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### Cas nécessitant les documents justificatifs

| Situation | Document requis | Raison |
|-----------|-----------------|--------|
| **Échéance de prêt** | Tableau d'amortissement | Ventilation intérêts (661) / capital (164) |
| **Opération sur titres** | Avis d'opération | Commissions, frais, ISIN, PRU |
| **Dividendes SCPI** | Bulletin de versement | Répartition par SCPI, retenue à la source |
| **Apport compte courant** | Avis d'opération crédit | Identification de l'associé (455) |

#### Documents conservés (traçabilité)
Même si le relevé suffit pour la comptabilisation courante, les documents suivants sont **archivés** :
- Factures (assurance, honoraires, frais bancaires)
- Bulletins de versement des revenus SCPI
- Avis d'opération sur valeurs mobilières
- Tableaux d'amortissement des prêts
- Relevés de compte bancaire

---

## 2. Rôle du Gérant et Interventions Requises

### 2.1 Principe : Validation Humaine Obligatoire

Le système _Head.Soeurise fonctionne en **mode semi-automatique** : il propose, le gérant valide.

**Pourquoi ?**
- Responsabilité légale du gérant sur les comptes
- Détection d'anomalies par l'œil humain
- Arbitrages comptables parfois nécessaires

### 2.2 Moments Clés Requérant l'Intervention du Gérant

```
┌─────────────────────────────────────────────────────────────────┐
│              INTERVENTIONS DU GÉRANT (par email)                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📧 TOUT AU LONG DE L'ANNÉE                                    │
│  ├── Communication des événements comptables                    │
│  │   (relevés, factures, avis d'opération)                     │
│  └── Validation des propositions d'écritures                   │
│                                                                 │
│  📧 FIN D'EXERCICE (décembre)                                  │
│  ├── Identification des éléments de cut-off :                  │
│  │   • Produits acquis mais non encaissés (PAR)                │
│  │   • Charges engagées mais non facturées (CAP)               │
│  │   • Intérêts courus non échus                               │
│  └── Validation des écritures de régularisation                │
│                                                                 │
│  📧 PRÉ-CLÔTURE (janvier-février N+1)                          │
│  ├── Revue du bilan provisoire                                 │
│  ├── Vérification du compte de résultat                        │
│  └── Signalement des corrections à apporter                    │
│                                                                 │
│  📧 CLÔTURE DÉFINITIVE (après AG, avril N+1)                   │
│  ├── Transmission du PV d'AG                                   │
│  ├── Confirmation de l'affectation du résultat                 │
│  └── Autorisation de clôture définitive                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Détail des Interventions

#### A. Communication des événements comptables (continu)

| Document | Fréquence | Action gérant |
|----------|-----------|---------------|
| Relevé bancaire mensuel | Mensuelle | Transmettre par email |
| Factures reçues | À réception | Scanner et transmettre |
| Avis d'opération (titres, prêts) | À réception | Transmettre |
| Bulletins dividendes SCPI | Trimestrielle | Transmettre |

#### B. Cut-off de fin d'année (décembre)

Le gérant doit **explicitement identifier** :
- Les revenus SCPI du T4 non encore versés → PAR (4181)
- Les honoraires du CAC/expert-comptable → CAP (4081)
- Les intérêts d'emprunt courus au 31/12 → CAP (4081)
- L'assurance payée couvrant N+1 → CCA (486)

**Email type** : "Pour le cut-off 2024, voici les éléments à provisionner : ..."

#### C. Pré-clôture (janvier-février N+1)

Le système génère les états financiers provisoires. Le gérant doit :
1. **Vérifier la cohérence** des soldes de comptes
2. **Identifier les anomalies** (montants inhabituels, comptes déséquilibrés)
3. **Demander les corrections** nécessaires

#### D. Clôture définitive (après AG)

Séquence obligatoire :
1. L'AG approuve les comptes (PV signé)
2. Le gérant transmet le PV par email
3. Le système exécute la clôture (`cloture_exercice.py --execute`)
4. Les écritures d'affectation sont générées sur N+1

**⚠️ CRITIQUE** : Aucune clôture définitive sans validation explicite du gérant après AG.

---

## 3. Architecture des Traitements

### 3.1 Vue d'Ensemble

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

### 3.2 Modules Principaux

| Module | Rôle |
|--------|------|
| `main.py` | Application Flask, réveil quotidien, traitement emails |
| `models_module2.py` | Modèles SQLAlchemy (ORM) |
| `module2_workflow_v2.py` | Workflow comptabilité automatisée |
| `cloture_exercice.py` | Clôture d'exercice (5 étapes) |
| `export_cerfa.py` | Génération données Cerfa (JSON) |
| `generer_cerfa_pdf.py` | Génération PDF des formulaires |
| `construire_etats_financiers_2024.py` | Bilan + Compte de résultat |

### 3.3 Tables PostgreSQL

| Table | Contenu |
|-------|---------|
| `exercices_comptables` | Exercices (2023, 2024, 2025...) |
| `plans_comptes` | Plan comptable SCI |
| `ecritures_comptables` | Journal des écritures |
| `prets_immobiliers` | Données des prêts (capital, taux, durée) |
| `echeances_prets` | Échéancier détaillé (intérêts/capital) |
| `evenements_comptables` | Queue de traitement emails |
| `propositions_en_attente` | Écritures à valider par Ulrik |

### 3.4 Processus de Clôture (cloture_exercice.py)

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

## 4. Limites d'Utilisation

### 4.1 Ce que le système FAIT

- ✅ Comptabilisation des opérations bancaires (relevés)
- ✅ Ventilation automatique intérêts/capital des prêts
- ✅ Calcul du résultat comptable
- ✅ Calcul de l'IS avec déficit reportable
- ✅ Génération des états financiers (Bilan, Compte de résultat)
- ✅ Génération des formulaires Cerfa pré-remplis (2065, 2033-A/B/F)
- ✅ Clôture d'exercice avec affectation du résultat

### 4.2 Ce que le système NE FAIT PAS

- ❌ Télédéclaration automatique sur impots.gouv.fr
- ❌ Gestion de la TVA (SCI non assujettie)
- ❌ Gestion des immobilisations avec amortissements
- ❌ Rapprochement bancaire automatique complet
- ❌ Multi-devises
- ❌ Gestion des notes de frais
- ❌ Interface utilisateur graphique (CLI uniquement)

### 4.3 Prérequis Techniques

| Élément | Requis |
|---------|--------|
| Python | 3.10+ |
| PostgreSQL | 13+ |
| Dépendances | sqlalchemy, psycopg2-binary, reportlab |
| Hébergement | Render.com (ou équivalent) |
| Variable d'environnement | `DATABASE_URL` |

### 4.4 Points d'Attention

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

## 5. Guide d'Utilisation

### 5.1 Configuration Initiale

```bash
# 1. Cloner le repository
git clone https://github.com/SoeuriseSCI/head-soeurise-module1.git
cd head-soeurise-module1

# 2. Créer le fichier .env
echo 'DATABASE_URL=postgresql://user:password@host/dbname' > .env

# 3. Installer les dépendances
pip install sqlalchemy psycopg2-binary reportlab
```

### 5.2 Commandes Courantes

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

### 5.3 Formulaires Cerfa Générés

| Formulaire | Fichier | Contenu |
|------------|---------|---------|
| 2065 | Page 1 du PDF | Déclaration de résultats IS |
| 2033-A | Page 2 du PDF | Bilan simplifié (Actif/Passif) |
| 2033-B | Page 3 du PDF | Compte de résultat simplifié |
| 2033-F | Page 4 du PDF | Composition du capital |

### 5.4 Workflow Annuel Recommandé

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

## 6. Évolutions Futures

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

## 7. Contacts et Support

- **Email SCI** : u6334452013@gmail.com
- **Gérant** : Ulrik BERGSTEN
- **Repository** : https://github.com/SoeuriseSCI/head-soeurise-module1

---

*Document généré automatiquement par _Head.Soeurise*
