# Analyse Manuelle : Extraction Complète et Rapprochements

**Date** : 13/11/2025
**PDF analysé** : Elements Comptables des 1-2-3T2024.pdf (41 pages)
**Objectif** : Simuler extraction complète (sans filtrage) et identifier patterns de rapprochement

---

## 📊 Vue d'ensemble

**Total opérations extraites (estimation)** : ~165 opérations

### Répartition par type de document
- **Relevés bancaires** (pages 1-20) : ~88 opérations
- **Factures comptables CRP 2C** (pages 21-24) : 4 factures
- **Bulletins SCPI ATLAND VOISIN** (pages 25, 27, 29) : 3 bulletins
- **Avis d'opération SCPI** (pages 26, 28, 30) : 6 avis (revenus + capital)
- **Avis achat valeurs mobilières** (pages 31-37) : 7 achats
- **Avis virements apports** (pages 39-40) : 4 apports
- **Facture INSEE LEI** (page 41) : 1 facture

---

## 🔗 GROUPES DE RAPPROCHEMENT DÉTECTÉS

### Groupe 1 : Factures CRP 2C → SEPA Prélèvements

#### 1.1 Facture Janvier 2024
**Documents liés** : 2 documents
- **Facture** (page 21) :
  - Date : 02/01/2024
  - N° facture : 2024013227
  - Montant TTC : 213,60€
  - Détails : 100€ provisions + 78€ honoraires + 35,60€ TVA
- **SEPA Prélèvement** (page 3, relevé janvier) :
  - Date : 24/01/2024
  - Libellé : "PRLV SEPA CRP Comptabilit Conseil LIBELLE:2024013227"
  - Montant : 213,60€ DEBIT

**Critères rapprochement** :
- ✅ Montant identique : 213,60€
- ✅ Dates proches : 02/01 → 24/01 (22 jours)
- ✅ N° facture dans libellé SEPA : "2024013227"

**Source à utiliser** : **SEPA** (opération bancaire réelle)
**Justificatif** : Facture (pour ventilation HT/TVA si besoin)

---

#### 1.2 Facture Avril 2024
**Documents liés** : 2 documents
- **Facture** (page 22) :
  - Date : 01/04/2024
  - N° facture : 2024043519
  - Montant TTC : 213,60€
- **SEPA Prélèvement** (page 9, relevé avril) :
  - Date : 24/04/2024
  - Libellé : "PRLV SEPA CRP Comptabilit Conseil LIBELLE:2024043519"
  - Montant : 213,60€ DEBIT

**Critères rapprochement** : Identiques au 1.1

---

#### 1.3 Facture Juin 2024
**Documents liés** : 2 documents
- **Facture** (page 23) :
  - Date : 01/06/2024
  - N° facture : 2024063803
  - Montant TTC : 564,00€
  - Détails : 470€ honoraires saisie + 94€ TVA
- **SEPA Prélèvement** (page 13, relevé juin) :
  - Date : 24/06/2024
  - Libellé : "PRLV SEPA CRP Comptabilit Conseil LIBELLE:2024063803"
  - Montant : 564,00€ DEBIT

**Critères rapprochement** :
- ✅ Montant identique : 564,00€
- ✅ Dates proches : 01/06 → 24/06 (23 jours)
- ✅ N° facture dans libellé SEPA : "2024063803"

---

#### 1.4 Facture Juillet 2024
**Documents liés** : 2 documents
- **Facture** (page 24) :
  - Date : 01/07/2024
  - N° facture : 2024073849
  - Montant TTC : 213,60€
- **SEPA Prélèvement** (page 15, relevé juillet) :
  - Date : 24/07/2024
  - Libellé : "PRLV SEPA CRP Comptabilite Conseil LIBELLE:2024073849"
  - Montant : 213,60€ DEBIT

**Critères rapprochement** : Identiques au 1.1

---

### Groupe 2 : Bulletins SCPI → Virements SCPI

#### 2.1 SCPI T4 2023
**Documents liés** : 2 documents
- **Bulletin informatif** (page 25) :
  - Date bulletin : 25/01/2024
  - Nature : "REVENUS DU 4ÈME TRIMESTRE 2023 SCPI Epargne Pierre"
  - Montant annoncé : 7 356,24€
- **Virement bancaire** (page 3, relevé janvier) :
  - Date : 29/01/2024
  - Libellé : "VIR SEPA SCPI EPARGNE PIERRE LIBELLE:SCPI EPARGNE PIERRE DISTRIBUTION 4EME TRIM .2023 SCI SOEURISE"
  - Montant : 7 356,24€ CREDIT

**Critères rapprochement** :
- ✅ Montant identique : 7 356,24€
- ✅ Dates très proches : 25/01 → 29/01 (4 jours)
- ✅ Même trimestre/période mentionné : "4ème trim 2023"

**+ Avis d'opération bancaire** (page 26) :
  - Date : 30/01/2024 (AU 30.01.2024)
  - Même libellé et montant

