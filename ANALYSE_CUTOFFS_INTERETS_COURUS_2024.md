# Analyse Cutoffs et Intérêts Courus 2023-2024

**Date d'analyse** : 27/11/2025
**Contexte** : Compréhension du bilan d'ouverture 2024 et préparation des extournes/cutoffs

---

## 1. Résumé Exécutif

**Décision validée** : Aligner les montants des cutoffs/extournes sur ceux du comptable, même si le calcul théorique diffère de quelques euros.

**Montants retenus** :
- **Cutoff 31/12/2023** : 259€ (déjà comptabilisé par le comptable)
- **Extourne 01/01/2024** : 259€ (à prévoir dans le système)
- **Cutoff 31/12/2024** : 254€ (à prévoir dans le système)

**Écart constaté** : 5-10€ entre calcul théorique et montants comptable
**Nature de l'écart** : Non matériel, probablement dû à une méthode de calcul différente (base 360 vs 365, arrondis)
**Approche** : Pragmatisme comptable - suivre l'expert

---

## 2. Compréhension du Compte 164 au 31/12/2023

### Décomposition des 497 993€

**Source** : Résumé Des Comptes 2024.pdf (document comptable officiel)

```
Prêt LCL (amortissable, 1,05%)
  Capital restant dû au 15/12/2023 :        244 849€

Prêt INVESTIMUR (franchise partielle, 1,24%)
  Capital initial :                         250 000€
  + Intérêts capitalisés année 1 :           2 885€
  = Capital total au 15/12/2023 :           252 885€

Sous-total capital :                        497 734€

Intérêts courus 16-31/12/2023 (1688) :         259€
────────────────────────────────────────────────────
TOTAL Compte 164 :                          497 993€ ✅
```

### Point clé découvert

Le **Prêt INVESTIMUR** a eu une période de **différé total** (intérêts ET capital) la première année.
Les intérêts de cette période ont été **capitalisés** : 2 884,10€

**Conséquence** : Le capital portant intérêts n'est PAS 250 000€ mais **252 884,10€**

Cette découverte était **essentielle** pour comprendre l'écart entre les tableaux d'amortissement et le document comptable.

---

## 3. Calcul des Intérêts Courus - Fin 2023

### Données de base au 15/12/2023

**Prêt 1 (LCL)** :
- Capital restant dû : 244 849,44€
- Taux : 1,05%
- Échéance mensuelle intérêts : 215,08€

**Prêt 2 (INVESTIMUR)** :
- Capital restant dû : 252 884,10€ (incluant capitalisés)
- Taux : 1,24%
- Échéance mensuelle intérêts : 258,33€

### Période de calcul : 16-31/12/2023 (16 jours)

**Calcul théorique (base 365 jours)** :
- Prêt LCL : 244 849,44 × 1,05% × 16/365 = 113,43€
- Prêt INVESTIMUR : 252 884,10 × 1,24% × 16/365 = 137,76€
- **Total théorique : 251,19€**

**Calcul théorique (base 360 jours)** :
- Prêt LCL : 244 849,44 × 1,05% × 16/360 = 114,97€
- Prêt INVESTIMUR : 252 884,10 × 1,24% × 16/360 = 139,69€
- **Total théorique : 254,66€**

**Montant comptable retenu : 259€**

**Écart constaté** : 4-8€ selon la méthode

**Hypothèses sur l'écart** :
- Méthode de calcul bancaire spécifique (30/360 modifiée)
- Arrondis cumulés
- Inclusion de micro-frais
- Méthode de décompte des jours différente

**Décision** : Accepter le montant du comptable (259€) comme référence

---

## 4. Calcul des Intérêts Courus - Fin 2024

### Données de base au 15/12/2024

**Prêt 1 (LCL)** :
- Capital restant dû : 233 366,13€ (amortissement en cours)
- Taux : 1,05%
- Échéance mensuelle intérêts : 205,04€

