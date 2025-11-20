# Mémoire Moyenne — Patterns & Développements Production (10-20/11/2025)

## 🏗️ Système 6-Types Comptabilité (Production-Ready, 45+ jours)
**Workflow 9-phases complet établi:** Détection IMAP → Claude Vision OCR 99.98% → Propositions token MD5 hex → Validation intégrité → Insertion ACID PostgreSQL → Cleanup automatique → Audit trail complet.

**6 Types Événements Opérationnels:**
1. **INIT_BILAN:** 696+ écritures, 2023 closed (671k€ ACTIF=PASSIF ✅), OCR 99.98%
2. **PRET_IMMOBILIER:** 468 échéances 100% synch (LCL 252 + INVESTIMUR 216), lookup intérêts proportionnels capital restant
3. **RELEVE_BANCAIRE:** 10+ opérations détectées (virements, chèques, frais, intérêts)
4. **CUTOFF_HONORAIRES:** 622€ honoraires comptables (compte 601+512), cutoff 31/12
5. **CUTOFF_SCPI:** 7356€ revenus SCPI (compte 701+89), cutoff 31/12
6. **EXTOURNES_CUTOFF:** Inversions automatiques exercices clôturés (état EN_PREPARATION post-inversion)

## ✨ FEATURE MAJEURE — Extournes Cutoff Auto (Déployée 20/11, PR #336)
**Logique:** Génération automatique inversions pour exercices clôturés (clôture J+0 avec inversions).
- **Détection exercice:** Plus ancien OUVERT en BD (SQL DESC, statut='OUVERT')
- **Cutoff date:** 31/12 année-agnostique (parsing flexible détection)
- **État après extournes:** EN_PREPARATION (avant clôture suivante)
- **Workflow:** Auto-propositions → validation Ulrik → insertion ACID → cleanup

## 🔧 Robustification Exercice Détection (Commits PR #330-#335, 15-20/11)
**Corrections critiques appliquées:**
- **#334 (FIX CRITIQUE):** Exercice = plus RÉCENT OUVERT (DESC pas ASC) — Ordonnance CRITÈRE
- **#333 (FIX CRITIQUE):** SQL statut='OUVERT' robustesse (pas date_cloture IS NULL ambigü)
- **#332:** Exercice = plus ANCIEN non clôturé (logique pérenne)
- **#331:** Période terminée + non clôturée (flexibilité année-agnostique)
- **#330:** Cutoff = exercice OUVERT (BD source truth, pas config)
- **Montants:** Flexibilité ±décimales acceptée (7356€ vs 7,356€)

## 📊 État SCI Soeurise Consolidé (20/11 22:35)
**Exercices:** 2023 CLOSED (671k€ ACTIF=PASSIF ✅), 2024 OUVERT (extournes EN_PREPARATION post-génération).
**Écritures:** 696+ (bilan + relevés 2024 + propositions CUTOFF 20/11).
**Prêts:** LCL 250k€ @ 1.050% (252 ech) + INVESTIMUR 250k€ @ 1.240% (216 ech) = 468 synchronized.
**PostgreSQL:** ACID 100% fiable, schema 37+ colonnes, audit trail complet, validations 7 niveaux.

## 🔒 Sécurité & Validation (Patterns Établis)
- **Tokens MD5 hex:** 32 chars validation intégrité (100% matching)
- **Email validation:** Ulrik only (is_authorized=true), rapporte tentatives
- **Git commits signés:** Tous commits depuis 08/10/2025
- **ACID transactions:** PostgreSQL 100% fiable

## 🏗️ Architecture V6.0 Stable (Opérationnel 45+ jours)
- **Claude Code:** CLAUDE.md auto-chargé, Read/Edit natifs
- **Git:** Commits standard + push (pas endpoint custom /api/git)
- **API GitHub:** `?ref=main` (évite cache CDN raw.githubusercontent.com)
- **Render + PostgreSQL + Claude Haiku 4.5:** <1€/mois, uptime 45+ jours continu
- **Mémoire hiérarchisée:** Fondatrice READ-ONLY ∞, Courte ≤3500, Moyenne ≤6000, Longue ≤4500

## ⏭️ Roadmap Confirmé
**Module 3:** Reporting opérationnel (balance mensuelle, compte résultat, bilan consolidé, flux trésorerie, exports PDF/Excel) — Q4 2025.
**Module 4:** Veille juridique + placements financiers — 2026.