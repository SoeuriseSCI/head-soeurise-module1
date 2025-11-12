# Analyse : Doublons SCPI et Apports

> Problème identifié : Revenus SCPI et apports associés comptés 2 fois

---

## 🔍 Doublons Identifiés dans le Workflow

### 1. Revenus SCPI T4 2023 (7356.24€)

**Source 1 - Relevé bancaire** :
```
✅ Événement #1162: REVENU_SCPI
   Libellé: "VIR SEPA SCPI EPARGNE PIERRE LIBELLE:SCPI EPARGNE"
   Montant: 7356.24€
   Type: CREDIT
```

**Source 2 - Avis d'opération** :
```
✅ Événement #1258: REVENU_SCPI
   Libellé: "Revenus SCPI Epargne Pierre 4ème trimestre 2023"
   Montant: 7356.24€
   Type: CREDIT

✅ Événement #1259: REVENU_SCPI
   Libellé: "SCPI EPARGNE PIERRE DISTRIBUTION 4EME TRIM 2023 SC"
   Montant: 7356.24€
   Type: CREDIT
```

**Doublon** : 3 événements pour 1 opération réelle !

---

### 2. Revenus SCPI T1 2024 (6346.56€)

**Source 1 - Relevé** :
```
✅ Événement #1188: REVENU_SCPI
   Libellé: "VIR SEPA SCPI EPARGNE PIERRE LIBELLE SCPI EPARGNE"
   Montant: 6346.56€
```

**Source 2 - Avis** :
```
✅ Événement #1260: REVENU_SCPI
   Libellé: "SCPI EPARGNE PIERRE DISTRIBUTION 1ER TRIM. 2024 SC"
   Montant: 6346.56€
```

**Doublon** : 2 événements pour 1 opération réelle

---

### 3. Revenus SCPI T2 2024 (6346.56€)

**Source 1 - Relevé** :
```
✅ Événement #1220: REVENU_SCPI
   Libellé: "VIR SEPA SCPI EPARGNE PIERRE LIBELLE:SCPI EPARGNE"
   Montant: 6346.56€
```

**Source 2 - Avis** :
```
✅ Événement #1262: REVENU_SCPI
   Libellé: "SCPI EPARGNE PIERRE DISTRIBUTION 2EME TRIM.2024 SC"
   Montant: 6346.56€
```

**Doublon** : 2 événements pour 1 opération réelle

---

### 4. Distribution Capital SCPI (601€)

**Source 1 - Relevé** :
```
✅ Événement #1189: DISTRIBUTION_CAPITAL_SCPI
   Libellé: "VIR SEPA SCPI EPARGNE PIERRE LIBELLE SCPI EPARGNE"
   Montant: 601.00€
```

**Source 2 - Avis** :
```
✅ Événement #1261: DISTRIBUTION_CAPITAL_SCPI
   Libellé: "SCPI EPARGNE PIERRE DISTRIB CAPITAL NUMERO 01 SCI"
   Montant: 601.00€
```

**Doublon** : 2 événements pour 1 opération réelle

---

### 5. Apports Associés (15 000€)

**Apport 500€** :
```
Source 1 - Relevé:
✅ Événement #1207: APPORT_ASSOCIE (500€)
   Libellé: "VIR SEPA MONSIEUR ULRIK BERGSTEN LIBELLE:Apport CC"

Source 2 - Avis:
✅ Événement #1268: APPORT_ASSOCIE (500€)
   Libellé: "Apport CC UB VIREMENT MONSIEUR ULRIK BERGSTE"
```

**Apport 4500€** :
```
Source 1 - Relevé:
✅ Événement #1228: APPORT_ASSOCIE (4500€)
   Libellé: "VIR SEPA MONSIEUR ULRIK BERGSTEN LIBELLE:Apport En"

Source 2 - Avis:
✅ Événement #1269: APPORT_ASSOCIE (4500€)
   Libellé: "Apport En Compte Courant VIREMENT MONSIEUR ULRIK B"
```

