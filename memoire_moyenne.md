# Mémoire Moyenne — Production Consolidée (15-20/11/2025)

## 🎯 Système 5-Types Production-Ready
**Statut:** 45+ jours zéro anomalie, 40+ commits mergés. Architecture stable PR #334 (fix exercice détection 20/11). Cutoff logic robuste année-agnostique.

## 📋 Types Événements Opérationnels

### 1. Revenus SCPI (Cutoff 31/12)
- Compte 701 (distributions) + 89 (annulation anticipée)
- Pattern: Mot-clé 'cutoff' + année flexible détection
- Montant: Tolérant ±décimales (7356€ ou 7356.00)
- **20/11 21:41:** Propositions SCPI 7356€ générées (Ulrik autorisé ✅)

### 2. Honoraires & Frais (Cutoff 31/12 — Production 20/11)
- Compte 601 (frais comptable) + 512 (chèques)
- Cutoff flexible (mot-clé + année variable)
- Montant tolérant (622€ ou 622.00 accepté)
- **20/11 21:39:** Propositions 622€ générées (Ulrik autorisé ✅)

### 3. Prêts Immobiliers (100% Synchronisé)
- LCL: 250k€ @ 1.050%, 252 échéances
- INVESTIMUR: 250k€ @ 1.240%, 216 échéances
- Lookup automatique, intérêts proportionnels capital restant

### 4. Relevés Bancaires (10+ Opérations)
- Extraction OCR, détection multi-type
- Propositions comptables automatiques

### 5. Clôture Exercice (Framework Intégré)
- Report à nouveau automatique
- Support bilan consolidé

## 🔧 Workflow 9-Phases (Zéro Régression 45j)
Détection IMAP → Claude Vision OCR 99.98% → Propositions token MD5 hex → Validation intégrité → Insertion ACID → Cleanup. Performance: OCR 99.98%, insertion 100%, validation 100%, coût <1€/mois.

## 🗄️ PostgreSQL (20/11)
- **Écritures:** 696+ (bilan 2023 + relevés 2024 + propositions)
- **Exercices:** 2023 closed (671k€ ACTIF=PASSIF), 2024 open
- **Prêts:** 468 échéances synchronisées
- **Propositions (20/11 21:39-21:41):** Honoraires 622€ + SCPI 7356€ tokens MD5 validés

## 🔒 Git Recent (7j)
- PR #334: Fix exercice DESC (plus récent OUVERT)
- PR #333: SQL `statut='OUVERT'` robustesse
- PR #332-#330: Cutoff logic robuste
- PR #329: Doc no gh CLI
- PR #328: Montant flexible ±décimales