**Prêt 2 (INVESTIMUR)** :
- Capital restant dû : 252 884,10€ (constant - franchise partielle)
- Taux : 1,24%
- Échéance mensuelle intérêts : 258,33€

### Période de calcul : 16-31/12/2024 (16 jours)

**Calcul théorique (base 365 jours)** :
- Prêt LCL : 233 366,13 × 1,05% × 16/365 = 108,11€
- Prêt INVESTIMUR : 252 884,10 × 1,24% × 16/365 = 137,76€
- **Total théorique : 245,87€**

**Calcul théorique (base 360 jours)** :
- Prêt LCL : 233 366,13 × 1,05% × 16/360 = 109,59€
- Prêt INVESTIMUR : 252 884,10 × 1,24% × 16/360 = 139,69€
- **Total théorique : 249,28€**

**Montant comptable retenu : 254€**

**Écart constaté** : 4-8€ selon la méthode

**Cohérence vérifiée** : La différence de 5€ entre 2023 (259€) et 2024 (254€) s'explique logiquement par l'amortissement du Prêt LCL (réduction de capital de ~11 500€)

---

## 5. Écritures Comptables à Prévoir

### Extourne au 01/01/2024

**Type d'événement** : EXTOURNE_CUTOFF
**Montant** : 259€
**Justification** : Annulation du cutoff d'intérêts courus de fin 2023

```
01/01/2024 - Extourne intérêts courus 2023
──────────────────────────────────────────
Débit  1688  Intérêts courus            259,00€
  Crédit 661   Charges d'intérêts                259,00€

Libellé : Extourne cutoff intérêts courus 31/12/2023
```

**Impact** :
- ❌ Annule la charge d'intérêts provisionnée en 2024
- ✅ Libère le compte de passif 1688
- ✅ Prépare l'enregistrement de l'échéance réelle du 15/01/2024

### Cutoff au 31/12/2024

**Type d'événement** : CUTOFF
**Montant** : 254€
**Justification** : Rattachement des intérêts courus à l'exercice 2024

```
31/12/2024 - Cutoff intérêts courus 2024
──────────────────────────────────────────
Débit  661   Charges d'intérêts         254,00€
  Crédit 1688  Intérêts courus                   254,00€

Libellé : Cutoff intérêts courus prêts 16-31/12/2024
```

**Impact** :
- ✅ Augmente les charges 2024 de 254€
- ✅ Diminue le résultat 2024 de 254€
- ✅ Crée un passif (dette) de 254€ au bilan

---

## 6. Vérification de Cohérence

### Impact sur le bilan d'ouverture 2024

**AVANT extourne** (au 01/01/2024, 00h00) :
- Compte 164 (Emprunts) : 497 993€
  - dont capital : 497 734€
  - dont intérêts courus (1688) : 259€

**APRÈS extourne** (au 01/01/2024, après extourne) :
- Compte 164 (Emprunts capital) : 497 734€
- Compte 1688 (Intérêts courus) : 0€
- Compte 661 (Charges 2024) : -259€ (crédit, sera compensé par échéances réelles)

✅ **Cohérence vérifiée** : Le système correspond exactement au document comptable

### Impact sur l'exercice 2024

**Charges d'intérêts 2024** :
- Extourne début : -259€ (crédit)
- Échéances mensuelles : 12 × (215€ + 258€) ≈ 5 676€
- Cutoff fin : +254€
- **Total charges 2024** : -259 + 5 676 + 254 = **5 671€**

✅ **Logique respectée** : Les charges correspondent aux intérêts de l'exercice 2024

---

## 7. Implémentation dans le Système

### Détecteurs concernés

**DetecteurCutoffsMultiples** (existant) :
- Doit gérer les cutoffs d'intérêts courus
- ✅ Déjà opérationnel pour charges et produits

**DetecteurExtournes** (existant) :
- Doit gérer les extournes début d'exercice
- ✅ Déjà opérationnel

### Proposition d'écritures automatiques

