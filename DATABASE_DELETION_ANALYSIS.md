# ANALYSE COMPLÈTE: Suppression Sécurisée des Données Comptables

## 1. STRUCTURE DES TABLES

### 1.1 Tables Principales

#### `ecritures_comptables` (157 entrées actuellement)
```
ID: Integer (PK)
exercice_id: Integer (FK → exercices_comptables.id) [NULLABLE: NO]
numero_ecriture: VARCHAR(50)
date_ecriture: DATE [IMPORTANT: Identifier par cette date]
date_enregistrement: TIMESTAMP
source_email_id: VARCHAR(255)
type_ecriture: VARCHAR(50) [KEY COLUMN: INIT_BILAN_2023, REMBOURSEMENT_PRET, etc.]
compte_debit: VARCHAR(10) (FK → plans_comptes.numero_compte)
compte_credit: VARCHAR(10) (FK → plans_comptes.numero_compte)
montant: NUMERIC(12, 2)
piece_jointe: VARCHAR(255)
notes: TEXT
valide: BOOLEAN
validee_par: VARCHAR(255)
validee_at: TIMESTAMP
created_at: TIMESTAMP
updated_at: TIMESTAMP
```

#### `evenements_comptables` (0 actuellement, mais peut être utilisée)
```
ID: Integer (PK)
email_id: VARCHAR(255) [UNIQUE]
email_from: VARCHAR(255)
email_date: DATETIME
email_subject: VARCHAR(255)
email_body: TEXT
type_evenement: VARCHAR(100) [ex: INIT_BILAN_2023, REMBOURSEMENT_PRET]
est_comptable: BOOLEAN
statut: VARCHAR(50) [EN_ATTENTE, VALIDE, REJETE, ERREUR]
message_erreur: TEXT
ecritures_creees: INTEGER[] [Array of ecriture IDs created from this event]
created_at: TIMESTAMP
traite_at: TIMESTAMP
updated_at: TIMESTAMP
```

#### `propositions_en_attente` (0 actuellement)
```
ID: Integer (PK)
token: VARCHAR(50) [UNIQUE]
type_evenement: VARCHAR(100)
email_id: VARCHAR(255)
email_from: VARCHAR(255)
email_date: TIMESTAMP
email_subject: VARCHAR(255)
propositions_json: JSONB [The actual proposal data]
statut: VARCHAR(50) [EN_ATTENTE, VALIDEE, REJETEE, EXPIREE]
created_at: TIMESTAMP
validee_at: TIMESTAMP
validee_par: VARCHAR(255)
notes: TEXT
```

#### `echeances_prets` (467 entrées - DO NOT TOUCH)
```
ID: Integer (PK)
pret_id: Integer (FK → prets_immobiliers.id) [ON DELETE CASCADE]
numero_echeance: INTEGER
date_echeance: DATE
montant_total: NUMERIC(15, 2)
montant_interet: NUMERIC(15, 2)
montant_capital: NUMERIC(15, 2)
capital_restant_du: NUMERIC(15, 2)
montant_assurance: NUMERIC(15, 2)
comptabilise: BOOLEAN
ecriture_comptable_id: Integer (FK → ecritures_comptables.id) [NULLABLE]
date_comptabilisation: TIMESTAMP
created_at: TIMESTAMP
updated_at: TIMESTAMP

CONSTRAINT: uq_pret_date_echeance UNIQUE (pret_id, date_echeance)
```

#### `prets_immobiliers` (2 entrées - DO NOT TOUCH)
```
ID: Integer (PK)
numero_pret: VARCHAR(50) [UNIQUE]
banque: VARCHAR(100)
libelle: VARCHAR(255)
montant_initial: NUMERIC(15, 2)
taux_annuel: NUMERIC(6, 4)
duree_mois: INTEGER
date_debut: DATE
date_fin: DATE
type_amortissement: VARCHAR(50)
mois_franchise: INTEGER
echeance_mensuelle: NUMERIC(15, 2)
interet_mensuel_franchise: NUMERIC(15, 2)
assurance_emprunteur: BOOLEAN
assures: VARCHAR(255)
source_email_id: VARCHAR(255)
source_document: VARCHAR(500)
date_ingestion: TIMESTAMP
actif: BOOLEAN
notes: TEXT
created_at: TIMESTAMP
updated_at: TIMESTAMP

CASCADE: echeances (ON DELETE CASCADE via FK)
```