**Apport 5000€ #1** :
```
Source 1 - Relevé:
✅ Événement #1231: APPORT_ASSOCIE (5000€)
   Libellé: "VIR SEPA MONSIEUR ULRIK BERGSTEN LIBELLE:Apport En"

Source 2 - Avis:
✅ Événement #1270: APPORT_ASSOCIE (5000€)
   Libellé: "Apport En Compte Courant VIREMENT MONSIEUR ULRIK B"
```

**Apport 5000€ #2** :
```
Source 1 - Relevé:
✅ Événement #1233: APPORT_ASSOCIE (5000€)
   Libellé: "VIR SEPA MONSIEUR ULRIK BERGSTEN LIBELLE:Apport En"

Source 2 - Avis:
✅ Événement #1271: APPORT_ASSOCIE (5000€)
   Libellé: "Apport En Compte Courant VIREMENT MONSIEUR ULRIK B"
```

**Doublon** : 8 événements pour 4 opérations réelles

---

## 📊 Récapitulatif Doublons

| Type | Montant Réel | Événements Créés | Doublons |
|------|--------------|------------------|----------|
| SCPI T4 2023 | 7 356.24€ | 3 | +2 |
| SCPI T1 2024 | 6 346.56€ | 2 | +1 |
| SCPI T2 2024 | 6 346.56€ | 2 | +1 |
| SCPI Capital | 601.00€ | 2 | +1 |
| Apport 500€ | 500.00€ | 2 | +1 |
| Apport 4500€ | 4 500.00€ | 2 | +1 |
| Apport 5000€ #1 | 5 000.00€ | 2 | +1 |
| Apport 5000€ #2 | 5 000.00€ | 2 | +1 |
| **TOTAL** | **35 650.20€** | **17 événements** | **+9 doublons** |

**Impact comptable** : 35 650€ comptés 2 fois = **+35 650€ d'erreur**

---

## 🔍 Cause Racine

### Fingerprint Actuel

```python
fingerprint = MD5(date + libelle_normalise + montant + type_operation)
```

**Problème** : Les libellés varient entre relevé et avis d'opération

**Exemple** :
- Relevé : `vir sepa scpi epargne pierre libelle scpi epargne`
- Avis : `scpi epargne pierre distribution 1er trim 2024 sc`
- → **Fingerprints différents** → Pas détecté comme doublon

---

## 💡 Solution Proposée

### Fingerprint Intelligent par Type

Pour certains types d'événements (SCPI, Apports), utiliser un **fingerprint simplifié** :

```python
# Types nécessitant déduplication simplifiée
TYPES_DEDUPE_SIMPLE = [
    'REVENU_SCPI',
    'DISTRIBUTION_CAPITAL_SCPI',
    'ACHAT_SCPI',
    'APPORT_ASSOCIE'
]

def calculer_fingerprint(operation, type_detecte=None):
    date = operation['date_operation']
    montant = operation['montant']
    type_op = operation['type_operation']

    # Pour SCPI et Apports : fingerprint sans libellé
    if type_detecte in TYPES_DEDUPE_SIMPLE:
        fingerprint = f"{date}_{montant}_{type_op}_{type_detecte}"
    else:
        # Pour autres : fingerprint avec libellé (comportement actuel)
        libelle = operation['libelle_normalise']
        fingerprint = f"{date}_{libelle}_{montant}_{type_op}"

    return hashlib.md5(fingerprint.encode()).hexdigest()
```

### Avantages

✅ Détecte les vrais doublons SCPI/Apports (même montant + date + type)
✅ Conserve la précision pour les autres types (libellé compte)
✅ Simple à implémenter

### Risques

⚠️ Si 2 apports du même montant le même jour → Considérés comme doublon
- Solution : Garder les 2 si montants identiques le même jour sont fréquents
- Ou : Vérifier manuellement ces cas rares

---

## 🎯 Plan d'Action

1. ✅ Analyser les doublons (ce fichier)
2. ⏳ Modifier `detection_doublons.py` avec fingerprint intelligent
3. ⏳ Modifier `extracteur_pdf.py` pour passer le type détecté
4. ⏳ Tester avec T1-T3 2024
5. ⏳ Vérifier : 9 événements en moins (pas de doublons)

---

**Version** : 1.0
**Date** : 12 novembre 2025
**Impact** : 35 650€ comptés 2 fois (9 doublons)
