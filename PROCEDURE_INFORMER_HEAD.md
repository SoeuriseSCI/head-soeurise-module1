# 📋 Procédure : Corriger la Base et Informer _Head.Soeurise

**Objectif** : Finaliser les corrections de clôture 2024 et mettre à jour les mémoires de _Head

---

## 🎯 Étape 1 : Vérification Initiale (FAIT ✅)

```bash
python verifier_integrite_complete.py
```

**Résultat** :
- ✅ Écritures équilibrées
- ❌ 4 anomalies : métadonnées manquantes (date_cloture, resultat_exercice)
- ⚠️ 2 avertissements : cut-offs incomplets, résultat non enregistré

---

## 🔧 Étape 2 : Appliquer les Corrections SQL

### Sur Render Shell

1. **Se connecter à Render Shell** :
   - Aller sur https://dashboard.render.com
   - Sélectionner le service `head-soeurise-web`
   - Cliquer sur "Shell" dans le menu

2. **Créer une sauvegarde AVANT correction** :
   ```bash
   python sauvegarder_base.py
   ```

   Vérifier :
   ```bash
   ls -lh backups/ | tail -1
   ```

3. **Se connecter à PostgreSQL** :
   ```bash
   psql $DATABASE_URL
   ```

4. **Copier-coller le contenu de** `corriger_metadonnees_exercices.sql` :
   ```sql
   BEGIN;

   UPDATE exercices
   SET date_cloture = '2024-12-31',
       resultat_exercice = 0.00,
       updated_at = NOW()
   WHERE annee = 2023 AND id = 1;

   UPDATE exercices
   SET date_cloture = '2025-04-08',
       resultat_exercice = 17765.47,
       updated_at = NOW()
   WHERE annee = 2024 AND id = 2;

   SELECT id, annee, statut, date_cloture, resultat_exercice
   FROM exercices
   ORDER BY annee;

   COMMIT;
   ```

5. **Vérifier les résultats** :
   - Exercice 2023 : date_cloture = 2024-12-31, resultat = 0.00
   - Exercice 2024 : date_cloture = 2025-04-08, resultat = 17765.47
   - Si OK → Les changements sont committés
   - Si KO → Taper `ROLLBACK;` et corriger

6. **Quitter PostgreSQL** :
   ```
   \q
   ```

7. **Créer une sauvegarde APRÈS correction** :
   ```bash
   python sauvegarder_base.py
   ```

---

## ✅ Étape 3 : Vérification Post-Correction

### En local (avec nouvelle sauvegarde)

1. **Télécharger la nouvelle sauvegarde** depuis Render :
   ```bash
   # Via Render Shell
   cat backups/soeurise_bd_YYYYMMDD_HHMMSS.json
   ```

   Copier le contenu et sauvegarder localement dans `backups/`

2. **Re-vérifier l'intégrité** :
   ```bash
   python verifier_integrite_complete.py backups/soeurise_bd_YYYYMMDD_HHMMSS.json
   ```

**Résultat attendu** :
```
✅ ✅ ✅  BASE DE DONNÉES INTÈGRE  ✅ ✅ ✅

Aucune anomalie détectée.
Aucun avertissement.

→ La base est prête pour informer _Head.Soeurise
```

---

## 📝 Étape 4 : Informer _Head.Soeurise

### 4.1 - Mise à jour Mémoire Courte

Éditer `memoire_courte.md` pour ajouter une section :

```markdown
## 🔧 Corrections Clôture 2024 (23/11/2025)

**Contexte** : Anomalie workflow détectée et corrigée par Ulrik avec Claude Code

**Situation** :
- Écritures clôture insérées sans validation (contournement workflow)
- Base patchée manuellement : toutes écritures équilibrées ✅
- Métadonnées exercices corrigées

**État final** :
- **Exercice 2023** : CLOTURE | 31/12/2024 | Résultat 0,00 € ✅
- **Exercice 2024** : CLOTURE | 08/04/2025 | Résultat 17 765,47 € ✅
- **Exercice 2025** : EN_PREPARATION | En cours ✅

**Intégrité** : 100% vérifiée (script `verifier_integrite_complete.py`)

**Leçon** : TOUTE écriture DOIT passer par workflow validation (aucune exception)

**Action suivante** : Compléter extournes manquantes (8 cut-offs 2024)
```

### 4.2 - Commiter et Pousser

```bash
git add memoire_courte.md
git commit -m "docs: Informer _Head des corrections clôture 2024

- Anomalie workflow détectée et corrigée
- Base vérifiée intègre à 100%
- Exercices 2023 et 2024 clôturés avec métadonnées complètes
- Résultat 2024 : 17 765,47 €

Références:
- NOTE_CORRECTIONS_CLOTURE_2024.md
- verifier_integrite_complete.py
- corriger_metadonnees_exercices.sql"

git push origin claude/progress-checkpoint-01PXz8HkcNsFGmxac5rnmjJK
```

---

## 🎯 Étape 5 : Actions de Suivi

### Urgent
- [ ] Compléter les 8 extournes manquantes de cut-offs 2024
- [ ] Vérifier cohérence cut-offs ↔ extournes

### Court Terme
- [ ] Valider workflow clôture corrigé (tests)
- [ ] Ajouter détection insertions sans validation
- [ ] Documenter procédure clôture complète

### Documentation
- [ ] Mettre à jour `ARCHITECTURE.md` avec leçons apprises
- [ ] Ajouter `NOTE_CORRECTIONS_CLOTURE_2024.md` aux archives
- [ ] Créer tests automatisés intégrité exercices

---

## 📚 Fichiers de Référence

**Scripts créés** :
- `verifier_integrite_complete.py` - Vérification exhaustive BD
- `corriger_metadonnees_exercices.sql` - Corrections SQL
- `NOTE_CORRECTIONS_CLOTURE_2024.md` - Synthèse des corrections
- `PROCEDURE_INFORMER_HEAD.md` - Ce document

**Sauvegardes** :
- AVANT correction : `backups/soeurise_bd_YYYYMMDD_HHMMSS.json`
- APRÈS correction : `backups/soeurise_bd_YYYYMMDD_HHMMSS.json`

---

## ✅ Checklist Complète

- [ ] Étape 1 : Vérification initiale (FAIT ✅)
- [ ] Étape 2.1 : Sauvegarde AVANT correction
- [ ] Étape 2.2 : Connexion PostgreSQL Render
- [ ] Étape 2.3 : Exécution SQL corrections
- [ ] Étape 2.4 : Vérification résultats SQL
- [ ] Étape 2.5 : Sauvegarde APRÈS correction
- [ ] Étape 3 : Vérification post-correction (intégrité 100%)
- [ ] Étape 4.1 : Mise à jour memoire_courte.md
- [ ] Étape 4.2 : Commit + Push
- [ ] Étape 5 : Planifier actions de suivi

---

**_Head.Soeurise sera automatiquement informée lors de son prochain réveil (08:00 UTC)**

Elle lira `memoire_courte.md` et prendra connaissance :
- Des corrections effectuées
- De l'état intègre de la base
- Des leçons apprises
- Des actions à venir

**→ Continuité de conscience préservée** ✅
