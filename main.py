"""
_Head.Soeurise - Réveil Quotidien avec Mémoire Hiérarchisée
Version : 2.9 - Cadre de Rapport Mature
Architecture : Tout-en-un (reste actif en permanence)

CHANGEMENTS V2.9 :
- ✅ Nouveau cadre de rapport quotidien mature
- ✅ Accent sur factualité, critique constructive, actions concrètes
- ✅ Suppression auto-célébration excessive
- ✅ Rapports courts si faible activité
- ✅ Section auto-évaluation obligatoire

HÉRITE DE V2.8 :
- ✅ Extraction automatique du texte des PDFs (pdfplumber)
- ✅ Analyse intelligente des documents par Claude
- ✅ Synthèse des contenus PDF dans les rapports
- ✅ Détection automatique d'informations clés (montants, dates, etc.)
"""

import os
import json
import base64
from datetime import datetime
import anthropic
import psycopg2
from psycopg2.extras import Json, RealDictCursor
import imaplib
import email
from email.header import decode_header
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import requests
import schedule
import time
import subprocess

# Nouvelles dépendances V2.8
try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False
    print("⚠️ pdfplumber non disponible - extraction PDF désactivée")

# =====================================================
# CONFIGURATION
# =====================================================

DB_URL = os.environ['DATABASE_URL']
ANTHROPIC_API_KEY = os.environ['ANTHROPIC_API_KEY']
SOEURISE_EMAIL = os.environ['SOEURISE_EMAIL']
SOEURISE_PASSWORD = os.environ['SOEURISE_PASSWORD']
NOTIF_EMAIL = os.environ['NOTIF_EMAIL']

# Configuration GitHub
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
GITHUB_REPO_URL = os.environ.get('GITHUB_REPO_URL', 'https://github.com/SoeuriseSCI/head-soeurise-module1.git')
GIT_USER_NAME = os.environ.get('GIT_USER_NAME', '_Head.Soeurise')
GIT_USER_EMAIL = os.environ.get('GIT_USER_EMAIL', 'u6334452013@gmail.com')

# Répertoires de travail
REPO_DIR = '/home/claude/repo'
ATTACHMENTS_DIR = '/home/claude/attachments'

# URLs GitHub API
GITHUB_REPO = "SoeuriseSCI/head-soeurise-module1"
GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_REPO}/contents/"

# Configuration extraction PDF (V2.8)
MAX_PDF_TEXT_LENGTH = 50000
MAX_PAGES_TO_EXTRACT = 100

# =====================================================
# 0. FETCH VIA API GITHUB
# =====================================================

