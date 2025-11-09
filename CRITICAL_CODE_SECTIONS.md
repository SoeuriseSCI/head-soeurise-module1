# Critical Code Sections - date_ecriture NULL Issue

## 1. TABLE DEFINITION (models_module2.py:80-89)

```python
class EcritureComptable(Base):
    __tablename__ = 'ecritures_comptables'
    
    id = Column(Integer, primary_key=True)
    exercice_id = Column(Integer, ForeignKey('exercices_comptables.id'), nullable=False)
    
    # Identifiant unique
    numero_ecriture = Column(String(50), nullable=False)
    date_ecriture = Column(Date, nullable=False)  # ← CONSTRAINT: NOT NULL
    date_enregistrement = Column(DateTime, default=datetime.utcnow)
```

**Issue:** `date_ecriture` MUST have a value

---

## 2. PROPOSAL GENERATION - PROBLEM AREAS

### Problem Area A: Simple Events (module2_workflow_v2.py:970-1003)

```python
@staticmethod
def generer_propositions_evenement_simple(email: Dict, montant: float, type_evt: str) -> Tuple[str, Dict, str]:
    """Génère propositions pour événement simple (loyer/charge)"""
    
    mapping = {
        'LOYER': {'debit': '511', 'credit': '701', 'libelle': 'Encaissement loyer'},
        'CHARGE': {'debit': '614', 'credit': '401', 'libelle': 'Charge'},
    }
    
    config = mapping.get(type_evt, mapping['CHARGE'])
    
    propositions = [
        {
            "numero_ecriture": f"2024-{datetime.now().strftime('%m%d')}-001",
            "type": type_evt,
            "compte_debit": config['debit'],
            "compte_credit": config['credit'],
            "montant": montant,
            "libelle": f"{config['libelle']} - {montant}€"
            # ❌ MISSING: "date_ecriture": ...
        }
    ]
    
    token = hashlib.md5(json.dumps(propositions, sort_keys=True).encode()).hexdigest()
    markdown = GenerateurPropositions._generer_markdown_propositions(propositions, type_evt)
    
    return markdown, {"propositions": propositions, "token": token}, token
```

**Fix:** Add `"date_ecriture": <date_from_email>`

---

### Problem Area B: Init Bilan 2023 (module2_workflow_v2.py:1006-1051)

```python
@staticmethod
def generer_propositions_init_bilan_2023(comptes: List[Dict]) -> Tuple[str, Dict, str]:
    """Génère propositions pour initialisation bilan 2023"""
    
    propositions = []
    compte_ouverture = "89"
    
    for i, compte in enumerate(comptes, 1):
        num_compte = compte["compte"]
        libelle = compte["libelle"]
        solde_original = compte["solde"]
        solde = abs(solde_original)
        
        sens = compte.get("sens", GenerateurPropositions._determiner_sens_compte(...))
        
        if sens == "DEBIT":
            propositions.append({
                "numero_ecriture": f"2023-INIT-{i:04d}",
                "type": "INIT_BILAN_2023",
                "compte_debit": num_compte,
                "compte_credit": compte_ouverture,
                "montant": solde,
                "libelle": f"Ouverture: {libelle}"
                # ❌ MISSING: "date_ecriture": "2023-01-01"  [or similar]
            })
        else:
            propositions.append({
                "numero_ecriture": f"2023-INIT-{i:04d}",
                "type": "INIT_BILAN_2023",
                "compte_debit": compte_ouverture,
                "compte_credit": num_compte,
                "montant": solde,
                "libelle": f"Ouverture: {libelle}"
                # ❌ MISSING: "date_ecriture": "2023-01-01"  [or similar]
            })
    
    token = hashlib.md5(json.dumps(propositions, sort_keys=True).encode()).hexdigest()
    markdown = GenerateurPropositions._generer_markdown_init_bilan(propositions, comptes)
    
    return markdown, {"propositions": propositions, "token": token}, token
```

**Fix:** Add `"date_ecriture": "2023-01-01"` to each proposal

---

### Problem Area C: Closure Exercise (module2_workflow_v2.py:1118-1158)

