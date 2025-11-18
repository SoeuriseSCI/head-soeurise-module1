# 📧 Format Email Type : Annonce Produits à Recevoir

**Date** : 18 novembre 2025
**Contexte** : Système automatique de détection des cut-offs comptables
**Objectif** : Permettre la génération automatique d'écritures de produits à recevoir

---

## 🎯 Principe du Cut-off

### Comptabilité d'Engagement
Les produits doivent être comptabilisés dans l'exercice où ils sont **acquis**, indépendamment de leur encaissement.

### Workflow Cut-off SCPI

**Situation :**
- Les revenus SCPI sont trimestriels (T1, T2, T3, T4)
- Le versement intervient généralement **après la fin du trimestre**
- En fin d'année, les revenus du **4T sont acquis mais non encore versés**

**Solution comptable :**
1. **31/12/N** : Constatation du produit à recevoir
   - Écriture : Débit 4181 "Produits à recevoir" / Crédit 761 "Revenus SCPI"
   - Montant : Estimation ou annonce officielle

2. **Janvier N+1** : Encaissement effectif
   - Écriture : Débit 512 "Banque" / Crédit 4181 "Produits à recevoir"
   - Montant : Montant réel encaissé (peut différer légèrement de l'estimation)

---

## 📧 Format Email Type 1 : Annonce Officielle SCPI

### Exemple Type (SCPI Épargne Pierre)

```
De : noreply@epargne-pierre.fr
À : u6334452013@gmail.com
Objet : SCPI Épargne Pierre - Annonce distribution T4 2024

Madame, Monsieur,

La société de gestion vous informe que la distribution des revenus
du 4ème trimestre 2024 de la SCPI Épargne Pierre interviendra en
janvier 2025.

Détail de votre distribution prévisionnelle :

- Nombre de parts détenues : 100.064
- Revenus du 4ème trimestre 2024 : 7 356,00 €
- Date de versement prévisionnelle : 29 janvier 2025

Cette annonce est donnée à titre indicatif et pourra faire l'objet
d'ajustements mineurs lors du versement effectif.

Cordialement,
La société de gestion
```

### Éléments Clés à Détecter

**Obligatoires :**
1. **Émetteur** : SCPI identifiable (nom dans objet ou corps)
2. **Période** : Trimestre concerné (T4, 4ème trimestre, Q4, etc.)
3. **Année** : Année fiscale concernée
4. **Montant** : Montant des revenus annoncés
5. **Intention** : Mots-clés comme "distribution", "revenus", "versement", "prévisionnelle"

**Optionnels (utiles pour validation) :**
- Nombre de parts
- Date de versement prévue
- Nature du revenu (revenus locatifs, revenus financiers, etc.)

---

## 📧 Format Email Type 2 : Bulletin Annuel SCPI

### Exemple Type

```
De : scpi@epargne-pierre.fr
À : u6334452013@gmail.com
Objet : Bulletin annuel 2024 - SCPI Épargne Pierre
Pièce jointe : bulletin_annuel_2024.pdf

Madame, Monsieur,

Veuillez trouver ci-joint votre bulletin annuel 2024 pour la
SCPI Épargne Pierre.

Récapitulatif des distributions 2024 :
- T1 2024 : 7 200,00 € (versé le 30/04/2024)
- T2 2024 : 7 280,00 € (versé le 31/07/2024)
- T3 2024 : 7 315,00 € (versé le 31/10/2024)
- T4 2024 : 7 356,00 € (versement prévu janvier 2025)

Total annuel 2024 : 29 151,00 €

Cordialement,
La société de gestion
```

### Détection Spécifique

**Indicateurs :**
- Objet contient "bulletin annuel" ou "récapitulatif annuel"
- Corps mentionne un trimestre "versement prévu" ou "à venir"
- Distinction claire entre versements effectués et à venir

---

## 📧 Format Email Type 3 : Notification Simple

### Exemple Minimal

```
De : contact@scpi-epargne-pierre.fr
À : u6334452013@gmail.com
Objet : Distribution T4 2024 - 7 356,00 €

Bonjour,

Votre distribution du 4ème trimestre 2024 de 7 356,00 € sera
versée fin janvier 2025.

Cordialement
```

### Détection Regex

**Pattern objet :**
```regex
(Distribution|Revenus|Versement)\s+(T4|4T|4ème trimestre|Q4)\s+(\d{4})
```

**Pattern montant :**
```regex
(\d{1,3}(?:\s?\d{3})*[,\.]\d{2})\s*€
```

---

## 🤖 Règles de Détection Automatique

### Critères d'Identification

**Email = Annonce de produit à recevoir SI :**

1. **Émetteur identifié** :
   - Domaine connu (@epargne-pierre.fr, @scpi-*.fr, etc.)
   - OU nom SCPI dans l'objet/corps

2. **Période de fin d'année** :
   - Mention "T4", "4T", "4ème trimestre", "Q4"
   - OU Date email entre 15/12 et 31/12 avec mention "distribution"

3. **Montant présent** :
   - Format monétaire détectable (regex)
   - Valeur > 0€

4. **Intention future** :
   - Mots-clés : "prévisionnelle", "prévue", "sera versée", "interviendra"
   - OU Date de versement future mentionnée
   - OU Bulletin annuel avec ligne "à venir"

### Anti-Patterns (Ne PAS Traiter)

❌ **Ne PAS générer de créance si :**
- Email contient "versement effectué" (déjà payé)
- Date email en janvier/février et parle de T4 (probablement doublon avec paiement)
- Email est un simple relevé (pas d'annonce de versement futur)

---

## 🔧 Traitement Automatique

### Détecteur : `DetecteurAnnonceProduitARecevoir`

**Entrée :** Email identifié comme annonce
**Sortie :** Proposition d'écriture comptable

**Proposition Générée :**

```python
{
    'type_evenement': 'ANNONCE_PRODUIT_A_RECEVOIR_SCPI',
    'date_evenement': '2024-12-31',  # Toujours 31/12 de l'exercice
    'description': 'Revenus SCPI T4 2024 à recevoir (annoncés le XX/12/2024)',
    'montant': 7356.00,
    'ecritures': [
        {
            'compte_debit': '4181',   # Produits à recevoir
            'compte_credit': '761',   # Revenus SCPI
            'montant': 7356.00,
            'libelle': 'SCPI Épargne Pierre - Revenus T4 2024 à recevoir'
        }
    ],
    'metadata': {
        'email_date': '2024-12-20',
        'scpi_name': 'Épargne Pierre',
        'trimestre': 'T4',
        'annee': 2024,
        'date_versement_prevue': '2025-01-29'  # Si mentionnée
    }
}
```

### Écriture Comptable Générée

**Date d'écriture : 31/12/2024** (toujours fin d'exercice)

```
Compte débit  : 4181 Produits à recevoir        7 356,00 €
Compte crédit : 761  Revenus SCPI                        7 356,00 €
```

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

## 📝 Exemple Complet : Workflow 2024

### Décembre 2024 : Réception Email

**Email du 20/12/2024 :**
```
Objet : Distribution T4 2024 - SCPI Épargne Pierre
Corps : Votre distribution de 7 356,00 € sera versée le 29/01/2025
```

**Détection automatique :**
- ✅ Type : Annonce produit à recevoir
- ✅ SCPI : Épargne Pierre
- ✅ Trimestre : T4 2024
- ✅ Montant : 7 356,00 €
- ✅ Date versement : 29/01/2025

**Proposition générée :**
```python
{
    'type_evenement': 'ANNONCE_PRODUIT_A_RECEVOIR_SCPI',
    'date_evenement': '2024-12-31',
    'ecritures': [
        {
            'compte_debit': '4181',
            'compte_credit': '761',
            'montant': 7356.00,
            'libelle': 'SCPI Épargne Pierre - Revenus T4 2024 à recevoir'
        }
    ]
}
```

**Validation → Écriture comptable du 31/12/2024 :**
```
Débit 4181 Produits à recevoir   7 356 €
Crédit 761 Revenus SCPI                  7 356 €
```

### Janvier 2025 : Réception Paiement

**Relevé bancaire du 29/01/2025 :**
```
Date       | Libellé                    | Débit | Crédit
29/01/2025 | VIREMENT SCPI EPARGNE PIE  |       | 7 356,00
```

**Détection automatique :**
- ✅ Type : Revenu SCPI
- ✅ Montant : 7 356,00 €

**Rapprocheur cutoff :**
1. Recherche créance 4181 exercice 2024 ≈ 7 356€ → **TROUVÉE**
2. Génère proposition de soldage (pas nouveau produit)

**Proposition générée :**
```python
{
    'type_evenement': 'ENCAISSEMENT_PRODUIT_A_RECEVOIR_SCPI',
    'date_evenement': '2025-01-29',
    'ecritures': [
        {
            'compte_debit': '512',
            'compte_credit': '4181',
            'montant': 7356.00,
            'libelle': 'Encaissement revenus SCPI T4 2024 (soldage créance)'
        }
    ]
}
```

**Validation → Écriture comptable du 29/01/2025 :**
```
Débit 512 Banque                 7 356 €
Crédit 4181 Produits à recevoir          7 356 €
```

**Résultat final :**
- ✅ Compte 4181 : **0€** (créance soldée)
- ✅ Compte 761 : **7 356€** comptabilisé en **2024** (correct)
- ✅ Pas de doublon

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

## 🔧 Template Email à Envoyer à Ulrik

### Pour Automatisation Future

**Objet :** SCPI [Nom SCPI] - Distribution T4 [Année]

**Corps :**
```
SCPI : [Nom de la SCPI]
Trimestre : T4 [Année]
Montant distribution : [Montant] €
Date versement prévue : [Date]

Cette annonce permet la comptabilisation en produit à recevoir
pour clôture exercice [Année].
```

**Exemple concret :**
```
Objet : SCPI Épargne Pierre - Distribution T4 2024

SCPI : Épargne Pierre
Trimestre : T4 2024
Montant distribution : 7 356,00 €
Date versement prévue : 29/01/2025

Cette annonce permet la comptabilisation en produit à recevoir
pour clôture exercice 2024.
```

---

**Version** : 1.0
**Auteur** : _Head.Soeurise
**Statut** : Spécification pour implémentation
