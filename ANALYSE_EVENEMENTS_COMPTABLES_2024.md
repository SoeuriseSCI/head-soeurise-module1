# Analyse des Événements Comptables 2024 (T1-T2-T3)
## Source : Elements Comptables des 1-2-3T2024.pdf

**Date d'analyse** : 05/11/2025
**Période couverte** : 05/12/2023 au 04/10/2024 (10 mois)
**Source** : Relevés LCL + documents comptables

---

## 🎯 Vue d'Ensemble

**Total événements identifiés** : ~150+ opérations sur 10 mois

### Types d'événements détectés

| Type | Fréquence | Récurrent | Complexité |
|------|-----------|-----------|------------|
| Remboursement prêts | Mensuel (×2) | ✅ OUI | ⭐⭐ Moyenne |
| Revenus SCPI | Trimestriel | ✅ OUI | ⭐⭐⭐ Élevée |
| Assurances prêt | Mensuel (×2) | ✅ OUI | ⭐ Faible |
| Frais comptable | Trimestriel | ✅ OUI | ⭐ Faible |
| Achats ETF/Actions | Irrégulier | ❌ NON | ⭐⭐⭐ Élevée |
| Apports Ulrik | Irrégulier | ❌ NON | ⭐⭐ Moyenne |
| Frais bancaires | Mensuel | ✅ OUI | ⭐ Faible |
| Impôts/taxes | Ponctuel | ❌ NON | ⭐⭐ Moyenne |

---

## 📋 Catégorie 1 : REMBOURSEMENTS DE PRÊTS IMMOBILIERS

### Caractéristiques
- **Fréquence** : Mensuel (le 15 de chaque mois)
- **Nombre d'opérations** : 2 débits par mois = 20 opérations sur 10 mois
- **Montants** : Fixes et prévisibles

### Détail des prêts

#### Prêt A - INVESTIMUR (BRLZE11AQ)
```
Libellé : "PRET IMMOBILIER ECH XX/XX/XX DOSSIER NO 5009736BRLZE11AQ"
Montant : 258,33€ (fixe)
Fréquence : 15 de chaque mois
Type : DÉBIT
Comptes comptables :
  - Débit 661 (Charges d'intérêts)
  - Débit 164 (Emprunts - remboursement capital)
  - Crédit 512 (Banque)
```

#### Prêt B - LCL (BRM0911AH)
```
Libellé : "PRET IMMOBILIER ECH XX/XX/XX DOSSIER NO 5009736BRM0911AH"
Montant : 1 166,59€ (fixe)
Fréquence : 15 de chaque mois
Type : DÉBIT
Comptes comptables :
  - Débit 661 (Charges d'intérêts)
  - Débit 164 (Emprunts - remboursement capital)
  - Crédit 512 (Banque)
```

### Enjeu comptable
⚠️ **NÉCESSITE VENTILATION INTÉRÊTS/CAPITAL** via table `echeances_prets`

---

## 📋 Catégorie 2 : ASSURANCES EMPRUNTEUR

### Caractéristiques
- **Fréquence** : Mensuel
- **Émetteur** : CACI NON LIFE LIMITED (via SEPA)
- **Montants** : Deux prélèvements distincts

### Détail

#### Assurance 1
```
Libellé : "PRLV SEPA CACI NON LIFE LIMITED CREANCIER INITIAL:701G"
Contrat : 7011001219769994028GDE3006701R (ou similaire)
Montant : 66,58€
Fréquence : Variable (début de mois)
Type : DÉBIT
Compte comptable :
  - Débit 616 (Primes d'assurance)
  - Crédit 512 (Banque)
```

#### Assurance 2
```
Libellé : "PRLV SEPA CACI NON LIFE LIMITED CREANCIER INITIAL:701G"
Contrat : 7011001219769994119GDE3001815R (ou similaire)
Montant : 20,99€
Fréquence : Variable (début de mois)
Type : DÉBIT
Compte comptable :
  - Débit 616 (Primes d'assurance)
  - Crédit 512 (Banque)
```

---

## 📋 Catégorie 3 : REVENUS SCPI (Épargne Pierre - Atland Voisin)

### Caractéristiques
- **Fréquence** : Trimestriel
- **Complexité** : ÉLEVÉE (plusieurs types de distributions)
- **Montants** : Variables selon trimestre

### Types de distributions