### 1.2 Tables Liées (mais pas affectées)
- `mouvements_portefeuille`: source_evenement_id → evenements_comptables.id
- `mouvements_comptes_courants`: source_evenement_id → evenements_comptables.id
- `calculs_amortissements`: ecriture_id → ecritures_comptables.id
- `balances_mensuelles`: Cached summary data (should be recalculated)
- `rapports_comptables`: Generated reports (should be regenerated)

---

## 2. CRITÈRES D'IDENTIFICATION SÉCURISÉE

### 2.1 Bilan 2023 (À CONSERVER)

**Identification:**
```sql
WHERE type_ecriture = 'INIT_BILAN_2023' AND exercice_id = 2
```

**Caractéristiques actuelles:**
- Total: 11 écritures
- Exercice ID: 2 (année 2023)
- Type: INIT_BILAN_2023
- Date: Généralement '2023-01-01' (mais peut être autre)
- Comptes: Tous les comptes de bilan (89, 101, 120, 211, 213, 280, etc.)

**Vérification:**
```python
# Count
SELECT COUNT(*) FROM ecritures_comptables 
WHERE type_ecriture = 'INIT_BILAN_2023' 
AND exercice_id = 2;
# Expected: 11 (ne pas supprimer si ce nombre change sans raison)

# Somme des montants (doit être équilibrée)
SELECT 
  SUM(CASE WHEN compte_debit LIKE '2%' THEN montant ELSE 0 END) as actif_debit,
  SUM(CASE WHEN compte_credit LIKE '1%' THEN montant ELSE 0 END) as passif_credit
FROM ecritures_comptables 
WHERE type_ecriture = 'INIT_BILAN_2023' 
AND exercice_id = 2;
# Expected: actif_debit ≈ passif_credit (vérification bilan)
```

### 2.2 T1-T4 2024 (À SUPPRIMER)

**Identification:**
```sql
WHERE exercice_id = 1 AND type_ecriture != 'INIT_BILAN_2023'
```

**Caractéristiques actuelles:**
- Total: 146 écritures
- Exercice ID: 1 (année 2024)
- Types: REMBOURSEMENT_PRET (22), ASSURANCE_PRET (90), REVENU_SCPI (13), HONORAIRES_COMPTABLE (10), FRAIS_BANCAIRES (8), ACHAT_ETF (3)
- Date: 2024-XX-XX (réellement encodés comme '2025-11-XX' mais marqués comme 2024)

**Sous-catégories:**

#### Prêts (112 écritures)
```sql
WHERE exercice_id = 1 
AND type_ecriture IN ('REMBOURSEMENT_PRET', 'ASSURANCE_PRET')
```
- REMBOURSEMENT_PRET: 22
- ASSURANCE_PRET: 90

#### Non-Prêt (34 écritures)
```sql
WHERE exercice_id = 1 
AND type_ecriture NOT IN ('REMBOURSEMENT_PRET', 'ASSURANCE_PRET')
```
- REVENU_SCPI: 13
- HONORAIRES_COMPTABLE: 10
- FRAIS_BANCAIRES: 8
- ACHAT_ETF: 3

### 2.3 Clôture 2023 (Si existe, À SUPPRIMER)

**Identification:**
```sql
WHERE type_ecriture = 'CLOTURE' AND exercice_id = 2 AND date_ecriture = '2023-12-31'
```

**Caractéristiques:**
- Marque la fin de l'exercice 2023
- Date: 2023-12-31
- Type: CLOTURE
- Peut être regénérée si nécessaire

---

## 3. FOREIGN KEY CONSTRAINTS & CASCADE RULES

### 3.1 Constraint Map (Ordre de suppression IMPORTANT)

```
propositions_en_attente (NO FK OUTGOING)
  ↓
mouvements_comptes_courants (FK: source_evenement_id → evenements_comptables)
mouvements_portefeuille (FK: source_evenement_id → evenements_comptables)
  ↓
ecritures_comptables (Multiple incoming FKs, SAFE to delete)
  ↓
evenements_comptables (Multiple incoming FKs via ecritures_creees ARRAY)
  ↓
echeances_prets (FK: ecriture_comptable_id → ecritures_comptables, nullable)
calculs_amortissements (FK: ecriture_id → ecritures_comptables)
```

