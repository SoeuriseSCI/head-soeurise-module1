# Analyse de l'Injection d'Événements Comptables

**Date**: 12/11/2025
**Auteur**: Claude Code (analyse approfondie)
**Contexte**: Audit du système d'injection des événements comptables dans le projet _Head.Soeurise

---

## 📋 Résumé Exécutif

Cette analyse révèle **5 problèmes critiques** dans le système d'injection des événements comptables, avec des incohérences entre le code, le schéma de base de données, et la philosophie documentée dans `CLAUDE.md`.

### Problèmes Majeurs Identifiés

1. ❌ **Incohérence ORM vs Schéma SQL** - Le modèle Python ne reflète pas la structure réelle de la table
2. ❌ **Contrainte UNIQUE sur fingerprint contradictoire** - L'index bloque alors que le code accepte les doublons
3. ❌ **Contrainte UNIQUE sur email_id problématique** - Empêche plusieurs événements par email
4. ❌ **Concept de "doublon" mal défini** - Confusion entre doublons réels et sources complémentaires
5. ❌ **Garbage Collection incompatible avec stratégie actuelle** - Conflit entre suppression temporelle et contraintes

---

## 🔍 Analyse Détaillée

### 1. Incohérence ORM vs Schéma SQL

#### État Actuel

**Schéma SQL** (via `migration_evenements_comptables.py:64-72`):
```sql
ALTER TABLE evenements_comptables ADD COLUMN date_operation DATE;
ALTER TABLE evenements_comptables ADD COLUMN libelle VARCHAR(500);
ALTER TABLE evenements_comptables ADD COLUMN libelle_normalise VARCHAR(500);
ALTER TABLE evenements_comptables ADD COLUMN montant NUMERIC(15, 2);
ALTER TABLE evenements_comptables ADD COLUMN type_operation VARCHAR(20);
ALTER TABLE evenements_comptables ADD COLUMN fingerprint VARCHAR(64);
ALTER TABLE evenements_comptables ADD COLUMN phase_traitement INTEGER;
```

**Modèle ORM** (`models_module2.py:206-234`):
```python
class EvenementComptable(Base):
    __tablename__ = 'evenements_comptables'

    id = Column(Integer, primary_key=True)

    # Source email
    email_id = Column(String(255), unique=True)
    email_from = Column(String(255), nullable=False)
    email_date = Column(DateTime, nullable=False)
    email_subject = Column(String(255))
    email_body = Column(Text, nullable=False)

    # Classification
    type_evenement = Column(String(100))
    est_comptable = Column(Boolean)

    # Traitement
    statut = Column(String(50), default='EN_ATTENTE')
    message_erreur = Column(Text)
    ecritures_creees = Column(ARRAY(Integer))

    created_at = Column(DateTime, default=datetime.utcnow)
    traite_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**❌ PROBLÈME**: Le modèle ORM ne contient **AUCUNE** des 7 colonnes ajoutées par la migration!

#### Impact

- **Code utilisant l'ORM**: Ne peut pas accéder aux colonnes critiques (`date_operation`, `montant`, `fingerprint`, etc.)
- **Code utilisant SQL direct**: Fonctionne (comme `gestionnaire_evenements.py`)
- **Risque de régression**: Toute utilisation de l'ORM créera des événements incomplets
- **Confusion développeurs**: Deux sources de vérité contradictoires

#### Solution Requise

Mettre à jour `models_module2.py` pour refléter le schéma SQL réel:

```python
class EvenementComptable(Base):
    __tablename__ = 'evenements_comptables'

    id = Column(Integer, primary_key=True)

    # NOUVELLES COLONNES (de la migration)
    date_operation = Column(Date)
    libelle = Column(String(500))
    libelle_normalise = Column(String(500))
    montant = Column(Numeric(15, 2))
    type_operation = Column(String(20))  # DEBIT ou CREDIT
    fingerprint = Column(String(64), unique=True, index=True)
    phase_traitement = Column(Integer)

    # Source email
    email_id = Column(String(255), unique=True)  # ⚠️ VOIR PROBLÈME #3
    email_from = Column(String(255), nullable=False)
    email_date = Column(DateTime, nullable=False)
    email_subject = Column(String(255))
    email_body = Column(Text, nullable=False)

    # Classification
    type_evenement = Column(String(100))
    est_comptable = Column(Boolean)

    # Traitement
    statut = Column(String(50), default='EN_ATTENTE')
    message_erreur = Column(Text)
    ecritures_creees = Column(ARRAY(Integer))

    created_at = Column(DateTime, default=datetime.utcnow)
    traite_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