**Source à utiliser** : **Virement SEPA du relevé** (opération réelle)
**Justificatifs** : Bulletin + Avis d'opération (détails fiscaux)

---

#### 2.2 SCPI T1 2024 - Revenus
**Documents liés** : 2 documents
- **Bulletin informatif** (page 27) :
  - Date bulletin : 24/04/2024
  - Nature : "REVENUS DU 1ER TRIMESTRE 2024 SCPI Epargne Pierre"
  - Montant revenus : 6 346,56€
- **Virement bancaire** (page 9, relevé avril) :
  - Date : 24/04/2024
  - Libellé : "VIR SEPA SCPI EPARGNE PIERRE LIBELLE:SCPI EPARGNE PIERRE DISTRIBUTION 1ER TRIM. 2024 SCI SOEURISE"
  - Montant : 6 346,56€ CREDIT

**Critères rapprochement** :
- ✅ Montant identique : 6 346,56€
- ✅ Dates identiques : 24/04/2024
- ✅ Même trimestre : "1er trim 2024"

**+ Avis d'opération bancaire** (page 28) :
  - Date : 24/04/2024 (AU 24.04.2024)
  - Même opération

---

#### 2.3 SCPI T1 2024 - Distribution capital
**Documents liés** : 2 documents
- **Bulletin informatif** (page 27) :
  - Date bulletin : 24/04/2024
  - Nature : "Distribution de réserves de plus-values"
  - Montant capital : 601,00€
- **Virement bancaire** (page 9, relevé avril) :
  - Date : 24/04/2024
  - Libellé : "VIR SEPA SCPI EPARGNE PIERRE LIBELLE:SCPI EPARGNE PIERRE DISTRIB CAPITAL NUMERO 01 SCI SOEURISE"
  - Montant : 601,00€ CREDIT

**Critères rapprochement** :
- ✅ Montant identique : 601,00€
- ✅ Dates identiques : 24/04/2024
- ✅ Mention "capital" dans les deux

**+ Avis d'opération bancaire** (page 28) :
  - Date : 24/04/2024
  - Même opération

---

#### 2.4 SCPI T2 2024
**Documents liés** : 2 documents
- **Bulletin informatif** (page 29) :
  - Date bulletin : 24/07/2024
  - Nature : "REVENUS DU 2ÈME TRIMESTRE 2024 SCPI Epargne Pierre"
  - Montant revenus : 6 346,56€
- **Virement bancaire** (page 15, relevé juillet) :
  - Date : 24/07/2024
  - Libellé : "VIR SEPA SCPI EPARGNE PIERRE LIBELLE:SCPI EPARGNE PIERRE DISTRIBUTION 2EME TRIM .2024 SCI SOEURISE"
  - Montant : 6 346,56€ CREDIT

**Critères rapprochement** : Identiques au 2.2

**+ Avis d'opération bancaire** (page 30) :
  - Date : 24/07/2024 (AU 06.08.2024)
  - Même opération

---

### Groupe 3 : Facture LEI → SEPA Prélèvement

**Documents liés** : 2 documents
- **Facture INSEE** (page 41) :
  - Date facture : 27/03/2024
  - N° facture : LEI/11833949/11834276
  - Prestation : "Renouvellement LEI"
  - Montant : 50€ (non assujetti TVA)
  - Paiement prévu : 21/03/2024
- **SEPA Prélèvement** (page 7, relevé mars) :
  - Date : 25/03/2024
  - Libellé : "VIR SEPA Regie Recettes Insee LEI 11833949 11834276"
  - Montant : 50,00€ DEBIT

**Critères rapprochement** :
- ✅ Montant identique : 50,00€
- ✅ Dates très proches : 21/03 prévu, 25/03 réel, 27/03 facture (±6 jours)
- ✅ N° facture dans libellé : "11833949 11834276"
- ✅ Mention "LEI" dans les deux

**Source à utiliser** : **SEPA** (opération bancaire)
**Justificatif** : Facture INSEE (preuve du service)

---

### Groupe 4 : Achats Valeurs Mobilières → Débits bancaires

#### 4.1 Achat ETF 30/01/2024
**Documents liés** : 2 documents
- **Avis d'achat** (page 31) :
  - Date opération : 30/01/2024 à 09h40
  - Titre : 150 AMUNDI MSCI WORLD V UC.ETF ACC (LU1781541179)
  - Cours : 15,6316€
  - Montant brut : 2 344,74€
  - Commission : 12,62€
  - Frais marché : 0,90€
  - **Total débité : 2 357,36€**
- **Débit bancaire** (page 3, relevé janvier) :
  - Date : 30/01/2024
  - Libellé : "150 AM.MSCI WLD V ETF ACHAT 3001 15,631600 EUR"
  - Montant : 2 357,36€ DEBIT

**Critères rapprochement** :
- ✅ Montant identique : 2 357,36€
- ✅ Dates identiques : 30/01/2024
- ✅ Quantité + titre dans libellé : "150 AM.MSCI WLD"

