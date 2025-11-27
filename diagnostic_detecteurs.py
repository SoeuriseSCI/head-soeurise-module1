#!/usr/bin/env python3
"""
Script de diagnostic pour vérifier les détecteurs disponibles sur Render
"""

import sys
import os

print("=" * 80)
print("DIAGNOSTIC DÉTECTEURS - Version déployée")
print("=" * 80)
print()

# 1. Vérifier l'import
print("1. TEST IMPORT DetecteurCutoffsMultiples...")
try:
    from detecteurs_evenements import DetecteurCutoffsMultiples
    print("   ✅ DetecteurCutoffsMultiples importé avec succès")
except ImportError as e:
    print(f"   ❌ ERREUR import: {e}")
    sys.exit(1)

# 2. Vérifier FactoryDetecteurs
print()
print("2. TEST IMPORT FactoryDetecteurs...")
try:
    from detecteurs_evenements import FactoryDetecteurs
    print("   ✅ FactoryDetecteurs importé avec succès")
except ImportError as e:
    print(f"   ❌ ERREUR import: {e}")
    sys.exit(1)

# 3. Lister les détecteurs disponibles
print()
print("3. LISTE DES DÉTECTEURS INSTANCIÉS...")
try:
    from models_module2 import get_session
    session = get_session(os.environ['DATABASE_URL'])

    detecteurs = FactoryDetecteurs.get_detecteurs(session)
    print(f"   Nombre total: {len(detecteurs)}")
    print()

    for i, detecteur in enumerate(detecteurs, 1):
        classe = detecteur.__class__.__name__
        print(f"   {i:2d}. {classe}")
        if classe == "DetecteurCutoffsMultiples":
            print("       ⭐ TROUVÉ!")

    session.close()

except Exception as e:
    print(f"   ❌ ERREUR listing: {e}")
    import traceback
    traceback.print_exc()

# 4. Test de détection
print()
print("4. TEST DÉTECTION EMAIL CUTOFFS...")
try:
    from models_module2 import get_session
    session = get_session(os.environ['DATABASE_URL'])

    detecteur = DetecteurCutoffsMultiples(session)

    email_test = {
        'email_subject': 'Cutoffs / extournes',
        'email_body': '''Bonjour _Head,

Peux-tu créer des cutoffs pour:
1) les honoraires comptables de clôture de l'exercice 2024 (622€)
2) les produits SCPI du 4e trimestre 2024 (6755€)

Merci!''',
        'email_date': '2025-11-27'
    }

    detecte = detecteur.detecter(email_test)
    print(f"   Détection: {detecte}")

    if detecte:
        print("   ✅ Email correctement détecté")
    else:
        print("   ❌ Email NON détecté (critères non remplis)")

    session.close()

except Exception as e:
    print(f"   ❌ ERREUR test: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
print("FIN DIAGNOSTIC")
print("=" * 80)
