# 🔧 Correction Compte SCPI : 106 → 768

**Date** : 15 novembre 2025
**Contexte** : Correction classification plus-values SCPI
**Script** : `corriger_compte_scpi_768.py`

---

## 📋 Erreur Identifiée

### Situation Actuelle (Incorrecte)
Les distributions de **1 202 €** (2 × 601 €) de la SCPI Epargne Pierre ont été classées au compte **106 "Réserves"**.

**Écritures concernées :**
1. VIR SEPA SCPI EPARGNE PIERRE - 601.00€
2. SCPI EPARGNE PIERRE DISTRIB CAPITAL - 601.00€

### Nature Réelle
Ces 1 202 € ne sont **PAS** :
- ❌ Des revenus trimestriels de la SCPI
- ❌ Une distribution de réserves

Ces 1 202 € sont **EN RÉALITÉ** :
- ✅ Un partage de **plus-value** suite à **cession d'un bien immobilier** par la SCPI
- ✅ Un produit financier exceptionnel

### Classification Correcte
**Compte approprié** : **768 "Autres produits financiers"**

---

## 💰 Impact Comptable

### Au Bilan

**AVANT correction :**
```
PASSIF
  Capitaux Propres
    106 Réserves : +1 202 € ❌
```

**APRÈS correction :**
```
PASSIF
  Capitaux Propres
    106 Réserves : 0 € (ou valeur initiale)
```

**Impact** : Diminution des capitaux propres de **-1 202 €**

---

### Au Compte de Résultat

**AVANT correction :**
```
(Aucun impact car compte de bilan uniquement)
```

**APRÈS correction :**
```
PRODUITS FINANCIERS (Classe 7)
  76 Produits financiers
    768 Autres produits financiers : +1 202 € ✅
```

**Impact** : Augmentation des produits financiers de **+1 202 €**

---

## ⚖️ Bilan Équilibre

### Équation Comptable

**AVANT :**
- Actif : inchangé
- Passif : Capitaux propres (+1 202 € au 106)
- Résultat : 0

**APRÈS :**
- Actif : inchangé
- Passif : Capitaux propres (0 € au 106)
- Résultat : +1 202 € (compte 768)

**L'équilibre est maintenu** : Les 1 202 € sont transférés des capitaux propres vers le résultat de l'exercice.

**Formule :**
```
ACTIF = PASSIF + RÉSULTAT
(inchangé) = (Passif - 1 202) + (Résultat + 1 202)
```

✅ Le bilan reste équilibré.

---

## 🔧 Exécution du Script

### Prérequis
- Accès à la base de données PostgreSQL (environnement Render)
- Variable d'environnement `DATABASE_URL` configurée

### Mode Dry-Run (Simulation)

```bash
# Modifier le script :
DRY_RUN = True

# Exécuter :
python corriger_compte_scpi_768.py
```

**Résultat** : Affiche les écritures qui seraient corrigées, sans modifier la base.

### Mode Exécution Réelle

```bash
# Modifier le script :
DRY_RUN = False

# Exécuter :
python corriger_compte_scpi_768.py
```

**Étapes :**
1. ✅ Identification automatique des 2 écritures
2. ✅ Affichage des écritures concernées
3. ⚠️  **Demande de confirmation** : Taper `oui`
4. ✅ Correction : UPDATE compte 106 → 768
5. ✅ Vérification post-correction

### Sur Render Shell

```bash
# Se connecter au shell Render
# https://dashboard.render.com → Service → Shell

# Exécuter le script
python corriger_compte_scpi_768.py

# Vérifier la correction
psql $DATABASE_URL -c "
  SELECT compte_id, COUNT(*), SUM(credit)
  FROM ecritures
  WHERE libelle ILIKE '%SCPI EPARGNE PIERRE%'
  GROUP BY compte_id;
"
```

**Résultat attendu :**
```
compte_id | count | sum
----------+-------+---------
768       | 2     | 1202.00
```

---

## ✅ Validation Post-Correction

### 1. Vérifier les écritures au compte 768

```sql
SELECT id, date_ecriture, libelle, credit
FROM ecritures
WHERE compte_id = '768'
ORDER BY date_ecriture;
```

**Attendu :** 2 écritures de 601 € chacune.

### 2. Vérifier qu'aucune écriture SCPI ne reste au compte 106

```sql
SELECT COUNT(*)
FROM ecritures
WHERE compte_id = '106'
  AND libelle ILIKE '%SCPI%';
```

**Attendu :** 0

### 3. Vérifier l'équilibre du bilan

```bash
python verifier_bilan_2023.py  # Ou script de vérification 2024
```

**Attendu :** Bilan équilibré (ACTIF = PASSIF)

---

## 📊 Impact sur les Documents Comptables

### Bilan (État du Patrimoine)
- ⬇️ **Capitaux propres** : -1 202 € (compte 106)
- ➡️ Compensé par augmentation du résultat de l'exercice

### Compte de Résultat (Performance Financière)
- ⬆️ **Produits financiers** : +1 202 € (compte 768)
- ✅ Meilleure représentation de la performance financière

### Balance des Comptes
- Compte 106 : Diminution de 1 202 €
- Compte 768 : Augmentation de 1 202 €

---

## 📖 Références Comptables

**Plan Comptable Général (PCG) :**

- **Compte 106** : Réserves
  - Classe 1 (Capitaux)
  - Sous-classe 10 (Capital et réserves)
  - Nature : Compte de bilan (Passif)

- **Compte 768** : Autres produits financiers
  - Classe 7 (Produits)
  - Sous-classe 76 (Produits financiers)
  - Nature : Compte de gestion (Compte de résultat)

**Principe de classification :**
- Plus-value de cession = Produit exceptionnel → Classe 7 (Produits)
- Distribution de capital/réserves = Mouvement de capitaux → Classe 1

---

## 🎯 Conclusion

### Pourquoi cette correction ?

1. **Exactitude comptable** : Les plus-values de cession sont des produits, pas des réserves
2. **Image fidèle** : Le compte de résultat doit refléter tous les produits de l'exercice
3. **Conformité PCG** : Respecter le plan comptable général

### Impact Global

- ✅ Amélioration de la qualité comptable
- ✅ Meilleure visibilité sur la performance financière
- ✅ Conformité avec les principes comptables
- ✅ Aucun impact sur la trésorerie (mouvement déjà enregistré)

---

**Version** : 1.0
**Auteur** : _Head.Soeurise
**Statut** : Prêt pour exécution sur Render
