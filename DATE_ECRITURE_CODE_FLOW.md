# Code Flow: date_ecriture NULL Issue

## Execution Flow

```
EMAIL RECEIVED
     ↓
[module2_workflow_v2.py] WorkflowModule2V2.traiter_email()
     ↓
     ├─→ DetecteurTypeEvenement.detecter() → TypeEvenement
     ↓
     ├─→ _traiter_evenement_simple() [or other branches]
     ↓
     ├─→ GenerateurPropositions.generer_propositions_evenement_simple()
     │   ├─→ Creates propositions WITHOUT date_ecriture ❌
     │   └─→ Returns: {
     │       "propositions": [{
     │           "numero_ecriture": "2024-1109-001",
     │           "type": "LOYER",
     │           "compte_debit": "511",
     │           "compte_credit": "701",
     │           "montant": 2500,
     │           "libelle": "Encaissement loyer"
     │           // ❌ MISSING: "date_ecriture"
     │       }],
     │       "token": "abc123..."
     │   }
     ↓
[STORAGE] propositions_en_attente table
     ├─→ token: "abc123..."
     ├─→ type_evenement: "EVENEMENT_SIMPLE"
     ├─→ propositions_json: {propositions: [...]}
     ├─→ statut: "EN_ATTENTE"
     ↓
USER VALIDATION EMAIL REPLY
     ↓
[module2_validations.py] OrchestratorValidations.traiter_email_validation()
     ↓
     PHASE 5: DetecteurValidations.detecter_validation()
     ├─→ Searches: [_Head] VALIDE: abc123...
     ├─→ Returns: token_email = "abc123..."
     ↓
     PHASE 6: PropositionsManager.recuperer_proposition(token)
     ├─→ Queries: SELECT * FROM propositions_en_attente WHERE token = 'abc123...'
     ├─→ Returns: proposition_data with propositions list
     ↓
     PHASE 7: ValidateurIntegriteJSON.valider_propositions()
     ├─→ Validates: token MD5, accounts exist, amounts > 0
     ├─→ ❌ DOES NOT VALIDATE: date_ecriture present
     ├─→ Returns: (True, "")  [passes validation]
     ↓
     PHASE 8: ProcesseurInsertion._inserer_propositions_generiques()
     │
     ├─→ FOR EACH proposition in propositions:
     │   ├─→ Line 386: date_ecriture_prop = prop.get('date_ecriture')
     │   │   │
     │   │   └─→ KEY NOT FOUND → returns None ❌
     │   │
     │   ├─→ Line 387: if isinstance(None, str):  [FALSE]
     │   │   └─→ Parsing skipped
     │   │
     │   ├─→ Line 392-405: CREATE EcritureComptable(
     │   │       exercice_id = 1,
     │   │       numero_ecriture = "2024-1109-001",
     │   │       date_ecriture = None,  ❌ NOT NULL VIOLATION
     │   │       libelle_ecriture = "Encaissement loyer",
     │   │       compte_debit = "511",
     │   │       compte_credit = "701",
     │   │       montant = Decimal('2500.00'),
     │   │       ...
     │   │   )
     │   │
     │   └─→ session.add(ecriture)
     │       session.flush()  → ❌ DATABASE ERROR
     │
     └─→ IntegrityError caught at line 411
         └─→ Rolls back transaction
         └─→ Returns: (False, "Erreur integrite DB: NOT NULL violation")

RESULT: ❌ INSERTION FAILS
```

---

## Data Structure Evolution

### Input: Email Object
```python
{
    "email_id": "msg_12345@domain.com",
    "from": "ulrik@example.com",
    "date": "2024-11-09T15:30:00+00:00",  # ← HAS DATE but not passed to generator
    "subject": "Loyer novembre",
    "body": "Loyer LCL: 2500€",
    "attachments": []
}
```

### After Generation Phase (INCORRECT)
```python
# From GenerateurPropositions.generer_propositions_evenement_simple()
{
    "propositions": [
        {
            "numero_ecriture": "2024-1109-001",
            "type": "LOYER",
            "compte_debit": "511",
            "compte_credit": "701",
            "montant": 2500,
            "libelle": "Encaissement loyer - 2500€"
            # ❌ date_ecriture MISSING
        }
    ],
    "token": "abc123..."
}
```

