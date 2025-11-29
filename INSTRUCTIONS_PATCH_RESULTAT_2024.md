# Instructions : Application du Patch Reprise Résultat 2024

## Contexte

Le bilan d'ouverture 2025 est incomplet. Il manque l'écriture de reprise du résultat 2024, ce qui cause un déséquilibre du compte 89 de -17,766.29€.

## Étapes d'application

### 1. Déployer le code corrigé sur Render

Déclencher le déploiement manuel sur Render pour le commit `f0df0df`.

**Vérification** : Attendre que le build soit terminé (~2-3 min).

---

### 2. Se connecter au shell Render

1. Aller sur https://dashboard.render.com
2. Sélectionner le service `head-soeurise-web`
3. Cliquer sur l'onglet **Shell**
4. Attendre que le shell soit prêt

---

### 3. Exécuter le script de patch

Dans le shell Render, exécuter :

```bash
python3 patch_reprise_resultat_2024.py
```

**Le script va :**
1. Vérifier l'état actuel du compte 89
2. Afficher l'écriture qui sera créée
3. Demander confirmation (`oui`/`non`)

**Sortie attendue :**
```
================================================================================
PATCH : REPRISE RÉSULTAT 2024 DANS BILAN D'OUVERTURE 2025
================================================================================

1. VÉRIFICATION ÉTAT ACTUEL
--------------------------------------------------------------------------------
✅ Exercice 2025 trouvé (ID: 4)

Compte 89 AVANT patch :
  Débit  :      553,249.69 €
  Crédit :      571,015.98 €
  Solde  :      -17,766.29 €

2. CRÉATION ÉCRITURE DE REPRISE
--------------------------------------------------------------------------------
Résultat 2024 à reprendre : 17,766.29 €
Type : Bénéfice (solde 89 créditeur)

Écriture à créer :
  Numéro  : 2025-0101-OUV-RES
  Date    : 2025-01-01
  Débit   : 89
  Crédit  : 120
  Montant : 17,766.29 €

3. CONFIRMATION
--------------------------------------------------------------------------------
Voulez-vous appliquer ce patch ? (oui/non) :
```

---

### 4. Confirmer l'application

Taper `oui` puis **Entrée**.

**Sortie attendue :**
```
4. APPLICATION DU PATCH
--------------------------------------------------------------------------------
✅ Écriture créée avec succès (ID: 708)

Compte 89 APRÈS patch :
  Débit  :      571,015.98 €
  Crédit :      571,015.98 €
  Solde  :            0.00 €

✅ SUCCÈS : Compte 89 maintenant équilibré !

================================================================================
PATCH TERMINÉ
================================================================================
```

---

### 5. Vérifier les bilans

Exécuter le script de vérification des bilans :

```bash
python3 << 'EOF'
import os
from decimal import Decimal
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_module2 import ExerciceComptable, EcritureComptable

engine = create_engine(os.environ['DATABASE_URL'])
Session = sessionmaker(bind=engine)
session = Session()

def verifier_bilan(annee):
    exercice = session.query(ExerciceComptable).filter_by(annee=annee).first()
    if not exercice:
        return

    # Écritures bilan d'ouverture
    if annee > 2023:
        ecritures_ouv = session.query(EcritureComptable).filter_by(
            exercice_id=exercice.id,
            type_ecriture='BILAN_OUVERTURE'
        ).all()

        solde_89 = Decimal('0')
        for e in ecritures_ouv:
            if e.compte_debit == '89':
                solde_89 += e.montant
            if e.compte_credit == '89':
                solde_89 -= e.montant

        print(f"\nExercice {annee} - Bilan d'ouverture :")
        print(f"  Compte 89 solde : {solde_89:>15,.2f} €")
        if abs(solde_89) < Decimal('0.01'):
            print("  ✅ ÉQUILIBRÉ")
        else:
            print(f"  ❌ DÉSÉQUILIBRÉ")

verifier_bilan(2025)

session.close()
EOF
```

**Résultat attendu :**
```
Exercice 2025 - Bilan d'ouverture :
  Compte 89 solde :            0.00 €
  ✅ ÉQUILIBRÉ
```

---

### 6. Vérifier les écritures 2025