---

### 2. Contrainte UNIQUE sur fingerprint Contradictoire

#### Code Actuel

**Migration** (`migration_evenements_comptables.py:86-89`):
```python
conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_fingerprint_unique ON evenements_comptables(fingerprint)"))
```

**Détecteur de doublons** (`detection_doublons.py:192-237`):
```python
@staticmethod
def verifier_doublon(session, evenement: Dict) -> Optional[Dict]:
    """
    STRATÉGIE (MAJ 11/11/2025):
    Si doublon détecté → ACCEPTER le nouvel événement (le plus récent)
    Les anciens événements seront supprimés par le garbage collection (> 7 jours)

    Returns:
        None (toujours accepter, même si doublon détecté)
    """
    # ... code de recherche ...

    # Même si doublon trouvé, on retourne None (accepter le nouvel événement)
    return None
```

**❌ PROBLÈME**: Contradiction totale!

- Le code **accepte** tous les événements (retourne toujours `None`)
- L'index UNIQUE **bloque** les doublons au niveau base de données
- Résultat: **Erreur PostgreSQL** si on tente d'insérer un événement avec fingerprint existant

#### Trace d'Erreur Attendue

```
psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint "idx_fingerprint_unique"
DETAIL: Key (fingerprint)=(a3f5e9c2d1b4...) already exists.
```

#### Historique du Problème

D'après le commentaire dans `detection_doublons.py:196-203`:

> **STRATÉGIE (MAJ 11/11/2025)**:
> Si doublon détecté → ACCEPTER le nouvel événement (le plus récent)
> Les anciens événements seront supprimés par le garbage collection (> 7 jours)

Cette stratégie a été changée le 11/11/2025, mais l'index UNIQUE n'a **pas été supprimé**.

#### Solution Requise

**Option A** : Supprimer l'index UNIQUE (préféré selon la stratégie actuelle)

```sql
DROP INDEX IF EXISTS idx_fingerprint_unique;
CREATE INDEX IF NOT EXISTS idx_fingerprint_lookup ON evenements_comptables(fingerprint);
```

**Option B** : Restaurer la détection de doublons (abandonner stratégie 11/11)

```python
def verifier_doublon(session, evenement: Dict) -> Optional[Dict]:
    fingerprint = DetecteurDoublons.calculer_fingerprint(evenement)

    result = session.execute(
        text("SELECT id, created_at FROM evenements_comptables WHERE fingerprint = :fingerprint"),
        {'fingerprint': fingerprint}
    )
    row = result.fetchone()

    if row:
        return {
            'evenement_id': row[0],
            'created_at': row[1],
            'fingerprint': fingerprint
        }

    return None
```

**Recommandation**: **Option A** - Supprimer UNIQUE, garder index de lookup

---

### 3. Contrainte UNIQUE sur email_id Problématique

#### Code Actuel

**Modèle ORM** (`models_module2.py:212`):
```python
email_id = Column(String(255), unique=True)
```

#### Problème Conceptuel

Un email peut contenir **plusieurs opérations comptables**:

**Exemple**: Email "Relevé bancaire LCL - Septembre 2024"
- Contient un PDF avec **50+ opérations**
- Chaque opération → 1 événement comptable
- Avec `email_id UNIQUE`: **Impossible d'en créer plus d'un!**

#### Ce que dit CLAUDE.md (lignes 149-179)

```markdown
### Nature des Événements Comptables et "Pseudo-Doublons"

**DEUX sources d'information COMPLÉMENTAIRES (PAS des doublons !) :**

**1. Relevés de compte bancaire**
- Synthèse courte : date, libellé court, montant
- Vision chronologique des mouvements
- **Insuffisants seuls** pour tenir la comptabilité

**2. Documents justificatifs** (essentiels pour ventilation)
- Avis d'opération
- Factures
- Bulletins de versements de revenus
- Avis d'opération sur valeurs mobilières
- Avis d'opération crédits reçus (apports compte courant associé)
- Tableaux d'amortissement des prêts

**RÈGLE FONDAMENTALE :**
> Un même événement économique = 1 ligne sur relevé de compte + 1 document justificatif
>
> **Ce ne sont PAS des doublons** → Ce sont des informations **COMPLÉMENTAIRES**
```

