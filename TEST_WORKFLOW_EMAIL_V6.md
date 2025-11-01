# Guide de Test - Workflow Email avec Parseur V6

**Date** : 01 novembre 2025
**Branche** : `claude/v6-architecture-impl-011CUhER84gzHmbSoYaE2bFG`
**Commit** : `5fb8182`

---

## 🎯 Objectif

Tester le workflow complet d'intégration V6 :
```
Email avec PDF → Réveil 08:00 UTC → Parseur V6 → Propositions → Validation → Insertion BD
```

---

## 📋 Prérequis

1. **Base de données propre** (déjà fait)
   - 0 écritures comptables
   - 0 prêts immobiliers
   - 2 exercices comptables (2023, 2024)

2. **Variables d'environnement**
   ```bash
   ANTHROPIC_API_KEY=<votre clé API Anthropic>
   DATABASE_URL=<PostgreSQL URL>
   GMAIL_USER=u6334452013@gmail.com
   GMAIL_APP_PASSWORD=<mot de passe>
   ```

3. **Emails de test préparés**
   - Bilan d'ouverture (avec pièces justificatives)
   - Prêt A (INVESTIMUR - 216 échéances)
   - Prêt B (SOLUTION P IMMO - 252 échéances)

---

## 🚀 Procédure de Test

### Étape 1 : Envoyer Emails de Test

#### Email 1 - Bilan d'Ouverture
```
De: ulrik.c.s.be@gmail.com
À: u6334452013@gmail.com
Objet: [Soeurise] Bilan d'ouverture 2023
Corps: Bilan d'ouverture de la SCI au 01/01/2023
Pièces jointes: Documents comptables 2023
```

#### Email 2 - Prêt A (INVESTIMUR)
```
De: ulrik.c.s.be@gmail.com
À: u6334452013@gmail.com
Objet: [Soeurise] Tableau amortissement prêt INVESTIMUR
Corps: Prêt immobilier INVESTIMUR (IN FINE - 216 échéances)
Pièce jointe: TABLEAUD'AMORTISSEMENTPRETIMMOBILIER_20230417.pdf
```

#### Email 3 - Prêt B (SOLUTION P IMMO)
```
De: ulrik.c.s.be@gmail.com
À: u6334452013@gmail.com
Objet: [Soeurise] Tableau amortissement prêt SOLUTION P IMMO
Corps: Prêt immobilier SOLUTION P IMMO (Amortissement constant - 252 échéances)
Pièce jointe: TABLEAUD'AMORTISSEMENTPRETIMMOBILIER_20230417-1.pdf
```

### Étape 2 : Déclencher Réveil Manuel (ou attendre 08:00 UTC)

#### Option A - Réveil Manuel Local
```bash
cd /home/user/head-soeurise-module1
python main.py
```

#### Option B - Réveil Automatique (Production)
```
Attendre le réveil quotidien à 08:00 UTC sur Render
```

### Étape 3 : Observer les Logs

#### Logs Attendus pour Bilan d'Ouverture
```
[WORKFLOW] Email traité: INIT_BILAN_2023
[PROPOSITION] Bilan d'ouverture généré
Token: <hash MD5>
```

#### Logs Attendus pour Prêt A
```
[WORKFLOW] Email traité: PRET_IMMOBILIER
[PARSEUR V6] Parsing PDF: TABLEAUD'AMORTISSEMENTPRETIMMOBILIER_20230417.pdf
[PARSEUR V6] Extraction complète: 216 échéances
[PARSEUR V6] Fichier créé: PRET_5009736BRLZE11AQ_echeances.md
[PROPOSITION] Prêt INVESTIMUR: 216 échéances extraites
Token: <hash MD5>
```

#### Logs Attendus pour Prêt B
```
[WORKFLOW] Email traité: PRET_IMMOBILIER
[PARSEUR V6] Parsing PDF: TABLEAUD'AMORTISSEMENTPRETIMMOBILIER_20230417-1.pdf
[PARSEUR V6] Extraction complète: 251 échéances (⚠️ 252 attendues)
[PARSEUR V6] Fichier créé: PRET_5009736BRM0911AH_echeances.md
[PROPOSITION] Prêt SOLUTION P IMMO: 251 échéances extraites
Token: <hash MD5>
```

### Étape 4 : Vérifier les Propositions

#### Proposition Bilan d'Ouverture
```markdown
## Proposition: Bilan d'ouverture 2023

**Type:** INIT_BILAN_2023
**Token:** <hash>

### Écritures comptables à créer:
- Compte 512 (Banque): +10000.00 EUR
- Compte 101 (Capital social): +10000.00 EUR
...

Pour valider: [_Head] VALIDE: <token>
```

#### Proposition Prêt A
```markdown
## Proposition: Prêt Immobilier INVESTIMUR

**Type:** PRET_IMMOBILIER
**Action:** INSERER_PRET
**Numéro:** 5009736BRLZE11AQ
**Montant:** 250000.00 EUR
**Durée:** 216 mois (18 ans)
**Taux:** 1.24%
**Type prêt:** IN_FINE
**Échéances extraites:** 216
**Fichier:** PRET_5009736BRLZE11AQ_echeances.md

Pour valider: [_Head] VALIDE: <token>
```

### Étape 5 : Valider les Propositions

