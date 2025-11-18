# 🔧 Correction Compte Produits à Recevoir : 412 → 4181

**Date** : 18 novembre 2025
**Contexte** : Correction classification créances SCPI
**Script** : `corriger_compte_4181.py`

---

## 📋 Erreur Identifiée

### Situation Actuelle (Incorrecte)
Les revenus SCPI du 4T 2023 (**7 356 €**) ont été classés au compte **412 "Créances douteuses ou litigieuses"**.

**Écriture concernée :**
- ID: 363
- Date: 01/01/2024 (Bilan d'ouverture)
- Libellé: "Bilan ouverture 2024 - Créances diverses"
- Montant: 7 356.00€
- Type: Bilan d'ouverture (INIT_BILAN)
- Écriture: Débit 412 / Crédit 89

### Nature Réelle
Le compte 412 ne convient **PAS** :
- ❌ Le compte 412 = "Créances douteuses ou litigieuses"
- ❌ Les revenus SCPI du 4T 2023 ne sont PAS douteux ou litigieux
- ❌ Ce compte est réservé aux créances à risque (recouvrement incertain)

Les revenus SCPI du 4T 2023 sont **EN RÉALITÉ** :
- ✅ Des **produits à recevoir** (revenus courus non encore encaissés)
- ✅ Revenus certains, juste décalés dans le temps (cut-off)
- ✅ Doivent être classés dans le compte 4181 "Produits à recevoir"

### Classification Correcte
**Compte approprié** : **4181 "Produits à recevoir"**

---

## 💰 Impact Comptable

### Au Bilan - ACTIF

**AVANT correction :**
```
ACTIF
  Actif circulant
    Créances
      412 Créances douteuses ou litigieuses : 7 356 € ❌
```

**APRÈS correction :**
```
ACTIF
  Actif circulant
    Créances
      4181 Produits à recevoir : 7 356 € ✅
```

**Impact** : Reclassement de **7 356 €** au sein des créances de l'actif circulant.

---

## ⚖️ Bilan Équilibre

### Équation Comptable

**AVANT et APRÈS :**
- Actif total : **inchangé** (571 890.98 €)
- Passif : **inchangé**
- Résultat : **inchangé**

**Seule la classification change** : Le montant reste à l'actif mais dans le bon compte.

**Formule :**
```
ACTIF = PASSIF
(412 - 7 356) + (4181 + 7 356) = PASSIF
```

✅ Le bilan reste équilibré (reclassement sans impact sur le total).

---

## 🔧 Exécution du Script

### Prérequis
- Accès à la base de données PostgreSQL (environnement Render)
- Variable d'environnement `DATABASE_URL` configurée

### Sur Render Shell

```bash
# Se connecter au shell Render
# https://dashboard.render.com → Service → Shell

# Exécuter le script
python corriger_compte_4181.py

# Vérifier la correction
psql $DATABASE_URL -c "
  SELECT id, date_ecriture, libelle_ecriture, compte_debit, compte_credit, montant
  FROM ecritures_comptables
  WHERE id = 363;
"
```

**Résultat attendu :**
```
id  | date_ecriture | libelle_ecriture                           | compte_debit | compte_credit | montant
----+---------------+--------------------------------------------+--------------+---------------+---------
363 | 2024-01-01    | Bilan ouverture 2024 - Produits à recevoir | 4181         | 89            | 7356.00
```

---

## ✅ Validation Post-Correction

### 1. Vérifier l'écriture au compte 4181

```bash
psql $DATABASE_URL -c "
  SELECT id, date_ecriture, libelle_ecriture, compte_debit, montant
  FROM ecritures_comptables
  WHERE compte_debit = '4181'
  ORDER BY date_ecriture;
"
```

**Attendu :** 1 écriture de 7 356 € au 01/01/2024.

### 2. Vérifier qu'aucune écriture SCPI ne reste au compte 412

```bash
psql $DATABASE_URL -c "
  SELECT COUNT(*)
  FROM ecritures_comptables
  WHERE compte_debit = '412'
    AND (libelle_ecriture ILIKE '%SCPI%' OR libelle_ecriture ILIKE '%revenus%');
"
```

**Attendu :** 0

### 3. Vérifier l'équilibre du bilan 2024

```bash
python construire_etats_financiers_2024.py
```

**Attendu :** Bilan équilibré (ACTIF = PASSIF = 571 890.98 €)

---

## 📊 Contexte : Pourquoi cette Créance Existe ?

### Cut-off Comptable de Fin d'Année

**Situation :**
1. **31/12/2023** : Clôture de l'exercice 2023
2. Les revenus SCPI du **4T 2023** sont **acquis** (trimestriel échu) mais **non encore versés**
3. Versement effectif : **29/01/2024** (exercice suivant)

**Principe comptable (comptabilité d'engagement) :**
> Les revenus doivent être comptabilisés dans l'exercice où ils sont acquis, **indépendamment de leur encaissement**.

**Conséquence :**
- Au 31/12/2023 : Produit à recevoir de 7 356 € (débit 4181 / crédit 761)
- Au 29/01/2024 : Encaissement qui **solde la créance** (débit 512 / crédit 4181)

---

## 🚨 Problème à Résoudre Après Cette Correction

### Le Cut-off n'est PAS Traité Automatiquement

**Actuellement :**
- ✅ La créance 4181 existe dans le bilan d'ouverture 2024
- ❌ L'écriture du 29/01/2024 (ID 380) crée un **nouveau produit** (débit 512 / crédit 761)
- ❌ La créance 4181 n'est **jamais soldée**

**Résultat actuel (INCORRECT) :**
```
Compte 4181 : 7 356 € (créance non soldée) ❌
Compte 761  : 7 356 € (nouveau produit) ❌
→ Doublon ! Les revenus du 4T 2023 sont comptés DEUX FOIS
```

**Résultat attendu (CORRECT) :**
```
Compte 4181 : 0 € (créance soldée le 29/01/2024) ✅
Compte 761  : 0 € (pas de nouveau produit, juste encaissement créance) ✅
→ Les revenus du 4T 2023 sont comptés UNE SEULE FOIS (en 2023)
```

---

## 🎯 Prochaine Étape

Après cette correction, il faudra :

**Phase 1** : Créer un module `rapprocheur_cutoff.py` qui :
1. Détecte qu'un encaissement correspond à une créance existante
2. Génère l'écriture de soldage (débit 512 / crédit 4181)
3. Au lieu de créer un nouveau produit (débit 512 / crédit 761)

**Phase 2** : Modifier `detecteurs_evenements.py` pour utiliser ce module

**Phase 3** : Nettoyer la base 2024 et rejouer tous les événements

---

## 📖 Références Comptables

**Plan Comptable Général (PCG) :**

- **Compte 412** : Créances douteuses ou litigieuses
  - Classe 4 (Comptes de tiers)
  - Sous-classe 41 (Clients et comptes rattachés)
  - Nature : Compte de bilan (ACTIF)
  - Usage : Créances dont le recouvrement est incertain (risque de non-paiement)

- **Compte 4181** : Produits à recevoir
  - Classe 4 (Comptes de tiers)
  - Sous-classe 41 (Clients et comptes rattachés)
  - Sous-sous-classe 418 (Clients - Produits non encore facturés)
  - Nature : Compte de bilan (ACTIF)
  - Usage : Produits acquis mais non encore encaissés (cut-off de fin d'exercice)

**Principe de classification :**
- Revenus SCPI 4T 2023 acquis mais non encaissés = Produits à recevoir → Compte 4181
- Créances douteuses = Risque de non-paiement → Compte 412

---

## 🎯 Conclusion

### Pourquoi cette correction ?

1. **Exactitude comptable** : Distinguer produits à recevoir des créances douteuses
2. **Conformité PCG** : Respecter la classification du plan comptable
3. **Clarté** : Le compte 412 induit en erreur sur la nature de la créance
4. **Préparation** : Étape 1 avant implémentation du rapprochement automatique

### Impact Global

- ✅ Amélioration de la qualité comptable
- ✅ Conformité avec le PCG
- ✅ Meilleure lisibilité du bilan
- ✅ Aucun impact sur les totaux (reclassement)
- ⏭️ Prépare le terrain pour le rapprochement automatique des cut-offs

---

**Version** : 1.0
**Auteur** : _Head.Soeurise
**Statut** : Prêt pour exécution sur Render