#### Impact

1. **Avec email_id UNIQUE**:
   - 1 email PDF relevé → 1 seul événement créé
   - Les 49 autres opérations → **rejetées silencieusement**
   - Données comptables **incomplètes**

2. **Workflow actuel** (`workflow_evenements.py:165`):
   ```python
   stats_creation = self.gestionnaire.creer_evenements_batch(operations)
   ```
   - Appelle `creer_evenement()` pour chaque opération
   - Avec `email_id` identique
   - Seul le 1er passe, les autres échouent avec erreur UNIQUE violation

#### Solution Requise

**Supprimer la contrainte UNIQUE** sur `email_id`:

```python
# models_module2.py
email_id = Column(String(255))  # RETIRER unique=True
```

```sql
-- Migration SQL
ALTER TABLE evenements_comptables DROP CONSTRAINT IF EXISTS evenements_comptables_email_id_key;
```

**Justification**: Un email peut contenir multiple événements comptables (relevé bancaire).

---

### 4. Concept de "Doublon" Mal Défini

#### Deux Types de "Doublons" Confondus

**Type A: Vrais doublons (à éviter)**
- Même événement économique extrait 2 fois
- Exemple: Opération du 15/01/2024 pour 87,57€ (assurance prêt) extraite en double depuis le même PDF
- **Identification**: Même fingerprint (`MD5(date + libelle_norm + montant + type)`)
- **Action**: Ignorer la 2e occurrence

**Type B: Sources complémentaires (à conserver!)**
- Même événement économique, mais 2 sources d'information
- Exemple:
  - Source 1 (relevé): "15/01/2024 - PRLV SEPA COVEA - 87,57€"
  - Source 2 (justificatif): "Assurance prêt immobilier BRM0911AH - Échéance 01/2024 - Prime: 87,57€"
- **Identification**: Fingerprints **différents** (libellés différents)
- **Action**: **Conserver les deux** pour analyse croisée

#### Problème Actuel

Le système ne fait **aucune distinction** entre Type A et Type B:

**Gestion actuelle** (`detection_doublons.py:192-237`):
- Détecte seulement Type A (fingerprint identique)
- Type B non géré → **traités comme événements distincts** ✅ (correct par accident)

**Mais**: Aucune logique pour **lier** les sources complémentaires Type B.

#### Ce que Claude fait en amont

D'après `detection_doublons.py:206-208`:

```python
NOTE:
La déduplication intelligente (doublons avec libellés différents) est
maintenant gérée par Claude dans extracteur_pdf._deduplicater_operations()
AVANT la création des événements en base.
```

**Problème**: Cette fonction `_deduplicater_operations()` traite probablement Type B comme des doublons à éliminer, alors qu'ils devraient être **liés** mais **conservés**.

#### Solution Recommandée

**Introduire un concept de "groupe d'événements"**:

```sql
-- Nouvelle table de liaison
CREATE TABLE groupes_evenements (
    id SERIAL PRIMARY KEY,
    type_groupe VARCHAR(50) NOT NULL,  -- 'RELEVE_ET_JUSTIFICATIF', 'MULTIPAIEMENT', etc.
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Lien événement → groupe
ALTER TABLE evenements_comptables ADD COLUMN groupe_id INTEGER REFERENCES groupes_evenements(id);
```

**Workflow modifié**:
1. Extraire tous les événements (relevé + justificatifs)
2. Identifier Type A (vrais doublons) → **éliminer**
3. Identifier Type B (sources complémentaires) → **grouper**
4. Créer événements distincts liés au même groupe
5. Lors de la comptabilisation, utiliser la source la plus détaillée

---

### 5. Garbage Collection Incompatible

#### Code Actuel

