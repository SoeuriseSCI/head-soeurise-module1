# Workflow Cutoff par Extourne - Revenus SCPI

## 🎯 Principe de l'Extourne

L'extourne est une technique comptable standard qui consiste à :
1. Enregistrer une charge/produit estimé en fin d'année N
2. **Annuler automatiquement** cette écriture au 01/01/N+1
3. Enregistrer la charge/produit réel quand il arrive en N+1

**Avantage** : Pas besoin de rapprochement complexe !

---

## 📅 Timeline : Exemple Distribution SCPI T4 2024

### Janvier 2025 - Ulrik reçoit notification SCPI

**SCPI envoie à Ulrik** (pas à _Head) :
- Distribution T4 2024 : **7 356,00 €**
- Date de versement : **29 janvier 2025**

### Janvier 2025 - Ulrik envoie email à _Head

**Email d'Ulrik** à u6334452013@gmail.com :

```
De : ulrik.c.s.be@gmail.com
À : u6334452013@gmail.com
Objet : SCPI Épargne Pierre - Distribution T4 2024

Distribution T4 2024 - SCPI Épargne Pierre

Montant : 7 356,00 €
Date versement : 29 janvier 2025

Cette information permet à _Head de créer le cut-off comptable
pour clôture exercice 2024.
```

### Janvier 2025 - _Head crée écritures DATÉES 31/12/2024

**Écritures créées RÉTROACTIVEMENT** (datées 31/12/2024) :

```
Date : 31/12/2024
Libellé : Cutoff 2024 - Distribution T4 SCPI Épargne Pierre

Débit  4181 (Produits à recevoir)      7 356,00 €
Crédit  761 (Produits participations)  7 356,00 €

Type : CUTOFF_PRODUIT_A_RECEVOIR
Extourne : OUI ← Marqueur important
```

**Effet sur bilan 2024** :
- ACTIF : +7 356€ (compte 4181)
- PRODUITS : +7 356€ (compte 761)
- Résultat 2024 : +7 356€ ✅

---

### 01/01/2025 - EXTOURNE AUTOMATIQUE

**_Head génère automatiquement** l'extourne :

```
Date : 01/01/2025
Libellé : Extourne - Cutoff 2024 - Distribution T4 SCPI Épargne Pierre

Débit   761 (Produits participations)  7 356,00 €
Crédit 4181 (Produits à recevoir)      7 356,00 €

Type : EXTOURNE_CUTOFF
```

**Effet sur comptes 2025** (temporaire) :
- Compte 4181 : **0€** (annulé)
- Compte 761 : **-7 356€** (négatif temporairement)

---

### 29/01/2025 - Paiement Réel Arrive

**Email relevé bancaire** → Détection automatique :

```
Date : 29/01/2025
Libellé : Distribution T4 SCPI Épargne Pierre

Débit  512 (Banque)                    7 356,00 €
Crédit  761 (Produits participations)  7 356,00 €

Type : DISTRIBUTION_SCPI
```

**Effet final sur comptes 2025** :
- Compte 4181 : **0€** (soldé)
- Compte 761 : **0€** (-7356 + 7356 = 0)
- Compte 512 : **+7 356€** ✅

**Résultat** :
- Exercice 2024 : Produit 761 comptabilisé ✅
- Exercice 2025 : Produit 761 = 0 (extourne annule) ✅
- Banque 2025 : +7 356€ ✅

---

## 🔧 Implémentation Technique

### 1. Détection Email Ulrik

**Classe** : `DetecteurAnnonceProduitARecevoir`

**Critères de détection** :
- Émetteur : **ulrik.c.s.be@gmail.com** (CRITIQUE)
- Objet : contient "Distribution" + "T4"
- Corps : contient "sera versé" + montant en €

**Extraction** :
- Année (ex: 2024)
- Montant (ex: 7 356,00)
- Date paiement (ex: 29/01/2025)
- Nom SCPI (ex: Épargne Pierre)

### 2. Génération Écritures Cutoff

**Type** : `CUTOFF_PRODUIT_A_RECEVOIR`
**Date** : 31/12/[année]
**Marqueur** : `extourne: True`

```python
{
    'date_ecriture': date(2024, 12, 31),
    'compte_debit': '4181',
    'compte_credit': '761',
    'montant': 7356.00,
    'type_ecriture': 'CUTOFF_PRODUIT_A_RECEVOIR',
    'extourne': True  # ← Important !
}
```

### 3. Génération Extournes Automatiques

**Classe** : `GenerateurExtournes`

**Quand** : À la clôture de l'exercice N ou au début N+1

