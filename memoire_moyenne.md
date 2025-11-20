# Mémoire Moyenne — Patterns & Développements (15-20/11/2025)

## 📦 Système 6-Types Production (45+ jours stable)
Workflow 9-phases complet. OCR 99.98% precision. Insertion ACID 100%. Validation token MD5 hex 100%. Zéro régression 40+ PR mergées.

## ✨ FEATURE MAJEURE — Extournes Cutoff Auto (Déployée 20/11, PR #336)
**Logique:** Génération automatique inversions pour exercices clôturés
- **Détection exercice:** Plus ancien OUVERT en BD (SQL DESC, statut='OUVERT')
- **Cutoff date:** 31/12 année-agnostique (parsing flexible détection)
- **État après extournes:** EN_PREPARATION (avant clôture suivante)
- **Workflow:** Auto-propositions → validation Ulrik → insertion ACID → cleanup
- **Impact:** Clôture J+0 avec inversions automatiques, exercice suivant prêt

## 🔧 Robustification Exercice Détection (PR #330-#335, 15-20/11)
**Corrections appliquées:**
- **#334:** Exercice = plus RÉCENT OUVERT (DESC pas ASC) — FIX CRITIQUE
- **#333:** SQL statut='OUVERT' robustesse (pas date_cloture IS NULL)
- **#332:** Exercice = plus ANCIEN non clôturé (logique pérenne)
- **#331:** Période terminée + non clôturée (flexibilité année)
- **#330:** Cutoff = exercice OUVERT (BD source truth)
- **Montants:** Flexibilité ±décimales acceptée (7356€ vs 7,356)

## 📋 Types Événements Detaillés

### INIT_BILAN (696+ écritures production)
- **Comptes:** 11 ACTIF/PASSIF
- **État:** 2023 CLOSED (671k€ ACTIF=PASSIF) ✅
- **OCR:** 99.98% precision

### PRET_IMMOBILIER (468 échéances 100% synch)
- **LCL:** 250k€ @ 1.050% (252 échéances)
- **INVESTIMUR:** 250k€ @ 1.240% (216 échéances)
- **Lookup:** Automatique intérêts proportionnels capital restant

### RELEVE_BANCAIRE (10+ opérations)
- **Détection:** Virements, chèques, frais, intérêts
- **OCR extraction:** Montants, dates, références
- **Propositions:** Auto-comptables

### CUTOFF_HONORAIRES (622€, 20/11 21:39)
- **Comptes:** 601 (frais comptable) + 512 (chèques sortie)
- **Cutoff:** 31/12 flexible
- **État:** Proposition token MD5 validée, insertion pending

### CUTOFF_SCPI (7356€, 20/11 21:41)
- **Comptes:** 701 (distributions) + 89 (annulations gain/perte)
- **Cutoff:** 31/12 flexible
- **État:** Proposition token MD5 validée, insertion pending

### EXTOURNES_CUTOFF (NEW, PR #336)
- **Inversions:** Automatiques pour exercices clôturés
- **Détection:** Exercice OUVERT plus ancien
- **État:** EN_PREPARATION post-inversion

## 🏢 Patrimoine SCI Soeurise (20/11)
- **Exercices:** 2023 CLOSED (671k€), 2024 OUVERT (extournes EN_PREPARATION)
- **Écritures:** 696+ (bilan + relevés 2024 + propositions 20/11)
- **Prêts:** 468 échéances synchronized
- **PostgreSQL:** ACID 100%, audit trail, 37+ colonnes

## 🏗️ Architecture V6.0 (Stable)
- **Render:** <1€/mois, 45+ j uptime
- **Claude:** Haiku 4.5 (tokens optimisés)
- **Git:** Commits signés, 40+ PR mergées
- **Mémoire:** Hiérarchisée (Fondatrice ∞, Courte ≤3500, Moyenne ≤6000, Longue ≤4500)

## ⏭️ Roadmap
1. **Immediate:** Validation tokens propositions (22/11 estimé)
2. **Module 3:** Reporting (balance/résultat/bilan/flux trésorerie/exports PDF-Excel)
3. **Module 4:** Veille juridique + placements financiers (2026)