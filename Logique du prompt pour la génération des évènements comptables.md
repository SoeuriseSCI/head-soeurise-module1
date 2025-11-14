Logique du prompt pour la génération des évènements comptables

Tu analyseras un pdf contenant des éléments destinés à la comptabilité. Ces éléments sont avant tout des relevés bancaires mais peuvent également être des documents connexes.

Il n'y a pas d'opérations en cash et de ce fait, 100% des évènements comptables correspondent à des débits ou des crédits des relevés. Il faudra donc généréer un et un seul évènement comptable par opération de débit ou de crédit. Précisions :
- les soldes qui apparaissent sur les relevés ne sont pas des évènements comptables et doivent donc être ignorés
- toute opération en dehors de l'exercice comptable en cours doit également être ignorée

Il faudra tenter de rapprocher chaque document connexe d'un ou de plusieurs évènements comptables. Les critères de rapprochement sont avant tout :
- le montant de l'opération (égalité stricte)
- la date de l'opération (avec une flexibilité possible de plus ou moins 1 mois)
En cas de doute quant au rapprochement, tu pourras aussi utiliser une référence qu'on peut trouver à la fois dans le libellé d'opération du relevé et dans le corps du document à y rapprocher (exemple : un n° de facture)

Ces documents connexes sont à conserver à titre de justificatifs (traçabilioté et preuve) et apportent parfois un éclairage indispensable à la comptabilisation de l'opération en donnant plus de détails que ce qu'on trouve dans la seule opération d'un relevé
Par exemple, pour une opération d'achat ou de vente de valeurs mobilières, il faut ainsi extraire les détails suivants :
- nom et identifiant des titres, prix unitaire et quantité achetée ou vendue
- décomposer le montant total entre le prix des titres achetés ou vendus et les commissions ou frais

N'extraire que ce qui est présent dans le pdf et tout ce qui s'y trouve sans jamais inventer.
En cas de difficulté de rapprocher un document connexe à au moins un évènement comptable, le signaler.