### 3.2 Critical Constraints

**NO CASCADE from ecritures_comptables:**
```
prets_immobiliers.echeances ← (ON DELETE CASCADE)
```
Mais echeances_prets.ecriture_comptable_id est NULLABLE, donc safe.

**Reverse constraint:**
```
echeances_prets.ecriture_comptable_id → ecritures_comptables.id
# This FK is NULLABLE, so deleting ecritures won't cascade to echeances
```

**evenements_comptables linkage:**
```
ecritures_comptables.source_email_id → evenements_comptables.email_id
# NOT a formal FK, but logical link (safe to delete)
```

---

## 4. DELETION STRATEGY (SAFE ORDER)

### PHASE 1: Backup (MANDATORY)
```bash
# Before ANY deletion, create backup
python sauvegarder_base.py  # JSON format
bash sauvegarder_base.sh    # SQL dump format
```

### PHASE 2: Cascade Delete Order

**Step 1: Empty Propositions (optional)**
```sql
-- 0 rows currently, but clean for good measure
DELETE FROM propositions_en_attente 
WHERE statut IN ('REJETEE', 'EXPIREE') 
OR created_at < CURRENT_DATE - INTERVAL '30 days';
```

**Step 2: Delete Movement Records**
```sql
-- Clean mouvements linked to events (reverse FK)
DELETE FROM mouvements_comptes_courants 
WHERE source_evenement_id IN (
  SELECT id FROM evenements_comptables
);

DELETE FROM mouvements_portefeuille 
WHERE source_evenement_id IN (
  SELECT id FROM evenements_comptables
);
```

**Step 3: Delete Target Ecritures**

**3a: Delete T1-T4 2024 Ecritures**
```sql
DELETE FROM ecritures_comptables 
WHERE exercice_id = 1 
AND type_ecriture != 'INIT_BILAN_2023';

-- This will cascade to:
-- - echeances_prets.ecriture_comptable_id (NULLABLE, no constraint)
-- - calculs_amortissements.ecriture_id (NULLABLE, no constraint)
```

**3b: Verify no impact on Prêts**
```sql
-- BEFORE deletion, verify:
SELECT COUNT(*) as orpaned_echeances
FROM echeances_prets 
WHERE ecriture_comptable_id IN (
  SELECT id FROM ecritures_comptables 
  WHERE exercice_id = 1 
  AND type_ecriture != 'INIT_BILAN_2023'
);
# Expected: 0 (ou notes après suppression)

-- AFTER deletion, verify:
SELECT COUNT(*) as total_echeances
FROM echeances_prets;
# Expected: 467 (unchanged)

SELECT COUNT(*) as linked_echeances
FROM echeances_prets 
WHERE ecriture_comptable_id IS NOT NULL;
# Expected: 0 (si deletion effectuée)
```

**Step 4: Clean Events (Optional)**
```sql
DELETE FROM evenements_comptables 
WHERE statut != 'VALIDE' 
OR type_evenement != 'INIT_BILAN_2023';

-- Or delete all if logs not needed:
DELETE FROM evenements_comptables;
```

**Step 5: Recalculate Caches**
```sql
-- balances_mensuelles will be stale, either:
-- a) Delete and recalculate (recommandé):
DELETE FROM balances_mensuelles 
WHERE exercice_id = 1;

-- b) Or leave for automatic recalculation

-- Rapports will be stale, delete:
DELETE FROM rapports_comptables 
WHERE exercice_id = 1;
```

---

## 5. VERIFICATION QUERIES (BEFORE & AFTER)

### BEFORE Deletion Check List

