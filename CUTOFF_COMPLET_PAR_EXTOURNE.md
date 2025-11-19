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
Objet: SCPI Épargne Pierre - Distribution T4 2023
Corps: Montant: 7 356,00 € sera versé le 29/01/2024
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
Objet: Cutoff honoraires comptables 2023
Corps: Provisionner honoraires 2023: 1 200,00 €
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
- Dernière échéance 2023 : 12/12/2023 (intérêts 12/11 → 11/12)
- Fin d'année : 31/12/2023
- **Intérêts courus non échus** : 12/12 → 31/12 (19 jours)

**Workflow** :

**Janvier N+1** - Première échéance de prêt détectée :
```
→ DetecteurRemboursementPret DÉCLENCHE AUTOMATIQUEMENT :
  - Vérifie si cutoff intérêts N existe déjà
  - Si NON : Calcule intérêts courus pour les 2 prêts
  - Crée cutoff 31/12/N + extourne 01/01/N+1 DANS LA FOULÉE
```

**31/12/N** - Cutoff (créé rétroactivement en janvier N+1) :
```
Formule: Capital restant × Taux annuel × (Nb jours / 365)
Exemple Prêt LCL: ~250 000€ × 2.5% × (19/365) = ~325€
Exemple Prêt INVESTIMUR: ~236 000€ × 2.0% × (19/365) = ~246€

Débit   661 (Charges d'intérêts)    ~325€  (Prêt LCL)
Crédit 1688 (Intérêts courus)       ~325€
Type: CUTOFF_INTERETS_COURUS

Débit   661 (Charges d'intérêts)    ~246€  (Prêt INVESTIMUR)
Crédit 1688 (Intérêts courus)       ~246€
Type: CUTOFF_INTERETS_COURUS
```

**01/01/N+1** - Extourne automatique (créée en même temps) :
```
Débit  1688  ~325€
Crédit  661  ~325€
Type: EXTOURNE_CUTOFF

Débit  1688  ~246€
Crédit  661  ~246€
Type: EXTOURNE_CUTOFF
```

**12/01/N+1** - Échéance réelle :
```
Débit   661  ~500€  (intérêts mois complet - LCL)
Crédit  512  ~500€
Type: INTERET_PRET

Débit   661  ~400€  (intérêts mois complet - INVESTIMUR)
Crédit  512  ~400€
Type: INTERET_PRET
```

**Résultat** :
- Exercice N : Charge 661 = **~571€** (19 jours, 2 prêts) ✅
- Exercice N+1 : Charge 661 = **~329€** (~900 - ~571)
- Total mois : **~900€** ✅

**Déclencheur** : `DetecteurRemboursementPret` (detecteurs_evenements.py)
**Calculateur** : `CalculateurInteretsCourus` (cutoff_extourne_interets.py)

---

## 🔧 Outils Disponibles

### Détecteurs (Création Cutoffs)

| Type | Classe | Fichier | Déclencheur |
|------|--------|---------|-------------|
| Revenus SCPI | `DetecteurAnnonceProduitARecevoir` | detecteurs_evenements.py | Email Ulrik (janvier N+1) |
| Honoraires | `DetecteurAnnonceHonorairesARegler` | cutoff_extourne_honoraires.py | Email Ulrik/estimation (décembre N) |
| Intérêts | `DetecteurRemboursementPret` | detecteurs_evenements.py | 1ère échéance janvier N+1 (automatique) |

**Note** : Tous les détecteurs créent **automatiquement** cutoff + extourne ensemble dans la foulée.

### Générateur d'Extournes (Utilitaire de Secours)

**Fichier** : `generateur_extournes.py`

**⚠️ Important** : Depuis la mise à jour, les détecteurs créent **automatiquement** cutoff + extourne ensemble dans la foulée de l'email/script.

**Ce script est un utilitaire de secours** pour :

**Cas d'Usage** :
1. **Réparation** : Générer extournes pour cutoffs créés SANS extourne (ancien code, migration)
2. **Migration** : Passage ancien système → nouveau système
3. **Vérification** : Dry-run pour voir quelles extournes seraient générées
4. **Cutoffs manuels** : Cutoffs créés manuellement en base (hors système détecteurs)

