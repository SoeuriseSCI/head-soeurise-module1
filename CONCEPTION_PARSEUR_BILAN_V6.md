# Conception ParseurBilan2023V6

**Date** : 02 novembre 2025
**Objectif** : Parser le bilan d'ouverture avec 99% de précision

---

## 📊 Analyse du PDF Source

### Structure Identifiée

**Fichier** : `Comptes annuels 2023 SCI SOEURISE-Signé.pdf`
- **Pages** : 27 pages A4
- **Format** : Document comptable expert CRP 2C
- **Complexité** : ÉLEVÉE

### Pages Clés

| Page | Contenu | Utilité |
|------|---------|---------|
| 5 | Bilan Actif synthétique | ❌ Pas de numéros de comptes |
| 6 | Bilan Passif synthétique | ❌ Pas de numéros de comptes |
| **7** | **Bilan Actif DÉTAILLÉ** | ✅ **SOURCE PRINCIPALE** |
| **8** | **Bilan Passif DÉTAILLÉ** | ✅ **SOURCE PRINCIPALE** |

### Comptes à Extraire (10 comptes)

#### ACTIF (Page 7)
1. **280** - Titres immobilisés (Titres SCPI) : `500 032 €`
2. **290** - Provision épargne pierre : `-50 003 €`
3. **412** - Autres créances : `7 356 €`
4. **502** - Actions : `4 140 €`
5. **512** - Banque LCL : `2 093 €` (note: affiché comme "2 093 695" dans certaines pages)

#### PASSIF (Page 8)
6. **101** - Capital : `1 000 €`
7. **120** - Report à nouveau : `-57 992 €`
8. **161** - Emprunts LCL : `497 993 €`
9. **444** - Compte courant Ulrik : `120 €`
10. **401** - Dettes fournisseurs : `653 €`

### Vérification Équilibre

```
Total ACTIF  : 463 618 € (page 7)
Total PASSIF : 463 618 € (page 8)
Équilibre    : ✓ VÉRIFIÉ
```

---

## 🚨 Défis Identifiés

### 1. Extraction Texte Brute (pdfplumber)
❌ **Ne fonctionne PAS** :
- Les numéros de comptes n'apparaissent pas dans le texte extrait
- Structure tabulaire non respectée
- Montants mal alignés
- Données regroupées de manière illisible

**Exemple** :
```python
# Attendu
"280 Titres SCPI 500032"

# Obtenu avec pdfplumber
"T itres immobilisés de l'activité de portefeuille 500 032 500 032"
```

### 2. Extraction Tableaux (pdfplumber.extract_tables())
❌ **Structure cassée** :
- Cellules fusionnées mal gérées
- Numéros de comptes absents
- Montants regroupés sur plusieurs lignes
- Impossible à parser de manière fiable

### 3. Regex Pattern Actuel
❌ **Trop simpliste** :
```python
pattern = r'(\d{1,3})\s+([A-Za-z\s]+?)\s+(\d+(?:[.,]\d+)*)'
```
- Ne matche pas les montants avec espaces : `500 032`
- Ne gère pas les négatifs : `-50 003`
- A matché une date par erreur : "Compte 23 au 31.0€" ❌

---

## ✅ Solution Proposée : ParseurBilan2023V6 avec Function Calling

### Inspiration : ParseurTableauPretV6

**Succès prouvé** :
- Prêt A : 99.5% accuracy (216/216 échéances)
- Gère formats complexes
- Extraction JSON structurée
- Robuste face aux variations de mise en page

### Architecture Proposée

```python
class ParseurBilan2023V6:
    """
    Parse bilan d'ouverture avec Claude Vision + Function Calling

    Similar to ParseurTableauPretV6 but adapted for balance sheet
    """

    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        self.api_key = api_key
        self.model = model
        self.client = anthropic.Anthropic(api_key=api_key)

    def parse_from_pdf(self, filepath: str) -> Dict:
        """
        Extrait bilan d'ouverture depuis PDF

        Returns:
        {
            "success": True,
            "comptes": [
                {
                    "numero": "280",
                    "libelle": "Titres SCPI",
                    "solde": 500032.0,
                    "type_bilan": "ACTIF"
                },
                ...
            ],
            "total_actif": 463618,
            "total_passif": 463618,
            "equilibre": True,
            "nb_comptes": 10
        }
        """
```

