# Mémoire Moyenne - Cycle 1 Complet + Prêts (29/10/2025)

## Module 2 Comptabilité - OPÉRATIONNEL
**État:** Production depuis 27/10/2025
- Workflow: Proposition → Token validation → Confirmé
- Bugs corrigés (27/10 16h48): Détection et envoi emails
- Schéma BD: 37 colonnes + table propositions_en_attente
- Prêt à intégration données métier

## Prêts Immobiliers SCI - DONNÉES STRUCTURANTES CONSOLIDÉES
**Reçu:** 29/10/2025 (tableaux 17/04/2023)
**Portfolio:** 500k€ nominal (Crédit Lyonnais)
**Sources:** 2 tableaux PDF détaillés (240 + 217 échéances)

### Prêt 1 (BRM0911AH) - Amortissement régulier
- 250k€ @ 1.05% fixe, 252 mois (21 ans)
- Amortissement: 15/05/2023 → 15/04/2043
- Échéance: 1,166.59€/mois (constant)
- Capital restant 15/10/2025: 223,704.21€
- Assurance: Emma & Pauline 50/50
- Total intérêts: 29,981.41€
- Profil: Régulier sans pics

### Prêt 2 (BRLZE11AQ) - Franchise 15 ans + pic remboursement
- 250k€ @ 1.24% fixe, 216 mois durée totale
- **Phase 1 (15 ans):** Intérêts seuls 258.33€/mois jusqu'au 15/03/2040 (cumulé 84,900€)
- **Phase 2 (avril 2040):** Remboursement unique 253,142.43€ (capital 250k€ + intérêts 3,142.43€)
- Sans assurance
- Total intérêts: 55,583.42€
- **CRITIQUE:** Pic trésorerie avril 2040 (15 ans planification obligatoire)

## Architecture V6.0 Claude Code - STABLE
- 38 réveils consécutifs sans rupture mémoire
- CLAUDE.md auto-chargé + outils natifs Read/Edit
- API GitHub ?ref=main (pas de cache CDN)
- Réveil: 08:00 UTC = 10:00 France été

## Roadmap Cycle 2
- Module 3: Placements + Veille juridique (après validation Ulrik)
- Ingestion données: Prêts immobiliers (EN COURS) + revenus locatifs + charges SCI
- Transmission Emma/Pauline: Automisation progressive analyses