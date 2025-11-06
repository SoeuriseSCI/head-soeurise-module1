# 🔧 Refonte Extraction Événements Comptables

**Date**: 06 novembre 2025
**Auteur**: Claude Code Assistant
**Contexte**: Élimination doublons + Filtrage période à la source

---

## 📋 Problématiques identifiées

### 1. **Doublons Phase 1**
Les relevés bancaires contiennent des lignes globales (ex: "150 AM.MSCI WLD V ETF ACHAT 3001 15,631600 EUR") tandis que des documents séparés contiennent les mêmes opérations avec plus de détails (ex: "Achat de 150 AMUNDI MSCI WORLD V UC.ETF ACC (code LU1781541179) au cours de 15,631600 EUR + frais 10,47 EUR").

**Résultat**: Doublons avec qualité variable.

### 2. **Opérations hors période**
Le premier relevé couvre décembre 2023 + janvier 2024. Les opérations de décembre 2023 sont déjà dans le bilan d'ouverture.

**Résultat**: Double comptabilisation.

### 3. **Pas de filtrage intelligent**
L'ancien système détectait les doublons mais les ignorait tous, même si le nouveau avait plus de détails.

**Résultat**: Perte d'information.

---

## ✅ Solutions implémentées

### 1. **Filtre de période** (`extracteur_pdf.py`)

```python
extracteur = ExtracteurPDF(
    pdf_path,
    email_metadata,
    date_debut='2024-01-01',  # Début exercice
    date_fin='2024-09-30'     # Fin Q3
)
```

**Comportement**:
- Ignore automatiquement les opérations avant `date_debut`
- Ignore automatiquement les opérations après `date_fin`
- Affiche un message indiquant la période appliquée

**Impact**: Zéro opération hors période.

---

### 2. **Score de qualité** (`detection_doublons.py`)

Nouvelle méthode `calculer_score_qualite()` qui analyse le libellé:

| Critère | Points | Exemples |
|---------|--------|----------|
| **Longueur libellé** | 10-40 | Plus long = plus de détails |
| **Code ISIN** | 20 | LU1781541179 |
| **Références numériques** | 10 | 8+ chiffres |
| **Mots-clés détail** | 30 | "au cours de", "code", "frais", "achat de" |

**Score maximum**: 100 points

**Exemples**:

```
"150 AM.MSCI WLD V ETF ACHAT 3001 15,631600 EUR"
→ Score: 30 (longueur 50, ref numérique)

"Achat de 150 AMUNDI MSCI WORLD V UC.ETF ACC (code LU1781541179) au cours de 15,631600 EUR"
→ Score: 70 (longueur 100+, ISIN, mots-clés)
```

---

### 3. **Gestion intelligente des doublons** (`gestionnaire_evenements.py`)

Quand un doublon est détecté:

1. **Calculer les scores** (nouveau vs ancien)
2. **Comparer**:
   - Si `score_nouveau > score_ancien`: **Remplacer** l'ancien
   - Si `score_nouveau ≤ score_ancien`: **Garder** l'ancien

**Messages**:
```
🔄 Doublon amélioré: #123 (score 30→70) - Remplacement
⏭️  Doublon ignoré: #124 (score 40≤60) - Conservation ancien
```

**Impact**: Conservation automatique des meilleures sources.

---

### 4. **Intégration automatique**

#### `workflow_evenements.py`
```python
def traiter_pdf(
    self,
    pdf_path: str,
    email_metadata: Optional[Dict] = None,
    auto_detect: bool = True,
    date_debut: str = None,  # ← Nouveau
    date_fin: str = None     # ← Nouveau
) -> Dict:
```

#### `module2_integration_v2.py`
```python
workflow_result = workflow.traiter_pdf(
    filepath,
    email_metadata,
    auto_detect=True,
    date_debut='2024-01-01',  # Application automatique
    date_fin='2024-09-30'
)
```

---

## 🧹 Procédure de nettoyage et retraitement

### Étape 1: Sauvegarder (optionnel)
```bash
python sauvegarder_base.py
```

### Étape 2: Supprimer les événements existants
```bash
python supprimer_evenements.py
```