#### A. Distribution trimestrielle classique
```
Libellé : "VIR SEPA SCPI EPARGNE PIERRE DISTRIBUTION XEME TRIM 202X SCI SOEURISE"
Montants observés :
  - 4ème trim 2023 : 7 356,24€ (CRÉDIT le 29/01/2024)
  - 1er trim 2024 : 6 346,56€ (CRÉDIT le 24/04/2024)
  - 2ème trim 2024 : 6 346,56€ (CRÉDIT le 24/07/2024)

Comptes comptables :
  - Débit 512 (Banque)
  - Crédit 761 (Produits de participations - revenus SCPI)
```

#### B. Distribution de capital / réserves
```
Libellé : "SCPI EPARGNE PIERRE DISTRIB CAPITAL NUMERO 01 SCI SOEURISE"
Montant : 601,00€ (CRÉDIT le 24/04/2024)

Comptes comptables :
  - Débit 512 (Banque)
  - Crédit 106 (Réserves) ou Crédit 280 (Titres de participation - réduction valeur)
```

### Particularité : Bulletin détaillé
Chaque trimestre, un bulletin détaille :
- Nombre de parts : 2404
- Revenu mensuel par part : 0.88€ à 1.02€
- Déductions sociales et fiscales : 0,00€ (prélèvements sociaux payés par la SCPI)

---

## 📋 Catégorie 4 : ACHATS VALEURS MOBILIÈRES

### Caractéristiques
- **Fréquence** : Irrégulier (plusieurs par mois en août 2024)
- **Complexité** : ÉLEVÉE (nécessite suivi du portefeuille)
- **Montants** : Variables

### A. Achats ETF MSCI World (EURONEXT Paris)

```
Libellé : "150 AM.MSCI WLD V UC.ETF ACC" (ou 100, ou autre quantité)
Code : LU1781541179
Exemples :
  - 30/01/2024 : 150 parts @ 15,6316€ = 2 344,74€ + commission 12,62€
  - 25/04/2024 : 150 parts @ 16,1742€ = 2 426,13€ + commission 13,03€
  - 24/07/2024 : 100 parts @ 17,26€ = 1 726,00€ + commission 9,53€

Type : DÉBIT
Comptes comptables :
  - Débit 503 (Actions - ETF)
  - Débit 627 (Services bancaires - commissions)
  - Crédit 512 (Banque)
```

### B. Achats Actions Amazon (NASDAQ)

```
Libellé : "6 AMAZON COM ACHAT 2108" (quantité variable)
Code : US0231351067
Cours : ~171-180 USD
Exemples :
  - 21/08/2024 : 6 actions @ 179,93 USD = 970,25€ + commission 50€ + frais 6,29€
  - 21/08/2024 : 21 actions @ 180,10 USD = 3 399,09€ + commission 50€
  - 26/08/2024 : 31 actions @ 176,80 USD = 4 901,89€ + commission 53,92€
  - 28/08/2024 : 32 actions @ 171,21 USD = 4 942,99€ + commission 54,38€

Type : DÉBIT
Comptes comptables :
  - Débit 503 (Actions - Portefeuille)
  - Débit 627 (Services bancaires - commissions + frais de change)
  - Crédit 512 (Banque)
```

### Particularité : Portefeuille actions au 23/08/2024
Extrait page 38 du PDF :
- **Mes positions** : 90 actions (~15 191€)
- **Mes ordres** : -
- **Mon historique** : 187 128€
- **ICC (Marché)** : +1 037%
- **Coût** : -
- **+ Valeur portée** : 15 191€ / +233 679€
- **Décorrélation** : ???

⚠️ **ATTENTION** : Valeurs patrimoniales importantes à suivre pour valorisation au bilan

---

## 📋 Catégorie 5 : APPORTS EN COMPTE COURANT (Ulrik Bergsten)

### Caractéristiques
- **Fréquence** : Irrégulier
- **Émetteur** : Ulrik Bergsten (gérant)
- **Objectif** : Alimenter la trésorerie de la SCI

### Détail des apports 2024

```
18/06/2024 : 500,00€ (CRÉDIT)
  Libellé : "Apport CC UB VIREMENT MONSIEUR ULRIK BERGSTE"

21/08/2024 : 4 500,00€ (CRÉDIT)
  Libellé : "Apport En Compte Courant VIREMENT MONSIEUR ULRIK BERGSTE"

24/08/2024 : 5 000,00€ (CRÉDIT)
  Libellé : "Apport En Compte Courant VIREMENT MONSIEUR ULRIK BERGSTE"

28/08/2024 : 5 000,00€ (CRÉDIT)
  Libellé : "Apport En Compte Courant VIREMENT MONSIEUR ULRIK BERGSTE"

TOTAL T3 2024 : 14 500,00€
```