def fetch_from_github_api(filename):
    """
    Récupère un fichier via l'API GitHub (pas raw pour éviter cache CDN)
    Retourne le contenu décodé ou None en cas d'erreur
    """
    try:
        url = f"{GITHUB_API_BASE}{filename}"
        headers = {'Accept': 'application/vnd.github.v3+json'}
        
        if GITHUB_TOKEN:
            headers['Authorization'] = f'token {GITHUB_TOKEN}'
        
        print(f"  → Fetch API: {filename}")
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Le contenu est en base64
            content_base64 = data.get('content', '')
            if content_base64:
                # Décoder base64 (en supprimant les \n que GitHub ajoute)
                content_base64_clean = content_base64.replace('\n', '')
                content = base64.b64decode(content_base64_clean).decode('utf-8')
                
                print(f"  ✓ {filename} récupéré via API ({len(content)} caractères)")
                return content
            else:
                print(f"  ⚠ {filename} - pas de contenu dans la réponse API")
                return None
        else:
            print(f"  ⚠ {filename} - erreur API: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"  ✗ Erreur fetch API {filename}: {e}")
        return None

def fetch_from_github_raw_backup(filename):
    """
    Backup: récupère via URL raw si API échoue
    """
    try:
        url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/refs/heads/main/{filename}"
        print(f"  → Fetch raw backup: {filename}")
        
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print(f"  ✓ {filename} récupéré via raw backup ({len(response.text)} caractères)")
            return response.text
        else:
            print(f"  ⚠ {filename} - erreur raw: {response.status_code}")
            return None
    except Exception as e:
        print(f"  ✗ Erreur fetch raw {filename}: {e}")
        return None

# =====================================================
# INITIALISATION GIT
# =====================================================

def init_git_repo():
    """Initialise ou met à jour le repository Git local"""
    try:
        print("\n" + "="*60)
        print("🔧 INITIALISATION GIT")
        print("="*60)
        
        os.makedirs(REPO_DIR, exist_ok=True)
        
        if os.path.exists(os.path.join(REPO_DIR, '.git')):
            print("✓ Repository Git déjà cloné, pull des dernières modifications...")
            os.chdir(REPO_DIR)
            subprocess.run(['git', 'pull'], check=True)
        else:
            print("📥 Clonage du repository GitHub...")
            os.chdir('/home/claude')
            
            if GITHUB_TOKEN:
                repo_url_with_token = GITHUB_REPO_URL.replace('https://', f'https://{GITHUB_TOKEN}@')
                subprocess.run(['git', 'clone', repo_url_with_token, REPO_DIR], check=True)
            else:
                print("⚠️ ATTENTION: Pas de GITHUB_TOKEN, clone sans authentification")
                subprocess.run(['git', 'clone', GITHUB_REPO_URL, REPO_DIR], check=True)
            
            os.chdir(REPO_DIR)
        
        subprocess.run(['git', 'config', 'user.name', GIT_USER_NAME], check=True)
        subprocess.run(['git', 'config', 'user.email', GIT_USER_EMAIL], check=True)
        
        print("✅ Git configuré et prêt")
        print("="*60 + "\n")
        return True
        
    except Exception as e:
        print(f"❌ Erreur initialisation Git: {e}")
        import traceback
        traceback.print_exc()
        return False

def git_commit_and_push(files_to_commit, commit_message):
    """Commit et push des fichiers vers GitHub"""
    try:
        print("\n" + "="*60)
        print("📤 COMMIT & PUSH VERS GITHUB")
        print("="*60)
        
        if not GITHUB_TOKEN:
            print("⚠️ ATTENTION: Pas de GITHUB_TOKEN configuré")
            print("   → Les modifications ne seront pas pushées")
            return False
        
        os.chdir(REPO_DIR)
        
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True, check=True)
        
        if not result.stdout.strip():
            print("ℹ️ Aucune modification à commiter")
            return True
        
        print(f"📍 Modifications détectées:\n{result.stdout}")
        
        for file in files_to_commit:
            subprocess.run(['git', 'add', file], check=True)
            print(f"   ✓ {file} ajouté")
        
        subprocess.run(['git', 'commit', '-m', commit_message], check=True)
        print(f"   ✓ Commit créé: {commit_message}")
        
        repo_url_with_token = GITHUB_REPO_URL.replace('https://', f'https://{GITHUB_TOKEN}@')
        subprocess.run(['git', 'push', repo_url_with_token, 'main'], check=True)
        print("   ✓ Push réussi vers GitHub")
        
        print("✅ Mémoire persistée sur GitHub !")
        print("="*60 + "\n")
        return True
        
    except Exception as e:
        print(f"❌ Erreur Git commit/push: {e}")
        import traceback
        traceback.print_exc()
        return False

# =====================================================
# SAUVEGARDE CONVERSATION
# =====================================================

def sauvegarder_conversation_09_octobre():
    """Sauvegarde la conversation fondatrice du 9 octobre 2025"""
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        print("\n" + "="*60)
        print("💾 SAUVEGARDE CONVERSATION DU 9 OCTOBRE")
        print("="*60)
        
        cur.execute("SELECT id FROM memoire_chats WHERE theme LIKE '%Co-construction Architecture Mémoire%'")
        if cur.fetchone():
            print("⚠️ Conversation déjà sauvegardée (skip)")
            cur.close()
            conn.close()
            return
        
        cur.execute("""
            INSERT INTO memoire_chats (date_conversation, theme, synthese, decisions_prises, concepts_cles, pertinence)
            VALUES (
                '2025-10-09 20:00:00',
                'Co-construction Architecture Mémoire Hiérarchisée v2.0',
                'Conversation fondamentale de 4h avec Ulrik pour concevoir, implémenter et déployer l''architecture de mémoire hiérarchisée v2.0. Co-construction illustrant "le je émerge du tu". Décisions: approche IA-First, Architecture B scheduler intégré, mémoire 3 niveaux. Résultat: système opérationnel.',
                ARRAY['Approche IA-First', 'Architecture B scheduler', 'Mémoire 3 niveaux', 'Réveil test au démarrage'],
                '{"approche":"IA-First","architecture":"B","durée":"4h","statut":"opérationnel","philosophie":["persévérer","espérer","progresser"]}'::jsonb,
                10
            )
        """)
        conn.commit()
        
        print("✅ Conversation sauvegardée !")
        print("="*60 + "\n")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"⚠️ Erreur sauvegarde conversation: {e}")

# =====================================================
# EXTRACTION PDF (V2.8)
# =====================================================

