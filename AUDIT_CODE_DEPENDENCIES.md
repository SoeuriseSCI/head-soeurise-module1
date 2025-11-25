# 🔍 Audit Dépendances Code - 24/11/2025

## 🚨 PROBLÈME CRITIQUE : Imports Obsolètes

**7 fichiers référencés mais MANQUANTS** :

1. ❌ `cutoff_extourne_interets.py` (importé par `detecteurs_evenements.py`)
2. ❌ `detection_doublons.py` (importé par `gestionnaire_evenements.py`)
3. ❌ `extracteur_intelligent.py` (importé par `workflow_evenements.py`)
4. ❌ `module2_integration.py` (importé par `main.py` ligne 122)
5. ❌ `parseur_bilan_v6.py` (importé par `module2_workflow_v2.py`)
6. ❌ `parseur_pret_v7.py` (importé par `module2_workflow_v2.py`)
7. ❌ `precloture_exercice.py` (importé par `module2_workflow_v2.py`)
8. ❌ `rapprocheur_cutoff.py` (importé par `detecteurs_evenements.py`)

**Impact** :
- Ces imports échouent silencieusement (try/except)
- Fonctionnalités potentiellement cassées sans erreur visible
- Code mort qui pollue la base

---

## ✅ Graphe de Dépendances RÉELLES

```
main.py
├── models_module2.py ✅
├── module2_integration.py ❌ MANQUANT
└── module2_integration_v2.py ✅
    ├── models_module2.py
    ├── module2_validations.py ✅
    │   ├── models_module2.py
    │   ├── module2_workflow_v2.py
    │   ├── prets_manager.py ✅
    │   │   └── models_module2.py
    │   └── propositions_manager.py ✅
    │       └── models_module2.py
    ├── module2_workflow_v2.py ✅
    │   ├── cloture_exercice.py ✅
    │   │   └── models_module2.py
    │   ├── detecteurs_evenements.py ✅
    │   │   ├── cutoff_extourne_interets.py ❌ MANQUANT
    │   │   └── rapprocheur_cutoff.py ❌ MANQUANT
    │   ├── models_module2.py
    │   ├── parseur_bilan_v6.py ❌ MANQUANT
    │   ├── parseur_pret_v7.py ❌ MANQUANT
    │   └── precloture_exercice.py ❌ MANQUANT
    ├── prets_manager.py
    ├── propositions_manager.py
    └── workflow_evenements.py ✅
        ├── detecteurs_evenements.py
        ├── extracteur_intelligent.py ❌ MANQUANT
        ├── gestionnaire_evenements.py ✅
        │   └── detection_doublons.py ❌ MANQUANT
        └── models_module2.py
```

---

## 📊 Fichiers du Projet (30 fichiers)

### ✅ Utilisés par main.py (19 fichiers)

**Actifs et fonctionnels** :
- ✅ `cloture_exercice.py`
- ✅ `detecteurs_evenements.py`
- ✅ `gestionnaire_evenements.py`
- ✅ `main.py`
- ✅ `models_module2.py`
- ✅ `module2_integration_v2.py`
- ✅ `module2_validations.py`
- ✅ `module2_workflow_v2.py`
- ✅ `prets_manager.py`
- ✅ `propositions_manager.py`
- ✅ `workflow_evenements.py`

**Référencés mais MANQUANTS** :
- ❌ `cutoff_extourne_interets.py`
- ❌ `detection_doublons.py`
- ❌ `extracteur_intelligent.py`
- ❌ `module2_integration.py`
- ❌ `parseur_bilan_v6.py`
- ❌ `parseur_pret_v7.py`
- ❌ `precloture_exercice.py`
- ❌ `rapprocheur_cutoff.py`

### 🔧 Scripts Autonomes (11 fichiers)

**Utilisation manuelle/CLI** :
- 📊 `analyser_exercice_2024.py`
- 🔍 `check_exercices_detailed.py`
- 🔍 `check_exercices_from_backup.py`
- 🔍 `check_exercices_status.py`
- 📝 `completer_plan_comptes.py`
- 📊 `construire_etats_financiers_2024.py`
- 📊 `construire_etats_financiers_2025.py`
- 📄 `export_cerfa.py`
- 📄 `generer_cerfa_pdf.py`
- 💾 `sauvegarder_base.py`
- ✅ `verifier_integrite_complete.py`

**Statut** : Scripts légitimes pour maintenance manuelle

---

## 🧹 Actions Recommandées

### 1️⃣ PRIORITÉ HAUTE : Nettoyer imports obsolètes

**Dans `main.py` (ligne 122)** :
```python
# AVANT (obsolète)
from module2_integration import integrer_module2_dans_reveil, init_module2

# APRÈS (supprimer car module2_integration.py n'existe plus)
# Import supprimé - module2_integration.py obsolète
```

**Dans `module2_workflow_v2.py`** :
```python
# SUPPRIMER imports manquants :
# from parseur_bilan_v6 import ...
# from parseur_pret_v7 import ...
# from precloture_exercice import ...
```

**Dans `detecteurs_evenements.py`** :
```python
# SUPPRIMER :
# from cutoff_extourne_interets import ...
# from rapprocheur_cutoff import ...
```

**Dans `workflow_evenements.py`** :
```python
# SUPPRIMER :
# from extracteur_intelligent import ...
```

**Dans `gestionnaire_evenements.py`** :
```python
# SUPPRIMER :
# from detection_doublons import ...
```

### 2️⃣ PRIORITÉ MOYENNE : Archiver scripts obsolètes

Créer dossier `scripts_maintenance/` et y déplacer :
- `analyser_exercice_2024.py` (spécifique 2024)
- `check_exercices_*.py` (3 fichiers similaires, garder le meilleur)
- `construire_etats_financiers_2024.py` (obsolète, gardé pour référence)

### 3️⃣ PRIORITÉ BASSE : Documenter scripts autonomes

Ajouter header à chaque script autonome :
```python
"""
SCRIPT AUTONOME - Usage manuel uniquement

Description : ...
Usage : python script.py [args]
"""
```

---

## 🎯 Résultat Attendu

**AVANT** :
- 30 fichiers .py
- 8 imports cassés
- Code mort non détecté

**APRÈS** :
- ~20 fichiers .py actifs
- 0 imports cassés
- Scripts autonomes documentés et archivés
- Base de code propre et maintenable

---

**Date** : 24/11/2025
**Auteur** : Claude Code Assistant
**Version** : Audit V1.0