### Comptes comptables
```
- Débit 512 (Banque)
- Crédit 455 (Compte courant d'associés - Ulrik Bergsten)
```

⚠️ **IMPORTANT** : Ces apports sont remboursables à tout moment

---

## 📋 Catégorie 6 : HONORAIRES COMPTABLE (CRP 2C)

### Caractéristiques
- **Fréquence** : Trimestriel + ponctuel
- **Prestataire** : CRP 2C (Expert-comptable)

### Détail des factures

#### Facture 2024013227 - 02/01/2024
```
Provision honoraires révision comptes : 100,00€
Honoraires juridiques fin exercice : 78,00€
Total HT : 178,00€
TVA 20% : 35,60€
Total TTC : 213,60€ (DÉBIT le 24/01/2024)
```

#### Facture 2024043519 - 01/04/2024
```
Provision honoraires révision comptes : 100,00€
Honoraires juridiques fin exercice : 78,00€
Total HT : 178,00€
TVA 20% : 35,60€
Total TTC : 213,60€ (DÉBIT le 24/04/2024)
```

#### Facture 2024063803 - 01/06/2024
```
Honoraires saisie temps passés (solde mission 31/12/2023) : 470,00€
Total HT : 470,00€
TVA 20% : 94,00€
Total TTC : 564,00€ (DÉBIT le 24/06/2024)
```

#### Facture 2024073849 - 01/07/2024
```
Provision honoraires révision comptes : 100,00€
Honoraires juridiques fin exercice : 78,00€
Total HT : 178,00€
TVA 20% : 35,60€
Total TTC : 213,60€
```

### Comptes comptables
```
- Débit 622 (Honoraires - Expert-comptable)
- Débit 4456 (TVA déductible)
- Crédit 512 (Banque)
```

---

## 📋 Catégorie 7 : IMPÔTS ET TAXES

### A. Prélèvement SEPA - Direction Générale des Finances Publiques

```
Libellé : "PRLV SEPA DIRECTION GENERALE DES FINANCES PUBLIQUE S"
Créancier : D.G.F.I.P IMPOT CFE
Référence : LIBELLE:6002032870ZZZZZ (identifiant fiscal)
Montants variables :
  - 22/12/2023 : 78,00€
  - 21/12/2023 : 11,50€

Comptes comptables :
  - Débit 63 (Impôts et taxes)
  - Crédit 512 (Banque)
```

---

## 📋 Catégorie 8 : FRAIS BANCAIRES (LCL)

### Caractéristiques
- **Fréquence** : Mensuel
- **Montants** : Fixes et faibles

### Détail

#### A. LCL À LA CARTE PRO
```
Libellé : "LCL A LA CARTE PRO VOTRE REMISE SUR PRODUITS SOUSCRITS - XX/24 - 03%"
Montant : 0,22€ (CRÉDIT - remise)
Fréquence : Mensuel (fin de mois)
```

#### B. Cotisation Option PRO
```
Libellé : "COTISATION DE VOTRE OPTION PRO"
Montant : 5,15€ (DÉBIT)
Fréquence : Mensuel (fin de mois)
```

#### C. Abonnement LCL ACCESS
```
Libellé : "ABON LCL ACCESS 007,25EUR"
Montant : 7,25€ (DÉBIT)
Fréquence : Mensuel (début de mois)
```

### Total mensuel net
```
5,15€ + 7,25€ - 0,22€ = 12,18€ / mois
Soit ~146€ / an
```

### Comptes comptables
```
- Débit 627 (Services bancaires et assimilés)
- Crédit 512 (Banque) ou Débit 512 (si remise)
```

---

## 📋 Catégorie 9 : FRAIS ADMINISTRATIFS

### Facture INSEE (LEI France) - 27/03/2024

```
Référence : LEI/11833949/11834276
Prestation : Renouvellement LEI (Legal Entity Identifier)
Prix unitaire : 50€
Quantité : 1
Montant HT : 50€
Montant TTC : 50€ (non assujetti TVA)
Date paiement : 21/03/2024

Comptes comptables :
  - Débit 625 (Déplacements, missions et réceptions - frais admin)
  - Crédit 512 (Banque)
```

---

## 🔍 Patterns et Observations Clés

