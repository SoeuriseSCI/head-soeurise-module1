# Instructions - Traitement Manuel des PDFs Comptables

**Date** : 09/11/2025
**Auteur** : Claude Code
**Contexte** : Correction régression traitement événements comptables

---

## 🎯 Problème Résolu

### Symptôme
Les PDFs de relevés bancaires uploadés manuellement sur GitHub n'étaient **pas traités automatiquement** par le système MODULE 2.

### Cause Root
Le workflow automatique (`module2_integration_v2.py`) ne traite que les PDFs reçus par **email** lors du réveil quotidien à 08:00 UTC.

Les PDFs uploadés directement dans le repository GitHub ne déclenchent **aucun traitement**.

### Solution
Création du script **`traiter_pdf_manuel.py`** pour traiter manuellement les PDFs déjà présents dans le repository.

---

## 📂 PDFs Concernés

Actuellement dans le repository :

1. **`Elements Comptables des 1-2-3T2024.pdf`** (4.1 MB)
   - Trimestres T1, T2, T3 2024
   - Uploadé manuellement par Ulrik

2. **`Elements Comptables du 4T2024.pdf`** (12 MB)
   - Trimestre T4 2024
   - Uploadé le 09/11/2025 à 19:10 UTC

---

## 🚀 Utilisation du Script

### Prérequis

