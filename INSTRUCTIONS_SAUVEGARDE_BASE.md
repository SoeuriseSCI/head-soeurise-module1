# Instructions : Sauvegarde Base de Données

## 🎯 Objectif

Créer une sauvegarde complète de la base de données PostgreSQL **avant d'intégrer de nouveaux événements comptables**. Cette sauvegarde servira de point de restauration en cas de problème.

---

## 📋 Étape par Étape

### 1. Configurer GITHUB_TOKEN sur Render (Une seule fois)

**Obligatoire pour l'upload automatique vers GitHub** :

1. Allez sur https://dashboard.render.com
2. Sélectionnez le service **head-soeurise-web**
3. Cliquez sur **Environment** (menu de gauche)
4. Ajoutez une nouvelle variable :
   - **Key** : `GITHUB_TOKEN`
   - **Value** : Votre token GitHub (avec permissions `repo`)
5. Cliquez sur **Save Changes**
6. Attendez le redéploiement (~2 min)

**Comment créer un token GitHub** :
- GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
- Generate new token → Cochez `repo` → Generate token
- Copiez le token (il ne sera affiché qu'une fois !)

### 2. Accéder au Shell Render

1. Allez sur https://dashboard.render.com
2. Sélectionnez le service **head-soeurise-web**
3. Cliquez sur l'onglet **Shell** (dans le menu de gauche)
4. Un terminal s'ouvrira dans le conteneur

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
   ✅ 2 exercices sauvegardés
📊 Sauvegarde plan comptable...
   ✅ 12 comptes sauvegardés
📊 Sauvegarde écritures comptables...
   ✅ 11 écritures sauvegardées
📊 Sauvegarde prêts immobiliers...
   ✅ 2 prêts sauvegardés
📊 Sauvegarde échéances...
   ✅ 467 échéances sauvegardées

💾 Écriture du fichier JSON...
   ✅ Fichier écrit : 155.77 KB

================================================================================
✅ SAUVEGARDE LOCALE TERMINÉE
================================================================================

📊 Résumé :
   - 2 exercices
   - 12 comptes
   - 11 écritures
   - 2 prêts
   - 467 échéances

💾 Fichier local : backups/soeurise_bd_20251104_HHMMSS.json

================================================================================
📤 UPLOAD VERS GITHUB
================================================================================

📍 Repository : SoeuriseSCI/head-soeurise-module1
📍 Branche    : main
📍 Chemin     : backups/soeurise_bd_20251104_HHMMSS.json

📖 Lecture du fichier pour upload...
   ✅ XXXXX caractères encodés

🔍 Vérification si le fichier existe déjà sur GitHub...
   ℹ️  Fichier n'existe pas - Création

📤 Upload vers GitHub...
   ✅ Upload réussi !

================================================================================
✅ SAUVEGARDE UPLOADÉE SUR GITHUB
================================================================================

📊 Détails :
   Commit  : a1b2c3d
   URL     : https://github.com/SoeuriseSCI/head-soeurise-module1/blob/main/backups/soeurise_bd_20251104_HHMMSS.json
   Message : 💾 Sauvegarde BD automatique - 04/11/2025 16:05
```

### 4. Télécharger la Sauvegarde depuis GitHub

Le fichier a été automatiquement uploadé sur GitHub. Pour le récupérer :

**Option 1 : Via le navigateur**
1. Allez sur : https://github.com/SoeuriseSCI/head-soeurise-module1/tree/main/backups
2. Cliquez sur le fichier `soeurise_bd_YYYYMMDD_HHMMSS.json`
3. Cliquez sur **Download** (bouton en haut à droite)

**Option 2 : Via Git en local**
```bash
git pull origin main
# Le fichier sera dans backups/
```

**Option 3 : Via wget/curl**
```bash
wget https://raw.githubusercontent.com/SoeuriseSCI/head-soeurise-module1/main/backups/soeurise_bd_YYYYMMDD_HHMMSS.json
```

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

### ✅ Sur GitHub (Automatique)

Le script `sauvegarder_base.py` upload **automatiquement** le fichier vers GitHub (branche `main`).

**Avantages** :
- ✅ Permanent (pas perdu au redémarrage Render)
- ✅ Versionné (historique des sauvegardes)
- ✅ Accessible de partout
- ✅ Pas de manipulation manuelle

**URL** : https://github.com/SoeuriseSCI/head-soeurise-module1/tree/main/backups

### ⚠️ Sur Render (Éphémère)

Les fichiers dans `backups/` sur Render sont **temporaires** et seront perdus au prochain redémarrage du conteneur. Ils ne servent que pour l'upload vers GitHub.

### 💾 Sur Disque Dur Local (Optionnel)

Téléchargez depuis GitHub (voir section précédente) et sauvegardez sur votre disque dur ou Drive/Cloud.

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