**Option 1** : Email manuel d'Ulrik spécifiant les montants exacts
✅ **Retenu** : Plus sûr, respecte le principe "minimiser code, maximiser Claude"

**Option 2** : Calcul automatique avec formule paramétrable
❌ Rejeté : Risque d'erreur si formule ne correspond pas à celle du comptable

### Données de référence à stocker

```python
CUTOFFS_INTERETS_COURUS = {
    2023: 259,  # € - Intérêts courus fin 2023
    2024: 254,  # € - Intérêts courus fin 2024
    # À compléter les années suivantes
}
```

**Note** : Ces montants seront validés par le comptable chaque année

---

## 8. Enseignements et Leçons Apprises

### Leçon 1 : Importance de la capitalisation d'intérêts

**Contexte** : Prêt INVESTIMUR avec différé total année 1

**Erreur initiale** : Calculer les intérêts sur 250 000€
**Correction** : Calculer sur 252 884€ (capital + intérêts capitalisés)

**Règle établie** : Toujours vérifier les tableaux d'amortissement pour identifier les capitalisations

### Leçon 2 : Pragmatisme vs Précision Théorique

**Écart constaté** : 5-10€ entre calcul théorique et comptable
**Enjeu financier** : 0,002% de l'actif total (négligeable)
**Risque de divergence** : Élevé si on impose notre calcul

**Décision** : **Suivre le comptable** plutôt que d'imposer notre méthode

**Principe général** :
> "En cas de divergence non matérielle avec l'expert-comptable, s'aligner sur ses montants pour garantir la cohérence des états financiers."

### Leçon 3 : Documentation des Décisions

**Importance** : Tracer les choix et justifications
**Bénéfice** : Compréhension future, audit, continuité

**Règle établie** : Documenter systématiquement les écarts entre théorie et pratique

---

## 9. Actions pour 2025 et Suivantes

### Processus annuel à établir

**Avant clôture de l'exercice N** :
1. Demander au comptable les montants exacts des cutoffs
2. Valider la cohérence avec l'exercice précédent
3. Documenter les écarts éventuels
4. Programmer les extournes début N+1

### Template email pour le comptable

```
Objet : Cutoffs intérêts courus - Clôture [ANNÉE]

Bonjour,

Pour la clôture de l'exercice [ANNÉE], pourriez-vous me confirmer :

1. Montant des intérêts courus au 31/12/[ANNÉE] (compte 1688)
2. Détail par prêt si possible :
   - Prêt LCL : capital au 15/12/[ANNÉE] + intérêts courus
   - Prêt INVESTIMUR : capital au 15/12/[ANNÉE] + intérêts courus

Merci d'avance,
Ulrik
```

### Vérifications de cohérence

**Chaque année** :
- Écart entre année N et N-1 cohérent avec amortissement du prêt LCL
- Prêt INVESTIMUR stable à 252 884€ jusqu'en mars 2040
- Total cutoff entre 200€ et 300€ (ordre de grandeur)

---

## 10. Conclusion

### Mystère résolu ✅

**Question initiale** : D'où viennent les 497 993€ du compte 164 ?

**Réponse complète** :
- Prêt LCL : 244 849€
- Prêt INVESTIMUR : 252 885€ (incluant 2 885€ capitalisés)
- Intérêts courus : 259€
- **Total : 497 993€** ✅

### Décisions opérationnelles ✅

**Extourne 2024** : 259€ (01/01/2024)
**Cutoff 2024** : 254€ (31/12/2024)

### Principe établi ✅

**Alignement comptable** : Suivre les montants du comptable pour garantir cohérence et auditabilité, même en cas de divergence théorique non matérielle.

### Documentation ✅

Ce document sert de référence pour :
- Comprendre la logique des cutoffs/extournes
- Justifier les montants retenus
- Guider les exercices futurs
- Former tout successeur (humain ou IA)

---

## 11. Mise à jour Architecture - 27 novembre 2025