```python
@staticmethod
def generer_propositions_cloture_2023(credit_data: Dict, scpi_data: List[Dict]) -> Tuple[str, Dict, str]:
    """Génère propositions pour clôture exercice 2023"""
    
    propositions = []
    
    # Intérêts crédit
    if credit_data.get('total_interets_payes', 0) > 0:
        propositions.append({
            "numero_ecriture": "2023-CLOTURE-INTERETS",
            "type": "INTÉRÊTS_CRÉDIT",
            "compte_debit": "661",
            "compte_credit": "401",
            "montant": credit_data['total_interets_payes'],
            "libelle": f"Intérêts crédits 2023: {credit_data['total_interets_payes']}€"
            # ❌ MISSING: "date_ecriture": "2023-12-31"
        })
    
    # Réévaluations SCPI
    for i, reevals in enumerate(scpi_data, 1):
        if reevals['type'] == 'GAIN':
            propositions.append({
                "numero_ecriture": f"2023-CLOTURE-SCPI-GAIN-{i}",
                "type": "RÉÉVALUATION_SCPI_GAIN",
                "compte_debit": "440",
                "compte_credit": "754",
                "montant": reevals['montant'],
                "libelle": f"Rééval SCPI gain S{reevals['semestre']}: {reevals['montant']}€"
                # ❌ MISSING: "date_ecriture": "2023-12-31"
            })
    
    token = hashlib.md5(json.dumps(propositions, sort_keys=True).encode()).hexdigest()
    markdown = GenerateurPropositions._generer_markdown_cloture(propositions, credit_data, scpi_data)
    
    return markdown, {"propositions": propositions, "token": token}, token
```

**Fix:** Add `"date_ecriture": "2023-12-31"` to each proposal

---

## 3. INSERTION FAILURE (module2_validations.py:364-423)

```python
def _inserer_propositions_generiques(self,
                                    propositions: List[Dict],
                                    evt_original_id: str,
                                    evt_validation_id: str,
                                    email_validation_from: str,
                                    exercice_id: int = None) -> Tuple[bool, str, List[int]]:
    """Insere les propositions de facon generique"""
    
    try:
        # If no exercice specified, use 2024
        if not exercice_id:
            exercice_2024 = self.session.query(ExerciceComptable).filter_by(annee=2024).first()
            if not exercice_2024:
                return False, "Exercice 2024 non trouve", []
            exercice_id = exercice_2024.id
        
        ecriture_ids = []
        
        for prop in propositions:
            try:
                # Line 384-385 COMMENT:
                # CORRECTION: Utiliser date_ecriture de la proposition (date opération réelle)
                # au lieu de datetime.now() (date de traitement)
                
                # Line 386: PROBLEM STARTS HERE
                date_ecriture_prop = prop.get('date_ecriture')  # ← Returns None ❌
                
                # Line 387-390: Attempt to parse if string
                if isinstance(date_ecriture_prop, str):  # ← False when None ❌
                    from datetime import datetime as dt
                    date_ecriture_prop = dt.strptime(date_ecriture_prop, '%Y-%m-%d').date()
                
                # Line 392-405: CREATE WITH NULL DATE ❌
                ecriture = EcritureComptable(
                    exercice_id=exercice_id,
                    numero_ecriture=prop['numero_ecriture'],
                    date_ecriture=date_ecriture_prop,  # ← None PASSED HERE
                    libelle_ecriture=prop.get('libelle', ''),
                    type_ecriture=prop.get('type', 'AUTRE'),
                    compte_debit=str(prop['compte_debit']),
                    compte_credit=str(prop['compte_credit']),
                    montant=Decimal(str(prop['montant'])),
                    source_email_id=evt_original_id,
                    source_email_from=email_validation_from,
                    validee_at=datetime.now(),
                    notes=f"Validee par Ulrik via email {evt_validation_id}"
                )
                
                self.session.add(ecriture)
                self.session.flush()  # ← DATABASE ERROR HERE ❌
                ecriture_ids.append(ecriture.id)
            
            except IntegrityError as ie:
                self.session.rollback()
                return False, f"Erreur integrite DB: {str(ie)[:100]}", ecriture_ids  # ← RETURNS ERROR
```

