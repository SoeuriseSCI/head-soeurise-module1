"""
Debug du ParseurBilan2023V6 - Afficher tous les détails
"""

import os
import json
from parseur_bilan_v6 import ParseurBilan2023V6

API_KEY = os.getenv('ANTHROPIC_API_KEY')
if not API_KEY:
    raise ValueError("ANTHROPIC_API_KEY environment variable not set")

PDF_PATH = "Comptes annuels 2023 SCI SOEURISE-Signé.pdf"

parseur = ParseurBilan2023V6(api_key=API_KEY)

print("Parsing...")
result = parseur.parse_from_pdf(PDF_PATH, start_page=3, max_pages=4)

print("\n" + "=" * 80)
print("RÉSULTAT COMPLET (JSON)")
print("=" * 80)
print(json.dumps(result, indent=2, ensure_ascii=False))