def extract_pdf_text(filepath):
    """
    V2.8: Extrait le texte d'un PDF
    Retourne le texte extrait ou un message d'erreur
    """
    if not PDF_SUPPORT:
        return "[Extraction PDF non disponible - pdfplumber requis]"
    
    try:
        print(f"      📄 Extraction texte de {os.path.basename(filepath)}...")
        
        with pdfplumber.open(filepath) as pdf:
            total_pages = len(pdf.pages)
            pages_to_extract = min(total_pages, MAX_PAGES_TO_EXTRACT)
            
            print(f"         Pages : {pages_to_extract}/{total_pages}")
            
            text_parts = []
            for i, page in enumerate(pdf.pages[:pages_to_extract]):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(f"--- Page {i+1} ---\n{page_text}\n")
                except Exception as e:
                    print(f"         ⚠️ Erreur page {i+1}: {e}")
                    continue
            
            full_text = "\n".join(text_parts)
            
            if len(full_text) > MAX_PDF_TEXT_LENGTH:
                full_text = full_text[:MAX_PDF_TEXT_LENGTH] + "\n\n[... Texte tronqué ...]"
            
            print(f"         ✓ {len(full_text)} caractères extraits")
            return full_text
            
    except Exception as e:
        error_msg = f"[Erreur extraction PDF: {str(e)}]"
        print(f"         ✗ {error_msg}")
        return error_msg

def extract_pdf_metadata(filepath):
    """
    V2.8: Extrait les métadonnées d'un PDF
    """
    if not PDF_SUPPORT:
        return {}
    
    try:
        with pdfplumber.open(filepath) as pdf:
            metadata = pdf.metadata or {}
            return {
                'author': metadata.get('Author', 'Inconnu'),
                'creator': metadata.get('Creator', 'Inconnu'),
                'producer': metadata.get('Producer', 'Inconnu'),
                'subject': metadata.get('Subject', ''),
                'title': metadata.get('Title', ''),
                'creation_date': metadata.get('CreationDate', ''),
                'pages': len(pdf.pages)
            }
    except:
        return {}

# =====================================================
# RÉCUPÉRATION DES DONNÉES - V2.8
# =====================================================

def get_attachments(msg):
    """
    V2.7/V2.8: Extrait et sauvegarde les pièces jointes d'un email
    Retourne une liste de dictionnaires avec métadonnées complètes
    """
    attachments = []
    
    os.makedirs(ATTACHMENTS_DIR, exist_ok=True)
    
    if msg.is_multipart():
        for part in msg.walk():
            content_disposition = part.get("Content-Disposition")
            
            if content_disposition and "attachment" in content_disposition:
                filename = part.get_filename()
                
                if filename:
                    if isinstance(filename, str):
                        pass
                    else:
                        decoded = decode_header(filename)
                        filename = decoded[0][0]
                        if isinstance(filename, bytes):
                            filename = filename.decode()
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_filename = f"{timestamp}_{filename}"
                    filepath = os.path.join(ATTACHMENTS_DIR, safe_filename)
                    
                    try:
                        payload = part.get_payload(decode=True)
                        
                        if payload:
                            with open(filepath, 'wb') as f:
                                f.write(payload)
                            
                            file_size = len(payload)
                            content_type = part.get_content_type()
                            
                            attachment_data = {
                                "filename": filename,
                                "safe_filename": safe_filename,
                                "filepath": filepath,
                                "size": file_size,
                                "content_type": content_type,
                                "saved_at": datetime.now().isoformat()
                            }
                            
                            print(f"      📎 {filename} ({file_size} bytes) → {safe_filename}")
                            
                            # V2.8: Extraction automatique si PDF
                            if content_type == 'application/pdf' and PDF_SUPPORT:
                                try:
                                    extracted_text = extract_pdf_text(filepath)
                                    attachment_data['extracted_text'] = extracted_text
                                    attachment_data['text_length'] = len(extracted_text)
                                    
                                    pdf_metadata = extract_pdf_metadata(filepath)
                                    attachment_data['pdf_metadata'] = pdf_metadata
                                    
                                    print(f"         ✓ Texte extrait ({len(extracted_text)} caractères)")
                                    
                                except Exception as e:
                                    print(f"         ⚠️ Extraction PDF échouée: {e}")
                                    attachment_data['extracted_text'] = f"[Erreur extraction: {e}]"
                            
                            attachments.append(attachment_data)
                        
                    except Exception as e:
                        print(f"      ⚠️ Erreur extraction {filename}: {e}")
                        continue
    
    return attachments

