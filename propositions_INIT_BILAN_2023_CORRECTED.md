# Initialisation Bilan 2023 - SCI SOEURISE

**Date:** 22/10/2025 22:50  
**Exercice:** 01/01/2023 - 31/12/2023  
**Source:** Comptes annuels 2023 signés par CRP 2C

---

## Bilan Synthétique au 31/12/2023

### ACTIF TOTAL: €463,618

**Immobilisations (€450,029):**
- Compte 280: Titres immobilisés SCPI: €500,032
- Compte 290: Provision epargne pierre: -€50,003

**Actif Circulant (€13,589):**
- Compte 412: Autres créances: €7,356
- Compte 502: Actions (autres titres): €4,140
- Compte 512: Banque LCL: €2,093

### PASSIF TOTAL: €463,618

**Capitaux Propres (-€35,148):**
- Compte 101: Capital: €1,000
- Compte 120: Report à nouveau: -€57,992
- Compte 130: Résultat 2023: €21,844

**Dettes (€498,765):**
- Compte 161: Emprunts LCL: €497,993
- Compte 444: Compte courant Bergsten Ulrik: €120
- Compte 401: Dettes fournisseurs: €653

---

## Propositions d'Écritures d'Ouverture

### Écriture 2023-INIT-0001: Ouverture Immobilisations
```
Débit  Compte 280 (Titres SCPI)          €500,032
  Crédit Compte 899 (Bilan ouverture)             €500,032
```

### Écriture 2023-INIT-0002: Ouverture Provision
```
Débit  Compte 899 (Bilan ouverture)      €50,003
  Crédit Compte 290 (Provision epargne)          €50,003
```

### Écriture 2023-INIT-0003: Ouverture Créances
```
Débit  Compte 412 (Autres créances)      €7,356
  Crédit Compte 899 (Bilan ouverture)            €7,356
```

### Écriture 2023-INIT-0004: Ouverture Valeurs Mobilières
```
Débit  Compte 502 (Actions propres)      €4,140
  Crédit Compte 899 (Bilan ouverture)            €4,140
```

### Écriture 2023-INIT-0005: Ouverture Disponibilités
```
Débit  Compte 512 (Banque LCL)           €2,093
  Crédit Compte 899 (Bilan ouverture)            €2,093
```

### Écriture 2023-INIT-0006: Ouverture Capital
```
Débit  Compte 899 (Bilan ouverture)      €1,000
  Crédit Compte 101 (Capital)                    €1,000
```

### Écriture 2023-INIT-0007: Ouverture Report à Nouveau
```
Débit  Compte 120 (Report à nouveau)     €57,992
  Crédit Compte 899 (Bilan ouverture)            €57,992
```

### Écriture 2023-INIT-0008: Ouverture Emprunts
```
Débit  Compte 899 (Bilan ouverture)      €497,993
  Crédit Compte 161 (Emprunts LCL)               €497,993
```

### Écriture 2023-INIT-0009: Ouverture Compte Courant
```
Débit  Compte 899 (Bilan ouverture)      €120
  Crédit Compte 444 (Compte courant Ulrik)       €120
```

### Écriture 2023-INIT-0010: Ouverture Dettes Fournisseurs
```
Débit  Compte 899 (Bilan ouverture)      €653
  Crédit Compte 401 (Dettes fournisseurs)        €653
```

---

## Vérification de l'Équilibre

**Total Débits (Actif):** €463,618  
**Total Crédits (Passif):** €463,618  
**Équilibre:** ✓ Vérifié

---

## Résultat Net 2023

**Produits:** €30,795 (Quote-part bénéfice SCPI attribuée)  
**Charges:** €8,951
- Intérêts emprunts: €5,736
- Charges externes (honoraires, assurances): €3,138
- Taxes: €78

**Résultat net comptable:** €21,844

---

## Métadonnées

```json
{
  "type_evenement": "INIT_BILAN_2023",
  "token": "9dde288cb3540b8283ba951d6f13725f",
  "generee_at": "2025-10-22T22:50:00.000000",
  "nb_ecritures": 10,
  "total_actif": 463618,
  "total_passif": 463618,
  "resultat_net": 21844,
  "validations": {
    "pdf_source": "Comptes_annuels_2023_SCI_SOEURISE-Signé.pdf",
    "expert_comptable": "Clotilde RIVIERE-PROST (CRP 2C)",
    "date_signature": "2024-05-03",
    "bilan_equilibre": true
  }
}
```
