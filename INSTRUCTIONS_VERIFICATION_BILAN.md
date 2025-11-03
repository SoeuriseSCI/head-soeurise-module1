# Instructions : Vérification Bilan 2023

## 🎯 Objectif

Exécuter le script `verifier_bilan_2023.py` sur **Render** pour vérifier si les écritures comptables du bilan 2023 insérées en base de données sont correctes ou contiennent les aberrations identifiées dans la synthèse.

---

## 📋 Étape par Étape

### 1. Accéder au Shell Render

1. Allez sur https://dashboard.render.com
2. Sélectionnez le service **head-soeurise-web**
3. Cliquez sur l'onglet **Shell** (dans le menu de gauche)
4. Un terminal s'ouvrira dans le conteneur

### 2. Vérifier les Fichiers

Dans le shell Render, vérifiez que le script est présent :

```bash
ls -l verifier_bilan_2023.py
```

**Attendu** : Le fichier doit être présent (après le prochain déploiement)

### 3. Exécuter le Script

```bash
python verifier_bilan_2023.py
```

**Note** : Le `DATABASE_URL` est déjà défini dans l'environnement Render, pas besoin de le spécifier.

### 4. Analyser les Résultats

Le script va afficher :

#### ✅ Cas 1 : Base CORRECTE

```
✅ BILAN 2023 CONFORME
   Toutes les écritures correspondent aux valeurs attendues

ACTIF  : 563,624.00€ ✅
PASSIF : 579,602.00€ ✅
```

**Conclusion** : Les écritures en base sont correctes, seule la **synthèse est fausse** (erreur documentaire).

**Action** : Corriger uniquement le tableau dans `SYNTHESE_SESSION_02NOV2025.md`

---

#### ❌ Cas 2 : Base CORROMPUE

```
❌ PROBLÈMES DÉTECTÉS:
   • 30 erreurs
   • 3 avertissements (aberrations)

🚨 ABERRATION MAJEURE:
   Le compte 101 (Capital) est utilisé comme contrepartie
   au lieu du compte 89 (Bilan d'ouverture)

⚠️  ABERRATIONS COMPTABLES:
   • 2023-INIT-0006: Même compte débit/crédit (101)
   • 2023-INIT-0002: Montant négatif (-36382.00€)
```

**Conclusion** : Les écritures en base sont **incorrectes**, le bilan d'ouverture est compromis.

**Action** :
1. Supprimer les 11 écritures erronées
2. Recréer le bilan avec les bonnes valeurs
3. Corriger la synthèse

---

## 📊 Valeurs Attendues (Référence)

### ACTIF (Débits, contrepartie crédit 89)

| Numéro | Compte Débit | Compte Crédit | Montant | Libellé |
|--------|--------------|---------------|---------|---------|
| 2023-INIT-0001 | 280 | 89 | 500 032,00€ | Titres immobilisés |
| 2023-INIT-0002 | 290 | 89 | 50 003,00€ | Provision épargne pierre |
| 2023-INIT-0003 | 412 | 89 | 7 356,00€ | Autres créances |
| 2023-INIT-0004 | 502 | 89 | 4 140,00€ | Actions propres |
| 2023-INIT-0005 | 512 | 89 | 2 093,00€ | Banque LCL |

**Total ACTIF** : 563 624,00€

### PASSIF (Crédits, contrepartie débit 89)

| Numéro | Compte Débit | Compte Crédit | Montant | Libellé |
|--------|--------------|---------------|---------|---------|
| 2023-INIT-0006 | 89 | 101 | 1 000,00€ | Capital |
| 2023-INIT-0007 | 89 | 120 | 57 992,00€ | Report à nouveau |
| 2023-INIT-0008 | 89 | 130 | 21 844,00€ | Résultat exercice |
| 2023-INIT-0009 | 89 | 161 | 497 993,00€ | Emprunts |
| 2023-INIT-0010 | 89 | 401 | 653,00€ | Fournisseurs |
| 2023-INIT-0011 | 89 | 444 | 120,00€ | Compte courant |

**Total PASSIF** : 579 602,00€

### Équilibre Compte 89

```
Débit 89  : 579 602,00€ (écritures passif)
Crédit 89 : 563 624,00€ (écritures actif)
Solde 89  : 15 978,00€
```

**Note** : Ce déséquilibre de ~16k€ était déjà noté dans les propositions originales ("Équilibre: ✗ ERREUR"). À investiguer.

---

## 🔧 Dépannage

### Erreur : "Module 'models_module2' not found"

```bash
pip install sqlalchemy psycopg2-binary
```

### Erreur : "DATABASE_URL non définie"

Sur Render, elle devrait être définie automatiquement. Vérifier dans les **Environment Variables** du service.

---

## 📤 Envoyer les Résultats

Une fois le script exécuté :

1. **Copier TOUT le résultat** (sélectionner et copier dans le shell)
2. **Me l'envoyer** pour que je puisse analyser et décider des corrections

Ou créer un fichier avec les résultats :

```bash
python verifier_bilan_2023.py > resultat_verification.txt
cat resultat_verification.txt
```

Puis copier le contenu.

---

**Date** : 03/11/2025
**Fichier** : verifier_bilan_2023.py
**Priorité** : 🔴 CRITIQUE