**Détails dans avis UNIQUEMENT** :
- ISIN : LU1781541179
- Nombre titres : 150
- Prix unitaire : 15,6316€
- Décomposition : 2344,74€ brut + 12,62€ commission + 0,90€ frais

**Source à utiliser** : **Avis d'achat** (détails essentiels ISIN/quantité/prix)
**Justificatif** : Débit relevé (confirmation bancaire)

---

#### 4.2 Achat ETF 25/04/2024
**Documents liés** : 2 documents (structure identique au 4.1)
- **Avis d'achat** (page 32) : 150 titres, 2 439,16€
- **Débit bancaire** (relevé avril) : 25/04/2024, 2 439,16€

#### 4.3 Achat ETF 24/07/2024
- **Avis d'achat** (page 33) : 100 titres, 1 735,53€
- **Débit bancaire** (relevé juillet) : 24/07/2024, 1 735,53€

#### 4.4-4.7 Achats AMAZON (pages 34-37)
- 21/08 : 6 actions, 1 026,54€
- 22/08 : 21 actions, 3 455,38€
- 27/08 : 31 actions, 4 962,07€
- 29/08 : 32 actions, 5 003,69€

Tous suivent le même pattern : Avis détaillé + Débit relevé même montant/date

---

### Groupe 5 : Apports Associés

**Documents liés** : 2 types de documents
- **Avis d'écriture LCL** (pages 39-40) :
  - 18/06 : Apport CC UB - 500,00€
  - 21/08 : Apport En Compte Courant - 4 500,00€
  - 24/08 : Apport En Compte Courant - 5 000,00€
  - 28/08 : Apport En Compte Courant - 5 000,00€
- **Crédits relevé bancaire** (pages 13, 17) :
  - 18/06/2024 : "VIR SEPA MONSIEUR ULRIK BERGSTEN LIBELLE:Apport CC UB" - 500,00€
  - 21/08/2024 : "VIR SEPA MONSIEUR ULRIK BERGSTEN LIBELLE:Apport En Compte Courant" - 4 500,00€
  - 24/08/2024 : idem - 5 000,00€
  - 28/08/2024 : idem - 5 000,00€

**Critères rapprochement** :
- ✅ Montants identiques
- ✅ Dates identiques
- ✅ Libellés identiques

**Note** : Avis d'écriture = Confirmation banque de l'opération vue dans relevé
C'est un **vrai doublon** (même document, 2 formats)

---

## 📊 SYNTHÈSE DES PATTERNS DE RAPPROCHEMENT

### Pattern A : Facture → Prélèvement (décalage temporel)
**Exemples** : CRP 2C, LEI
**Critères** :
1. Montant identique
2. Dates ±20-30 jours
3. N° facture dans libellé prélèvement

**Règle** : Utiliser prélèvement, garder facture comme justificatif

---

### Pattern B : Bulletin informatif → Virement (annonce → réalisation)
**Exemples** : SCPI
**Critères** :
1. Montant identique
2. Dates ±0-7 jours
3. Période/trimestre identique

**Règle** : Utiliser virement SEPA, garder bulletin justificatif

---

### Pattern C : Avis opération → Débit/Crédit (détails → synthèse)
**Exemples** : Valeurs mobilières
**Critères** :
1. Montant identique
2. Date identique ou date valeur
3. Référence opération

**Règle** : Utiliser avis (détails ISIN/quantité/prix), garder relevé confirmation

---

### Pattern D : Doublons exacts (même opération, 2 formats)
**Exemples** : Avis d'écriture LCL
**Critères** :
1. Montant identique
2. Date identique
3. Libellé identique

**Règle** : Garder relevé bancaire uniquement, supprimer avis

---

## 🎯 CONCLUSION POUR PHASE 2

### Nombre d'opérations économiques réelles
**~88 opérations** (vs 165 extractions brutes)

### Réductions attendues
- Factures CRP 2C : 4 doublons éliminés
- Bulletins SCPI : 3 doublons éliminés
- Avis SCPI : 3 doublons éliminés (3 virements apparaissent 2x : bulletin + avis)
- Avis achats VM : 7 doublons éliminés
- Avis virements : 4 doublons éliminés
- **Total : -21 doublons**

### Algorithme de rapprochement
```python
Pour chaque groupe d'opérations avec même montant (±0,01€):
    1. Trier par date
    2. Si dates ±30 jours ET (n° facture match OU libellé similaire):
        → Groupe candidat
    3. Dans groupe, score de qualité:
        - Relevé bancaire : score base
        - + Facture avec n° : +20 points
        - + Avis avec ISIN : +30 points
        - + Bulletin SCPI : +10 points
    4. Garder source score max pour écriture
    5. Marquer autres comme justificatifs
```

### Validation humaine
Cette analyse manuelle servira de **gold standard** pour valider que Claude API détecte les mêmes groupes.

---

**Prochaine étape** : Implémenter `rapprocheur_operations.py` avec prompt Claude API