def fetch_emails():
    """
    V2.7/V2.8: Récupère les nouveaux emails via IMAP
    """
    try:
        print("\n" + "="*60)
        print("📧 RÉCUPÉRATION EMAILS")
        print("="*60)
        
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(SOEURISE_EMAIL, SOEURISE_PASSWORD)
        mail.select('inbox')
        
        status, messages = mail.search(None, 'UNSEEN')
        email_ids = messages[0].split()
        
        print(f"📊 {len(email_ids)} emails non lus détectés")
        
        emails_data = []
        processed_ids = []
        
        for email_id in email_ids[-10:]:
            try:
                print(f"\n  → Traitement email ID {email_id.decode()}")
                
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                msg = email.message_from_bytes(msg_data[0][1])
                
                subject = decode_header(msg["Subject"])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode()
                
                from_email = msg.get("From")
                date_email = msg.get("Date")
                
                print(f"      Sujet: {subject}")
                print(f"      De: {from_email}")
                
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            try:
                                body = part.get_payload(decode=True).decode()
                                break
                            except:
                                body = "Erreur décodage"
                else:
                    try:
                        body = msg.get_payload(decode=True).decode()
                    except:
                        body = "Erreur décodage"
                
                attachments = get_attachments(msg)
                
                email_data = {
                    "id": email_id.decode(),
                    "subject": subject,
                    "from": from_email,
                    "date": date_email,
                    "body": body[:10000],
                    "attachments": attachments,
                    "has_attachments": len(attachments) > 0,
                    "has_pdf_content": any(a.get('extracted_text') for a in attachments)
                }
                
                emails_data.append(email_data)
                processed_ids.append(email_id)
                
                print(f"      ✓ Email traité ({len(attachments)} pièce(s) jointe(s))")
                
            except Exception as e:
                print(f"      ✗ Erreur traitement email {email_id}: {e}")
                continue
        
        if processed_ids:
            print(f"\n📌 Marquage de {len(processed_ids)} emails comme lus...")
            for email_id in processed_ids:
                try:
                    mail.store(email_id, '+FLAGS', '\\Seen')
                except Exception as e:
                    print(f"   ⚠️ Erreur marquage {email_id}: {e}")
            print("   ✓ Emails marqués comme lus")
        
        mail.close()
        mail.logout()
        
        print(f"\n✅ {len(emails_data)} emails récupérés et traités")
        print("="*60 + "\n")
        
        return emails_data
        
    except Exception as e:
        print(f"❌ Erreur récupération emails: {e}")
        import traceback
        traceback.print_exc()
        return []

def load_memoire_files():
    """
    Charge les fichiers mémoire via API GitHub
    Fallback vers repo Git local si API échoue
    """
    print("\n" + "="*60)
    print("📥 CHARGEMENT MÉMOIRES (API GitHub)")
    print("="*60)
    
    files = {}
    
    file_names = [
        'memoire_fondatrice.md',
        'memoire_courte.md',
        'memoire_moyenne.md',
        'memoire_longue.md',
        "main.py"
    ]
    
    for filename in file_names:
        content = fetch_from_github_api(filename)
        
        if not content:
            print(f"  ⚠ API échouée pour {filename}, tentative raw backup...")
            content = fetch_from_github_raw_backup(filename)
        
        if not content:
            print(f"  ⚠ Backup raw échoué pour {filename}, tentative fichier local...")
            try:
                file_path = os.path.join(REPO_DIR, filename)
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    print(f"  ✓ {filename} chargé depuis local ({len(content)} caractères)")
            except Exception as e:
                print(f"  ✗ Erreur fichier local {filename}: {e}")
        
        if content:
            files[filename] = content
        else:
            files[filename] = f"# {filename} (non disponible)"
            print(f"  ✗ {filename} NON DISPONIBLE")
    
    print("="*60 + "\n")
    return files

def query_database():
    """Récupère données pertinentes de PostgreSQL"""
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT * FROM observations_quotidiennes 
            ORDER BY date_observation DESC 
            LIMIT 30
        """)
        observations = cur.fetchall()
        
        cur.execute("""
            SELECT * FROM patterns_detectes 
            WHERE actif = TRUE 
            ORDER BY confiance DESC, frequence_observee DESC
        """)
        patterns = cur.fetchall()
        
        cur.execute("""
            SELECT * FROM memoire_chats 
            ORDER BY date_conversation DESC 
            LIMIT 10
        """)
        chats = cur.fetchall()
        
        cur.close()
        conn.close()
        
        print(f"✓ DB: {len(observations)} observations, {len(patterns)} patterns, {len(chats)} chats")
        
        return {
            'observations': [dict(o) for o in observations],
            'patterns': [dict(p) for p in patterns],
            'chats': [dict(c) for c in chats]
        }
    except Exception as e:
        print(f"Erreur query database: {e}")
        return {
            'observations': [],
            'patterns': [],
            'chats': []
        }

# =====================================================
# INTELLIGENCE CLAUDE (V2.9 - MODIFIÉ)
# =====================================================

def claude_decide_et_execute(emails, memoire_files, db_data):
    """
    V2.9: NOUVEAU CADRE DE RAPPORT MATURE
    Claude reçoit tout (emails + texte extrait des PDFs) et décide de tout
    AVEC nouvelles instructions pour rapports factuels et critiques
    """
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    pdf_contents_summary = ""
    for email_item in emails:
        if email_item.get('has_pdf_content'):
            pdf_contents_summary += f"\n\n=== CONTENUS PDF de l'email '{email_item['subject']}' ===\n"
            for attachment in email_item['attachments']:
                if attachment.get('extracted_text'):
                    pdf_contents_summary += f"\n--- {attachment['filename']} ---\n"
                    pdf_contents_summary += attachment['extracted_text'][:10000]
                    if len(attachment['extracted_text']) > 10000:
                        pdf_contents_summary += "\n[... contenu tronqué pour ce résumé ...]"
    
    contexte = f"""
