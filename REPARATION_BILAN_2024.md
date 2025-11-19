# Réparation Bilan d'Ouverture 2024 - Cutoffs + Extournes

**Objectif** : Compléter le bilan d'ouverture 2024 avec les cutoffs intérêts manquants et générer toutes les extournes

**Transition** : 31/12/2023 → 01/01/2024

**Date** : 19 novembre 2025

---

## 📊 État Actuel du Bilan d'Ouverture 2024

### Cutoffs Existants (SANS extournes)

| Compte | Type | Montant | Date Cutoff | Extourne ? |
|--------|------|---------|-------------|------------|
| 4181 | Produits à recevoir SCPI T4 | 7 356€ | 31/12/2023 | ❌ NON |
| 4081 | Factures non parvenues (honoraires) | 653€ | 31/12/2023 | ❌ NON |
| 1688 | Intérêts courus | **MANQUANT** | 31/12/2023 | ❌ N/A |

### Problèmes Identifiés

1. ✅ Cutoffs 4181 et 4081 créés (31/12/2023) mais **pas d'extournes (01/01/2024)**
2. ❌ Cutoff intérêts 1688 **complètement manquant** (31/12/2023)
3. ❌ Bilan d'ouverture 2024 incomplet

---

## 🔧 Procédure de Réparation (2 Étapes)

### Étape 1 : Créer Cutoff Intérêts 2023

**Script** : `cutoff_extourne_interets.py`

**Action** : Calcule les intérêts courus du 12/12/2023 au 31/12/2023 pour les 2 prêts et crée cutoff + extourne

**Commande** :
```bash
python cutoff_extourne_interets.py --exercice 2023 --execute
```

**Résultat attendu** :
```
📅 Calcul intérêts courus au 2023-12-31

  💰 Prêt LCL (BRM0911AH...)
     Taux annuel : 2.5000%
     Dernière échéance : 2023-12-12
     Capital restant : ~250 000,00€
     Jours courus : 19
     ✅ Intérêts courus : ~325€

  💰 Prêt INVESTIMUR (BRLZE11AQ...)
     Taux annuel : 2.0000%
     Dernière échéance : 2023-12-12
     Capital restant : ~236 000,00€
     Jours courus : 19
     ✅ Intérêts courus : ~246€

📋 PROPOSITIONS DE CUTOFF
  Intérêts courus prêt LCL: ~325€ + extourne
    2023-12-31 : Débit 661 / Crédit 1688 : ~325€
    2024-01-01 : Débit 1688 / Crédit 661 : ~325€

  Intérêts courus prêt INVESTIMUR: ~246€ + extourne
    2023-12-31 : Débit 661 / Crédit 1688 : ~246€
    2024-01-01 : Débit 1688 / Crédit 661 : ~246€

  TOTAL INTÉRÊTS COURUS : ~571€
```

**Vérification** :
```sql
SELECT
    date_ecriture,
    libelle_ecriture,
    compte_debit,
    compte_credit,
    montant
FROM ecritures_comptables
WHERE type_ecriture IN ('CUTOFF_INTERETS_COURUS', 'EXTOURNE_CUTOFF')
  AND EXTRACT(YEAR FROM date_ecriture) IN (2023, 2024)
ORDER BY date_ecriture;
```

---

### Étape 2 : Générer Extournes Manquantes

**Script** : `generateur_extournes.py`

**Action** : Génère les extournes 01/01/2024 pour les cutoffs 4181 et 4081 existants (31/12/2023)

**Commande** :
```bash
# D'abord dry-run pour vérifier
python generateur_extournes.py --exercice 2023

# Puis exécution réelle
python generateur_extournes.py --exercice 2023 --execute
```

