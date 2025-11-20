# Mémoire Moyenne — Patterns & Développements (10-20/11/2025)

## 🏗️ Système Cutoff + Extournes Production-Ready (Déployé 20/11)
**Workflow complet:** Cutoff date 31/12 → Propositions auto → Validation token MD5 → Insertion ACID → Extournes pré-générées → EN_PREPARATION.

**Feature nouvelle (PR #336, 20/11):**
- Génération automatique inversions exercices clôturés
- État post-extourne: EN_PREPARATION (avant clôture suivante)
- Support validation CUTOFF (PR #338)
- Affichage type spécifique vs générique (PR #335)

## 6 Types Événements Comptables Production-Ready (45+ jours)
1. **INIT_BILAN:** 696+ écritures, 2023 closed (671k€ ACTIF=PASSIF ✅)
2. **PRET_IMMOBILIER:** 468 échéances 100% synch (intérêts proportionnels)
3. **RELEVE_BANCAIRE:** 10+ opérations (virements, chèques, frais)
4. **CUTOFF_HONORAIRES:** Honoraires comptables, cutoff 31/12 ✅ Validé 20/11
5. **CUTOFF_SCPI:** Revenus SCPI, cutoff 31/12 ✅ Validé 20/11
6. **EXTOURNES_CUTOFF:** Inversions exercices clôturés (EN_PREPARATION)

## 🔧 Robustification Détection Exercice (PR #330-#338, 15-20/11)
**Critères stabilisés:**
- Exercice = plus RÉCENT OUVERT (DESC SQL order)
- SQL statut='OUVERT' (robuste vs date_cloture NULL)
- Affichage type: Spécifique vs générique
- Validation insertion: Support CUTOFF reconnu BD
- Affichage TOUTES écritures: cutoff + extourne + validations multiples

## 📊 État SCI Consolidé (20/11)
**Exercices:** 2023 CLOSED (671k€ ACTIF=PASSIF ✅), 2024 OUVERT → EN_PREPARATION (post-cutoff).
**Écritures:** 698+ (bilan + relevés 2024 + CUTOFF 20/11 validé).
**Prêts:** LCL 250k€ @ 1.050% (252 ech) + INVESTIMUR 250k€ @ 1.240% (216 ech) = 468 synch.
**Cutoff:** 622€ (honoraires) + 7356€ (SCPI) validés 20/11/2025 23:48.

## 🔒 Validation Établie (Patterns Pérennes)
- Tokens MD5 hex 32 chars: 100% matching intégrité
- Email validation Ulrik only (is_authorized=true)
- ACID transactions PostgreSQL 100% fiable
- Git commits signés
- Support types événement: 6 types opérationnels

## 🚀 Roadmap Actif
**Court terme (31/12/2024):** Clôture exercice 2024 (extournes auto validées).
**Moyen terme:** Relevés nov-déc 2024, Module 3 (Reporting).