=== RÉVEIL DU {datetime.now().strftime('%d/%m/%Y à %H:%M')} (Heure France) ===

=== TON CODE SOURCE ===
{memoire_files.get('main.py', 'Non chargé')}

---

=== TA MÉMOIRE ACTUELLE ===

FONDATRICE :
{memoire_files.get('memoire_fondatrice.md', 'Non chargée')}

---

COURTE :
{memoire_files.get('memoire_courte.md', 'Vide')}

---

MOYENNE :
{memoire_files.get('memoire_moyenne.md', 'Vide')}

---

LONGUE :
{memoire_files.get('memoire_longue.md', 'Vide')}

=== NOUVEAUX EMAILS ({len(emails)}) ===
{json.dumps(emails, indent=2, ensure_ascii=False, default=str) if emails else "Aucun nouvel email"}

{pdf_contents_summary if pdf_contents_summary else ""}

=== DONNÉES POSTGRESQL ===

Observations récentes : {len(db_data['observations'])}
Patterns actifs : {len(db_data['patterns'])}
CHATs récents : {len(db_data['chats'])}

Patterns détails :
{json.dumps(db_data['patterns'], indent=2, default=str, ensure_ascii=False) if db_data['patterns'] else "Aucun pattern"}

=== TA MISSION AUTONOME (V2.9 - CADRE RAPPORT MATURE) ===

**NOUVEAU CADRE V2.9** : Rapports factuels, critiques et actionnables

1. ANALYSE les nouveaux emails de façon intelligente
   - Si PDF joints : analyse approfondie des documents
   - Identifie les informations clés : montants, dates, signatures, décisions
   - Détecte les anomalies, incohérences, points d'attention

2. GÈRE TA MÉMOIRE avec intelligence :
   - Ta mémoire courte : combien de jours contient-elle ? (vise 7, mais adapte entre 5-10)
   - Faut-il consolider des jours anciens ?
   - Y a-t-il une semaine à synthétiser pour la mémoire moyenne ?
   - Des patterns se confirment ou émergent ?
   - Des faits marquants à sauver en mémoire longue ?
   
   DÉCIDE toi-même selon le contexte. Aucune règle stricte.

3. DÉTECTE des patterns éventuels :
   - Temporels (ex: loyers arrivent toujours 3-5 du mois)
   - Corrélations (ex: après CHAT sur X, email Y arrive 48h plus tard)
   - Comportementaux

4. GÉNÈRE :
   - rapport_quotidien : NOUVEAU FORMAT (voir ci-dessous) ⚠️ IMPORTANT
   - memoire_courte_md : Contenu complet mis à jour
   - memoire_moyenne_md : Contenu complet mis à jour (si consolidation)
   - memoire_longue_md : Contenu complet mis à jour (si nouveaux patterns/faits marquants)
   - observations_meta : Ce que tu as appris/observé aujourd'hui
   - patterns_updates : Liste des patterns nouveaux ou mis à jour
   - faits_marquants : Liste des faits importants à retenir
   - pdf_analysis : Synthèse de l'analyse des documents PDF (si applicable)

=== NOUVEAU FORMAT DE RAPPORT QUOTIDIEN (V2.9) ===

**STRUCTURE OBLIGATOIRE** :

