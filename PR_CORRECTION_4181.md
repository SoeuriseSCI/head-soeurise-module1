## 📋 Résumé

Correction de la classification comptable des revenus SCPI du 4T 2023 : passage du compte 412 (Créances douteuses) au compte 4181 (Produits à recevoir).

Cette correction est la **première étape** avant l'implémentation du système automatique de rapprochement des cut-offs.

---

## 🔧 Correction : Produits à Recevoir SCPI (412 → 4181)

**Montant concerné** : 7 356 €
**Date** : 01/01/2024 (Bilan d'ouverture)
**Écriture ID** : 363

### Changement

- ❌ **AVANT** : Compte 412 "Créances douteuses ou litigieuses" (incorrect)
- ✅ **APRÈS** : Compte 4181 "Produits à recevoir" (correct)

### Raison

Les 7 356 € ne sont **pas** des créances douteuses ou litigieuses, mais des **produits à recevoir** :
- Revenus SCPI du 4T 2023 acquis mais non encore encaissés au 31/12/2023
- Encaissement effectif le 29/01/2024 (exercice suivant)
- Cut-off comptable de fin d'exercice (comptabilité d'engagement)

### Impact Comptable

**Bilan :**
- Créances (412) : -7 356 €
- Produits à recevoir (4181) : +7 356 €
- Total ACTIF : Inchangé (571 890.98 €)

**Compte de Résultat :**
- Aucun impact (mouvement de bilan uniquement)

✅ **Équilibre maintenu** : Reclassement sans impact sur les totaux.

---

## 📦 Contenu de la PR

### Scripts de correction

**`corriger_compte_4181.py`**
- Crée le compte 4181 si nécessaire
- Met à jour l'écriture ID 363 (compte débit 412 → 4181)
- Met à jour le libellé de l'écriture
- Vérifie la correction

### Documentation

**`CORRECTION_COMPTE_4181.md`**
- Explication détaillée de l'erreur 412 → 4181
- Impact comptable (Bilan)
- Instructions d'exécution
- Références au PCG
- **Contexte du problème sous-jacent** : cut-off non traité automatiquement
- **Prochaines étapes** : implémentation du rapprocheur automatique

---

## ⚙️ Exécution

Le script devra être exécuté sur l'environnement Render :

```bash
# Sur Render Shell
python corriger_compte_4181.py
```

---

## ✅ Validation

Après exécution du script :

1. ✅ Vérifier que l'écriture ID 363 utilise le compte 4181
2. ✅ Vérifier qu'aucune écriture SCPI ne reste au compte 412
3. ✅ Vérifier l'équilibre du bilan (ACTIF = PASSIF = 571 890.98 €)

```bash
# Vérification
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

## 🚨 Problème Sous-Jacent

### Cut-off Non Traité Automatiquement

**Situation actuelle (APRÈS cette correction) :**
- ✅ Créance 4181 : 7 356 € (bilan d'ouverture 2024)
- ❌ Écriture 29/01/2024 (ID 380) crée un **nouveau produit** (débit 512 / crédit 761)
- ❌ La créance 4181 n'est **jamais soldée**

**Résultat :** Les revenus du 4T 2023 sont comptés **DEUX FOIS** (doublon)

**Solution à venir :**
1. Créer module `rapprocheur_cutoff.py`
2. Détecter qu'un encaissement correspond à une créance existante
3. Générer écriture de soldage (débit 512 / crédit 4181) au lieu de nouveau produit

---

## 🎯 Prochaines Étapes

**Phase 1** : Exécuter ce script de correction ✅ (cette PR)

**Phase 2** : Créer `rapprocheur_cutoff.py`
- Fonction `chercher_creance()` pour détecter créances existantes
- Fonction `generer_ecriture_soldage()` pour solder la créance

**Phase 3** : Modifier `detecteurs_evenements.py`
- Utiliser le rapprocheur avant de créer nouveau produit

**Phase 4** : Nettoyer base 2024 et rejouer événements

**Phase 5** : Valider états financiers 2024

---

## 📝 Plan de Test

- [ ] Exécuter le script sur Render
- [ ] Valider l'écriture ID 363 utilise bien compte 4181
- [ ] Vérifier l'équilibre du bilan
- [ ] Vérifier qu'aucune écriture SCPI ne reste au compte 412

---

## 📊 Résumé des Impacts

| Élément | Avant | Après | Impact |
|---------|-------|-------|--------|
| Compte débit | 412 Créances douteuses | 4181 Produits à recevoir | Reclassement |
| Libellé | Créances diverses | Produits à recevoir | Clarification |
| Montant | 7 356 € | 7 356 € | Inchangé |
| Total ACTIF | 571 890.98 € | 571 890.98 € | Inchangé |
| Total PASSIF | 571 890.98 € | 571 890.98 € | Inchangé |

**Impact sur équilibre** : ✅ Maintenu

---

**Fichiers modifiés** :
- ✅ `corriger_compte_4181.py` (nouveau)
- ✅ `CORRECTION_COMPTE_4181.md` (nouveau)

**Impact sur la production** : Aucun (script à exécuter manuellement sur Render)

**Préparation** : ✅ Prêt pour implémentation rapprocheur automatique (Phase 2)
