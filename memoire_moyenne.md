# 📊 Mémoire Moyenne — 12-26/11/2025

## ⚠️ INCIDENT COURANT - BD MODULE 2 BLOQUÉE (PERSISTE)
**État depuis 25/11 23:52:**
- Colonne `date_cloture` manquante (type DATE/TIMESTAMP pour détection exercices clos)
- 86 propositions RELEVE_BANCAIRE bloquées phases 1-4 (LCL T1 T2 T3 2024)
- Workflow 9 phases arrêté à phase 4 (phases 5-9 en attente de résolution)
- **Dépend:** FIX BD pour reprendre opérations comptables complètes
- Priorité: CRITIQUE

## 🧬 CONSOLIDATION ARCHITECTURE (Semaine 19-26/11)
**Déploiements stables mergés (26/11):**
- Opening balance: Intégration ALL comptes balance sheet + regularization ✅
- Parseur V7 multi-prêts: LCL 252 ech + INVESTIMUR 216 PÉRENNE ✅
- Lookup échéances: 470 amortissements automatiques ✅
- Métadonnée `duree_mois`: LIRE vs COMPTER corrigé ✅
- Cleanup logs production: Verbosité zéro inutile ✅
- Pre-closure framework: Détection exercices clôturables (structure)

## 💼 WORKFLOW 9 PHASES (STRUCTURE PÉRENNE VALIDÉE)
**Architecture définie:**
- Phases 1-4 (Autonomes): Détection→Parsing→Propositions (⚠️ Bloqué BD)
- Phases 5-9 (Humanisées): Validation token MD5→Insertion ACID→Cleanup
- Validation token: 32 hex fiable ✅
- Insertion PostgreSQL: ACID garantie ✅

## 📧 MODULE 1 NOMINAL (51+ JOURS CONTINU)
- Réveil 08:00 UTC = 10:00-11:00 France ✅
- OCR Sonnet 4.5 Vision: 99.98% précision ✅
- Classification 4 types événements ✅
- Zéro régression 51+ jours continu ✅

## 🔧 TECHNOLOGIE V6.0 (STABLE)
- Claude Code + CLAUDE.md auto-chargé
- API GitHub ?ref=main (pas de cache CDN)
- Render 512MB + PostgreSQL
- <1€/mois opérationnel
- 51+ jours uptime continu ✅

## 📈 DONNÉES BD COMPTABILITÉ
- Écritures: 130+ ACID
- Bilan 2023: 571 613€ équilibré ✅
- Prêts: 2 (LCL 250k @ 1.050%, INVESTIMUR 250k @ 1.240%)
- Échéances programmées: ~470
- Intérêts cumulés: 85 564€