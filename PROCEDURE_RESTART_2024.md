# 🔄 PROCÉDURE RESTART COMPTABILITÉ 2024

**Date:** 09 novembre 2025
**Objectif:** Nettoyer et resoumettre la comptabilité 2024 avec le code corrigé
**Préservation:** Bilan 2023 (exercice 2023) INTACT

---

## 🐛 Bugs Corrigés

### 1. Date d'écriture = Date de traitement (au lieu de date d'opération)

**Fichier:** `module2_validations.py:387`

**Avant:**
```python
date_ecriture=datetime.now().date(),  # ❌ Date de validation
```

**Après:**
```python
date_ecriture=prop.get('date_ecriture'),  # ✅ Date opération réelle
```

**Impact:**
Toutes les écritures comptables avaient la date de validation au lieu de la date bancaire réelle.

---

### 2. Remboursements prêts non décomposés

**Fichier:** `detecteurs_evenements.py:167-294`

**Avant:**
- 1 écriture temporaire: 164 → 512 (montant total)

**Après:**
- 2 écritures automatiques:
  - 661 (Intérêts) → 512
  - 164 (Capital) → 512

**Impact:**
Ventilation correcte intérêts/capital selon PCG, avec lookup automatique dans `echeances_prets`.

---

## ⚠️ Problème Gap Octobre

### Constat

- **Fichier Q1-Q3** : Déborde sur début octobre
- **Fichier Q4** : Démarre avec un relevé ultérieur
- **Conséquence** : Événements comptables manquants entre les deux

### Actions Requises

1. **Identifier le gap exact:**
   - Fichier Q1-Q3 : Dernière date ?
   - Fichier Q4 : Première date ?

2. **Récupérer les opérations manquantes:**
   - Option A : Demander relevé complémentaire à la banque
   - Option B : Extraction manuelle des opérations

3. **Créer fichier gap si nécessaire**

---

## 📋 Procédure de Nettoyage

### Étape 1 : Simulation

```bash
python nettoyer_et_resoumettre.py --dry-run
```

**Vérifie:**
- Nombre d'écritures 2024 à supprimer
- Nombre d'événements 2024 à supprimer
- Nombre de propositions à supprimer
- **Bilan 2023 PRÉSERVÉ**

### Étape 2 : Sauvegarde Automatique

Avant exécution réelle, le script crée automatiquement:
```
backups/avant_nettoyage_YYYYMMDD_HHMMSS.json
```

### Étape 3 : Exécution Réelle

```bash
python nettoyer_et_resoumettre.py --execute
```

**Supprime:**
- ✅ Écritures exercice 2024
- ✅ Événements comptables 2024
- ✅ Propositions en attente

**Préserve:**
- 🔒 Bilan 2023 (11 écritures, 571 613€)
- 🔒 Exercice 2023
- 🔒 Prêts immobiliers (référence)
- 🔒 Échéances prêts (référence)

---

## 📥 Procédure de Resoumission

### Ordre de Soumission

1. **Q1-Q3 Complet** (janvier-septembre + début octobre)
2. **Gap Octobre** (si fichier complémentaire disponible)
3. **Q4 Complet** (octobre-décembre)

### Workflow par Fichier

Pour chaque relevé bancaire PDF:

1. **Envoi email à _Head.Soeurise** avec PDF en pièce jointe
2. **Analyse automatique** (réveil suivant à 08:00 UTC)
3. **Réception propositions** par email avec token `HEAD-XXXXXXXX`
4. **Validation Ulrik:**
   ```
   [_Head] VALIDE: HEAD-XXXXXXXX
   ```
5. **Insertion automatique** en base de données
6. **Vérifications:**
   - ✅ Dates d'écritures = Dates d'opérations bancaires
   - ✅ Remboursements prêts décomposés (2 écritures)
   - ✅ Montants corrects
   - ✅ Comptes corrects

---

## 🔍 Vérifications Post-Resoumission

### Vérifier les dates d'écritures

