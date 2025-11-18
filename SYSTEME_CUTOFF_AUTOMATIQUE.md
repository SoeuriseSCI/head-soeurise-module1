# 🔄 Système de Cut-off Automatique

**Date** : 18 novembre 2025
**Version** : 1.0
**Statut** : Implémenté, tests unitaires OK, en attente déploiement

---

## 📋 Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [Problème résolu](#problème-résolu)
3. [Architecture](#architecture)
4. [Fonctionnement détaillé](#fonctionnement-détaillé)
5. [Utilisation](#utilisation)
6. [Tests](#tests)
7. [Prochaines étapes](#prochaines-étapes)
8. [FAQ](#faq)

---

## 🎯 Vue d'Ensemble

### Qu'est-ce qu'un Cut-off Comptable ?

En **comptabilité d'engagement**, les produits et charges doivent être comptabilisés dans l'exercice où ils sont **acquis/engagés**, indépendamment de leur encaissement/paiement.

**Exemple SCPI :**
- **31/12/2023** : Revenus SCPI T4 2023 sont acquis mais pas encore versés
- **29/01/2024** : Versement effectif des revenus

**Principe** : Les revenus T4 2023 doivent être comptabilisés en **2023** (exercice où acquis), pas en 2024 (exercice où encaissés).

### Solution Automatique

Le système détecte automatiquement :
1. **Fin d'année** : Email annonçant revenus T4 → Créer créance (Débit 4181 / Crédit 761)
2. **Début d'année** : Paiement SCPI → Chercher créance → Solder (Débit 512 / Crédit 4181)

**Résultat** : Revenus comptabilisés dans le bon exercice, sans intervention manuelle.

---

## ❌ Problème Résolu

### Avant (Problème)

**Situation Bilan 2023/2024 :**

```
31/12/2023 - Bilan d'ouverture 2024:
  Débit 412 Créances diverses : 7 356 € ← Créance T4 2023
  Crédit 89 Bilan ouverture   : 7 356 €

29/01/2024 - Paiement SCPI:
  Débit 512 Banque            : 7 356 € ← Nouveau produit !
  Crédit 761 Revenus SCPI     : 7 356 €

Résultat: Créance 412 jamais soldée + Nouveau produit 761
→ DOUBLON : Revenus T4 2023 comptés DEUX FOIS
```

**Problèmes identifiés :**
1. Créance 412 (Créances douteuses) → Compte incorrect, devrait être 4181 (Produits à recevoir)
2. Créance jamais soldée (reste 7 356 € en 412)
3. Paiement janvier 2024 crée un nouveau produit 761 au lieu de solder la créance
4. Revenus T4 2023 comptés 2 fois : une fois en créance, une fois en produit

### Après (Solution)

**Workflow automatique :**

```
20/12/2023 - Email annonce revenus T4:
  "Distribution T4 2023 de 7 356 € sera versée le 29/01/2024"
  → Détecteur: DetecteurAnnonceProduitARecevoir

31/12/2023 - Écriture générée automatiquement:
  Débit 4181 Produits à recevoir : 7 356 €
  Crédit 761 Revenus SCPI        : 7 356 €

29/01/2024 - Paiement SCPI:
  → Détecteur: DetecteurDistributionSCPI
  → Rapprocheur: Cherche créance 4181 ≈ 7 356 €
  → Créance trouvée !

29/01/2024 - Écriture générée automatiquement:
  Débit 512 Banque               : 7 356 €
  Crédit 4181 Produits à recevoir: 7 356 € ← Solde la créance

Résultat: Créance 4181 soldée + Aucun nouveau produit
→ CORRECT : Revenus T4 2023 comptés UNE SEULE FOIS (en 2023)
```

---

## 🏗️ Architecture

### Modules Créés

#### 1. `FORMAT_EMAIL_PRODUITS_A_RECEVOIR.md`
**Rôle** : Spécification formats emails d'annonce

**Contenu :**
- 3 types d'emails supportés (annonce simple, bulletin annuel, notification)
- Règles de détection automatique (patterns)
- Anti-patterns (emails à ignorer)
- Template email pour Ulrik

#### 2. `DetecteurAnnonceProduitARecevoir` (dans `detecteurs_evenements.py`)
**Rôle** : Détecter emails annonçant revenus SCPI T4 en fin d'année

**Pattern détection :**
```python
- type_source == 'EMAIL'
- Contient: SCPI + T4/4T/Q4 + Distribution/Revenus
- Montant présent (regex)
- Intention future: "prévisionnelle", "prévue", "sera versée"
- OU Période 15-31 décembre
```

**Écriture générée :**
```python
Date: 31/12/N (toujours fin exercice)
Débit 4181 Produits à recevoir : montant_annoncé
Crédit 761 Revenus SCPI        : montant_annoncé
```

#### 3. `rapprocheur_cutoff.py`
**Rôle** : Module de rapprochement automatique créances/dettes

**Fonctions principales :**

**`chercher_creance(montant, tolerance=2€)`**
- Cherche écriture avec compte_debit = 4181
- Dans exercice précédent
- Montant dans tolérance (±2€ ou ±2%)
- Non encore soldée

**`generer_ecriture_soldage_creance(creance, montant_encaisse)`**
- Cas 1 (montant exact) : 1 écriture de soldage
- Cas 2 (écart) : 2 écritures (soldage + ajustement)

**`rapprocher_encaissement(montant, date)`** (high-level)
- Cherche créance correspondante
- Génère proposition d'écritures
- Retourne None si aucune créance

#### 4. Modification `DetecteurDistributionSCPI`
**Rôle** : Intégrer rapprocheur avant création produit

**Nouveau workflow :**
```python
def generer_proposition(self, evenement):
    # ÉTAPE 1: Tenter rapprochement
    rapprocheur = RapprocheurCutoff(self.session)
    proposition_rapprochement = rapprocheur.rapprocher_encaissement(...)

    # ÉTAPE 2: Si créance trouvée → Retourner soldage
    if proposition_rapprochement:
        return proposition_rapprochement

    # ÉTAPE 3: Sinon → Créer nouveau produit (comportement normal)
    return {
        'type_evenement': 'REVENU_SCPI',
        'ecritures': [{'compte_debit': '512', 'compte_credit': '761', ...}]
    }
```

#### 5. `test_cutoff_automatique.py`
**Rôle** : Tests unitaires complets

**Tests :**
1. Détection email annonce (4 scénarios)
2. Recherche créance (3 scénarios)
3. Génération écritures soldage (3 cas: exact, écart+, écart-)
4. Workflow complet high-level
5. Détecteur SCPI avec rapprochement

---

## ⚙️ Fonctionnement Détaillé

### Workflow Complet Année N

#### Phase 1: Fin d'Année (Décembre N)

**1. Réception Email Annonce**
```
De: scpi@epargne-pierre.fr
Objet: Distribution T4 2024 - SCPI Épargne Pierre
Date: 20/12/2024

Votre distribution du 4T 2024 de 7 356,00 € sera versée le 29/01/2025.
```

**2. Détection Automatique**
- Module : `DetecteurAnnonceProduitARecevoir`
- Vérifie : type_source='EMAIL', pattern SCPI+T4, montant, intention future
- Résultat : ✅ Détecté

**3. Génération Proposition**
```json
{
  "type_evenement": "ANNONCE_PRODUIT_A_RECEVOIR_SCPI",
  "description": "Revenus SCPI T4 2024 à recevoir : 7 356 €",
  "confiance": 0.90,
  "ecritures": [
    {
      "date_ecriture": "2024-12-31",
      "libelle_ecriture": "SCPI Épargne Pierre - Revenus T4 2024 à recevoir",
      "compte_debit": "4181",
      "compte_credit": "761",
      "montant": 7356.00
    }
  ]
}
```

**4. Validation et Écriture**
- Utilisateur valide la proposition
- Écriture créée au 31/12/2024
- Compte 4181 : +7 356 € (créance)
- Compte 761 : +7 356 € (produit exercice 2024)

#### Phase 2: Début d'Année (Janvier N+1)

**1. Réception Paiement Bancaire**
```
Date: 29/01/2025
Libellé: VIREMENT SCPI EPARGNE PIERRE DISTRIBUTION TRIMESTRIELLE
Crédit: 7 356,00 €
```

**2. Détection Automatique**
- Module : `DetecteurDistributionSCPI`
- Vérifie : pattern SCPI+DISTRIBUTION, type=CREDIT
- Résultat : ✅ Détecté

**3. Rapprochement Automatique**
```python
# DetecteurDistributionSCPI.generer_proposition()
rapprocheur = RapprocheurCutoff(session)
proposition = rapprocheur.rapprocher_encaissement(
    montant=7356.00,
    date_operation='2025-01-29'
)
# → Cherche créance 4181 ≈ 7 356 € dans exercice 2024
# → Créance trouvée ! ID 363
```

**4. Génération Proposition Soldage**
```json
{
  "type_evenement": "ENCAISSEMENT_PRODUIT_A_RECEVOIR",
  "description": "Encaissement SCPI Épargne Pierre (soldage créance)",
  "confiance": 0.95,
  "ecritures": [
    {
      "date_ecriture": "2025-01-29",
      "libelle_ecriture": "SCPI Épargne Pierre - Encaissement revenus T4 (soldage créance)",
      "compte_debit": "512",
      "compte_credit": "4181",
      "montant": 7356.00
    }
  ],
  "metadata": {
    "creance_id": 363,
    "creance_montant": 7356.00,
    "ecart": 0.00
  }
}
```

**5. Validation et Écriture**
- Utilisateur valide la proposition
- Écriture créée au 29/01/2025
- Compte 512 : +7 356 € (banque)
- Compte 4181 : -7 356 € (créance soldée → 0€)

**Résultat Final :**
- ✅ Compte 4181 : 0€ (créance soldée)
- ✅ Compte 761 : 7 356 € comptabilisé en 2024 (exercice correct)
- ✅ Compte 512 : +7 356 € en 2025 (encaissement)
- ✅ Pas de doublon

### Gestion des Écarts

#### Cas 1: Montant Exact
```
Annonce: 7 356 € | Paiement: 7 356 € → Écart 0€
```
**Écriture générée** (1 seule) :
```
29/01/2025:
  Débit 512 Banque               : 7 356 €
  Crédit 4181 Produits à recevoir: 7 356 €
```

#### Cas 2: Écart Positif (paiement > annonce)
```
Annonce: 7 356 € | Paiement: 7 360 € → Écart +4€
```
**Écritures générées** (2) :
```
29/01/2025 - Soldage:
  Débit 512 Banque               : 7 356 €
  Crédit 4181 Produits à recevoir: 7 356 €

29/01/2025 - Ajustement:
  Débit 512 Banque               : 4 €
  Crédit 761 Revenus SCPI        : 4 €
  Libellé: "Ajustement revenus T4 (écart annonce/réel: +4€)"
```

#### Cas 3: Écart Négatif (paiement < annonce)
```
Annonce: 7 356 € | Paiement: 7 350 € → Écart -6€
```
**Écritures générées** (2) :
```
29/01/2025 - Soldage partiel:
  Débit 512 Banque               : 7 350 €
  Crédit 4181 Produits à recevoir: 7 350 €

29/01/2025 - Correction:
  Débit 6788 Charges except.     : 6 €
  Crédit 4181 Produits à recevoir: 6 €
  Libellé: "Correction produit à recevoir (écart annonce/réel: -6€)"
```

---

## 🚀 Utilisation

### Pour Ulrik (Fin d'Année)

#### Option 1: Email Automatique de la SCPI
Si vous recevez un email d'annonce de distribution T4 :
1. Transférer l'email à `u6334452013@gmail.com` (email SCI)
2. _Head.Soeurise détectera automatiquement l'annonce
3. Proposition générée → Valider
4. Écriture créée au 31/12

#### Option 2: Email Manuel
Si aucun email reçu, envoyer un email à `u6334452013@gmail.com` :

**Objet :** SCPI Épargne Pierre - Distribution T4 2024

**Corps :**
```
SCPI : Épargne Pierre
Trimestre : T4 2024
Montant distribution : 7 356,00 €
Date versement prévue : 29/01/2025

Cette annonce permet la comptabilisation en produit à recevoir
pour clôture exercice 2024.
```

### Pour _Head.Soeurise (Automatique)

#### Réveil Quotidien (08:00 UTC)
1. Récupérer emails depuis dernier réveil
2. Pour chaque email :
   - Tester `DetecteurAnnonceProduitARecevoir`
   - Si détecté → Générer proposition → Valider automatiquement
3. Récupérer relevés bancaires
4. Pour chaque opération SCPI :
   - Tester `DetecteurDistributionSCPI`
   - Si détecté → Chercher créance via `RapprocheurCutoff`
   - Générer proposition (soldage OU nouveau produit)
   - Valider automatiquement

---

## 🧪 Tests

### Exécution Tests Unitaires

**Sur environnement de développement :**
```bash
python test_cutoff_automatique.py
```

**Sur Render Shell :**
```bash
# Se connecter au shell Render
python test_cutoff_automatique.py
```

### Résultats Attendus

**Test 1: Détection Email Annonce**
- ✅ Email simple détecté
- ✅ Email bulletin annuel détecté
- ✅ Relevé bancaire ignoré
- ✅ Email "versement effectué" ignoré

**Test 2: Recherche Créance**
- ✅ Créance montant exact trouvée
- ✅ Créance avec écart ±2€ trouvée
- ✅ Créance écart > tolérance non trouvée

**Test 3: Génération Écritures Soldage**
- ✅ Montant exact : 1 écriture
- ✅ Écart positif : 2 écritures (soldage + ajustement)
- ✅ Écart négatif : 2 écritures (soldage partiel + correction)

**Test 4: Workflow Complet**
- ✅ Rapprochement automatique fonctionne
- ✅ Métadonnées correctes (ID créance, écart, etc.)

**Test 5: Détecteur avec Rapprochement**
- ✅ Distribution SCPI détectée
- ✅ Créance cherchée automatiquement
- ✅ Type événement correct selon résultat rapprochement

---

## 🔜 Prochaines Étapes

### Phase 6: Nettoyage Base 2024 et Rejeu Événements

**Objectif :** Appliquer le nouveau système sur les données 2024 existantes

**Étapes :**

1. **Sauvegarde complète base de données**
   ```bash
   python sauvegarder_base.py
   bash sauvegarder_base.sh
   ```

2. **Supprimer toutes les écritures 2024 sauf bilan d'ouverture**
   ```sql
   DELETE FROM ecritures_comptables
   WHERE exercice_id = 2  -- Exercice 2024
     AND id != 361        -- Bilan ouverture 2024
     AND id != 362
     AND id != 363
     AND id != ...;       -- Conserver toutes les lignes du bilan d'ouverture
   ```

3. **Rejouer tous les événements 2024 avec nouveau système**
   - Récupérer tous les événements depuis `evenements_comptables`
   - Réappliquer détecteurs (avec nouveau `DetecteurAnnonceProduitARecevoir`)
   - Réappliquer `DetecteurDistributionSCPI` (avec rapprochement)
   - Valider toutes les propositions

4. **Vérifier cohérence**
   - Comparer soldes avant/après
   - Vérifier compte 4181 = 0€ (créances soldées)
   - Vérifier aucun doublon revenus SCPI

### Phase 7: Validation États Financiers 2024

**Objectif :** Confirmer que les états financiers sont corrects après rejeu

**Étapes :**

1. **Générer états financiers 2024**
   ```bash
   python construire_etats_financiers_2024.py
   ```

2. **Vérifier équilibre**
   - ACTIF = PASSIF
   - Compte 4181 = 0€ (ou montant correct si créances en attente)
   - Compte 761 cohérent (revenus SCPI année entière)

3. **Comparer avec états avant modification**
   - Total revenus SCPI identique (pas de perte)
   - Pas de doublon (revenus comptés 1 fois)
   - Classification correcte (4181 au lieu de 412)

4. **Validation finale**
   - Accepter les nouveaux états comme référence
   - Documenter les différences (si pertinentes)

### Phase 8: Extension Factures Non Parvenues (Optionnel)

**Objectif :** Étendre le système aux dettes (compte 408)

**Similaire aux créances mais inversé :**
- Email annonce honoraires comptables → Créer dette (Débit 622 / Crédit 408)
- Paiement effectif → Chercher dette → Solder (Débit 408 / Crédit 512)

**Détecteur à créer :**
- `DetecteurAnnonceFNP` (Factures Non Parvenues)

**Modification détecteur existant :**
- `DetecteurHonorairesComptable` → Utiliser `rapprocheur.rapprocher_paiement()`

---

## ❓ FAQ

### 1. Que se passe-t-il si aucun email d'annonce n'est reçu ?

**Réponse :** Le système fonctionne quand même en mode dégradé :
- Aucune écriture au 31/12 (pas de créance)
- Paiement janvier → Aucune créance trouvée → Nouveau produit créé (Débit 512 / Crédit 761)
- **Conséquence** : Revenus T4 comptabilisés en janvier (exercice N+1) au lieu de décembre (exercice N)
- **Solution** : Envoyer email manuel (voir section Utilisation)

### 2. Comment gérer les doublons d'annonce ?

**Réponse :** Le rapprocheur détecte automatiquement les doublons :
- Avant de créer une créance, vérifie si créance similaire existe déjà
- Si oui → Ignore l'email (log : "Créance déjà enregistrée")
- Si non → Crée la créance

### 3. Que faire si l'écart entre annonce et paiement est > 2% ?

**Réponse :** Le rapprocheur ne trouve pas la créance :
- Aucun rapprochement effectué
- Nouveau produit créé (Débit 512 / Crédit 761)
- **Intervention manuelle requise** :
  1. Identifier la créance non soldée (compte 4181)
  2. Créer manuellement l'écriture de soldage
  3. Ajuster si nécessaire

**Recommandation :** Augmenter temporairement la tolérance :
```python
rapprocheur.rapprocher_encaissement(..., tolerance_pourcentage=0.05)  # 5%
```

### 4. Le système fonctionne-t-il pour d'autres SCPI ?

**Réponse :** Oui, avec adaptations mineures :
- Pattern détection dans `DetecteurAnnonceProduitARecevoir` accepte tout nom de SCPI
- Libellé écriture utilise le nom détecté dans l'email
- **Action requise** : Vérifier que les emails des autres SCPI suivent un format similaire

### 5. Peut-on utiliser ce système pour d'autres types de revenus ?

**Réponse :** Oui, le système est générique :
- **Créances (4181)** : Dividendes, revenus locatifs, intérêts, etc.
- **Dettes (408)** : Honoraires, factures, charges, etc.

**Action requise** : Créer détecteurs spécifiques pour chaque type.

### 6. Comment désactiver temporairement le rapprochement ?

**Réponse :** Commenter l'appel au rapprocheur dans `DetecteurDistributionSCPI` :
```python
# rapprocheur = RapprocheurCutoff(self.session)
# proposition_rapprochement = rapprocheur.rapprocher_encaissement(...)
# if proposition_rapprochement:
#     return proposition_rapprochement

# Comportement normal (pas de rapprochement)
return {
    'type_evenement': 'REVENU_SCPI',
    ...
}
```

### 7. Peut-on tester le système sans impacter la base de production ?

**Réponse :** Oui :
1. Sauvegarder la base : `python sauvegarder_base.py`
2. Exécuter tests : `python test_cutoff_automatique.py`
3. Tests utilisent des créances fictives (pas d'écriture en base)
4. Pour tests réels : Utiliser une base de développement séparée

---

## 📊 Résumé Technique

### Fichiers Modifiés/Créés

| Fichier | Type | Lignes | Description |
|---------|------|--------|-------------|
| `FORMAT_EMAIL_PRODUITS_A_RECEVOIR.md` | Doc | 450 | Spécification formats emails |
| `detecteurs_evenements.py` | Code | +240 | Ajout `DetecteurAnnonceProduitARecevoir` + Modification `DetecteurDistributionSCPI` |
| `rapprocheur_cutoff.py` | Code | 700 | Module complet rapprochement cutoff |
| `test_cutoff_automatique.py` | Tests | 380 | Tests unitaires complets |
| `SYSTEME_CUTOFF_AUTOMATIQUE.md` | Doc | 800 | Documentation complète (ce fichier) |
| `corriger_compte_4181.py` | Script | 150 | Script correction compte 412 → 4181 |
| `CORRECTION_COMPTE_4181.md` | Doc | 200 | Doc correction compte |

**Total** : ~2 920 lignes ajoutées

### Impact Comptable

**Avant :**
- Compte 412 (Créances douteuses) : 7 356 € ← Incorrect
- Compte 761 (Revenus SCPI 2024) : +7 356 € ← Doublon

**Après :**
- Compte 4181 (Produits à recevoir) : 0 € ← Soldé correctement
- Compte 761 (Revenus SCPI 2024) : Montant correct sans doublon

**Gain :**
- ✅ Conformité comptabilité d'engagement
- ✅ Classification correcte (4181 au lieu de 412)
- ✅ Fin du doublon (revenus comptés 1 fois)
- ✅ Automatisation complète (pas d'intervention manuelle)

---

## ✅ Checklist Déploiement

Avant de merger vers `main` :

- [x] Correction compte 412 → 4181 appliquée en production
- [x] Module `rapprocheur_cutoff.py` créé et testé
- [x] Détecteur `DetecteurAnnonceProduitARecevoir` créé et intégré
- [x] Modification `DetecteurDistributionSCPI` avec rapprochement
- [x] Tests unitaires créés et validés
- [x] Documentation complète rédigée
- [ ] Nettoyage base 2024 effectué
- [ ] Rejeu événements 2024 effectué
- [ ] Validation états financiers 2024
- [ ] Merge vers `main`
- [ ] Déploiement manuel Render par Ulrik

---

**Version** : 1.0
**Auteur** : _Head.Soeurise
**Statut** : ✅ Implémenté - ⏳ En attente validation et déploiement
