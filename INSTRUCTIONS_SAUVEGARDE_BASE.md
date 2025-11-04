# Instructions : Sauvegarde Base de Données

## 🎯 Objectif

Créer une sauvegarde complète de la base de données PostgreSQL **avant d'intégrer de nouveaux événements comptables**. Cette sauvegarde servira de point de restauration en cas de problème.

---

## 📋 Étape par Étape

### 1. Accéder au Shell Render

1. Allez sur https://dashboard.render.com
2. Sélectionnez le service **head-soeurise-web**
3. Cliquez sur l'onglet **Shell** (dans le menu de gauche)
4. Un terminal s'ouvrira dans le conteneur

### 2. Vérifier les Fichiers de Sauvegarde

Dans le shell Render, vérifiez que les scripts sont présents :

```bash
ls -l sauvegarder_base.*
```

**Attendu** :
```
-rwxr-xr-x sauvegarder_base.sh
-rw-r--r-- sauvegarder_base.py
```

### 3. Exécuter la Sauvegarde (Python)

Le script Python est recommandé car il ne nécessite pas `pg_dump` :

```bash
python sauvegarder_base.py
```

**Note** : Le `DATABASE_URL` est déjà défini dans l'environnement Render.

#### Sortie Attendue

```
================================================================================
💾 SAUVEGARDE BASE DE DONNÉES (FORMAT JSON)
================================================================================

📁 Répertoire de sauvegarde : ./backups
📄 Fichier de sauvegarde    : backups/soeurise_bd_20251104_HHMMSS.json

📊 Sauvegarde exercices comptables...
   ✅ 1 exercices sauvegardés
📊 Sauvegarde plan comptable...
   ✅ XX comptes sauvegardés
📊 Sauvegarde écritures comptables...
   ✅ 11 écritures sauvegardées
📊 Sauvegarde prêts immobiliers...
   ✅ 2 prêts sauvegardés
📊 Sauvegarde échéances...
   ✅ 468 échéances sauvegardées

💾 Écriture du fichier JSON...
   ✅ Fichier écrit : XX.XX KB

================================================================================
✅ SAUVEGARDE TERMINÉE
================================================================================

📊 Résumé :
   - 1 exercices
   - XX comptes
   - 11 écritures
   - 2 prêts
   - 468 échéances

💾 Fichier : backups/soeurise_bd_20251104_HHMMSS.json
```

### 4. Vérifier la Sauvegarde

Vérifiez que le fichier a été créé :

```bash
ls -lh backups/
```

Vous devriez voir un fichier JSON avec le timestamp actuel.

### 5. Télécharger la Sauvegarde (Optionnel)

Pour récupérer la sauvegarde en local :

```bash
cat backups/soeurise_bd_*.json
```

Copiez le contenu et sauvegardez-le localement sur votre machine.

---

## 🔧 Alternative : Sauvegarde SQL (si pg_dump disponible)

Si `pg_dump` est installé dans l'environnement Render :

```bash
bash sauvegarder_base.sh
```

**Avantage** : Dump SQL complet, restauration plus rapide
**Inconvénient** : Nécessite `pg_dump` installé

---

## 📊 Contenu de la Sauvegarde

### Format JSON (sauvegarder_base.py)

Le fichier JSON contient 5 sections :

```json
{
  "metadata": {
    "timestamp": "20251104_HHMMSS",
    "date": "2025-11-04T...",
    "database": "soeurise_sci",
    "version": "V6.0"
  },
  "exercices": [...],        // ExerciceComptable (1 exercice)
  "plan_comptable": [...],   // PlanCompte (tous les comptes)
  "ecritures": [...],        // EcritureComptable (11 écritures bilan 2023)
  "prets": [...],            // PretImmobilier (2 prêts)
  "echeances": [...]         // EcheancePret (468 échéances)
}
```

### Données Sauvegardées (État Actuel)

**Exercices** : 1
- Exercice 2023 (OUVERT)

**Écritures comptables** : 11
- Bilan 2023 : 571 613€ (ACTIF = PASSIF ✅)

**Prêts immobiliers** : 2
- Prêt A (LCL) : 250 000€ @ 1,050%, 252 échéances
- Prêt B (INVESTIMUR) : 250 000€ @ 1,240%, 216 échéances

**Échéances** : 468
- Total capital : 500 000€
- Total intérêts : ~85 829€

**Total** : **479 enregistrements production**

---

## 🔄 Restauration (Procédure Future)

### Depuis JSON (Python)

Créer un script `restaurer_base.py` qui :
1. Lit le fichier JSON
2. Supprime les données actuelles (ATTENTION!)
3. Réinsère les données sauvegardées

### Depuis SQL (pg_dump)

```bash
psql $DATABASE_URL < backups/soeurise_bd_TIMESTAMP.sql
```

**⚠️ ATTENTION** : La restauration écrase toutes les données actuelles !

---

## 🚨 Dépannage

### Erreur : "Module 'models_module2' not found"

```bash
pip install sqlalchemy psycopg2-binary
```

### Erreur : "DATABASE_URL non définie"

Sur Render, elle devrait être définie automatiquement. Vérifier dans les **Environment Variables** du service.

### Erreur : "Permission denied: backups/"

Le répertoire `backups/` sera créé automatiquement par le script.

### Le fichier JSON est vide ou incomplet

Vérifier les logs pour voir quelle table a échoué. Possible problème de connexion à PostgreSQL.

---

## 📤 Archivage de la Sauvegarde

### Sur Render (Éphémère)

⚠️ Les fichiers dans `backups/` sur Render sont **temporaires** et seront perdus au prochain redémarrage du conteneur.

**Solution** : Télécharger la sauvegarde localement ou sur GitHub.

### Sur GitHub (Recommandé)

Pour sauvegarder définitivement :

```bash
# Télécharger le fichier JSON
cat backups/soeurise_bd_*.json > backup_local.json

# Puis sur votre machine locale :
git add backups/
git commit -m "💾 Sauvegarde BD avant intégration événements comptables"
git push
```

**Note** : Attention à ne pas commiter de données sensibles si le repo est public.

### Sur Drive/Cloud (Alternative)

Télécharger le fichier JSON et le sauvegarder sur Google Drive, Dropbox, etc.

---

## ✅ Checklist de Validation

Avant de continuer avec l'intégration d'événements comptables :

- [ ] Sauvegarde créée avec succès
- [ ] Fichier JSON présent dans `backups/`
- [ ] Taille du fichier cohérente (> 10 KB)
- [ ] 11 écritures sauvegardées
- [ ] 2 prêts sauvegardés
- [ ] 468 échéances sauvegardées
- [ ] Sauvegarde archivée localement ou sur GitHub

---

## 📅 Fréquence de Sauvegarde Recommandée

- **Avant toute modification majeure** (intégration événements, corrections)
- **Après validation d'une étape importante** (bilan validé, prêts insérés)
- **Quotidiennement** (via cron/scheduler) → À implémenter

---

**Date** : 04/11/2025
**Priorité** : 🔴 CRITIQUE
**Contexte** : Sauvegarde avant intégration événements comptables
**Statut** : 479 enregistrements en production - Base validée correcte
