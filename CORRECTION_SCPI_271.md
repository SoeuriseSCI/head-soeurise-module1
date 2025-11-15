# 🔧 Correction Compte SCPI : 280 → 271

**Date** : 15 novembre 2025
**Contexte** : Correction classification parts SCPI
**Script** : `corriger_compte_scpi_271.py`

---

## 📋 Erreur Identifiée

### Situation Actuelle (Incorrecte)
Les parts de SCPI Epargne Pierre (**500 032 €**) ont été classées au compte **280 "Amortissements des immobilisations incorporelles"**.

**Écriture concernée :**
- Date: 01/01/2023 (Bilan d'ouverture)
- Libellé: "Titres immobilisés" ou "SCPI Epargne Pierre"
- Montant: 500 032.00€
- Type: Bilan d'ouverture (INIT_BILAN)

### Nature Réelle
Le compte 280 ne convient **PAS** :
- ❌ Le compte 280 = "Amortissements des immobilisations incorporelles"
- ❌ Les parts de SCPI ne sont PAS des amortissements
- ❌ Ce compte diminue l'actif (contrepartie d'amortissement)

Les parts de SCPI sont **EN RÉALITÉ** :
- ✅ Des **immobilisations financières**
- ✅ Des titres de placement à long terme
- ✅ Doivent être classées dans la classe 27 "Autres immobilisations financières"

### Classification Correcte
**Compte approprié** : **271 "Titres immobilisés (autres que les titres immobilisés de l'activité de portefeuille - TIAP)"**

---

## 💰 Impact Comptable

### Au Bilan - ACTIF

**AVANT correction :**
```
ACTIF
  Immobilisations
    280 Amortissements des immobilisations incorporelles : 500 032 € ❌
```

**APRÈS correction :**
```
ACTIF
  Immobilisations
    27 Autres immobilisations financières
      271 Titres immobilisés : 500 032 € ✅
```

**Impact** : Reclassement de **500 032 €** au sein de l'actif immobilisé.

---

## ⚖️ Bilan Équilibre

### Équation Comptable

**AVANT et APRÈS :**
- Actif total : **inchangé** (500 032 €)
- Passif : **inchangé**
- Résultat : **inchangé**

**Seule la classification change** : Le montant reste à l'actif mais dans le bon compte.

**Formule :**
```
ACTIF = PASSIF
(280 - 500 032) + (271 + 500 032) = PASSIF
```

✅ Le bilan reste équilibré (reclassement sans impact sur le total).

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
python corriger_compte_scpi_271.py
```

**Résultat** : Affiche les écritures qui seraient corrigées, sans modifier la base.

### Mode Exécution Réelle

```bash
# Modifier le script :
DRY_RUN = False

# Exécuter :
python corriger_compte_scpi_271.py
```

**Étapes :**
1. ✅ Identification automatique des écritures au compte 280
2. ✅ Affichage des écritures concernées
3. ⚠️  **Demande de confirmation** : Taper `oui`
4. ✅ Correction : UPDATE compte 280 → 271
5. ✅ Vérification post-correction

### Sur Render Shell

```bash
# Se connecter au shell Render
# https://dashboard.render.com → Service → Shell

# Exécuter le script
python corriger_compte_scpi_271.py

# Vérifier la correction
psql $DATABASE_URL -c "
  SELECT compte_id, COUNT(*), SUM(debit)
  FROM ecritures
  WHERE libelle ILIKE '%SCPI%'
    AND compte_id IN ('280', '271')
  GROUP BY compte_id;
"
```

**Résultat attendu :**
```
compte_id | count | sum
----------+-------+-----------
271       | 1     | 500032.00
```

---

## ✅ Validation Post-Correction

### 1. Vérifier l'écriture au compte 271

```sql
SELECT id, date_ecriture, libelle, debit
FROM ecritures
WHERE compte_id = '271'
ORDER BY date_ecriture;
```

**Attendu :** 1 écriture de 500 032 €.

### 2. Vérifier qu'aucune écriture SCPI ne reste au compte 280

```sql
SELECT COUNT(*)
FROM ecritures
WHERE compte_id = '280'
  AND (libelle ILIKE '%SCPI%' OR libelle ILIKE '%Titres immobilisés%');
```

**Attendu :** 0

### 3. Vérifier l'équilibre du bilan

```bash
python verifier_bilan_2023.py
```

**Attendu :** Bilan équilibré (ACTIF = PASSIF = 571 613 €)

---

## 📊 Impact sur les Documents Comptables

### Bilan (État du Patrimoine)
- **ACTIF** : Reclassement au sein des immobilisations
  - Compte 280 : -500 032 € ❌
  - Compte 271 : +500 032 € ✅
- **Total ACTIF** : Inchangé (571 613 €)

### Compte de Résultat
- ✅ Aucun impact (mouvement de bilan uniquement)

### Balance des Comptes
- Compte 280 : Diminution de 500 032 € (ou 0 si c'était la seule écriture)
- Compte 271 : Augmentation de 500 032 €

---

## 📖 Références Comptables

**Plan Comptable Général (PCG) :**

- **Compte 280** : Amortissements des immobilisations incorporelles
  - Classe 2 (Immobilisations)
  - Sous-classe 28 (Amortissements des immobilisations)
  - Nature : Compte de bilan (ACTIF - diminution)
  - Usage : Contrepartie des dotations aux amortissements

- **Compte 271** : Titres immobilisés (autres que les TIAP)
  - Classe 2 (Immobilisations)
  - Sous-classe 27 (Autres immobilisations financières)
  - Nature : Compte de bilan (ACTIF)
  - Usage : Parts de SCPI, obligations, actions détenues à long terme

**Principe de classification :**
- Parts de SCPI = Immobilisations financières → Classe 27 (non 28)
- Amortissements = Diminution de valeur comptable → Classe 28

---

## 🎯 Conclusion

### Pourquoi cette correction ?

1. **Exactitude comptable** : Les parts de SCPI sont des immobilisations financières
2. **Conformité PCG** : Respecter la classification du plan comptable
3. **Clarté** : Distinguer les immobilisations financières des amortissements
4. **Image fidèle** : Le bilan doit refléter la nature réelle des actifs

### Impact Global

- ✅ Amélioration de la qualité comptable
- ✅ Conformité avec le PCG
- ✅ Meilleure lisibilité du bilan
- ✅ Aucun impact sur les totaux (reclassement)

---

**Version** : 1.0
**Auteur** : _Head.Soeurise
**Statut** : Prêt pour exécution sur Render
