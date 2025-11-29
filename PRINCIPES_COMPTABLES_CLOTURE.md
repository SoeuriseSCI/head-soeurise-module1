# Principes Comptables - Clôture d'Exercice

> Documentation technique sur le processus de pré-clôture et clôture définitive d'exercice comptable
> SCI Soeurise - Régime IS
> Créé le : 29/11/2025

---

## Table des matières

1. [Comptes de Bilan vs Comptes de Flux](#comptes-de-bilan-vs-comptes-de-flux)
2. [Le Compte 120 - Résultat de l'Exercice](#le-compte-120---résultat-de-lexercice)
3. [Processus de Pré-Clôture](#processus-de-pré-clôture)
4. [Processus de Clôture Définitive](#processus-de-clôture-définitive)
5. [Schéma Chronologique Complet](#schéma-chronologique-complet)
6. [Règles Comptables Appliquées](#règles-comptables-appliquées)

---

## Comptes de Bilan vs Comptes de Flux

### 🏦 Comptes de BILAN (Classes 1-5) - STOCKS

**Nature** : Photographie à un instant T

**Classes** :
- **1** : Capitaux propres et dettes financières (Capital, RAN, Emprunts)
- **2** : Immobilisations (Titres, Terrains, Constructions)
- **3** : Stocks (matières premières, produits finis)
- **4** : Tiers (Clients, Fournisseurs, Comptes courants)
- **5** : Financiers (Banque, Caisse, VMP)

**Caractéristiques** :
- ✅ **Cumulatifs** : Le solde se reporte d'un exercice à l'autre
- ✅ **Permanents** : Ne se soldent JAMAIS (sauf disparition de l'élément)
- ✅ **Bilan d'ouverture N+1** = Bilan de clôture N

**Exemple** :
```
Compte 512 (Banque) au 31/12/2024 : 2,320.35€
→ Bilan d'ouverture 01/01/2025 : 2,320.35€ (repris tel quel)
→ Les mouvements 2025 s'ajoutent au solde existant
```

---

### 💰 Comptes de FLUX (Classes 6-7) - FLUX

**Nature** : Film sur une période

**Classes** :
- **6** : Charges (Achats, Salaires, Loyers, Intérêts)
- **7** : Produits (Ventes, Revenus locatifs, Intérêts perçus)

**Caractéristiques** :
- ✅ **Périodiques** : Mesurent les flux pendant l'exercice
- ✅ **Soldés en fin d'exercice** : Repartent à zéro au 01/01
- ✅ **Ne passent PAS dans le bilan d'ouverture**
- ✅ **Différence 7x - 6x** = Résultat de l'exercice

**Exemple** :
```
Exercice 2024 :
  Compte 761 (Revenus SCPI) : 26,395.92€ (flux annuel cumulé)
  Compte 661 (Intérêts)     :  5,610.73€ (flux annuel cumulé)

Au 31/12/2024 :
  → Résultat = 26,395.92 - 8,629.63 = 17,766.29€

Au 01/01/2025 :
  → Compte 761 : 0.00€ (repart à zéro pour 2025)
  → Compte 661 : 0.00€ (repart à zéro pour 2025)
  → Le résultat est transféré au compte 110 (RAN)
```

---

### 📊 Tableau Comparatif

| Aspect | Comptes BILAN (1-5) | Comptes FLUX (6-7) |
|--------|---------------------|-------------------|
| **Type** | STOCKS (photo) | FLUX (film) |
| **Durée** | Permanent | Annuel |
| **Report** | OUI (bilan d'ouverture) | NON (repart à zéro) |
| **Solde** | Cumulatif | Périodique |
| **Exemple** | Banque, Immobilisations | Loyers, Revenus |

**Règle d'or** :
- Comptes de **BILAN** = ce que la société **possède/doit**
- Comptes de **FLUX** = ce que la société **gagne/dépense** pendant l'année

---

## Le Compte 120 - Résultat de l'Exercice

### Particularité du compte 120

Le compte 120 est **TRÈS spécial** car :

1. ❌ **Il n'existe PAS pendant l'exercice**
2. ✅ **Il est créé lors de la clôture définitive**
3. ✅ **Il vit le temps de 2 écritures** (reprise + affectation)
4. ✅ **Son solde final est toujours 0€**

### Cycle de vie du compte 120

```
Pendant exercice N (01/01 → 31/12)
  Compte 120 : N'EXISTE PAS
  Les comptes 6-7 accumulent les flux

Pré-clôture (décembre N)
  Compte 120 : N'EXISTE TOUJOURS PAS
  Résultat = calcul Python (7x - 6x)

Clôture définitive (01/01 N+1)
  ┌─ Écriture 1 : REPRISE RÉSULTAT
  │    Débit 89 / Crédit 120 : 17,766€
  │    → Compte 120 CRÉÉ avec solde créditeur
  │
  ├─ Écriture 2 : AFFECTATION
  │    Débit 120 / Crédit 110 : 17,766€
  │    → Compte 120 SOLDÉ
  │
  └─ État final : Compte 120 solde = 0€ ✅
```

### Pourquoi le compte 120 ?

**Principe comptable** : Les comptes 6-7 ne sont **JAMAIS soldés explicitement**.

Le compte 120 sert de **pont** pour transférer la différence (résultat) vers les capitaux propres (110 ou 119).

**Alternative théorique** (non appliquée) :
```
# On POURRAIT solder directement 6-7 vers 110
Débit 761 / Crédit 110 : 26,396€
Débit 110 / Crédit 661 : 5,611€
...

# Mais c'est INTERDIT par les normes comptables
❌ Les comptes 6-7 doivent garder leur solde au 31/12
```

---

## Processus de Pré-Clôture

### Quand : Décembre N (avant AG)

### Objectifs
1. Rattacher les charges/produits à l'exercice concerné (cutoffs)
2. Calculer le résultat prévisionnel
3. Préparer les documents pour l'AG

### Écritures créées

#### 1. Cutoffs - Produits à recevoir

```
Date: 31/12/2024
Exercice: 2024
Type: CUTOFF

Débit 4181 (Produits à recevoir) : 6,755€
Crédit 761 (Revenus SCPI)        : 6,755€

Libellé: "Cutoff 2024 - Revenus SCPI T4"
```

**Raison** : Les revenus du T4 2024 seront perçus en janvier 2025, mais ils concernent économiquement 2024.

---

#### 2. Cutoffs - Charges à payer

```
Date: 31/12/2024
Exercice: 2024
Type: CUTOFF

Débit 6226 (Honoraires)              : 622€
Crédit 4081 (Fournisseurs - FNP)     : 622€

Libellé: "Cutoff 2024 - Honoraires comptables"
```

**Raison** : Facture non encore reçue mais charge de 2024.

---

#### 3. Cutoffs - Intérêts courus

```
Date: 31/12/2024
Exercice: 2024
Type: CUTOFF

Débit 661 (Intérêts)           : 254€
Crédit 1688 (Intérêts courus)  : 254€

Libellé: "Cutoff 2024 - Intérêts courus non échus"
```

**Raison** : Intérêts courus mais non encore échus au 31/12.

---

### Calcul du résultat (SANS ÉCRITURE)

**Code Python** :
```python
# precloture_exercice.py
resultat_brut = sum(produits_7x) - sum(charges_6x)
is_calcule = calculer_is(resultat_brut, deficit_reportable)
resultat_net = resultat_brut - is_calcule
```

**Exemple 2024** :
```
Produits (7x)     : 26,395.92€
Charges (6x)      :  8,629.63€
─────────────────────────────
Résultat brut     : 17,766.29€
IS (25%)          :      0.00€  (absorption déficit antérieur)
─────────────────────────────
Résultat net      : 17,766.29€
```

**⚠️ IMPORTANT** :
- ❌ Aucune écriture au compte 120
- ❌ Le compte 120 n'existe pas encore
- ✅ Le résultat est un **nombre calculé**, stocké dans un JSON

---

### État au 31/12/2024 après pré-clôture

```
Comptes de bilan (1-5) :
  271 (Titres)       : 500,032€ débiteur
  512 (Banque)       :   2,320€ débiteur
  164 (Emprunts)     : 486,251€ créditeur
  4181 (Prod. recevoir) : 6,755€ débiteur  ← Créé par cutoff
  ...

Comptes de flux (6-7) :
  761 (Revenus)      :  26,396€ créditeur  ← Incluant cutoff
  661 (Intérêts)     :   5,611€ débiteur   ← Incluant cutoff
  ...

Compte 120 (Résultat) : N'EXISTE PAS ❌
```

**Le résultat existe comme calcul** : 26,396 - 8,630 = 17,766€

---

### Proposition envoyée à Ulrik

```markdown
# Proposition Pré-clôture Exercice 2024

**Résultat brut** : 17,766.29€
**IS**            :     0.00€
**Résultat net**  : 17,766.29€

## Écritures proposées
3 écritures de cutoff seront créées

Token : ABC123
```

---

## Processus de Clôture Définitive

### Quand : Après AG (01/01/2025)

### Déclencheur

Email Ulrik :
```
Action: CLOTURE
Exercice: 2024
PV AG: Assemblée Générale du 15/03/2025
```

Puis validation :
```
[_Head] VALIDE: TOKEN_CLOTURE
```

---

### Écritures créées (TOUTES sur exercice 2025 !)

#### ÉTAPE 1 : Bilan d'ouverture 2025

**1A. Reprise des comptes de bilan (1-5)**

```
Date: 01/01/2025
Exercice: 2025
Type: BILAN_OUVERTURE

# ACTIF
Débit 271 / Crédit 89 : 500,032.00€  (Titres immobilisés)
Débit 273 / Crédit 89 :  25,760.63€  (Titres immobilisés)
Débit 4181 / Crédit 89 :  6,755.00€  (Produits à recevoir)
Débit 512 / Crédit 89 :   2,320.35€  (Banque)

# PASSIF
Débit 89 / Crédit 101 :   1,000.00€  (Capital)
Débit 119 / Crédit 89 :  36,148.00€  (RAN débiteur)
Débit 89 / Crédit 164 : 486,250.69€  (Emprunts)
Débit 89 / Crédit 290 :  50,003.00€  (Provision SCPI)
Débit 89 / Crédit 1688:     254.00€  (Intérêts courus)
Débit 89 / Crédit 4081:     622.00€  (FNP)
Débit 89 / Crédit 455 :  15,120.00€  (Comptes courants)
```

**À ce stade** : Compte 89 déséquilibré de -17,766.29€

---

**1B. Reprise du RÉSULTAT** ✨

```
Date: 01/01/2025
Exercice: 2025
Type: BILAN_OUVERTURE
Numéro: 2025-0101-OUV-RES

Débit 89 / Crédit 120 : 17,766.29€

Libellé: "Bilan d'ouverture 2025 - Résultat exercice 2024"
```

**🎯 C'EST ICI QUE LE COMPTE 120 EST CRÉÉ !**

**Résultat ÉTAPE 1** :
- Compte 89 : SOLDÉ (0€) ✅
- Compte 120 : Créditeur 17,766.29€ (nouvellement créé)

---

#### ÉTAPE 2 : Affectation du résultat

```
Date: 01/01/2025
Exercice: 2025
Type: AFFECTATION_RESULTAT
Numéro: 2025-0101-AFF-001

Débit 120 / Crédit 110 : 17,766.29€

Libellé: "Affectation résultat 2024 - Report à nouveau (PV AG du 15/03/2025)"
```

**Cas particuliers** :

**Si déficit antérieur à absorber** :
```
# Absorption totale ou partielle du déficit
Débit 120 / Crédit 119 : min(résultat, déficit)€

# Si reste après absorption
Débit 120 / Crédit 110 : (résultat - absorption)€
```

**Si perte (résultat < 0)** :
```
Débit 119 / Crédit 129 : abs(résultat)€
```

**Résultat ÉTAPE 2** :
- Compte 120 : SOLDÉ (0€) ✅
- Compte 110 : Créditeur +17,766.29€ (RAN créditeur)

---

#### ÉTAPE 3 : Extournes des cutoffs

**3A. Extourne produits à recevoir**

```
Date: 01/01/2025
Exercice: 2025
Type: CUTOFF

Débit 761 / Crédit 4181 : 6,755€

Libellé: "Extourne - Cutoff 2024 - Revenus SCPI T4"
```

**Raison** : Le cutoff 2024 a créé une créance fictive (4181). Quand le revenu sera vraiment perçu en 2025, il passera par 761. Sans extourne, on compterait le revenu deux fois.

---

**3B. Extourne charges à payer**

```
Date: 01/01/2025
Exercice: 2025
Type: CUTOFF

Débit 4081 / Crédit 6226 : 622€

Libellé: "Extourne - Cutoff 2024 - Honoraires comptables"
```

---

**3C. Extourne intérêts courus**

```
Date: 01/01/2025
Exercice: 2025
Type: CUTOFF

Débit 1688 / Crédit 661 : 254€

Libellé: "Extourne - Cutoff 2024 - Intérêts courus"
```

**Résultat ÉTAPE 3** :
- Comptes 4181, 4081, 1688 : SOLDÉS (0€)
- Les flux réels 2025 pourront être enregistrés normalement

---

#### ÉTAPE 4 : Marquage exercice 2024

```python
# Pas d'écriture, juste un changement de statut
exercice_2024.statut = 'CLOTURE'
```

---

### État final au 01/01/2025

**Comptes de bilan** :
```
271 (Titres)       : 500,032€ (repris de 2024)
512 (Banque)       :   2,320€ (repris de 2024)
164 (Emprunts)     : 486,251€ (repris de 2024)
110 (RAN créditeur):  17,766€ (résultat 2024 affecté) ✅
119 (RAN débiteur) : -36,148€ (repris de 2024)
...
```

**Comptes de flux** :
```
761 (Revenus)      :   6,755€ (extourne du cutoff, pas de flux réel 2025 encore)
661 (Intérêts)     :    -254€ (extourne du cutoff)
...
```

**Comptes techniques** :
```
89 (Bilan ouverture) :   0€ ✅ (soldé)
120 (Résultat)       :   0€ ✅ (soldé)
```

---

## Schéma Chronologique Complet

```
┌──────────────────────────────────────────────────────────────────┐
│              EXERCICE 2024 (01/01 → 31/12)                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Écritures courantes (toute l'année) :                           │
│    Débit 512 / Crédit 761 : 19,641€ (revenus réels)             │
│    Débit 661 / Crédit 512 :  5,357€ (intérêts réels)            │
│    Débit 6226 / Crédit 512 : 1,495€ (honoraires)                │
│    ...                                                           │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│  PRÉ-CLÔTURE (décembre 2024)                                     │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1️⃣ CUTOFFS (Écritures sur exercice 2024)                        │
│     Date: 31/12/2024                                             │
│     ─────────────────────────────────────────────────            │
│     Débit 4181 / Crédit 761 : 6,755€  (produits à recevoir)     │
│     Débit 6226 / Crédit 4081: 622€    (charges à payer)         │
│     Débit 661 / Crédit 1688 : 254€    (intérêts courus)         │
│                                                                  │
│  2️⃣ CALCUL RÉSULTAT (Python - pas d'écriture)                    │
│     Produits 7x : 26,396€                                        │
│     Charges 6x  :  8,630€                                        │
│     ─────────────────────                                        │
│     Résultat    : 17,766€ ← Stocké dans JSON, PAS dans compte   │
│                                                                  │
│  3️⃣ PROPOSITION envoyée à Ulrik                                  │
│     Token: ABC123                                                │
│                                                                  │
│  État au 31/12/2024 :                                            │
│    Comptes 1-5 : avec soldes finaux                              │
│    Comptes 6-7 : avec soldes finaux (incluant cutoffs)          │
│    Compte 120  : N'EXISTE PAS ❌                                 │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                              │
                              │ AG + Validation Ulrik
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│         CLÔTURE DÉFINITIVE (01/01/2025)                          │
├──────────────────────────────────────────────────────────────────┤
│  TOUTES les écritures ci-dessous :                               │
│    - Date: 01/01/2025                                            │
│    - Exercice: 2025 (pas 2024 !)                                │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│  ÉTAPE 1 : Bilan d'ouverture 2025                                │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1A. Reprise comptes 1-5 (Type: BILAN_OUVERTURE)                 │
│      ─────────────────────────────────────────────               │
│      Débit 271 / Crédit 89 : 500,032€                           │
│      Débit 512 / Crédit 89 :   2,320€                           │
│      Débit 89 / Crédit 164 : 486,251€                           │
│      Débit 119 / Crédit 89 :  36,148€                           │
│      ...                                                         │
│      → Compte 89 : -17,766€ (déséquilibré)                      │
│                                                                  │
│  1B. ✨ REPRISE RÉSULTAT (Type: BILAN_OUVERTURE)                 │
│      ─────────────────────────────────────────────               │
│      Débit 89 / Crédit 120 : 17,766€                            │
│      Numéro: 2025-0101-OUV-RES                                   │
│      → Compte 120 CRÉÉ avec solde créditeur                      │
│      → Compte 89 SOLDÉ (0€) ✅                                   │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│  ÉTAPE 2 : Affectation résultat                                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Type: AFFECTATION_RESULTAT                                      │
│  ─────────────────────────────────────────────                   │
│  Débit 120 / Crédit 110 : 17,766€                               │
│  Numéro: 2025-0101-AFF-001                                       │
│  → Compte 120 SOLDÉ (0€) ✅                                      │
│  → Compte 110 : +17,766€ (RAN créditeur)                        │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│  ÉTAPE 3 : Extournes cutoffs                                     │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Type: CUTOFF                                                    │
│  ─────────────────────────────────────────────                   │
│  Débit 761 / Crédit 4181 :  6,755€  (extourne prod. recevoir)   │
│  Débit 4081 / Crédit 6226:    622€  (extourne FNP)              │
│  Débit 1688 / Crédit 661 :    254€  (extourne int. courus)      │
│  → Comptes 4181, 4081, 1688 SOLDÉS                              │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│  ÉTAPE 4 : Marquage exercice                                     │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  exercice_2024.statut = 'CLOTURE'                                │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│         ÉTAT FINAL 01/01/2025                                    │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Comptes de BILAN repris de 2024 :                               │
│    271, 512, 164, 119, etc. → Valeurs 31/12/2024                │
│                                                                  │
│  Résultat 2024 intégré :                                         │
│    110 (RAN créditeur) : +17,766€ ✅                             │
│                                                                  │
│  Comptes de FLUX repartent à zéro :                              │
│    6x, 7x : nouveaux flux 2025                                   │
│                                                                  │
│  Comptes techniques soldés :                                     │
│    89 (Bilan ouverture) : 0€ ✅                                  │
│    120 (Résultat)       : 0€ ✅                                  │
│                                                                  │
│  Exercice 2024 : STATUT = CLOTURE ✅                             │
│  Exercice 2025 : STATUT = OUVERT   ✅                            │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Règles Comptables Appliquées

### 1. Indépendance des exercices

**Principe** : Chaque exercice doit enregistrer les charges/produits qui le concernent économiquement, même si le flux financier intervient sur un autre exercice.

**Application** : Cutoffs (4181, 4081, 1688) pour rattacher les opérations.

---

### 2. Non-solde des comptes 6-7

**Principe** : Les comptes de gestion (6-7) ne sont jamais soldés explicitement. Ils gardent leur solde au 31/12 et repartent à zéro au 01/01.

**Application** : Le compte 120 sert de pont pour transférer le résultat (différence 7x-6x) vers les capitaux propres.

---

### 3. Bilan d'ouverture = Bilan de clôture

**Principe** : Tous les comptes de bilan (1-5) doivent être repris à l'identique dans le bilan d'ouverture de l'exercice suivant.

**Application** : Écritures de bilan d'ouverture avec compte 89 comme contrepartie universelle.

---

### 4. Le résultat fait partie du bilan

**Principe** : Le résultat de l'exercice N fait partie du bilan de clôture N, même s'il n'est pas dans les comptes 1-5.

**Application** : L'écriture de reprise du résultat (Débit 89 / Crédit 120) intègre le résultat au bilan d'ouverture N+1.

---

### 5. Extourne des cutoffs

**Principe** : Les écritures de rattachement créent des créances/dettes fictives qui doivent être extournées au début de l'exercice suivant pour éviter les doubles comptes.

**Application** : Écritures inverses au 01/01/N+1 pour solder les comptes de cutoff.

---

### 6. Traçabilité et audit trail

**Principe** : Toutes les écritures doivent être tracées (source, valideur, date).

**Application** :
- `source_email_id` : ID de l'email déclencheur
- `source_email_from` : Émetteur de l'email
- `validee_at` : Date/heure de validation
- `validee_par` : Email du valideur
- `notes` : Contexte de validation

---

## Implémentation Technique

### Fichiers concernés

- **`precloture_exercice.py`** : Script de pré-clôture (cutoffs + calcul résultat)
- **`cloture_exercice.py`** : Script de clôture (bilan ouverture + affectation + extournes)
- **`module2_validations.py`** : Gestion validation et insertion écritures
  - Méthode : `inserer_cloture_definitive()`
- **`module2_workflow_v2.py`** : Orchestration workflow Module 2
  - Méthodes : `_traiter_pre_cloture_exercice()`, `_traiter_cloture_exercice()`

### Modèles de données

```python
class EcritureComptable:
    exercice_id: int              # Exercice concerné
    numero_ecriture: str          # Format: YYYY-MMDD-TYPE-NNN
    date_ecriture: date           # Date de l'écriture
    type_ecriture: str            # CUTOFF, BILAN_OUVERTURE, AFFECTATION_RESULTAT
    compte_debit: str             # Compte débité
    compte_credit: str            # Compte crédité
    montant: Decimal              # Montant
    source_email_id: str          # Traçabilité
    validee_at: datetime          # Audit trail
    validee_par: str              # Email valideur
```

---

## Questions Fréquentes

### Q1 : Pourquoi les écritures de clôture sont-elles sur l'exercice 2025 et pas 2024 ?

**R** : Parce qu'elles constituent le **bilan d'ouverture de 2025**, pas le bilan de clôture de 2024. Le bilan de clôture 2024 est l'état des comptes au 31/12/2024 après les cutoffs.

---

### Q2 : Pourquoi le compte 120 n'existe-t-il pas pendant l'exercice ?

**R** : Les normes comptables imposent que les comptes 6-7 gardent leur solde au 31/12. Le compte 120 sert uniquement de **compte de transition** pour transférer leur différence (résultat) vers les capitaux propres au moment de la clôture.

---

### Q3 : Que se passe-t-il si on ne fait pas les extournes ?

**R** : Les flux réels de 2025 s'ajouteraient aux cutoffs fictifs de 2024, créant des doubles comptes. Exemple :

```
Sans extourne :
  Compte 761 au 01/01/2025 : 6,755€ (cutoff 2024)
  + Revenus réels T4 payés en janvier : 6,755€
  = Total 761 : 13,510€ ❌ (double compte)

Avec extourne :
  Compte 761 au 01/01/2025 : 6,755€ (cutoff)
  - Extourne : -6,755€
  = Solde après extourne : 0€
  + Revenus réels T4 : 6,755€
  = Total 761 : 6,755€ ✅ (correct)
```

---

### Q4 : Pourquoi le bilan 2024 affiche-t-il un déséquilibre de +17,766€ ?

**R** : C'est **normal**. La formule comptable est :

```
ACTIF = PASSIF + RÉSULTAT
```

Donc :
```
ACTIF - PASSIF = RÉSULTAT
484,865€ - 467,099€ = 17,766€ ✅
```

Le résultat n'est pas "dans" le passif, il est dans une section séparée du bilan (ou dans le compte de résultat détaillé).

---

### Q5 : Peut-on éviter d'utiliser le compte 89 ?

**R** : Théoriquement oui, en créant chaque écriture de bilan d'ouverture avec sa contrepartie directe. Mais le compte 89 simplifie énormément :

```
Sans compte 89 (complexe) :
  Débit 271 / Crédit 164 : ???€  (quelle proportion ?)
  Débit 512 / Crédit 455 : ???€  (comment répartir ?)
  → Impossible à équilibrer proprement

Avec compte 89 (simple) :
  Débit 271 / Crédit 89 : 500,032€
  Débit 512 / Crédit 89 : 2,320€
  Débit 89 / Crédit 164 : 486,251€
  → Compte 89 s'équilibre automatiquement à 0€
```

---

## Historique

| Date | Version | Modification |
|------|---------|--------------|
| 29/11/2025 | 1.0 | Création initiale |

---

## Références

- Plan Comptable Général (PCG) français
- Code de commerce - Livre III
- Règlement ANC n°2014-03 relatif au PCG
- Architecture V6.1 - Module 2 SCI Soeurise

---

**Auteur** : Claude Code (Sonnet 4.5)
**Projet** : _Head.Soeurise - Module 2 Comptabilité
**Licence** : Usage interne SCI Soeurise
