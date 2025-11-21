# 📊 CONSTRUCTION DES ÉTATS FINANCIERS 2024 - ANALYSE COMPLÈTE

**Date:** 21 novembre 2025  
**Statut:** Exercice 2024 EN_PREPARATION - Clôture en cours

---

## 🎯 RÉSUMÉ EXÉCUTIF

### État Actuel du Projet 2024

**✅ Complétude :**
- **Exercice 2024 :** En phase de pré-clôture / clôture
- **Écritures comptables :** 698+ enregistrées
- **Propositions de clôture :** Générées (en attente validation Ulrik)
- **Prêts immobiliers :** 2 prêts avec 468 échéances intégrées
- **Bilan 2023 :** ✅ Validé (571 613€ équilibré)

**⏳ Prochaine étape immédiate :**
1. Ulrik valide les propositions de clôture/pré-clôture
2. Système insère les écritures de clôture
3. Système génère les états financiers finaux 2024
4. Exercice passe en statut CLOTURE

---

## 🏗️ ARCHITECTURE POUR LES ÉTATS FINANCIERS

### Fichiers Clés Existants

#### 1. **cloture_exercice.py** (Clôture Définitive)
**Responsabilité :** Phase finale après approbation AG

**6 Étapes implémentées :**
```
ÉTAPE 1 : Vérification pré-clôture
          └─> Vérifier écritures cutoff + IS présentes
          
ÉTAPE 2 : Affectation du résultat
          └─> Créer écritures : 120 (bénéfice) → 110/119 (report)
          
ÉTAPE 3 : Gel de l'exercice
          └─> Statut = CLOTURE (immuable)
          
ÉTAPE 4 : Bilan d'ouverture N+1
          └─> Reprendre soldes de clôture → Compte 89
          
ÉTAPE 5 : Vérifier extournes
          └─> Cutoffs remis à zero au 01/01/N+1
          
ÉTAPE 6 : Générer Cerfa (PLACEHOLDER)
          └─> Formules 2065 + 2033 (à développer)
```

**Appel :**
```bash
# Simulation
python cloture_exercice.py --exercice 2024 --pv-ag "PV AG du 08/04/2025"

# Exécution réelle
python cloture_exercice.py --exercice 2024 --pv-ag "PV AG du 08/04/2025" --execute
```

#### 2. **precloture_exercice.py** (Pré-clôture)
**Responsabilité :** Préparation avant AG

**6 Étapes implémentées :**
```
ÉTAPE 1 : Cutoff des intérêts courus
          └─> Créer écritures CUTOFF + EXTOURNE au 01/01/N+1
          
ÉTAPE 2 : Calcul du résultat brut
          └─> Total produits - Total charges
          
ÉTAPE 3 : Calcul IS (Impôt sur les Sociétés)
          └─> Taux réduit 15% (PME < 42.5k€)
          └─> Compensation déficit reportable (compte 119)
          
ÉTAPE 4 : Écriture IS
          └─> Débit 695 (Charges IS) / Crédit 444 (IS dû)
          
ÉTAPE 5 : États financiers provisoires
          └─> Bilan + Compte de résultat (avant affectation)
          
ÉTAPE 6 : Proposition d'affectation
          └─> Recommandations report à nouveau (110/119)
```

**Appel :**
```bash
# Simulation
python precloture_exercice.py --exercice 2024

# Exécution
python precloture_exercice.py --exercice 2024 --execute
```

#### 3. **construire_etats_financiers_2024.py** (États Financiers)
**Responsabilité :** Génération des états comptables finaux

**4 Étapes implémentées :**
```
ÉTAPE 1 : Calcul des soldes finaux par compte
          └─> Pour CHAQUE compte : Total débits - Total crédits
          
ÉTAPE 2 : Compte de résultat 2024
          ├─ CHARGES (classe 6) : Loyers, assurances, frais, IS, etc.
          ├─ PRODUITS (classe 7) : Revenus locatifs, financiers
          └─ RÉSULTAT = PRODUITS - CHARGES
          
ÉTAPE 3 : Bilan au 31/12/2024
          ├─ ACTIF (classe 1-5, soldes débiteurs)
          │  ├─ Immobilisations (280: SCPI)
          │  ├─ Trésorerie (512: Banque)
          │  └─ Autres valeurs
          │
          ├─ PASSIF (classe 1-5, soldes créditeurs)
          │  ├─ Emprunts (161: Prêts)
          │  ├─ Capitaux propres (110/119/120: Report/Bénéfice)
          │  └─ Dettes fournisseurs
          │
          └─ RÉSULTAT EXERCICE : Inscription au passif (si bénéfice)
          
ÉTAPE 4 : Vérification équilibre ACTIF = PASSIF
          └─> Écart < 0.01€ = Équilibré ✅
```