**Exemple situation actuelle (bilan d'ouverture 2024)** :
```
Situation : Bilan d'ouverture 2024 a déjà des cutoffs 31/12/2023 (4181: 7356€, 4081: 653€) SANS extournes
Solution : Utiliser le générateur pour créer les extournes manquantes (01/01/2024)
```

**Supporte** :
- `CUTOFF_PRODUIT_A_RECEVOIR`
- `CUTOFF_HONORAIRES`
- `CUTOFF_INTERETS_COURUS`

**Utilisation** :
```bash
# Simulation (dry-run) - RECOMMANDÉ pour vérifier d'abord
python generateur_extournes.py --exercice 2023

# Exécution réelle
python generateur_extournes.py --exercice 2023 --execute

# Tous les exercices cloturés
python generateur_extournes.py --tous --execute
```

---

## 📅 Timeline Annuelle Type (Système 100% Automatique)

**Décembre N** :
1. ✅ Email Ulrik honoraires → Crée cutoff 31/12/N + extourne 01/01/N+1 **automatiquement**

**Janvier N+1** :
1. ✅ Email Ulrik SCPI T4 → Crée cutoff 31/12/N + extourne 01/01/N+1 **automatiquement** (rétroactif)
2. ✅ Première échéance prêt → Détecte janvier → Crée cutoff intérêts 31/12/N + extourne 01/01/N+1 **automatiquement**

**Année N+1** :
- Paiements réels arrivent normalement
- Charges/produits N+1 = écarts avec estimations
- **Aucune action manuelle requise** pour les extournes (déjà créées)
- **Aucune action manuelle requise** pour les cutoffs intérêts (créés automatiquement)

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

## 🔄 Flux Technique Complet (100% Automatique)

```
┌─────────────────────────────────────────────────────────┐
│ FIN DÉCEMBRE N - Email Ulrik Honoraires                │
│ → DetecteurAnnonceHonorairesARegler                     │
│ → Crée AUTOMATIQUEMENT :                                │
│   - Cutoff 31/12/N : 6226 → 4081                       │
│   - Extourne 01/01/N+1 : 4081 → 6226                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ JANVIER N+1 - Email Ulrik Revenus SCPI T4              │
│ → DetecteurAnnonceProduitARecevoir                      │
│ → Crée AUTOMATIQUEMENT (rétroactif) :                  │
│   - Cutoff 31/12/N : 4181 → 761                        │
│   - Extourne 01/01/N+1 : 761 → 4181                    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ JANVIER N+1 - Première Échéance Prêt (ex: 12/01)       │
│ → DetecteurRemboursementPret                            │
│ → Détecte mois = janvier → Vérifie cutoff intérêts     │
│ → Si NON trouvé : Appelle CalculateurInteretsCourus    │
│ → Crée AUTOMATIQUEMENT (rétroactif) :                  │
│   - Écritures échéance : 661 → 512 + 164 → 512         │
│   - Cutoff intérêts 31/12/N : 661 → 1688 (2 prêts)     │
│   - Extourne 01/01/N+1 : 1688 → 661 (2 prêts)          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ ANNÉE N+1 - Paiements Réels                            │
│ - Janvier : Distribution SCPI (512 → 761)              │
│ - Reste année : Échéances prêts (661 → 512 + 164 → 512)│
│ - Mars : Facture honoraires (6226 → 512)               │
└─────────────────────────────────────────────────────────┘

NOTE : Aucune action manuelle requise, tout est 100% automatique !
```

---

## 📝 Notes Importantes

1. **Ordre d'exécution** :
   - Cutoff honoraires : Décembre N (via email Ulrik)
   - Cutoff revenus SCPI : Janvier N+1 (via email Ulrik, rétroactif)
   - Cutoff intérêts : Janvier N+1 (via première échéance, rétroactif, automatique)
   - Extournes : Créées ENSEMBLE avec les cutoffs (dans la foulée)

2. **Sécurité** :
   - Cutoffs honoraires/revenus : Seul Ulrik peut créer (email ulrik.c.s.be@gmail.com)
   - Cutoff intérêts : Créé automatiquement (calcul mathématique, pas d'intervention humaine)
   - Générateur extournes : dry-run par défaut (utilitaire de secours uniquement)

3. **Écarts** :
   - Montant réel ≠ estimation → Écart comptabilisé en N+1
   - Acceptable comptablement (principe de prudence)

4. **Automatisation** :
   - Système 100% automatique pour tous les types de cutoffs
   - Aucune action manuelle requise
   - Détection intelligente (vérifie si cutoff existe déjà)

---

**Version** : 1.1 - 19 novembre 2025
**Auteur** : _Head.Soeurise avec Claude Code
**Changelog** :
- v1.1 (19/11/2025) : Ajout déclenchement automatique cutoff intérêts lors 1ère échéance janvier
- v1.0 (18/11/2025) : Version initiale système cutoff par extourne