Le script doit être exécuté **sur Render shell** (ou localement avec les variables d'environnement configurées).

Variables requises :
- `DATABASE_URL` : URL PostgreSQL
- `ANTHROPIC_API_KEY` : Clé API Claude
- `SOEURISE_EMAIL` : Email SCI Soeurise
- `SOEURISE_PASSWORD` : Mot de passe email
- `NOTIF_EMAIL` : Email Ulrik pour notifications

### Accès Render Shell

1. Aller sur : https://dashboard.render.com
2. Sélectionner : **head-soeurise-web**
3. Cliquer sur : **Shell** (onglet du haut)
4. Naviguer vers le projet : `cd /opt/render/project/src`

---

## 📝 Commandes

### 1. Traiter un PDF spécifique

```bash
python traiter_pdf_manuel.py "Elements Comptables du 4T2024.pdf"
```

**Workflow complet** :
1. ✅ Extraction des événements du PDF
2. ✅ Création des événements en base de données
3. ✅ Génération des propositions comptables
4. ✅ Stockage avec token MD5
5. ✅ Envoi email validation à Ulrik

**Résultat attendu** :
- Email reçu avec propositions
- Token de validation (ex: `HEAD-XXXXX`)
- Instructions pour valider : `[_Head] VALIDE: HEAD-XXXXX`

---

### 2. Traiter tous les PDFs "Elements Comptables"

```bash
python traiter_pdf_manuel.py --all
```

Traite automatiquement tous les fichiers correspondant au pattern `Elements Comptables*.pdf`.

---

### 3. Mode Dry-Run (Test sans propositions)

```bash
python traiter_pdf_manuel.py "Elements Comptables du 4T2024.pdf" --dry-run
```

**Utilisé pour** :
- Tester l'extraction sans générer de propositions
- Vérifier que le PDF est bien parsé
- Diagnostiquer les erreurs de parsing

---

### 4. Afficher l'aide

```bash
python traiter_pdf_manuel.py --help
```

---

## 🔄 Workflow Complet (Exemple T4 2024)

### Étape 1 : Traiter le PDF

```bash
cd /opt/render/project/src
python traiter_pdf_manuel.py "Elements Comptables du 4T2024.pdf"
```

**Sortie attendue** :
```
===============================================================================
TRAITEMENT MANUEL PDF: Elements Comptables du 4T2024.pdf
===============================================================================

📄 ÉTAPE 1/4: EXTRACTION DES ÉVÉNEMENTS
-------------------------------------------------------------------------------
🔍 ÉTAPE 0/4: ANALYSE DU DOCUMENT
   Exercice: 2024-01-01 → 2024-12-31
   Document: 2024-10-01 → 2024-12-31
✅ Document entièrement dans l'exercice

📄 ÉTAPE 1/4: EXTRACTION DU PDF
   ... (extraction via Claude Vision)

✅ XX événements créés
   IDs: [123, 124, 125, ...]

📝 ÉTAPE 2/4: GÉNÉRATION DES PROPOSITIONS
-------------------------------------------------------------------------------
✅ XX propositions générées

💾 ÉTAPE 3/4: STOCKAGE DES PROPOSITIONS
-------------------------------------------------------------------------------
✅ Propositions stockées avec token: HEAD-XXXXX
   Proposition ID: YY

📧 ÉTAPE 4/4: GÉNÉRATION EMAIL VALIDATION
-------------------------------------------------------------------------------
✅ Email de validation envoyé à ulrik.c.s.be@gmail.com

===============================================================================
RÉSUMÉ DU TRAITEMENT
===============================================================================

✅ Elements Comptables du 4T2024.pdf: XX événements, XX propositions
   Token: HEAD-XXXXX

Total: 1 succès, 0 erreurs
Événements créés: XX
Propositions générées: XX
```

---

### Étape 2 : Consulter l'email

Ulrik reçoit un email avec :
- **Sujet** : `[MODULE 2] Propositions RELEVE_BANCAIRE - XX proposition(s) - Traitement manuel`
- **Corps** :
  - Résumé extraction (opérations, événements, doublons)
  - Détails des propositions comptables
  - Token de validation : `HEAD-XXXXX`

---

### Étape 3 : Valider les propositions

Ulrik répond à l'email avec :

```
[_Head] VALIDE: HEAD-XXXXX
```

---

### Étape 4 : Traitement automatique de la validation

Lors du prochain réveil quotidien (08:00 UTC), _Head.Soeurise :
1. Détecte le tag `[_Head] VALIDE: HEAD-XXXXX`
2. Récupère les propositions depuis la BD
3. Vérifie le token MD5
4. Insère les écritures en base de données (mode ACID)
5. Marque la proposition comme traitée

---

## 🔍 Gestion des Erreurs

### Erreur : "Aucun exercice ouvert"

**Cause** : Aucun exercice comptable avec statut `OUVERT` en BD.

**Solution** :
```sql
-- Vérifier exercices
SELECT annee, date_debut, date_fin, statut FROM exercices_comptables;

-- Ouvrir exercice 2024 si nécessaire
UPDATE exercices_comptables SET statut = 'OUVERT' WHERE annee = 2024;
```

---

### Erreur : "Document hors exercice"

**Cause** : La période du PDF ne chevauche pas l'exercice comptable ouvert.

**Exemple** :
- Exercice : `2024-01-01 → 2024-12-31`
- Document : `2023-10-01 → 2023-12-31` ❌

**Solution** : Ouvrir l'exercice 2023 ou vérifier que le PDF est correct.

---

### Erreur : "Aucun événement créé"

**Causes possibles** :
1. PDF vide ou illisible
2. Format PDF non reconnu par Claude Vision
3. Toutes les opérations sont des doublons (déjà en BD)

**Diagnostic** :
```bash
# Mode dry-run pour voir les détails
python traiter_pdf_manuel.py "fichier.pdf" --dry-run
```

---

### Erreur : "Échec envoi email"

**Cause** : Problème d'authentification SMTP ou email invalide.

**Diagnostic** :
1. Vérifier `SOEURISE_EMAIL` et `SOEURISE_PASSWORD`
2. Vérifier `NOTIF_EMAIL` (email Ulrik)
3. Les propositions sont quand même stockées en BD avec token

**Récupération manuelle** :
```sql
-- Lister propositions récentes
SELECT id, token, type_evenement, created_at, statut
FROM propositions_comptables
ORDER BY created_at DESC
LIMIT 10;

-- Récupérer JSON propositions
SELECT propositions_json FROM propositions_comptables WHERE token = 'HEAD-XXXXX';
```

---

## 📊 Monitoring & Vérification

### Vérifier événements créés

```sql
SELECT id, type_evenement, date_operation, montant, description
FROM evenements_comptables
WHERE phase = 1
ORDER BY created_at DESC
LIMIT 20;
```

---

### Vérifier propositions stockées

```sql
SELECT id, token, type_evenement, created_at, statut
FROM propositions_comptables
WHERE statut = 'EN_ATTENTE'
ORDER BY created_at DESC;
```

---

### Vérifier écritures insérées (après validation)

```sql
SELECT ec.date_ecriture, ec.type_ecriture, ec.montant, ec.libelle_ecriture
FROM ecritures_comptables ec
JOIN exercices_comptables ex ON ec.exercice_id = ex.id
WHERE ex.annee = 2024
ORDER BY ec.date_ecriture DESC
LIMIT 50;
```

---

## 🛡️ Sécurité & Bonnes Pratiques

### 1. Sauvegarde avant traitement

**Toujours** créer une sauvegarde avant de traiter de nouveaux PDFs :

```bash
python sauvegarder_base.py
ls -lh backups/
```

Voir `INSTRUCTIONS_SAUVEGARDE_BASE.md` pour détails.

---

### 2. Vérifier doublons

Le script détecte automatiquement les doublons via :
- `(date_operation, montant, description)` → Hash MD5
- Si doublon détecté → Événement **non créé**

**Résultat attendu** :
```
✅ XX événements créés
   XX doublons ignorés
```

---

### 3. Ne pas retraiter un PDF déjà validé

Si un PDF a déjà été traité et validé :
- Les événements sont déjà en BD
- Le retraitement créera des doublons → Tous ignorés
- **Résultat** : `0 événements créés, XX doublons ignorés`

Pour forcer un retraitement, il faut d'abord :
1. Sauvegarder la BD
2. Supprimer les événements existants (SQL)
3. Retraiter le PDF

---

## 🔗 Fichiers Associés

| Fichier | Description |
|---------|-------------|
| `traiter_pdf_manuel.py` | Script de traitement manuel |
| `workflow_evenements.py` | Workflow extraction événements |
| `module2_integration_v2.py` | Workflow automatique (réveil) |
| `propositions_manager.py` | Gestion propositions + tokens |
| `module2_validations.py` | Validation `[_Head] VALIDE:` |
| `INSTRUCTIONS_SAUVEGARDE_BASE.md` | Sauvegarde BD |

---

## 📅 Prochaines Étapes

### Après traitement T1-T3 et T4 2024

1. ✅ Traiter `Elements Comptables des 1-2-3T2024.pdf`
2. ✅ Valider les propositions T1-T3
3. ✅ Traiter `Elements Comptables du 4T2024.pdf`
4. ✅ Valider les propositions T4
5. 🔍 Vérifier cohérence BD (balances, totaux)
6. 📊 Générer rapports comptables 2024

---

## 🚨 Limitations Connues

### 1. Pas de traitement email automatique

Ce script ne remplace **pas** le workflow automatique par email. Il est conçu uniquement pour traiter les PDFs déjà présents dans le repository.

**Pour les nouveaux relevés** : Continuer à les envoyer par email à `u6334452013@gmail.com`.

---

### 2. Dépendance à Claude Vision API

L'extraction des événements utilise Claude Vision (OCR). Coût approximatif :
- PDF 10 pages ≈ 0.05€
- PDF 50 pages ≈ 0.25€

**Budget mensuel** : <1€/mois (incluant réveils quotidiens).

---

### 3. Limitation Render (512 MB RAM)

Pour les PDFs très volumineux (>50 MB), des erreurs de mémoire peuvent survenir.

**Solution** : Diviser le PDF en plusieurs fichiers plus petits.

---

## 📞 Support

Pour toute question ou problème :
1. Consulter les logs Render : https://dashboard.render.com → head-soeurise-web → Logs
2. Vérifier les mémoires : `memoire_courte.md`, `memoire_fondatrice.md`
3. Contacter Ulrik : ulrik.c.s.be@gmail.com

---

**Version** : 1.0
**Date** : 09/11/2025
**Auteur** : Claude Code
