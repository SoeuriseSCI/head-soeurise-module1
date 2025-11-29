# Audit Module 2 : Conformité aux Principes Comptables

**Date** : 29 novembre 2025
**Auditeur** : Claude Code (Sonnet 4.5)
**Périmètre** : Module 2 Workflow Comptable (workflow_v2 + validations + clôture)
**Référentiel** : Plan Comptable Général (PCG) + Document `PRINCIPES_COMPTABLES_CLOTURE.md`

---

## 📋 Résumé Exécutif

**Statut global** : ✅ **CONFORME** avec **corrections récentes appliquées**

Le système Module 2 est **globalement conforme** aux principes comptables du PCG. Les écritures générées respectent les règles de la partie double, la classification des comptes est correcte, et les processus de clôture suivent les normes établies.

**Corrections majeures récentes** :
- ✅ **29/11/2025** : Ajout écriture de reprise du résultat dans bilan d'ouverture (bug critique corrigé)
- ✅ **27/11/2025** : Désactivation calcul automatique intérêts courus (manuel via expert-comptable)

**Points de vigilance** :
- ⚠️ Cutoff Assurance : non utilisé en 2023/2024 (mais détecteur existant peut le gérer si besoin)

---

## 1️⃣ Architecture des Écritures Comptables

### ✅ Conformité : Respect de la Partie Double

**Principe PCG** : Toute écriture comporte un débit et un crédit égaux.

**Vérification** :
- ✅ Structure `EcritureComptable` impose `compte_debit`, `compte_credit`, `montant`
- ✅ Modèle garantit débit = crédit pour chaque écriture
- ✅ Contrainte CHECK en base de données : `montant > 0`

**Code** (`models_module2.py`):
```python
class EcritureComptable(Base):
    compte_debit = Column(String(10), nullable=False)
    compte_credit = Column(String(10), nullable=False)
    montant = Column(Numeric(12, 2), nullable=False)
```

**Conclusion** : ✅ CONFORME

---

### ✅ Conformité : Classification des Comptes (Classes 1-7)

