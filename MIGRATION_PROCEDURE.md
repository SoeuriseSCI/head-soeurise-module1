# Procédure de Migration Base de Données - Module 2

## 📋 Contexte

Suite à l'analyse du schéma PostgreSQL en production, plusieurs colonnes manquent dans les tables par rapport aux modèles Python définis dans `models_module2.py`. Cette migration ajoute toutes les colonnes manquantes et crée la nouvelle table `propositions_en_attente` pour le workflow de validation.

## 🎯 Objectifs

1. **Migration 002** : Ajouter 37 colonnes manquantes dans 6 tables existantes
2. **Migration 003** : Créer la table `propositions_en_attente` pour le workflow de validation

## 📊 Détails des Migrations

### Migration 002 - Synchronisation Schéma

**Tables modifiées :**

| Table | Colonnes ajoutées | Impact |
|-------|-------------------|--------|
| `ecritures_comptables` | 11 colonnes | Traçabilité email, validation, timestamps |
| `evenements_comptables` | 8 colonnes | email_subject, statut, traitement |
| `immobilisations` | 5 colonnes | description, traçabilité, actif |
| `calculs_amortissements` | 6 colonnes | détails calcul, traçabilité |
| `balances_mensuelles` | 5 colonnes | soldes détaillés, recalcul |
| `rapports_comptables` | 3 colonnes | JSON, métadonnées |

**Colonnes ajoutées dans ecritures_comptables** (les plus importantes) :
- `date_enregistrement` : Date d'enregistrement de l'écriture
- `source_email_id`, `source_email_date`, `source_email_from` : Traçabilité email
- `type_ecriture` : Classification (LOYER, CHARGE, AMORTISSEMENT, etc.)
- `piece_jointe`, `notes` : Documents et commentaires
- `valide`, `validee_par`, `validee_at` : Workflow de validation
- `updated_at` : Timestamp de dernière modification

### Migration 003 - Table Propositions

**Nouvelle table créée :** `propositions_en_attente`

Cette table permet de stocker les propositions d'écritures comptables en attente de validation et de valider via token uniquement (sans renvoyer le JSON complet).

**Structure :**
```sql
CREATE TABLE propositions_en_attente (
    id SERIAL PRIMARY KEY,
    token VARCHAR(50) UNIQUE NOT NULL,
    type_evenement VARCHAR(100) NOT NULL,
    email_id VARCHAR(255),
    email_from VARCHAR(255),
    email_date TIMESTAMP,
    email_subject VARCHAR(255),
    propositions_json JSONB NOT NULL,
    statut VARCHAR(50) DEFAULT 'EN_ATTENTE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    validee_at TIMESTAMP,
    validee_par VARCHAR(255),
    notes TEXT
);
```

**Index créés :**
- `idx_propositions_token` sur `token` (recherche rapide)
- `idx_propositions_statut` sur `statut` (filtrage)
- `idx_propositions_created` sur `created_at` (nettoyage automatique)

## 🚀 Application des Migrations sur Render

### ⚠️ ÉTAPE PRÉALABLE OBLIGATOIRE : Déployer le Code

**AVANT TOUTE CHOSE**, il faut déployer le code mergé sur Render :

1. **Ouvrir le Dashboard Render** : https://dashboard.render.com
2. **Sélectionner** le service "head-soeurise-web"
3. **Cliquer sur "Manual Deploy"** → "Deploy latest commit"
4. **Attendre** 2-3 minutes que le déploiement se termine (statut "Live")
5. **Vérifier** que les nouveaux fichiers sont présents :
   ```bash
   # Dans le Shell Render
   ls -la apply_migration.py propositions_manager.py
   ```

### Option A : Via Shell Render (Recommandé)

**Une fois le déploiement terminé** :

1. **Accéder au shell Render** :
   - Dashboard Render → Service "head-soeurise-web"
   - Cliquer sur "Shell" dans le menu de gauche

2. **Vérifier l'état actuel** :
   ```bash
   python apply_migration.py --dry
   ```

3. **Appliquer les migrations** :
   ```bash
   python apply_migration.py
   ```

4. **Vérifier le schéma** :
   ```bash
   python verify_schema.py
   ```

### Option B : Via Script Python Direct

Si `apply_migration.py` ne fonctionne pas, utiliser directement Alembic :

```bash
# Vérifier la version actuelle
alembic current

# Afficher l'historique
alembic history

# Appliquer toutes les migrations
alembic upgrade head

# Ou appliquer une migration spécifique
alembic upgrade 002  # Synchronisation schéma
alembic upgrade 003  # Table propositions
```

