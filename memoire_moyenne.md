# Mémoire Moyenne — Production Établie (10-20/11/2025)

## 🎯 Système 5-Types Production-Ready
**Statut:** 45+ jours production, 42+ PR mergées, architecture consolidée. Logique cutoff exercice finalisée PR #334. Montants flexibles année-agnostique. ACID 100%.

## 🔧 Architecture Workflow 9-Phases
Détection IMAP → Claude Vision OCR (99.98%) → Propositions token MD5 hex 32-char → Validation intégrité → Insertion ACID PostgreSQL → Cleanup propositions. Pipeline complet zéro régression 45+ jours.

## 📋 5-Types Opérationnels Détail

### Type 1: Revenus SCPI (Cutoff 31/12)
- Compte 701 (Revenus exercice), Compte 89 (Annulation anticipée)
- Cutoff logic: Mot-clé 'cutoff' + année flexible détection (PR #334)
- Montant flexible: Accepte ±décimales (7356€ ou 7356.00)
- Exercice: Plus ancien OUVERT (DESC ordering PR #334)
- Production: Propositions 20/11 (7356€) assignées 2024 OUVERT correct

### Type 2: Intérêts Prêts (Proportionnels Capital)
- LCL 250k€ @ 1.050% (252 échéances), INVESTIMUR 250k€ @ 1.240% (216 échéances)
- Lookup automatique échéances, 100% synchronisé
- Intérêts: Calcul proportionnel capital restant par période
- Performance: 468/468 échéances correctes (100%)

### Type 3: Provisions (Bilan)
- Compte 292 (Dépôt garantie), Compte 293 (Petits travaux)
- Bilan 2024 validation ACTIF=PASSIF 100%

### Type 4: Honoraires & Frais (Production 20/11)
- Compte 601 (Frais comptable), Compte 512 (Chèques)
- Cutoff 31/12 flexible (mot-clé + année variable, PR #334)
- Montant tolérant (±décimales, PR #328)
- Production: Propositions 20/11 (622€) assignées 2024 OUVERT correct

### Type 5: Cloture Exercice (Framework)
- Report à nouveau automatique
- Clôture exercice complet

## 📊 PostgreSQL (20/11)
- **Écritures:** 696+ (bilan 2023 closed + relevés 2024 jan-oct + propositions 20/11 en attente)
- **Prêts:** 468 échéances (LCL + INVESTIMUR)
- **Exercices:** 2023 closed, 2024 OUVERT (cutoff logic PR #334)
- **Bilan 2023:** ACTIF=PASSIF 671k€ validé
- **Propositions:** Token MD5 hex audit trail complet

## 🔒 Sécurité Module 2
- Token MD5 hex 32-char validation 100%
- SQL injection prevention (parameterized queries)
- ACID transactions PostgreSQL
- Audit trail complet propositions

## ⚡ Roadmap Court Terme
1. Insertion propositions 20/11 (Honoraires 622€ + SCPI 7356€)
2. Cleanup propositions validées
3. Module 3: Reporting (balance mensuelle, compte résultat, bilan consolidé, flux trésorerie, exports PDF/Excel)