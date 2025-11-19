# Système Cutoff Complet par Extourne

**Système unifié pour tous les cutoffs de fin d'année**

---

## 🎯 Principe Général de l'Extourne

L'extourne est une technique comptable qui permet de :
1. **Enregistrer** une charge/produit estimé en fin d'année N (cutoff)
2. **Annuler automatiquement** cette écriture au 01/01/N+1 (extourne)
3. **Enregistrer** la charge/produit réel quand il arrive en N+1

**Avantage** : Pas de rapprochement complexe créance ↔ paiement !

---

## 📊 Les 3 Types de Cutoffs SCI Soeurise

### 1. Revenus SCPI à Recevoir (761 / 4181)

**Contexte** : Distribution T4 gagnée en année N, payée en janvier N+1

**Workflow** :

**Janvier N+1** - Email Ulrik :
```
De: ulrik.c.s.be@gmail.com
Objet: SCPI Épargne Pierre - Distribution T4 2024
Corps: Montant: 7 356,00 € sera versé le 29/01/2025
```

**31/12/N** - Cutoff (créé rétroactivement) :
```
Débit  4181 (Produits à recevoir)      7 356€
Crédit  761 (Produits participations)  7 356€
Type: CUTOFF_PRODUIT_A_RECEVOIR
```

**01/01/N+1** - Extourne automatique :
```
Débit   761  7 356€
Crédit 4181  7 356€
Type: EXTOURNE_CUTOFF
```

**29/01/N+1** - Paiement réel :
```
Débit  512 (Banque)  7 356€
Crédit  761          7 356€
Type: DISTRIBUTION_SCPI
```

**Résultat** :
- Exercice N : Produit 761 = **+7 356€** ✅
- Exercice N+1 : Produit 761 = **0€** (-7356 + 7356)
- Banque N+1 : **+7 356€** ✅

**Détecteur** : `DetecteurAnnonceProduitARecevoir` (detecteurs_evenements.py)

---

### 2. Honoraires Comptables à Payer (6226 / 4081)

**Contexte** : Honoraires exercice N facturés en mars N+1

**Workflow** :

**Décembre N** - Email Ulrik ou estimation :
```
De: ulrik.c.s.be@gmail.com
Objet: Cutoff honoraires comptables 2024
Corps: Provisionner honoraires 2024: 1 200,00 €
```

**31/12/N** - Cutoff :
```
Débit  6226 (Honoraires)                1 200€
Crédit 4081 (Factures non parvenues)    1 200€
Type: CUTOFF_HONORAIRES
```

**01/01/N+1** - Extourne automatique :
```
Débit  4081  1 200€
Crédit 6226  1 200€
Type: EXTOURNE_CUTOFF
```

**Mars N+1** - Facture réelle :
```
Débit  6226  1 250€  (facture réelle)
Crédit  512  1 250€
Type: HONORAIRES_COMPTABLE
```

**Résultat** :
- Exercice N : Charge 6226 = **1 200€** (estimation)
- Exercice N+1 : Charge 6226 = **50€** (écart)
- Total correct sur 2 ans : **1 250€** ✅

**Détecteur** : `DetecteurAnnonceHonorairesARegler` (cutoff_extourne_honoraires.py)

---

### 3. Intérêts Courus Non Échus (661 / 1688)

**Contexte** : Intérêts courent quotidiennement, payés mensuellement

**Exemple** :
- Dernière échéance 2024 : 12/12/2024 (intérêts 12/11 → 11/12)
- Fin d'année : 31/12/2024
- **Intérêts courus non échus** : 12/12 → 31/12 (20 jours)

**Workflow** :

**31/12/N** - Calcul automatique :
```
Formule: Capital restant × Taux annuel × (Nb jours / 365)
Exemple: 486 000€ × 2.5% × (20/365) = 666.58€
```

**31/12/N** - Cutoff :
```
Débit   661 (Charges d'intérêts)    666.58€
Crédit 1688 (Intérêts courus)       666.58€
Type: CUTOFF_INTERETS_COURUS
```

**01/01/N+1** - Extourne automatique :
```
Débit  1688  666.58€
Crédit  661  666.58€
Type: EXTOURNE_CUTOFF
```

**12/01/N+1** - Échéance réelle :
```
Débit   661  1 020.00€  (intérêts mois complet)
Crédit  512  1 020.00€
Type: INTERET_PRET
```

**Résultat** :
- Exercice N : Charge 661 = **666.58€** (20 jours)
- Exercice N+1 : Charge 661 = **353.42€** (1020 - 666.58)
- Total mois : **1 020€** ✅

**Calculateur** : `CalculateurInteretsCourus` (cutoff_extourne_interets.py)

---

## 🔧 Outils Disponibles

### Détecteurs (Création Cutoffs)

| Type | Classe | Fichier | Déclencheur |
|------|--------|---------|-------------|
| Revenus SCPI | `DetecteurAnnonceProduitARecevoir` | detecteurs_evenements.py | Email Ulrik |
| Honoraires | `DetecteurAnnonceHonorairesARegler` | cutoff_extourne_honoraires.py | Email Ulrik/estimation |
| Intérêts | `CalculateurInteretsCourus` | cutoff_extourne_interets.py | Calcul automatique |