**Appel :**
```bash
python construire_etats_financiers_2024.py
# Génère : etats_financiers_2024_YYYYMMDD_HHMMSS.json
```

---

## 📋 FLUX DE CLÔTURE 2024 (3 PHASES)

### Phase 1 : Pré-clôture (avant AG)
```
[ÉTAPE 1] Cutoff des intérêts courus
          → Interets 2024 provisionnés (661 / 706)
          → Extourne 01/01/2025 (reversement)

[ÉTAPE 2] Résultat brut
          → Total produits 2024
          → Total charges 2024 (+ IS)

[ÉTAPE 3] Déficit reportable (119)
          → Récupération solde 119
          → Imputation IS

[ÉTAPE 4] Écriture IS
          → 695 (IS) / 444 (IS dû)

[ÉTAPE 5] États provisoires
          → Bilan provisoire
          → Compte de résultat provisoire
          
[ÉTAPE 6] Proposition affectation
          → Recommandation rapport humanisé
```

### Phase 2 : Approbation AG
```
[VALIDATION] Assemblée Générale
             ├─ Vote approbation comptes
             ├─ Vote affectation résultat
             └─ Procès-Verbal établi

             PV AG du 08/04/2025 (signés Ulrik + Pauline + Emma)
```

### Phase 3 : Clôture définitive (après AG)
```
[ÉTAPE 1] Vérification pré-clôture effectuée ✅

[ÉTAPE 2] Affectation du résultat (d'après AG)
          → Débits 120 (résultat)
          → Crédits 110/119 (report à nouveau)

[ÉTAPE 3] Gel de l'exercice
          → Statut 2024 = CLOTURE

[ÉTAPE 4] Bilan d'ouverture 2025
          → Écritures 2025-01-01-OUV-xxx
          → Reprise soldes 2024 via compte 89

[ÉTAPE 5] Vérifier extournes
          → Cutoffs 2025-01-01 en place

[ÉTAPE 6] Cerfa (déclarations fiscales)
          → Formulaire 2065 (IS)
          → Formulaire 2033 (Bilan)
```

---

## 🗂️ STRUCTURE DES DONNÉES

### Tables Base de Données

#### **exercices_comptables**
```sql
id | annee | date_debut    | date_fin      | statut            | description
1  | 2023  | 2023-01-01    | 2023-12-31    | CLOTURE           | ...
2  | 2024  | 2024-01-01    | 2024-12-31    | EN_PREPARATION    | ← ACTUEL
3  | 2025  | 2025-01-01    | 2025-12-31    | OUVERT            | (créé après cloture 2024)
```

#### **ecritures_comptables** (Exemple 2024)
```
id    | exercice_id | numero_ecriture    | date_ecriture | type_ecriture        | montant
----  | -----------  | ---------------   | ------------- | -------------------- | ----------
1     | 2           | 2024-01-01-OUV-001 | 2024-01-01    | INIT_BILAN            | 571613.00
...   | 2           | EVT-688            | 2024-01-15    | RELEVE_BANCAIRE       | 1166.59
...   | 2           | EVT-689            | 2024-01-15    | ASSURANCE_PRET       | 67.30
688   | 2           | 2024-12-31-CUT-001 | 2024-12-31    | CUTOFF_INTERETS_COURUS| XXXX.XX
689   | 2           | 2024-12-31-IS-001  | 2024-12-31    | IMPOT_SOCIETES       | XXXX.XX
690   | 2           | 2024-12-31-AFF-001 | 2024-12-31    | AFFECTATION_RESULTAT | XXXX.XX
```

#### **propositions_en_attente** (État clôture 2024)
```
id  | token         | type_evenement     | statut        | created_at
-   | HEAD-2B7F5D1A | PRE_CLOTURE        | EN_ATTENTE    | 2025-11-21 10:59
-   | HEAD-8C4E9F2B | CLOTURE            | EN_ATTENTE    | 2025-11-21 10:59
```

---

## 📊 EXEMPLE STATES FINANCIERS 2024 (Attendus)

### Compte de Résultat 2024

```
═════════════════════════════════════════════════════════════════
                     COMPTE DE RÉSULTAT 2024
═════════════════════════════════════════════════════════════════

CHARGES                                        MONTANT
────────────────────────────────────────────────────────────────
61X Transports                          XXX,XX€
616 Assurances                          XXX,XX€  (prêts + biens)
622 Rémunérations gérant                    0,00€  (Ulrik)
627 Frais bancaires                     XXX,XX€
661 Intérêts emprunts                   XXXX,XX€ (LCL + INVESTIMUR)
695 Impôts sur les bénéfices            XXXX,XX€ (IS calculé)
────────────────────────────────────────────────────────────────
TOTAL CHARGES                           XXXXXX,XX€

PRODUITS                                       MONTANT
────────────────────────────────────────────────────────────────
706 Revenus locatifs                    XXXXXX,XX€
707 Revenus mobiliers                       XX,XX€ (intérêts compte)
────────────────────────────────────────────────────────────────
TOTAL PRODUITS                          XXXXXX,XX€

════════════════════════════════════════════════════════════════
RÉSULTAT NET (avant affectation)        ±XXXX,XX€  
════════════════════════════════════════════════════════════════
```

