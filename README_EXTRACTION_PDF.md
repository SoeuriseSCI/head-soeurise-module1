# Extraction PDF - Événements Comptables

**Date**: 05/11/2025
**Version**: 1.0
**Statut**: ✅ Prêt pour test sur Render

---

## 📋 Vue d'Ensemble

Module d'extraction automatique d'événements comptables depuis des PDF de relevés bancaires.

### Workflow Complet

```
PDF → Extraction → Création Événements → Détection Types → Propositions Écritures
```

---

## 🗂️ Fichiers Créés

### 1. `extracteur_pdf.py`

**Rôle**: Extraction des opérations individuelles depuis PDF

**Utilisation**:
```python
from extracteur_pdf import ExtracteurPDF

# Avec métadonnées d'email
email_metadata = {
    'email_id': 'msg_123',
    'email_from': 'comptabilite@lcl.fr',
    'email_date': datetime.now(),
    'email_subject': 'Relevés T1-T3 2024'
}

extracteur = ExtracteurPDF('releve.pdf', email_metadata)
evenements = extracteur.extraire_evenements()

# Retourne:
# [
#   {
#     'date_operation': '2024-01-15',
#     'libelle': 'PRLV SEPA COVEA RISKS',
#     'montant': 87.57,
#     'type_operation': 'DEBIT',
#     'email_id': 'msg_123',
#     'email_from': 'comptabilite@lcl.fr',
#     ...
#   }
# ]
```

**CLI**:
```bash
python extracteur_pdf.py 'Elements Comptables des 1-2-3T2024.pdf'
```

### 2. `workflow_evenements.py`

**Rôle**: Orchestration complète du workflow

**Utilisation**:
```python
from workflow_evenements import WorkflowEvenements

workflow = WorkflowEvenements(DATABASE_URL, phase=1)

# Traiter un PDF complet
resultats = workflow.traiter_pdf(
    pdf_path='releve.pdf',
    email_metadata={...},
    auto_detect=True
)

# Résultats:
# {
#   'total_operations': 80,
#   'evenements_crees': 75,
#   'doublons_detectes': 5,
#   'erreurs': 0,
#   'types_detectes': 30,
#   'ids_crees': [1, 2, 3, ...]
# }
```

**CLI**:
```bash
# Traiter un PDF
python workflow_evenements.py 'Elements Comptables des 1-2-3T2024.pdf'

# Afficher statistiques
python workflow_evenements.py --stats

# Générer propositions
python workflow_evenements.py --propositions
```

---

## 🚀 Test sur Render

### Prérequis

1. **Migration appliquée** ✅ (fait)
2. **Base de données nettoyée** ✅ (0 événements)
3. **Variable d'environnement**: `ANTHROPIC_API_KEY` (déjà configurée sur Render)

### Étapes de Test

#### 1. Déployer le code

```bash
git add extracteur_pdf.py workflow_evenements.py README_EXTRACTION_PDF.md
git commit -m "📄 Add: PDF extraction module with complete workflow"
git push origin claude/accounting-events-setup-011CUpVyiZmLKaJZA8uJxADo
```

#### 2. Sur Render Shell

##### Test 1: Extraction seule
```bash
python extracteur_pdf.py 'Elements Comptables des 1-2-3T2024.pdf'
```

**Résultat attendu**:
- Extraction de ~80 opérations du PDF
- Création du fichier `evenements_extraits.json`
- Aucune modification en base de données

##### Test 2: Workflow complet
```bash
python workflow_evenements.py 'Elements Comptables des 1-2-3T2024.pdf'
```

**Résultat attendu**:
```
📄 ÉTAPE 1/3: EXTRACTION DU PDF
✅ 80 opérations extraites

💾 ÉTAPE 2/3: CRÉATION DES ÉVÉNEMENTS
✅ Événements créés: 75
⚠️  Doublons détectés: 5
❌ Erreurs: 0

🔍 ÉTAPE 3/3: DÉTECTION DES TYPES D'ÉVÉNEMENTS
✅ Événement #1: ASSURANCE_PRET
✅ Événement #2: FRAIS_BANCAIRES
✅ Événement #5: HONORAIRES_COMPTABLE
...
✅ Types détectés: 30/75

RÉSUMÉ:
📊 Opérations extraites: 80
✅ Événements créés: 75
🔍 Types détectés: 30
⚠️  Doublons ignorés: 5
❌ Erreurs: 0
```

##### Test 3: Vérifier les événements créés
```bash
python check_evenements.py
```

**Résultat attendu**:
- Liste complète des événements avec leurs détails
- Vérification des types détectés (ASSURANCE_PRET, FRAIS_BANCAIRES, etc.)
- Vérification des fingerprints

