-- Migration : Ajout colonne type_taux aux prêts immobiliers
-- Date : 25/11/2025
-- Raison : Séparer type de taux (FIXE/VARIABLE) du type d'amortissement (AMORTISSABLE/IN_FINE)

BEGIN;

-- 1. Ajouter la nouvelle colonne type_taux avec valeur par défaut
ALTER TABLE prets_immobiliers
ADD COLUMN IF NOT EXISTS type_taux VARCHAR(20) DEFAULT 'FIXE';

-- 2. Mettre à jour les valeurs existantes (par défaut FIXE en France)
UPDATE prets_immobiliers
SET type_taux = 'FIXE'
WHERE type_taux IS NULL;

-- 3. Ajouter commentaire pour documentation
COMMENT ON COLUMN prets_immobiliers.type_taux IS 'Type de taux : FIXE (presque toujours en France) ou VARIABLE';

COMMIT;

-- Vérification
SELECT id, numero_pret, banque, type_taux, type_amortissement
FROM prets_immobiliers;
