# Corrections Requises - 03/11/2025

## 🎯 SOURCE DE VÉRITÉ ÉTABLIE

Les fichiers `PRET_A_ECHEANCES_REFERENCE.md` et `PRET_B_ECHEANCES_REFERENCE.md` contiennent les **valeurs réelles extraites des PDF originaux**.

---

## ✅ VALEURS CORRECTES (Source de Vérité)

### Convention de Nommage (Mémoire Courte)

La **mémoire courte** utilise cette convention :
- **PRÊT A** = LCL (SOLUTION P IMMO)
- **PRÊT B** = INVESTIMUR

### Prêt A - LCL (5009736BRM0911AH)

| Paramètre | Valeur Correcte |
|-----------|-----------------|
| **Banque** | LCL / SOLUTION P IMMO |
| **N° Prêt** | 5009736BRM0911AH |
| **Montant** | 250 000,00€ ✅ |
| **Taux annuel** | 1,050% ✅ |
| **Durée totale** | 252 mois (21 ans) |
| **Date début** | 15.04.2022 |
| **Date début amortissement** | 15.04.2023 |
| **Date fin** | **15.04.2043** ✅ |
| **Type** | AMORTISSEMENT_CONSTANT |
| **Structure** | 12 mois franchise (0€) + 240 mois amortissement |
| **Mensualité** | 1 166,59€ |
| **Échéances totales** | 252 |
| **Total intérêts** | **29 981,41€** ✅ |
| **Coût du crédit** | ~12% |

### Prêt B - INVESTIMUR (4009736BRM0911AA)

| Paramètre | Valeur Correcte |
|-----------|-----------------|
| **Banque** | INVESTIMUR |
| **N° Prêt** | 4009736BRM0911AA |
| **Montant** | 250 000,00€ ✅ |
| **Taux annuel** | 1,240% ✅ |
| **Durée totale** | 216 mois (18 ans) |
| **Date début** | 15.05.2022 |
| **Date début amortissement** | 15.05.2023 |
| **Date fin** | **15.04.2040** ✅ (PAS 15.05.2040) |
| **Type** | IN FINE / FRANCHISE_PARTIELLE |
| **Structure** | 12 mois franchise (0€) + 203 mois intérêts seuls (258,33€) + 1 paiement final capital |
| **Intérêt mensuel** | 258,33€ |
| **Échéances totales** | 216 |
| **Total intérêts** | **55 847,62€** ✅ |
| **Coût du crédit** | ~22% |

### Totaux Globaux

| Paramètre | Valeur Correcte |
|-----------|-----------------|
| **Total capital** | 500 000,00€ ✅ |
| **Total intérêts** | **85 829,03€** ✅ (29 981,41€ + 55 847,62€) |
| **Coût moyen crédit** | ~17,17% |
| **Taux moyen pondéré** | 1,145% (250k@1.050% + 250k@1.240%) |

---

## ❌ ERREURS DANS SYNTHESE_SESSION_02NOV2025.md

### 1. Tableau Récapitulatif (Lignes 52-76)

#### Prêt A (LCL)
| Ligne | Paramètre | Valeur Synthèse | Valeur Correcte | Correction |
|-------|-----------|-----------------|-----------------|------------|
| 54 | Montant initial | 250 000,00€ | 250 000,00€ | ✅ OK |
| 55 | Taux annuel | 1,0500% | 1,050% | ✅ OK |
| 56 | Durée | 252 mois | 252 mois | ✅ OK |
| 58 | **Date fin** | **2042-04-15** ❌ | **2043-04-15** | **+1 an** |
| 60 | Échéance mensuelle | 1 166,59€ | 1 166,59€ | ✅ OK |
| 61 | Nombre échéances | 251 | 252 | +1 |
| 62 | **Total intérêts** | **~29 981€** | **29 981,41€** | ✅ OK |

#### Prêt B (INVESTIMUR)
| Ligne | Paramètre | Valeur Synthèse | Valeur Correcte | Correction |
|-------|-----------|-----------------|-----------------|------------|
| 65 | **Montant initial** | **252 884,00€** ❌ | **250 000,00€** | **-2 884€** |
| 66 | Taux annuel | 1,2400% | 1,240% | ✅ OK |
| 67 | **Durée** | **252 mois** ❌ | **216 mois** | **-36 mois (-3 ans)** |
| 69 | **Date fin** | **2042-05-15** ❌ | **2040-04-15** | **-2 ans -1 mois** |
| 72 | Mois franchise | 180 mois | ? | À vérifier structure |
| 73 | Intérêt franchise | 258,33€ | 258,33€ | ✅ OK |
| 74 | Nombre échéances | 216 | 216 | ✅ OK |
| 75 | **Total intérêts** | **~55 583€** | **55 847,62€** | +264,62€ |

### 2. Ligne 31 - Total Échéances

| Synthèse | Correct |
|----------|---------|
| 467 (251 + 216) ❌ | **468 (252 + 216)** ✅ |

### 3. Ligne 48 - Total Bilan

| Synthèse | Correct |
|----------|---------|
| 463 618,00€ | 463 618,00€ ✅ |

### 4. Ligne 218 - Coût API

| Synthèse | Correct |
|----------|---------|
| <1€/mois | <1€/mois ✅ |

### 5. Ligne 335 - Total Enregistrements

| Synthèse | Correct |
|----------|---------|
| 478 (11 + 2 + 467 - 2) ❌ | **479 (11 + 2 + 468 - 2)** ✅ |