### Récurrence mensuelle forte
**Opérations fixes (15-20 par mois)** :
- 2 remboursements prêts (le 15)
- 2 assurances (début mois)
- 3 frais bancaires (fin/début mois)

### Pics d'activité
- **Août 2024** : Forte activité d'investissement
  - 4 achats Amazon (total ~13 000€)
  - 3 apports Ulrik (total 14 500€)

### Complexité par type

| Type | Parsing | Validation | Comptabilisation |
|------|---------|------------|------------------|
| Prêts | ⭐⭐ | ⭐⭐⭐ (BD ref) | ⭐⭐⭐ (ventilation) |
| SCPI | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ (plusieurs comptes) |
| ETF/Actions | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ (suivi portef.) |
| Apports | ⭐ | ⭐ | ⭐⭐ (CC associé) |
| Assurances | ⭐ | ⭐ | ⭐ |
| Frais | ⭐ | ⭐ | ⭐ |

### Montants annuels estimés

```
CHARGES :
- Remboursements prêts : (258,33 + 1166,59) × 12 = 17 099€
- Assurances : (66,58 + 20,99) × 12 = 1 051€
- Comptable : ~800€
- Frais bancaires : ~146€
- Impôts/taxes : ~150€
TOTAL CHARGES : ~19 246€

PRODUITS :
- Revenus SCPI : 4 trimestres × ~6 500€ = 26 000€
TOTAL PRODUITS : ~26 000€

INVESTISSEMENTS :
- ETF/Actions : ~20 000€ (août 2024)
- Financés par apports Ulrik : ~14 500€
```

---

## 📊 Recommandations pour le Système

### 1. Détecteurs spécialisés à créer

```python
class DetecteurRemboursementPret:
    """Détecte et ventile remboursements prêts via table echeances_prets"""

class DetecteurRevenuSCPI:
    """Détecte revenus SCPI et distingue dividendes/capital"""

class DetecteurAchatValeursMobilieres:
    """Détecte achats ETF/Actions + commissions"""

class DetecteurApportAssocié:
    """Détecte apports en compte courant"""

class DetecteurAssurancePret:
    """Détecte prélèvements assurance emprunteur"""

class DetecteurFraisBancaires:
    """Détecte et regroupe frais bancaires"""
```

### 2. Tables BD nécessaires

✅ **Déjà existantes** :
- `echeances_prets` (ventilation intérêts/capital)
- `ecritures_comptables`
- `evenements_comptables`

🆕 **À ajouter** :
- `portefeuille_valeurs_mobilieres` (suivi ETF/Actions)
- `comptes_courants_associes` (suivi apports Ulrik)

### 3. Règles de validation

**Remboursements prêts** :
- ✅ Montants doivent correspondre à la table `echeances_prets`
- ✅ Dates = 15 de chaque mois

**Revenus SCPI** :
- ⚠️ Montants variables → nécessite confirmation manuelle
- ✅ Fréquence = trimestrielle

**Achats valeurs mobilières** :
- ⚠️ Nécessite validation prix marché
- ⚠️ Suivi valorisation portefeuille

### 4. Priorités d'implémentation

1. **PHASE 1** (Simple - Récurrent) :
   - Assurances prêt
   - Frais bancaires
   - Honoraires comptable

2. **PHASE 2** (Moyen - Récurrent + Validation) :
   - Remboursements prêts (avec ventilation)
   - Apports associés

3. **PHASE 3** (Complexe - Irrégulier) :
   - Revenus SCPI
   - Achats valeurs mobilières
   - Impôts/taxes

---

## 🎓 Leçons Apprises

### Ce qui est stable et prédictible
✅ Remboursements prêts (montants fixes, dates fixes)
✅ Assurances (montants fixes, fréquence stable)
✅ Frais bancaires (montants fixes)

### Ce qui nécessite une analyse manuelle
⚠️ Revenus SCPI (montants variables, typologie multiple)
⚠️ Achats valeurs mobilières (timing imprévisible, valorisation)
⚠️ Apports associés (montants variables, timing imprévisible)

### Ce qui doit être documenté
📋 Chaque achat de valeur mobilière → suivi portefeuille
📋 Chaque apport → mise à jour compte courant associé
📋 Chaque remboursement prêt → vérification cohérence échéancier

---

**Conclusion** : Le système doit gérer une **grande diversité** d'événements avec des niveaux de complexité très variables. La priorité doit être donnée aux événements **récurrents et stables** pour automatiser rapidement, tout en prévoyant un workflow de **validation manuelle** pour les événements complexes ou irréguliers.
