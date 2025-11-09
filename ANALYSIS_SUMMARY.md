# Database Analysis Summary - Safe Deletion Strategy

## Files Generated

Three comprehensive analysis documents have been created:

1. **DATABASE_DELETION_ANALYSIS.md** (Complete Technical Reference)
   - Full table structure documentation
   - Foreign key constraint maps
   - Deletion strategies with explanations
   - Safety verification procedures
   - Rollback procedures

2. **QUICK_REFERENCE_DELETION.txt** (Fast Copy-Paste Reference)
   - Current database state snapshot
   - Deletion criteria summary
   - Ready-to-run SQL queries
   - Verification checklists
   - Quick backup/restore commands

3. **This file** (Quick Summary)
   - High-level overview
   - Key findings
   - Action items

---

## Key Findings

### Database Structure (157 total entries)

| Component | Count | Status | Location |
|-----------|-------|--------|----------|
| **Bilan 2023** | 11 | ✅ KEEP | `type_ecriture = 'INIT_BILAN_2023' AND exercice_id = 2` |
| **T1-T4 2024** | 146 | ❌ DELETE | `exercice_id = 1 AND type_ecriture != 'INIT_BILAN_2023'` |
| **Prêts** | 2 | ✅ KEEP | `prets_immobiliers` table |
| **Échéances** | 467 | ✅ KEEP | `echeances_prets` table |
| **Propositions** | 0 | ⚠️ EMPTY | `propositions_en_attente` table |
| **Événements** | 0 | ? | `evenements_comptables` table |

### T1-T4 2024 Breakdown (146 entries to delete)

- **REMBOURSEMENT_PRET**: 22 entries
- **ASSURANCE_PRET**: 90 entries
- **REVENU_SCPI**: 13 entries
- **HONORAIRES_COMPTABLE**: 10 entries
- **FRAIS_BANCAIRES**: 8 entries
- **ACHAT_ETF**: 3 entries

### Foreign Key Safety Analysis

**Good News:**
- ✅ `prets_immobiliers` has NO foreign keys pointing to `ecritures_comptables`
- ✅ `echeances_prets.ecriture_comptable_id` is NULLABLE
- ✅ No CASCADE DELETE constraints from prêt tables
- ✅ Safe to delete T1-T4 2024 without affecting loan data

**What's Protected:**
- Bilan 2023: 11 entries (identified by type_ecriture = 'INIT_BILAN_2023')
- Prêts Master Data: 2 contracts
- Loan Payment Schedule: 467 échéances

---

## Deletion Criteria (Exact WHERE Clauses)

### How to Identify Bilan 2023 (DO NOT DELETE)
```sql
WHERE type_ecriture = 'INIT_BILAN_2023' AND exercice_id = 2
```
- Count: 11
- Represents: Opening balance for 2023
- Safety: CORE DATA - MUST NOT DELETE

### How to Identify T1-T4 2024 (DELETE THESE)
```sql
WHERE exercice_id = 1 AND type_ecriture != 'INIT_BILAN_2023'
```
- Count: 146
- Represents: All transactional data for Q1-Q4 2024
- Safety: Can be safely deleted (no loan data affected)

### How to Identify Prêt Payments (DO NOT DELETE)
```sql
WHERE type_ecriture IN ('REMBOURSEMENT_PRET', 'ASSURANCE_PRET')
```
- Count: 112 (22 + 90)
- Represents: Loan repayment and insurance
- Note: These ARE being deleted with T1-T4 2024 (intentional)

### How to Identify Prêt Master Data (DO NOT TOUCH)
```sql
SELECT * FROM prets_immobiliers;  -- 2 contracts
SELECT * FROM echeances_prets;    -- 467 payment lines
```
- These are NOT affected by deletion
- They are reference data for loan tracking

---

## Safe Deletion Procedure

### Step 1: Backup (MANDATORY)
```bash
cd /home/user/head-soeurise-module1

# Create JSON backup
python sauvegarder_base.py

# Create SQL dump (if available)
bash sauvegarder_base.sh

# Verify backup
ls -lh backups/soeurise_bd_*.json
```

### Step 2: Verify Before Deletion
Run these queries to confirm current state:
1. Count Bilan 2023: Expected 11
2. Count T1-T4 2024: Expected 146
3. Count Prêts: Expected 2
4. Count Échéances: Expected 467

(See QUICK_REFERENCE_DELETION.txt for exact queries)

### Step 3: Execute Deletion
```sql
DELETE FROM ecritures_comptables 
WHERE exercice_id = 1 AND type_ecriture != 'INIT_BILAN_2023';

DELETE FROM balances_mensuelles WHERE exercice_id = 1;
DELETE FROM rapports_comptables WHERE exercice_id = 1;
DELETE FROM propositions_en_attente WHERE statut IN ('REJETEE', 'EXPIREE');
```

### Step 4: Verify After Deletion
Run verification queries to confirm:
1. Total Écritures: Expected 11 (only Bilan 2023)
2. Bilan 2023: Expected 11
3. T1-T4 2024: Expected 0
4. Prêts: Expected 2 (UNCHANGED)
5. Échéances: Expected 467 (UNCHANGED)

---

## Table Structure Reference

### Main Table: `ecritures_comptables`

**Primary Identification Columns:**
- `id`: Integer (Primary Key)
- `exercice_id`: Integer (FK → exercices_comptables.id)
  - Value 1 = 2024
  - Value 2 = 2023