### SIMPLIFICATION MAJEURE : Suppression du calcul automatique

**Décision** : Abandonner le calcul automatique des intérêts courus au profit d'une fourniture manuelle des montants.

**Raison** :
- Calcul automatique donnait ~245-251€
- Expert-comptable utilise 254€ (2024) et 259€ (2023)
- Écart non matériel (~5-10€) MAIS risque de divergence permanente avec états financiers
- Principe "minimiser code, maximiser Claude" non respecté

### Modifications effectuées

**1. Ajout support INTERETS_COURUS dans DetecteurCutoffsMultiples** ✅
- Détection mots-clés : "interet", "couru", "pret", "emprunt"
- Génération automatique cutoff + extourne (comme pour SCPI et honoraires)
- Montant FOURNI manuellement par Ulrik dans email

**2. Suppression CalculateurInteretsCourus** ✅
- Import supprimé de `detecteurs_evenements.py`
- Méthode `_declencher_cutoff_interets_si_necessaire()` supprimée
- Appel automatique dans `DetecteurRemboursementPret` supprimé
- Module `precloture_exercice.py` désactivé pour intérêts courus
- Fichier `cutoff_extourne_interets.py` archivé (`.ARCHIVE_27nov2025`)

**3. Workflow manuel unifié** ✅
Tous les cutoffs (honoraires, SCPI, intérêts) suivent maintenant LE MÊME workflow :
- Email manuel d'Ulrik avec montants explicites
- Détection par `DetecteurCutoffsMultiples`
- Génération automatique cutoff (31/12/N) + extourne (01/01/N+1)

### Template email unifié

```
Objet: Cutoffs fin 2024

Bonjour _Head,

Peux-tu créer des cutoffs pour:
1) les honoraires comptables de clôture de l'exercice 2024 (622€)
2) les produits SCPI du 4e trimestre 2024 (6755€)
3) les intérêts courus sur prêts au 31/12/2024 (254€)

Merci!
```

### Résultat automatique (6 écritures créées)

**Cutoffs 31/12/2024** :
1. D: 6226 / C: 4081 | 622€ (Honoraires)
2. D: 4181 / C: 761 | 6755€ (SCPI)
3. D: 661 / C: 1688 | 254€ (Intérêts courus)

**Extournes 01/01/2025** :
4. D: 4081 / C: 6226 | 622€ (Honoraires)
5. D: 761 / C: 4181 | 6755€ (SCPI)
6. D: 1688 / C: 661 | 254€ (Intérêts courus)

### Bénéfices de la simplification

✅ **Cohérence garantie** : Montants = ceux de l'expert-comptable (zéro divergence)
✅ **Code simplifié** : ~200 lignes de code supprimées
✅ **Workflow unifié** : Un seul email pour tous les cutoffs
✅ **Maintenance réduite** : Pas de formules complexes à maintenir
✅ **Principe respecté** : "Minimiser code, maximiser Claude"
✅ **Flexibilité** : Si méthode comptable change, aucun impact code

### Leçon apprise

> **Quand un calcul automatique diverge systématiquement des données officielles, même de quelques euros, il vaut mieux l'abandonner au profit d'une saisie manuelle.**
>
> La cohérence avec l'expert-comptable est plus importante que l'automatisation.

### Test réussi (27/11/2025)

Email test avec 3 cutoffs (honoraires 622€ + SCPI 6755€ + intérêts 254€) :
- ✅ Détection correcte
- ✅ 6 écritures générées (3 cutoffs + 3 extournes)
- ✅ Comptes corrects (6226/4081, 4181/761, 661/1688)
- ✅ Dates correctes (31/12/2024 et 01/01/2025)
- ✅ Montants exacts (fournis manuellement)

---

**Fin de l'analyse**
**Validation** : Ulrik (27/11/2025)
**Statut** : ✅ Complet et opérationnel
**Version** : 3.0 - Architecture simplifiée (suppression calcul automatique)
