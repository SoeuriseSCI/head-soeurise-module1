# Configuration Auto-Merge pour branches Claude Code

Ce fichier explique comment configurer l'auto-merge automatique des branches `claude/*` vers `main`.

## 🎯 Objectif

Permettre à Claude Code de pousser des changements qui seront **automatiquement mergés vers `main`** sans intervention manuelle.

## ⚙️ Configuration GitHub requise

### 1. Activer GitHub Actions

GitHub Actions doit avoir les permissions nécessaires :

1. Aller dans **Settings** → **Actions** → **General**
2. Sous **Workflow permissions**, sélectionner :
   - ✅ **Read and write permissions**
   - ✅ **Allow GitHub Actions to create and approve pull requests**
3. Cliquer **Save**

### 2. Option A : Sans branch protection (le plus simple)

Aucune configuration supplémentaire nécessaire. L'action mergera directement.

### 2. Option B : Avec branch protection

Si vous avez activé la protection de branche sur `main` :

1. Aller dans **Settings** → **Branches**
2. Cliquer sur **Edit** pour la règle de protection de `main`
3. Activer :
   - ✅ **Allow auto-merge**
   - ✅ Sous "Restrict who can push to matching branches", ajouter `github-actions[bot]`
4. **Save changes**

## 🔄 Comment ça fonctionne

### Déclenchement

Quand Claude Code pousse vers une branche `claude/*` :

```bash
git push origin claude/ma-session-xyz
```

### Processus automatique

1. **GitHub Action détectée** (`.github/workflows/auto-merge-claude-branches.yml`)
2. **PR créée automatiquement** : `main` ← `claude/ma-session-xyz`
3. **Merge automatique** : La PR est mergée immédiatement
4. **Branche supprimée** : La branche `claude/*` est nettoyée

### Résultat

Les changements sont sur `main` sans intervention manuelle ! ✅

## 🧪 Tester la configuration

### Test 1 : Créer une branche de test

```bash
git checkout -b claude/test-auto-merge-123
echo "Test auto-merge" > test.txt
git add test.txt
git commit -m "Test auto-merge"
git push origin claude/test-auto-merge-123
```

### Test 2 : Vérifier

1. Aller dans l'onglet **Actions** sur GitHub
2. Vérifier que le workflow s'exécute
3. Vérifier qu'une PR est créée et mergée automatiquement
4. Vérifier que `test.txt` est bien sur `main`

## 🚨 Sécurité

**Pourquoi c'est sécurisé ?**

- ✅ Ne fonctionne **que** pour les branches `claude/**`
- ✅ Historique complet dans les PR (traçabilité)
- ✅ Possibilité de désactiver si besoin
- ✅ Compatible avec les réveils automatiques de _Head.Soeurise (qui pousse directement vers `main`)

## 📝 Workflows existants

### Auto-merge Claude branches

**Fichier** : `.github/workflows/auto-merge-claude-branches.yml`

**Déclencheur** : Push sur `claude/**`

**Actions** :
1. Checkout du code
2. Vérification si PR existe déjà
3. Création PR si nécessaire
4. Merge automatique + suppression branche

## 🔧 Dépannage

### L'action ne se déclenche pas

Vérifier que GitHub Actions est activé dans Settings → Actions.

### L'action échoue au merge

Vérifier les permissions dans Settings → Actions → General.

### Les PRs ne se créent pas

Vérifier que "Allow GitHub Actions to create and approve pull requests" est coché.

---

**Version** : 1.0 - 26 octobre 2025
**Dernière mise à jour** : Configuration initiale auto-merge
