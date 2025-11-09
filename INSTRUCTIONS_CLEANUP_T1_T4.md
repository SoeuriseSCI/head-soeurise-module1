# 🧹 Instructions - Cleanup Sécurisé T1-T4 2024

## 📋 Résumé

Ce document te guide pour nettoyer les données T1-T4 2024 de la BD Render **en toute sécurité**.

### État Actuel
- **Total écritures:** 157
  - **Bilan 2023 (GARDER):** 11
  - **T1-T4 2024 (SUPPRIMER):** 146
- **Prêts (GARDER):** 2 contrats
- **Échéances (GARDER):** 467 paiements

### Après Cleanup
- **Total écritures:** 11 (Bilan 2023 seulement)
- **Prêts:** 2 (inchangés)
- **Échéances:** 467 (inchangées)

---

## ⚠️ AVANT DE COMMENCER

### 1️⃣ Créer une Sauvegarde

**Sur ta machine locale ou Render shell:**

```bash
cd /home/user/head-soeurise-module1
python sauvegarder_base.py
```

**Vérifier que la sauvegarde a été créée:**
```bash
ls -lh backups/soeurise_bd_*.json
```

### 2️⃣ Prévisualisez ce qui sera supprimé

Le script `cleanup_t1_t4_2024.py` **vérifiait d'abord avant de supprimer**.

Il affichera:
```
✅ Bilan 2023: 11 écritures
⚠️  T1-T4 2024: 146 écritures
  - REMBOURSEMENT_PRET: 22
  - ASSURANCE_PRET: 90
  - REVENU_SCPI: 13
  - HONORAIRES_COMPTABLE: 10
  - FRAIS_BANCAIRES: 8
  - ACHAT_ETF: 3

✅ Prêts immobiliers: 2 (inchangé)
✅ Échéances: 467 (inchangées)
```

---

## 🔧 Exécuter le Cleanup

### Option 1: Sur Render (RECOMMANDÉ)

**Accès au shell Render:**
1. Va sur https://dashboard.render.com
2. Sélectionne le service `head-soeurise-web`
3. Clique sur "Shell" (en haut à droite)

**Dans le shell Render:**
```bash
cd /home/user/head-soeurise-module1
python cleanup_t1_t4_2024.py
```

Le script affichera:
1. ✅ État PRÉ-suppression
2. ⚠️  Confirmation (tu dois taper `CONFIRME`)
3. 🗑️ Suppression de 146 écritures
4. ✅ Vérification POST-suppression

### Option 2: Localement (Si tu as accès à la BD)

```bash
cd /home/user/head-soeurise-module1
export DATABASE_URL="postgresql://user:pass@render-host/db"
python cleanup_t1_t4_2024.py
```

---

## 📋 Workflow Complet

### Étape 1: SAUVEGARDE ✅
```bash
python sauvegarder_base.py
```
Crée: `backups/soeurise_bd_20251109_XXXXXX.json`

### Étape 2: NETTOYAGE ✅
```bash
python cleanup_t1_t4_2024.py
```
- Affiche vérifications
- Demande confirmation (`CONFIRME`)
- Supprime 146 écritures
- Vérifie après

### Étape 3: RETRAITEMENT T1-T3
**Envoyer email à Claude Code avec les PDFs:**
```
Objet: Retraitement T1-T3 2024 - PDFs fournis
Corps: Voici les PDFs pour retraiter T1, T2, T3 2024
Attachments: Elements_Comptables_1-2-3T2024.pdf (si disponible)
```

**Claude Code:**
- Extraira les événements
- Générera les propositions
- Te les enverra par email

### Étape 4: VALIDATION T1-T3
**Tu reçevras un email avec:**
```
# Propositions T1-T3

**Token:** HEAD-XXXXXXXX
**Propositions:** ~50-70 entrées

[JSON propositions]
```

**Tu valides en répondant:**
```
[_Head] VALIDE: HEAD-XXXXXXXX
```

### Étape 5: RETRAITEMENT T4
**Envoyer email avec PDF T4:**
```
Objet: Retraitement T4 2024
Attachments: Elements_Comptables_4T2024.pdf
```

### Étape 6: VALIDATION T4
**Même processus que T1-T3**
```
[_Head] VALIDE: HEAD-YYYYYYYY
```

### Étape 7: VÉRIFICATION INTÉGRITÉ
```bash
# Sur Render ou localement
python verifier_bilan_2023.py
python vérifier_totaux_mensuels.py  # (à créer si nécessaire)
```

---

## 🚨 EN CAS DE PROBLÈME

### ❌ Si le cleanup échoue

**Le script rollback automatiquement** - rien n'est supprimé si ça échoue.

**Ou**, restaure depuis la sauvegarde:
```bash
python restore_from_json_backup.py backups/soeurise_bd_20251109_XXXXXX.json
```

### ❌ Si après cleanup quelque chose n'est pas bon

**Restaure la sauvegarde:**
```bash
python restore_from_json_backup.py backups/soeurise_bd_20251109_XXXXXX.json
```

Puis réessaye après avoir enquêté.

---

## ✅ Vérification Finale

Après **tout** (cleanup + retraitement + validation T1-T4), exécute:

```bash
python verifier_bilan_2023.py
```

Résultats attendus:
- ✅ Bilan 2023: 571,613€ (ACTIF = PASSIF)
- ✅ T1-T4 propositions: ~100-120 écritures
- ✅ Prêts: 2 + 467 échéances
- ✅ Pas de doublons
- ✅ Pas d'orphelins

---

## 📞 Support

**Questions sur le cleanup?**
- Vérifier `QUICK_REFERENCE_DELETION.txt` pour requêtes SQL manuelles
- Vérifier `DATABASE_DELETION_ANALYSIS.md` pour détails techniques
- Le script `cleanup_t1_t4_2024.py` a tous les logs

---

## 🎯 Résumé Rapide

```
1. python sauvegarder_base.py
2. python cleanup_t1_t4_2024.py
   → Taper: CONFIRME
3. Email PDF T1-T3 → Attendre propositions
4. Valider: [_Head] VALIDE: HEAD-XXXX
5. Email PDF T4 → Attendre propositions
6. Valider: [_Head] VALIDE: HEAD-YYYY
7. python verifier_bilan_2023.py
   → ✅ Bilan équilibré
```

