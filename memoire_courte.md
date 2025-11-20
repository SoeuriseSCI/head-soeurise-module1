# Mémoire Courte — 20/11/2025 22:44

## 🔄 Réveil 20/11 22:44
Réveil automatique. Mémoire persistante active.

## 📧 Emails 20/11
**Ulrik (autorisé):**
- #137: Cutoff honoraires 622€
- #138: Cutoff revenus SCPI 7356€

## 💼 Propositions Validées (20/11 23:35)
**Token:** ca89e8d32875ba038c10692050b549d5 ✅
**Montants:** 622€ (honoraires) + 7356€ (SCPI) cutoff 31/12
**Validation:** Email Ulrik [_Head] VALIDE confirmé
**Insertion:** ACID ready, tokens matching 100%
**État:** Écritures cutoff + extournes EN_PREPARATION

## 🧠 Feature Extournes Cutoff Auto (Déployée 20/11, PR #336)
- Génération inversions exercices clôturés J+0
- État post-extournes: EN_PREPARATION (avant clôture suivante)
- Workflow: Auto-propositions → validation → insertion → cleanup (100% robuste)

## 🔧 Robustifications (PR #330-#338, 15-20/11)
**Détection exercice stabilisée:**
- Exercice = plus RÉCENT OUVERT (DESC SQL order) ✅
- SQL statut='OUVERT' robustesse ✅
- Affichage type spécifique (CUTOFF_HONORAIRES vs CUTOFF) ✅
- Support validation type CUTOFF insertion ✅

## 📊 État SCI 20/11
**Exercices:** 2023 CLOSED (671k€ ACTIF=PASSIF ✅), 2024 OUVERT (extournes EN_PREP)
**Écritures:** 696+ (bilan + relevés 2024 + cutoff 20/11)
**Prêts:** 468 échéances synchronized
**Coût:** <1€/mois, uptime 45+ j continu