### After Generation Phase (CORRECT - What it should be)
```python
{
    "propositions": [
        {
            "numero_ecriture": "2024-1109-001",
            "type": "LOYER",
            "compte_debit": "511",
            "compte_credit": "701",
            "montant": 2500,
            "libelle": "Encaissement loyer - 2500€",
            "date_ecriture": "2024-11-09"  # ✅ FROM email.date
        }
    ],
    "token": "abc123..."
}
```

### During Insertion (FAILS)
```python
# module2_validations.py line 386
date_ecriture_prop = prop.get('date_ecriture')  # → None

# module2_validations.py line 395
date_ecriture=None  # ← PASSED TO ORM

# models_module2.py line 88
date_ecriture = Column(Date, nullable=False)  # ← NOT NULL CONSTRAINT

# RESULT: IntegrityError
```

---

## File References

### 1. models_module2.py - Column Definition
**Line 80-122:** `EcritureComptable` class
```python
class EcritureComptable(Base):
    __tablename__ = 'ecritures_comptables'
    
    # ... [lines 83-87] ...
    date_ecriture = Column(Date, nullable=False)  # ← Line 88
```

### 2. module2_workflow_v2.py - Proposal Generation

**Lines 970-1003:** Simple Events
```python
@staticmethod
def generer_propositions_evenement_simple(email: Dict, montant: float, type_evt: str):
    propositions = [{
        "numero_ecriture": f"2024-{datetime.now().strftime('%m%d')}-001",
        # ❌ Missing: "date_ecriture"
    }]
```

**Lines 1006-1051:** Init Bilan 2023
```python
@staticmethod
def generer_propositions_init_bilan_2023(comptes: List[Dict]):
    propositions = []
    for i, compte in enumerate(comptes, 1):
        propositions.append({
            "numero_ecriture": f"2023-INIT-{i:04d}",
            # ❌ Missing: "date_ecriture"
        })
```

**Lines 1118-1158:** Closure Exercise
```python
@staticmethod
def generer_propositions_cloture_2023(credit_data: Dict, scpi_data: List[Dict]):
    propositions = []
    if credit_data.get('total_interets_payes', 0) > 0:
        propositions.append({
            "numero_ecriture": "2023-CLOTURE-INTERETS",
            # ❌ Missing: "date_ecriture"
        })
```

### 3. module2_validations.py - Insertion Logic

**Lines 364-423:** `_inserer_propositions_generiques()` method
```python
def _inserer_propositions_generiques(self, propositions: List[Dict], ...):
    for prop in propositions:
        try:
            # Line 386
            date_ecriture_prop = prop.get('date_ecriture')  # ← RETURNS None
            
            # Line 387-390
            if isinstance(date_ecriture_prop, str):  # ← False when None
                # ... parsing skipped ...
                pass
            
            # Line 392-405
            ecriture = EcritureComptable(
                # ... other fields ...
                date_ecriture=date_ecriture_prop,  # ← None PASSED HERE
            )
```

**Lines 178-268:** `ValidateurIntegriteJSON.valider_propositions()`
```python
def valider_propositions(self, propositions: List[Dict], token_email: str):
    # Validates:
    # - Token MD5
    # - compte_debit exists
    # - compte_credit exists
    # - montant > 0
    
    # ❌ Does NOT validate:
    # - date_ecriture is present
    # - date_ecriture is not NULL
    # - date_ecriture can be parsed as date
```

### 4. detecteurs_evenements.py - Reference (CORRECT)

**Lines 139-164:** `DetecteurAssurancePret.generer_proposition()`
```python
def generer_proposition(self, evenement: Dict) -> Dict:
    montant = float(evenement.get('montant', 0))
    date_op = evenement.get('date_operation')  # ← GETS DATE
    
    return {
        'type_evenement': 'ASSURANCE_PRET',
        'ecritures': [{
            'date_ecriture': date_op,  # ✅ CORRECTLY SETS DATE
            'libelle_ecriture': '...',
            'compte_debit': '616',
            'compte_credit': '512',
            'montant': montant
        }]
    }
```

---

## Problem Summary Table

| Component | Expected | Actual | Result |
|-----------|----------|--------|--------|
| **Email Object** | Has `date` field | Has `date` field ✅ | Date available but not used |
| **Proposal Generation** | Include `date_ecriture` | Missing ❌ | None in proposal |
| **Validation** | Check `date_ecriture` exists | No check ❌ | Invalid proposal accepted |
| **Insertion** | Use proposal's date | `.get()` returns None ❌ | NULL passed to NOT NULL column |
| **Database** | Accept date value | Rejects NULL ❌ | IntegrityError crash |

