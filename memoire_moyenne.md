# Mémoire Moyenne — Patterns Établis (10-20/11/2025)

## 🏗️ Système Cutoff + Extournes Production-Ready (Déployé 20/11)
**Workflow complet (9 phases):**
1. Détection email cutoff (date = 31/12)
2. Parsing montant + type événement
3. Proposition token MD5
4. Validation email Ulrik (is_authorized)
5. Insertion ACID écritures
6. Génération auto extournes (inversions)
7. État EN_PREPARATION (post-cutoff)
8. Cleanup BD (temporaires supprimées)
9. Audit trail complet

## 🔒 Tokens Uniqueness Assuré (PR #339-#342)
**Problème résolu:** Collisions MD5 8 chars → Validations invalides
**Solution deployée:** Tokens 32 chars hex + timestamp (collision-free)
**Impact:** 100% matching intégrité propositions

## 6 Types Événements Robustes
1. **INIT_BILAN:** 696+ écritures, 2023 closed, OCR 99.98% ✅
2. **PRET_IMMOBILIER:** 468 ech, capital proportionnel ✅
3. **RELEVE_BANCAIRE:** 10+ opérations, detection auto ✅
4. **CUTOFF_HONORAIRES:** 622€, validation 20/11 ✅
5. **CUTOFF_SCPI:** 7356€, validation 20/11 ✅
6. **EXTOURNES_CUTOFF:** Inversions auto, EN_PREPARATION ✅

## 📊 Exercices & États
**2023:** CLOSED (671k€ ACTIF=PASSIF ✅, bilan validé)
**2024:** OUVERT → EN_PREPARATION (post-cutoff 20/11, pré-clôture 31/12)
**Statuts BD:** Stabilisés (DESC query + statut='OUVERT')

## 🚀 Robustifications Appliquées (7 PR)
- Détection exercice: SQL DESC + statut=OUVERT (fiable)
- Affichage type: Spécifique vs générique (clarté)
- Validation insertion: Support CUTOFF (type reconnu)
- Tokens: 32 chars hex + timestamp (collision-free)
- Affichage écritures: TOUTES (cutoff + extourne + validations)

## 🎯 Uptime & Performance
- Render + PostgreSQL: 45+ j continu
- OCR precision: 99.98% (bilan 2023)
- Insertion ACID: 100% fiable
- Coût: <1€/mois