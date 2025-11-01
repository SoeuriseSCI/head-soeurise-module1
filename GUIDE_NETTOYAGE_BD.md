# Guide de Nettoyage de la Base de Données

**Date** : 01 novembre 2025
**Objectif** : Nettoyer les données de test pour retester le parseur V6 avec une base propre

---

## 🎯 Quand Utiliser ?

Utilisez ce script quand vous voulez :
- **Retester le parseur V6** avec les PDFs de référence
- **Nettoyer les données d'échéances** incorrectes
- **Repartir à zéro** pour tester l'insertion en BD

---

## 📝 Script : `nettoyer_donnees_test.py`

### Ce qu'il SUPPRIME ❌

- Tous les **prêts immobiliers**
- Toutes les **échéances de prêts**
- Toutes les **écritures comptables** (SAUF bilan d'ouverture)
- Toutes les **opérations bancaires**
- Tous les **événements comptables**
- Toutes les **propositions en attente**

### Ce qu'il PRÉSERVE ✅

- Le **schéma de la base de données**
- L'**exercice comptable 2023**
- Le **plan comptable** (12 comptes)
- Les **écritures du bilan d'ouverture 2023** (`type_ecriture = 'INIT_BILAN_2023'`)

---

## 🚀 Utilisation

### Mode Interactif (avec confirmation)

```bash
python nettoyer_donnees_test.py
```

Le script vous demandera de taper `OUI` pour confirmer.

### Mode Automatique (sans confirmation)

```bash
python nettoyer_donnees_test.py --yes
```

ou

```bash
python nettoyer_donnees_test.py -y
```

⚠️ **Attention** : Le mode `--yes` exécute immédiatement sans demander confirmation !

### Aide

```bash
python nettoyer_donnees_test.py --help
```

---

## 📊 Exemple de Sortie

```
================================================================================
🧹 NETTOYAGE DONNÉES DE TEST
================================================================================

Ce script va SUPPRIMER :
  ❌ Tous les prêts immobiliers
  ❌ Toutes les échéances de prêts
  ❌ Toutes les écritures comptables (SAUF bilan d'ouverture)
  ❌ Toutes les opérations bancaires
  ❌ Tous les événements comptables
  ❌ Toutes les propositions en attente

Ce script va PRÉSERVER :
  ✅ Le schéma de la base de données
  ✅ L'exercice comptable 2023
  ✅ Le plan comptable
  ✅ Les écritures du bilan d'ouverture (type_ecriture = 'INIT_BILAN_2023')

⚠️  Idéal pour retester le parseur V6 avec une base propre !

✅ Mode --yes activé : confirmation automatique

🧹 Début du nettoyage...
--------------------------------------------------------------------------------

📊 ÉTAPE 1/6 : Suppression des échéances de prêts
  ✓ 467 échéances supprimées

🏠 ÉTAPE 2/6 : Suppression des prêts immobiliers
  ✓ 2 prêts supprimés

💰 ÉTAPE 3/6 : Suppression des écritures comptables
  ✓ 156 écritures supprimées
  ✅ 11 écritures du bilan d'ouverture préservées

🏦 ÉTAPE 4/6 : Suppression des opérations bancaires
  ✓ 0 opérations supprimées

📧 ÉTAPE 5/6 : Suppression des événements comptables
  ✓ 0 événements supprimés

📝 ÉTAPE 6/6 : Suppression des propositions en attente
  ✓ 0 propositions supprimées

================================================================================
✅ VÉRIFICATION FINALE
================================================================================

État de la base après nettoyage :

✅ PRÉSERVÉ :
  - 1 exercice(s) comptable(s)
  - 12 comptes dans le plan comptable
  - 11 écritures (bilan d'ouverture uniquement)

🧹 NETTOYÉ :
  - 0 prêt(s) immobilier(s)
  - 0 échéance(s) de prêt

================================================================================
🎉 NETTOYAGE TERMINÉ AVEC SUCCÈS !
================================================================================

🚀 Vous pouvez maintenant retester le parseur V6 :

  1. Exécuter : python test_parseur_v6.py
  2. Vérifier l'insertion en BD
  3. Consulter les résultats avec : python examiner_bd_prets.py
```

---

## 🔄 Workflow Complet de Test

### 1. Nettoyer la base

```bash
python nettoyer_donnees_test.py --yes
```

### 2. Retester le parseur V6

```bash
export ANTHROPIC_API_KEY="votre-clé-api"
python test_parseur_v6.py
```

### 3. Vérifier l'insertion en BD

```bash
python examiner_bd_prets.py
```

Ou via SQL direct :

```sql
-- Compter les prêts
SELECT COUNT(*) FROM prets_immobiliers;

-- Compter les échéances
SELECT COUNT(*) FROM echeances_prets;

-- Voir les prêts insérés
SELECT numero_pret, banque, montant_initial, duree_mois
FROM prets_immobiliers;

-- Vérifier les échéances d'un prêt
SELECT COUNT(*), MIN(date_echeance), MAX(date_echeance)
FROM echeances_prets
WHERE pret_id = 1;
```

---

## ⚠️ Précautions

1. **Sauvegardez avant** si vous avez des données importantes
2. **Ne lancez PAS en production** (uniquement en développement/test)
3. **Vérifiez DATABASE_URL** avant d'exécuter
4. Le script **nécessite psycopg2** : `pip install psycopg2-binary`

---

## 🔍 Dépannage

### Erreur : `DATABASE_URL non défini`

```bash
export DATABASE_URL="postgresql://user:pass@host:port/dbname"
```

### Erreur : `ModuleNotFoundError: No module named 'psycopg2'`

```bash
pip install psycopg2-binary
```

### Erreur : `permission denied`

```bash
chmod +x nettoyer_donnees_test.py
```

---

## 📚 Voir Aussi

- `reinitialiser_bd.py` : Réinitialisation COMPLÈTE (supprime tout, y compris le bilan d'ouverture)
- `test_parseur_v6.py` : Tests automatisés du parseur V6
- `RAPPORT_TEST_PARSEUR_V6.md` : Rapport détaillé des tests

---

**Commit** : [À compléter]
**Branche** : `claude/v6-architecture-impl-011CUhER84gzHmbSoYaE2bFG`
