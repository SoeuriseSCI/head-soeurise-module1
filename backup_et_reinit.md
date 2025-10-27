# Guide Sauvegarde et Réinitialisation BD

## 📦 1. Faire un Backup

Sur le shell Render :

```bash
# Backup complet
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# Vérifier la taille
ls -lh backup_*.sql
```

## 🔄 2. Restaurer depuis un Backup

```bash
# Restaurer
psql $DATABASE_URL < backup_20251027_123456.sql
```

## 🆕 3. Réinitialisation Complète (État Propre)

### Option A : Script Python (Render)

```bash
# Télécharger le script depuis GitHub (après merge)
curl -O https://raw.githubusercontent.com/SoeuriseSCI/head-soeurise-module1/main/reinitialiser_bd.py

# Exécuter
python reinitialiser_bd.py
```

### Option B : Commandes Manuelles Simples

```bash
# 1. Supprimer tout
python -c "import psycopg2,os;c=psycopg2.connect(os.environ['DATABASE_URL']);r=c.cursor();[r.execute(f'DROP TABLE IF EXISTS {t} CASCADE') for t in ['propositions_en_attente','rapports_comptables','balances_mensuelles','evenements_comptables','calculs_amortissements','ecritures_comptables','immobilisations','plans_comptes','exercices_comptables']];c.commit();print('✅ Tables supprimées')"

# 2. Recréer le schéma
# TODO: Utiliser un script d'init

# 3. Insérer le bilan 2023
python test_bilan_2023.py
```

## ✅ 4. Vérifier l'État

```bash
# Vérifier le schéma
python verify_schema.py

# Compter les données
python -c "import psycopg2,os;c=psycopg2.connect(os.environ['DATABASE_URL']);r=c.cursor();r.execute('SELECT COUNT(*) FROM ecritures_comptables');print(f'Écritures: {r.fetchone()[0]}');c.close()"
```

## 🎯 Use Cases

### Test du Workflow Complet

1. Réinitialiser la BD (état propre)
2. Envoyer un email avec bilan 2023
3. Vérifier que _Head crée les propositions
4. Valider avec le token
5. Vérifier que les écritures sont créées

### Rollback après Tests

```bash
# Restaurer le backup
psql $DATABASE_URL < backup_avant_tests.sql
```

