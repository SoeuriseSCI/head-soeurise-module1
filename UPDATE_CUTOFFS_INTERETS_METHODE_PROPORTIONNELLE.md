# Mise à Jour Cutoffs Intérêts - Méthode Proportionnelle

**Date** : 20 novembre 2025
**Raison** : Passage de la méthode sur capital à la méthode proportionnelle basée sur les tableaux d'amortissement

## Changement de Méthode

### Ancienne méthode (sur capital)
```
Intérêts courus = Capital restant × Taux × (Jours / 365)
```

### Nouvelle méthode (proportionnelle - préférée)
```
Intérêts courus = Intérêts échéance × (Jours courus / Jours période)
```

**Avantage** : Suit directement les tableaux d'amortissement des prêts

## Nouveaux Montants Calculés

### Prêt LCL #1 (Taux 1,24%)
- Intérêts échéance 15/12/2023 : 258,33€
- Calcul : 258,33€ × (16/31) = **133,33€**
- Ancien montant : 135,89€
- Écart : -2,56€

### Prêt LCL #2 (Taux 1,05%)
- Intérêts échéance 15/12/2023 : 215,08€
- Calcul : 215,08€ × (16/31) = **111,01€**
- Ancien montant : 112,70€
- Écart : -1,69€

### Total
- Nouveau total : **244,34€**
- Ancien total : 248,59€
- Écart : -4,25€

## Commandes SQL à Exécuter sur Render

```sql
-- Mise à jour cutoff prêt #1 (31/12/2023)
UPDATE ecritures_comptables
SET montant = 133.33,
    notes = 'Calcul proportionnel: 258,33€ × (16/31 jours). Période: 2023-12-16 → 2023-12-31. Extourne créée automatiquement au 01/01/2024.'
WHERE date_ecriture = '2023-12-31'
  AND type_ecriture = 'CUTOFF_INTERETS_COURUS'
  AND compte_debit = '661'
  AND compte_credit = '1688'
  AND montant = 135.89;

-- Mise à jour extourne prêt #1 (01/01/2024)
UPDATE ecritures_comptables
SET montant = 133.33
WHERE date_ecriture = '2024-01-01'
  AND type_ecriture = 'EXTOURNE_CUTOFF'
  AND compte_debit = '1688'
  AND compte_credit = '661'
  AND montant = 135.89;

-- Mise à jour cutoff prêt #2 (31/12/2023)
UPDATE ecritures_comptables
SET montant = 111.01,
    notes = 'Calcul proportionnel: 215,08€ × (16/31 jours). Période: 2023-12-16 → 2023-12-31. Extourne créée automatiquement au 01/01/2024.'
WHERE date_ecriture = '2023-12-31'
  AND type_ecriture = 'CUTOFF_INTERETS_COURUS'
  AND compte_debit = '661'
  AND compte_credit = '1688'
  AND montant = 112.70;

-- Mise à jour extourne prêt #2 (01/01/2024)
UPDATE ecritures_comptables
SET montant = 111.01
WHERE date_ecriture = '2024-01-01'
  AND type_ecriture = 'EXTOURNE_CUTOFF'
  AND compte_debit = '1688'
  AND compte_credit = '661'
  AND montant = 112.70;
```

## Script Python pour Render

```bash
python << 'ENDSCRIPT'
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

engine = create_engine(os.environ['DATABASE_URL'])
session = sessionmaker(bind=engine)()

print("Mise à jour cutoffs intérêts - Méthode proportionnelle\n")

# Mise à jour cutoff prêt #1
session.execute(text("""
    UPDATE ecritures_comptables
    SET montant = 133.33,
        notes = 'Calcul proportionnel: 258,33€ × (16/31 jours). Période: 2023-12-16 → 2023-12-31. Extourne créée automatiquement au 01/01/2024.'
    WHERE date_ecriture = '2023-12-31' AND type_ecriture = 'CUTOFF_INTERETS_COURUS'
      AND compte_debit = '661' AND compte_credit = '1688' AND montant = 135.89
"""))
print("✅ Cutoff prêt #1 : 135.89€ → 133.33€")

# Mise à jour extourne prêt #1
session.execute(text("""
    UPDATE ecritures_comptables
    SET montant = 133.33
    WHERE date_ecriture = '2024-01-01' AND type_ecriture = 'EXTOURNE_CUTOFF'
      AND compte_debit = '1688' AND compte_credit = '661' AND montant = 135.89
"""))
print("✅ Extourne prêt #1 : 135.89€ → 133.33€")

# Mise à jour cutoff prêt #2
session.execute(text("""
    UPDATE ecritures_comptables
    SET montant = 111.01,
        notes = 'Calcul proportionnel: 215,08€ × (16/31 jours). Période: 2023-12-16 → 2023-12-31. Extourne créée automatiquement au 01/01/2024.'
    WHERE date_ecriture = '2023-12-31' AND type_ecriture = 'CUTOFF_INTERETS_COURUS'
      AND compte_debit = '661' AND compte_credit = '1688' AND montant = 112.70
"""))
print("✅ Cutoff prêt #2 : 112.70€ → 111.01€")

# Mise à jour extourne prêt #2
session.execute(text("""
    UPDATE ecritures_comptables
    SET montant = 111.01
    WHERE date_ecriture = '2024-01-01' AND type_ecriture = 'EXTOURNE_CUTOFF'
      AND compte_debit = '1688' AND compte_credit = '661' AND montant = 112.70
"""))
print("✅ Extourne prêt #2 : 112.70€ → 111.01€")

session.commit()
print("\n✅ Mises à jour appliquées")
print(f"Ancien total : 248.59€")
print(f"Nouveau total : 244.34€")
print(f"Écart : -4.25€")

session.close()
ENDSCRIPT
```

## Impact sur le Bilan 2024

L'écart de **-4,25€** sur les cutoffs d'intérêts réduira légèrement :
- Les charges 2023 de 4,25€
- Le résultat 2024 restera équilibré (les extournes compensent)

Le bilan restera équilibré.

---

**Validation** : Relancer `python construire_etats_financiers_2024.py` après la mise à jour