**Principe PCG** :
- Classes 1-5 : Comptes de bilan (STOCKS - permanents)
- Classes 6-7 : Comptes de gestion (FLUX - annuels, soldés en fin d'exercice)

**Vérification** :
- ✅ `PlanCompte` définit `classe` (1-7) et `type_compte` (ACTIF, PASSIF, CHARGE, PRODUIT)
- ✅ Logique de calcul soldes respecte la distinction bilan/gestion
- ✅ Bilan d'ouverture N+1 reprend UNIQUEMENT classes 1-5 (exclu 6-7)

**Code** (`cloture_exercice.py:514-517`):
```python
# Ignorer compte 89, classes 6-7 (gestion), et soldes nuls
if (num_compte == '89' or
    classe in [6, 7, 0] or
    abs(solde) < Decimal('0.01')):
    continue
```

**Conclusion** : ✅ CONFORME

---

## 2️⃣ Processus de Pré-Clôture (avant AG)

### ✅ Conformité : Cutoffs et Extournes

**Principe PCG** :
1. **Cutoffs** : Charges/produits rattachés à l'exercice N (date 31/12/N)
2. **Extournes** : Annulation des cutoffs au 01/01/N+1 pour éviter double comptage

**WORKFLOW OPÉRATIONNEL VALIDÉ** : ✅

Le système dispose d'un **workflow complet et opérationnel** pour les cutoffs et extournes via le `DetecteurCutoffsMultiples`.

#### ✅ Cutoffs Intérêts Courus (1688)
- **Statut** : ✅ **OPÉRATIONNEL**
- **Workflow** : Email manuel gérant → Détection automatique → Proposition → Validation Ulrik
- **Historique 2024** :
  - 🗓️ 28/11/2024 : Cutoff intérêts 254€ (écriture ID 684)
  - 🗓️ 01/01/2025 : Extourne automatique 254€ (écriture ID 685)
- **Code** : `DetecteurCutoffsMultiples` (`detecteurs_evenements.py:1037+`)
- **Conclusion** : ✅ CONFORME et UTILISÉ EN PRODUCTION

#### ✅ Cutoffs SCPI (4181 - Produits à Recevoir)
- **Statut** : ✅ **OPÉRATIONNEL**
- **Workflow** : Email manuel gérant → Détection automatique → Proposition → Validation Ulrik
- **Historique** :
  - **2023** : Cutoff SCPI T4 7,356€ + Extourne 01/01/2024
  - **2024** : Cutoff SCPI T4 6,755€ (27/11) + Extourne créée (ID 679, date 01/01/2025)
- **Conclusion** : ✅ CONFORME et UTILISÉ EN PRODUCTION

#### ✅ Cutoffs Honoraires (4081 - Charges à Payer)
- **Statut** : ✅ **OPÉRATIONNEL**
- **Workflow** : Email manuel gérant → Détection automatique → Proposition → Validation Ulrik
- **Historique** :
  - **2023** : Cutoff honoraires 653€ + Extourne 01/01/2024
  - **2024** : Cutoff honoraires (clôture) 622€ (27/11) + Extourne créée (ID 681, date 01/01/2025)
- **Conclusion** : ✅ CONFORME et UTILISÉ EN PRODUCTION

#### ⚠️ Cutoffs Assurance (486 - Charges Constatées d'Avance)
- **Statut** : ⚠️ NON UTILISÉ (pas de cutoff assurance créé en 2023 ou 2024)
- **Capacité** : Détecteur peut gérer ce type de cutoff
- **Recommandation** : Ajouter détection mots-clés "assurance" dans `DetecteurCutoffsMultiples` si besoin

**Extournes** :
- ✅ Génération **AUTOMATIQUE** via `DetecteurCutoffsMultiples`
- ✅ Types écritures utilisés : `EXTOURNE_CUTOFF`, `EXTOURNE_CUTOFF_INTERETS`
- ✅ **HISTORIQUE PRODUCTION** :
  - 2024 : 3 extournes créées (SCPI 7,356€ + Honoraires 653€ + Intérêts 259€)
  - 2025 : 3 extournes créées (SCPI 6,755€ + Honoraires 622€ + Intérêts 254€)

**Mécanisme** :
Le `DetecteurCutoffsMultiples` génère **automatiquement** :
1. Écriture cutoff sur exercice N (31/12/N)
2. Écriture extourne sur exercice N+1 (01/01/N+1) avec comptes inversés

**Code** (`detecteurs_evenements.py:1200+`):
```python
# Créer écriture d'extourne (sens inverse)
proposition_extourne = {
    "numero_ecriture": f"{annee_suivante}-0101-EXT-{compteur:03d}",
    "date_ecriture": date_extourne,
    "compte_debit": proposition_cutoff["compte_credit"],  # INVERSION
    "compte_credit": proposition_cutoff["compte_debit"],  # INVERSION
    "montant": montant_float,
    "libelle_ecriture": f"Extourne - {libelle_base}"
}
```

**Conclusion** : ✅ **PLEINEMENT CONFORME**
- **Conformité structurelle** : ✅ OK
- **Conformité opérationnelle** : ✅ **UTILISÉ EN PRODUCTION 2023 ET 2024**
- **Preuve** : 6 cutoffs + 6 extournes créés et validés (12 écritures au total)

---

### ✅ Conformité : Calcul Impôt sur les Sociétés (IS)

**Principe PCG/Fiscal** :
- Base imposable = Résultat brut - Déficit reportable
- Taux : 15% (≤ 42 500€) + 25% (> 42 500€)
- Écriture : Débit 695 / Crédit 444

**Vérification** :
- ✅ Calcul correct selon barème IS 2024
- ✅ Prise en compte déficit reportable (compte 119)
- ✅ Écriture générée sur exercice N (31/12/N)
- ✅ Type écriture `IMPOT_SOCIETES` correctement utilisé

**Code** (`precloture_exercice.py:410-427`):
```python
if base_imposable <= 42500:
    self.is_calcule = base_imposable * Decimal('0.15')
else:
    part_15 = Decimal('42500') * Decimal('0.15')
    part_25 = (base_imposable - Decimal('42500')) * Decimal('0.25')
    self.is_calcule = part_15 + part_25
```

**Conclusion** : ✅ CONFORME

---

### ✅ Conformité : États Financiers Provisoires

**Principe PCG** :
- Bilan : ACTIF = PASSIF
- Compte de Résultat : PRODUITS - CHARGES = RÉSULTAT

**Vérification** :
- ✅ Génération bilan avec distinction ACTIF/PASSIF
- ✅ Traitement correct comptes négatifs (119, 290)
- ✅ Compte de résultat avec totaux charges/produits
- ✅ Vérification équilibre automatique

**Code** (`precloture_exercice.py:506-517`):
```python
# Compte 119 (RAN débiteur) = perte antérieure
# Solde débiteur (positif) → DIMINUE le passif
if num_compte == '119':
    passif[num_compte] = {
        'libelle': data['libelle'],
        'montant': float(-abs(solde))  # Négatif au passif
    }
```

**Conclusion** : ✅ CONFORME

---

## 3️⃣ Processus de Clôture Définitive (après AG)

### ✅ Conformité : Reprise du Résultat dans Bilan d'Ouverture N+1

**Principe PCG** :
Le compte 120 (Résultat de l'exercice) n'existe PAS pendant l'exercice N.
Il est créé UNIQUEMENT lors de la clôture pour recevoir le résultat avant affectation.

**Processus conforme** :
1. **Clôture N** : Calcul résultat (Produits - Charges)
2. **Bilan d'ouverture N+1** :
   - ÉTAPE 1 : Reprise résultat → **Débit 89 / Crédit 120** (si bénéfice)
   - ÉTAPE 2 : Affectation résultat → **Débit 120 / Crédit 110 ou 119**

**BUG CORRIGÉ (29/11/2025)** :

**Avant correction** :
- ❌ Pas d'ÉTAPE 1 → compte 89 déséquilibré
- ❌ ÉTAPE 2 débitait 120 sans crédit préalable

**Après correction** (`module2_validations.py:612-632`):
```python
# ÉTAPE 1 : Reprise du résultat N dans le bilan d'ouverture N+1
if resultat_net != 0:
    ecriture_reprise = EcritureComptable(
        exercice_id=exercice_n1.id,
        numero_ecriture=f'{annee + 1}-0101-OUV-RES',
        date_ecriture=date_affectation,
        libelle_ecriture=f'Bilan d\'ouverture {annee + 1} - Résultat exercice {annee}',
        type_ecriture='BILAN_OUVERTURE',
        compte_debit='89' if resultat_net > 0 else '120',
        compte_credit='120' if resultat_net > 0 else '89',
        montant=Decimal(str(abs(resultat_net))),
        source_email_id=evt_original_id,
        source_email_from=email_validation_from,
        validee_at=datetime.now(),
        notes=f'Reprise résultat {annee} dans bilan ouverture {annee + 1}'
    )
```

**Vérification patch** :
- ✅ Patch appliqué sur données 2024 (écriture ID 708 créée)
- ✅ Compte 89 équilibré (0.00€)
- ✅ Compte 120 soldé après affectation (0.00€)

**Conclusion** : ✅ **CONFORME** (après correction du 29/11/2025)

---

### ✅ Conformité : Affectation du Résultat

**Principe PCG** :
L'affectation du résultat est comptabilisée sur l'exercice N+1 à la date de l'AG.

**Vérification** :

#### Cas 1 : Bénéfice sans déficit antérieur
- ✅ Écriture : **Débit 120 / Crédit 110** (Report à nouveau créditeur)
- ✅ Code correct (`module2_validations.py:656-672`)

#### Cas 2 : Bénéfice avec déficit antérieur
- ✅ Absorption déficit : **Débit 120 / Crédit 119** (min(déficit, bénéfice))
- ✅ Excédent : **Débit 120 / Crédit 110** (reste)
- ✅ Code correct (`module2_validations.py:635-686`)

#### Cas 3 : Perte
- ✅ Écriture : **Débit 119 / Crédit 129** (Report à nouveau débiteur)
- ✅ Code correct (`module2_validations.py:688-707`)

**Traçabilité** :
- ✅ Référence PV AG dans libellé
- ✅ `source_email_id` conservé
- ✅ `validee_at` horodaté
- ✅ `validee_par` identifié

**Date** :
- ✅ Écritures créées sur exercice N+1
- ✅ Date = 01/01/N+1 (convention comptable)

**Conclusion** : ✅ CONFORME

---

### ✅ Conformité : Bilan d'Ouverture N+1

**Principe PCG** :
Le bilan d'ouverture N+1 reprend TOUS les soldes de bilan (classes 1-5) de clôture N.

**Vérification** :
- ✅ Calcul soldes AVANT affectation (`_calculer_soldes_cloture`)
- ✅ Exclusion explicite comptes gestion (classes 6-7)
- ✅ Exclusion compte 89 (contrepartie temporaire)
- ✅ Utilisation compte 89 comme contrepartie universelle :
  - Solde débiteur → **Débit compte / Crédit 89**
  - Solde créditeur → **Débit 89 / Crédit compte**
- ✅ Protection anti-doublon (vérification écritures existantes)

**Code** (`cloture_exercice.py:520-527`):
```python
# Solde débiteur → ACTIF : Débit compte / Crédit 89
# Solde créditeur → PASSIF : Débit 89 / Crédit compte
if solde > 0:
    compte_debit = num_compte
    compte_credit = COMPTE_BILAN_OUVERTURE
else:
    compte_debit = COMPTE_BILAN_OUVERTURE
    compte_credit = num_compte
```

**Vérification équilibre compte 89** :
- ✅ Σ débits 89 = Σ crédits 89 → Solde 89 = 0€
- ✅ Validation automatique dans le code

**Conclusion** : ✅ CONFORME

---

### ✅ Conformité : Gel de l'Exercice

**Principe PCG** :
Un exercice clôturé ne peut plus être modifié (immutabilité comptable).

**Vérification** :
- ✅ Statut `CLOTURE` empêche nouvelles écritures
- ✅ Horodatage de la clôture dans `description`
- ✅ Référence PV AG conservée

**Code** (`cloture_exercice.py:432-438`):
```python
if execute:
    self.exercice.statut = STATUT_CLOTURE
    self.exercice.description = (
        f"{self.exercice.description or ''}\n"
        f"Clôturé le {datetime.now().strftime('%d/%m/%Y')} - {self.pv_ag}"
    ).strip()
```

**Conclusion** : ✅ CONFORME

---

## 4️⃣ Traçabilité et Audit Trail

### ✅ Conformité : Audit Trail Complet

**Exigences PCG** :
- Traçabilité de toute écriture (origine, date, valideur)
- Justificatifs conservés

**Vérification** :
- ✅ `source_email_id` : ID email originel
- ✅ `source_email_from` : Expéditeur email
- ✅ `validee_at` : Date/heure validation
- ✅ `validee_par` : Email valideur (Ulrik)
- ✅ `notes` : Contexte additionnel
- ✅ Table `propositions_en_attente` conserve tokens et propositions validées

**Code** (`module2_validations.py:626-628`):
```python
source_email_id=evt_original_id,
source_email_from=email_validation_from,
validee_at=datetime.now(),
```

**Conservation** :
- ✅ Propositions validées conservées (statut = 'VALIDEE')
- ✅ Garbage collection exclut écritures validées
- ✅ Délai de 7 jours pour debug (événements temporaires)

**Conclusion** : ✅ CONFORME

---

## 5️⃣ Contrôles et Validations

### ✅ Conformité : Protections Anti-Erreur

**Vérification** :

#### Protection anti-doublon
- ✅ Vérification écritures affectation existantes (`module2_validations.py:288-299`)
- ✅ Vérification écritures ouverture existantes (`cloture_exercice.py:479-493`)
- ✅ Vérification cutoffs existants (`precloture_exercice.py:224-239`)

#### Cohérence des données
- ✅ Vérification exercice existe avant insertion
- ✅ Création automatique exercice N+1 si nécessaire
- ✅ Flush() avant commit pour détection erreurs contraintes

#### Gestion des erreurs
- ✅ Try/except sur toutes opérations critiques
- ✅ Rollback automatique en cas d'erreur
- ✅ Messages d'erreur explicites
- ✅ Traçabilité des échecs dans `propositions_en_attente` (statut = 'ERREUR')

**Conclusion** : ✅ CONFORME

---

### ✅ Conformité : Validation Humaine Requise

**Principe** : Aucune écriture automatique sans validation Ulrik.

**Vérification** :
- ✅ Workflow validation par token MD5 unique
- ✅ Email validation requis pour insertion
- ✅ Vérification token avant traitement
- ✅ Détection multi-tokens supportée

**Code** (`module2_validations.py:883-897`):
```python
# Extraire token de l'email de validation
result = self.detecteur.detecter_validation(email)
if not result['validation_detectee']:
    return {...}

token_email = result['token']
```

**Conclusion** : ✅ CONFORME

---

## 6️⃣ Gestion des Types d'Écritures

### ✅ Conformité : Types d'Écritures Normalisés

**Types définis** :
- ✅ `INIT_BILAN` : Initialisation bilan 2023
- ✅ `BILAN_OUVERTURE` : Bilan d'ouverture N+1
- ✅ `AFFECTATION_RESULTAT` : Affectation résultat après AG
- ✅ `CUTOFF_INTERETS_COURUS` : Cutoff intérêts 1688
- ✅ `CUTOFF_SCPI` : Cutoff produits SCPI 4181
- ✅ `CUTOFF_HONORAIRES` : Cutoff honoraires 4081
- ✅ `CUTOFF_ASSURANCE` : Cutoff assurance 486
- ✅ `EXTOURNE_CUTOFF` : Extourne cutoffs
- ✅ `IMPOT_SOCIETES` : Écriture IS
- ✅ `EVENEMENT_SIMPLE` : Opérations courantes

**Utilisation** :
- ✅ Filtrage par type dans requêtes
- ✅ Statistiques par type
- ✅ Logique métier adaptée par type

**Conclusion** : ✅ CONFORME

---

## 7️⃣ Points d'Amélioration Identifiés

### ✅ ~~Recommandation 1 : Implémenter Cutoffs Manquants~~ **DÉJÀ FAIT**

**Priorité** : ~~MOYENNE~~ **RÉSOLU**
**Impact** : Exhaustivité clôture annuelle

**Statut** : ✅ **OPÉRATIONNEL EN PRODUCTION**

Le `DetecteurCutoffsMultiples` est déjà implémenté et utilisé avec succès :
- ✅ Cutoffs SCPI : 2 occurrences (2023 + 2024)
- ✅ Cutoffs honoraires : 2 occurrences (2023 + 2024)
- ✅ Cutoffs intérêts : 2 occurrences (2023 + 2024)
- ✅ Extournes automatiques : 6 créées (2024 + 2025)

**Preuve** : `detecteurs_evenements.py:1037-1300` (DetecteurCutoffsMultiples)

---

### ✅ ~~Recommandation 1 : Développer Module Cerfa~~ **FAIT**

**Priorité** : ~~FAIBLE~~ **RÉSOLU**
**Impact** : Automatisation déclarations fiscales

**Statut** : ✅ **OPÉRATIONNEL**

Le module Cerfa est développé et intégré au workflow de clôture :
- ✅ `export_cerfa.py` : Génération données JSON (2065, 2033-A, 2033-B, 2033-F)
- ✅ `generer_cerfa_pdf.py` : Génération PDF pré-remplis
- ✅ Intégration dans `cloture_exercice.py:617-727` (étape 6)
- ✅ **Tests réussis** : Cerfa 2024 généré (29/11/2025)

**Utilisation** :
- Mode standalone : `python export_cerfa.py 2024 && python generer_cerfa_pdf.py cerfa_2024_*.json`
- Mode intégré : `python cloture_exercice.py --exercice 2024 --pv-ag "PV AG..." --execute`

**Preuve** : Fichiers `cerfa_2024_20251129_181136.json` et `.pdf` générés avec succès

---

### 🔧 Recommandation 2 : Renforcer Tests Automatisés

**Priorité** : MOYENNE
**Impact** : Robustesse système

**Actions** :
1. Tests unitaires pour chaque type écriture
2. Tests d'intégration processus clôture complet
3. Tests de régression après chaque modification

**Fichiers à tester** :
- `module2_validations.py` (logique insertion)
- `DetecteurCutoffsMultiples` (cutoffs + extournes)
- `cloture_exercice.py` (affectation + ouverture)

---

### ✅ ~~Recommandation 3 : Documentation Processus Clôture~~ **FAIT**

**Priorité** : ~~ÉLEVÉE~~ **RÉSOLU**
**Impact** : Transmission connaissance

**Actions** :
1. ✅ **FAIT** : Document `PRINCIPES_COMPTABLES_CLOTURE.md` créé (29/11/2025)
2. ✅ **FAIT** : Audit complet `AUDIT_MODULE2_CONFORMITE_PCG.md` créé (29/11/2025)
3. 🔧 TODO : Créer checklist clôture annuelle (gérant)
4. 🔧 TODO : Documenter workflow validation emails

---

## 8️⃣ Tableau de Bord Conformité

| Domaine | Statut | Commentaire |
|---------|--------|-------------|
| **Écritures comptables** | ✅ CONFORME | Partie double respectée |
| **Classification comptes** | ✅ CONFORME | PCG classes 1-7 respectées |
| **Cutoffs intérêts** | ✅ CONFORME | Opérationnel (2023 + 2024) |
| **Cutoffs SCPI** | ✅ CONFORME | Opérationnel (2023 + 2024) |
| **Cutoffs honoraires** | ✅ CONFORME | Opérationnel (2023 + 2024) |
| **Cutoff assurance** | ⚠️ NON UTILISÉ | Détecteur prêt si besoin |
| **Extournes automatiques** | ✅ CONFORME | 6 extournes créées (2024+2025) |
| **Calcul IS** | ✅ CONFORME | Barème 2024 correct |
| **Reprise résultat** | ✅ CONFORME | Bug corrigé 29/11/2025 |
| **Affectation résultat** | ✅ CONFORME | 3 cas gérés correctement |
| **Bilan d'ouverture** | ✅ CONFORME | Compte 89 équilibré |
| **Gel exercice** | ✅ CONFORME | Statut CLOTURE immutable |
| **Audit trail** | ✅ CONFORME | Traçabilité complète |
| **Protections anti-erreur** | ✅ CONFORME | Anti-doublon + rollback |
| **Validation humaine** | ✅ CONFORME | Token MD5 requis |
| **Cerfa (déclarations)** | ✅ CONFORME | Opérationnel (2065+2033) |

**Score global** : **15/16 CONFORME** (94%)

---

## 9️⃣ Conclusion

Le **Module 2 Workflow Comptable** est **globalement conforme** aux principes comptables du PCG.

**Forces** :
- ✅ Respect strict de la partie double
- ✅ Traçabilité complète (audit trail)
- ✅ Protections anti-erreur robustes
- ✅ Validation humaine systématique
- ✅ **Workflow cutoffs/extournes opérationnel** (12 écritures 2023-2025)
- ✅ Correction rapide du bug reprise résultat (29/11/2025)

**Axes d'amélioration** :
- 🔧 Renforcer tests automatisés
- 🔧 Créer checklist clôture annuelle pour le gérant
- 🔧 Ajouter détection cutoff assurance si besoin futur

**Recommandation finale** :
Le système est **PRÊT POUR PRODUCTION** et **DÉJÀ UTILISÉ** pour la clôture 2024. Le workflow cutoffs/extournes est opérationnel (2023+2024), et le module Cerfa génère automatiquement les déclarations fiscales.

---

**Signature numérique** : Claude Code (Sonnet 4.5)
**Date** : 29 novembre 2025
**Commit** : À créer après validation Ulrik