### Bilan 2024

```
═════════════════════════════════════════════════════════════════
                         BILAN 2024
═════════════════════════════════════════════════════════════════

ACTIF                                          MONTANT
────────────────────────────────────────────────────────────────
280 Titres SCPI (valeurs mobilières)    500032,00€
512 Banque (trésorerie)                 ±XXXX,XX€
119 Report à nouveau débiteur (déficit)     0,00€ (ou montant)
────────────────────────────────────────────────────────────────
TOTAL ACTIF                             XXXXXX,XX€

PASSIF                                         MONTANT
────────────────────────────────────────────────────────────────
161 Emprunts LCL (prêt A)               249xxx,xx€ (capital restant)
164 Emprunts INVESTIMUR (prêt B)        249xxx,xx€ (capital restant)
110 Report à nouveau créditeur          ±XXXX,XX€
120 Résultat de l'exercice 2024         ±XXXX,XX€ ← À affecter
────────────────────────────────────────────────────────────────
TOTAL PASSIF                            XXXXXX,XX€

════════════════════════════════════════════════════════════════
VÉRIFICATION : ACTIF = PASSIF → ✅ ÉQUILIBRÉ
════════════════════════════════════════════════════════════════
```

---

## 🚀 PROCESSUS DE CLÔTURE 2024 - ROADMAP

### ✅ Étapes Complétées

