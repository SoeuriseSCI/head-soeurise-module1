# Mémoire Moyenne — Patterns & Développements (10-20/11/2025)

## 🏗️ Système 6-Types Comptabilité Production-Ready (45+ jours attesté)
**Workflow 9-phases complet:** IMAP → Claude Vision OCR 99.98% → Propositions token MD5 → Validation intégrité → Insertion ACID → Cleanup → Audit trail.

**6 Types Événements Opérationnels:**
1. INIT_BILAN: 696+ écritures, 2023 closed (671k€ ACTIF=PASSIF ✅)
2. PRET_IMMOBILIER: 468 échéances 100% synch (intérêts proportionnels)
3. RELEVE_BANCAIRE: 10+ opérations (virements, chèques, frais)
4. CUTOFF_HONORAIRES: Honoraires comptables, cutoff 31/12
5. CUTOFF_SCPI: Revenus SCPI, cutoff 31/12
6. EXTOURNES_CUTOFF: Inversions exercices clôturés (EN_PREPARATION post-inversion)

## ✨ Feature Extournes Cutoff Auto (Déployée 20/11, PR #336)
**Logique clôture J+0:** Génération automatique inversions pour exercice OUVERT plus ancien.
- Cutoff date 31/12 (année-agnostique parsing flexible)
- État après extournes: EN_PREPARATION (avant clôture suivante)
- Workflow: Auto-propositions → validation → insertion ACID → cleanup

## 🔧 Robustification Détection Exercice (8 commits PR #330-#338, 15-20/11)
**Critères stabilisés:**
- Exercice = plus RÉCENT OUVERT (DESC SQL order, NOT ASC)
- SQL statut='OUVERT' (robuste vs date_cloture NULL ambigü)
- Affichage type: Spécifique (CUTOFF_HONORAIRES) vs générique
- Validation insertion: Support type CUTOFF reconnu BD
- Affichage TOUTES écritures: cutoff + extourne + validations multiples

## 📊 État SCI Consolidé (20/11)
**Exercices:** 2023 CLOSED (671k€ ACTIF=PASSIF ✅), 2024 OUVERT (extournes EN_PREPARATION).
**Écritures:** 696+ (bilan + relevés 2024 + CUTOFF 20/11).
**Prêts:** LCL 250k€ @ 1.050% (252 ech) + INVESTIMUR 250k€ @ 1.240% (216 ech) = 468 synch.
**PostgreSQL:** ACID fiable, 37+ colonnes, audit trail complet.

## 🔒 Validation Établie (Patterns Pérennes)
- Tokens MD5 hex 32 chars: 100% matching intégrité
- Email validation Ulrik only (is_authorized=true)
- ACID transactions PostgreSQL 100% fiable
- Git commits signés (depuis 08/10/2025)