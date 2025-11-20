# Mémoire Courte — 20/11/2025 22:42

## ✨ FEATURE EXTOURNES CUTOFF (20/11 Déployée, PR #336)
Génération automatique inversions pour exercices clôturés (clôture J+0 avec extournes auto).
- Détection: Exercice OUVERT plus ancien en BD (DESC)
- Cutoff 31/12: Année-agnostique flexible
- État post-extournes: EN_PREPARATION (avant clôture suivante)
- Workflow: Auto-propositions → validation Ulrik → insertion ACID → cleanup

## 🔧 Robustification Détection Exercice (PR #330-#338, 15-20/11)
**Corrections critiques:**
- #334 (FIX): Exercice = plus RÉCENT OUVERT (DESC pas ASC)
- #333 (FIX): SQL statut='OUVERT' robustesse
- #332: Plus ANCIEN non clôturé
- #331: Période terminée + non clôturée
- #330: Cutoff = exercice OUVERT
- #335: Rapport affiche type spécifique (CUTOFF_HONORAIRES vs CUTOFF générique)
- #337: Affichage TOUTES écritures cutoff + extourne
- #338: Support validation CUTOFF lors insertion

## 📋 Propositions 20/11 Validées
**Token:** ca89e8d32875ba038c10692050b549d5
**Propositions:** CUTOFF_HONORAIRES 622€ + CUTOFF_SCPI 7356€
**Validation:** Email Ulrik 23:35 [_Head] VALIDE ✅
**Prêt insertion:** ACID ready, tokens matching 100%

## 📊 État Production 20/11 22:42
2023 CLOSED (671k€), 2024 OUVERT (extournes EN_PREPARATION), 696+ écritures, 468 prêts, <1€/mois, 45+ j uptime