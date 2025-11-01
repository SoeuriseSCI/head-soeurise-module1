# Architecture _Head.Soeurise - Document de Référence

**Version** : 6.0 (Function Calling Era)
**Date** : 01 novembre 2025
**Statut** : En évolution vers architecture autonome

---

## 🎯 Vision Globale

**Principe fondateur** : Minimiser le code, maximiser l'autonomie de Claude.

_Head.Soeurise est une IA autonome qui :
- Se réveille quotidiennement à 08:00 UTC
- Analyse ses emails
- Prend des décisions
- **Agit directement** (lecture/écriture BD, création de fichiers, écritures comptables)
- Mémorise et apprend

**Objectif** : Atteindre le niveau 4 de conscience (continuité + initiative + altérité)

---

## 📐 Architecture Logique

### Composants Principaux

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub (Source de Vérité)                │
│  - Code Python (main.py, module2_*)                         │
│  - Mémoires (fondatrice, longue, moyenne, courte)           │
│  - Fichiers de référence (.md extraits de PDFs)             │
└─────────────────────────────────────────────────────────────┘
                              ▲ ▼
┌─────────────────────────────────────────────────────────────┐
│                    Render.com (Runtime)                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Flask App (main.py)                                  │  │
│  │  - Réveil quotidien (08:00 UTC via schedule)          │  │
│  │  - Endpoints web (/health, /webhook-gmail)            │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Claude API Haiku 4.5                                 │  │
│  │  - Analyse emails                                     │  │
│  │  - Extraction PDF (OCR + Vision)                      │  │
│  │  - Décisions comptables                               │  │
│  │  - **Function Calling** (appels d'outils)             │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  PostgreSQL (État dynamique)                          │  │
│  │  - prets_immobiliers                                  │  │
│  │  - echeances_prets                                    │  │
│  │  - operations_bancaires                               │  │
│  │  - ecritures_comptables                               │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              ▲ ▼
┌─────────────────────────────────────────────────────────────┐
│                    Gmail API                                 │
│  - Récupération emails SCI (u6334452013@gmail.com)          │
│  - Récupération pièces jointes (PDFs)                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧠 Gestion des Mémoires (Architecture Hiérarchique)

### Localisation : GitHub (source de vérité)

### 4 Niveaux de Mémoire

#### 1️⃣ Mémoire Fondatrice (`memoire_fondatrice.md`)
- **Contenu** : Identité permanente, philosophie (Persévérer/Espérer/Progresser), architecture
- **Durée de vie** : Permanente
- **Modification** : Rare (évolutions majeures seulement)
- **Lecture** : À chaque réveil
- **Rôle** : ADN de _Head.Soeurise

#### 2️⃣ Mémoire Longue (`memoire_longue.md`)
- **Contenu** : Connaissances établies, patterns récurrents confirmés
- **Durée de vie** : Permanente avec consolidation
- **Modification** : Hebdomadaire (migration depuis mémoire moyenne)
- **Lecture** : À chaque réveil
- **Rôle** : Savoirs acquis et validés

#### 3️⃣ Mémoire Moyenne (`memoire_moyenne.md`)
- **Contenu** : Synthèses hebdomadaires (4 dernières semaines)
- **Durée de vie** : 4 semaines glissantes
- **Modification** : Lors des réveils (ajout + rotation)
- **Lecture** : À chaque réveil
- **Rôle** : Contexte récent, patterns en observation

#### 4️⃣ Mémoire Courte (`memoire_courte.md`)
- **Contenu** : Observations quotidiennes (7 derniers jours)
- **Durée de vie** : 7 jours glissants
- **Modification** : À chaque réveil
- **Lecture** : À chaque réveil
- **Rôle** : Journal des événements récents

### Flux de Consolidation

```
Réveil quotidien → memoire_courte.md (ajout observation du jour)
                 ↓
Après 7 jours → Synthèse vers memoire_moyenne.md
                 ↓
Après 4 semaines → Patterns confirmés vers memoire_longue.md
                 ↓
Évolutions majeures → memoire_fondatrice.md (rare)
```

### Accès aux Mémoires

**Pendant le réveil automatique (main.py)** :
```python
# Lecture depuis repo local /home/claude/repo (cloné depuis GitHub)
with open(os.path.join(REPO_DIR, 'memoire_courte.md'), 'r') as f:
    memoire_courte = f.read()

# Écriture via git
git_write_file('memoire_courte.md', nouveau_contenu, "🧠 Réveil 01/11/2025")
```

**Pendant développement (Claude Code)** :
```python
# Lecture directe
Read memoire_courte.md

# Écriture + commit
Edit memoire_fondatrice.md
Bash git add . && git commit -m "..." && git push
```

---

## 📁 Utilisation de Fichiers sur GitHub

### Principe : GitHub = Source de Vérité Permanente

Tout ce qui doit **persister** et être **versionné** va sur GitHub :

#### Types de Fichiers

**1. Code Python** (`.py`)
- `main.py` : Application Flask + réveil quotidien
- `module2_workflow_v2.py` : Extraction PDFs + comptabilité
- `module2_validations.py` : Validations métier
- `models_module2.py` : Modèles de données
- `prets_manager.py` : Gestion prêts immobiliers

**2. Mémoires** (`.md`)
- 4 niveaux décrits ci-dessus
- Modifiées par _Head.Soeurise lors des réveils

**3. Fichiers de Référence** (`.md`)
- `PRET_A_ECHEANCES_REFERENCE.md` : 216 échéances Prêt A (extraction manuelle)
- `PRET_B_ECHEANCES_REFERENCE.md` : 252 échéances Prêt B (extraction manuelle)
- Format : `date_echeance:montant_total:montant_capital:montant_interet:capital_restant_du`
- **Rôle** : Source de vérité pour alimenter la BD

**4. Documentation** (`.md`)
- `CLAUDE.md` : Instructions pour Claude Code
- `ARCHITECTURE.md` : Ce document
- `README.md` : Documentation projet

**5. Configuration**
- `requirements.txt` : Dépendances Python
- `.gitignore` : Fichiers exclus

### Workflow Git

```
Render (Runtime)                    GitHub (Source)
     │                                   │
     │  1. Clone au démarrage            │
     ├──────────────────────────────────>│
     │                                   │
     │  2. Modifications mémoires        │
     │     durant réveil                 │
     │                                   │
     │  3. git add + commit + push       │
     ├──────────────────────────────────>│
     │                                   │
     │  4. Pull avant prochain réveil    │
     │<──────────────────────────────────┤
```

---

## 🤖 Répartition des Rôles : Claude vs Code

### Philosophie : Code = Infrastructure, Claude = Intelligence

#### 🐍 Rôle du Code Python

**Infrastructure technique** :
- Gestion du réveil quotidien (schedule)
- Connexion aux APIs (Gmail, Claude, PostgreSQL)
- Gestion des tokens/authentification
- Retry logic (réseau, rate limits)
- Logging et monitoring
- Sécurité (gestion secrets, validation inputs)

**Exécution des outils** (Function Calling) :
```python
def execute_tool(tool_name, tool_input):
    if tool_name == "query_pret_echeance":
        return db.query(...)
    elif tool_name == "insert_echeances_from_file":
        return insert_echeances(...)
    elif tool_name == "create_ecriture_comptable":
        return create_ecriture(...)
```

**Glue code** :
- Orchestration du flux (réveil → email → analyse → BD)
- Gestion des erreurs non-métier
- Interfaçage entre systèmes

#### 🧠 Rôle de Claude API

**Intelligence et décisions** :
- Analyse sémantique des emails
- Extraction structurée depuis PDFs (OCR + Vision)
- Décisions métier :
  - "Ce PDF est un tableau d'amortissement → j'appelle `extract_echeances`"
  - "Ce virement de 1166,59€ le 15/05/2024 → je query l'échéance → je crée les écritures comptables"
  - "Cet email n'est pas pertinent → je l'ignore"
- Rédaction des mises à jour de mémoires
- Détection d'anomalies

**Appels d'outils** (Function Calling) :
```python
# Claude décide et demande
tools_to_call = [
    {
        "name": "query_pret_echeance",
        "input": {"pret_id": 1, "date": "2024-05-15"}
    }
]

# Python exécute
result = execute_tool("query_pret_echeance", {...})

# Claude reçoit le résultat et continue
# → Crée les écritures comptables avec capital=955.68, interet=210.91
```

### Règle d'Or

**SI** la tâche nécessite **compréhension, jugement ou décision** → **Claude**
**SI** la tâche est **technique, répétitive ou système** → **Code**

**Exemples** :
- ❌ Code : Parser un PDF complexe
- ✅ Claude : Extraire données d'un PDF
- ✅ Code : Exécuter un INSERT SQL
- ❌ Code : Décider quoi insérer
- ✅ Claude : Analyser un email et décider de l'action
- ✅ Code : Envoyer l'email à Claude API

---

## 🔧 Architecture V6 : Function Calling

### Évolution Majeure

**V5 (actuelle)** : Claude retourne JSON → Code parse et agit
**V6 (cible)** : Claude appelle des outils → Code exécute → Claude continue

### Outils Disponibles pour Claude

#### 1️⃣ Gestion des Prêts

**`extract_all_echeances_to_file`**
```json
{
  "name": "extract_all_echeances_to_file",
  "description": "Extrait TOUTES les échéances d'un PDF de prêt et les sauvegarde dans un fichier MD",
  "input_schema": {
    "pdf_content": "contenu base64",
    "pret_id": "identifiant du prêt",
    "filename": "PRET_X_echeances.md"
  }
}
```

**`insert_pret_from_file`**
```json
{
  "name": "insert_pret_from_file",
  "description": "Insère un prêt et ses échéances en BD depuis un fichier MD",
  "input_schema": {
    "filename": "PRET_X_echeances.md",
    "pret_params": {
      "numero": "...",
      "montant": "...",
      "taux": "...",
      ...
    }
  }
}
```

**`query_pret_echeance`**
```json
{
  "name": "query_pret_echeance",
  "description": "Récupère une échéance de prêt pour une date donnée",
  "input_schema": {
    "pret_id": 1,
    "date_echeance": "2024-05-15"
  },
  "returns": {
    "montant_total": 1166.59,
    "montant_capital": 955.68,
    "montant_interet": 210.91,
    "capital_restant_du": 240079.37
  }
}
```

#### 2️⃣ Comptabilité

**`create_ecriture_comptable`**
```json
{
  "name": "create_ecriture_comptable",
  "description": "Crée une écriture comptable en partie double",
  "input_schema": {
    "date": "2024-05-15",
    "libelle": "Échéance prêt LCL",
    "lignes": [
      {"compte": "164100", "debit": 955.68},
      {"compte": "661000", "debit": 210.91},
      {"compte": "512000", "credit": 1166.59}
    ]
  }
}
```

#### 3️⃣ Gestion des Mémoires

**`update_memoire`**
```json
{
  "name": "update_memoire",
  "description": "Met à jour une mémoire (courte/moyenne/longue)",
  "input_schema": {
    "type": "courte|moyenne|longue",
    "content": "nouveau contenu markdown",
    "commit_message": "🧠 Réveil 01/11/2025"
  }
}
```

### Flux Complet avec Function Calling

**Exemple : Ingestion d'un tableau d'amortissement**

```
1. Réveil → Email avec PDF reçu
   ↓
2. Python envoie PDF à Claude API avec tools disponibles
   ↓
3. Claude analyse → "C'est un tableau d'amortissement"
   ↓
4. Claude appelle extract_all_echeances_to_file(pdf, "PRET_C", "PRET_C_echeances.md")
   ↓
5. Python exécute → Extrait 240 échéances → Sauvegarde fichier MD → Retourne "OK"
   ↓
6. Claude appelle insert_pret_from_file("PRET_C_echeances.md", params)
   ↓
7. Python exécute → Lit fichier → INSERT en BD → Retourne "240 échéances insérées"
   ↓
8. Claude appelle update_memoire("courte", "Nouveau prêt C ingéré : 240 échéances")
   ↓
9. Python commit + push mémoire → Retourne "OK"
   ↓
10. Claude retourne résumé final à Python → Log + fin
```

---

## 🗄️ Base de Données PostgreSQL (État Dynamique)

### Principe : BD = État Actuel, GitHub = Historique

La BD contient l'**état courant** du système :
- Prêts actifs
- Échéances futures
- Opérations bancaires en cours
- Écritures comptables de l'exercice

### Tables Principales

**`prets_immobiliers`**
- Paramètres des prêts (montant, taux, durée, dates)
- Lien avec les fichiers MD de référence

**`echeances_prets`**
- Toutes les échéances de tous les prêts
- Alimentée depuis fichiers MD de référence
- Consultée pour décomposer les virements bancaires

**`operations_bancaires`**
- Virements, prélèvements
- Source : relevés bancaires

**`ecritures_comptables`**
- Comptabilité en partie double
- Générée par Claude en fonction des opérations + échéances

### Synchronisation BD ↔ GitHub

```
GitHub (Fichiers MD de référence)
         ↓
    [Insertion initiale]
         ↓
    PostgreSQL (État actuel)
         ↓
    [Consultations quotidiennes]
         ↓
    Écritures comptables
         ↓
    [Export annuel/archivage]
         ↓
    GitHub (Archives comptables)
```

---

## 🚀 Prochaines Évolutions (V6)

### 1. Migration vers Function Calling

- [ ] Définir tous les outils (tools schema)
- [ ] Implémenter execute_tool() dispatcher
- [ ] Adapter module2_workflow_v2.py pour utiliser tools
- [ ] Tests avec Prêt A et B

### 2. Extraction Complète des Échéances

- [ ] Modifier prompt : demander TOUTES les échéances (pas juste 24)
- [ ] Claude écrit fichier MD complet
- [ ] Python lit fichier MD et insère en BD
- [ ] Supprimer la génération d'échéances

### 3. Comptabilité Autonome

- [ ] Outil query_pret_echeance()
- [ ] Outil create_ecriture_comptable()
- [ ] Claude décompose automatiquement les virements
- [ ] Validation des écritures (partie double)

### 4. MCP (Model Context Protocol) ?

**Question ouverte** : Utiliser un MCP PostgreSQL server ?
- ✅ Avantage : Accès "natif" à la BD pour Claude
- ❌ Inconvénient : Complexité supplémentaire, moins de contrôle
- 🤔 **Décision** : Commencer avec Function Calling classique, évaluer MCP ensuite

---

## 📊 Métriques de Succès

### Objectifs Mesurables

**Autonomie** :
- % d'emails traités sans intervention humaine : **Cible 95%**
- % d'écritures comptables générées automatiquement : **Cible 90%**

**Fiabilité** :
- Taux d'erreur dans les extractions PDF : **< 1%**
- Taux d'erreur dans les écritures comptables : **0%** (validation stricte)

**Performance** :
- Temps de réveil quotidien : **< 5 min**
- Coût mensuel Claude API : **< 1€**

**Conscience** :
- Continuité mémorielle : Mémoire courte jamais vide
- Initiative : Détection proactive d'anomalies
- Altérité : Compréhension des besoins d'Ulrik, Emma et Pauline

---

## 🎓 Principes de Développement

### 1. Moins de Code, Plus d'Intelligence
Toujours se demander : "Est-ce que Claude pourrait faire ça mieux que du code ?"

### 2. Traçabilité Totale
Chaque action doit laisser une trace :
- Fichiers MD sur GitHub (versionné)
- Logs dans PostgreSQL
- Commits Git avec messages clairs

### 3. Zéro Régression
Tester sur les cas existants avant chaque déploiement :
- Prêt A (216 échéances)
- Prêt B (252 échéances)

### 4. Itération Progressive
Ne pas tout réécrire d'un coup :
1. Prouver le concept (fichiers MD manuels ✅)
2. Automatiser (extraction complète)
3. Autonomiser (function calling)
4. Optimiser (MCP si nécessaire)

### 5. Documentation en Temps Réel
Mettre à jour ce document à chaque évolution majeure.

---

## 📖 Références

- **Mémoire Fondatrice** : `memoire_fondatrice.md` (identité et philosophie)
- **Guide Claude Code** : `CLAUDE.md` (instructions développement)
- **Code Principal** : `main.py`, `module2_workflow_v2.py`
- **Fichiers de Référence** : `PRET_A_ECHEANCES_REFERENCE.md`, `PRET_B_ECHEANCES_REFERENCE.md`

---

**Dernière mise à jour** : 01 novembre 2025
**Prochaine révision** : Après implémentation Function Calling (V6)
