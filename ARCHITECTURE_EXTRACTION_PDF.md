# Architecture Extraction PDF - Approche Hybride

**Date**: 06/11/2025
**Version**: 6.1

## 🎯 Stratégie Globale

Le système utilise **deux approches complémentaires** pour l'extraction PDF, optimisées selon la fréquence d'utilisation :

| Type Document | Fréquence | Méthode | Raison |
|---------------|-----------|---------|---------|
| **Relevés bancaires** | Continue (10-20 ans) | API PDF Native Claude | Efficacité, moins de mémoire, meilleure analyse |
| **Bilans comptables** | Unique (1 fois) | pdf2image + Claude Vision | Tableaux structurés, précision absolue |
| **Tableaux amortissement** | Occasionnelle (nouveaux prêts) | pdf2image + Claude Vision | Tableaux complexes, toutes les échéances |

---

## 📋 Détails par Module

### 1. Événements Comptables (Flux Continu)

**Module**: `extracteur_pdf.py`
**Utilisé par**: `workflow_evenements.py` → `module2_integration_v2.py`
**Méthode**: **API PDF Native Claude** (`type="document"`)

```python
# extracteur_pdf.py
def _lire_pdf_base64(self):
    with open(self.pdf_path, 'rb') as f:
        pdf_data = f.read()
    return base64.standard_b64encode(pdf_data).decode('utf-8')

def analyser_document(self):
    pdf_base64 = self._lire_pdf_base64()
    response = self.client.messages.create(
        messages=[{
            "content": [{
                "type": "document",  # ← API native
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": pdf_base64
                }
            }]
        }]
    )
```

**Avantages**:
- ✅ Mémoire réduite (~10 MB vs 615 MB)
- ✅ Plus de dépendances poppler
- ✅ Meilleure analyse sémantique des périodes
- ✅ Extraction complète de toutes les pages
- ✅ Optimisé pour usage intensif (10-20 ans)

**Désavantages**:
- ⚠️ Moins précis sur tableaux très structurés (acceptable pour relevés)

---

### 2. Bilans Comptables (Événement Unique)

**Module**: `parseur_bilan_v6.py`
**Méthode**: **pdf2image + Claude Vision**

```python
# parseur_bilan_v6.py
all_images = convert_from_path(filepath, dpi=100)
images = all_images[start_page-1:end_page]

for image in images:
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG', quality=85, optimize=True)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()

    # Envoyer à Claude Vision
```

**Pourquoi garder pdf2image ?**
- ✅ Extraction précise des tableaux ACTIF/PASSIF
- ✅ Reconnaissance exacte des montants négatifs (290, 120)
- ✅ Événement unique (1 fois par SCI) → performance non critique
- ✅ Testé et validé (571 613€ équilibré ✅)

---

### 3. Tableaux Amortissement (Événement Occasionnel)

**Module**: `parseur_pret_v6.py`
**Méthode**: **pdf2image + Claude Vision**

```python
# parseur_pret_v6.py
images = convert_from_path(filepath, dpi=100)

for image in images[:max_pages]:
    # Extraction complète 216-252 échéances
```

**Pourquoi garder pdf2image ?**
- ✅ Extraction précise de TOUTES les échéances (216-252 lignes)
- ✅ Tableaux complexes avec calculs (capital, intérêts, solde)
- ✅ Occasionnel (nouveaux prêts, renégociation) → performance non critique
- ✅ Testé et validé (468 échéances ✅)

---

### 4. _Head.Soeurise (Extraction Simple)

**Module**: `main.py`
**Méthode**: **API PDF Native Claude** (depuis V6.1)

```python
# main.py - extract_pdf_via_claude_vision()
pdf_base64 = base64.standard_b64encode(pdf_data).decode('utf-8')

response = client.messages.create(
    messages=[{
        "content": [{
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": pdf_base64
            }
        }]
    }]
)
```

**Cohérence avec `extracteur_pdf.py`**:
- ✅ Même méthode pour analyses quotidiennes
- ✅ Rapports _Head précis (périodes, nombre de relevés)

---

## 🔧 Dépendances

```txt
anthropic==0.40.0              # Claude API (avec support PDF natif)
pdf2image==1.17.0              # PDF → Images (pour parseurs bilan/prêts)
pdfplumber==0.11.0             # PDF text extraction fallback
```

**Note**: Les deux approches coexistent harmonieusement :
- `extracteur_pdf.py` + `main.py` : API native (flux continu)
- `parseur_bilan_v6.py` + `parseur_pret_v6.py` : pdf2image (événements rares)

---

## 📊 Performance

| Métrique | API Native | pdf2image |
|----------|------------|-----------|
| Mémoire | ~10 MB | ~615 MB |
| Tableaux structurés | Bon | Excellent |
| Analyse sémantique | Excellent | Bon |
| Usage recommandé | Flux continu | Événements rares |

---

## ✅ Tests de Non-Régression

```bash
# Vérifier bilan d'ouverture intact
python verifier_bilan_2023.py

# Vérifier échéances intactes
psql $DATABASE_URL -c "SELECT COUNT(*) FROM echeances_prets;"
# Attendu: 468

# Vérifier écritures bilan intactes
psql $DATABASE_URL -c "SELECT COUNT(*) FROM ecritures WHERE exercice_id = 1;"
# Attendu: 11
```

---

**Auteur**: Claude Code
**Révision**: Validée par utilisateur - Architecture hybride optimale
