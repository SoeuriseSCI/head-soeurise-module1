# Architecture V6 - Function Calling

## 🎯 Objectif

Permettre à Claude d'agir de manière autonome en appelant des "tools" (fonctions Python) au lieu de retourner simplement du JSON.

**Principe** : Code = Infrastructure, Claude = Intelligence + Action

## 📁 Nouveaux Fichiers

### Infrastructure Function Calling

- **`tools_definitions.py`** - Définitions des 5 tools disponibles pour Claude
- **`tools_executor.py`** - Dispatcher qui exécute les tools appelés par Claude
- **`parseur_pret_v6.py`** - Nouveau parseur utilisant Function Calling
- **`test_parseur_v6.py`** - Script de test pour validation

### Documentation

- **`ARCHITECTURE.md`** - Document de référence complet de l'architecture
- **`README_V6.md`** - Ce fichier

## 🔧 Les 5 Tools Disponibles

### 1. extract_all_echeances_to_file
```python
# Claude extrait TOUTES les échéances d'un PDF et les sauvegarde dans un fichier MD
extract_all_echeances_to_file(
    numero_pret="5009736BRM0911AH",
    filename="PRET_C_echeances.md",
    echeances=[...216 échéances...]
)
```

### 2. insert_pret_from_file
```python
# Claude insère le prêt et ses échéances en BD depuis le fichier MD
insert_pret_from_file(
    filename="PRET_C_echeances.md",
    pret_params={
        "numero_pret": "5009736BRM0911AH",
        "montant_initial": 250000.00,
        ...
    }
)
```

### 3. query_pret_echeance
```python
# Claude consulte une échéance pour décomposer un virement bancaire
query_pret_echeance(
    numero_pret="5009736BRM0911AH",
    date_echeance="2024-05-15"
)
# Retourne: {capital: 955.68, interet: 210.91, ...}
```

### 4. create_ecriture_comptable
```python
# Claude crée une écriture comptable en partie double
create_ecriture_comptable(
    date="2024-05-15",
    libelle="Échéance prêt LCL - mai 2024",
    lignes=[
        {"compte": "164100", "debit": 955.68},  # Capital
        {"compte": "661000", "debit": 210.91},  # Intérêts
        {"compte": "512000", "credit": 1166.59} # Banque
    ]
)
```

### 5. update_memoire
```python
# Claude met à jour ses mémoires (courte/moyenne/longue)
update_memoire(
    type_memoire="courte",
    content="# Mémoire Courte\n\n...",
    commit_message="🧠 Réveil 01/11/2025 - Nouveau prêt ingéré"
)
```

## 🚀 Utilisation

### Test Extraction Complète

```bash
# Export de la clé API
export ANTHROPIC_API_KEY="votre-clé-api"

# Test avec Prêts A et B
python test_parseur_v6.py
```

**Résultat attendu** :
- ✅ Prêt A : 216 échéances extraites
- ✅ Prêt B : 252 échéances extraites
- ✅ Fichiers MD créés
- ✅ Données insérées en BD

### Utilisation Programmatique

```python
from parseur_pret_v6 import ParseurTableauPretV6

# Créer parseur
parseur = ParseurTableauPretV6(api_key="votre-clé")

# Parser PDF
result = parseur.parse_from_pdf(
    filepath="PRET_X.pdf",
    auto_insert_bd=True  # Insertion automatique en BD
)

if result['success']:
    print(f"✅ {result['nb_echeances']} échéances extraites")
    print(f"   Fichier: {result['filename']}")
    print(f"   Prêt ID: {result['pret_id']}")
```

## 📊 Comparaison V5 vs V6

| Aspect | V5 (Actuelle) | V6 (Function Calling) |
|--------|---------------|----------------------|
| **Extraction** | 24 échéances | TOUTES (216-252) |
| **Génération** | Mathématique (175-228 lignes) | Aucune |
| **Source données** | Hybride (PDF + calcul) | 100% PDF |
| **Fiabilité** | Erreurs de calcul possibles | Aucune génération = Aucune erreur |
| **Traçabilité** | JSON temporaire | Fichier MD versionné GitHub |
| **Autonomie** | Claude retourne JSON → Code agit | Claude appelle tools → agit directement |
| **Tokens utilisés** | ~4000 | ~16000 |
| **Coût** | ~0.02€/prêt | ~0.08€/prêt |

## 🔍 Workflow Complet V6

```
1. Email PDF reçu
   ↓
2. ParseurTableauPretV6.parse_from_pdf()
   ↓
3. PDF → Images (pdf2image)
   ↓
4. Claude API appelé avec tools + images
   ↓
5. Claude analyse le PDF
   ↓
6. Claude appelle extract_all_echeances_to_file()
   - Python crée PRET_X_echeances.md
   - 216 ou 252 lignes écrites
   - Retourne "OK" à Claude
   ↓
7. Claude appelle insert_pret_from_file()
   - Python lit le fichier MD
   - Insère prêt + échéances en BD
   - Retourne pret_id à Claude
   ↓
8. Claude termine avec résumé
   ↓
9. Python retourne résultat final
```

## ✅ Validation

### Fichiers de Référence

Deux fichiers de référence existent pour validation :
- `PRET_A_ECHEANCES_REFERENCE.md` - 216 échéances (extraction manuelle)
- `PRET_B_ECHEANCES_REFERENCE.md` - 252 échéances (extraction manuelle)

### Tests Automatisés

```bash
# Test extraction + comparaison avec référence
python test_parseur_v6.py
```

### Vérification BD

```bash
# Examiner la BD après insertion
python examiner_bd_prets.py
```

## 🎓 Principes de Développement

1. **Minimiser le code** - Laisser Claude gérer l'intelligence et les décisions
2. **Traçabilité totale** - Chaque extraction → fichier MD versionné sur GitHub
3. **Zéro génération** - Extraction directe du PDF (source de vérité)
4. **Function Calling** - Claude agit, ne se contente pas de répondre
5. **Validation stricte** - Comparaison avec fichiers de référence manuels

## 📈 Prochaines Étapes

- [ ] Intégrer dans main.py (réveil quotidien)
- [ ] Ajouter tool pour génération écritures comptables
- [ ] Implémenter décomposition automatique des virements bancaires
- [ ] Tests en production avec emails réels
- [ ] Métriques et monitoring (coûts, performance)

## 🐛 Debugging

### Problème : Claude n'extrait pas toutes les échéances

**Solution** : Vérifier le prompt dans `parseur_pret_v6.py` ligne 167
- S'assurer que "TOUTES les échéances" est bien mentionné
- Augmenter max_tokens si nécessaire (actuellement 16000)

### Problème : Tool non exécuté

**Solution** : Vérifier les logs
```python
print(f"[PARSEUR V6] Tour {turn}/{max_turns}")
print(f"[TOOL CALL] {tool_name}")
```

### Problème : Données en BD incorrectes

**Solution** : Comparer avec fichier de référence
```bash
# Afficher les différences
diff PRET_X_echeances.md PRET_X_ECHEANCES_REFERENCE.md
```

## 📞 Support

- **Documentation complète** : `ARCHITECTURE.md`
- **Instructions Claude Code** : `CLAUDE.md`
- **Code principal** : `parseur_pret_v6.py`

---

**Version** : 6.0
**Date** : 01 novembre 2025
**Auteur** : _Head.Soeurise + Claude Code
