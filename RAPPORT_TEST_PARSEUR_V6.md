# Rapport de Test - Parseur V6 (Function Calling)

**Date** : 01 novembre 2025
**Session** : claude/v6-architecture-impl-011CUhER84gzHmbSoYaE2bFG
**Objectif** : Tester le parseur V6 avec extraction complète via Function Calling

---

## 📊 Résultats Globaux

| Prêt | Échéances Extraites | Échéances Attendues | Précision | Statut |
|------|---------------------|---------------------|-----------|---------|
| **Prêt A (INVESTIMUR)** | 216 | 216 | **99.5%** | ✅ Excellent |
| **Prêt B (SOLUTION P IMMO)** | 251 | 252 | **5%** | ❌ Échec |

---

## ✅ Prêt A - INVESTIMUR (Prêt IN FINE)

### Résultat
- **216 échéances extraites** sur 216 attendues ✅
- **1 seule différence** sur 216 lignes (0.5%)
- **Temps d'extraction** : ~60 secondes

### Détail de la Différence
- **Ligne 13** (transition franchise → intérêts)
  - Référence : `2023-05-15:258.33:0.00:258.33:250000.00`
  - Extrait : `2023-05-15:0.00:0.00:258.33:250000.00`
  - **Problème** : `montant_total` = 0.00 au lieu de 258.33

### Analyse
- La différence se situe à la première échéance avec intérêts
- Tous les autres champs (capital, intérêts, capital restant dû) sont **corrects**
- Les 215 autres échéances sont **identiques au centime près**
- Résultat **largement acceptable** pour la production

---

## ❌ Prêt B - SOLUTION P IMMO (Prêt Amortissement Constant)

### Résultat
- **251 échéances extraites** sur 252 attendues ❌
- **239 différences** sur 251 lignes (95%)
- **Temps d'extraction** : ~80 secondes

### Problème Identifié
**Décalage généralisé à partir de la ligne 13**

#### Exemple ligne 13 :
- Référence : `2023-05-15:1166.59:0.00:1166.59:250000.00` (intérêts seuls)
- Extrait : `2023-05-15:1166.59:948.19:218.40:248650.50` (déjà en amortissement)

#### Exemple ligne 15 :
- Référence : `2023-07-15:1166.59:401.31:765.28:249598.69`
- Extrait : `2023-07-15:1166.59:949.85:216.74:246751.63`

### Analyse
1. **Il manque 1 échéance** (251 vs 252)
2. **Décalage dès la période d'amortissement** : Claude a probablement :
   - Sauté une échéance de transition
   - Ou mal interprété 2 lignes consécutives à intérêts seuls
3. **Toutes les échéances suivantes sont décalées d'une position**

### Cause Probable
Le PDF du Prêt B a une structure plus complexe :
- **2 échéances à intérêts seuls** (2023-05-15 et 2023-06-15)
- Puis **transition vers amortissement** (2023-07-15)
- Claude a probablement lu la première comme déjà en amortissement

---

## 🔧 Améliorations Apportées (depuis test initial)

### Prompt Amélioré
✅ Format visuel du tableau LCL avec exemples
✅ Instructions étape par étape claires
✅ Règles d'extraction strictes (DBL, première ECH)
✅ Vérifications (dates séquentielles, comptage)
✅ Obligation d'appeler `insert_pret_from_file`

### Paramètres Techniques
✅ `max_tokens` : 16000 → 20000 (compromis pour éviter timeout)
✅ `timeout` : 600s (10 minutes)
✅ Meilleure gestion des erreurs

### Résultat vs Premier Test
| Aspect | Premier Test | Test Amélioré |
|--------|-------------|---------------|
| **Prêt A - Nb échéances** | 217 (❌ +1) | 216 (✅) |
| **Prêt A - Dates** | Doublons + sauts | Séquentielles ✅ |
| **Prêt A - Valeurs** | Cumulatives ❌ | Par échéance ✅ |
| **Prêt A - Précision** | ~1% | **99.5%** |
| **Prêt B - Extraction** | max_tokens ❌ | Complète ✅ |
| **Prêt B - Précision** | N/A | 5% (décalage) |

---

## 🎯 Conclusions

### Points Positifs ✅
1. **Prêt A quasi-parfait** : 99.5% de précision est excellent
2. **Extraction complète fonctionnelle** : 216-251 échéances extraites
3. **Format correct** : Dates, montants, capital restant dû cohérents
4. **Function Calling opérationnel** : `extract_all_echeances_to_file` appelé avec succès
5. **Amélioration significative** depuis le premier test

### Points d'Attention ⚠️
1. **Prêt B à revoir** : Décalage non résolu
2. **Structures complexes** : Transitions franchise → intérêts → amortissement
3. **Lignes "ECH" ambiguës** : Différence entre intérêts seuls et amortissement

---

## 📋 Recommandations

### Option A - Utiliser V6 en Production pour Prêt A Uniquement
- ✅ Prêt IN FINE (type A) : Précision 99.5% acceptable
- ❌ Prêt Amortissement Constant (type B) : Nécessite correction

### Option B - Affiner le Prompt pour Prêt B
Ajouter des instructions spécifiques :
- Identifier précisément les 2 premières échéances à intérêts seuls
- Compter les échéances pendant l'extraction
- Vérifier que `capital_restant_du` diminue progressivement (sauf IN FINE)

### Option C - Approche Hybride
- V6 pour extraction initiale
- Validation automatique Python pour détecter les décalages
- Correction ou alerte si incohérence

### Option D - Conserver V5 en Production
- V5 (24 échéances + génération) : Fiable et testée
- V6 : Réservée aux tests et améliorations futures

---

## 📈 Métriques

### Coûts Estimés
- **Prêt A** : ~20000 tokens × 2 tours = 40k tokens input + output
- **Prêt B** : ~20000 tokens × 2 tours = 40k tokens input + output
- **Coût total session** : ~0.15€ (estimation)

### Performance
- **Temps total** : ~140 secondes (2min 20s) pour 2 prêts
- **Vitesse** : ~3.3 échéances/seconde

---

## 🔄 Prochaines Étapes Suggérées

1. **Analyser manuellement le PDF Prêt B** pour comprendre le format exact
2. **Ajuster le prompt** avec exemples spécifiques du Prêt B
3. **Implémenter validation Python** : vérifier décroissance capital_restant_du
4. **Re-tester Prêt B** avec prompt affiné
5. **Décider** : V6 en production ou rester sur V5

---

**Commit** : `3e4f415`
**Branche** : `claude/v6-architecture-impl-011CUhER84gzHmbSoYaE2bFG`
**Fichiers générés** :
- `PRET_5009736BRLZE11AQ_echeances.md` (216 lignes)
- `PRET_5009736BRM0911AH_echeances.md` (251 lignes)