```sql
-- 1. Count current state
SELECT 'ecritures_comptables' as table_name, COUNT(*) as total
FROM ecritures_comptables
UNION ALL
SELECT 'evenements_comptables', COUNT(*) FROM evenements_comptables
UNION ALL
SELECT 'propositions_en_attente', COUNT(*) FROM propositions_en_attente
UNION ALL
SELECT 'echeances_prets', COUNT(*) FROM echeances_prets
UNION ALL
SELECT 'prets_immobiliers', COUNT(*) FROM prets_immobiliers;

-- 2. Verify Bilan 2023 integrity
SELECT 
  COUNT(*) as bilan_entries,
  SUM(montant) FILTER (WHERE compte_debit LIKE '2%' OR compte_debit LIKE '3%') as actif,
  SUM(montant) FILTER (WHERE compte_credit LIKE '1%' OR compte_credit LIKE '8%') as passif
FROM ecritures_comptables 
WHERE type_ecriture = 'INIT_BILAN_2023' AND exercice_id = 2;

-- 3. Check for orphaned echeances
SELECT COUNT(*) as orphaned_echeances
FROM echeances_prets 
WHERE ecriture_comptable_id NOT IN (
  SELECT id FROM ecritures_comptables 
  WHERE echeances_prets.ecriture_comptable_id IS NOT NULL
);

-- 4. List T1-T4 data to be deleted
SELECT 
  type_ecriture,
  COUNT(*) as total,
  MIN(date_ecriture) as first_date,
  MAX(date_ecriture) as last_date
FROM ecritures_comptables 
WHERE exercice_id = 1 AND type_ecriture != 'INIT_BILAN_2023'
GROUP BY type_ecriture;

-- 5. Count movements linked to events
SELECT 
  'mouvements_comptes_courants' as table_name,
  COUNT(*) as total,
  COUNT(source_evenement_id) as with_event_link
FROM mouvements_comptes_courants
UNION ALL
SELECT 'mouvements_portefeuille', COUNT(*), COUNT(source_evenement_id)
FROM mouvements_portefeuille;
```

### AFTER Deletion Verification

```sql
-- 1. Verify final state
SELECT 'Remaining ecritures' as check_name, COUNT(*) as count
FROM ecritures_comptables
UNION ALL
SELECT 'Remaining 2023', COUNT(*) 
FROM ecritures_comptables WHERE exercice_id = 2
UNION ALL
SELECT 'Remaining Bilan', COUNT(*) 
FROM ecritures_comptables WHERE type_ecriture = 'INIT_BILAN_2023'
UNION ALL
SELECT 'Remaining 2024', COUNT() 
FROM ecritures_comptables WHERE exercice_id = 1
UNION ALL
SELECT 'Orphaned echeances', COUNT(*) 
FROM echeances_prets WHERE ecriture_comptable_id NOT IN (
  SELECT id FROM ecritures_comptables 
  WHERE echeances_prets.ecriture_comptable_id IS NOT NULL
);

-- 2. Verify data integrity
SELECT 
  'Prets still intact' as check_name,
  COUNT(*) as count
FROM prets_immobiliers;

SELECT 'Echeances still intact', COUNT(*) FROM echeances_prets;

-- 3. Verify no data loss in preserved tables
SELECT 'Bilan entries preserved', COUNT(*) FROM ecritures_comptables 
WHERE type_ecriture = 'INIT_BILAN_2023';
```

---

## 6. EXACT DELETION QUERIES

### Safe Queries (Tested Order)

```sql
-- ═══════════════════════════════════════════════════════════════════
-- TRANSACTION: Safe T1-T4 2024 Deletion
-- ═══════════════════════════════════════════════════════════════════

BEGIN TRANSACTION;

-- Step 1: Save what we're deleting (optional log)
CREATE TEMP TABLE deleted_ecritures_log AS
SELECT * FROM ecritures_comptables 
WHERE exercice_id = 1 AND type_ecriture != 'INIT_BILAN_2023';

-- Step 2: Delete from lowest-level tables first
DELETE FROM mouvements_comptes_courants 
WHERE source_evenement_id NOT IN (
  SELECT id FROM evenements_comptables 
  WHERE type_evenement = 'INIT_BILAN_2023'
);

DELETE FROM mouvements_portefeuille 
WHERE source_evenement_id NOT IN (
  SELECT id FROM evenements_comptables 
  WHERE type_evenement = 'INIT_BILAN_2023'
);

-- Step 3: Delete ecritures (the main deletion)
DELETE FROM ecritures_comptables 
WHERE exercice_id = 1 AND type_ecriture != 'INIT_BILAN_2023';

-- Step 4: Delete orphaned events
DELETE FROM evenements_comptables 
WHERE ecritures_creees IS NULL OR array_length(ecritures_creees, 1) IS NULL
OR NOT (ecritures_creees && ARRAY(SELECT id FROM ecritures_comptables));

-- Step 5: Clean propositions (if needed)
DELETE FROM propositions_en_attente 
WHERE statut IN ('REJETEE', 'EXPIREE');

-- Step 6: Recalculate caches
DELETE FROM balances_mensuelles WHERE exercice_id = 1;
DELETE FROM rapports_comptables WHERE exercice_id = 1;

-- Verify nothing broke
SELECT 'VERIFICATION' as phase;
SELECT COUNT(*) FROM prets_immobiliers; -- Should still be 2
SELECT COUNT(*) FROM echeances_prets;   -- Should still be 467
SELECT COUNT(*) FROM ecritures_comptables WHERE exercice_id = 2; -- Should still be 11

COMMIT;
```

