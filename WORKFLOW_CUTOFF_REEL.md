# ✅ Adaptations Système Cut-off : Workflow Réel SCI Soeurise

**Date** : 18 novembre 2025
**Version** : 2.0 (Corrigée selon réalité SCPI)

---

## 🔄 Changements Importants

### ❌ Hypothèse Initiale (Incorrecte)

Nous avions initialement supposé :
1. La SCPI envoie un email d'annonce **en décembre** avec montant prévisionnel
2. _Head crée la créance au 31/12 pendant l'exercice
3. Le paiement arrive en janvier et solde la créance

### ✅ Réalité SCI Soeurise (Correcte)

1. **La SCPI n'envoie PAS d'email d'annonce en décembre**
2. **Le montant précis n'est connu que fin janvier** (quelques jours avant versement)
3. **C'est ULRIK (gérant SCI) qui informe _Head** quand il connaît le montant
4. **Création rétroactive** : Écriture datée 31/12/N mais créée en janvier N+1
5. Le paiement arrive quelques jours après et solde la créance

---

## 📧 Template Email pour Ulrik

### Quand Envoyer ?

**Fin janvier** (généralement 20-28 janvier), dès que vous recevez la notification de la SCPI avec le montant exact du T4.

### Format Email

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

**IMPORTANT** :
- Émetteur : **ulrik.c.s.be@gmail.com** (obligatoire pour validation sécurisée)
- Destinataire : **u6334452013@gmail.com** (email SCI)
- Montant : **EXACT** (tel que communiqué par SCPI)
- Timing : **Quelques jours AVANT le versement effectif**

---

## ⚙️ Workflow Complet

### 1. Fin Janvier N+1 : Notification SCPI

Vous recevez la notification de la SCPI Épargne Pierre :
- **Montant exact** distribution T4 année N
- **Date versement prévue** (généralement fin janvier)

### 2. Immédiatement : Email à _Head

Vous envoyez l'email à **u6334452013@gmail.com** avec le template ci-dessus.

### 3. Quelques Heures Après : _Head Crée la Créance

**_Head.Soeurise détecte automatiquement votre email** et :
- Vérifie que l'émetteur est bien **ulrik.c.s.be@gmail.com**
- Extrait le montant, l'année, le trimestre
- **Crée une écriture datée du 31/12/N** (exercice N, même si on est en janvier N+1)

**Écriture générée :**
```
Date  : 31/12/2024 (RÉTROACTIVE)
Débit : 4181 Produits à recevoir   7 356 €
Crédit: 761 Revenus SCPI           7 356 €
```

### 4. Quelques Jours Après : Paiement SCPI

Le versement SCPI arrive sur le compte bancaire.

**_Head.Soeurise détecte automatiquement le paiement** et :
- Cherche créance 4181 ≈ 7 356 € dans exercice précédent
- **Trouve la créance** créée quelques jours avant
- **Génère écriture de soldage** automatiquement

**Écriture générée :**
```
Date  : 29/01/2025 (date réelle paiement)
Débit : 512 Banque                 7 356 €
Crédit: 4181 Produits à recevoir   7 356 €
```

### 5. Résultat Final

- ✅ Compte 4181 : **0 €** (créance soldée)
- ✅ Compte 761 : **7 356 €** comptabilisé en **2024** (exercice correct)
- ✅ Compte 512 : **+7 356 €** en 2025 (encaissement)
- ✅ **Pas de doublon**
- ✅ **Conformité comptabilité d'engagement**

---

## 🎯 Pourquoi Cette Approche ?

### Création Rétroactive : Est-ce Légal ?

**OUI**, car :
1. L'exercice 2024 est encore **ouvert** en janvier 2025 (clôture mars/avril)
2. Nous créons une écriture **dans un exercice non clôturé**
3. La datele 31/12/2024 est correcte : c'est la date où le produit est acquis
4. Conforme au **principe de comptabilité d'engagement**

### Pourquoi Pas d'Estimation en Décembre ?

