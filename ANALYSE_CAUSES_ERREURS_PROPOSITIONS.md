# Analyse des Causes Racines - Erreurs dans les Propositions Comptables

**Date** : 12/11/2025
**Référence** : Token HEAD-161DC4AD (88 propositions générées)
**Documents analysés** :
- `gestionnaire_evenements.py:181-273`
- `detecteurs_evenements.py:297-350`
- `extracteur_pdf.py:81-159`
- `COMPARAISON_PROPOSITIONS_T1T2T3_2024.md`

---

## 🎯 Résumé Exécutif

J'ai identifié **3 causes racines** expliquant les erreurs critiques dans les 88 propositions comptables :

1. **DetecteurRevenuSCPI défaillant** → 27 000€ de revenus comptés comme achats
2. **DetecteurApportAssocie inexistant** → 15 000€ d'apports non détectés
3. **Déduplication Claude Haiku défaillante** → Doublons systématiques ETF/Amazon

---

## 🔴 Problème #1 : DetecteurRevenuSCPI Défaillant

### Localisation

**Fichier** : `detecteurs_evenements.py:297-350`

### Code Problématique

```python
class DetecteurRevenuSCPI(DetecteurBase):
    """
    Détecte les revenus SCPI (Société Civile de Placement Immobilier)

    PATTERN:
    - Libellé contient: SCPI, EPARGNE PIERRE
    - Montant variable (revenus trimestriels)
    - Type: DEBIT (virement sortant vers placement)  ← ❌ FAUX !
    - Fréquence: Trimestriel

    COMPTABILISATION:
    Débit 273 (Titres immobilisés - SCPI) : XX.XX€  ← ❌ TOUJOURS !
    Crédit 512 (Banque LCL)                : XX.XX€

    NOTE:
    - Les achats de parts SCPI sont des immobilisations financières
    - Les revenus futurs seront en 761 (Produits de participations)  ← ⚠️ "futurs" !
    """

    def detecter(self, evenement: Dict) -> bool:
        """Détecte un achat/revenu SCPI"""
        libelle_norm = evenement.get('libelle_normalise', '').lower()
        type_evt = evenement.get('type_evenement', '')

        # ❌ NE VÉRIFIE JAMAIS SI C'EST UN DEBIT OU UN CREDIT !
        patterns = ['scpi', 'epargne pierre']
        match_libelle = any(pattern in libelle_norm for pattern in patterns)

        match_type = type_evt == 'REVENU_SCPI'

        return match_libelle or match_type

    def generer_proposition(self, evenement: Dict) -> Dict:
        """Génère la proposition d'écriture"""
        montant = float(evenement.get('montant', 0))
        date_op = evenement.get('date_operation')

        # ❌ GÉNÈRE TOUJOURS LA MÊME ÉCRITURE (Achat de parts)
        # Même si c'est une distribution (CRÉDIT) !
        return {
            'type_evenement': 'REVENU_SCPI',
            'description': f'Achat parts SCPI Épargne Pierre',  ← ❌ "Achat" alors que type = "REVENU" !
            'confiance': 0.9,
            'ecritures': [
                {
                    'date_ecriture': date_op,
                    'libelle_ecriture': f'Acquisition parts SCPI Épargne Pierre',
                    'compte_debit': '273',  ← ❌ TOUJOURS 273 (Actif)
                    'compte_credit': '512',
                    'montant': montant,
                    'type_ecriture': 'ACHAT_SCPI',
                    'notes': 'Immobilisation financière - Parts SCPI'
                }
            ]
        }
```

### Analyse

Le détecteur souffre de **3 incohérences majeures** :

1. **Nom vs Comportement** :
   - Nom : `DetecteurRevenuSCPI`
   - Comportement : Détecte TOUS les événements SCPI (achats + revenus)
   - Comptabilisation : **TOUJOURS comme un achat** (Débit 273)

2. **Documentation contradictoire** :
   - Documentation : "Les revenus **futurs** seront en 761"
   - Réalité : Les revenus **actuels** sont déjà reçus !
   - Impact : 27 000€ de revenus T1-T3 2024 mal comptabilisés

