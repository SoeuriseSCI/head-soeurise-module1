-- ============================================================================
-- CORRECTION DES MÉTADONNÉES DES EXERCICES 2023 ET 2024
-- ============================================================================
-- Date : 23/11/2025
-- Contexte : Après patchs manuels de clôture, mise à jour des métadonnées
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 1. EXERCICE 2023 - Mise à jour métadonnées
-- ----------------------------------------------------------------------------
-- L'exercice 2023 a été clôturé mais les métadonnées n'ont pas été renseignées

UPDATE exercices
SET
    date_cloture = '2024-12-31',  -- Date de clôture administrative
    resultat_exercice = 0.00,      -- Résultat à confirmer (calculer si nécessaire)
    updated_at = NOW()
WHERE annee = 2023 AND id = 1;

-- ----------------------------------------------------------------------------
-- 2. EXERCICE 2024 - Mise à jour métadonnées
-- ----------------------------------------------------------------------------
-- Résultat calculé par le script de vérification : 17 765,47 €
-- (Produits 26 395,92 € - Charges 8 630,45 € = 17 765,47 €)

UPDATE exercices
SET
    date_cloture = '2025-04-08',   -- Date AG de clôture 08/04/2025
    resultat_exercice = 17765.47,  -- Résultat vérifié par calcul
    updated_at = NOW()
WHERE annee = 2024 AND id = 2;

-- ----------------------------------------------------------------------------
-- Vérification
-- ----------------------------------------------------------------------------
SELECT
    id,
    annee,
    statut,
    date_debut,
    date_fin,
    date_cloture,
    resultat_exercice
FROM exercices
ORDER BY annee;

COMMIT;

-- ============================================================================
-- NOTES D'EXÉCUTION
-- ============================================================================
-- Ce script doit être exécuté sur Render Shell :
--
-- 1. Se connecter à Render Shell
-- 2. psql $DATABASE_URL
-- 3. Copier-coller ce script
-- 4. Vérifier les résultats
-- 5. Si OK, les changements sont committés automatiquement
-- 6. Créer une nouvelle sauvegarde : python sauvegarder_base.py
-- ============================================================================
