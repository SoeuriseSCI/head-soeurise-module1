# Correction des Remises LCL - Plan Détaillé

**Date** : 14 novembre 2025
**Auteur** : Claude Code (Sonnet 4.5)
**Contexte** : Construction états financiers 2024

---

## 🎯 Problème Identifié

### État Actuel (INCORRECT)

Les **remises LCL** (bank fee rebates) sont comptabilisées comme suit :

```
Débit  627 (Frais bancaires et commissions)
Crédit 512 (Banque LCL)
Montant: 0.22€ (positif)
```

**Impact** : Cela **AUGMENTE** les charges au lieu de les **DIMINUER**.

### État Souhaité (CORRECT - Plan Comptable Général)

Les remises doivent être comptabilisées comme une **réduction de charges** :

```
Débit  512 (Banque LCL)
Crédit 627 (Frais bancaires et commissions)
Montant: 0.22€
```

**Impact** : Cela **DIMINUE** les charges (crédit du compte 627).

---

## 📊 Écritures Concernées

### Identification

**Critères** :
- Type : `FRAIS_BANCAIRES`
- Libellé contient : `REMISE`, `VOTRE REM`, `REM LCL`, `REMBT`
- Exercice : 2024

**Commande d'identification** :
```bash
python identifier_remises_lcl_2024.py
```

**Résultat attendu** :
- ~12 écritures
- Montant total : ~2.63€
- Impact résultat : +5.26€ (2× le montant)

### Exemple Concret

```
ID: 123
Numéro: EVT-0042
Date: 2024-03-15
Libellé: VOTRE REMISE DU 15/03
Montant: 0.22€

ÉCRITURE ACTUELLE (INCORRECTE) :
  Débit  627 (Frais bancaires)     0.22€
  Crédit 512 (Banque)              0.22€
  → Augmente les charges de 0.22€

ÉCRITURE CORRECTE (À APPLIQUER) :
  Débit  512 (Banque)              0.22€
  Crédit 627 (Frais bancaires)     0.22€
  → Diminue les charges de 0.22€
```

---

## 🔧 Méthode de Correction

### Principe : Contre-Passation + Écriture Correcte

Pour chaque remise, créer **2 écritures** :

#### 1. Contre-Passation (Annulation)

Annule l'écriture incorrecte en inversant débit/crédit :

```
Numéro: EVT-0042-ANNUL
Libellé: Annulation écriture incorrecte - VOTRE REMISE DU 15/03
Débit  512 (Banque)              0.22€
Crédit 627 (Frais bancaires)     0.22€
Type: CORRECTION
```

#### 2. Écriture Correcte

Enregistre l'écriture qui aurait dû être faite :

```
Numéro: EVT-0042-CORR
Libellé: Correction - VOTRE REMISE DU 15/03
Débit  512 (Banque)              0.22€
Crédit 627 (Frais bancaires)     0.22€
Type: FRAIS_BANCAIRES
```

### Résultat Net

Pour 1 remise de 0.22€ :