#### Email de Validation
```
De: ulrik.c.s.be@gmail.com
À: u6334452013@gmail.com
Objet: [_Head] VALIDE: <token>
Corps: Validation de la proposition <token>
```

### Étape 6 : Vérifier l'Insertion en BD

```bash
# Depuis Render ou local
python inspecter_base.py
```

#### Résultat Attendu après Validation Bilan
```
EXERCICES COMPTABLES : 2
  ID 1 : Année 2023 (2023-01-01 → 2023-12-31) [OUVERT]
           Écritures associées: 12  ← Bilan d'ouverture inséré ✓

ÉCRITURES COMPTABLES : 12
  2023-01-01 : Compte 512 (Banque) +10000.00 EUR
  2023-01-01 : Compte 101 (Capital social) +10000.00 EUR
  ...
```

#### Résultat Attendu après Validation Prêt A
```
PRÊTS IMMOBILIERS : 1
  Prêt 1 : 5009736BRLZE11AQ (INVESTIMUR)
           Capital: 250000.00 EUR
           Taux: 1.24%
           Durée: 216 mois
           Type: IN_FINE

ÉCHÉANCES PRÊTS : 216
  2023-05-15 : 258.33 EUR (intérêts: 258.33, capital: 0.00)
  2023-06-15 : 258.33 EUR (intérêts: 258.33, capital: 0.00)
  ...
  2041-04-15 : 250258.33 EUR (intérêts: 258.33, capital: 250000.00)
```

---

## ✅ Critères de Succès

### Bilan d'Ouverture
- [ ] Email détecté comme INIT_BILAN_2023
- [ ] Proposition générée avec token
- [ ] Validation acceptée
- [ ] Écritures insérées en BD (12 écritures)
- [ ] Exercice 2023 contient les écritures

### Prêt A (INVESTIMUR)
- [ ] Email détecté comme PRET_IMMOBILIER
- [ ] PDF parsé avec V6 (216 échéances extraites)
- [ ] Fichier PRET_5009736BRLZE11AQ_echeances.md créé
- [ ] Proposition générée avec token
- [ ] Validation acceptée
- [ ] Prêt inséré en BD
- [ ] 216 échéances insérées en BD

### Prêt B (SOLUTION P IMMO)
- [ ] Email détecté comme PRET_IMMOBILIER
- [ ] PDF parsé avec V6 (⚠️ 251/252 échéances - problème connu)
- [ ] Fichier PRET_5009736BRM0911AH_echeances.md créé
- [ ] Proposition générée avec token
- [ ] Validation acceptée (si utilisateur OK avec 251 échéances)
- [ ] Prêt inséré en BD
- [ ] 251 échéances insérées en BD

---

## ⚠️ Problèmes Connus

### Prêt B - Décalage Échéances
**Symptôme** : 251 échéances extraites au lieu de 252
**Cause** : Transition franchise → intérêts → amortissement mal interprétée
**Impact** : Décalage à partir de la ligne 13 (95% de différences)
**Workaround** : Valider manuellement ou attendre amélioration prompt V6
**Référence** : RAPPORT_TEST_PARSEUR_V6.md

### Timeout max_tokens
**Symptôme** : "Streaming required for operations > 10 minutes"
**Solution** : max_tokens = 20000 (compromis), timeout = 600s
**Impact** : Extraction complète possible mais limitée

---

## 🔧 Dépannage

### Email Non Traité
1. Vérifier format objet : `[Soeurise]` ou `[_Head]`
2. Vérifier expéditeur : `ulrik.c.s.be@gmail.com`
3. Vérifier logs dans `main.py`

### Parseur V6 Échoue
1. Vérifier ANTHROPIC_API_KEY définie
2. Vérifier poppler-utils installé (`pdftoppm --version`)
3. Vérifier format PDF (tableaux LCL uniquement)

### Validation Refusée
1. Vérifier token exact dans email
2. Vérifier format : `[_Head] VALIDE: <token>`
3. Vérifier expéditeur autorisé

### Insertion BD Échoue
1. Vérifier contraintes uniques (numéro_pret, dates)
2. Vérifier exercice comptable existe
3. Vérifier logs PostgreSQL

---

## 📊 Métriques de Performance

### Temps d'Exécution (Estimé)
- Détection email : < 1s
- Parsing V6 Prêt A : ~60s
- Parsing V6 Prêt B : ~80s
- Génération propositions : < 5s
- Insertion BD : < 10s

### Coûts API Claude (Estimé)
- Bilan d'ouverture : ~5000 tokens (~0.02€)
- Prêt A (216 échéances) : ~40000 tokens (~0.08€)
- Prêt B (252 échéances) : ~40000 tokens (~0.08€)
- **Total session test** : ~0.18€

---

## 📝 Checklist Finale

Avant de déployer en production :
- [ ] Tous les tests passent (bilan + 2 prêts)
- [ ] Aucune régression sur V5 (si applicable)
- [ ] Logs clairs et informatifs
- [ ] Gestion d'erreurs robuste
- [ ] Documentation à jour
- [ ] Mémoires _Head.Soeurise mises à jour

---

**Philosophie** : Persévérer / Espérer / Progresser ✨

**Commit** : `5fb8182`
**Branche** : `claude/v6-architecture-impl-011CUhER84gzHmbSoYaE2bFG`
