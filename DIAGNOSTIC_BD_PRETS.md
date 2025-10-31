# Diagnostic et Réinitialisation BD - Prêts Immobiliers

**Date:** 31 octobre 2025
**Contexte:** Après ingestion avec extraction incomplète (4-16 échéances au lieu de 24)

---

## 🔍 Scripts Disponibles

### 1. Examiner les données (`examiner_bd_prets.py`)

**Usage:**
```bash
python3 examiner_bd_prets.py
```

**Affiche:**
- Liste de tous les prêts en BD
- Nombre d'échéances par prêt
- Première et dernière échéance (dates, montants, capital restant)
- Les 10 premières échéances (diagnostic)
- Les 5 dernières échéances

**Objectif:** Vérifier si les données sont correctes avant de décider de réinitialiser.

---

### 2. Réinitialiser les données (`reinitialiser_prets.py`)

**Usage (simulation):**
```bash
python3 reinitialiser_prets.py
```
→ Affiche ce qui serait supprimé SANS supprimer

**Usage (réel):**
```bash
python3 reinitialiser_prets.py --confirmer
```
→ Demande une confirmation explicite ("OUI") puis supprime TOUT

**⚠️ ATTENTION:** Supprime **TOUS les prêts** et **TOUTES les échéances**. Irréversible !

---

## 📊 Problème Détecté (31 oct 12:04)

### Logs d'ingestion

**Prêt B (5009736BRLZE11AQ):**
```
[PARSING] Échéances extraites (après dédup): 4, duree_mois: 216
[PARSING] Dernière échéance extraite: 2022-07-15
[PARSING] Génération depuis mois 5 jusqu'à 216
[PARSING] Échéances générées: 212
[PRETS_MGR] COMMIT RÉUSSI pour prêt 5009736BRLZE11AQ
```

**Prêt A (5009736BRM0911AH):**
```
[PARSING] Échéances extraites (après dédup): 16, duree_mois: 252
[PARSING] Dernière échéance extraite: 2023-07-15
[PARSING] Génération depuis mois 17 jusqu'à 252
[PARSING] Échéances générées: 236
[PRETS_MGR] COMMIT RÉUSSI pour prêt 5009736BRM0911AH
```

### Analyse

❌ **Extraction incomplète:**
- Prêt B: Seulement **4 échéances** extraites au lieu de 24
- Prêt A: Seulement **16 échéances** extraites au lieu de 24

❌ **Dates de dernière échéance incorrectes:**
- Prêt B: `2022-07-15` (devrait être `2024-04-15`)
- Prêt A: `2023-07-15` (devrait être `2024-04-15`)

✅ **Génération compense:**
- Les 216 et 252 échéances sont bien en BD
- MAIS les dates des premiers mois sont décalées

### Conséquences

Les **échéances générées** partent de mauvaises dates de référence:
- Au lieu de partir du **15/05/2024** (après 24 extraites)
- Elles partent de **2022-07-15** (Prêt B) ou **2023-07-15** (Prêt A)

→ **Décalage temporel** de 1 à 2 ans sur les dates d'échéances !

---

## ✅ Correction Appliquée (Pas Encore Déployée)

**Commit:** `2324350` sur branche `claude/fix-schedule-generation-date-011CUXYwLNG2gaeperhySx9e`

**Changements:**
1. Prompt plus explicite: "CRITIQUE: Tu DOIS extraire EXACTEMENT 24 échéances, pas moins !"
2. Structure attendue avec exemple ligne par ligne
3. Vérification: "Si tu n'as pas 24 échéances, CONTINUE À EXTRAIRE !"
4. Augmentation tokens: 4000 → 8000

**Résultat attendu après déploiement:**
```
[PARSING] Échéances extraites (après dédup): 24, duree_mois: 216
[PARSING] Dernière échéance extraite: 2024-04-15
[PARSING] Génération depuis mois 25 jusqu'à 216
[PARSING] Échéances générées: 192
```

---

## 🎯 Plan d'Action Recommandé

### Étape 1: Examiner les données actuelles
```bash
python3 examiner_bd_prets.py
```
→ Vérifier les dates des premières échéances (doivent commencer en 2023-05-15)

### Étape 2: Décider si réinitialisation nécessaire

**OUI, réinitialiser si:**
- Les dates sont décalées (commencent en 2022 pour Prêt B)
- Besoin de tester la nouvelle extraction

**NON, garder si:**
- Vous voulez conserver l'historique même avec dates incorrectes
- Pour comparaison avant/après

### Étape 3: Réinitialiser (si décidé)
```bash
# Simulation d'abord
python3 reinitialiser_prets.py

# Puis réel
python3 reinitialiser_prets.py --confirmer
# (taper "OUI" quand demandé)
```

### Étape 4: Merger et redéployer
```bash
# Merger la branche de correction vers main
git checkout main
git merge claude/fix-schedule-generation-date-011CUXYwLNG2gaeperhySx9e
git push origin main
```
→ Render redéploie automatiquement

### Étape 5: Tester la nouvelle ingestion
- Attendre fin du déploiement Render
- Déclencher `/admin/trigger-reveil`
- Vérifier logs: doit afficher "24 échéances extraites"

### Étape 6: Vérifier résultat
```bash
python3 examiner_bd_prets.py
```
→ Première échéance doit être `2023-05-15`, 25e échéance doit être `2024-05-15`

---

## 📈 Données Attendues (Après Correction)

### Prêt B - INVESTIMUR (5009736BRLZE11AQ)

**Extraction:**
- Lignes DBL → ignorées
- Première ECH (15/05/2023) → ignorée
- ECH 15/06/2023 → échéance #1
- ...
- 014 15/04/2024 → échéance #12 ou 13
- ...
- 025 15/03/2025 → échéance #24

**Génération:**
- 15/04/2025 → échéance #25
- ...
- 15/04/2040 → échéance #216

### Prêt A - SOLUTION P IMMO (5009736BRM0911AH)

**Extraction:** Idem (24 échéances)
**Génération:** Jusqu'à 15/04/2043 (échéance #252)

---

**Philosophie:** Persévérer / Espérer / Progresser ✨
