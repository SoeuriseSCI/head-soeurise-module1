# Système de Gestion des Prêts Immobiliers

## 🎯 Objectif

Résoudre le problème : **Les relevés bancaires ne ventilent pas intérêts/capital**.

```
Relevé bancaire :
"15/11/2023 | Prêt LCL #5009736BRM | -1,166.59€"

Question comptable :
- Combien en intérêts (compte 661) ?
- Combien en capital (compte 164) ?
```

**Solution** : Stocker les tableaux d'amortissement comme **données de référence** puis faire un **lookup** lors de la comptabilisation.

---

## 📦 Architecture

### **Workflow en 2 Temps**

#### **Temps 1 : Ingestion Référence** (Type : PRET_IMMOBILIER)

```
Email avec "Tableaux amortissement LCL.pdf"
    ↓
DetecteurTypeEvenement → PRET_IMMOBILIER
    ↓
ParseurTableauPret → Extraction complète (contrat + toutes échéances)
    ↓
PretsManager.ingest_tableau_pret()
    ↓
Stockage dans BD :
  - prets_immobiliers (1 ligne : contrat)
  - echeances_prets (240 lignes : échéancier complet)
    ↓
Rapport ingestion (PAS de proposition comptable)
```

#### **Temps 2 : Comptabilisation** (Type : CLOTURE_EXERCICE)

```
Email avec relevé bancaire
"15/11/2023 | Prêt #5009736BRM | -1,166.59€"
    ↓
DetecteurTypeEvenement → CLOTURE_EXERCICE
    ↓
Parser relevé → Détecter lignes prêts
    ↓
PretsManager.lookup_echeance(numero="5009736BRM", date=2023-11-15)
    ↓
Résultat :
{
  "montant_total": 1166.59,
  "montant_interet": 215.32,  ← Compte 661
  "montant_capital": 951.27    ← Compte 164
}
    ↓
Génération proposition avec ventilation précise
    ↓
Après validation : marquer_echeance_comptabilisee()
```

---

## 🗄️ Tables BD

### **prets_immobiliers**
Contrats de prêts (données contractuelles).

```sql
CREATE TABLE prets_immobiliers (
    id SERIAL PRIMARY KEY,
    numero_pret VARCHAR(50) UNIQUE,      -- Ex: 5009736BRM0911AH
    banque VARCHAR(100),                 -- Ex: LCL
    montant_initial NUMERIC(15,2),       -- Ex: 250000.00
    taux_annuel NUMERIC(6,4),            -- Ex: 0.0105 (1.05%)
    duree_mois INTEGER,                  -- Ex: 240
    date_debut DATE,                     -- Ex: 2023-04-15
    date_fin DATE,                       -- Ex: 2043-04-15
    type_amortissement VARCHAR(50),      -- AMORTISSEMENT_CONSTANT | FRANCHISE_PARTIELLE
    echeance_mensuelle NUMERIC(15,2),    -- Ex: 1166.59
    ...
);
```

### **echeances_prets**
Échéancier ligne par ligne (une ligne par mois).

```sql
CREATE TABLE echeances_prets (
    id SERIAL PRIMARY KEY,
    pret_id INTEGER REFERENCES prets_immobiliers(id),
    numero_echeance INTEGER,             -- 1, 2, 3... 240
    date_echeance DATE,                  -- 2023-05-15, 2023-06-15...
    montant_total NUMERIC(15,2),         -- 1166.59
    montant_interet NUMERIC(15,2),       -- 218.75 ← Clé !
    montant_capital NUMERIC(15,2),       -- 947.84 ← Clé !
    capital_restant_du NUMERIC(15,2),    -- 249052.16
    comptabilise BOOLEAN DEFAULT FALSE,
    ecriture_comptable_id INTEGER,
    UNIQUE (pret_id, date_echeance)
);
```

**Index** : Lookup ultra-rapide par `(pret_id, date_echeance)`.

---

## 🔧 Composants

### **1. Modèles (models_module2.py)**
Classes SQLAlchemy : `PretImmobilier`, `EcheancePret`.

### **2. Migration (migration_004_tables_prets.py)**
Crée les tables + index.

Usage :
```bash
python migration_004_tables_prets.py
```

### **3. Parseur (module2_workflow_v2.py)**
`ParseurTableauPret` : Extrait contrat + toutes échéances depuis PDF via Claude Vision.