---

## 7. SAFETY CHECKS BEFORE DELETION

✅ **MANDATORY Checklist:**

- [ ] **Backup Created**: Run `python sauvegarder_base.py` and verify file in `backups/`
- [ ] **SQL Dump Created**: Run `bash sauvegarder_base.sh` (if available)
- [ ] **Verification Queries Run**: Execute all "BEFORE Deletion" queries and log results
- [ ] **Bilan 2023 Integrity**: Verified 11 entries with correct balances
- [ ] **Prêts Count**: Verified 2 prêts and 467 échéances remain untouched
- [ ] **T1-T4 Count**: Verified 146 entries to be deleted (exercice_id = 1, NOT INIT_BILAN_2023)
- [ ] **No Direct FK Constraints**: Verified no cascading deletes will harm loan data
- [ ] **Exercice States**: Checked exercice 2023 = CLOTURE, exercice 2024 = OUVERT
- [ ] **Event Count**: Verified 0 events (safe to delete all if needed)
- [ ] **Proposition Count**: Verified 0 propositions (safe to delete)

⚠️ **ABORT DELETION IF:**

- Bilan 2023 count is NOT 11
- Prêts count changes
- Écheances count changes
- Any SQL error occurs
- Unexpected row counts

---

## 8. ROLLBACK PROCEDURE

**If deletion fails or data corruption occurs:**

```bash
# 1. Stop all applications accessing DB
# 2. Restore from latest backup:

# Option A: From JSON backup
python restore_from_json_backup.py backups/soeurise_bd_YYYYMMDD_HHMMSS.json

# Option B: From SQL dump (if available)
psql $DATABASE_URL < backups/dump_YYYYMMDD_HHMMSS.sql

# Option C: Contact Ulrik for manual restore on Render
```

---

## 9. SUMMARY TABLE

| Data Type | Count | To Keep? | Identifier | Notes |
|-----------|-------|----------|------------|-------|
| Bilan 2023 | 11 | ✅ YES | type_ecriture = 'INIT_BILAN_2023' AND exercice_id = 2 | Core asset position |
| T1-T4 2024 | 146 | ❌ NO | exercice_id = 1 AND type_ecriture != 'INIT_BILAN_2023' | Transactional data to reset |
| Prêts | 2 | ✅ YES | prets_immobiliers table | Loan master data |
| Écheances | 467 | ✅ YES | echeances_prets table | Loan payment schedule |
| Événements | 0 | ❓ ? | evenements_comptables table | Can be cleared |
| Propositions | 0 | ❌ NO | propositions_en_attente table | Should be emptied |

---

## 10. FINAL NOTES

1. **NO CASCADE from Prêts**: The prets_immobiliers table has NO foreign keys pointing to ecritures_comptables, so deletion is safe.

2. **Nullable FK**: echeances_prets.ecriture_comptable_id is NULLABLE, so orphaned echéances won't cause constraint violations.

3. **Reverse FK**: Even if there were constraints, they're one-directional (events → ecritures), so deleting ecritures won't cascade.

4. **Always Backup**: Even though deletion seems safe, ALWAYS create backup before running DELETE queries.

5. **Verification is Key**: Run verification queries before AND after to ensure data integrity.

6. **Render Deployment**: After deletion, changes will sync to Render after next deploy by Ulrik.