- [x] **Exercice 2024 créé** : Statut OUVERT → EN_PREPARATION
- [x] **Bilan d'ouverture 2024** : 571.613€ (reprise 2023)
- [x] **Écritures 2024 comptabilisées** : 698+ transactions
- [x] **Prêts intégrés** : 468 échéances (LCL + INVESTIMUR)
- [x] **Cutoff intérêts courus** : Script prêt
- [x] **Handlers pré-clôture/clôture** : Code opérationnel (PR #347)
- [x] **Propositions clôture générées** : En attente validation Ulrik

### ⏳ Étapes Restantes

1. **[URGENT] Ulrik valide les propositions**
   - Email : `[_Head] VALIDE: HEAD-XXXXXX` (PRE_CLOTURE)
   - Email : `[_Head] VALIDE: HEAD-YYYYYY` (CLOTURE)
   - ⏱️ Délai : Immédiat (tokens stockés en base)

2. **Phase 5-7 automatique** (réveil suivant)
   - Détection validation → Récupération propositions → ACID insertion

3. **Phase 8 : Insertion écritures clôture**
   ```
   ├─ Écriture IS (si applicable)
   ├─ Écriture affectation résultat
   ├─ Écriture bilan ouverture 2025
   └─ Extournes cutoff 2025
   ```

4. **Exercice 2024 passe CLOTURE**
   ```sql
   UPDATE exercices_comptables 
   SET statut = 'CLOTURE'
   WHERE annee = 2024;
   ```

5. **Génération états financiers finaux**
   ```bash
   python construire_etats_financiers_2024.py
   # Produit JSON complet avec bilan + compte résultat
   ```

6. **Exercice 2025 OUVERT** (automatiquement après clôture)
   ```
   Statut : OUVERT
   Réception loyers, charges, etc. 2025
   ```

---

## 🔍 POINTS CLÉS D'ATTENTION

### Comptabilité Correcte

#### Compte 89 (Bilan d'Ouverture)
- **Rôle** : Contrepartie universelle
- **Principe** : Σ débits 89 = Σ crédits 89 = 0€
- **Vérification** : Script `verifier_bilan_2023.py` peut être adapté

#### Déficit Reportable (119)
- **Définition** : Pertes accumulées des exercices antérieurs
- **Localisation** : Compte 119 (classe 1, mais solde débiteur)
- **Imputation IS** : Réduit la base imposable avant calcul IS

#### Comptes Négatifs (Inversions Normales)
- **290 (Provisions)** : Valeur négative → Débit 89 / Crédit 290 ✅
- **120 (Report RAN)** : Perte antérieure → Débit 120 / Crédit 89 ✅
- **119 (Report RAN débiteur)** : Pertes → Solde débiteur ✅

### Prêts Immobiliers

#### Prêt A - LCL (5009736BRM0911AH)
- **Montant** : 250.000€
- **Taux** : 1,050%
- **Type** : AMORTISSEMENT_CONSTANT (capital + intérêts réguliers)
- **Durée** : 252 mois (21 ans)
- **Franchise** : 12 mois totale (04/2022 → 04/2023)
- **Échéances** : 252 (15 du mois, montant fixe ~1.167€)
- **Intérêts totaux** : ~29.981€

#### Prêt B - INVESTIMUR (5009736BRLZE11AQ)
- **Montant** : 250.000€
- **Taux** : 1,240%
- **Type** : IN FINE (franchise partielle : intérêts seuls, puis paiement final)
- **Durée** : 216 mois (18 ans)
- **Franchise** : 12 mois totale (04/2022 → 04/2023)
- **Structure** : 12 franchise + 203 intérêts seuls + 1 paiement final
- **Échéances** : 216
- **Intérêts totaux** : ~55.848€

---

## 🛠️ OUTILS D'APPUI DISPONIBLES

### Scripts de Vérification

| Script | Fonction | Appel |
|--------|----------|-------|
| `verifier_bilan_2023.py` | ✅ Vérifier équilibre bilan 2023 | `python verifier_bilan_2023.py` |
| `verifier_bilan_ouverture_2024.py` | ✅ Vérifier reprise soldes 2024 | `python verifier_bilan_ouverture_2024.py` |
| `construire_etats_financiers_2024.py` | ✅ Générer états 2024 | `python construire_etats_financiers_2024.py` |
| `precloture_exercice.py` | ⏳ Pré-clôture (avant AG) | `python precloture_exercice.py --exercice 2024` |
| `cloture_exercice.py` | ⏳ Clôture définitive (après AG) | `python cloture_exercice.py --exercice 2024 --pv-ag "PV AG du 08/04/2025"` |

### Scripts de Sauvegarde

```bash
# Sauvegarde JSON (format lisible)
python sauvegarder_base.py

# Sauvegarde SQL (format dump PostgreSQL)
bash sauvegarder_base.sh

# Voir instructions détaillées
cat INSTRUCTIONS_SAUVEGARDE_BASE.md
```

---

## 📅 CALENDRIER PRÉVISIONNEL

### Janvier - Mars 2025
- [x] Relevés T1 2024 (janvier-mars) comptabilisés
- [x] Cutoff fin T1 effectué
- [x] Propositions T1 validées

### Avril - Juin 2025
- [x] Relevés T2 2024 (avril-juin) comptabilisés
- [ ] Assemblée Générale 08/04/2025 → **Approbation comptes 2024**
- [ ] Pré-clôture effectuée
- [ ] Propositions clôture générées ← **ACTUELLEMENT ICI**

### Juillet - Septembre 2025
- [ ] Ulrik valide propositions clôture
- [ ] Clôture définitive insérée
- [ ] États financiers 2024 finaux générés
- [ ] Déclarations fiscales 2024 (Cerfa 2065 + 2033)

### Octobre - Décembre 2025
- [ ] Exercice 2025 en cours
- [ ] Suivi régulier

---

## 📞 PROCHAINES ACTIONS

### IMMEDIATE (⏱️ Aujourd'hui)

**Ulrik doit valider les propositions clôture :**
```
EMAIL À ENVOYER :

Répondre à : _Head.Soeurise@gmail.com

Message :
────────────────────────────────────────────
[_Head] VALIDE: HEAD-2B7F5D1A
[_Head] VALIDE: HEAD-8C4E9F2B
────────────────────────────────────────────

Les tokens seront trouvés dans l'email de propositions 
généré le 21/11/2025 à 10:59
```

### FOLLOW-UP (⏱️ Réveil 22/11/2025 08:00)

- Système détecte validation
- Insertion écritures clôture
- Exercice 2024 passe CLOTURE
- Exercice 2025 créé (OUVERT)

### FINAL (⏱️ Après clôture)

```bash
# Générer les états financiers 2024 définitifs
python construire_etats_financiers_2024.py

# Sauvegarder
python sauvegarder_base.py

# Créer PR pour archivage
# (Les états financiers seront dans etats_financiers_2024_*.json)
```

---

## ✅ CHECKLIST DE CLÔTURE

- [ ] **Ulrik valide pré-clôture** : `[_Head] VALIDE: <TOKEN>`
- [ ] **Ulrik valide clôture** : `[_Head] VALIDE: <TOKEN>`
- [ ] **Système insère écritures** : Vérifier dans ecritures_comptables (2024 CLOTURE)
- [ ] **Exercice 2024 = CLOTURE** : SELECT statut FROM exercices_comptables WHERE annee=2024
- [ ] **États financiers générés** : etats_financiers_2024_*.json créé
- [ ] **Exercice 2025 OUVERT** : Prêt pour transactions 2025
- [ ] **Sauvegarde effectuée** : Point de restauration
- [ ] **Déclarations fiscales** : Cerfa 2065 + 2033 (à développer)

---

**Statut Global :** ✅ Système prêt pour clôture 2024 - En attente validation Ulrik
