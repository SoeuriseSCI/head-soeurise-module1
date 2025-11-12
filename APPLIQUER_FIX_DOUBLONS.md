# Comment Appliquer le Fix Doublons SCPI/Apports

> **Guide rapide** pour déployer le fix après que vous ayez fait le déploiement sur Render

---

## 🎯 Objectif

Éliminer les 9 doublons (35 650€) entre relevés bancaires et avis d'opérations.

---

## 📦 Option 1 : Appliquer le Patch Git (Recommandé)

**Sur votre machine locale** (avant de déployer) :

```bash
cd /home/user/head-soeurise-module1

# Appliquer le patch (6 commits)
git am < fix_doublons_scpi.patch

# Pousser vers GitHub
git push origin main
```

**Puis déployer** sur Render comme d'habitude.

---

## 📦 Option 2 : Push Direct (Si Session Git OK)

```bash
cd /home/user/head-soeurise-module1
git push origin main
```

Puis déployer sur Render.

---

## 📦 Option 3 : Copie Manuelle sur Render

Si les options 1 et 2 ne fonctionnent pas, copiez les fichiers après déploiement :

**Sur le shell Render** :

```bash
cd ~/project/src

# Vérifier detection_doublons.py (devrait déjà être OK)
grep -c "calculer_fingerprint_simplifie" detection_doublons.py
# Si affiche 0 → Fichier à mettre à jour

# Vérifier extracteur_pdf.py
grep -c "ÉTAPE 2: Grouper par fingerprint SIMPLIFIÉ" extracteur_pdf.py
# Si affiche 0 → Fichier à mettre à jour
```

**Si mise à jour nécessaire**, utilisez les fichiers locaux :
- `/home/user/head-soeurise-module1/detection_doublons.py`
- `/home/user/head-soeurise-module1/extracteur_pdf.py`

---

## ✅ Vérification

Après déploiement, relancez le workflow :

```
GET https://head-soeurise-web.onrender.com/admin/trigger-reveil
```

**Logs attendus** :

```
🔍 Doublon SCPI/Apport: 2024-01-24 - 6346.56€
   Gardé: SCPI EPARGNE PIERRE DISTRIBUTION 1ER TRIM. 2024...
   Supprimé: VIR SEPA SCPI EPARGNE PIERRE...

✅ Déduplication: 130 → 121 opérations
   • Doublons exacts: 0
   • Doublons SCPI/Apports: 9

✅ 108 événements créés (pas 117)
✅ 88 propositions générées (pas 97)
```

---

## 📊 Résultat Attendu

### Avant Fix
- 117 événements
- 97 propositions
- 35 650€ d'erreur (doublons)

### Après Fix
- 108 événements (-9)
- 88 propositions (-9)
- 0€ d'erreur

---

## 📁 Fichiers Modifiés

1. **detection_doublons.py**
   - Ajout `calculer_fingerprint_simplifie()` (ligne 192-231)

2. **extracteur_pdf.py**
   - Modification `_deduplicater_operations()` (ligne 81-173)
   - Déduplication en 2 passes

3. **Documentation**
   - ANALYSE_DOUBLONS_SCPI_APPORTS.md
   - FIX_DOUBLONS_SCPI_APPORTS.md
   - SYNTHESE_FINALE_CORRECTIONS_DETECTEURS.md
   - VALIDATION_FINALE_CORRECTIONS_12NOV2025.md

---

## 🆘 En Cas de Problème

Si après déploiement les doublons persistent :

1. **Vérifier les fichiers** :
   ```bash
   grep "calculer_fingerprint_simplifie" detection_doublons.py
   grep "ÉTAPE 2" extracteur_pdf.py
   ```

2. **Consulter la documentation** :
   - `FIX_DOUBLONS_SCPI_APPORTS.md` - Guide complet
   - `ANALYSE_DOUBLONS_SCPI_APPORTS.md` - Analyse détaillée

3. **Appliquer manuellement** les modifications depuis les fichiers locaux

---

**Prêt pour déploiement** ✅
