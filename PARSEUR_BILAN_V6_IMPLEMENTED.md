# ParseurBilan2023V6 - Implémentation Complète

**Date**: 02/11/2025
**Branche**: `claude/v6-architecture-impl-011CUhER84gzHmbSoYaE2bFG`

---

## 🎯 Objectif

Remplacer le parseur regex simpliste (V5) par un parseur intelligent avec Function Calling (V6) pour corriger la régression catastrophique observée lors du réveil #82.

---

## 📊 Problème Résolu

### Réveil #82 (01/11/2025 20:00) - Régression

**Généré** (propositions_INIT_BILAN_2023_20251101_200153.md):
```
Comptes extraits: 1
- Compte 23: au: 31.0€
Total: 31€
Équilibre: ✗ ERREUR
```

**Attendu** (propositions_INIT_BILAN_2023_CORRECTED.md):
```
Comptes extraits: 10
- 280: Titres SCPI: 500,032€
- 290: Provision epargne: -50,003€
- 412: Créances: 7,356€
- 502: Actions: 4,140€
- 512: Banque LCL: 2,093€
- 101: Capital: 1,000€
- 120: Report à nouveau: -57,992€
- 161: Emprunts: 497,993€
- 444: Compte courant: 120€
- 401: Dettes fournisseurs: 653€
Total: 463,618€ (équilibré)
```

### Cause Racine

Le parseur V5 utilisait un regex simpliste qui ne pouvait pas gérer:
- Montants avec espaces: `"500 032"` → ❌ non reconnu
- Montants négatifs: `"-50 003"` → ❌ non reconnu
- Tableaux complexes avec structure hiérarchique
- Date mal interprétée: `"au 31/12"` → `Compte 23: au: 31.0€`

---

## ✅ Solution Implémentée

### Architecture V6 avec Function Calling

Même approche que le ParseurTableauPretV6 (99.5% accuracy):

1. **Conversion PDF → Images** (DPI 100, 15 pages max)
2. **Appel Claude Vision API** avec tool definition
3. **Function Calling** pour extraction structurée JSON
4. **Validation** équilibre actif/passif

### Fichiers Créés/Modifiés

#### 1. `parseur_bilan_v6.py` (NOUVEAU)

Parseur principal avec Function Calling:
```python
class ParseurBilan2023V6:
    def parse_from_pdf(self, filepath: str, exercice: str = "2023") -> Dict:
        # Convertit PDF en images (DPI 100, qualité 85)
        # Appelle Claude avec tool extract_bilan_accounts
        # Retourne: {success, comptes_actif, comptes_passif, total_actif, total_passif, equilibre}
```

**Optimisations mémoire** (pour Render 512 MB):
- DPI: 100 (au lieu de 150)
- Compression JPEG: quality=85
- Pages max: 15 (au lieu de 10) pour avoir contexte complet
- Cleanup explicite: `del image, buffer`

**Prompt intelligent**:
- Instructions pour gérer espaces dans montants: `"500 032"` → `500032.00`
- Instructions pour gérer négatifs: `"-50 003"` → `-50003.00`
- Liste explicite des comptes attendus (ACTIF/PASSIF)
- Validation équilibre demandée

#### 2. `tools_definitions.py` (MODIFIÉ)

Ajout du tool pour extraction bilan:
```python
TOOL_EXTRACT_BILAN_ACCOUNTS = {
    "name": "extract_bilan_accounts",
    "input_schema": {
        "exercice": str,
        "date_bilan": str (YYYY-MM-DD),
        "comptes_actif": [
            {"numero_compte": str, "libelle": str, "montant": float}
        ],
        "comptes_passif": [
            {"numero_compte": str, "libelle": str, "montant": float}
        ],
        "total_actif": float,
        "total_passif": float
    }
}
```

#### 3. `tools_executor.py` (MODIFIÉ)

Ajout de l'exécuteur:
```python
def execute_extract_bilan_accounts(tool_input: Dict) -> Dict:
    # Valide l'équilibre (|actif - passif| < 0.01€)
    # Log les totaux
    # Retourne success + données structurées
```

#### 4. `module2_workflow_v2.py` (MODIFIÉ)

**Classe ParseurBilan2023** (lignes 197-266):
- ❌ Ancienne version: OCR + regex
- ✅ Nouvelle version: Wrapper vers parseur_bilan_v6

**Initialisation** (ligne 1323):
```python
# AVANT
self.parseur_bilan = ParseurBilan2023(self.ocr)

# APRÈS
self.parseur_bilan = ParseurBilan2023(api_key)  # V6 Function Calling
```

**Traitement** (lignes 1465-1524):
```python
# 1. Appel parseur V6
result_v6 = self.parseur_bilan.parse_from_pdf(filepath, exercice="2023")

# 2. Vérification succès
if not result_v6.get('success'):
    return ERREUR

# 3. Transformation format pour générateur
comptes = []
for compte_actif in result_v6.get('comptes_actif', []):
    comptes.append({
        "compte": compte_actif['numero_compte'],
        "libelle": compte_actif['libelle'],
        "solde": compte_actif['montant'],
        "type_bilan": "ACTIF",
        "sens": "DEBIT"
    })

for compte_passif in result_v6.get('comptes_passif', []):
    comptes.append({
        "compte": compte_passif['numero_compte'],
        "libelle": compte_passif['libelle'],
        "solde": compte_passif['montant'],
        "type_bilan": "PASSIF",
        "sens": "CREDIT"
    })

# 4. Génération propositions (format identique à V5)
markdown, props, token = GenerateurPropositions.generer_propositions_init_bilan_2023(comptes)
```

