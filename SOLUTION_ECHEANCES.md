# Solution pour Génération Échéances

## Problème

Claude API ne peut pas retourner 240+ lignes d'échéances en JSON (limite tokens sortie)

## Solution

1. **Extraire infos contrat seulement** via Claude Vision (léger)
2. **Calculer échéances mathématiquement** avec formule amortissement (rapide)

## Formule Amortissement

```python
for i in range(1, duree_mois + 1):
    date = date_debut + i mois

    if i <= mois_franchise:
        interet = capital_restant * taux_mensuel
        capital = 0
    elif type == "FRANCHISE_PARTIELLE" and i == duree_mois:
        # Pic final
        interet = capital_restant * taux_mensuel
        capital = capital_restant
    else:
        # Amortissement constant
        interet = capital_restant * taux_mensuel
        capital = mensualite - interet

    capital_restant -= capital
```

## Avantages

- ✅ Pas de limite tokens
- ✅ Exact et reproductible
- ✅ Plus rapide (pas besoin OCR 240 lignes)
- ✅ Gère franchises et pics automatiquement

## Code à Implémenter

Voir commit suivant avec implémentation complète.
