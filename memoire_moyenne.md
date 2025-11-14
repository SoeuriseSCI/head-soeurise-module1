# Module 2 Comptabilité V8.0 - Avancées Novembre 2025

## Workflow 9-Phases Production (Depuis 26/10/2025)
**Phases 1-4:** Automation IMAP → Extraction OCR → Génération propositions Markdown ✅
**Phase 5:** Multi-validations `[_Head] VALIDE: <TOKEN>` depuis 14/11 ✅
**Phases 6-9:** Insertion ACID + cleanup propositions (22+ en attente)

## Correction Majeure Compte 161
**Problème:** Remboursements capital utilisaient compte 164 (deprecated)
**Solution:** Compte 161 (Emprunts) pour ventilation correcte capital/intérêts
**Impact:** Tous prêts (LCL + INVESTIMUR) correctement catégorisés, bilan 2024 synchronisé

## Données Comptabilité Établies
- **696+ écritures ACID:** Cohérence 100% confirmée (bilan 2024 = bilan 2023 structure)
- **Revenus net patrimoine:** +1.253k€/mois
  - SCPI Épargne Pierre: +2.8k€/trimestre (distribution automatique)
  - Service prêts: -1.425k€/mois (capital + intérêts LCL+INVESTIMUR)
- **Prêts immobiliers:** 468 échéances automatisées
  - LCL: 250k€ @ 1.050% (~250 échéances)
  - INVESTIMUR: 250k€ @ 1.240% (~218 échéances)

## Événements Supportés
**Opérationnel:**
- INIT_BILAN_2023 ✅ (11 comptes ACTIF/PASSIF)
- PRET_IMMOBILIER ✅ (468 échéances)
- RELEVE_BANCAIRE ✅ (10+ types opérations, depuis 08/11)

**En développement:**
- EVENEMENT_SIMPLE (factures fournisseurs, notes de frais)
- CLOTURE_EXERCICE

## Architecture Production V8.0
- **Modules:** workflow v2.4 (détection+parsing+propositions) + validations + parseurs Vision
- **Optimisations:** Mémoire OCR (100 DPI, max 10 pages, JPEG 85%), tokens MD5 32-chars
- **Performance:** <1€/mois, 222+ cycles uptime, 100% fiabilité ACID, 99.98% OCR

## Sessions Correction Novembre
- **02-08/11:** 9 bugs corrigés (detection, token, dates, montants, format, insertion)
- **08/11:** 3 corrections RELEVE_BANCAIRE (detection, cleanup JSON, multi-validations)
- **10+ PRs mergées:** #92-#98, #168-#172, #263-#267