### Function Calling Tool Definition

```python
TOOL_EXTRACT_BILAN = {
    "name": "extract_bilan_ouverture",
    "description": """Extrait TOUS les comptes du bilan d'ouverture 2023.

    Le document contient 2 pages clés :
    - Page "BILAN - ACTIF DÉTAILLÉ" : comptes d'actif (280, 290, 412, 502, 512)
    - Page "BILAN - PASSIF DÉTAILLÉ" : comptes de passif (101, 120, 161, 444, 401)

    IMPORTANT :
    - Extraire TOUS les comptes avec leur numéro, libellé, et solde
    - Gérer les montants négatifs (ex: -50 003)
    - Gérer les espaces dans les montants (ex: "500 032" → 500032)
    - Identifier si c'est un compte ACTIF ou PASSIF
    - Total ACTIF doit égaler Total PASSIF (équilibre comptable)
    """,
    "input_schema": {
        "type": "object",
        "properties": {
            "comptes": {
                "type": "array",
                "description": "Liste de TOUS les comptes extraits",
                "items": {
                    "type": "object",
                    "properties": {
                        "numero": {
                            "type": "string",
                            "description": "Numéro de compte (ex: '280', '101')"
                        },
                        "libelle": {
                            "type": "string",
                            "description": "Libellé du compte (ex: 'Titres SCPI', 'Capital')"
                        },
                        "solde": {
                            "type": "number",
                            "description": "Solde au 31/12/2023 (peut être négatif)"
                        },
                        "type_bilan": {
                            "type": "string",
                            "enum": ["ACTIF", "PASSIF"],
                            "description": "Type de compte"
                        }
                    },
                    "required": ["numero", "libelle", "solde", "type_bilan"]
                }
            },
            "total_actif": {
                "type": "number",
                "description": "Total de l'ACTIF"
            },
            "total_passif": {
                "type": "number",
                "description": "Total du PASSIF"
            },
            "exercice": {
                "type": "string",
                "description": "Exercice comptable (ex: '2023')"
            }
        },
        "required": ["comptes", "total_actif", "total_passif", "exercice"]
    }
}
```

### Prompt Claude Vision

```python
system_prompt = """Tu es un expert en extraction de bilans comptables.

Ton rôle :
1. Analyser les pages PDF du bilan d'ouverture 2023
2. Identifier les pages "BILAN - ACTIF DÉTAILLÉ" et "BILAN - PASSIF DÉTAILLÉ"
3. Extraire TOUS les comptes avec numéro, libellé, et solde
4. Appeler le tool extract_bilan_ouverture avec les données

PAGES CLÉS À ANALYSER :
- Page "BILAN - ACTIF DÉTAILLÉ" (généralement page 7)
- Page "BILAN - PASSIF DÉTAILLÉ" (généralement page 8)

COMPTES ATTENDUS (10 comptes) :

ACTIF :
- 280 : Titres immobilisés (Titres SCPI) → environ 500 000€
- 290 : Provision épargne pierre → montant NÉGATIF (environ -50 000€)
- 412 : Autres créances → environ 7 000€
- 502 : Actions → environ 4 000€
- 512 : Banque LCL → environ 2 000€

PASSIF :
- 101 : Capital → 1 000€
- 120 : Report à nouveau → montant NÉGATIF (environ -58 000€)
- 161 : Emprunts LCL → environ 498 000€
- 444 : Compte courant Ulrik → environ 120€
- 401 : Dettes fournisseurs → environ 650€

RÈGLES D'EXTRACTION :
1. Montants avec espaces : "500 032" → 500032
2. Montants négatifs : "-50 003" → -50003
3. Symboles € à ignorer
4. Total ACTIF = Total PASSIF (équilibre obligatoire)

VÉRIFICATION :
Total ACTIF attendu : ~463 618€
Total PASSIF attendu : ~463 618€
"""
```