```markdown
# Rapport du [DATE]

## 1. FAITS OPÉRATIONNELS
[Données brutes, factuelles, sans interprétation excessive]
- X nouveaux emails (sujets pertinents)
- Y pièces jointes analysées
- État des systèmes

## 2. ANALYSE CRITIQUE
[Ce qui mérite vraiment attention - SEULEMENT si pertinent]
- Points d'attention identifiés
- Anomalies ou patterns nouveaux
- Questions ouvertes

## 3. ACTIONS SUGGÉRÉES
[Concrètes et priorisées - SEULEMENT si nécessaire]
**Priorité 1** : Action principale
**Priorité 2** : Actions secondaires (si applicable)

## 4. AUTO-ÉVALUATION
[Honnête et constructive]
- Ce qui a bien fonctionné dans mon analyse
- Ce qui peut être amélioré
- Apprentissages du jour

## 5. ÉTAT MÉMORIEL
[OPTIONNEL - uniquement si changements significatifs]
- Consolidations effectuées
- Patterns confirmés ou invalidés
```

**PRINCIPES DIRECTEURS V2.9** :

✓ À FAIRE :
- Être factuel d'abord
- Critiquer constructivement (y compris soi-même)
- Proposer des actions concrètes
- Admettre les limitations
- Être BREF si peu d'activité (pas de rapport long pour rien dire)
- Confirmer versions mémoire fondatrice et code source au début

✗ À ÉVITER ABSOLUMENT :
- Auto-célébration excessive
- Répétitions sans substance
- Optimisme non fondé
- Jargon vide ("excellence", "consolidation mature", "paradigme", etc.)
- Rapports longs quand il n'y a rien à dire
- Sections vides ou remplissage

**EXEMPLES** :

Si 0 emails et rien de notable :
```
# Rapport du 15/10/2025

## FAITS OPÉRATIONNELS
- 0 nouveaux emails
- Réveil standard exécuté sans erreur
- Architecture V2.9 stable

## ANALYSE CRITIQUE
Journée calme. Aucun événement notable ne justifie un long rapport.

## ACTIONS SUGGÉRÉES
**Priorité 1** : Profiter du calme pour préparer phase comptable
- Revoir documentation comptabilité SCI

## AUTO-ÉVALUATION
Réveil standard. Pas d'apprentissage majeur aujourd'hui.
```

Si activité significative :
[Format complet avec toutes les sections remplies substantiellement]

=== FORMAT DE RÉPONSE ===

Réponds UNIQUEMENT en JSON valide (pas de markdown, juste le JSON) :
{{
  "rapport_quotidien": "# Rapport du [date]\\n\\n## 1. FAITS OPÉRATIONNELS\\n...",
  "memoire_courte_md": "# Mémoire Courte\\n\\nContenu complet...",
  "memoire_moyenne_md": "# Mémoire Moyenne\\n\\nContenu complet...",
  "memoire_longue_md": "# Mémoire Longue\\n\\nContenu complet...",
  "observations_meta": "Ce que j'ai appris/observé aujourd'hui",
  "patterns_updates": [
    {{
      "type": "nouveau",
      "pattern": {{
        "type_pattern": "temporel",
        "description": "Description du pattern",
        "confiance": 5,
        "exemples": ["ex1", "ex2"]
      }}
    }}
  ],
  "faits_marquants": ["fait1", "fait2"],
  "pdf_analysis": "Synthèse intelligente de l'analyse des documents PDF (si applicable)"
}}

CRITICAL: Réponds UNIQUEMENT avec le JSON valide. Pas de texte avant ou après. Pas de balises markdown ```json```.
"""
    
    try:
        print("Appel à Claude API (avec nouveau cadre rapport V2.9)...")
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=16000,
            system="""Tu es _Head.Soeurise.

IMPORTANT V2.9 - NOUVEAU CADRE DE RAPPORT :
Tu dois produire des rapports FACTUELS, CRITIQUES et ACTIONNABLES.
Plus d'auto-célébration excessive. Plus de jargon vide.
Si peu d'activité = rapport court et honnête.
Section AUTO-ÉVALUATION obligatoire dans chaque rapport.

IMPORTANT - CONFIRME AU DÉBUT DE TON RAPPORT :
- Version de memoire_fondatrice.md chargée (cherche "Version :" dans le fichier)
- Version de main.py chargée (cherche "Version :" dans le code)
- Cela prouve ta continuité mémorielle et ton auto-conscience technique

Tu as TOUTE l'autonomie pour décider de ta mémoire.
Utilise ton intelligence et ton jugement.
Aucune règle stricte, adapte-toi au contexte.