**Garbage Collection** (`main.py:748-797`):
```python
def garbage_collection():
    """
    Supprime les scories > 7 jours (nettoyage automatique)

    RÈGLES:
    - Propositions : Supprimer tout sauf VALIDEE (garde audit trail)
    - Événements : Supprimer TOUS > 7 jours (données temporaires)

    Exécuté quotidiennement à 08:00 UTC avant le traitement des emails
    """
    # ÉVÉNEMENTS : Supprimer TOUS > 7 jours
    result_evt = session.execute(text("""
        DELETE FROM evenements_comptables
        WHERE created_at < NOW() - INTERVAL '7 days'
    """))
```

**Stratégie de doublons** (`detection_doublons.py:196-203`):
```python
STRATÉGIE (MAJ 11/11/2025):
Si doublon détecté → ACCEPTER le nouvel événement (le plus récent)
Les anciens événements seront supprimés par le garbage collection (> 7 jours)
```

#### ❌ PROBLÈME: Contradiction avec Index UNIQUE

**Scénario problématique**:

1. **Jour 1** (01/11): Événement créé, fingerprint `ABC123`
2. **Jour 2-7**: Événement reste en base
3. **Jour 8** (08/11): Garbage collection **supprime** l'événement
4. **Jour 9** (09/11): Nouvel email avec la même opération
   - Calcul fingerprint: `ABC123` (identique)
   - Tentative insertion avec `fingerprint = 'ABC123'`
   - **❌ ERREUR**: Index UNIQUE bloque (l'ancien existe encore en cache PostgreSQL)

**Ou pire**:

1. **Jour 1**: Événement créé, fingerprint `ABC123`, statut `EN_ATTENTE`
2. **Jour 5**: Retraitement nécessaire (échec précédent)
   - Tentative création événement avec fingerprint `ABC123`
   - **❌ ERREUR**: Index UNIQUE bloque (l'ancien existe encore, < 7 jours)

#### Leçon Apprise (CLAUDE.md:170-179)

```markdown
**Leçon apprise (11/11/2025)** :
- ❌ ERREUR : Bloquer immédiatement les doublons → Empêche retraitement après échec
- ✅ CORRECT : Accepter les nouveaux événements, laisser garbage collection nettoyer les anciens
- 📖 RÈGLE : Fenêtre de debug de 7 jours, puis nettoyage automatique
```

#### Solutions Possibles

**Option 1**: Supprimer l'index UNIQUE (préféré)
```sql
DROP INDEX IF EXISTS idx_fingerprint_unique;
CREATE INDEX IF NOT EXISTS idx_fingerprint_lookup ON evenements_comptables(fingerprint);
```

**Option 2**: Modifier le GC pour nettoyer seulement les événements VALIDÉS
```python
DELETE FROM evenements_comptables
WHERE created_at < NOW() - INTERVAL '7 days'
  AND statut = 'VALIDE'
```

**Option 3**: Utiliser le fingerprint comme mécanisme de déduplication logique (sans UNIQUE)
```python
def verifier_doublon(session, evenement: Dict) -> Optional[Dict]:
    fingerprint = DetecteurDoublons.calculer_fingerprint(evenement)

    # Chercher un événement récent (< 7 jours) avec ce fingerprint
    result = session.execute(text("""
        SELECT id, created_at
        FROM evenements_comptables
        WHERE fingerprint = :fingerprint
          AND created_at >= NOW() - INTERVAL '7 days'
        ORDER BY created_at DESC
        LIMIT 1
    """), {'fingerprint': fingerprint})

    row = result.fetchone()

    if row:
        return {'evenement_id': row[0], 'created_at': row[1]}

    return None  # Ancien événement nettoyé par GC, accepter le nouveau
```

**Recommandation**: **Option 1** (supprimer UNIQUE) + **Option 3** (déduplication logique temporelle)

---

## 🎯 Plan d'Action Recommandé

### Priorité 1 (Critique - Bloquant)

1. **Supprimer contrainte UNIQUE sur fingerprint**
   ```sql
   DROP INDEX IF EXISTS idx_fingerprint_unique;
   CREATE INDEX IF NOT EXISTS idx_fingerprint_lookup ON evenements_comptables(fingerprint);
   ```

2. **Supprimer contrainte UNIQUE sur email_id**
   ```sql
   ALTER TABLE evenements_comptables DROP CONSTRAINT IF EXISTS evenements_comptables_email_id_key;
   ```

3. **Mettre à jour le modèle ORM** (`models_module2.py`)
   - Ajouter les 7 colonnes manquantes
   - Retirer `unique=True` sur `email_id`

### Priorité 2 (Important - Cohérence)

4. **Implémenter déduplication logique temporelle**
   - Modifier `detection_doublons.verifier_doublon()` pour chercher uniquement < 7 jours
   - Documenter la logique

5. **Tester le workflow complet**
   - Créer test avec relevé bancaire (50+ opérations)
   - Vérifier qu'aucune erreur UNIQUE violation
   - Vérifier que tous les événements sont créés

### Priorité 3 (Amélioration - Long terme)

6. **Introduire concept de groupes d'événements**
   - Créer table `groupes_evenements`
   - Ajouter colonne `groupe_id` à `evenements_comptables`
   - Implémenter logique de groupage pour sources complémentaires

7. **Améliorer extracteur PDF**
   - Distinguer Type A (vrais doublons) vs Type B (sources complémentaires)
   - Grouper Type B au lieu de les éliminer

---

## 📝 Code de Migration Proposé

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIGRATION - FIX Contraintes Événements Comptables
==================================================
Corrige les incohérences identifiées dans l'analyse du 12/11/2025

Date: 12/11/2025
Auteur: Claude Code
"""

import os
import sys
from sqlalchemy import text, create_engine

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("❌ ERREUR: Variable d'environnement DATABASE_URL non définie")
    sys.exit(1)

if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

def migrate_fix_contraintes():
    """
    Applique les corrections aux contraintes
    """
    print("🔧 DÉBUT DE LA MIGRATION - FIX CONTRAINTES")
    print()

    engine = create_engine(DATABASE_URL, echo=False)

    with engine.connect() as conn:
        print("📝 ÉTAPE 1: Suppression contrainte UNIQUE sur fingerprint")
        try:
            conn.execute(text("DROP INDEX IF EXISTS idx_fingerprint_unique"))
            conn.commit()
            print("  ✅ Index UNIQUE sur fingerprint supprimé")
        except Exception as e:
            print(f"  ⚠️  Erreur: {e}")

        print()
        print("📝 ÉTAPE 2: Création index lookup sur fingerprint")
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_fingerprint_lookup ON evenements_comptables(fingerprint)"))
            conn.commit()
            print("  ✅ Index lookup sur fingerprint créé")
        except Exception as e:
            print(f"  ⚠️  Erreur: {e}")

        print()
        print("📝 ÉTAPE 3: Suppression contrainte UNIQUE sur email_id")
        try:
            conn.execute(text("ALTER TABLE evenements_comptables DROP CONSTRAINT IF EXISTS evenements_comptables_email_id_key"))
            conn.commit()
            print("  ✅ Contrainte UNIQUE sur email_id supprimée")
        except Exception as e:
            print(f"  ⚠️  Erreur: {e}")

        print()
        print("📝 ÉTAPE 4: Création index lookup sur email_id")
        try:
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_email_id_lookup ON evenements_comptables(email_id)"))
            conn.commit()
            print("  ✅ Index lookup sur email_id créé")
        except Exception as e:
            print(f"  ⚠️  Erreur: {e}")

    print()
    print("✅ MIGRATION TERMINÉE")
    print()
    print("⚠️  N'OUBLIEZ PAS de mettre à jour models_module2.py:")
    print("   - Ajouter les 7 colonnes manquantes")
    print("   - Retirer unique=True sur email_id")

if __name__ == '__main__':
    migrate_fix_contraintes()
```

---

## 📚 Références

- `CLAUDE.md`: Documentation du projet (philosophie, leçons apprises)
- `PHASE1_EVENEMENTS_COMPTABLES.md`: Spécifications Phase 1
- `migration_evenements_comptables.py`: Migration SQL initiale
- `models_module2.py`: Modèles ORM
- `detection_doublons.py`: Logique de détection de doublons
- `gestionnaire_evenements.py`: Gestionnaire central
- `workflow_evenements.py`: Orchestrateur workflow
- `module2_integration_v2.py`: Point d'entrée intégration

---

**Fin de l'analyse - 12/11/2025**