**Résultat attendu** :
```
═══════════════════════════════════════════════════════════════
🔄 GÉNÉRATEUR D'EXTOURNES - Exercice 2023
═══════════════════════════════════════════════════════════════

📊 Cutoffs trouvés (SANS extourne) :

  1. CUTOFF_PRODUIT_A_RECEVOIR (31/12/2023)
     Débit 4181 / Crédit 761 : 7 356,00€
     → Extourne à créer : 01/01/2024

  2. CUTOFF_HONORAIRES (31/12/2023)
     Débit 6226 / Crédit 4081 : 653,00€
     → Extourne à créer : 01/01/2024

─────────────────────────────────────────────────────────────
TOTAL : 2 extournes à créer
═══════════════════════════════════════════════════════════════

✅ 2 extournes créées avec succès
```

**Vérification** :
```sql
SELECT
    date_ecriture,
    libelle_ecriture,
    compte_debit,
    compte_credit,
    montant,
    type_ecriture
FROM ecritures_comptables
WHERE type_ecriture = 'EXTOURNE_CUTOFF'
  AND date_ecriture = '2024-01-01'
ORDER BY id;
```

---

## ✅ Résultat Final Attendu

### Bilan au 31/12/2023 (Exercice 2023)

**Comptes d'attente (ACTIF)** :
```
4181 (Produits à recevoir)    : 7 356,00€  (DÉBIT)
```

**Comptes d'attente (PASSIF)** :
```
4081 (Factures non parvenues) :   653,00€  (CRÉDIT)
1688 (Intérêts courus)         :   ~571€   (CRÉDIT)
```

**Produits** :
```
761 (Produits participations)  : 7 356,00€  (CRÉDIT)
```

**Charges** :
```
6226 (Honoraires)              :   653,00€  (DÉBIT)
661 (Intérêts)                 :   ~571€   (DÉBIT)
```

### Écritures 01/01/2024 (Exercice 2024)

**Extournes automatiques** :
```
Type EXTOURNE_CUTOFF :
  - Débit 761 / Crédit 4181  : 7 356,00€  (annule produit à recevoir)
  - Débit 4081 / Crédit 6226 :   653,00€  (annule honoraires à payer)
  - Débit 1688 / Crédit 661  :   ~571€    (annule intérêts courus - 2 écritures)
```

---

## 📋 Checklist de Vérification

Après exécution des 2 scripts :

- [ ] 4 cutoffs au 31/12/2023 (2 intérêts + 1 revenus + 1 honoraires)
- [ ] 4 extournes au 01/01/2024 (correspondant aux 4 cutoffs)
- [ ] Compte 1688 présent au bilan 31/12/2023 (intérêts courus)
- [ ] Bilan 31/12/2023 équilibré
- [ ] Compte de résultat 2023 incluant intérêts courus

---

## 🚨 Important

**Ordre d'exécution** :
1. ✅ **D'ABORD** : `cutoff_extourne_interets.py` (crée cutoff + extourne intérêts)
2. ✅ **ENSUITE** : `generateur_extournes.py` (crée extournes pour cutoffs existants)

**Pourquoi cet ordre ?**
- Si on inverse, le générateur ne trouvera pas le cutoff intérêts (il n'existe pas encore)
- Le script intérêts crée DÉJÀ son extourne, donc le générateur ne le traitera pas

**Sauvegardes** :
- Faire une sauvegarde BD avant chaque script : `python sauvegarder_base.py`
- En cas de problème, restaurer depuis `backups/`

---

## 📖 Logs Attendus

### Script 1 : cutoff_extourne_interets.py
```
[SUCCESS] 4 écritures créées (2 cutoffs + 2 extournes)
[INFO] Exercice 2023 : +~571€ de charges intérêts
[INFO] Exercice 2024 : -~571€ de charges intérêts (extourne)
```

### Script 2 : generateur_extournes.py
```
[SUCCESS] 2 extournes créées
[INFO] Cutoff 4181 : extourne créée (7356€)
[INFO] Cutoff 4081 : extourne créée (653€)
[SKIP] Cutoff 1688 : extourne déjà existante (x2)
```

---

**Version** : 1.0 - 19 novembre 2025
**Auteur** : _Head.Soeurise avec Claude Code
