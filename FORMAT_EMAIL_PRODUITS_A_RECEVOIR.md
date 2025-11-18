# 📧 Format Email Type : Annonce Produits à Recevoir

**Date** : 18 novembre 2025
**Contexte** : Système automatique de détection des cut-offs comptables
**Objectif** : Permettre la génération automatique d'écritures de produits à recevoir

---

## 🎯 Principe du Cut-off

### Comptabilité d'Engagement
Les produits doivent être comptabilisés dans l'exercice où ils sont **acquis**, indépendamment de leur encaissement.

### Workflow Cut-off SCPI (Réalité SCI Soeurise)

**Situation :**
- Les revenus SCPI sont trimestriels (T1, T2, T3, T4)
- Le versement intervient généralement **fin janvier N+1** pour le T4 de l'année N
- **Le montant précis du T4 N n'est connu que fin janvier N+1** (quelques jours avant versement)
- La SCPI n'envoie PAS d'email d'annonce en décembre
- C'est **Ulrik (gérant SCI)** qui doit informer _Head quand il connaît le montant

**Solution comptable (Création rétroactive) :**
1. **Fin janvier N+1** : Ulrik reçoit notification SCPI avec montant exact T4
2. **Ulrik envoie email à _Head** : "Distribution T4 année N de X € sera versée le JJ/MM/AAAA"
3. **_Head crée créance datée 31/12/N** (rétroactive, avant clôture exercice)
   - Écriture : Débit 4181 "Produits à recevoir" / Crédit 761 "Revenus SCPI"
   - Date écriture : **31/12/N** (exercice N, même si créée en janvier N+1)
   - Montant : Montant exact communiqué par SCPI

4. **Quelques jours après** : Encaissement effectif
   - Écriture : Débit 512 "Banque" / Crédit 4181 "Produits à recevoir"
   - Date écriture : Date réelle du paiement (janvier N+1)
   - Montant : Montant encaissé (normalement identique)

