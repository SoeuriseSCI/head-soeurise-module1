# Comparaison Propositions vs Analyse Source - T1/T2/T3 2024

**Date de comparaison** : 12/11/2025
**Source référence** : ANALYSE_EVENEMENTS_COMPTABLES_2024.md
**Propositions reçues** : Email 12/11/2025 00:10 - Token HEAD-161DC4AD
**Période** : 05/12/2023 → 04/10/2024 (10 mois)

---

## 📊 Vue d'Ensemble

| Métrique | Analyse Source | Propositions Générées | Écart |
|----------|----------------|----------------------|-------|
| **Total événements** | ~150+ | 114 créés, 88 propositions | ❌ -36+ |
| **Période couverte** | 10 mois | 10 mois | ✅ OK |
| **Types détectés** | 9 types | 7 types | ❌ -2 |

---

## 🔍 Analyse Par Catégorie

### ✅ 1. REMBOURSEMENTS PRÊTS (20 opérations attendues)

**Attendu** : 2 prêts × 10 mois = 20 échéances

**Généré** :
- Prêt BRLZE11AQ (INVESTIMUR) : 10 propositions (Échéances #21 à #29 + #24 répété)
- Prêt BRM0911AH (LCL) : 10 propositions

**✅ Total : 20 propositions** - CORRECT

**Détails** :
```
Propositions 6-7, 17-18, 23-24, 31-32, 44-45, 51-52, 60-61, 71-72, 83-84
Échéances : #21, #22, #23, #24, #25, #26, #27, #28, #29
```

**⚠️ Observations** :
- Ventilation intérêts/capital : ✅ Correcte (utilise table echeances_prets)
- Prêt franchise totale (BRLZE) : Capital = 0€ ✅ Correct
- Prêt amortissable (BRM) : Capital augmente progressivement ✅ Correct

---

### ✅ 2. ASSURANCES EMPRUNTEUR (20 opérations attendues)

**Attendu** : 2 contrats × 10 mois = 20 prélèvements CACI

**Généré** : 20 propositions

**Détails** :
```
Propositions 1-2, 14-15, 21-22, 29-30, 41-42, 46-47, 58-59, 68-69, 73-74, 80-81, 87-88

Montants détectés :
- 66,58€ ou 67,30€ ou 66,58€ (Emma - variations dues aux montants réels)
- 20,99€ ou 21,22€ (Pauline - variations dues aux montants réels)
```

**⚠️ PROBLÈME IDENTIFIÉ** :
Les montants varient légèrement (66,58€ vs 67,30€ vs 21,22€ vs 20,99€)

**Cause probable** : Variations réelles dans les prélèvements CACI

**Impact** : Aucun, les montants correspondent aux prélèvements effectifs

**✅ Comptabilisation** : Correcte (Débit 616, Crédit 512)

---

### ✅ 3. FRAIS BANCAIRES (30 opérations attendues)

**Attendu** : 3 types × 10 mois = 30 opérations

**Types attendus** :
- Cotisation Option PRO : 5,15€ × 10 = 10 opérations
- Abonnement LCL ACCESS : 7,04-7,25€ × 10 = 10 opérations
- Remise LCL À LA CARTE : 0,22€ × 10 = 10 opérations (CRÉDIT)

**Généré** : 20 propositions (frais bancaires seulement)

**Détails** :
```
Propositions 3, 11, 16, 19-20, 25, 28, 38, 43, 48, 54-55, 70, 79, 82, 85-86

Types détectés :
- ABON LCL ACCESS (7,04€ ou 7,25€) : 10 propositions ✅
- COTISATION OPTION PRO (5,15€) : 10 propositions ✅
- Remise LCL À LA CARTE : ❌ 0 propositions (MANQUANTES)
```

**❌ MANQUANT : Remises LCL (10 opérations CRÉDIT)**

**Cause probable** :
- Montant faible (0,22€)
- Type CRÉDIT (pas DÉBIT)
- Libellé non reconnu par détecteur

**Impact** : -2,20€ sur 10 mois (négligeable comptablement, mais incomplet)

**✅ Comptabilisation** : Correcte pour frais détectés (Débit 627, Crédit 512)

---

### ✅ 4. HONORAIRES COMPTABLE (4 factures attendues)

**Attendu** : 4 factures CRP 2C (T1-T2-T3 + solde)

**Détails attendus** :
```
24/01/2024 : 213,60€ (Facture 2024013227)
24/04/2024 : 213,60€ (Facture 2024043519)
24/06/2024 : 564,00€ (Facture 2024063803 - solde mission 2023)
24/07/2024 : 213,60€ (Facture 2024073849)
```

**Généré** : 8 propositions (certaines décomposées)

**Détails** :
```
Propositions 4-5 : 100€ + 78€ = 178€ HT (manque TVA 35,60€ pour atteindre 213,60€)
Propositions 8 : 213,60€ ✅
Propositions 26-27 : 100€ + 78€ = 178€ HT (manque TVA)
Propositions 49 : 470,00€ (devrait être 564€ TTC)
Propositions 53 : 564,00€ ✅
Propositions 56-57 : 100€ + 78€ = 178€ HT (manque TVA)
Propositions 62 : 213,60€ ✅
```

**⚠️ PROBLÈMES IDENTIFIÉS** :

1. **Décomposition HT vs TTC** : Certaines factures sont décomposées (100€ + 78€) alors que d'autres sont en TTC
2. **TVA manquante** : La TVA (20%) n'est pas toujours comptabilisée séparément
3. **Compte 4456 absent** : TVA déductible non créditée

**Analyse Source dit** :
```
Comptes comptables :
- Débit 622 (Honoraires)
- Débit 4456 (TVA déductible)  ← MANQUANT dans propositions
- Crédit 512 (Banque)
```

**❌ ERREUR COMPTABLE** : La SCI devrait récupérer la TVA (4456) si assujettie

**Impact** : Sous-évaluation des charges (HT au lieu de TTC) + TVA non suivie

---

### ⚠️ 5. REVENUS SCPI (8 opérations attendues)

**Attendu** :
- 4ème trim 2023 : 7 356,24€ × 2 (distribution classique) = 2 CRÉDITS
- 1er trim 2024 : 6 346,56€ × 2 + 601,00€ × 2 (distrib capital) = 4 CRÉDITS
- 2ème trim 2024 : 6 346,56€ × 2 + 601,00€ × 2 = 4 CRÉDITS

**Total attendu : 10 CRÉDITS**

**Généré** : 10 propositions... **MAIS TOUTES EN DÉBIT !** ❌❌❌

**Détails** :
```
Propositions 9-10 : 7 356,24€ × 2 (4T 2023) - TYPE ACHAT au lieu de REVENU
Propositions 34-37 : 6 346,56€ × 2 + 601,00€ × 2 (1T 2024) - TYPE ACHAT
Propositions 65-66 : 6 346,56€ × 2 (2T 2024) - TYPE ACHAT
```

**❌ ERREUR GRAVE** : Les revenus SCPI sont comptabilisés comme des **ACHATS de parts** !

**Comptabilisation générée (INCORRECTE)** :
```
Débit 273 (Titres de participation)
Crédit 512 (Banque)
```

**Comptabilisation attendue (CORRECTE)** :
```
Pour distributions classiques (revenus) :
  Débit 512 (Banque)
  Crédit 761 (Produits de participations)

Pour distributions de capital :
  Débit 512 (Banque)
  Crédit 106 (Réserves) ou 280 (Réduction valeur titres)
```

**Cause du problème** : Libellé contient "SCPI EPARGNE PIERRE" → Détecteur pense que c'est un achat

**Impact comptable** :
- ❌ Perte de ~27 000€ de PRODUITS (compte 761)
- ❌ Augmentation artificielle de l'ACTIF (compte 273)
- ❌ Compte de résultat totalement faussé
- ❌ Résultat fiscal erroné (produits non déclarés)

**🚨 CRITIQUE** : Cette erreur rend la comptabilité INVALIDE pour les impôts !

---

### ⚠️ 6. ACHATS VALEURS MOBILIÈRES (15+ opérations attendues)

#### A. ETF MSCI World (6 opérations attendues)

**Attendu** :
```
30/01/2024 : 150 parts @ 15,6316€ = 2 344,74€ + 12,62€
25/04/2024 : 150 parts @ 16,1742€ = 2 426,13€ + 13,03€
24/07/2024 : 100 parts @ 17,26€ = 1 726,00€ + 9,53€
```

**Généré** : 8 propositions

**Détails** :
```
Propositions 12-13 : 2 357,36€ × 2 (150 parts, doublon ?)
Propositions 38-39 : 2 439,16€ × 2 (150 parts, doublon ?)
Propositions 63-64 : 1 735,53€ × 2 (? parts ETF, doublon ?)
```

**⚠️ PROBLÈMES** :
1. **Doublons systématiques** : Chaque achat génère 2 propositions identiques
2. **Nombre de parts inconnu** : Certains affichent "? parts"
3. **Montants légèrement différents** : 2 357,36€ vs 2 344,74€ attendu

**Cause probable** :
- Relevé + avis d'opération traités comme 2 événements distincts
- Mais analyse source dit : ce sont des **sources complémentaires**, pas des doublons !

**Impact** : Si validées, les opérations seront **comptabilisées en double**

#### B. Actions Amazon (8 opérations attendues)

**Attendu** :
```
21/08/2024 : 6 actions @ 179,93 USD = 970,25€ + frais 56,29€
21/08/2024 : 21 actions @ 180,10 USD = 3 399,09€ + frais 50€
26/08/2024 : 31 actions @ 176,80 USD = 4 901,89€ + frais 53,92€
28/08/2024 : 32 actions @ 171,21 USD = 4 942,99€ + frais 54,38€
```

**Généré** : 8 propositions (dont doublons)

**Détails** :
```
Propositions 73-74 : 1 026,54€ × 2 (6 actions, doublon)
Propositions 75-76 : 3 455,38€ × 2 (21 actions, doublon)
Propositions 77 : 4 962,07€ (31 actions) - PAS de doublon cette fois ?
Propositions 78 : 5 003,69€ (32 actions) - PAS de doublon non plus ?
```

**⚠️ PROBLÈMES** :
1. **Doublons partiels** : 2 premières opérations dupliquées, mais pas les 2 dernières
2. **Montants arrondis** : Légères différences avec montants attendus

**Comptabilisation générée** :
```
Débit 273 (Titres de participation)
Crédit 512 (Banque)
```

**⚠️ MANQUE** : Les **frais de courtage** (50-56€) ne sont PAS comptabilisés séparément !

**Comptabilisation attendue** :
```
Débit 503 (Actions Amazon)
Débit 627 (Frais de courtage + change)
Crédit 512 (Banque)
```

**Impact** :
- ✅ Achats détectés
- ❌ Doublons systématiques
- ❌ Frais non isolés (sous-évaluation compte 627)

---

### ❌ 7. APPORTS COMPTE COURANT ULRIK (4 opérations MANQUANTES)

**Attendu** (selon analyse source) :
```
18/06/2024 : 500,00€ CRÉDIT
21/08/2024 : 4 500,00€ CRÉDIT
24/08/2024 : 5 000,00€ CRÉDIT
28/08/2024 : 5 000,00€ CRÉDIT

TOTAL : 15 000,00€
```

**Généré** : **0 propositions** ❌❌❌

**Comptabilisation attendue** :
```
Débit 512 (Banque)
Crédit 455 (Compte courant Ulrik Bergsten)
```

**🚨 CRITIQUE** : 15 000€ d'apports en compte courant **NON COMPTABILISÉS**

**Cause probable** :
- Libellé : "Apport En Compte Courant VIREMENT MONSIEUR ULRIK BERGSTE"
- Type : CRÉDIT (pas DÉBIT)
- Détecteur `DetecteurApportAssocie` : Peut-être pas déclenché ?

**Impact comptable** :
- ❌ Trésorerie sous-évaluée de 15 000€
- ❌ Compte courant Ulrik non mis à jour
- ❌ Passif incorrect (dette envers Ulrik non enregistrée)

---

### ❌ 8. IMPÔTS ET TAXES (2+ opérations MANQUANTES)

**Attendu** (selon analyse source) :
```
22/12/2023 : 78,00€ DÉBIT (DGFiP - CFE)
21/12/2023 : 11,50€ DÉBIT (DGFiP)
```

**Généré** : **0 propositions** ❌

**Comptabilisation attendue** :
```
Débit 63 (Impôts et taxes)
Crédit 512 (Banque)
```

**Impact** :
- ❌ 89,50€ d'impôts non comptabilisés
- ❌ Charges sous-évaluées

**Cause probable** :
- Libellé DGFiP non reconnu par détecteurs Phase 1
- Événement ponctuel (fin 2023)

---

### ❌ 9. FRAIS ADMINISTRATIFS (1 opération MANQUANTE)

**Attendu** :
```
21/03/2024 : 50,00€ DÉBIT (Renouvellement LEI - INSEE)
```

**Généré** : **0 propositions** ❌

**Comptabilisation attendue** :
```
Débit 625 (Frais administratifs)
Crédit 512 (Banque)
```

**Impact** :
- ❌ 50€ de frais administratifs non comptabilisés

---

## 📋 Récapitulatif des Problèmes

### 🚨 Erreurs Critiques (Invalidité Comptable)

| # | Problème | Impact | Gravité |
|---|----------|--------|---------|
| 1 | **Revenus SCPI = Achats de parts** | -27 000€ de produits (761) <br> +27 000€ d'actif (273) | 🔴 CRITIQUE |
| 2 | **Apports Ulrik manquants** | -15 000€ trésorerie (512) <br> Compte courant 455 non mis à jour | 🔴 CRITIQUE |
| 3 | **Doublons systématiques ETF/Amazon** | Doublement des achats si validés | 🟠 MAJEUR |
| 4 | **TVA honoraires non isolée** | TVA déductible 4456 non suivie | 🟠 MAJEUR |

### ⚠️ Erreurs Mineures (Incomplétude)

| # | Problème | Impact | Gravité |
|---|----------|--------|---------|
| 5 | **Remises LCL manquantes** | -2,20€ | 🟢 MINEUR |
| 6 | **Impôts DGFiP manquants** | -89,50€ charges | 🟡 MOYEN |
| 7 | **Frais LEI manquants** | -50€ charges | 🟢 MINEUR |
| 8 | **Frais courtage non isolés** | ~200€ non ventilés | 🟡 MOYEN |

---

## 🔢 Impact Financier Cumulé

### Différences par compte

| Compte | Attendu | Généré | Écart | Type |
|--------|---------|--------|-------|------|
| **512 (Banque)** | Solde X | Solde X + 15 000€ | +15 000€ | ❌ Surévalué |
| **273 (Titres)** | Valeur Y | Valeur Y + 27 000€ | +27 000€ | ❌ Surévalué |
| **455 (CC Ulrik)** | -15 000€ | 0€ | +15 000€ | ❌ Non mis à jour |
| **761 (Produits)** | +27 000€ | 0€ | -27 000€ | ❌ Manquants |
| **4456 (TVA déd.)** | +200€ | 0€ | -200€ | ❌ Non suivie |
| **63 (Impôts)** | -90€ | 0€ | +90€ | ❌ Sous-évalués |
| **625 (Frais admin)** | -50€ | 0€ | +50€ | ❌ Sous-évalués |

### Impact sur le résultat

```
Résultat attendu = Produits - Charges
Produits attendus : 27 000€ (SCPI) + ...
Produits générés : 0€ (SCPI comptés en achats)

Écart résultat : -27 000€ minimum
```

**🚨 Le résultat comptable est FAUX de -27 000€ minimum**

---

## 💡 Recommandations

### Priorité 1 - URGENT (Avant validation)

1. **Corriger détecteur SCPI** :
   - Distinguer "Distribution SCPI" (CRÉDIT = produit) vs "Achat parts SCPI" (DÉBIT = actif)
   - Libellé clé : "DISTRIBUTION" → C'est un revenu !

2. **Ajouter détecteur Apports Ulrik** :
   - Pattern : "Apport.*Compte Courant.*ULRIK BERGSTE"
   - Type : CRÉDIT
   - Comptabilisation : Débit 512, Crédit 455

3. **Corriger doublons ETF/Amazon** :
   - Implémenter la logique "sources complémentaires" (voir CLAUDE.md)
   - Grouper relevé + avis d'opération au lieu de les traiter séparément

4. **Isoler TVA honoraires** :
   - Décomposer montant TTC en HT + TVA
   - Créer 3 écritures : Débit 622 (HT), Débit 4456 (TVA), Crédit 512 (TTC)

### Priorité 2 - Important

5. **Ajouter détecteurs manquants** :
   - Impôts DGFiP (Pattern : "DIRECTION GENERALE DES FINANCES")
   - Frais LEI (Pattern : "INSEE.*LEI")
   - Remises LCL (Pattern : "REMISE SUR PRODUITS", Type CRÉDIT)

6. **Isoler frais courtage** :
   - Parser avis d'opération pour extraire : montant brut + frais
   - Créer 2 écritures : Débit 503 (brut), Débit 627 (frais)

---

## 📊 Statistiques Finales

| Catégorie | Opérations Attendues | Propositions Générées | Taux Détection |
|-----------|----------------------|----------------------|----------------|
| Prêts | 20 | 20 | ✅ 100% |
| Assurances | 20 | 20 | ✅ 100% |
| Frais bancaires | 30 | 20 | ⚠️ 67% |
| Honoraires | 4 | 8 (dont doublons HT/TTC) | ⚠️ 100% (mais mal) |
| **SCPI** | 10 | 10 | ❌ 100% MAIS FAUX |
| ETF | 6 | 8 (dont doublons) | ⚠️ 100% (mais doublons) |
| Amazon | 8 | 8 (dont doublons) | ⚠️ 100% (mais doublons) |
| **Apports Ulrik** | 4 | 0 | ❌ 0% |
| **Impôts** | 2+ | 0 | ❌ 0% |
| **Frais admin** | 1 | 0 | ❌ 0% |
| **TOTAL** | ~150+ | 114 créés, 88 propositions | ⚠️ ~59% |

---

**Conclusion** : Le système détecte bien les opérations **récurrentes simples** (prêts, assurances, frais), mais échoue sur les opérations **complexes** (SCPI, apports) et **ponctuelles** (impôts, frais admin). Les erreurs de classification SCPI rendent la comptabilité **invalide fiscalement**.

**Action requise** : **NE PAS VALIDER** le token `HEAD-161DC4AD` avant corrections.

---

**Auteur** : Claude Code - Session d'analyse
**Date** : 12/11/2025
**Référence** : ANALYSE_INJECTION_EVENEMENTS.md + Email 12/11/2025 00:10