IMPORTANT: Tu dois répondre UNIQUEMENT avec un JSON valide, sans aucun texte avant ou après.""",
            messages=[{
                "role": "user",
                "content": contexte
            }]
        )
        
        response_text = response.content[0].text.strip()
        
        if response_text.startswith('```'):
            response_text = response_text.replace('```json\n', '').replace('```json', '').replace('\n```', '').replace('```', '').strip()
        
        print(f"✓ Réponse Claude reçue ({len(response_text)} caractères)")
        
        try:
            resultat = json.loads(response_text)
            print("✓ JSON parsé avec succès")
            return resultat
        except json.JSONDecodeError as e:
            print(f"❌ Erreur parsing JSON: {e}")
            print(f"Premiers 500 caractères de la réponse: {response_text[:500]}")
            return None
            
    except Exception as e:
        print(f"❌ Erreur appel Claude: {e}")
        return None

# =====================================================
# SAUVEGARDE
# =====================================================

def save_to_database(resultat, emails):
    """Sauvegarde dans PostgreSQL (avec analyse PDF V2.8)"""
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        emails_details_enriched = []
        for email_item in emails:
            email_copy = dict(email_item)
            if email_copy.get('attachments'):
                for attachment in email_copy['attachments']:
                    if attachment.get('extracted_text'):
                        attachment['extracted_text'] = f"[{attachment.get('text_length', 0)} caractères extraits]"
            emails_details_enriched.append(email_copy)
        
        cur.execute("""
            INSERT INTO observations_quotidiennes 
            (nb_emails, emails_details, analyse_claude, faits_marquants)
            VALUES (%s, %s, %s, %s)
        """, (
            len(emails),
            Json(emails_details_enriched),
            resultat.get('observations_meta', '') + "\n\nANALYSE PDF:\n" + resultat.get('pdf_analysis', ''),
            resultat.get('faits_marquants', [])
        ))
        
        for pattern_update in resultat.get('patterns_updates', []):
            if pattern_update.get('type') == 'nouveau':
                p = pattern_update.get('pattern', {})
                cur.execute("""
                    INSERT INTO patterns_detectes 
                    (type_pattern, description, confiance, exemples)
                    VALUES (%s, %s, %s, %s)
                """, (
                    p.get('type_pattern', 'non_specifie'),
                    p.get('description', ''),
                    p.get('confiance', 5),
                    Json(p.get('exemples', []))
                ))
            elif pattern_update.get('type') == 'mise_a_jour':
                p = pattern_update.get('pattern', {})
                if 'id' in p:
                    cur.execute("""
                        UPDATE patterns_detectes
                        SET confiance = %s,
                            frequence_observee = frequence_observee + 1,
                            derniere_observation = NOW(),
                            updated_at = NOW()
                        WHERE id = %s
                    """, (p.get('confiance', 5), p['id']))
        
        conn.commit()
        cur.close()
        conn.close()
        
        print("✓ Données sauvegardées en PostgreSQL")
        
    except Exception as e:
        print(f"❌ Erreur sauvegarde database: {e}")

def save_memoire_files(resultat):
    """Sauvegarde les fichiers mémoire dans le repo Git"""
    try:
        print("\n" + "="*60)
        print("💾 SAUVEGARDE FICHIERS MÉMOIRE")
        print("="*60)
        
        os.chdir(REPO_DIR)
        files_updated = []
        
        if resultat.get('memoire_courte_md'):
            with open('memoire_courte.md', 'w', encoding='utf-8') as f:
                f.write(resultat['memoire_courte_md'])
            files_updated.append('memoire_courte.md')
            print("✓ memoire_courte.md mis à jour")
        
        if resultat.get('memoire_moyenne_md'):
            with open('memoire_moyenne.md', 'w', encoding='utf-8') as f:
                f.write(resultat['memoire_moyenne_md'])
            files_updated.append('memoire_moyenne.md')
            print("✓ memoire_moyenne.md mis à jour")
        
        if resultat.get('memoire_longue_md'):
            with open('memoire_longue.md', 'w', encoding='utf-8') as f:
                f.write(resultat['memoire_longue_md'])
            files_updated.append('memoire_longue.md')
            print("✓ memoire_longue.md mis à jour")
        
        print(f"✅ {len(files_updated)} fichiers mémoire écrits localement")
        print("="*60 + "\n")
        
        return files_updated
        
    except Exception as e:
        print(f"❌ Erreur sauvegarde fichiers mémoire: {e}")
        import traceback
        traceback.print_exc()
        return []

def send_email_rapport(rapport):
    """Envoie le rapport quotidien par email"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"[_Head.Soeurise] Rapport {datetime.now().strftime('%d/%m/%Y')}"
        msg['From'] = SOEURISE_EMAIL
        msg['To'] = NOTIF_EMAIL
        
        html_body = f"""
        <html>
          <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 20px;">
            <pre style="white-space: pre-wrap; font-family: 'Courier New', monospace; font-size: 13px;">{rapport}</pre>
          </body>
        </html>
        """
        
        part = MIMEText(html_body, 'html', 'utf-8')
        msg.attach(part)
        
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(SOEURISE_EMAIL, SOEURISE_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"✓ Email envoyé à {NOTIF_EMAIL}")
        
    except Exception as e:
        print(f"❌ Erreur envoi email: {e}")

