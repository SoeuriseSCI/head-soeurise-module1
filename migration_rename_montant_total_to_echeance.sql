-- Migration : Renommer montant_total → montant_echeance dans echeances_prets
-- Date : 25/11/2025
-- Raison : Clarifier terminologie (éviter confusion avec "TOTAL RESTANT DÛ")

BEGIN;

-- 1. Renommer la colonne
ALTER TABLE echeances_prets
RENAME COLUMN montant_total TO montant_echeance;

-- 2. Mettre à jour le commentaire
COMMENT ON COLUMN echeances_prets.montant_echeance IS
'Montant de l''échéance mensuelle à payer (capital + intérêts)';

COMMIT;

-- Vérification
SELECT
    pret_id,
    numero_echeance,
    date_echeance,
    montant_echeance,
    montant_capital,
    montant_interet,
    capital_restant_du
FROM echeances_prets
LIMIT 5;