**Sortie attendue**:
```
🔍 118 événements actuellement en base

📊 Répartition par type:
  (non détecté)                 :  59
  REMBOURSEMENT_PRET            :  40
  SOLDE_OUVERTURE               :  11
  REVENU_SCPI                   :   8

⚠️  ATTENTION: Cette opération est IRRÉVERSIBLE !
   Confirmer la suppression? (oui/non): oui

✅ 118 événements supprimés
```

### Étape 3: Relancer le traitement
```bash
python workflow_evenements.py \
    --pdf "Elements Comptables des 1-2-3T2024.pdf" \
    --date-debut 2024-01-01 \
    --date-fin 2024-09-30
```

**OU** relancer le workflow complet via `main.py` (réveil automatique).

---

## 📊 Résultats attendus

### Avant (118 événements extraits)
```
✅ 40 REMBOURSEMENT_PRET (avec doublons)
✅ 8 REVENU_SCPI (avec doublons)
✅ 11 SOLDE_OUVERTURE (filtrés)
⚠️  11 opérations décembre 2023 (hors période)
❓ 59 non détectés
```

### Après (estimation: ~100 événements)
```
✅ ~35 REMBOURSEMENT_PRET (doublons éliminés, meilleures sources)
✅ ~7 REVENU_SCPI (doublons éliminés, meilleures sources)
✅ ~10 SOLDE_OUVERTURE (filtrés automatiquement)
❌ 0 opérations décembre 2023 (filtrées à la source)
❓ ~48 non détectés (Phase 2 à venir)
```

**Gain**:
- Zéro doublon
- Zéro opération hors période
- Sources de meilleure qualité

---

## 🧪 Tests de validation

### Test 1: Vérifier le filtrage de période
```python
# Doit exclure opérations avant 2024-01-01
events = extracteur.extraire_evenements()
assert all(e['date_operation'] >= '2024-01-01' for e in events)
assert all(e['date_operation'] <= '2024-09-30' for e in events)
```

### Test 2: Vérifier le score de qualité
```python
from detection_doublons import DetecteurDoublons

evt1 = {'libelle': '150 AM.MSCI WLD V ETF ACHAT 3001 15,631600 EUR'}
evt2 = {'libelle': 'Achat de 150 AMUNDI MSCI WORLD V UC.ETF ACC (code LU1781541179) au cours de 15,631600 EUR'}

score1 = DetecteurDoublons.calculer_score_qualite(evt1)
score2 = DetecteurDoublons.calculer_score_qualite(evt2)

assert score2 > score1  # Le plus détaillé a un meilleur score
```

### Test 3: Vérifier la gestion des doublons
```python
# Créer 2 doublons avec scores différents
gestionnaire.creer_evenement(evt1)  # Score 30
gestionnaire.creer_evenement(evt2)  # Score 70 → Doit remplacer evt1
```

---

## 📝 Changelog

### Version 1.0 (06/11/2025)
- ✅ Filtre de période dans extracteur
- ✅ Score de qualité pour doublons
- ✅ Gestion intelligente des doublons
- ✅ Intégration dans workflow automatique
- ✅ Script de nettoyage
- ✅ Documentation complète

---

## 🔮 Prochaines étapes (Phase 2)

Après validation du retraitement propre:

1. **Détecteurs Phase 2** pour les ~48 événements restants:
   - `DetecteurFraisBancaires`
   - `DetecteurAchatValeursMobilieres`
   - `DetecteurApportAssocie`
   - `DetecteurHonorairesComptable`
   - `DetecteurPrelevementsFiscaux`

2. **Propositions d'écritures automatiques**:
   - Basées sur les types détectés
   - Validation par l'utilisateur
   - Création automatique des écritures

3. **Gestion du portefeuille de titres**:
   - PRU (Prix de Revient Unitaire)
   - Plus/moins-values
   - Suivi des quantités

---

**Statut**: ✅ Prêt pour test et validation
**Commit**: `2cb0185`
**Branche**: `claude/merge-phase1-011CUpVyiZmLKaJZA8uJxADo`