### **4. Gestionnaire (prets_manager.py)**
`PretsManager` :
- `ingest_tableau_pret()` : Stocke données
- `lookup_echeance()` : Retrouve ventilation
- `marquer_echeance_comptabilisee()` : Marque comme traitée

### **5. Workflow (module2_integration_v2.py)**
Détecte `PRET_IMMOBILIER` et orchestre ingestion.

---

## 📝 Exemple Complet

### **Étape 1 : Ingestion Tableau**

Email reçu : `"Tableaux d'amortissement LCL.pdf"`

```python
# Détection
type_evt = DetecteurTypeEvenement.detecter(email)
# → PRET_IMMOBILIER

# Parsing
parseur = ParseurTableauPret(ocr)
data = parseur.parse_from_pdf("tableau.pdf")
# → {"pret": {...}, "echeances": [{...}, {...}, ...]}

# Ingestion
manager = PretsManager(session)
success, msg, pret_id = manager.ingest_tableau_pret(
    data['pret'],
    data['echeances'],
    source_email_id=email['id']
)
# → 240 échéances stockées en BD
```

**Résultat** : Aucune écriture comptable, juste stockage référence.

### **Étape 2 : Comptabilisation Relevé**

Email reçu : `"Relevé bancaire novembre 2023"`

Contenu : `"15/11/2023 | Prêt LCL #5009736BRM | -1,166.59€"`

```python
# Lookup
from datetime import date
ventilation = manager.lookup_echeance(
    numero_pret="5009736BRM0911AH",
    date_echeance=date(2023, 11, 15)
)
# → {
#     "montant_total": 1166.59,
#     "montant_interet": 215.32,
#     "montant_capital": 951.27,
#     ...
#   }

# Génération propositions
propositions = [
    {
        "compte": "661100",
        "libelle": "Intérêts emprunts",
        "debit": 215.32,
        "credit": 0
    },
    {
        "compte": "164100",
        "libelle": "Emprunts (capital)",
        "debit": 951.27,
        "credit": 0
    },
    {
        "compte": "512000",
        "libelle": "Banque",
        "debit": 0,
        "credit": 1166.59
    }
]
```

**Résultat** : Écriture comptable précise avec ventilation exacte.

---

## 🚀 Déploiement

### **1. Appliquer Migration**

Sur serveur Render (shell) :
```bash
python migration_004_tables_prets.py
```

### **2. Tester Ingestion**

Envoyer email avec tableau amortissement LCL.

**Attendu** :
- Détection `PRET_IMMOBILIER` ✓
- Parsing réussi ✓
- Stockage BD ✓
- Email rapport (pas de propositions) ✓

### **3. Tester Lookup**

Envoyer relevé bancaire avec ligne prêt.

**Attendu** :
- Détection `CLOTURE_EXERCICE` ✓
- Lookup échéance ✓
- Proposition avec ventilation ✓
- Email propositions ✓

---

## 🔍 Vérification BD

```sql
-- Lister prêts actifs
SELECT numero_pret, banque, montant_initial, echeance_mensuelle
FROM prets_immobiliers
WHERE actif = TRUE;

-- Compter échéances stockées
SELECT pret_id, COUNT(*)
FROM echeances_prets
GROUP BY pret_id;

-- Échéances non comptabilisées
SELECT p.numero_pret, e.date_echeance, e.montant_total
FROM echeances_prets e
JOIN prets_immobiliers p ON e.pret_id = p.id
WHERE e.comptabilise = FALSE
ORDER BY e.date_echeance;
```

---

## 📊 Avantages

1. **Précision** : Ventilation exacte intérêts/capital (pas d'approximation)
2. **Automatisation** : Un seul email tableau → 240 échéances stockées
3. **Traçabilité** : Flag `comptabilise` + lien vers `ecriture_comptable_id`
4. **Performance** : Lookup O(1) avec index `(pret_id, date_echeance)`
5. **Scalabilité** : Gère N prêts facilement

---

## 🔮 Évolutions Futures

1. **Assurance emprunteur** : Ajouter ventilation assurance (compte 616)
2. **Prêts in fine** : Gérer franchises totales (0€ capital pendant X années)
3. **Renégociations** : Désactiver ancien prêt, créer nouveau
4. **Alertes** : Notifier si échéance non comptabilisée après X jours
5. **Dashboard** : Visualiser capital restant dû, total intérêts payés

---

**Date** : 27 octobre 2025
**Version** : 1.0
**Auteur** : Claude Code