**Recherche** :
- Toutes écritures exercice N
- Type = `CUTOFF_PRODUIT_A_RECEVOIR`
- Marqueur `extourne = True`

**Génère** : Écriture inverse au 01/01/N+1

```python
{
    'date_ecriture': date(2025, 1, 1),
    'compte_debit': '761',      # ← INVERSION
    'compte_credit': '4181',    # ← INVERSION
    'montant': 7356.00,
    'type_ecriture': 'EXTOURNE_CUTOFF'
}
```

### 4. Détection Paiement Réel

**Classe** : `DetecteurDistributionSCPI` (existante)

**PAS DE MODIFICATION** : Continue de fonctionner normalement
- Détecte paiement sur relevé bancaire
- Crée écriture : Débit 512 / Crédit 761
- **Plus besoin de chercher créance** (l'extourne a déjà tout annulé)

---

## ✅ Avantages vs Système Précédent

| Critère | Avec Rapprocheur | Avec Extourne |
|---------|------------------|---------------|
| Complexité code | ⚠️ Élevée (rapprochement intelligent) | ✅ Simple (inversion mécanique) |
| Robustesse | ⚠️ Si montants différents, besoin ajustement | ✅ Fonctionne toujours |
| Standard comptable | ✅ Oui (provisions) | ✅ Oui (extourne très courante) |
| Audit trail | ⚠️ Créance + apurement | ✅ Clair : estimation → annulation → réel |
| Maintenance | ⚠️ Beaucoup de code | ✅ Peu de code |

---

## 📊 Cas Spéciaux

### Cas 1 : Montant Réel ≠ Estimation

**31/12/2024** - Estimation 7 000€ :
```
Débit 4181  7000€
Crédit 761  7000€
```

**01/01/2025** - Extourne :
```
Débit 761   7000€
Crédit 4181 7000€
```

**29/01/2025** - Réel 7 356€ :
```
Débit 512  7356€
Crédit 761 7356€
```

**Résultat** :
- Exercice 2024 : Produit = **7 000€** (estimation)
- Exercice 2025 : Produit = **356€** (écart)
- **Pas de problème** ! L'écart est en 2025 (acceptable)

### Cas 2 : Pas de Paiement en 2025

Si le paiement n'arrive jamais :
- Exercice 2024 : Produit = **7 356€** (peut-être optimiste)
- Exercice 2025 : Produit = **-7 356€** (correction)
- **Audit trail clair** : On voit l'erreur d'estimation

---

## 🔄 Flux Complet

```
┌─────────────────────────────────────────────────────────────┐
│ JANVIER 2025 - Email Ulrik                                  │
│ "Distribution T4 2024 : 7356€"                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ _Head crée écritures DATÉES 31/12/2024                     │
│ Débit 4181 / Crédit 761 : 7356€                            │
│ Type: CUTOFF_PRODUIT_A_RECEVOIR                            │
│ Marqueur: extourne = True                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ CLÔTURE 2024 ou DÉBUT 2025                                  │
│ GenerateurExtournes cherche écritures marquées              │
│ → Génère extourne au 01/01/2025                            │
│ Débit 761 / Crédit 4181 : 7356€                            │
│ Type: EXTOURNE_CUTOFF                                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 29/01/2025 - Paiement arrive (relevé bancaire)             │
│ DetecteurDistributionSCPI détecte                           │
│ → Crée écriture normale                                    │
│ Débit 512 / Crédit 761 : 7356€                             │
│ Type: DISTRIBUTION_SCPI                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 💾 Modification Base de Données

**Option A** : Ajouter colonne `extourne` (BOOLEAN) à `ecritures_comptables`

```sql
ALTER TABLE ecritures_comptables
ADD COLUMN extourne BOOLEAN DEFAULT FALSE;
```

**Option B** : Utiliser `type_ecriture` comme marqueur (plus simple)
- Si `type_ecriture = 'CUTOFF_PRODUIT_A_RECEVOIR'` → À extourn er

**Recommandation** : **Option B** (plus simple, pas de migration)

---

## 🎯 Prochaines Étapes

1. ✅ Créer `cutoff_extourne_revenus.py` (FAIT)
2. ⏳ Intégrer dans `detecteurs_evenements.py`
3. ⏳ Créer tâche planifiée pour générer extournes au 01/01
4. ⏳ Tester avec email réel Ulrik
5. ⏳ Documenter dans `CLAUDE.md`

---

**Version** : 1.0 - 18 novembre 2025
**Auteur** : _Head.Soeurise avec Claude Code