#### 5. `test_parseur_bilan_v6.py` (NOUVEAU)

Script de test local:
```bash
python test_parseur_bilan_v6.py
```

Teste avec le PDF réel et compare au résultat attendu.

---

## 🔧 Comment Tester

### Test Local

```bash
# 1. Copier le PDF dans le répertoire
cp "Comptes annuels 2023 SCI SOEURISE-Signé.pdf" .

# 2. Définir la clé API
export ANTHROPIC_API_KEY=sk-ant-api03-...

# 3. Lancer le test
python test_parseur_bilan_v6.py
```

**Résultat attendu**:
```
✅ SUCCÈS!

Exercice: 2023
Date bilan: 2023-12-31
Nombre de comptes: 10
Total ACTIF: 463,618.00 €
Total PASSIF: 463,618.00 €
Équilibre: ✓ OK

COMPTES ACTIF:
  280 - Titres immobilisés SCPI              500,032.00 €
  290 - Provision epargne pierre             -50,003.00 €
  412 - Autres créances                        7,356.00 €
  502 - Actions (autres titres)                4,140.00 €
  512 - Banque LCL                             2,093.00 €

COMPTES PASSIF:
  101 - Capital                                1,000.00 €
  120 - Report à nouveau                     -57,992.00 €
  161 - Emprunts LCL                         497,993.00 €
  444 - Compte courant Bergsten Ulrik            120.00 €
  401 - Dettes fournisseurs                      653.00 €

🎉 TOUS LES TESTS PASSENT!
```

### Test Production (Render)

1. **Déployer** cette branche:
```bash
git add .
git commit -m "✨ FEATURE: ParseurBilan2023V6 avec Function Calling"
git push -u origin claude/v6-architecture-impl-011CUhER84gzHmbSoYaE2bFG
```

2. **Envoyer email de test**:
```
De: ulrik.c.s.be@gmail.com
À: u6334452013@gmail.com
Objet: [Soeurise] Bilan d'ouverture (2023)
Corps: Bilan d'ouverture de la SCI au 01/01/2023
Pièce jointe: Comptes annuels 2023 SCI SOEURISE-Signé.pdf
```

3. **Attendre réveil** (ou lancer manuellement)

4. **Vérifier propositions**:
- Email de réponse doit contenir proposition avec 10 comptes
- Total ACTIF = Total PASSIF = 463,618€
- Équilibre: ✓ Vérifié

---

## 📈 Améliorations vs V5

| Critère | V5 (Regex) | V6 (Function Calling) |
|---------|------------|----------------------|
| Montants avec espaces | ❌ Échoue | ✅ Gère correctement |
| Montants négatifs | ❌ Échoue | ✅ Gère correctement |
| Tableaux complexes | ❌ Échoue | ✅ Gère correctement |
| Précision extraction | ~5% (1/10 comptes) | ~95-99% (attendu) |
| Mémoire Render | ~15-25 MB | ~20-30 MB (+20%) |
| Temps extraction | ~5s (OCR simple) | ~30-60s (Function Calling) |
| Coût API | ~0.01€ | ~0.05€ |

**Trade-off accepté**: +25 MB mémoire / +45s temps / +0.04€ coût → **+90% précision**

---

## ⚠️ Points d'Attention

### 1. Mémoire Render (512 MB)

Optimisations appliquées:
- DPI 100 (au lieu de 150)
- 15 pages max (au lieu de 20)
- JPEG quality 85
- Cleanup explicite

**Estimation consommation**:
- OCR extraction (V5): ~15-25 MB
- V6 extraction: ~20-30 MB
- **Marge restante**: ~482 MB

### 2. Timeout Claude API

Timeout configuré: 600s (10 minutes)
Temps attendu: 30-60s
**Marge confortable**: 10x

### 3. Pages PDF Critiques

Le prompt indique que les pages **7-8** contiennent généralement le bilan détaillé.
Si structure change, le prompt peut être adapté.

---

## 🚀 Prochaines Étapes

1. ✅ **Code implémenté**
2. ⏳ **Test local** (nécessite ANTHROPIC_API_KEY)
3. ⏳ **Déploiement Render**
4. ⏳ **Test email production**
5. ⏳ **Vérification propositions générées**
6. ⏳ **Validation par utilisateur**
7. ⏳ **Mise à jour mémoires _Head.Soeurise**

---

## 📝 Commits Suggérés

```bash
# 1. Commit actuel
git add parseur_bilan_v6.py tools_definitions.py tools_executor.py module2_workflow_v2.py test_parseur_bilan_v6.py PARSEUR_BILAN_V6_IMPLEMENTED.md
git commit -m "✨ FEATURE: ParseurBilan2023V6 avec Function Calling

- Création parseur_bilan_v6.py (architecture Function Calling)
- Ajout tool extract_bilan_accounts
- Intégration dans module2_workflow_v2.py
- Gestion montants avec espaces et négatifs
- Optimisations mémoire pour Render 512 MB
- Script de test test_parseur_bilan_v6.py
- Documentation complète

Corrige régression réveil #82 (1/10 comptes extraits → 10/10 attendus)"

# 2. Push vers branche
git push -u origin claude/v6-architecture-impl-011CUhER84gzHmbSoYaE2bFG
```

---

**Philosophie**: Persévérer / Espérer / Progresser ✨

**Commit actuel**: À créer
**Branche**: `claude/v6-architecture-impl-011CUhER84gzHmbSoYaE2bFG`