**Raisons** :
1. **Exactitude** : Montant exact dès la première saisie (pas d'ajustement)
2. **Simplicité** : Une seule écriture de créance (pas d'estimation + ajustement)
3. **Réalité** : Reflète le processus réel de la SCPI

### Sécurité : Vérification Émetteur

Le système vérifie que l'émetteur est bien **ulrik.c.s.be@gmail.com** :
- ✅ Évite détection erronée d'emails publicitaires SCPI
- ✅ Garantit que c'est bien un **acte de gestion** (gérant SCI)
- ✅ Seul le gérant peut déclencher création cut-off

---

## 📋 Checklist Annuelle (Décembre → Janvier)

### ❌ En Décembre

**RIEN À FAIRE**
- Pas d'email à envoyer
- Pas de création de créance
- _Head ne fait rien automatiquement

### ✅ Fin Janvier (20-28 janvier)

1. **Vous recevez** : Notification SCPI avec montant exact T4
2. **Vous envoyez** : Email à u6334452013@gmail.com (template ci-dessus)
3. **_Head crée** : Créance datée 31/12 (automatique, rétroactive)
4. **Vous validez** : Proposition de créance (si validation manuelle activée)

### ✅ Quelques Jours Après (28-31 janvier)

1. **Paiement arrive** : Virement SCPI sur compte bancaire
2. **_Head détecte** : Cherche créance correspondante
3. **_Head solde** : Génère écriture de soldage automatiquement
4. **Vous validez** : Proposition de soldage (si validation manuelle activée)

### ✅ Résultat

- Compte 4181 : 0 € (soldé)
- Revenus T4 comptabilisés en année N (correct)
- Pas de doublon
- Exercice N peut être clôturé (mars/avril)

---

## ❓ Questions Fréquentes

### 1. Dois-je envoyer l'email même si le paiement arrive le lendemain ?

**OUI, impérativement.**
Même si le délai est court (1-2 jours), l'email est nécessaire pour :
- Créer la créance au 31/12 (rétroactive)
- Permettre au rapprocheur de trouver la créance lors du paiement
- Éviter que le paiement soit comptabilisé comme nouveau produit en année N+1

### 2. Que se passe-t-il si j'oublie d'envoyer l'email ?

**Conséquence** :
- Aucune créance créée au 31/12
- Paiement janvier comptabilisé comme **nouveau produit** (année N+1)
- **Revenus T4 comptabilisés en N+1 au lieu de N** (incorrect)

**Solution** :
- Envoyer l'email dès que possible (même après paiement)
- _Head créera la créance rétroactive
- Vous devrez peut-être corriger l'écriture de paiement manuellement

### 3. Puis-je envoyer l'email depuis un autre compte email ?

**NON.**
Le système vérifie que l'émetteur est exactement **ulrik.c.s.be@gmail.com**.
Si vous envoyez depuis un autre compte, l'email sera ignoré.

### 4. Comment savoir si _Head a bien créé la créance ?

**Deux méthodes** :
1. **Email de confirmation** : _Head envoie un email de confirmation
2. **Interface web** : Vérifier sur https://head-soeurise-web.onrender.com

### 5. Que faire si le montant réel diffère légèrement du montant annoncé ?

**Géré automatiquement.**
Le rapprocheur a une tolérance de ±2€ ou ±2% :
- Si écart dans tolérance → Soldage + Ajustement automatique
- Si écart hors tolérance → Vous devrez intervenir manuellement

---

## 📊 Résumé Technique

### Modifications Code

Les modifications suivantes ont été apportées au système :

**1. Documentation :**
- ✅ `FORMAT_EMAIL_PRODUITS_A_RECEVOIR.md` : Workflow corrigé
- ✅ Template email pour Ulrik

**2. Détecteurs (À venir) :**
- ⏳ `DetecteurAnnonceProduitARecevoir.detecter()` : Vérification émetteur Ulrik
- ⏳ Date créance : 31/12 de l'année mentionnée (pas année courante si janvier)

**3. Tests (À venir) :**
- ⏳ Tests avec émetteur Ulrik vs autres
- ⏳ Tests création rétroactive (janvier → 31/12 année précédente)

### État Actuel

- ✅ Correction compte 412 → 4181 **APPLIQUÉE en production**
- ✅ Module `rapprocheur_cutoff.py` créé
- ✅ Modification `DetecteurDistributionSCPI` avec rapprochement
- ✅ Documentation corrigée selon réalité
- ⏳ Modification détecteur email Ulrik (en cours)
- ⏳ Tests adaptés (en cours)

---

## ✅ Validation

**Ce workflow a été validé par Ulrik le 18 novembre 2025.**

Les adaptations reflètent maintenant la **réalité du fonctionnement SCPI Épargne Pierre** et le rôle du gérant SCI dans le processus de cut-off.

---

**Version** : 2.0
**Auteur** : _Head.Soeurise
**Statut** : ✅ Workflow validé - ⏳ Code en cours d'adaptation