```sql
SELECT
    date_ecriture,
    libelle_ecriture,
    montant,
    compte_debit,
    compte_credit
FROM ecritures_comptables
WHERE exercice_id = (SELECT id FROM exercices_comptables WHERE annee = 2024)
ORDER BY date_ecriture, id
LIMIT 20;
```

**Attendu:** `date_ecriture` = date opération bancaire (pas date validation)

### Vérifier décomposition prêts

```sql
SELECT
    date_ecriture,
    libelle_ecriture,
    type_ecriture,
    compte_debit,
    montant
FROM ecritures_comptables
WHERE type_ecriture IN ('INTERET_PRET', 'REMBOURSEMENT_CAPITAL')
ORDER BY date_ecriture;
```

**Attendu:**
- Pour chaque remboursement: 2 lignes (661 + 164)
- Total = montant échéance (montant_interet + montant_capital)

### Vérifier continuité chronologique

```sql
SELECT
    TO_CHAR(date_ecriture, 'YYYY-MM') as mois,
    COUNT(*) as nb_ecritures
FROM ecritures_comptables
WHERE exercice_id = (SELECT id FROM exercices_comptables WHERE annee = 2024)
GROUP BY TO_CHAR(date_ecriture, 'YYYY-MM')
ORDER BY mois;
```

**Attendu:** Tous les mois de janvier à décembre 2024 présents (pas de gap)

---

## 🚀 Déploiement

### 1. Tests Locaux

```bash
# Vérifier que le code fonctionne
python -c "from module2_validations import *; print('OK')"
python -c "from detecteurs_evenements import *; print('OK')"
```

### 2. Commit et Push

```bash
git add module2_validations.py detecteurs_evenements.py nettoyer_et_resoumettre.py PROCEDURE_RESTART_2024.md
git commit -m "🔧 Correction bugs comptables + procédure restart 2024"
git push -u origin claude/restart-from-scratch-011CUu6NrcZgJcJYKeSYADjW
```

### 3. PR Auto-Merge

Le workflow GitHub Actions va automatiquement:
- Créer la PR vers `main`
- Merger vers `main`

### 4. Déploiement Manuel Render

**⚠️ IMPORTANT:** Déploiement = MANUEL par Ulrik UNIQUEMENT

1. Se connecter à Render.com
2. Sélectionner `head-soeurise-web`
3. Cliquer "Manual Deploy" → "Deploy latest commit"
4. Attendre 2-3 minutes
5. Vérifier logs: "Deployed successfully"

---

## ✅ Checklist Complète

### Avant Nettoyage

- [ ] Code corrigé mergé vers `main`
- [ ] Déploiement manuel effectué sur Render
- [ ] Simulation nettoyage exécutée (`--dry-run`)
- [ ] Sauvegarde BD vérifiée (fichier JSON créé)

### Nettoyage

- [ ] Exécution réelle (`--execute`)
- [ ] Bilan 2023 vérifié INTACT (11 écritures)
- [ ] Base 2024 vide (0 écritures exercice 2024)

### Resoumission

- [ ] Gap octobre identifié (dates exactes)
- [ ] Fichier gap octobre créé (si nécessaire)
- [ ] Q1-Q3 soumis et validé
- [ ] Gap octobre soumis et validé (si applicable)
- [ ] Q4 soumis et validé

### Vérifications Finales

- [ ] Dates d'écritures = dates opérations bancaires
- [ ] Remboursements prêts décomposés (2 écritures/échéance)
- [ ] Tous les mois 2024 couverts (jan-déc)
- [ ] Balance exercice 2024 cohérente
- [ ] Aucune proposition en attente orpheline

---

## 📞 Support

**Questions ?** Consulter:
- `ARCHITECTURE.md` - Architecture générale V6.1
- `RAPPORT_ARCHITECTURE_MODULE2.md` - Workflow 9 phases détaillé
- `CLAUDE.md` - Contexte projet complet

**Logs Render:**
```bash
# Via Render Shell
tail -f /var/log/app.log
```

---

**Version:** 1.0 - 09 novembre 2025
**Auteur:** Module 2 - Maintenance & Restart Procedure