### Option C : SQL Direct (Dernière option)

Si Alembic ne fonctionne pas, exécuter directement le SQL :

```bash
python -c "
import psycopg2, os
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

# Lire et exécuter le SQL de migration 002
with open('alembic/versions/002_sync_schema.py') as f:
    # Extraire les commandes SQL et les exécuter
    pass

conn.commit()
cur.close()
conn.close()
"
```

## ✅ Vérification Post-Migration

### 1. Vérifier le nombre de colonnes

```bash
python -c "
import psycopg2, os
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

tables = ['ecritures_comptables', 'evenements_comptables', 'propositions_en_attente']
for table in tables:
    cur.execute(f'''
        SELECT COUNT(*) FROM information_schema.columns
        WHERE table_name = '{table}'
    ''')
    count = cur.fetchone()[0]
    print(f'{table}: {count} colonnes')

cur.close()
conn.close()
"
```

**Résultats attendus :**
- `ecritures_comptables` : 20 colonnes (était 9)
- `evenements_comptables` : 14 colonnes (était 6)
- `propositions_en_attente` : 13 colonnes (nouvelle table)

### 2. Vérifier les données existantes

Les données existantes (11 écritures du bilan 2023) ne sont PAS affectées. Les nouvelles colonnes auront des valeurs NULL par défaut.

```bash
python -c "
import psycopg2, os
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

cur.execute('SELECT COUNT(*) FROM ecritures_comptables WHERE exercice_id = 2')
count = cur.fetchone()[0]
print(f'Écritures bilan 2023 : {count} (doit être 11)')

cur.close()
conn.close()
"
```

## 🔄 Rollback (Si Nécessaire)

Si la migration cause des problèmes, il est possible de revenir en arrière :

```bash
# Revenir à la migration 001 (avant synchronisation)
alembic downgrade 001

# Ou revenir complètement en arrière
alembic downgrade base
```

**⚠️ ATTENTION** : Le rollback supprime les colonnes ajoutées. Si des données ont été insérées dans ces colonnes, elles seront perdues.

## 📝 Impact sur le Code

### Fichiers modifiés dans ce commit :

1. **requirements.txt** : Ajout de `alembic==1.13.1`
2. **models_module2.py** : Ajout de la classe `PropositionEnAttente`
3. **alembic/versions/002_sync_schema.py** : Migration synchronisation
4. **alembic/versions/003_propositions_table.py** : Migration table propositions
5. **apply_migration.py** : Script d'application des migrations
6. **verify_schema.py** : Script de vérification du schéma

### Prochaines étapes de développement :

1. **Adapter module2_workflow_v2.py** :
   - Générer un token unique lors de la création de propositions
   - Stocker les propositions dans `propositions_en_attente`
   - Inclure le token dans l'email envoyé à l'utilisateur

2. **Adapter module2_validations.py** :
   - Détecter le token dans l'email de validation `[_Head] VALIDE: TOKEN123`
   - Récupérer les propositions depuis `propositions_en_attente` via le token
   - Créer les écritures et marquer la proposition comme validée

3. **Ajouter nettoyage automatique** :
   - Script pour supprimer les propositions expirées (> 30 jours)

## 🔍 Troubleshooting

### Erreur : "relation already exists"

Si une table/colonne existe déjà, vérifier avec :

```sql
SELECT column_name FROM information_schema.columns
WHERE table_name = 'ecritures_comptables'
ORDER BY ordinal_position;
```

### Erreur : "cannot connect to database"

Vérifier que `DATABASE_URL` est défini :

```bash
echo $DATABASE_URL
```

### Migration bloquée

Si Alembic est bloqué, vérifier la table `alembic_version` :

```bash
python -c "
import psycopg2, os
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute('SELECT * FROM alembic_version')
print(cur.fetchone())
cur.close()
conn.close()
"
```

Pour forcer une version :

```bash
alembic stamp 002  # Marquer comme appliquée sans exécuter
```

## 📊 Statistiques de la Migration

- **Tables modifiées** : 6
- **Tables créées** : 1
- **Colonnes ajoutées** : 37
- **Index créés** : 3
- **Temps estimé** : < 5 secondes (aucune donnée à migrer)
- **Impact production** : Aucun (ajout de colonnes, pas de suppression)

---

**Date** : 27 octobre 2025
**Version** : 5.1 - Synchronisation schéma BD
**Auteur** : Claude Code Assistant
