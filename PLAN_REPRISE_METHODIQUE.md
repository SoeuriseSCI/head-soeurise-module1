# Plan de Reprise Méthodique - Correction Régression

**Date** : 09/11/2025
**Objectif** : Reprendre le traitement comptable 2024 étape par étape avec validation

---

## 🎯 Problème Identifié

**Commit `5592bb5` du 06/11/2025** a introduit une extraction ciblée qui ignore les sections autres que "releves_bancaires".

### Impact Mesuré

Pour `Elements Comptables des 1-2-3T2024.pdf` (41 pages) :
- **Pages 1-20** (relevés bancaires) : ✅ Extraites (~90 opérations)
- **Pages 21-38** (avis opérations VM - ETF/Actions) : ❌ Ignorées (~50 opérations)
- **Pages 39-41** (factures diverses) : ❌ Ignorées (~10 opérations)

**Résultat** : ~60 événements manquants sur 150 attendus (**40% de perte**)

---

## ✅ Corrections Appliquées

### 1. Bug Extraction PDF Corrigé

**Fichier** : `extracteur_pdf.py` (lignes 551-580)

**Avant** : Extraction uniquement `releves_bancaires`
**Après** : Extraction de TOUTES les sections détectées :
- `releves_bancaires` (colonnes Date|Libellé|Débit|Crédit)
- `avis_operations_vm` (achats ETF, actions)
- `factures` (comptable, LEI, etc.)

**Résultat attendu** : ~150 opérations au lieu de ~90

---

### 2. Script Réinitialisation BD

**Fichier** : `reinitialiser_pour_reprise.py`

**Fonctionnalités** :
- ✅ Sauvegarde JSON automatique avant nettoyage
- ✅ Supprime TOUT sauf Bilan 2023 (11 écritures validées)
- ✅ Vérifications avant/après avec rapport détaillé
- ✅ Confirmation utilisateur obligatoire

**Tables nettoyées** :
- `prets_immobiliers`
- `echeances_prets`
- `evenements_comptables`
- `propositions_comptables`
- `ecritures_comptables` (sauf `INIT_BILAN_2023`)
- `balances_mensuelles`

---

## 📋 Plan de Reprise (5 Étapes)

### Étape 1 : Réinitialisation BD ✅ PRÊT

**Sur Render Shell** :
```bash
cd /opt/render/project/src
python reinitialiser_pour_reprise.py
# Taper 'OUI' pour confirmer
```

**Vérifications automatiques** :
- ✓ Sauvegarde créée dans `backups/`
- ✓ Bilan 2023 préservé (11 écritures)
- ✓ Toutes autres données supprimées

**État final attendu** :
```
Base de données:
  ✓ Exercices: 2 (2023 + 2024)
  ✓ Écritures: 11 (Bilan 2023 uniquement)
  ✓ Prêts: 0
  ✓ Échéances: 0
  ✓ Événements: 0
  ✓ Propositions: 0
```

---

### Étape 2 : Tableaux Amortissement 🔄 EN ATTENTE

**Fichiers à traiter** (présents dans repository) :
- `TABLEAUD'AMORTISSEMENTPRETIMMOBILIER_20230417.pdf` (Prêt A - LCL)
- `TABLEAUD'AMORTISSEMENTPRETIMMOBILIER_20230417-1.pdf` (Prêt B - INVESTIMUR)

**Méthode** : Email à `u6334452013@gmail.com`
```
Objet: Tableaux amortissement prêts immobiliers
Corps: [Joindre les 2 PDFs]
```

**Résultats attendus** :
- Prêt A (LCL - BRM0911AH) : 252 échéances
- Prêt B (INVESTIMUR - BRLZE11AQ) : 216 échéances
- **Total : 468 échéances**

**Vérification** :
```sql
-- Sur Render Shell ou via outil BD
SELECT COUNT(*) FROM prets_immobiliers;  -- Attendu: 2
SELECT COUNT(*) FROM echeances_prets;    -- Attendu: 468
```

---

### Étape 3 : Événements T1-T3 2024 🔄 EN ATTENTE

**Fichier à traiter** : `Elements Comptables des 1-2-3T2024.pdf` (4.1 MB, 41 pages)

**Méthode** : Email à `u6334452013@gmail.com`
```
Objet: Événements comptables T1-T3 2024
Corps: [Joindre le PDF]
```

**Avec la correction appliquée, résultats attendus** :
- **~150 opérations extraites** (au lieu de ~90)
  - Pages 1-20 : Relevés bancaires (~90 ops)
  - Pages 21-38 : Avis opérations VM (~50 ops)
  - Pages 39-41 : Factures (~10 ops)

**Propositions attendues** :
- Remboursements prêts : ~18 événements (9 mois × 2 prêts)
- Assurances emprunteur : ~18 événements (9 mois × 2 cotisations)
- Frais bancaires : ~27 événements (9 mois × 3 frais)
- Honoraires comptable : ~4 factures
- Revenus SCPI : ~3 distributions trimestrielles
- Achats ETF/Actions : ~30-40 opérations (août 2024)
- Apports compte courant : ~4 virements
- Impôts/taxes : ~2 prélèvements
- **TOTAL ESTIMÉ : ~110-130 événements**