##### Test 4: Statistiques
```bash
python workflow_evenements.py --stats
```

**Résultat attendu**:
```
STATISTIQUES ÉVÉNEMENTS COMPTABLES

📊 Total événements: 75

Par statut:
  - EN_ATTENTE: 75

Par phase:
  - Phase 1: 30

Par type:
  - ASSURANCE_PRET: 9
  - FRAIS_BANCAIRES: 12
  - HONORAIRES_COMPTABLE: 3
```

##### Test 5: Générer propositions
```bash
python workflow_evenements.py --propositions
```

**Résultat attendu**:
- Propositions d'écritures pour les 30 événements détectés
- Détail des comptes débités/crédités
- Montants et libellés

---

## 🔍 Événements Attendus du PDF

D'après l'analyse du PDF "Elements Comptables des 1-2-3T2024.pdf" (40 pages, Jan-Sep 2024):

### Détectables par Phase 1 (~30 événements)

#### 1. Assurance Prêt (9 événements)
- **Pattern**: PRLV SEPA CACI NON LIFE LIMITED / COVEA
- **Montant**: ~87,57€
- **Fréquence**: Mensuel (15 du mois)

#### 2. Frais Bancaires (12+ événements)
- **Pattern**: ABON LCL ACCESS, FRAIS TENUE DE COMPTE, COTISATION CARTE
- **Montant**: Varie (3-15€)
- **Fréquence**: Mensuel/Trimestriel

#### 3. Honoraires Comptable (3 événements)
- **Pattern**: PRLV SEPA CRP Comptabilit Conseil
- **Montants**: 213,60€ (Jan), 564,00€ (Avr), 213,60€ (Juil)
- **Fréquence**: Trimestriel

### Non-détectables Phase 1 (~45 événements)

- **Remboursements prêt**: 9 échéances (nécessite table `echeances_prets` - Phase 2)
- **Distributions SCPI**: 3 distributions (calcul revenus/capital - Phase 3)
- **Achats ETF**: 8 achats (mise à jour portefeuille - Phase 3)
- **Apports associé**: Varie (identification Ulrik Bergsten - Phase 2)

---

## 🧪 Validation

### Critères de Succès

✅ **Extraction**:
- [ ] 80+ opérations extraites du PDF
- [ ] Dates normalisées en format YYYY-MM-DD
- [ ] Montants correctement parsés (format français → décimal)
- [ ] Types DEBIT/CREDIT correctement identifiés

✅ **Création**:
- [ ] 75+ événements créés en base
- [ ] Fingerprints calculés et uniques
- [ ] Libellés normalisés
- [ ] Métadonnées email attachées

✅ **Détection**:
- [ ] 9 assurances prêt détectées
- [ ] 12+ frais bancaires détectés
- [ ] 3 honoraires comptable détectés
- [ ] Phase de traitement = 1

✅ **Doublons**:
- [ ] Si on re-lance le workflow, 0 nouveaux événements créés
- [ ] Message "Doublon détecté" pour chaque opération

---

## 🛠️ Dépannage

### Erreur: "ANTHROPIC_API_KEY non définie"

**Solution**: Vérifier la variable d'environnement sur Render
```bash
echo $ANTHROPIC_API_KEY | cut -c1-10
```

### Erreur: "PDF non trouvé"

**Solution**: Le PDF doit être dans le répertoire courant
```bash
ls -l "Elements Comptables des 1-2-3T2024.pdf"
```

### Pas d'événements créés

**Cause possible**: Tous détectés comme doublons
**Solution**: Vérifier avec `check_evenements.py` et nettoyer si nécessaire

### Types non détectés

**Cause**: Patterns Phase 1 limités
**Normal**: ~30/80 événements détectés en Phase 1
**Solution**: Phases 2 et 3 pour le reste

---

## 📊 Intégration Module 2

Une fois les événements créés et détectés, ils peuvent être intégrés au workflow comptable:

```python
from module2_workflow_v2 import generer_propositions_evenements

# Récupérer les événements validés
evenements_valides = [...]

# Générer les écritures comptables
for evt in evenements_valides:
    proposition = generer_proposition(evt)
    if valider_proposition(proposition):
        creer_ecriture_comptable(proposition)
```

---

## 🔗 Documentation Connexe

- `PHASE1_EVENEMENTS_COMPTABLES.md`: Documentation complète Phase 1
- `gestionnaire_evenements.py`: API du gestionnaire d'événements
- `detecteurs_evenements.py`: Détecteurs Phase 1 (patterns)
- `detection_doublons.py`: Système de fingerprinting
- `check_evenements.py`: Script de vérification

---

**Auteur**: Claude Code Assistant
**Prêt pour déploiement**: ✅ OUI
**Prochaine étape**: Test sur Render avec PDF réel