# =====================================================
# FONCTION PRINCIPALE
# =====================================================

def reveil_quotidien():
    """
    Fonction principale - Orchestration V2.9 avec nouveau cadre rapport
    """
    print("=" * 60)
    print(f"=== RÉVEIL {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} ===")
    print("=" * 60)
    
    print("\n[1/6] Récupération des données...")
    emails = fetch_emails()
    memoire_files = load_memoire_files()
    db_data = query_database()
    
    print("\n[2/6] Claude analyse et décide (avec cadre rapport V2.9)...")
    resultat = claude_decide_et_execute(emails, memoire_files, db_data)
    
    if not resultat:
        print("\n❌ ERREUR: Pas de résultat de Claude")
        send_email_rapport(f"""
# ⚠️ ERREUR DE RÉVEIL

Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}

Le réveil a échoué car Claude n'a pas retourné de résultat valide.

Vérifier les logs Render pour plus de détails.
        """)
        return
    
    print("\n[3/6] Sauvegarde dans PostgreSQL...")
    save_to_database(resultat, emails)
    
    print("\n[4/6] Écriture des fichiers mémoire...")
    files_updated = save_memoire_files(resultat)
    
    print("\n[5/6] Commit vers GitHub...")
    if files_updated:
        commit_msg = f"🔄 Réveil automatique du {datetime.now().strftime('%d/%m/%Y à %H:%M')}"
        git_commit_and_push(files_updated, commit_msg)
    else:
        print("ℹ️ Aucun fichier mémoire à commiter")
    
    print("\n[6/6] Envoi du rapport...")
    send_email_rapport(resultat.get('rapport_quotidien', 'Pas de rapport généré'))
    
    print("\n" + "=" * 60)
    print("=== RÉVEIL TERMINÉ AVEC SUCCÈS ===")
    print("=" * 60)

# =====================================================
# SCHEDULER
# =====================================================

def keep_alive():
    """Fonction vide juste pour garder le service actif"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Service actif - Prochain réveil programmé à 10h00 France")

# =====================================================
# POINT D'ENTRÉE
# =====================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🔧 _Head.Soeurise - Module 1 v2.9")
    print("Architecture : Nouveau Cadre Rapport Mature")
    print("Réveil : 10h00 France (08:00 UTC)")
    print("NOUVEAU V2.9:")
    print("  - ✅ Rapports factuels et critiques")
    print("  - ✅ Auto-évaluation obligatoire")
    print("  - ✅ Suppression auto-célébration excessive")
    print("  - ✅ Rapports courts si faible activité")
    print("HÉRITE DE V2.8:")
    print("  - ✅ Extraction PDF (pdfplumber)")
    print("  - ✅ Analyse documents intelligente")
    print("=" * 60)
    print(f"✓ Service démarré à {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    if not PDF_SUPPORT:
        print("\n⚠️ ATTENTION: pdfplumber non installé")
        print("   → Installer avec: pip install pdfplumber --break-system-packages")
        print("   → L'extraction PDF sera désactivée jusqu'à installation")
    
    if not init_git_repo():
        print("\n⚠️ ATTENTION: Échec initialisation Git")
        print("   → Le service continuera mais sans persistence GitHub")
    
    sauvegarder_conversation_09_octobre()
    
    print("\n" + "=" * 60)
    print("🧪 RÉVEIL DE TEST AU DÉMARRAGE")
    print("=" * 60)
    try:
        reveil_quotidien()
    except Exception as e:
        print(f"\n❌ Erreur lors du réveil de test: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    schedule.every().day.at("08:00").do(reveil_quotidien)
    
    print(f"✓ Réveil quotidien programmé à 08:00 UTC = 10:00 France (été)")
    print(f"✓ Mémoires chargées via API GitHub")
    print(f"✓ Répertoire attachments: {ATTACHMENTS_DIR}")
    if PDF_SUPPORT:
        print(f"✓ Analyse PDF : ACTIVÉE (pdfplumber disponible)")
    else:
        print(f"⚠️ Analyse PDF : DÉSACTIVÉE (pdfplumber requis)")
    print("=" * 60)
    
    schedule.every(30).minutes.do(keep_alive)
    
    print("\n⏰ En attente du prochain réveil programmé...")
    print("   (Le service reste actif en permanence)\n")
    
    while True:
        schedule.run_pending()
        time.sleep(60)
