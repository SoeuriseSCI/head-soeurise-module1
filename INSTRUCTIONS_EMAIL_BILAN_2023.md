# Instructions pour Initialiser le Bilan 2023

## 📧 Format de l'Email

Pour initialiser le bilan 2023, envoyez un email à **u6334452013@gmail.com** avec :

### Sujet
Un de ces mots-clés dans le sujet :
- `bilan 2023`
- `bilan_2023`
- `bilan initial`
- `initialisation comptable`

**Exemple de sujet** : `Initialisation bilan 2023`

---

## 📝 Contenu de l'Email

Vous avez **2 options** :

### Option 1 : JSON dans le corps de l'email (RECOMMANDÉ)

Copiez-collez les données dans un bloc JSON dans le corps de l'email :

```json
{
  "comptes": [
    {"compte": "280", "libelle": "SCPI Patrimmo Croissance", "solde": 500032, "type_bilan": "ACTIF"},
    {"compte": "412", "libelle": "Créances diverses", "solde": 7356, "type_bilan": "ACTIF"},
    {"compte": "502", "libelle": "Actions", "solde": 4140, "type_bilan": "ACTIF"},
    {"compte": "512", "libelle": "Banque", "solde": 2093, "type_bilan": "ACTIF"},
    {"compte": "120", "libelle": "Report à nouveau (négatif)", "solde": 57992, "type_bilan": "ACTIF"},
    {"compte": "290", "libelle": "Provision dépréciation SCPI", "solde": 50003, "type_bilan": "PASSIF"},
    {"compte": "101", "libelle": "Capital social", "solde": 1000, "type_bilan": "PASSIF"},
    {"compte": "130", "libelle": "Résultat 2023", "solde": 21844, "type_bilan": "PASSIF"},
    {"compte": "161", "libelle": "Emprunts", "solde": 497993, "type_bilan": "PASSIF"},
    {"compte": "444", "libelle": "Compte courant associés", "solde": 120, "type_bilan": "PASSIF"},
    {"compte": "401", "libelle": "Dettes fournisseurs", "solde": 653, "type_bilan": "PASSIF"}
  ]
}
```

**Avantages** :
- ✓ Pas besoin de PDF
- ✓ Données déjà structurées
- ✓ Pas d'erreur OCR
- ✓ Plus rapide

---

### Option 2 : PDF en pièce jointe

Attachez un PDF contenant le bilan 2023 avec :
- Colonnes : N° compte | Libellé | Solde
- Nom du fichier contenant "bilan" et "2023" (ex: `bilan_2023.pdf`)

Le système utilisera l'OCR pour extraire les données.

---

## 🔄 Workflow Complet

1. **Envoi de l'email** avec le bilan (JSON ou PDF)
2. **_Head.Soeurise** traite l'email lors de son réveil à 08:00 UTC
3. **Génération automatique** des propositions d'écritures comptables :
   - Compte 89 utilisé comme contrepartie (bilan d'ouverture)
   - Classification automatique ACTIF (débit) / PASSIF (crédit)
   - Vérification de l'équilibre
4. **Email de réponse** avec :
   - Markdown détaillant les propositions
   - JSON avec toutes les écritures
   - Token de validation
5. **Validation** : Répondez avec `[_Head] VALIDE:` pour confirmer

---

## ✅ Vérifications Automatiques

Le système vérifie automatiquement :
- ✓ Tous les comptes sont bien classifiés (ACTIF vs PASSIF)
- ✓ Le compte 130 (Résultat 2023) est présent
- ✓ Le compte 89 (bilan d'ouverture) se solde à 0€
- ✓ Total ACTIF = Total PASSIF
- ✓ Équilibre comptable respecté

---

## 📊 Comptes Attendus pour 2023

| Compte | Libellé | Solde | Type |
|--------|---------|-------|------|
| 280 | SCPI Patrimmo Croissance | 500,032€ | ACTIF |
| 412 | Créances diverses | 7,356€ | ACTIF |
| 502 | Actions | 4,140€ | ACTIF |
| 512 | Banque | 2,093€ | ACTIF |
| 120 | Report à nouveau (négatif) | 57,992€ | ACTIF |
| 290 | Provision dépréciation SCPI | 50,003€ | PASSIF |
| 101 | Capital social | 1,000€ | PASSIF |
| **130** | **Résultat 2023** | **21,844€** | **PASSIF** |
| 161 | Emprunts | 497,993€ | PASSIF |
| 444 | Compte courant associés | 120€ | PASSIF |
| 401 | Dettes fournisseurs | 653€ | PASSIF |

**Total ACTIF** : 571,613€
**Total PASSIF** : 571,613€
**Équilibre** : ✓ OK

---

## 🛠️ Corrections Appliquées (V6)

Les corrections suivantes ont été apportées au code :

1. **Compte 899 → Compte 89**
   - Ancien : Utilisait compte 899 (temporaire, incorrect)
   - Nouveau : Utilise compte 89 (bilan d'ouverture standard)

2. **Classification DEBIT/CREDIT**
   - Nouveau : Classification automatique selon Plan Comptable Général français
   - Classe 1 : Capitaux propres (crédit) sauf 12x RAN négatif (débit)
   - Classe 2 : Immobilisations (débit) sauf 28x/29x provisions (crédit)
   - Classe 4 : Tiers - 41x créances (débit) / 40x/44x dettes (crédit)
   - Classe 5 : Trésorerie (débit)

3. **Compte 130 inclus**
   - Ancien : Compte 130 (Résultat 2023) était manquant
   - Nouveau : Automatiquement inclus avec les autres comptes

4. **Double format accepté**
   - Ancien : Uniquement PDF
   - Nouveau : PDF OU JSON dans l'email

---

## 📞 Support

En cas de problème :
- Email SCI : u6334452013@gmail.com
- Email Ulrik : ulrik.c.s.be@gmail.com

---

**Version** : V6.0 - 26 octobre 2025
**Auteur** : _Head.Soeurise (Claude Code)