### Générateur d'Extournes (Unique pour tous)

**Fichier** : `generateur_extournes.py`

**Supporte** :
- `CUTOFF_PRODUIT_A_RECEVOIR`
- `CUTOFF_HONORAIRES`
- `CUTOFF_INTERETS_COURUS`

**Utilisation** :
```bash
# Simulation (dry-run)
python generateur_extournes.py --exercice 2024

# Exécution réelle
python generateur_extournes.py --exercice 2024 --execute

# Tous les exercices cloturés
python generateur_extournes.py --tous --execute
```

---

## 📅 Timeline Annuelle Type

**Décembre N** :
1. ✅ Créer cutoff honoraires (estimation)
2. ✅ Calculer intérêts courus au 31/12

**31/12/N** :
- Écritures de cutoff datées 31/12/N enregistrées

**Janvier N+1** :
1. ✅ Email Ulrik annonce distribution SCPI T4 → Cutoff créé rétroactivement
2. ✅ Générer extournes au 01/01/N+1 : `python generateur_extournes.py --exercice N --execute`

**Année N+1** :
- Paiements réels arrivent normalement
- Charges/produits N+1 = écarts avec estimations

---

## 🎯 Comparaison vs Système avec Rapprochement

| Critère | Avec Rapprocheur | Avec Extourne |
|---------|------------------|---------------|
| **Complexité code** | ⚠️ ~500 lignes (matching intelligent) | ✅ ~200 lignes (inversion mécanique) |
| **Maintenance** | ⚠️ Difficile (logique complexe) | ✅ Simple (standard comptable) |
| **Robustesse** | ⚠️ Si montants ≠, ajustement complexe | ✅ Fonctionne toujours |
| **Audit trail** | ⚠️ Créance → Apurement → Ajustement | ✅ Estimation → Annulation → Réel |
| **Performance** | ⚠️ Requêtes de recherche | ✅ Simple inversion |

---

## ✅ Avantages du Système Unifié

1. **Simplicité** : Un seul générateur pour tous les types
2. **Standard** : Pratique comptable éprouvée (extourne très courante)
3. **Audit** : Trail clair estimation → extourne → réel
4. **Robuste** : Fonctionne même si montants différents
5. **Automatisable** : Génération extournes 100% automatique

---

## 📊 Comptes Utilisés

| Type Cutoff | Charge/Produit | Compte d'Attente | Commentaire |
|-------------|----------------|------------------|-------------|
| Revenus SCPI | 761 (Produits) | 4181 (Produits à recevoir) | ACTIF débiteur |
| Honoraires | 6226 (Charges) | 4081 (Factures non parvenues) | PASSIF créditeur |
| Intérêts courus | 661 (Charges) | 1688 (Intérêts courus) | PASSIF créditeur |

---

## 🔄 Flux Technique Complet

```
┌─────────────────────────────────────────────────────────┐
│ FIN DÉCEMBRE N - Préparation Cutoffs                    │
│ - Email Ulrik honoraires (estimation)                   │
│ - Calcul automatique intérêts courus                    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 31/12/N - Écritures Cutoff (datées 31/12/N)            │
│ - CUTOFF_HONORAIRES : 6226 → 4081                      │
│ - CUTOFF_INTERETS_COURUS : 661 → 1688                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ JANVIER N+1 - Email Ulrik Revenus SCPI                 │
│ → Création RÉTROACTIVE CUTOFF_PRODUIT_A_RECEVOIR       │
│   Daté 31/12/N : 4181 → 761                            │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ DÉBUT JANVIER N+1 - Génération Extournes               │
│ python generateur_extournes.py --exercice N --execute  │
│                                                          │
│ → Crée 3 écritures datées 01/01/N+1 :                  │
│   - EXTOURNE revenus : 761 → 4181                      │
│   - EXTOURNE honoraires : 4081 → 6226                  │
│   - EXTOURNE intérêts : 1688 → 661                     │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ ANNÉE N+1 - Paiements Réels                            │
│ - Janvier : Distribution SCPI (512 → 761)              │
│ - Janvier : Échéance prêt (661 → 512)                  │
│ - Mars : Facture honoraires (6226 → 512)               │
└─────────────────────────────────────────────────────────┘
```

---

## 📝 Notes Importantes

1. **Ordre d'exécution** :
   - Cutoffs honoraires/intérêts : Avant clôture exercice N
   - Cutoff revenus SCPI : Janvier N+1 (rétroactif)
   - Extournes : Début janvier N+1 (après cutoff revenus)

2. **Sécurité** :
   - Seul Ulrik peut créer cutoffs (email ulrik.c.s.be@gmail.com)
   - Générateur extournes : dry-run par défaut

3. **Écarts** :
   - Montant réel ≠ estimation → Écart comptabilisé en N+1
   - Acceptable comptablement (principe de prudence)

---

**Version** : 1.0 - 18 novembre 2025
**Auteur** : _Head.Soeurise avec Claude Code
