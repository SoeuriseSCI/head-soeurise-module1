# Précisions : Déclenchement Extournes - Quand et Comment ?

## 🤔 Question Clé : "Automatique" = Quand Exactement ?

Le document parle d'"extourne automatique" mais n'est pas assez précis. Clarifions.

---

## 🎯 Deux Approches Possibles

### Approche A : Extourne Immédiate (Recommandée)

**Principe** : Créer cutoff + extourne **dans la même transaction** lors du traitement de l'email.

**Exemple revenus SCPI** :
```
Janvier 2025 - Email Ulrik reçu : "Distribution T4 2024 : 7 356€"

→ DetecteurAnnonceProduitARecevoir génère DEUX écritures :

   1. Cutoff (datée 31/12/2024, exercice 2024) :
      Débit 4181 / Crédit 761 : 7 356€
      Type: CUTOFF_PRODUIT_A_RECEVOIR

   2. Extourne (datée 01/01/2025, exercice 2025) :
      Débit 761 / Crédit 4181 : 7 356€
      Type: EXTOURNE_CUTOFF

Résultat : Cutoff + extourne créés ensemble dans le même flux
```

**Avantages** :
- ✅ Vraiment automatique (pas d'action manuelle)
- ✅ Atomique (cutoff et extourne = paire indissociable)
- ✅ Simple pour l'utilisateur (rien à faire)
- ✅ Pas de risque d'oubli

**Inconvénients** :
- ⚠️ Nécessite que l'exercice N+1 existe (création auto si besoin)
- ⚠️ Deux écritures dans des exercices différents (transaction unique)

---

### Approche B : Extourne en Deux Temps (Actuellement Documentée)

**Principe** : Créer cutoff lors du traitement email, puis exécuter script séparé pour extournes.

**Exemple revenus SCPI** :
```
Janvier 2025 - Email Ulrik reçu : "Distribution T4 2024 : 7 356€"

→ DetecteurAnnonceProduitARecevoir génère UNE écriture :
   Cutoff (datée 31/12/2024, exercice 2024) :
   Débit 4181 / Crédit 761 : 7 356€
   Type: CUTOFF_PRODUIT_A_RECEVOIR

Puis MANUELLEMENT :
→ python generateur_extournes.py --exercice 2024 --execute
   Crée extourne 01/01/2025
```

**Avantages** :
- ✅ Séparation claire (cutoff ≠ extourne)
- ✅ Contrôle manuel (peut vérifier avant extourne)
- ✅ Peut générer toutes les extournes d'un coup

**Inconvénients** :
- ❌ Pas vraiment "automatique" (action manuelle requise)
- ❌ Risque d'oubli
- ❌ Complexité pour l'utilisateur

---

## 💡 Recommandation : Approche A (Extourne Immédiate)

Pour que ce soit **vraiment automatique**, je recommande **l'Approche A** :

### Pour Revenus SCPI (761/4181)

**Déclencheur** : Email Ulrik reçu par _Head (janvier N+1)

**Action** : `DetecteurAnnonceProduitARecevoir.generer_proposition()`

**Génère** :
1. Cutoff 31/12/2024 (exercice 2024)
2. Extourne 01/01/2025 (exercice 2025) **← Dans la foulée**

**Timing** : Immédiat lors du traitement de l'email

---

### Pour Honoraires (6226/4081)

**Déclencheur** : Email Ulrik ou estimation (décembre N)

**Action** : `DetecteurAnnonceHonorairesARegler.generer_proposition()`

**Génère** :
1. Cutoff 31/12/2024 (exercice 2024)
2. Extourne 01/01/2025 (exercice 2025) **← Dans la foulée**

**Timing** : Immédiat lors du traitement de l'email

---

### Pour Intérêts Courus (661/1688)

**Déclencheur** : AUTOMATIQUE lors de la première échéance de prêt en janvier N+1

**Action** : `DetecteurRemboursementPret._declencher_cutoff_interets_si_necessaire()`

**Workflow automatique** :
1. Détection échéance de prêt en janvier N+1
2. Vérification : cutoff intérêts N existe déjà ?
3. Si NON → Appel automatique `CalculateurInteretsCourus`
4. Calcul pour les 2 prêts (LCL + INVESTIMUR)
5. Création cutoff 31/12/N + extourne 01/01/N+1 **← Dans la même proposition**

**Génère** :
1. Écritures remboursement (intérêts + capital)
2. Cutoff 31/12/2024 (exercice 2024) pour les 2 prêts
3. Extourne 01/01/2025 (exercice 2025) pour les 2 prêts **← Dans la foulée**

**Timing** : Lors du traitement de la première échéance de janvier N+1

**Exemple** :
```
Janvier 2025 : Traitement échéance LCL 12/01/2025
→ Détecte : janvier 2025
→ Vérifie : cutoff 2024 existe ? NON
→ DÉCLENCHE : Calcul intérêts courus 2024
→ CRÉE : 6 écritures au total
  - 2 écritures échéance (intérêts + capital)
  - 4 écritures cutoff intérêts (2 cutoffs + 2 extournes)
```

**Commande manuelle** (fallback si besoin réparation) :
```bash
python cutoff_extourne_interets.py --exercice 2024 --execute
```

---

## 🔧 Cas d'Usage de `generateur_extournes.py`

Avec l'Approche A, `generateur_extournes.py` devient un **utilitaire de secours** :

### Cas d'Usage 1 : Réparation

**Situation** : Des cutoffs ont été créés SANS extournes (bug, ancien code, etc.)

**Solution** :
```bash
python generateur_extournes.py --exercice 2024 --execute
```

→ Génère les extournes manquantes pour l'exercice 2024

---

### Cas d'Usage 2 : Migration

**Situation** : Passage de l'ancien système (sans extourne) au nouveau

**Solution** :
```bash
python generateur_extournes.py --tous --execute
```

→ Génère extournes pour TOUS les exercices cloturés

---

### Cas d'Usage 3 : Vérification

**Situation** : Vérifier quelles extournes seraient générées (dry-run)

**Solution** :
```bash
python generateur_extournes.py --exercice 2024
```

→ Simule sans créer (affiche ce qui serait fait)

---

### Cas d'Usage 4 : Cutoffs Créés Manuellement

**Situation** : Un cutoff a été créé manuellement en base (hors système détecteurs)

**Solution** :
```bash
python generateur_extournes.py --exercice 2024 --execute
```

→ Génère l'extourne correspondante

---

## 📋 Implémentation Recommandée

### Modification `DetecteurAnnonceProduitARecevoir`

```python
def generer_proposition(self, evenement: Dict) -> Optional[Dict]:
    """Génère cutoff + extourne dans la foulée"""

    # ... extraction données ...

    annee = 2024
    montant = 7356.00

    # Date cutoff : 31/12/N
    date_cutoff = date(annee, 12, 31)

    # Date extourne : 01/01/N+1
    date_extourne = date(annee + 1, 1, 1)

    return {
        'type_evenement': 'CUTOFF_PRODUIT_A_RECEVOIR',
        'description': f'Cutoff revenus SCPI T4 {annee}: {montant}€ + extourne',
        'confiance': 0.95,
        'ecritures': [
            # Écriture 1 : Cutoff 31/12/N
            {
                'date_ecriture': date_cutoff,
                'exercice_id': exercice_N,  # Exercice 2024
                'libelle_ecriture': f'Cutoff {annee} - Distribution T4',
                'compte_debit': '4181',
                'compte_credit': '761',
                'montant': montant,
                'type_ecriture': 'CUTOFF_PRODUIT_A_RECEVOIR'
            },
            # Écriture 2 : Extourne 01/01/N+1
            {
                'date_ecriture': date_extourne,
                'exercice_id': exercice_N_plus_1,  # Exercice 2025
                'libelle_ecriture': f'Extourne - Cutoff {annee} - Distribution T4',
                'compte_debit': '761',      # INVERSION
                'compte_credit': '4181',    # INVERSION
                'montant': montant,
                'type_ecriture': 'EXTOURNE_CUTOFF'
            }
        ]
    }
```

**Note importante** : Nécessite que l'exercice N+1 existe. Si pas encore créé, le créer automatiquement.

---

## 🎯 Synthèse : Qui Fait Quoi et Quand ?

| Cutoff Type | Déclencheur | Quand | Cutoff | Extourne | Automatique ? |
|-------------|-------------|-------|--------|----------|---------------|
| **Revenus SCPI** | Email Ulrik | Janvier N+1 | ✅ Dans flux email | ✅ Dans flux email | ✅ OUI (100%) |
| **Honoraires** | Email/Estimation | Décembre N ou janvier N+1 | ✅ Dans flux email | ✅ Dans flux email | ✅ OUI (100%) |
| **Intérêts courus** | 1ère échéance janvier | Janvier N+1 | ✅ Dans flux échéance | ✅ Dans flux échéance | ✅ OUI (100%) |

**generateur_extournes.py** : Utilitaire de secours/réparation uniquement

**SYSTÈME 100% AUTOMATIQUE** :
- Aucune action manuelle requise pour les cutoffs
- Déclenchement au bon moment (janvier N+1)
- Cutoff + extourne créés ensemble dans la foulée

---

## ⚠️ Points d'Attention

### Gestion de l'Exercice N+1

Quand on crée une extourne 01/01/N+1 en janvier N+1, l'exercice N+1 peut ne pas encore exister.

**Solutions** :
1. **Création automatique** : Le détecteur crée l'exercice N+1 s'il n'existe pas
2. **Vérification** : Vérifier existence avant, sinon erreur claire
3. **Différé** : Créer uniquement cutoff, extourne par script plus tard (Approche B)

**Recommandation** : **Création automatique** pour être vraiment automatique.

```python
# Créer exercice N+1 si nécessaire
exercice_suivant = session.query(ExerciceComptable).filter_by(annee=annee + 1).first()
if not exercice_suivant:
    exercice_suivant = ExerciceComptable(
        annee=annee + 1,
        date_debut=date(annee + 1, 1, 1),
        date_fin=date(annee + 1, 12, 31),
        statut='OUVERT'
    )
    session.add(exercice_suivant)
    session.flush()
```

---

**Voulez-vous que je modifie le code pour implémenter l'Approche A (extourne immédiate) ?**