```bash
python3 << 'EOF'
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_module2 import ExerciceComptable, EcritureComptable

engine = create_engine(os.environ['DATABASE_URL'])
Session = sessionmaker(bind=engine)
session = Session()

exercice_2025 = session.query(ExerciceComptable).filter_by(annee=2025).first()

ecritures = session.query(EcritureComptable).filter_by(
    exercice_id=exercice_2025.id
).filter(
    EcritureComptable.numero_ecriture.like('%OUV%')
).order_by(
    EcritureComptable.numero_ecriture
).all()

print(f"\nÉcritures d'ouverture 2025 : {len(ecritures)}")
print("-"*80)
for e in ecritures:
    print(f"{e.numero_ecriture:<20} | {e.compte_debit:>6} → {e.compte_credit:<6} | {e.montant:>13,.2f} €")

session.close()
EOF
```

**Résultat attendu :**
```
Écritures d'ouverture 2025 : 12
--------------------------------------------------------------------------------
2025-0101-OUV-001    |     89 → 101    |      1,000.00 €
2025-0101-OUV-002    |    119 → 89     |     36,148.00 €
2025-0101-OUV-003    |     89 → 164    |    486,250.69 €
2025-0101-OUV-004    |     89 → 1688   |        254.00 €
2025-0101-OUV-005    |    271 → 89     |    500,032.00 €
2025-0101-OUV-006    |    273 → 89     |     25,760.63 €
2025-0101-OUV-007    |     89 → 290    |     50,003.00 €
2025-0101-OUV-008    |     89 → 4081   |        622.00 €
2025-0101-OUV-009    |   4181 → 89     |      6,755.00 €
2025-0101-OUV-010    |     89 → 455    |     15,120.00 €
2025-0101-OUV-011    |    512 → 89     |      2,320.35 €
2025-0101-OUV-RES    |     89 → 120    |     17,766.29 €  ← NOUVELLE ÉCRITURE
```

---

## Vérifications finales

### Compte 89 (Bilan d'ouverture)
- **Avant patch** : Solde = -17,766.29€ ❌
- **Après patch** : Solde = 0.00€ ✅

### Compte 120 (Résultat de l'exercice)
- **Avant patch** : Solde débiteur = 17,766.29€ (incohérent)
- **Après patch** :
  - Crédit par OUV-RES : 17,766.29€
  - Débit par AFF-001 : 17,766.29€
  - **Solde final = 0.00€** ✅

### Bilan 2025
- **ACTIF** : Équilibré ✅
- **PASSIF** : Équilibré ✅
- **Capitaux propres** :
  - 101 (Capital) : 1,000.00€
  - 110 (RAN créditeur) : 17,766.29€ ← Résultat 2024 affecté
  - 119 (RAN débiteur) : -36,148.00€
  - **Total capitaux** : 1,000 + 17,766.29 - 36,148 = **-17,381.71€**

---

## En cas de problème

### Le script indique "Écriture déjà créée"
```
⚠️  L'écriture 2025-0101-OUV-RES existe déjà (ID: 708)
   Aucune action nécessaire.
```
→ **Patch déjà appliqué**, rien à faire.

### Le compte 89 reste déséquilibré après patch
→ Vérifier les logs pour identifier l'erreur
→ Contacter support si nécessaire

### Erreur de connexion BD
→ Vérifier que `DATABASE_URL` est bien définie dans l'environnement Render

---

## Rollback (si nécessaire)

Pour annuler le patch :

```bash
python3 << 'EOF'
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_module2 import EcritureComptable

engine = create_engine(os.environ['DATABASE_URL'])
Session = sessionmaker(bind=engine)
session = Session()

# Supprimer l'écriture créée par le patch
ecriture = session.query(EcritureComptable).filter_by(
    numero_ecriture='2025-0101-OUV-RES'
).first()

if ecriture:
    print(f"Suppression de l'écriture {ecriture.numero_ecriture} (ID: {ecriture.id})")
    session.delete(ecriture)
    session.commit()
    print("✅ Écriture supprimée")
else:
    print("❌ Écriture non trouvée")

session.close()
EOF
```

---

## Contact

En cas de question : ulrik.c.s.be@gmail.com
