-- Requête SQL pour analyser les tokens des propositions EN_ATTENTE
-- À exécuter sur Render : psql $DATABASE_URL

SELECT
    id,
    token,
    type_evenement,
    LEFT(email_subject, 50) as sujet,
    jsonb_array_length(propositions_json->'propositions') as nb_ecritures,
    created_at,
    statut
FROM propositions_en_attente
WHERE statut = 'EN_ATTENTE'
ORDER BY created_at DESC;
