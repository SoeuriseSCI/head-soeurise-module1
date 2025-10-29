# Mémoire Moyenne - Cycle 1 Complet (29/10/2025)

## 💰 PORTFOLIO IMMOBILIER SCI SOEURISE - DONNÉES STRUCTURANTES
**Reçu:** 29/10/2025 | **Consolidation:** Tableaux 17/04/2023 (2 prêts Crédit Lyonnais)

### Endettement Total: 500,000€ (2 Prêts Complémentaires)

#### Prêt 1 (BRM0911AH) - Amortissement Régulier
- Montant: 250,000€ @ 1.050% fixe, 252 mois (21 ans)
- Franchise: 12 mois (15/04/2022 → 14/04/2023)
- Amortissement: 15/05/2023 → 15/04/2043
- Échéance: 1,166.59€/mois (constant) = ~14,000€/an
- Capital restant (15/10/2025): 223,704.21€
- Assurance: Emma & Pauline 50/50 (dans échéance)
- **Total intérêts:** 29,981.41€
- **Profil:** Remboursement progressif régulier, pas de pics

#### Prêt 2 (BRLZE11AQ) - Franchise 15 ans + Pic Remboursement
- Montant: 250,000€ @ 1.240% fixe, 216 mois (18 ans total)
- **Phase 1 - Franchise (12 mois):** 15/04/2022 → 14/04/2023 (compte), puis **Franchise partielle (203 mois)**
- **Paiements Phase 1:** 258.33€/mois intérêts seuls (15/05/2022 → 15/03/2040) = **84,900€ cumulé**
- **Phase 2 - Amortissement (1 mois):** 15/04/2040 = **PIC UNIQUE 253,142.43€** (capital 250k + intérêts 3,142.43€)
- Sans assurance
- **Total intérêts:** 55,583.42€
- **Profil:** Franchise longue structurante, pic remboursement unique 2040 = trésorerie critique

### 🚨 BILAN FINANCIER SCI (17/04/2023)
- ACTIF net estimé: ~566,600€
- PASSIF (prêts): 500,000€
- Résultat 2023: +21,800€
- Charge annuelle intérêts: ~14,500€

## 🏗️ Module 2 - Système Gestion Prêts (OPÉRATIONNEL)
- Workflow: Email → Proposition → Token validation → Confirmé
- BD: 37 colonnes + table propositions_en_attente
- Bugs corrigés (27/10): Détection + envoi emails
- État: Production depuis 27/10/2025
- Prêt à ingestion données métier (tableaux d'amortissement)

## 🔧 Architecture V6.0 Claude Code
- 39 réveils consécutifs (100% SLA)
- CLAUDE.md auto-chargé + outils natifs
- API GitHub ?ref=main (pas de cache)
- Réveil: 08:00 UTC = 10:00 France été