**Avantages de cette approche :**
- Produit comptabilisé dans le bon exercice (année N)
- Montant exact dès la première saisie (pas d'estimation)
- Exercice N encore ouvert en janvier (clôture mars/avril)
- Workflow compatible avec la réalité de la SCPI

---

## 📧 Format Email Type 1 : Email d'Ulrik (Gérant SCI)

### Exemple Type - Email Simple

**IMPORTANT** : Cet email est envoyé par **Ulrik (gérant SCI)** à _Head.Soeurise, PAS par la SCPI.

```
De : ulrik.c.s.be@gmail.com
À : u6334452013@gmail.com
Objet : SCPI Épargne Pierre - Distribution T4 2024

Distribution T4 2024 - SCPI Épargne Pierre

Montant : 7 356,00 €
Date versement : 29 janvier 2025

Cette information permet à _Head de créer le cut-off comptable
pour clôture exercice 2024.
```

### Éléments Clés à Détecter

**Obligatoires :**
1. **Émetteur** : Email d'Ulrik (ulrik.c.s.be@gmail.com) ← **CRITIQUE**
2. **Période** : Trimestre concerné (T4, 4ème trimestre, Q4, etc.)
3. **Année** : Année fiscale concernée
4. **Montant** : Montant des revenus annoncés (montant EXACT, pas estimation)
5. **Mots-clés** : "SCPI", "Distribution", "T4"

**Optionnels (utiles pour validation) :**
- Date de versement prévue
- Mention "cut-off" ou "clôture exercice"

**Note importante :**
- Le montant est EXACT (connu fin janvier)
- Pas d'estimation, pas de "prévisionnelle"
- Email envoyé **quelques jours avant le versement** (fin janvier)

---

## 📧 Format Email Type 2 : Email d'Ulrik avec Contexte

### Exemple Type - Email Détaillé

```
De : ulrik.c.s.be@gmail.com
À : u6334452013@gmail.com
Objet : Cut-off SCPI T4 2024

Bonjour _Head,

Je viens de recevoir la notification de la SCPI Épargne Pierre
concernant la distribution du 4ème trimestre 2024.

Informations pour le cut-off comptable :
- SCPI : Épargne Pierre
- Trimestre : T4 2024
- Montant : 7 356,00 €
- Date versement prévu : 29/01/2025

Merci de créer l'écriture de produit à recevoir pour la clôture
de l'exercice 2024.

Ulrik
```

### Détection Spécifique

**Indicateurs :**
- Émetteur : ulrik.c.s.be@gmail.com
- Mention explicite "cut-off" ou "produit à recevoir"
- Contexte clair pour clôture exercice

---

## 📧 Format Email Type 3 : Email Minimaliste

### Exemple Minimal (Acceptable)

```
De : ulrik.c.s.be@gmail.com
À : u6334452013@gmail.com
Objet : SCPI T4 2024

SCPI Épargne Pierre T4 2024 : 7 356,00 €
Versement : 29/01/2025
```

### Détection Regex

**Pattern objet :**
```regex
(SCPI|Distribution|Revenus|Cut-off).*\s+(T4|4T|4ème trimestre|Q4)\s+(\d{4})
```

**Pattern montant :**
```regex
(\d{1,3}(?:\s?\d{3})*[,\.]\d{2})\s*€
```

---

## 🤖 Règles de Détection Automatique

### Critères d'Identification

**Email = Annonce de produit à recevoir SI :**

1. **Émetteur ULRIK (CRITIQUE)** :
   - De : ulrik.c.s.be@gmail.com ← **OBLIGATOIRE**
   - Seul Ulrik peut demander création cut-off
   - Acte de gestion de la SCI

2. **Période T4 mentionnée** :
   - Mention "T4", "4T", "4ème trimestre", "Q4"
   - Année fiscale concernée (ex: 2024)

3. **Montant présent** :
   - Format monétaire détectable (regex)
   - Valeur > 0€
   - **Montant EXACT** (pas d'estimation)

4. **Contexte cut-off** :
   - Mots-clés : "cut-off", "produit à recevoir", "clôture exercice"
   - OU Mention SCPI + T4 + montant (suffisant)

5. **Date réception** :
   - Généralement **fin janvier** (quelques jours avant versement)
   - Peut être début février si retard

### Anti-Patterns (Ne PAS Traiter)

❌ **Ne PAS générer de créance si :**
- Émetteur ≠ Ulrik (ulrik.c.s.be@gmail.com)
- Email contient "versement effectué" (déjà payé)
- Email est un simple relevé bancaire
- Créance T4 déjà créée pour cette année (doublon)

---

## 🔧 Traitement Automatique

### Détecteur : `DetecteurAnnonceProduitARecevoir`

**Entrée :** Email d'Ulrik identifié comme demande de cut-off
**Sortie :** Proposition d'écriture comptable (rétroactive)

**Proposition Générée :**

```python
{
    'type_evenement': 'ANNONCE_PRODUIT_A_RECEVOIR_SCPI',
    'date_evenement': '2024-12-31',  # Toujours 31/12 de l'exercice (RÉTROACTIF)
    'description': 'Revenus SCPI T4 2024 à recevoir (montant connu le 25/01/2025)',
    'montant': 7356.00,
    'ecritures': [
        {
            'compte_debit': '4181',   # Produits à recevoir
            'compte_credit': '761',   # Revenus SCPI
            'montant': 7356.00,
            'libelle': 'SCPI Épargne Pierre - Revenus T4 2024 à recevoir',
            'date_ecriture': '2024-12-31'  # RÉTROACTIF !
        }
    ],
    'metadata': {
        'email_date': '2025-01-25',  # Date email Ulrik (janvier)
        'email_emetteur': 'ulrik.c.s.be@gmail.com',
        'scpi_name': 'Épargne Pierre',
        'trimestre': 'T4',
        'annee': 2024,
        'date_versement_prevue': '2025-01-29',
        'creation_retroactive': True  # Écriture créée après 31/12 mais datée 31/12
    }
}
```

### Écriture Comptable Générée

**Date d'écriture : 31/12/2024** (rétroactive, même si créée en janvier 2025)

```
Compte débit  : 4181 Produits à recevoir        7 356,00 €
Compte crédit : 761  Revenus SCPI                        7 356,00 €
Libellé       : SCPI Épargne Pierre - Revenus T4 2024 à recevoir
```

**Note technique :**
- Écriture créée en **janvier 2025** (quand montant connu)
- Mais **datée du 31/12/2024** (exercice où produit acquis)
- Possible car exercice 2024 encore ouvert (clôture mars/avril)
- Conforme comptabilité d'engagement

---

## ⚠️ Cas Particuliers et Gestion d'Erreurs

### 1. Différence entre Montant Annoncé et Montant Réel

**Situation :**
- Annonce : 7 356,00 €
- Versement réel : 7 360,00 € (différence de +4€)

**Traitement :**
1. Rapprocheur détecte créance 4181 = 7 356€
2. Paiement reçu = 7 360€
3. Écart = +4€ dans la tolérance (±2%)

**Solution A (Recommandée) :** Soldage partiel + ajustement
```
1. Soldage créance :
   Débit 512 Banque           7 356 €
   Crédit 4181 Produits       7 356 €

2. Complément :
   Débit 512 Banque           4 €
   Crédit 761 Revenus SCPI    4 €
   Libellé : "Ajustement revenus T4 2024 (écart annonce/réel)"
```

**Solution B :** Ajustement créance puis soldage
```
1. Ajustement créance (31/12) :
   Débit 4181 Produits        4 €
   Crédit 761 Revenus SCPI    4 €

2. Soldage total (janvier) :
   Débit 512 Banque           7 360 €
   Crédit 4181 Produits       7 360 €
```

**Choix recommandé :** Solution A (plus simple, pas de rétroactivité)

### 2. Annonce Multiple (Doublon)

**Situation :**
- 20/12/2024 : Email annonce 7 356€
- 28/12/2024 : Bulletin annuel mentionne aussi 7 356€

**Détection :**
```python
# Vérifier si créance existe déjà
SELECT * FROM ecritures_comptables
WHERE compte_debit = '4181'
  AND exercice_id = exercice_courant
  AND libelle ILIKE '%T4%'
  AND ABS(montant - 7356.00) < 2.0
```

**Traitement :**
- Si créance existe déjà → **Ignorer** le doublon
- Loguer : "Créance T4 déjà enregistrée, email ignoré"

### 3. Aucune Annonce Reçue

**Situation :**
- Fin d'année, aucun email d'annonce
- Paiement arrive en janvier sans annonce préalable

**Traitement :**
- **Pas de créance au 31/12** (comptabilité de trésorerie par défaut)
- En janvier, détecteur normal crée un nouveau produit (Débit 512 / Crédit 761)
- ⚠️ **Attention** : Revenues comptabilisés dans mauvais exercice (année N+1 au lieu de N)

**Recommandation :**
- En fin d'année, si aucune annonce → **Email manuel à envoyer** avec format type
- Ou saisie manuelle de la créance via interface

---

## 📝 Exemple Complet : Workflow Année N (2024)

### Fin Janvier N+1 (25/01/2025) : Email Ulrik

**Email d'Ulrik :**
```
De : ulrik.c.s.be@gmail.com
À : u6334452013@gmail.com
Objet : SCPI Épargne Pierre - Distribution T4 2024
Date : 25/01/2025

Distribution T4 2024 - SCPI Épargne Pierre

Montant : 7 356,00 €
Date versement : 29 janvier 2025

Cette information permet à _Head de créer le cut-off comptable
pour clôture exercice 2024.
```

**Détection automatique (_Head.Soeurise) :**
- ✅ Émetteur : ulrik.c.s.be@gmail.com
- ✅ Type : Annonce produit à recevoir
- ✅ SCPI : Épargne Pierre
- ✅ Trimestre : T4 2024
- ✅ Montant : 7 356,00 € (EXACT)
- ✅ Date versement : 29/01/2025

**Proposition générée (25/01/2025) :**
```python
{
    'type_evenement': 'ANNONCE_PRODUIT_A_RECEVOIR_SCPI',
    'date_evenement': '2024-12-31',  # RÉTROACTIF !
    'ecritures': [
        {
            'date_ecriture': '2024-12-31',  # Datée 31/12/2024
            'compte_debit': '4181',
            'compte_credit': '761',
            'montant': 7356.00,
            'libelle': 'SCPI Épargne Pierre - Revenus T4 2024 à recevoir'
        }
    ],
    'metadata': {
        'email_date': '2025-01-25',
        'creation_retroactive': True
    }
}
```

**Validation → Écriture comptable créée le 25/01/2025, DATÉE du 31/12/2024 :**
```
Date  : 31/12/2024 (exercice 2024, rétroactif)
Débit : 4181 Produits à recevoir   7 356 €
Crédit: 761 Revenus SCPI           7 356 €
```

### Quelques Jours Après (29/01/2025) : Paiement SCPI

**Relevé bancaire du 29/01/2025 :**
```
Date       | Libellé                    | Débit | Crédit
29/01/2025 | VIREMENT SCPI EPARGNE PIE  |       | 7 356,00
```

**Détection automatique (_Head.Soeurise) :**
- ✅ Type : Revenu SCPI (DetecteurDistributionSCPI)
- ✅ Montant : 7 356,00 €

**Rapprocheur cutoff :**
1. Recherche créance 4181 exercice 2024 ≈ 7 356€ → **TROUVÉE** (créée le 25/01)
2. Génère proposition de soldage (pas nouveau produit)

**Proposition générée (29/01/2025) :**
```python
{
    'type_evenement': 'ENCAISSEMENT_PRODUIT_A_RECEVOIR_SCPI',
    'date_evenement': '2025-01-29',
    'ecritures': [
        {
            'date_ecriture': '2025-01-29',  # Date réelle paiement
            'compte_debit': '512',
            'compte_credit': '4181',
            'montant': 7356.00,
            'libelle': 'Encaissement revenus SCPI T4 2024 (soldage créance)'
        }
    ],
    'metadata': {
        'creance_id': 999,
        'ecart': 0.00
    }
}
```

**Validation → Écriture comptable du 29/01/2025 :**
```
Date  : 29/01/2025 (exercice 2025)
Débit : 512 Banque                 7 356 €
Crédit: 4181 Produits à recevoir   7 356 €
```

**Résultat final :**
- ✅ Compte 4181 : **0€** (créance créée le 25/01, soldée le 29/01)
- ✅ Compte 761 : **7 356€** comptabilisé en **2024** (exercice correct)
- ✅ Compte 512 : +7 356€ en 2025 (encaissement)
- ✅ Pas de doublon
- ✅ Conformité comptabilité d'engagement

---

## 🎯 Résumé : Règles de Gestion

| Situation | Email Type | Date Écriture | Écriture Générée |
|-----------|-----------|---------------|-------------------|
| **Annonce T4 en décembre** | Type 1, 2 ou 3 | 31/12/N | Débit 4181 / Crédit 761 |
| **Paiement avec créance** | Relevé bancaire | Date paiement | Débit 512 / Crédit 4181 |
| **Paiement sans créance** | Relevé bancaire | Date paiement | Débit 512 / Crédit 761 |
| **Doublon annonce** | Type 1, 2 ou 3 | - | Ignoré |
| **Écart annonce/réel** | Relevé bancaire | Date paiement | Soldage + Ajustement |

---

## 🔧 Template Email pour Ulrik

### Email à Envoyer par le Gérant SCI

**IMPORTANT** : C'est **Ulrik (gérant SCI)** qui doit envoyer cet email à _Head.Soeurise quand il reçoit la notification de la SCPI (fin janvier).

**De :** ulrik.c.s.be@gmail.com
**À :** u6334452013@gmail.com (email SCI)
**Objet :** SCPI [Nom SCPI] - Distribution T4 [Année]

**Corps :**
```
Distribution T4 [Année] - SCPI [Nom SCPI]

Montant : [Montant exact] €
Date versement : [Date prévue]

Cette information permet à _Head de créer le cut-off comptable
pour clôture exercice [Année].
```

**Exemple concret (Janvier 2025 pour T4 2024) :**
```
De : ulrik.c.s.be@gmail.com
À : u6334452013@gmail.com
Objet : SCPI Épargne Pierre - Distribution T4 2024

Distribution T4 2024 - SCPI Épargne Pierre

Montant : 7 356,00 €
Date versement : 29 janvier 2025

Cette information permet à _Head de créer le cut-off comptable
pour clôture exercice 2024.
```

**Timing :**
- Envoyer cet email **dès réception de la notification SCPI** (fin janvier)
- Quelques jours AVANT le versement effectif
- Permet à _Head de créer la créance au 31/12 (rétroactif) avant le paiement

---

**Version** : 1.0
**Auteur** : _Head.Soeurise
**Statut** : Spécification pour implémentation