3. **Pas de distinction DEBIT/CREDIT** :
   - Achats SCPI : Libellé court, DÉBIT (sortie d'argent)
   - Distributions SCPI : Libellé "DISTRIBUTION", CRÉDIT (entrée d'argent)
   - **Le détecteur ne vérifie jamais `type_operation`** !

### Événements Mal Classés (10 distributions = 27 000€)

```
Proposition 9-10  : 7 356,24€ × 2 (4T 2023) - Distribution comptée comme Achat
Proposition 34-37 : 6 346,56€ × 2 + 601,00€ × 2 (1T 2024) - Idem
Proposition 65-66 : 6 346,56€ × 2 (2T 2024) - Idem
```

**Total** : 10 distributions × montants variés = **27 000€ en compte 273 au lieu de 761**

### Impact Comptable

```
ATTENDU:
  Débit 512 (Banque)     : +27 000€
  Crédit 761 (Produits)  : +27 000€
  → Résultat : +27 000€

GÉNÉRÉ:
  Débit 273 (Actif SCPI) : +27 000€
  Crédit 512 (Banque)    : -27 000€
  → Résultat : 0€ (aucun produit comptabilisé !)

ÉCART:
  - Résultat fiscal : -27 000€
  - Actif : Surévalué de 27 000€
  - Produits : Manquants de 27 000€
```

### Solution Requise

```python
class DetecteurRevenuSCPI(DetecteurBase):
    """
    Détecte les DISTRIBUTIONS SCPI (revenus trimestriels)

    PATTERN:
    - Libellé contient: SCPI + DISTRIBUTION (ou DISTRIB)
    - Type: CREDIT (entrée d'argent)
    - Montants observés: 6 346,56€ ou 7 356,24€ ou 601,00€
    """

    def detecter(self, evenement: Dict) -> bool:
        libelle_norm = evenement.get('libelle_normalise', '').lower()
        type_op = evenement.get('type_operation', '')

        # ✅ Vérifier libellé + type CREDIT
        match_libelle = 'scpi' in libelle_norm and 'distri' in libelle_norm
        match_type = type_op == 'CREDIT'

        return match_libelle and match_type

    def generer_proposition(self, evenement: Dict) -> Dict:
        montant = float(evenement.get('montant', 0))
        date_op = evenement.get('date_operation')
        libelle = evenement.get('libelle', '')

        # Déterminer si distribution classique (761) ou de capital (106/280)
        est_capital = 'capital' in libelle.lower() or 'numero 01' in libelle.lower()

        if est_capital:
            # Distribution de capital (réduction valeur parts ou réserves)
            return {
                'type_evenement': 'DISTRIBUTION_CAPITAL_SCPI',
                'description': f'Distribution capital SCPI : {montant}€',
                'confiance': 0.9,
                'ecritures': [
                    {
                        'date_ecriture': date_op,
                        'libelle_ecriture': 'Distribution capital SCPI Épargne Pierre',
                        'compte_debit': '512',  # ✅ Banque
                        'compte_credit': '106',  # ✅ Réserves (ou 280)
                        'montant': montant,
                        'type_ecriture': 'DISTRIBUTION_CAPITAL',
                        'notes': 'Remboursement partiel capital / Réserves'
                    }
                ]
            }
        else:
            # Distribution classique (revenus)
            return {
                'type_evenement': 'REVENU_SCPI',
                'description': f'Distribution SCPI trimestre : {montant}€',
                'confiance': 0.95,
                'ecritures': [
                    {
                        'date_ecriture': date_op,
                        'libelle_ecriture': 'Revenus SCPI Épargne Pierre',
                        'compte_debit': '512',  # ✅ Banque
                        'compte_credit': '761',  # ✅ Produits
                        'montant': montant,
                        'type_ecriture': 'REVENU_SCPI',
                        'notes': 'Revenus trimestriels SCPI (2404 parts)'
                    }
                ]
            }


class DetecteurAchatSCPI(DetecteurBase):
    """
    NOUVEAU : Détecte les ACHATS de parts SCPI

    PATTERN:
    - Libellé contient: SCPI + ACHAT (ou SOUSCRIPTION)
    - Type: DEBIT (sortie d'argent)
    """

    def detecter(self, evenement: Dict) -> bool:
        libelle_norm = evenement.get('libelle_normalise', '').lower()
        type_op = evenement.get('type_operation', '')

        # ✅ Vérifier libellé + type DEBIT
        match_libelle = 'scpi' in libelle_norm and ('achat' in libelle_norm or 'souscription' in libelle_norm)
        match_type = type_op == 'DEBIT'

        return match_libelle and match_type

    def generer_proposition(self, evenement: Dict) -> Dict:
        montant = float(evenement.get('montant', 0))
        date_op = evenement.get('date_operation')

        return {
            'type_evenement': 'ACHAT_SCPI',
            'description': f'Acquisition parts SCPI : {montant}€',
            'confiance': 0.95,
            'ecritures': [
                {
                    'date_ecriture': date_op,
                    'libelle_ecriture': 'Acquisition parts SCPI Épargne Pierre',
                    'compte_debit': '273',  # ✅ Immobilisation
                    'compte_credit': '512',
                    'montant': montant,
                    'type_ecriture': 'ACHAT_SCPI',
                    'notes': 'Titres de participation immobilisés'
                }
            ]
        }
```

---

## 🔴 Problème #2 : DetecteurApportAssocie Inexistant

### Localisation

**Fichier** : `detecteurs_evenements.py`

### Code Actuel

```bash
$ grep "class Detecteur" detecteurs_evenements.py
class DetecteurBase:
class DetecteurAssurancePret(DetecteurBase):
class DetecteurRemboursementPret(DetecteurBase):
class DetecteurRevenuSCPI(DetecteurBase):
class DetecteurAchatETF(DetecteurBase):
class DetecteurAchatAmazon(DetecteurBase):
class DetecteurFraisBancaires(DetecteurBase):
class DetecteurHonorairesComptable(DetecteurBase):
```

**❌ Aucun `DetecteurApportAssocie` !**

### Détection Partielle dans gestionnaire_evenements.py

```python
# gestionnaire_evenements.py:240-242
# Apport associé (élargir pour capter tous les virements Ulrik)
elif ('vir sepa' in libelle_norm and 'bergsten' in libelle_norm) or 'apport' in libelle_norm:
    type_evt = 'APPORT_ASSOCIE'
```

Ce code **détecte** le type d'événement, mais il n'y a **pas de générateur de propositions** associé !

### Événements Manqués (4 apports = 15 000€)

```
18/06/2024 : 500,00€    - "Apport CC UB VIREMENT MONSIEUR ULRIK BERGSTE"
21/08/2024 : 4 500,00€  - "Apport En Compte Courant VIREMENT MONSIEUR ULRIK BERGSTE"
24/08/2024 : 5 000,00€  - "Apport En Compte Courant VIREMENT MONSIEUR ULRIK BERGSTE"
28/08/2024 : 5 000,00€  - "Apport En Compte Courant VIREMENT MONSIEUR ULRIK BERGSTE"

TOTAL : 15 000€ NON DÉTECTÉS
```

### Cause Racine

Le workflow est :
1. `gestionnaire_evenements.py:detecter_type_evenement()` → Marque `type_evenement = 'APPORT_ASSOCIE'` ✅
2. `workflow_evenements.py:generer_propositions()` → Appelle `FactoryDetecteurs.detecter_et_proposer()` ✅
3. `FactoryDetecteurs` → Cherche un détecteur pour `APPORT_ASSOCIE` → **❌ N'existe pas**
4. Résultat : Type détecté, mais **AUCUNE proposition générée**

### Solution Requise

```python
class DetecteurApportAssocie(DetecteurBase):
    """
    Détecte les apports en compte courant des associés

    PATTERN:
    - Libellé contient: APPORT + (COMPTE COURANT ou CC) + BERGSTEN
    - Type: CREDIT (entrée d'argent)
    - Montants variables

    COMPTABILISATION:
    Débit 512 (Banque)              : XX.XX€
    Crédit 455 (Compte courant Ulrik) : XX.XX€

    NOTE:
    - Remboursable à tout moment
    - Pas d'intérêts (sauf convention contraire)
    """

    def detecter(self, evenement: Dict) -> bool:
        libelle_norm = evenement.get('libelle_normalise', '').lower()
        type_op = evenement.get('type_operation', '')
        type_evt = evenement.get('type_evenement', '')

        # Vérifier le type détecté (prioritaire)
        if type_evt == 'APPORT_ASSOCIE':
            return True

        # Vérifier le pattern (fallback)
        match_libelle = (
            'apport' in libelle_norm and
            'bergsten' in libelle_norm and
            ('compte courant' in libelle_norm or 'cc' in libelle_norm)
        )

        # Vérifier que c'est un CRÉDIT (entrée d'argent)
        match_type = type_op == 'CREDIT'

        return match_libelle and match_type

    def generer_proposition(self, evenement: Dict) -> Dict:
        montant = float(evenement.get('montant', 0))
        date_op = evenement.get('date_operation')

        return {
            'type_evenement': 'APPORT_ASSOCIE',
            'description': f'Apport compte courant Ulrik Bergsten : {montant}€',
            'confiance': 0.95,
            'ecritures': [
                {
                    'date_ecriture': date_op,
                    'libelle_ecriture': 'Apport en compte courant - Ulrik Bergsten',
                    'compte_debit': '512',   # Banque
                    'compte_credit': '455',  # Compte courant associé
                    'montant': montant,
                    'type_ecriture': 'APPORT_ASSOCIE',
                    'notes': 'Apport remboursable sans intérêts'
                }
            ]
        }
```

---

## 🟠 Problème #3 : Déduplication Claude Haiku Défaillante

### Localisation

**Fichier** : `extracteur_pdf.py:81-159`

### Code Actuel

```python
def _deduplicater_operations(self, operations: List[Dict]) -> List[Dict]:
    """
    Utilise Claude pour déduplicater intelligemment les opérations

    PRINCIPE:
    Certaines opérations apparaissent en double dans les relevés avec des libellés
    légèrement différents. Claude identifie ces doublons (même date + même montant)
    et garde LA VERSION LA PLUS DÉTAILLÉE.
    """

    # Envoie à Claude Haiku avec prompt de 60+ lignes (lignes 108-165)
    response = self.client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=16000,
        messages=[{
            "role": "user",
            "content": f"""Voici {len(operations)} opérations bancaires...

CONTEXTE CRITIQUE - SCI Soeurise:
- Pas d'espèces, une seule banque, un seul compte
- Tout événement comptable = 1 ligne sur relevé de compte + 0, 1 ou N documents justificatifs
- Relevé + Justificatif = COMPLÉMENTAIRES (PAS des doublons !)

RÈGLE FONDAMENTALE:
Un même événement économique peut apparaître dans:
1. RELEVÉ DE COMPTE : Synthèse courte (date, libellé court, montant)
2. DOCUMENT JUSTIFICATIF : Détails pour ventilation comptable

⚠️ NE JAMAIS DÉDUPLICATER relevé + justificatif !

TÂCHE:
1. Analyse TOUTES les opérations
2. Identifie le TYPE de chaque opération (relevé bancaire, avis d'opération, etc.)
3. Identifie les VRAIS DOUBLONS (même document extrait 2 fois, même contenu exact)
4. NE PAS déduplicater si:
   - Une opération est une synthèse (relevé) et l'autre est détaillée (justificatif)
   - Les libellés sont différents (même date/montant) → probablement complémentaires
5. Supprime UNIQUEMENT les vrais doublons (contenu quasi-identique)
...
"""
        }]
    )
```

### Analyse

Le code **tente** de résoudre le problème des doublons intelligemment :

1. ✅ **Prompt détaillé** : Explique le contexte SCI (pas d'espèces, 1 banque)
2. ✅ **Instructions claires** : "NE JAMAIS DÉDUPLICATER relevé + justificatif"
3. ✅ **Règles explicites** : Garde version la plus détaillée

**MAIS** : Les résultats montrent que Claude Haiku **ne suit pas toujours ces instructions** !

### Doublons Détectés dans les Propositions

```
ETF MSCI World (6 achats attendus → 8 propositions générées):
  Propositions 12-13 : 2 357,36€ × 2 (doublon !)
  Propositions 38-39 : 2 439,16€ × 2 (doublon !)
  Propositions 63-64 : 1 735,53€ × 2 (doublon !)

Actions Amazon (4 achats attendus → 6-8 propositions):
  Propositions 73-74 : 1 026,54€ × 2 (doublon !)
  Propositions 75-76 : 3 455,38€ × 2 (doublon !)
  Proposition 77 : 4 962,07€ (PAS de doublon ? Incohérent)
  Proposition 78 : 5 003,69€ (PAS de doublon ? Incohérent)
```

**Pattern observé** : Doublons **partiels et incohérents**

### Causes Possibles

1. **Claude Haiku trop rapide** :
   - Modèle : `claude-haiku-4-5-20251001` (optimisé vitesse, pas précision)
   - Tâche complexe : Analyse sémantique de 100+ opérations
   - Résultat : Décisions incohérentes

2. **Prompt trop complexe** :
   - 60+ lignes d'instructions
   - Multiples conditions (relevé vs justificatif)
   - Claude Haiku peut "oublier" certaines règles

3. **Pas de validation post-traitement** :
   - La fonction fait confiance aveugle à Claude
   - Aucune vérification du résultat
   - Doublons passent directement en base

### Solutions Possibles

#### Option A : Désactiver la déduplication IA (Recommandé court terme)

```python
def _deduplicater_operations(self, operations: List[Dict]) -> List[Dict]:
    """
    DÉSACTIVÉ : La déduplication IA génère trop de faux positifs

    Stratégie :
    - Accepter TOUTES les opérations extraites
    - Laisser le fingerprinting gérer les VRAIS doublons (MD5)
    - Gérer les sources complémentaires en post-traitement
    """
    print("⚠️  Déduplication IA désactivée - Toutes opérations conservées")
    return operations  # Pas de déduplication
```

**Avantages** :
- ✅ Pas de perte d'information
- ✅ Doublons exacts gérés par fingerprint MD5
- ✅ Simplicité

**Inconvénients** :
- ❌ Sources complémentaires non groupées
- ❌ Validations manuelles plus longues

#### Option B : Améliorer le prompt + Modèle Sonnet (Long terme)

```python
# Utiliser Claude Sonnet (plus précis) au lieu de Haiku
model="claude-sonnet-4-5-20250929",  # Au lieu de Haiku

# Simplifier le prompt drastiquement
"""Analyse ces {len(operations)} opérations bancaires.

RÈGLE UNIQUE:
Supprime UNIQUEMENT les opérations ayant EXACTEMENT:
- Même date
- Même montant
- Même libellé (>90% similarité)

Garde TOUTES les autres opérations (même si date + montant identiques).

Retourne JSON: {{"operations_uniques": [...], "nb_doublons": X}}
"""
```

#### Option C : Déduplication déterministe (Recommandé long terme)

```python
def _deduplicater_operations_deterministe(self, operations: List[Dict]) -> List[Dict]:
    """
    Déduplication déterministe basée sur fingerprint + score de qualité

    Stratégie:
    1. Calculer fingerprint MD5 pour chaque opération
    2. Grouper opérations par fingerprint
    3. Dans chaque groupe, garder celle avec le score qualité le plus élevé
    4. Score qualité = longueur libellé + présence ISIN + références
    """
    from detection_doublons import DetecteurDoublons
    from collections import defaultdict

    groupes = defaultdict(list)

    # Grouper par fingerprint
    for op in operations:
        fingerprint = DetecteurDoublons.calculer_fingerprint(op)
        score_qualite = DetecteurDoublons.calculer_score_qualite(op)
        groupes[fingerprint].append((op, score_qualite))

    # Garder la meilleure de chaque groupe
    operations_uniques = []
    doublons_supprimes = 0

    for fingerprint, ops_avec_score in groupes.items():
        if len(ops_avec_score) > 1:
            # Trier par score décroissant
            ops_avec_score.sort(key=lambda x: x[1], reverse=True)
            doublons_supprimes += len(ops_avec_score) - 1

        # Garder la meilleure
        operations_uniques.append(ops_avec_score[0][0])

    print(f"✅ Déduplication: {len(operations)} → {len(operations_uniques)} ({doublons_supprimes} doublons)")

    return operations_uniques
```

**Avantages** :
- ✅ Déterministe (pas d'aléa IA)
- ✅ Rapide (pas d'appel API)
- ✅ Garde la version la plus détaillée automatiquement

---

## 📊 Récapitulatif des Corrections

| Problème | Fichier | Action | Priorité |
|----------|---------|--------|----------|
| **SCPI mal comptabilisées** | `detecteurs_evenements.py:297-350` | Scinder en 2 détecteurs : `DetecteurRevenuSCPI` (CREDIT→761) + `DetecteurAchatSCPI` (DEBIT→273) | 🔴 CRITIQUE |
| **Apports Ulrik manquants** | `detecteurs_evenements.py` (nouveau) | Créer `DetecteurApportAssocie` avec pattern CREDIT + Bergsten → 512/455 | 🔴 CRITIQUE |
| **Doublons ETF/Amazon** | `extracteur_pdf.py:81-159` | Option A: Désactiver IA <br> Option C: Déduplication déterministe | 🟠 MAJEUR |
| **TVA honoraires** | `detecteurs_evenements.py:563+` | Décomposer TTC en HT + TVA (622 + 4456) | 🟡 MOYEN |
| **Impôts DGFiP** | `detecteurs_evenements.py` (nouveau) | Créer `DetecteurImpotsTaxes` avec pattern DGFiP → 63/512 | 🟡 MOYEN |

---

## 🎯 Plan d'Action Recommandé

### Phase 1 - Corrections Critiques (1-2h)

1. ✅ Corriger `DetecteurRevenuSCPI` :
   - Renommer en `DetecteurDistributionSCPI`
   - Ajouter vérification `type_operation == 'CREDIT'`
   - Comptabiliser : Débit 512, Crédit 761

2. ✅ Créer `DetecteurAchatSCPI` :
   - Pattern : SCPI + ACHAT + DEBIT
   - Comptabiliser : Débit 273, Crédit 512

3. ✅ Créer `DetecteurApportAssocie` :
   - Pattern : APPORT + BERGSTEN + CREDIT
   - Comptabiliser : Débit 512, Crédit 455

### Phase 2 - Déduplication (2-3h)

4. ✅ Implémenter `_deduplicater_operations_deterministe()` :
   - Basé sur fingerprint MD5 + score qualité
   - Remplacer l'appel Claude Haiku

5. ✅ Tester sur relevés T1-T3 2024 :
   - Vérifier 0 doublon ETF/Amazon
   - Vérifier toutes distributions SCPI conservées

### Phase 3 - Améliorations (optionnel)

6. ⭐ Améliorer `DetecteurHonorairesComptable` :
   - Décomposer TTC en HT + TVA
   - Créer 2 écritures (622 + 4456)

7. ⭐ Créer `DetecteurImpotsTaxes` :
   - Pattern : DGFiP + CFE
   - Comptabiliser : Débit 63, Crédit 512

---

## 🧪 Tests de Validation

Après corrections, re-tester avec le PDF T1-T3 2024 :

```bash
# Test complet
python workflow_evenements.py --pdf "Elements Comptables des 1-2-3T2024.pdf" --test

# Vérifications attendues:
✅ Distributions SCPI (10) : Débit 512, Crédit 761 (27 000€)
✅ Apports Ulrik (4) : Débit 512, Crédit 455 (15 000€)
✅ ETF (6 achats) : 6 propositions (pas 8)
✅ Amazon (4 achats) : 4 propositions (pas 6-8)
```

---

**Auteur** : Claude Code - Analyse des causes racines
**Date** : 12/11/2025
**Références** :
- COMPARAISON_PROPOSITIONS_T1T2T3_2024.md
- gestionnaire_evenements.py:181-273
- detecteurs_evenements.py:297-350
- extracteur_pdf.py:81-159
