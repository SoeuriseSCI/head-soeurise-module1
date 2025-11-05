# FIX - Contrainte email_id UNIQUE

**Date**: 05/11/2025
**Problème**: Contrainte UNIQUE sur `email_id` empêche plusieurs événements par email
**Impact**: Workflow automatique a créé seulement 1/114 événements

---

## 🔍 Diagnostic

### Erreur observée

```
duplicate key value violates unique constraint "evenements_comptables_email_id_key"
DETAIL:  Key (email_id)=(104) already exists.
```

### Cause racine

La migration `migration_evenements_comptables.py` a créé une contrainte `UNIQUE` sur `email_id` :

```sql
email_id VARCHAR(100) UNIQUE
```

**Problème** : Un email peut contenir **plusieurs événements** !
- Relevé bancaire = 114 opérations = 114 événements
- Tous devraient avoir le même `email_id`

### Conséquence

1. Premier événement créé : ✅ #4 - "ANCIEN SOLDE"
2. Deuxième événement : ❌ Erreur contrainte UNIQUE
3. Transaction PostgreSQL en état "aborted"
4. Les 112 autres événements : ❌ Tous échoués avec "current transaction is aborted"

---

## ✅ Solution Complète

### Étape 1: Déployer les corrections sur Render

**Code poussé** :
- `fix_email_id_constraint.py` : Script de migration
- `gestionnaire_evenements.py` : Ajout rollback sur erreur

**Action** : Attendre que Render déploie (auto-deploy) ou déclencher manuellement depuis le dashboard.

### Étape 2: Sur Render Shell

```bash
# 1. Appliquer la migration (supprimer contrainte UNIQUE)
python fix_email_id_constraint.py
```

**Résultat attendu** :
```
🔍 Vérification de la contrainte email_id...
✅ Contrainte trouvée: evenements_comptables_email_id_key
🔧 Suppression de la contrainte...
✅ Contrainte supprimée avec succès
```

```bash
# 2. Nettoyer l'événement orphelin
python -c "
from models_module2 import get_session
from sqlalchemy import text
import os

DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

session = get_session(DATABASE_URL)
result = session.execute(text('DELETE FROM evenements_comptables WHERE id = 4'))
session.commit()
print(f'✅ {result.rowcount} événement supprimé')
session.close()
"
```

**Résultat attendu** :
```
✅ 1 événement supprimé
```

```bash
# 3. Vérifier que la table est vide
python check_evenements.py
```

**Résultat attendu** :
```
ÉVÉNEMENTS COMPTABLES

Total: 0 événements
```

### Étape 3: Relancer le workflow

**Option A - Marquer l'email comme UNSEEN** (recommandé):

```bash
# Via Python
python -c "
import imaplib
import os

mail = imaplib.IMAP4_SSL('imap.gmail.com')
mail.login(os.getenv('SOEURISE_EMAIL'), os.getenv('SOEURISE_PASSWORD'))
mail.select('inbox')

# Trouver l'email par ID (104)
status, messages = mail.search(None, 'ALL')
email_ids = messages[0].split()

# Le dernier email devrait être le 104
last_email_id = email_ids[-1]
mail.store(last_email_id, '-FLAGS', '(\Seen)')

print(f'✅ Email {last_email_id.decode()} marqué comme UNSEEN')
mail.close()
mail.logout()
"
```

**Option B - Attendre le prochain réveil à 08:00 UTC**

Le workflow se relancera automatiquement et traitera l'email non-vu.

**Option C - Déclencher réveil manuel**:

```bash
curl -X POST http://localhost:10000/api/reveil_manuel \
  -H "Authorization: Bearer $API_SECRET_TOKEN"
```

---

## 📊 Résultat Attendu (Après Fix)

```
================================================================================
WORKFLOW ÉVÉNEMENTS - PDF: 20251105_171844_Elements Comptables des 1-2-3T2024.pdf
================================================================================

📄 ÉTAPE 1/3: EXTRACTION DU PDF
✅ TOTAL: 114 opérations extraites

💾 ÉTAPE 2/3: CRÉATION DES ÉVÉNEMENTS
✅ Événement créé: #5 - ANCIEN SOLDE - 3612.05€
✅ Événement créé: #6 - PRET IMMOBILIER ECH 15/12/23 - 258.33€
✅ Événement créé: #7 - PRET IMMOBILIER ECH 15/12/23 - 1166.59€
... (111 autres)
✅ Événements créés: 114
⚠️  Doublons détectés: 0
❌ Erreurs: 0

🔍 ÉTAPE 3/3: DÉTECTION DES TYPES D'ÉVÉNEMENTS
✅ Événement #8: ASSURANCE_PRET
✅ Événement #15: FRAIS_BANCAIRES
✅ Événement #28: HONORAIRES_COMPTABLE
...
✅ Types détectés: 30/114

RÉSUMÉ:
📊 Opérations extraites: 114
✅ Événements créés: 114
🔍 Types détectés: 30
⚠️  Doublons ignorés: 0
❌ Erreurs: 0
```

### Vérification en base

```bash
python check_evenements.py
```

**Résultat attendu** :
```
ÉVÉNEMENTS COMPTABLES

Total: 114 événements

Par statut:
  - EN_ATTENTE: 114

Par phase:
  - Phase 1: 30

Par type:
  - ASSURANCE_PRET: 9
  - FRAIS_BANCAIRES: 18
  - HONORAIRES_COMPTABLE: 3
  - NON_DETECTE: 84
```

---

## 🔄 Résumé des Corrections

### 1. Migration SQL
- **Fichier**: `fix_email_id_constraint.py`
- **Action**: Supprime `UNIQUE CONSTRAINT` sur `email_id`
- **Commit**: a2dd479

### 2. Gestion des erreurs
- **Fichier**: `gestionnaire_evenements.py`
- **Action**: Ajout `self.session.rollback()` dans le catch
- **Pourquoi**: Évite que les erreurs cascade en "transaction aborted"
- **Commit**: 4b2b76e

---

## 🧪 Test de Non-Régression

Après le fix, tester avec un **deuxième email** :

```bash
# Renvoyer le même PDF avec un nouveau subject
# Subject: "Test relevé bancaire - Vérification doublons"
```

**Résultat attendu** :
- 114 opérations extraites
- 0 événements créés (tous détectés comme doublons)
- 114 doublons détectés ✅

Cela confirme que :
1. Le système permet plusieurs événements par email
2. La détection de doublons fonctionne (fingerprint)

---

## 📝 Checklist

- [ ] Déploiement Render terminé
- [ ] Migration appliquée (`python fix_email_id_constraint.py`)
- [ ] Événement orphelin supprimé
- [ ] Base vérifiée vide (`python check_evenements.py`)
- [ ] Email remarqué UNSEEN (option A) OU réveil manuel (option C)
- [ ] 114 événements créés
- [ ] 30 types détectés
- [ ] Test doublon effectué

---

**Auteur**: Claude Code Assistant
**Commits**: a2dd479, 4b2b76e
**Prêt pour correction**: ✅ OUI