- `type_ecriture`: VARCHAR(50)
  - 'INIT_BILAN_2023' = Bilan entries
  - 'REMBOURSEMENT_PRET' = Loan principal
  - 'ASSURANCE_PRET' = Loan insurance
  - Others: REVENU_SCPI, HONORAIRES_COMPTABLE, etc.
- `date_ecriture`: DATE (when the entry was recorded)
- `montant`: NUMERIC(12, 2) (amount in euros)

**Other Key Columns:**
- `compte_debit`, `compte_credit`: Account codes (FK → plans_comptes)
- `numero_ecriture`: Internal reference number
- `source_email_id`: Email origin (for audit trail)
- `valide`: Boolean (whether validated)
- `created_at`, `updated_at`: Timestamps

### Reference Tables (DO NOT TOUCH)

#### `prets_immobiliers` (2 entries)
- 5009736BRM0911AH (LCL) - 250,000€
- 5009736BRLZE11AQ (LCL) - 250,000€

#### `echeances_prets` (467 entries)
- Linked to `prets_immobiliers` via `pret_id`
- Payment schedule line-by-line
- `ecriture_comptable_id` is NULLABLE (can be orphaned safely)

---

## Related Tables Affected by Deletion

| Table | Action | Reason |
|-------|--------|--------|
| `ecritures_comptables` | DELETE 146 rows | Main deletion target |
| `balances_mensuelles` | DELETE (exercice_id=1) | Cached, becomes stale |
| `rapports_comptables` | DELETE (exercice_id=1) | Cached, becomes stale |
| `propositions_en_attente` | OPTIONAL CLEAN | Already empty |
| `evenements_comptables` | OPTIONAL CLEAN | 0 entries |
| `mouvements_comptes_courants` | NOT AFFECTED | No FK to deleted entries |
| `mouvements_portefeuille` | NOT AFFECTED | No FK to deleted entries |
| `prets_immobiliers` | PROTECTED | 2 entries untouched |
| `echeances_prets` | PROTECTED | 467 entries untouched |

---

## Risk Assessment

**Risk Level: LOW**

**Rationale:**
1. No cascading deletes from loan tables
2. Nullable foreign keys in echeances_prets
3. No direct references from prets to ecritures
4. Exercice separation prevents accidental cross-year deletion
5. Type_ecriture filtering provides additional safety

**Mitigation:**
1. Backup before deletion
2. Run verification queries before/after
3. Use transaction (BEGIN...COMMIT) for atomic operation
4. Can rollback from backup if needed

---

## Next Steps

### Immediate Actions
1. Read `QUICK_REFERENCE_DELETION.txt` for copy-paste queries
2. Run backup commands: `python sauvegarder_base.py`
3. Run "BEFORE DELETION" verification queries
4. Document current state for audit trail

### When Ready to Delete
1. Execute deletion transaction (provided in QUICK_REFERENCE_DELETION.txt)
2. Run "AFTER DELETION" verification queries
3. Confirm Bilan 2023 (11 entries) still present
4. Confirm Prêts (2) and Échéances (467) unchanged
5. Commit changes

### After Deletion
1. Changes are local to dev environment
2. To sync to Render: Need Ulrik's manual deployment
3. Test thoroughly before asking for prod deployment

---

## Important Notes

### Data Preservation Guarantee
- **Bilan 2023**: Will remain intact (11 entries)
- **Prêts**: Will remain intact (2 contracts)
- **Échéances**: Will remain intact (467 lines)
- **Plan Comptable**: Will remain intact (all accounts)
- **Exercices**: Will remain intact (2023 + 2024)

### Data Loss Scope
- **T1-T4 2024 Écritures**: 146 entries deleted
- **Cached Balances**: Will be stale (can recalculate)
- **Cached Reports**: Will be stale (can regenerate)
- **Propositions**: Empty anyway (0 entries)

### Rollback Capability
- Full restore from JSON backup if needed
- Latest backup: `backups/soeurise_bd_20251109_130355.json`
- SQL dump restore if available

---

## Reference Files

**Location:** `/home/user/head-soeurise-module1/`

1. `DATABASE_DELETION_ANALYSIS.md` - Complete technical documentation
2. `QUICK_REFERENCE_DELETION.txt` - Fast reference and SQL queries
3. `models_module2.py` - ORM definitions (table schemas)
4. `alembic/versions/` - Database migrations
5. `backups/soeurise_bd_*.json` - Backup files

**Key Model Definitions:**
- `EcritureComptable` - Accounting entries
- `PretImmobilier` - Loan contracts
- `EcheancePret` - Loan payment schedule
- `EvenementComptable` - Email events queue
- `PropositionEnAttente` - Pending proposals

---

## Questions & Answers

**Q: Will deleting T1-T4 2024 affect the loan data?**
A: No. Prêts (2 contracts) and Échéances (467 lines) are completely protected. They have no direct links to T1-T4 2024 ecritures.

**Q: What if something goes wrong?**
A: Restore from backup using: `python sauvegarder_base.py --restore backups/soeurise_bd_20251109_130355.json`

**Q: Why are T1-T4 2024 being deleted?**
A: To reset the year for a fresh start. Bilan 2023 remains as the opening balance.

**Q: Can we delete prêt entries from T1-T4?**
A: Yes, they're part of T1-T4 2024. Master prêt data (in prets_immobiliers table) is protected.

**Q: Will the deleted data be recoverable?**
A: Yes, from the backup files created before deletion.

**Q: Can the deletion be undone after it's done?**
A: Yes, by restoring the backup. But you'll lose any data added after the deletion.

---

**Status:** Analysis Complete ✅
**Date Created:** 2025-11-09
**Last Updated:** 2025-11-09
**Version:** 1.0

