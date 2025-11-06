# Corrections et Compléments - Analyse Événements Comptables 2024

**Date** : 05/11/2025
**Auteur** : Corrections apportées par Ulrik Bergsten

---

## ✅ Corrections Critiques

### 1. Période couverte : 9 MOIS (pas 10)

**ERREUR INITIALE** : "10 mois (05/12/2023 au 04/10/2024)"

**CORRECTION** :
- **Période réelle** : Janvier 2024 à Septembre 2024 = **9 mois**
- Le premier relevé LCL chevauche décembre 2023 et janvier 2024
- Les événements à traiter = **UNIQUEMENT 2024** (du 01/01/2024 au 30/09/2024)

### 2. Assurance Emprunteur : UN SEUL prêt concerné

**ERREUR INITIALE** : "Deux prélèvements d'assurance pour deux prêts"

**CORRECTION** :
- **Assurance UNIQUEMENT pour le prêt AMORTISSABLE** (Prêt LCL - BRM0911AH)
- **PAS d'assurance pour le prêt IN FINE** (Prêt INVESTIMUR - BRLZE11AQ)
  - Raison : Garanti par des assurances vie EXTERNES à Soeurise
  - Assurés : Emma, Pauline et Ulrik (hors périmètre comptable Soeurise)

**Détail des cotisations** :
- Emma : 66,58€/mois
- Pauline : 20,99€/mois
- Différence due à l'état de santé (critères actuariels)
- **Mais couverture identique : 50% Emma / 50% Pauline en cas de décès**

**TOTAL mensuel** : 87,57€ (et non 87,57€ pour "deux prêts")

### 3. Distribution de capital Épargne Pierre : REVENU EXCEPTIONNEL

**ERREUR INITIALE** : "Crédit 106 (Réserves) ou Crédit 280 (réduction valeur titres)"

**CORRECTION** :
- Les 601,00€ de "Distribution de capital" = **REVENU EXCEPTIONNEL**
- Comptabilisation :
  ```
  Débit 512 (Banque) : 601,00€
  Crédit 777 (Produits exceptionnels - Distribution capital SCPI) : 601,00€
  ```