**Compte 512 (Banque)** :
- Écriture originale : Crédit -0.22€
- Contre-passation : Débit +0.22€
- Écriture correcte : Débit +0.22€
- **Solde final : +0.22€** (inchangé car les 2 nouvelles s'annulent)

**Compte 627 (Frais bancaires)** :
- Écriture originale : Débit +0.22€ (augmente charges)
- Contre-passation : Crédit -0.22€ (annule)
- Écriture correcte : Crédit -0.22€ (diminue charges)
- **Solde final : -0.22€ × 2 = -0.44€**

**Résultat** : Diminue charges de **2× le montant de la remise** ✅

---

## 🚀 Procédure d'Exécution

### 1. Identification (Dry-Run)

```bash
python identifier_remises_lcl_2024.py
```

**Output attendu** :
- Liste des remises détectées
- Montants
- Impact prévisionnel
- Plan de correction détaillé

### 2. Sauvegarde (OBLIGATOIRE)

Avant toute modification, sauvegarder la base :

```bash
python sauvegarder_base.py
# OU
bash sauvegarder_base.sh
```

### 3. Correction

```bash
python corriger_remises_lcl_2024.py
```

**Demande de confirmation** :
```
Cette opération va créer 24 nouvelles écritures :
- 12 contre-passations
- 12 écritures correctes

Impact final :
- Résultat 2024 : +5.26€
- Charges (627) : -5.26€

Tapez 'OUI' pour confirmer :
```

### 4. Vérification

Reconstruire les états financiers pour vérifier l'impact :

```bash
python construire_etats_financiers_2024.py
```

**Vérifier** :
- Résultat augmente de ~5€
- Charges diminuent de ~5€
- Bilan reste équilibré

---

## 🔄 Correction du Traitement Futur

Pour éviter que ce problème se reproduise lors des prochaines extractions.

### Option 1 : Type Distinct (Plus complexe)

**Modifier** : `gestionnaire_evenements.py` (ligne ~228)

**Avant** :
```python
elif ('frais' in libelle_norm or 'cotisation' in libelle_norm or
      'abon' in libelle_norm or 'abonnement' in libelle_norm or
      'remise' in libelle_norm or 'lcl a la carte' in libelle_norm):
    type_evt = 'FRAIS_BANCAIRES'
```

**Après** :
```python
# Remises bancaires (réduction de charges) - À TRAITER EN PREMIER
elif ('remise' in libelle_norm or 'votre rem' in libelle_norm):
    type_evt = 'REMISE_FRAIS_BANCAIRES'  # Nouveau type

# Frais bancaires (charges normales)
elif ('frais' in libelle_norm or 'cotisation' in libelle_norm or
      'abon' in libelle_norm or 'abonnement' in libelle_norm or
      'lcl a la carte' in libelle_norm):
    type_evt = 'FRAIS_BANCAIRES'
```

**Puis ajouter** : Logique de génération des propositions pour `REMISE_FRAIS_BANCAIRES` (même écriture que FRAIS_BANCAIRES mais avec sens inversé).

---

### Option 2 : Prompt Universel (RECOMMANDÉ ✅)

**Modifier** : `extracteur_intelligent.py` - Prompt universel

**Ajouter règle** dans le prompt (section "Règles de Comptabilisation") :

```python
prompt_universel = f"""
...

## Règles de Comptabilisation Spécifiques

### Remises Bancaires (Réduction de Charges)
Pour les opérations dont le libellé contient "REMISE", "VOTRE REM", "REM LCL" :

**Écriture comptable** :
- Compte débit : 512 (Banque)
- Compte crédit : 627 (Frais bancaires)
- Catégorie : "FRAIS_BANCAIRES"
- Details : "Remise bancaire - Diminution charges"

**IMPORTANT** : Les remises sont des RÉDUCTIONS de charges, donc :
- La banque est débitée (augmentation trésorerie)
- Le compte 627 est crédité (diminution charges)

### Frais Bancaires (Charges Normales)
Pour les autres frais bancaires (cotisations, abonnements, etc.) :

**Écriture comptable** :
- Compte débit : 627 (Frais bancaires)
- Compte crédit : 512 (Banque)
- Catégorie : "FRAIS_BANCAIRES"

...
"""
```

**Avantages** :
- ✅ Pas de nouveau type d'événement
- ✅ Claude gère automatiquement l'inversion
- ✅ Cohérent avec l'architecture V8.0 (intelligence Claude)
- ✅ Plus simple à maintenir

---

## 📈 Impact Prévisionnel

### Sur les États Financiers 2024

**Compte de Résultat** :
```
Charges (classe 6) :
  Avant correction : X€
  Après correction : X - 5.26€

Résultat :
  Avant correction : Y€
  Après correction : Y + 5.26€
```

**Bilan** :
```
ACTIF reste inchangé
PASSIF (résultat) : +5.26€

Équilibre : Maintenu ✅
```

### Impact Négligeable

Montant : ~5€ sur un résultat de plusieurs milliers d'euros.

**Mais** : Respect des principes comptables (zéro tolérance) ✅

---

## ⚠️ Points d'Attention

### Avant Correction

1. ✅ **Sauvegarde BD obligatoire**
2. ✅ **Dry-run** avec `identifier_remises_lcl_2024.py`
3. ✅ **Vérifier** que seules les remises sont identifiées (pas d'autres FB)

### Pendant Correction

1. ⚠️ **Confirmation manuelle** requise (saisir "OUI")
2. ⚠️ **Transaction atomique** (rollback si erreur)

### Après Correction

1. ✅ **Reconstruire états financiers** (`construire_etats_financiers_2024.py`)
2. ✅ **Vérifier équilibre bilan**
3. ✅ **Comparer avec documents officiels**
4. ✅ **Corriger traitement futur** (Option 2 recommandée)

---

## 📋 Checklist

- [ ] Lire ce document entièrement
- [ ] Identifier les remises : `python identifier_remises_lcl_2024.py`
- [ ] Sauvegarder la base : `python sauvegarder_base.py`
- [ ] Exécuter correction : `python corriger_remises_lcl_2024.py`
- [ ] Confirmer avec "OUI"
- [ ] Vérifier états financiers : `python construire_etats_financiers_2024.py`
- [ ] Corriger traitement futur (Option 2)
- [ ] Commit et push
- [ ] Déploiement manuel (Ulrik)

---

## 🎯 Conclusion

**Problème** : Remises comptabilisées en débit 627 → augmentent charges
**Solution** : Contre-passation + Écriture correcte → diminuent charges
**Impact** : +5€ sur résultat 2024 (négligeable mais correct)
**Prévention** : Modifier prompt universel extracteur intelligent (Option 2)

**Philosophie** : Zéro tolérance en comptabilité, même pour 5€ ✅

---

**Date** : 14 novembre 2025
**Version** : 1.0
**Auteur** : Claude Code (Sonnet 4.5)
