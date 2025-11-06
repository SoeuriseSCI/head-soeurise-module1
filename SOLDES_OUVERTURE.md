# 🔍 Filtre des Soldes d'Ouverture

**Date**: 05 novembre 2025
**Auteur**: Claude Code Assistant
**Contexte**: Exclusion des "ANCIEN SOLDE" du traitement comptable

---

## 📋 Problématique

Dans les relevés bancaires, l'opération **"ANCIEN SOLDE"** apparaît au début de chaque mois comme solde d'ouverture. Ces lignes ne sont **pas des transactions réelles** mais des reports de solde du mois précédent.

### Exemples détectés (118 événements extraits)
```
#121 | 2023-12-04 | ANCIEN SOLDE              | 3612.05€ CREDIT
#131 | 2024-01-04 | ANCIEN SOLDE              | 1997.28€ CREDIT
#141 | 2024-02-02 | ANCIEN SOLDE              | 5256.94€ CREDIT
#152 | 2024-03-04 | ANCIEN SOLDE              | 3731.32€ CREDIT
...
```

### Impact comptable
Comptabiliser ces soldes doublerait les montants car ce sont des **reports**, pas des flux réels.

---

## ✅ Solution Implémentée

### 1. Nouveau type d'événement
**Fichier**: `module2_workflow_v2.py`

Ajout du type `SOLDE_OUVERTURE` dans l'enum:
```python
class TypeEvenement(Enum):
    EVENEMENT_SIMPLE = "EVENEMENT_SIMPLE"
    INIT_BILAN_2023 = "INIT_BILAN_2023"
    CLOTURE_EXERCICE = "CLOTURE_EXERCICE"
    PRET_IMMOBILIER = "PRET_IMMOBILIER"
    RELEVE_BANCAIRE = "RELEVE_BANCAIRE"
    SOLDE_OUVERTURE = "SOLDE_OUVERTURE"  # ← Nouveau
    UNKNOWN = "UNKNOWN"
```

### 2. Détection dans l'extracteur PDF
**Fichier**: `extracteur_pdf.py`

Flag `est_solde_ouverture` ajouté lors de l'extraction:
```python
libelle_norm = op['libelle'].upper().strip()
est_solde_ouverture = any(pattern in libelle_norm for pattern in [
    'ANCIEN SOLDE',
    'SOLDE REPORTE',
    'SOLDE REPORTÉ',
    'SOLDE PRECEDENT',
    'SOLDE PRÉCÉDENT',
    'REPORT SOLDE'
])
```

### 3. Classification automatique
**Fichier**: `gestionnaire_evenements.py`

Détecteur de type mis à jour:
```python
# Solde d'ouverture (non comptabilisable)
if any(pattern in libelle_norm for pattern in [
    'ancien solde', 'solde reporte', 'solde precedent', 'report solde'
]):
    type_evt = 'SOLDE_OUVERTURE'
```

### 4. Exclusion du workflow comptable
**Fichier**: `workflow_evenements.py`

Filtre dans `generer_propositions()`:
```python
# EXCLURE les soldes d'ouverture (non comptabilisables)
if evenement['type_evenement'] == 'SOLDE_OUVERTURE':
    print(f"⏭️  Événement #{evt_id} ignoré (SOLDE_OUVERTURE - non comptabilisable)")
    continue
```

---

## 🚀 Mise en Production

### Étape 1: Marquer les événements existants
Sur **Render Shell**, exécuter:
```bash
python marquer_soldes_ouverture.py
```

Résultat attendu:
```
🔍 10 soldes d'ouverture détectés:
  #121 | 2023-12-04 | ANCIEN SOLDE | 3612.05€
  #131 | 2024-01-04 | ANCIEN SOLDE | 1997.28€
  ...

✅ 10 événements marqués comme SOLDE_OUVERTURE

📊 Répartition par type:
  REMBOURSEMENT_PRET      :  40
  REVENU_SCPI             :   8
  SOLDE_OUVERTURE         :  10  ← Nouveau
  (non détecté)           :  60
```

### Étape 2: Vérifier l'exclusion
```bash
python workflow_evenements.py --stats
```

Les événements de type `SOLDE_OUVERTURE` ne doivent **pas** apparaître dans les propositions comptables.

---

## 📊 Impact

### Avant
- ✅ 118 événements créés
- ❌ 10 soldes d'ouverture comptabilisables (erreur)
- ⚠️  Risque de doublons dans les écritures

### Après
- ✅ 118 événements créés
- ✅ 10 soldes d'ouverture **exclus** automatiquement
- ✅ 108 événements comptabilisables (40 REMBOURSEMENT_PRET + 8 REVENU_SCPI + 60 non détectés)
- 🛡️  Aucun risque de double comptabilisation

---

## 🔮 Prochaines Étapes

1. ✅ **Automatique**: Tous les nouveaux PDFs avec "ANCIEN SOLDE" seront filtrés
2. 🔄 **Phase 2**: Détecteurs additionnels pour les 60 événements non classifiés:
   - Frais bancaires (tenue de compte)
   - Honoraires comptable
   - Achats ETF/Actions (Degiro, Amazon)
   - Apports Ulrik

---

**Version**: 1.0
**Statut**: ✅ Prêt pour production