**Issue Chain:**
1. Line 386: `prop.get('date_ecriture')` → None (key doesn't exist)
2. Line 387: `isinstance(None, str)` → False (skip parsing)
3. Line 395: `date_ecriture=None` (pass to ORM)
4. Line 407: `session.flush()` (database rejects NOT NULL violation)
5. Line 411: Catch IntegrityError, return failure

---

## 4. MISSING VALIDATION (module2_validations.py:178-268)

```python
def valider_propositions(self, propositions: List[Dict], token_email: str) -> Tuple[bool, str]:
    """Valide integrite des propositions"""
    
    # 1. Verifier token MD5
    token_calculated = hashlib.md5(
        json.dumps(propositions, sort_keys=True).encode()
    ).hexdigest()
    
    # Token comparison... [OK]
    
    # 2. Verifier chaque proposition
    for i, prop in enumerate(propositions):
        
        prop_type = prop.get('type', '')
        
        if prop_type == 'PRET_IMMOBILIER':
            # Special validation for loans
            pass
        else:
            # For accounting entries
            required_keys = ['compte_debit', 'compte_credit', 'montant', 'numero_ecriture']
            for key in required_keys:
                if key not in prop:
                    return False, f"Proposition {i}: cle '{key}' manquante"
            
            # ❌ MISSING: Check for 'date_ecriture'
            # ❌ MISSING: Validate date can be parsed
            # ❌ MISSING: Ensure date is not None
            
            # Verify montant
            try:
                montant = Decimal(str(prop['montant']))
                if montant < 0:
                    return False, f"Proposition {i}: montant ne peut pas etre negatif"
            except (ValueError, TypeError):
                return False, f"Proposition {i}: montant invalide"
            
            # Verify accounts exist in database
            compte_debit = self.session.query(PlanCompte).filter_by(
                numero_compte=str(prop['compte_debit'])
            ).first()
            
            if not compte_debit:
                return False, f"Proposition {i}: compte debit '{prop['compte_debit']}' n'existe pas"
    
    return True, ""  # ← RETURNS OK even without date_ecriture
```

**Missing Validations:**
1. Check `'date_ecriture' in prop`
2. Check `prop.get('date_ecriture') is not None`
3. Try parsing date if string
4. Validate date format (YYYY-MM-DD)

---

## 5. REFERENCE IMPLEMENTATION (detecteurs_evenements.py:139-164)

```python
class DetecteurAssurancePret(DetecteurBase):
    """Détecte les prélèvements d'assurance emprunteur"""
    
    def generer_proposition(self, evenement: Dict) -> Dict:
        """Génère la proposition d'écriture"""
        montant = float(evenement.get('montant', 0))
        date_op = evenement.get('date_operation')  # ← GETS DATE ✅
        
        # Calculate confidence level
        confiance = 1.0
        if abs(montant - self.MONTANT_TOTAL) > 0.01:
            confiance = 0.9
        
        return {
            'type_evenement': 'ASSURANCE_PRET',
            'description': f'Assurance emprunteur (Emma 66,58€ + Pauline 20,99€)',
            'confiance': confiance,
            'ecritures': [
                {
                    'date_ecriture': date_op,  # ✅ CORRECTLY INCLUDES DATE
                    'libelle_ecriture': f'Assurance emprunteur prêt LCL',
                    'compte_debit': '616',
                    'compte_credit': '512',
                    'montant': montant,
                    'type_ecriture': 'ASSURANCE_PRET',
                    'notes': 'Assurance uniquement pour prêt amortissable LCL (BRM0911AH)'
                }
            ]
        }
```

**Key Pattern:**
- Extracts date from source: `date_op = evenement.get('date_operation')`
- Includes in proposal: `'date_ecriture': date_op`
- Never allows NULL date

---

## 6. SOLUTION SUMMARY

### Option 1: Modify Proposal Generators (RECOMMENDED)

```python
# In generer_propositions_evenement_simple():
@staticmethod
def generer_propositions_evenement_simple(email: Dict, montant: float, type_evt: str):
    # Extract email date
    email_date = email.get('date')
    if email_date:
        date_str = email_date.strftime('%Y-%m-%d') if hasattr(email_date, 'strftime') else str(email_date)[:10]
    else:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    propositions = [{
        "numero_ecriture": f"2024-{datetime.now().strftime('%m%d')}-001",
        "type": type_evt,
        "compte_debit": config['debit'],
        "compte_credit": config['credit'],
        "montant": montant,
        "libelle": f"{config['libelle']} - {montant}€",
        "date_ecriture": date_str  # ✅ ADD THIS
    }]
```

### Option 2: Add Fallback in Insertion Logic

```python
# In _inserer_propositions_generiques():
date_ecriture_prop = prop.get('date_ecriture') or datetime.now().date()

if isinstance(date_ecriture_prop, str):
    from datetime import datetime as dt
    date_ecriture_prop = dt.strptime(date_ecriture_prop, '%Y-%m-%d').date()

ecriture = EcritureComptable(
    # ...
    date_ecriture=date_ecriture_prop,  # ✅ NO LONGER NULL
    # ...
)
```

### Option 3: Add Validation

```python
# In ValidateurIntegriteJSON.valider_propositions():
# After checking required_keys:
if 'date_ecriture' not in prop:
    return False, f"Proposition {i}: date_ecriture manquante"

date_ecriture = prop.get('date_ecriture')
if date_ecriture is None:
    return False, f"Proposition {i}: date_ecriture ne peut pas etre None"

# Try parsing if string
if isinstance(date_ecriture, str):
    try:
        from datetime import datetime as dt
        dt.strptime(date_ecriture, '%Y-%m-%d')
    except ValueError:
        return False, f"Proposition {i}: date_ecriture invalide (format: YYYY-MM-DD)"
```

---