**Vérification** :
```sql
SELECT COUNT(*) FROM evenements_comptables
WHERE date_operation >= '2024-01-01' AND date_operation < '2024-10-01';
-- Attendu: ~110-130
```

---

### Étape 4 : Validation Propositions T1-T3 🔄 EN ATTENTE

**Après réception email avec propositions** :

Répondre avec :
```
[_Head] VALIDE: HEAD-XXXXX
```

**Lors du prochain réveil (08:00 UTC)** :
- Détection validation
- Vérification intégrité (MD5)
- Insertion écritures en BD (mode ACID)

**Vérification** :
```sql
SELECT COUNT(*) FROM ecritures_comptables
WHERE exercice_id = (SELECT id FROM exercices_comptables WHERE annee = 2024);
-- Attendu: ~110-130 écritures
```

---

### Étape 5 : Événements T4 2024 🔄 EN ATTENTE

**Fichier à traiter** : `Elements Comptables du 4T2024.pdf` (12 MB)

**Méthode** : Email à `u6334452013@gmail.com`
```
Objet: Événements comptables T4 2024
Corps: [Joindre le PDF]
```

**Résultats attendus** :
- ~30-40 opérations (3 mois : oct, nov, déc 2024)
- Mêmes types d'événements que T1-T3

**Validation** : Répondre avec `[_Head] VALIDE: HEAD-YYYYY`

---

## 🔍 Points de Vérification à Chaque Étape

### Extraction PDF

**Logs à examiner** (Render → Logs) :
```
✅ Extraction globale: pages 1-41 (toutes sections)
📋 Section 'releves_bancaires': pages 1-20
📋 Section 'avis_operations_vm': pages 21-38
📋 Section 'factures': pages 39-41
✅ XXX opérations extraites du PDF
✅ YYY événements après filtrage
```

**Si sections manquantes** :
```
⚠️  Aucune section détectée - extraction complète du PDF
```
→ Pas grave, tout le PDF sera extrait

---

### Détection Doublons

**Logs normaux** :
```
⏭️  Doublon détecté (fingerprint): événement #42 ignoré
```

**Si trop de doublons (>50%)** :
→ Probable retraitement d'un PDF déjà traité
→ Vérifier que la BD a bien été nettoyée

---

### Génération Propositions

**Email reçu avec** :
- Token : `HEAD-XXXXX` (8 caractères après HEAD-)
- Nombre de propositions
- Détail de chaque proposition

**Vérifier dans BD** :
```sql
SELECT token, type_evenement, statut, created_at
FROM propositions_comptables
WHERE statut = 'EN_ATTENTE'
ORDER BY created_at DESC
LIMIT 5;
```

---

## 🚨 Gestion des Erreurs

### Erreur "Aucun exercice ouvert"

**Cause** : Exercice 2024 fermé ou inexistant

**Solution** :
```sql
UPDATE exercices_comptables
SET statut = 'OUVERT'
WHERE annee = 2024;
```

---

### Erreur "Document hors exercice"

**Cause** : Période PDF ne chevauche pas l'exercice

**Vérification** :
```sql
SELECT date_debut, date_fin, statut
FROM exercices_comptables
WHERE annee = 2024;
```

**Solution** : Ajuster dates exercice si nécessaire

---

### Troncature Extraction (<30 opérations pour 41 pages)

**Cause** : Limite tokens Claude ou PDF trop volumineux

**Diagnostic logs** :
```
🔍 DEBUG Chunk X: stop_reason=max_tokens
⚠️  TRONCATURE DÉTECTÉE
```

**Solution** : Division en chunks plus petits (déjà implémenté à 5 pages)

---

## 📊 État Attendu Final

Après traitement complet T1-T4 2024 :

```
Base de données:
  ✓ Exercices: 2 (2023 + 2024)
  ✓ Écritures: ~150-170
    - Bilan 2023: 11
    - Événements 2024: ~140-160
  ✓ Prêts: 2
  ✓ Échéances: 468
  ✓ Événements: ~150-170
  ✓ Propositions: 0 (toutes validées et insérées)
```

---

## 🔧 Commandes Utiles

### Render Shell

```bash
# Accéder au shell
cd /opt/render/project/src

# Sauvegarder BD
python sauvegarder_base.py

# Réinitialiser BD
python reinitialiser_pour_reprise.py

# Vérifier Bilan 2023
python verifier_bilan_2023.py

# Lister sauvegardes
ls -lh backups/
```

---

### SQL (via Render Shell)

```bash
# Connexion PostgreSQL
python -c "import os; print(os.environ['DATABASE_URL'])"

# Ou utiliser psql directement si disponible
```

---

## 📞 Support

En cas de problème :
1. Consulter les logs Render : https://dashboard.render.com → head-soeurise-web → Logs
2. Vérifier les mémoires : `memoire_courte.md`, `memoire_fondatrice.md`
3. Examiner ce document : `PLAN_REPRISE_METHODIQUE.md`

---

**Prêt pour déploiement** : ✅ Oui (après merge + déploiement manuel Ulrik)

**Prochaine action** : Merger la PR et déclencher déploiement manuel Render