---

## ❌ ERREURS DANS memoire_courte.md

### Ligne 24 - Date Fin Prêt B

| Mémoire Courte | Correct |
|----------------|---------|
| maturité **15.04.2040** (ou **15.05.2040** ?) | **15.04.2040** ✅ |

**Note** : L'hésitation "ou 15.05.2040" est une erreur. La bonne date est **15.04.2040**.

### Ligne 22 - Intérêts Globaux

| Mémoire Courte | Calcul | Correct |
|----------------|--------|---------|
| 85.564€ | ? | **85 829,03€** (29 981,41€ + 55 847,62€) |

**Écart** : -265,03€ (probablement approximation)

---

## ❌ ERREURS DANS memoire_fondatrice.md

### Section MODULE 2 (Lignes 488-575)

Les mêmes erreurs que dans la synthèse se retrouvent dans la mémoire fondatrice :

#### Ligne 514 - Prêt B Montant
```
- Prêt B (INVESTIMUR) : 252 884€ @ 1,240%, 216 échéances
```
**Correction** :
```
- Prêt B (INVESTIMUR) : 250 000€ @ 1,240%, 216 échéances
```

#### Ligne 534 - Total Capital
```
- Total capital : 502 884€
```
**Correction** :
```
- Total capital : 500 000€
```

#### Ligne 535 - Total Intérêts
```
- Total intérêts : ~85 564€
```
**Correction** :
```
- Total intérêts : ~85 829€
```

---

## 🔍 POINT D'ATTENTION : Numéros de Prêts

### Confusion Possible

Les fichiers de référence utilisent des numéros différents de ce qui apparaît dans les noms de fichiers :

| Fichier | Nom dans fichier | N° prêt mentionné |
|---------|------------------|-------------------|
| PRET_A_ECHEANCES_REFERENCE.md | "Prêt A - INVESTIMUR" | 4009736BRM0911AA |
| PRET_B_ECHEANCES_REFERENCE.md | "Prêt B - SOLUTION P IMMO" | 5009736BRM0911AH |

Mais dans la synthèse :
- "Prêt A (LCL) - 5009736BRM0911AH"
- "Prêt B (INVESTIMUR) - 5009736BRLZE11AQ"

### ⚠️ INVERSION POSSIBLE

Il semble y avoir une **inversion des lettres A/B** entre :
- Les fichiers de référence (A=INVESTIMUR, B=LCL)
- La synthèse et mémoires (A=LCL, B=INVESTIMUR)

### ✅ Résolution

La **mémoire courte** utilise la convention :
- **Prêt A = LCL @ 1.050%**
- **Prêt B = INVESTIMUR @ 1.240%**

Cette convention sera conservée pour cohérence.

---

## 📋 PLAN DE CORRECTION

### 1. Corriger SYNTHESE_SESSION_02NOV2025.md

#### Bloc Prêt A (lignes 52-62)
- ✅ Ligne 58 : `2042-04-15` → `2043-04-15`
- ✅ Ligne 61 : `251` → `252` échéances

#### Bloc Prêt B (lignes 64-76)
- ✅ Ligne 65 : `252 884,00€` → `250 000,00€`
- ✅ Ligne 67 : `252 mois (21 ans)` → `216 mois (18 ans)`
- ✅ Ligne 69 : `2042-05-15` → `2040-04-15`
- ✅ Ligne 75 : `~55 583€` → `~55 848€`

#### Ligne 31 - Total Échéances
- ✅ `467` → `468` (252 + 216)

#### Ligne 335 - Total Enregistrements
- ✅ `478` → `479`

### 2. Corriger memoire_courte.md

#### Ligne 24
- ✅ `maturité 15.04.2040 (ou 15.05.2040 ?)` → `maturité 15.04.2040`

#### Ligne 22
- ✅ `Intérêts globaux : 85.564€` → `Intérêts globaux : 85.829€`

### 3. Corriger memoire_fondatrice.md

#### Section MODULE 2 (lignes 488-575)
- ✅ Ligne 514 : `252 884€` → `250 000€`
- ✅ Ligne 534 : `502 884€` → `500 000€`
- ✅ Ligne 535 : `~85 564€` → `~85 829€`

### 4. Vérifier Base de Données

**IMPORTANT** : Vérifier que les valeurs en base correspondent aux valeurs correctes ci-dessus.

Si la base contient les mêmes erreurs que la synthèse, il faudra **corriger les enregistrements**.

---

## 🎯 RÉSUMÉ DES CORRECTIONS

### Synthèse
- **7 corrections** dans le document principal
- **Erreur principale** : Montant Prêt B (252 884€ au lieu de 250 000€)
- **Erreur secondaire** : Dates de fin erronées

### Mémoire Courte
- **2 corrections** mineures
- Clarification date Prêt B
- Ajustement total intérêts

### Mémoire Fondatrice
- **3 corrections** dans section MODULE 2
- Alignement avec valeurs correctes

### Base de Données
- **À vérifier** : Les valeurs stockées sont-elles correctes ?
- Si non → Script de migration nécessaire

---

**Date** : 03/11/2025
**Auteur** : Claude Code (Sonnet 4.5)
**Source de vérité** : Fichiers `PRET_A_ECHEANCES_REFERENCE.md` et `PRET_B_ECHEANCES_REFERENCE.md`
**Statut** : Prêt pour application des corrections