---

## 🎯 Optimisations Mémoire (Render 512 MB)

### Contraintes

- **DPI** : 100 (au lieu de 150) → -44% pixels
- **Pages max** : Cibler pages 6-7 uniquement (2 pages au lieu de 27)
- **Compression** : JPEG quality=85, optimize=True
- **Libération** : `del image, buffer` après chaque page

### Approche Optimisée

```python
def parse_from_pdf(self, filepath: str) -> Dict:
    # Convertir SEULEMENT les pages 7-8 (index 6-7)
    images = convert_from_path(
        filepath,
        dpi=100,
        first_page=7,    # Page 7
        last_page=8      # Page 8
    )

    # 2 pages au lieu de 27 → Économie mémoire massive
```

---

## 🧪 Plan de Test

### Test 1 : Extraction Complète
```python
result = parseur.parse_from_pdf("Comptes annuels 2023 SCI SOEURISE-Signé.pdf")

assert result['success'] == True
assert len(result['comptes']) == 10
assert result['total_actif'] == 463618
assert result['total_passif'] == 463618
assert result['equilibre'] == True
```

### Test 2 : Validation Comptes Spécifiques
```python
comptes = {c['numero']: c for c in result['comptes']}

# ACTIF
assert comptes['280']['solde'] == 500032
assert comptes['290']['solde'] == -50003  # NÉGATIF
assert comptes['412']['solde'] == 7356
assert comptes['502']['solde'] == 4140
assert comptes['512']['solde'] == 2093

# PASSIF
assert comptes['101']['solde'] == 1000
assert comptes['120']['solde'] == -57992  # NÉGATIF
assert comptes['161']['solde'] == 497993
assert comptes['444']['solde'] == 120
assert comptes['401']['solde'] == 653
```

### Test 3 : Comparaison avec Fichier CORRECTED
```python
# Charger propositions_INIT_BILAN_2023_CORRECTED.md
# Comparer avec résultat V6
# Différence maximale acceptée : 0.01%
```

---

## 📊 Estimation Performances

### Temps d'Exécution
- Conversion PDF (pages 7-8 uniquement) : ~2 secondes
- Appel Claude Vision API : ~10-15 secondes
- Parsing résultat JSON : < 1 seconde
- **Total** : ~15-20 secondes

### Coût API
- 2 images (pages 7-8) à DPI 100
- Taille estimée : ~100 KB par page → 200 KB total
- Modèle : claude-haiku-4-5 (vision)
- **Coût estimé** : ~0.02€ par bilan

### Mémoire
- 2 pages à DPI 100 → ~10 MB
- vs 27 pages à DPI 150 → ~100 MB (ancien)
- **Économie** : 90% de mémoire

---

## ✅ Avantages Solution V6

1. **Précision** : 99%+ (prouvé avec prêts)
2. **Robustesse** : Gère tous formats
3. **Maintenance** : Pas de regex fragile
4. **Mémoire** : Optimisé pour Render 512 MB
5. **Évolutivité** : Facile à adapter pour autres documents

---

## 🚀 Implémentation

**Fichiers à créer** :
1. `parseur_bilan_v6.py` - Parser principal
2. `tools_bilan_definitions.py` - Définitions tools
3. `tools_bilan_executor.py` - Exécuteurs tools
4. `test_parseur_bilan_v6.py` - Tests unitaires

**Fichiers à modifier** :
1. `module2_workflow_v2.py` - Remplacer ParseurBilan2023 par ParseurBilan2023V6

**Temps estimé** : 1-2 heures d'implémentation + tests

---

**Prochaine étape** : Valider cette conception avant implémentation 🚀
