# Correction Compte 161 → 164 - Status

**Date** : 18 novembre 2025
**Branche** : `claude/fix-scpi-capital-gains-account-016Hgvb3aciKb2fokd1yaxMc`
**Commit** : `3f9e2f0` 🔧 Correction compte emprunts : 161 → 164

---

## ✅ TRAVAIL COMPLÉTÉ

### 1. Modifications Code (FAIT)

**Fichier `detecteurs_evenements.py`** :
- Ligne 182 : Documentation classe → Référence compte 164
- Ligne 275 : Génération écriture capital (avec échéance) → `compte_debit: '164'`
- Ligne 294 : Génération écriture capital (fallback) → `compte_debit: '164'`

**Résultat** : Tous les futurs remboursements de prêts utiliseront le compte 164 (correct).

### 2. Script de Correction Base de Données (CRÉÉ)

**Fichier `corriger_compte_161_vers_164.py`** :
- ✅ Crée compte 164 s'il n'existe pas
- ✅ Marque compte 161 comme obsolète (actif = false)
- ✅ Corrige TOUTES les écritures existantes (débit + crédit)
- ✅ Affiche vérifications post-correction
- ✅ Gestion complète des erreurs

### 3. Git (FAIT)

```bash
✅ Commit : 3f9e2f0
✅ Push   : origin/claude/fix-scpi-capital-gains-account-016Hgvb3aciKb2fokd1yaxMc
```

---

## ⏳ TRAVAIL RESTANT

### Exécution Script sur Render Shell

**IMPORTANT** : Le script ne peut pas être exécuté depuis l'environnement local (restrictions réseau).

**Où exécuter** : Sur Render Shell (accès direct à la base de données)

**Comment** :
1. Se connecter à Render Dashboard : https://dashboard.render.com/
2. Sélectionner le service `head-soeurise-web`
3. Ouvrir le Shell (bouton "Shell" en haut à droite)
4. Dans le shell, exécuter :

```bash
python corriger_compte_161_vers_164.py
```

5. **Confirmer** avec `oui` quand demandé

**Ce que le script va faire** :
```
[1/5] Créer compte 164
[2/5] Marquer compte 161 comme obsolète
[3/5] Analyser les écritures à corriger
[4/5] Corriger les écritures (après confirmation)
[5/5] Vérifier résultats
```

**Résultat attendu** :
- Compte 164 créé dans `plans_comptes`
- Compte 161 marqué obsolète (libellé + actif=false)
- Toutes les écritures corrigées : 161 → 164
  - Bilan d'ouverture 2024 (emprunt)
  - Tous les remboursements capital 2024
- Solde compte 164 affiché (créditeur = PASSIF)
- Compte 161 : 0 écritures restantes

---

## 📊 IMPACT

### Écritures Affectées

**Bilan d'ouverture 2024** :
- Emprunt initial (crédit) : 161 → 164

**Remboursements capital 2024** :
- Tous les remboursements mensuels (débit) : 161 → 164

**Estimation** : ~13-24 écritures (1 bilan + 11-23 remboursements selon date)

### Conformité PCG

| Avant (FAUX) | Après (CORRECT) |
|--------------|-----------------|
| **161** Emprunts obligataires convertibles | **164** Emprunts auprès des établissements de crédit |
| ❌ Incorrect pour emprunts bancaires | ✅ Correct pour prêts LCL + INVESTIMUR |

---

## 🔍 VÉRIFICATION POST-EXÉCUTION

Après exécution du script, vérifier :

```sql
-- 1. Compte 164 existe et est actif
SELECT * FROM plans_comptes WHERE numero_compte = '164';

-- 2. Compte 161 marqué obsolète
SELECT * FROM plans_comptes WHERE numero_compte = '161';

-- 3. Aucune écriture sur 161
SELECT COUNT(*) FROM ecritures_comptables
WHERE compte_debit = '161' OR compte_credit = '161';
-- Résultat attendu : 0

-- 4. Solde compte 164
SELECT
    SUM(CASE WHEN compte_debit = '164' THEN montant ELSE 0 END) as total_debit,
    SUM(CASE WHEN compte_credit = '164' THEN montant ELSE 0 END) as total_credit
FROM ecritures_comptables;
-- Résultat : total_credit > total_debit (PASSIF créditeur normal)
```

---

## ⚠️ NOTES IMPORTANTES

1. **Sauvegarde** : Render effectue des sauvegardes automatiques quotidiennes
2. **Réversibilité** : Le script pourrait être inversé si nécessaire (164 → 161)
3. **Exercice concerné** : Principalement 2024 (bilan ouverture + remboursements)
4. **Impact comptable** : Aucun sur les montants, uniquement classification

---

## 🎯 PROCHAINE ÉTAPE RECOMMANDÉE

**Après correction 161 → 164** :

Vérifier que le système complet est cohérent :

```bash
python verifier_bilan_2023.py  # Vérifier bilan 2023
python sauvegarder_base.py     # Créer sauvegarde post-correction
```

Puis :
- Merger la branche vers `main`
- Déployer sur Render (manuel par Ulrik)

---

**Statut Actuel** : ✅ Code prêt | ⏳ Exécution requise sur Render Shell