**Justification** : Pour Soeurise (SCI à l'IS), cette distribution reste un produit imposable

### 4. Bulletins SCPI et fiscalité : SCI à l'IS

**PRÉCISION IMPORTANTE** :
- Soeurise = SCI à l'**Impôt sur les Sociétés (IS)**
- ≠ SCI à l'Impôt sur le Revenu (IR)

**Conséquences comptables** :
- Les prélèvements sociaux indiqués "0,00€" sur les bulletins ne sont **pas pertinents**
- La SCPI paie les prélèvements pour les associés personnes physiques uniquement
- Soeurise doit elle-même gérer son IS (et n'a pas de prélèvements sociaux sur les revenus SCPI)

### 5. Portefeuille valeurs mobilières : Détail au bilan

**ERREUR INITIALE** : Suggérer un montant global au bilan

**CORRECTION** :
- **Bilan d'ouverture 2024** : Détailler ligne par ligne
  - Nombre de parts ETF MSCI World
  - Nombre d'actions Amazon
  - Prix d'acquisition unitaire
  - Valeur comptable totale

**Principe comptable** :
- ✅ Comptabiliser au **coût d'acquisition** (prix d'achat + frais)
- ❌ **JAMAIS** de plus-values latentes au bilan
- ❌ **JAMAIS** de plus-values latentes au compte d'exploitation
- ✅ Plus ou moins-values **UNIQUEMENT lors de la VENTE**

### 6. Portefeuille au 23/08/2024 : Chiffres erronés

**ERREUR INITIALE** : J'ai mal lu les données de la page 38

**CORRECTION À FAIRE** :
- Revoir les vrais chiffres du portefeuille
- Extraire correctement :
  - Nombre de titres par ligne
  - Valeur comptable vs valeur de marché
  - Plus-values latentes (pour info uniquement, pas comptabilisées)

### 7. Apports en compte courant : 15 000€ (pas 14 500€)

**ERREUR INITIALE** : "14 500€ en T3 2024"

**CORRECTION** :
- T1 2024 : 500,00€ (18/06/2024)
- T3 2024 août : 4 500,00€ + 5 000,00€ + 5 000,00€ = 14 500,00€
- **TOTAL T1+T2+T3 2024 : 15 000,00€**

**Bilan compte courant Ulrik** :
- Solde initial 01/01/2024 : 120,00€ (bilan 2023)
- Apports 2024 : +15 000,00€
- **Solde fin septembre 2024 : 15 120,00€**

### 8. TVA : Soeurise NON soumise à TVA

**ERREUR INITIALE** : Proposer compte 4456 (TVA déductible)

**CORRECTION** :
- Soeurise **n'est PAS soumise à la TVA**
- Conséquence : **AUCUNE TVA déductible**

**Comptabilisation des factures** :
```
Exemple : Facture comptable 213,60€ TTC
AVANT (FAUX) :
  Débit 622 : 178,00€
  Débit 4456 (TVA déductible) : 35,60€
  Crédit 512 : 213,60€

APRÈS (CORRECT) :
  Débit 622 : 213,60€  ← TTC intégral
  Crédit 512 : 213,60€
```

---

## 📊 Compléments à Intégrer

### 9. Grand Livre : À prévoir explicitement

**MANQUE DANS L'ANALYSE INITIALE** :

Le système doit produire un **Grand Livre comptable** :
- Liste chronologique de toutes les écritures par compte
- Permettre d'auditer chaque mouvement
- Format standard pour expert-comptable

**Structure Grand Livre** :
```
Compte 512 - Banque LCL
Date       | Libellé                        | Débit    | Crédit   | Solde
-----------|--------------------------------|----------|----------|----------
01/01/2024 | Solde initial                  |          |          | 1 997,28
15/01/2024 | Prêt LCL ECH 15/01/24         |          |  258,33  | 1 738,95
15/01/2024 | Prêt INVESTIMUR ECH 15/01/24  |          | 1166,59  |   572,36
...
```

### 10. Compte d'Exploitation (Compte de Résultat)

**MANQUE DANS L'ANALYSE INITIALE** :

En plus du **Bilan** (situation patrimoniale), produire le **Compte d'Exploitation 2024** :

```
COMPTE D'EXPLOITATION 2024 (9 mois)

PRODUITS D'EXPLOITATION
  761 - Revenus SCPI                    : ~19 500€
  777 - Produits exceptionnels (capital):    601€
  Total Produits                        : ~20 101€

CHARGES D'EXPLOITATION
  616 - Assurances emprunteur           :    788€ (9 mois × 87,57€)
  622 - Honoraires expert-comptable     :  1 161€
  625 - Frais administratifs (LEI)      :     50€
  627 - Frais bancaires                 :    110€ (9 mois × 12,18€)
  661 - Charges d'intérêts prêts        : ~3 500€ (estimation)
  Total Charges                         : ~5 609€

RÉSULTAT D'EXPLOITATION (avant impôt)  : ~14 492€
```

### 11. Financement des investissements : Sources multiples

**PRÉCISION** :

Les investissements 2024 (~20 000€ ETF + Actions) sont financés par :

1. **Apports en compte courant** : 15 000€
2. **Cash flow libre de l'activité** : ~5 000€
   - Revenus SCPI : ~20 000€
   - Charges courantes : ~2 100€ (hors intérêts)
   - Cash flow disponible : ~17 900€
   - Dont remboursement capital prêts : ~12 900€
   - **Reste disponible : ~5 000€**

---

## 🔧 Spécifications Techniques pour le Développement

### 12. Workflow de production : PDF complet fourni

**SPECIFICATION** :
- L'utilisateur fournira **TOUJOURS un PDF complet** (tous les relevés + documents)
- Le système doit parser l'intégralité et détecter tous les événements
- Pas de traitement incrémental fichier par fichier

### 13. Mécanisme de nettoyage BD (debugging)

**BESOIN** : Pouvoir annuler proprement une tentative de traitement ratée

**FONCTIONNALITÉ À DÉVELOPPER** :
```python
def nettoyer_tentative_ratee(periode: str):
    """
    Supprime proprement les écritures et événements d'une période
    pour permettre un nouveau traitement

    Args:
        periode: "2024-T1", "2024-T2", "2024-T3", etc.

    Actions:
        1. Identifier toutes les écritures de la période
        2. Identifier tous les événements de la période
        3. Supprimer en cascade (événements → écritures)
        4. Logger l'action (audit trail)
        5. Confirmer auprès de l'utilisateur
    """
```

**Cas d'usage** :
- Phase de test/debug : tester plusieurs fois le parsing
- Correction d'erreurs : retraiter après correction du code
- Ajustements manuels : annuler et recommencer

### 14. Détection de doublons entre phases

**BESOIN** : Éviter de retraiter des événements déjà comptabilisés

**FONCTIONNALITÉ À DÉVELOPPER** :
```python
def detecter_evenement_deja_traite(evenement: Dict) -> bool:
    """
    Vérifie si un événement a déjà été traité

    Critères d'unicité:
        - date_operation
        - libelle (normalisé)
        - montant
        - type_operation (DEBIT/CREDIT)

    Returns:
        True si déjà traité, False sinon
    """
```

**Stratégie par phase** :
- **Phase 1** : Traite assurances + frais bancaires + comptable
  - Marque les événements traités avec `phase_traitement = 1`
- **Phase 2** : Traite prêts + apports
  - Vérifie que `phase_traitement IS NULL OR phase_traitement < 2`
  - Marque les nouveaux avec `phase_traitement = 2`
- **Phase 3** : Traite SCPI + valeurs mobilières + reste
  - Vérifie que `phase_traitement IS NULL OR phase_traitement < 3`
  - Marque les nouveaux avec `phase_traitement = 3`

**Table `evenements_comptables` enrichie** :
```sql
ALTER TABLE evenements_comptables ADD COLUMN phase_traitement INTEGER;
ALTER TABLE evenements_comptables ADD COLUMN fingerprint VARCHAR(64);
-- fingerprint = MD5(date + libelle_normalise + montant + type)
```

---

## 📋 TODO : Corrections à Appliquer

### Dans le code

- [ ] Corriger la période : 9 mois (jan-sep 2024)
- [ ] Assurance : UN SEUL prêt concerné
- [ ] Distribution capital : Compte 777 (produit exceptionnel)
- [ ] TVA : Supprimer tout compte 4456 (TVA déductible)
- [ ] Apports CC : Corriger total à 15 000€
- [ ] Ajouter colonne `phase_traitement` à `evenements_comptables`
- [ ] Ajouter colonne `fingerprint` pour détection doublons

### Dans la documentation

- [ ] Mettre à jour `ANALYSE_EVENEMENTS_COMPTABLES_2024.md`
- [ ] Créer `SPECIFICATIONS_TECHNIQUES.md`
- [ ] Documenter le workflow de nettoyage BD
- [ ] Documenter la détection de doublons

### Nouveaux modules à développer

- [ ] `generateur_grand_livre.py` : Génération du Grand Livre
- [ ] `generateur_compte_exploitation.py` : Compte de résultat
- [ ] `nettoyage_bd.py` : Outils de nettoyage/rollback
- [ ] `detection_doublons.py` : Détection événements déjà traités
- [ ] `portefeuille_manager.py` : Suivi détaillé valeurs mobilières

---

**Statut** : Document de corrections validé
**Prochaine étape** : Créer les spécifications techniques complètes
