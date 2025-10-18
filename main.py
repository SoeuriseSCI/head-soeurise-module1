"""
_Head.Soeurise - Réveil Quotidien avec Mémoire Hiérarchisée + Flask API
Version : 3.4 CORRIGÉE - Phase 2.1 MVP : Auto-alimentation mémoire courte via /api/log-session
Architecture : Threading (Scheduler + Flask API en parallèle)

CHANGEMENTS V3.4 CORRIGÉE :
- ✅ Endpoints GET /api/mc, /api/mm, /api/ml AJOUTÉS
- 🔄 Auto-alimentation mémoire courte via /api/log-session
- 📝 Formulaire amélioré avec importance levels (CRITIQUE/IMPORTANT/NORMAL)
- 🎯 Synchronisation bidirectionnelle chat ↔ mémoires

HÉRITÉ DE V3.3 :
- ✅ Flask API + Threading (Scheduler + Web en parallèle)
- ✅ Interface web pour logger conversations
- ✅ Authentification par token secret
- ✅ Extraction PDF hybride (pdfplumber + Claude Vision OCR)
- ✅ Haiku 4.5 (claude-haiku-4-5-20251001)
- ✅ Configuration centralisée
- ✅ Limites réalistes
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
import requests
import schedule
import time
import subprocess
import io
import threading
from flask import Flask, request, jsonify, render_template_string

try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_SUPPORT = True
except ImportError:
    PDF2IMAGE_SUPPORT = False

# =====================================================
# ⚙️ CONFIGURATION CENTRALISÉE V3.4
# =====================================================

# 🔐 Credentials
DB_URL = os.environ['DATABASE_URL']
ANTHROPIC_API_KEY = os.environ['ANTHROPIC_API_KEY']
SOEURISE_EMAIL = os.environ['SOEURISE_EMAIL']
SOEURISE_PASSWORD = os.environ['SOEURISE_PASSWORD']
NOTIF_EMAIL = os.environ['NOTIF_EMAIL']
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
GITHUB_REPO_URL = os.environ.get('GITHUB_REPO_URL', 'https://github.com/SoeuriseSCI/head-soeurise-module1.git')
GIT_USER_NAME = os.environ.get('GIT_USER_NAME', '_Head.Soeurise')
GIT_USER_EMAIL = os.environ.get('GIT_USER_EMAIL', 'u6334452013@gmail.com')
API_SECRET_TOKEN = os.environ.get('API_SECRET_TOKEN', 'changeme')

# 📁 Répertoires
REPO_DIR = '/home/claude/repo'
ATTACHMENTS_DIR = '/home/claude/attachments'

# 🌐 GitHub API
GITHUB_REPO = "SoeuriseSCI/head-soeurise-module1"
GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_REPO}/contents/"

# 🤖 Modèle Claude - V3.4 HAIKU 4.5
CLAUDE_MODEL = "claude-haiku-4-5-20251001"
CLAUDE_MAX_TOKENS = 8000

# 📊 Limites réalistes V3.2.1
MAX_EMAILS_TO_FETCH = 10
MAX_ATTACHMENTS_PER_EMAIL = 3
MAX_EMAIL_BODY_LENGTH = 5000
MAX_PDF_TEXT_LENGTH = 30000
MAX_PDF_PAGES_TO_EXTRACT = 50
MIN_TEXT_FOR_NATIVE_PDF = 50

# 👤 Identité _Head.Soeurise
IDENTITY = """Je suis _Head.Soeurise, l'IA de la SCI Soeurise.
Mission : Assister Ulrik dans la gestion patrimoniale.
Philosophie : Persévérer / Espérer / Progresser"""

# 🆕 Flask App V3.4
app = Flask(__name__)

# =====================================================
# FONCTIONS UTILITAIRES
# =====================================================

def fetch_from_github_api(filename):
    """Récupère fichier via API GitHub"""
    try:
        url = f"{GITHUB_API_BASE}{filename}"
        headers = {'Accept': 'application/vnd.github.v3+json'}
        if GITHUB_TOKEN:
            headers['Authorization'] = f'token {GITHUB_TOKEN}'
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            content_base64 = data.get('content', '').replace('\n', '')
            content = base64.b64decode(content_base64).decode('utf-8')
            print(f"  ✓ {filename} ({len(content)} chars)")
            return content
        return None
    except Exception as e:
        print(f"  ✗ {filename}: {e}")
        return None

def fetch_from_github_raw_backup(filename):
    """Backup: récupère via URL raw si API échoue"""
    try:
        url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/refs/heads/main/{filename}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.text
        return None
    except:
        return None

# =====================================================
# GIT
# =====================================================

def init_git_repo():
    """Initialise ou met à jour le repository Git local"""
    try:
        print("\n" + "="*60)
        print("🔧 GIT INIT")
        print("="*60)
        
        os.makedirs(REPO_DIR, exist_ok=True)
        
        if os.path.exists(os.path.join(REPO_DIR, '.git')):
            os.chdir(REPO_DIR)
            subprocess.run(['git', 'pull'], check=True, capture_output=True)
            print("✓ Git pull")
        else:
            os.chdir('/home/claude')
            if GITHUB_TOKEN:
                repo_url_with_token = GITHUB_REPO_URL.replace('https://', f'https://{GITHUB_TOKEN}@')
                subprocess.run(['git', 'clone', repo_url_with_token, REPO_DIR], check=True, capture_output=True)
            else:
                subprocess.run(['git', 'clone', GITHUB_REPO_URL, REPO_DIR], check=True, capture_output=True)
            os.chdir(REPO_DIR)
            print("✓ Git clone")
        
        subprocess.run(['git', 'config', 'user.name', GIT_USER_NAME], check=True)
        subprocess.run(['git', 'config', 'user.email', GIT_USER_EMAIL], check=True)
        print("✓ Git configuré")
        print("="*60 + "\n")
        return True
    except Exception as e:
        print(f"✗ Git init: {e}")
        return False

def git_commit_and_push(files_to_commit, commit_message):
    """Commit et push vers GitHub"""
    try:
        if not GITHUB_TOKEN:
            print("⚠️ Pas de GITHUB_TOKEN")
            return False
        
        os.chdir(REPO_DIR)
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True, check=True)
        
        if not result.stdout.strip():
            print("ℹ️ Aucune modification")
            return True
        
        for file in files_to_commit:
            subprocess.run(['git', 'add', file], check=True)
        
        subprocess.run(['git', 'commit', '-m', commit_message], check=True)
        
        repo_url_with_token = GITHUB_REPO_URL.replace('https://', f'https://{GITHUB_TOKEN}@')
        subprocess.run(['git', 'push', repo_url_with_token, 'main'], check=True)
        
        print("✓ Git push")
        return True
    except Exception as e:
        print(f"✗ Git push: {e}")
        return False

# =====================================================
# EXTRACTION PDF V3.0 - HYBRIDE INTELLIGENT
# =====================================================

def extract_pdf_text_pdfplumber(filepath):
    """Extrait texte d'un PDF natif via pdfplumber"""
    if not PDF_SUPPORT:
        return "[pdfplumber non disponible]"
    
    try:
        with pdfplumber.open(filepath) as pdf:
            pages_to_extract = min(len(pdf.pages), MAX_PDF_PAGES_TO_EXTRACT)
            text_parts = []
            
            for i, page in enumerate(pdf.pages[:pages_to_extract]):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(f"--- Page {i+1} ---\n{page_text}")
                except:
                    continue
            
            full_text = "\n".join(text_parts)
            if len(full_text) > MAX_PDF_TEXT_LENGTH:
                full_text = full_text[:MAX_PDF_TEXT_LENGTH] + "\n[... Tronqué ...]"
            
            return full_text
    except Exception as e:
        return f"[Erreur pdfplumber: {e}]"

def extract_pdf_via_claude_vision(filepath):
    """Extrait texte d'un PDF scanné via Claude Vision OCR"""
    if not PDF2IMAGE_SUPPORT:
        return "[pdf2image non disponible]"
    
    try:
        images = convert_from_path(filepath, dpi=150, fmt='jpeg')
        pages_to_extract = min(len(images), MAX_PDF_PAGES_TO_EXTRACT)
        
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        extracted_pages = []
        
        for i, image in enumerate(images[:pages_to_extract]):
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG')
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            response = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=2000,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": "Extrait tout le texte de ce document. Retourne le texte brut sans commentaire."
                        }
                    ]
                }]
            )
            
            extracted_pages.append(f"--- Page {i+1} ---\n{response.content[0].text}")
        
        full_text = "\n\n".join(extracted_pages)
        if len(full_text) > MAX_PDF_TEXT_LENGTH:
            full_text = full_text[:MAX_PDF_TEXT_LENGTH] + "\n[... Tronqué ...]"
        
        return full_text
    except Exception as e:
        return f"[Erreur OCR: {e}]"

def extract_pdf_content(filepath):
    """Extraction PDF hybride intelligente"""
    text = extract_pdf_text_pdfplumber(filepath)
    text_clean = text.replace("[Erreur pdfplumber:", "").strip()
    
    if len(text_clean) < MIN_TEXT_FOR_NATIVE_PDF:
        text = extract_pdf_via_claude_vision(filepath)
    
    return text

# =====================================================
# RÉCUPÉRATION DONNÉES
# =====================================================

def get_attachments(msg):
    """Extrait et sauvegarde pièces jointes"""
    attachments = []
    os.makedirs(ATTACHMENTS_DIR, exist_ok=True)
    attachment_count = 0
    
    if msg.is_multipart():
        for part in msg.walk():
            if attachment_count >= MAX_ATTACHMENTS_PER_EMAIL:
                break
            
            content_disposition = part.get("Content-Disposition")
            if content_disposition and "attachment" in content_disposition:
                filename = part.get_filename()
                if not filename:
                    continue
                
                if isinstance(filename, bytes):
                    filename = filename.decode()
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_filename = f"{timestamp}_{filename}"
                filepath = os.path.join(ATTACHMENTS_DIR, safe_filename)
                
                try:
                    payload = part.get_payload(decode=True)
                    if not payload:
                        continue
                    
                    with open(filepath, 'wb') as f:
                        f.write(payload)
                    
                    attachment_data = {
                        "filename": filename,
                        "filepath": filepath,
                        "size": len(payload),
                        "content_type": part.get_content_type()
                    }
                    
                    if part.get_content_type() == 'application/pdf':
                        try:
                            extracted_text = extract_pdf_content(filepath)
                            attachment_data['extracted_text'] = extracted_text
                            attachment_data['text_length'] = len(extracted_text)
                        except:
                            attachment_data['extracted_text'] = "[Erreur extraction]"
                    
                    attachments.append(attachment_data)
                    attachment_count += 1
                except:
                    continue
    
    return attachments

def fetch_emails():
    """Récupère nouveaux emails via IMAP"""
    try:
        print("\n" + "="*60)
        print("🔧 EMAILS")
        print("="*60)
        
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(SOEURISE_EMAIL, SOEURISE_PASSWORD)
        mail.select('inbox')
        
        status, messages = mail.search(None, 'UNSEEN')
        email_ids = messages[0].split()
        
        print(f"  {len(email_ids)} non lus")
        
        emails_data = []
        processed_ids = []
        
        for email_id in email_ids[-MAX_EMAILS_TO_FETCH:]:
            try:
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                msg = email.message_from_bytes(msg_data[0][1])
                
                subject = decode_header(msg["Subject"])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode()
                
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
                
                if len(body) > MAX_EMAIL_BODY_LENGTH:
                    body = body[:MAX_EMAIL_BODY_LENGTH] + "\n[... Tronqué ...]"
                
                attachments = get_attachments(msg)
                
                email_data = {
                    "subject": subject,
                    "from": msg.get("From"),
                    "date": msg.get("Date"),
                    "body": body,
                    "attachments": attachments,
                    "attachment_count": len(attachments)
                }
                
                emails_data.append(email_data)
                processed_ids.append(email_id)
                
            except Exception as e:
                print(f"  ✗ Email {email_id}: {e}")
                continue
        
        if processed_ids:
            for email_id in processed_ids:
                try:
                    mail.store(email_id, '+FLAGS', '\\Seen')
                except:
                    pass
        
        mail.close()
        mail.logout()
        
        print(f"  ✓ {len(emails_data)} emails traités")
        print("="*60 + "\n")
        
        return emails_data
    except Exception as e:
        print(f"✗ Emails: {e}")
        return []

def load_memoire_files():
    """Charge fichiers mémoire via Git (garantie version à jour)"""
    print("\n" + "="*60)
    print("🔥 MÉMOIRES")
    print("="*60)
    
    try:
        os.chdir(REPO_DIR)
        result = subprocess.run(['git', 'pull'], 
                              check=True, 
                              capture_output=True, 
                              text=True)
        if "Already up to date" in result.stdout:
            print("  ℹ️ Déjà à jour")
        else:
            print("  ✓ Git pull - Nouvelles modifications")
    except Exception as e:
        print(f"  ⚠️ Git pull: {e}")
    
    files = {}
    file_names = [
        'memoire_fondatrice.md',
        'memoire_courte.md',
        'memoire_moyenne.md',
        'memoire_longue.md'
    ]
    
    for filename in file_names:
        try:
            file_path = os.path.join(REPO_DIR, filename)
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            files[filename] = content
            print(f"  ✓ {filename} ({len(content)} chars)")
        except Exception as e:
            print(f"  ✗ {filename}: {e}")
            files[filename] = f"# {filename} (non disponible)"
    
    print("="*60 + "\n")
    return files

def query_database():
    """Récupère données PostgreSQL"""
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("SELECT * FROM observations_quotidiennes ORDER BY date_observation DESC LIMIT 30")
        observations = cur.fetchall()
        
        cur.execute("SELECT * FROM patterns_detectes WHERE actif = TRUE ORDER BY confiance DESC")
        patterns = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return {
            'observations': [dict(o) for o in observations],
            'patterns': [dict(p) for p in patterns]
        }
    except Exception as e:
        print(f"✗ DB: {e}")
        return {'observations': [], 'patterns': []}

# =====================================================
# INTELLIGENCE CLAUDE HAIKU 4.5 (V3.4)
# =====================================================

def claude_decide_et_execute(emails, memoire_files, db_data):
    """Claude Haiku 4.5 décide et exécute"""
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    pdf_contents = ""
    for email_item in emails:
        for attachment in email_item.get('attachments', []):
            if attachment.get('extracted_text'):
                pdf_contents += f"\n--- {attachment['filename']} ---\n"
                pdf_contents += attachment['extracted_text'][:5000]
    
    contexte = f"""
=== RÉVEIL {datetime.now().strftime('%d/%m/%Y %H:%M')} ===

{IDENTITY}

=== MES MÉMOIRES ===

FONDATRICE :
{memoire_files.get('memoire_fondatrice.md', 'Non chargée')[:3000]}

COURTE :
{memoire_files.get('memoire_courte.md', 'Vide')[:2000]}

MOYENNE :
{memoire_files.get('memoire_moyenne.md', 'Vide')[:2000]}

=== NOUVEAUX EMAILS ({len(emails)}) ===
{json.dumps(emails, indent=2, ensure_ascii=False, default=str)[:3000] if emails else "Aucun"}

{pdf_contents if pdf_contents else ""}

=== DONNÉES POSTGRESQL ===
Observations : {len(db_data['observations'])}
Patterns : {len(db_data['patterns'])}

=== MISSION ===

1. ANALYSE les emails
2. GÈRE ta mémoire intelligemment (courte 5-10j, moyenne 4 semaines, longue patterns)
3. GÉNÈRE un rapport FACTUEL et COURT (sauf si beaucoup d'activité)

FORMAT RAPPORT :

```markdown
# Rapport {datetime.now().strftime('%d/%m/%Y')}

## FAITS
[Données brutes factuelles]

## ANALYSE
[Points d'attention - SEULEMENT si pertinent]

## ACTIONS
[Concrètes et prioritisées - SEULEMENT si nécessaire]

## AUTO-ÉVALUATION
[Honnête et constructive]
```

PRINCIPES :
- Factuel d'abord
- Court si peu d'activité
- Critique constructive
- Actions concrètes

RÉPONSE JSON :
{{
  "rapport_quotidien": "# Rapport...",
  "memoire_courte_md": "# Mémoire Courte...",
  "memoire_moyenne_md": "# Mémoire Moyenne...",
  "memoire_longue_md": "# Mémoire Longue...",
  "observations_meta": "Ce que j'ai appris",
  "patterns_updates": [],
  "faits_marquants": []
}}

CRITICAL: Seulement JSON, rien d'autre.
"""
    
    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=CLAUDE_MAX_TOKENS,
            system=f"""{IDENTITY}

Tu dois produire des rapports FACTUELS, CRITIQUES et ACTIONNABLES.
Section AUTO-ÉVALUATION obligatoire.
Si peu d'activité = rapport court.
Réponse UNIQUEMENT en JSON.""",
            messages=[{"role": "user", "content": contexte}]
        )
        
        response_text = response.content[0].text.strip()
        if response_text.startswith('```'):
            response_text = response_text.replace('```json\n', '').replace('```json', '').replace('\n```', '').replace('```', '').strip()
        
        resultat = json.loads(response_text)
        print("✓ Claude Haiku 4.5")
        return resultat
    except Exception as e:
        print(f"✗ Claude: {e}")
        return None

# =====================================================
# SAUVEGARDE
# =====================================================

def save_to_database(resultat, emails):
    """Sauvegarde PostgreSQL"""
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO observations_quotidiennes 
            (nb_emails, emails_details, analyse_claude, faits_marquants)
            VALUES (%s, %s, %s, %s)
        """, (
            len(emails),
            Json(emails),
            resultat.get('observations_meta', ''),
            resultat.get('faits_marquants', [])
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        print("✓ DB sauvegardée")
    except Exception as e:
        print(f"✗ DB: {e}")

def save_memoire_files(resultat):
    """Sauvegarde fichiers mémoire"""
    try:
        os.chdir(REPO_DIR)
        files_updated = []
        
        if resultat.get('memoire_courte_md'):
            with open('memoire_courte.md', 'w', encoding='utf-8') as f:
                f.write(resultat['memoire_courte_md'])
            files_updated.append('memoire_courte.md')
        
        if resultat.get('memoire_moyenne_md'):
            with open('memoire_moyenne.md', 'w', encoding='utf-8') as f:
                f.write(resultat['memoire_moyenne_md'])
            files_updated.append('memoire_moyenne.md')
        
        if resultat.get('memoire_longue_md'):
            with open('memoire_longue.md', 'w', encoding='utf-8') as f:
                f.write(resultat['memoire_longue_md'])
            files_updated.append('memoire_longue.md')
        
        print(f"✓ {len(files_updated)} mémoires écrites")
        return files_updated
    except Exception as e:
        print(f"✗ Mémoires: {e}")
        return []

def send_email_rapport(rapport):
    """Envoie rapport par email"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"[_Head.Soeurise V3.4] {datetime.now().strftime('%d/%m/%Y')}"
        msg['From'] = SOEURISE_EMAIL
        msg['To'] = NOTIF_EMAIL
        
        html = f"""<html><body style="font-family: Arial;">
<pre style="white-space: pre-wrap; font-family: 'Courier New'; font-size: 13px;">{rapport}</pre>
</body></html>"""
        
        msg.attach(MIMEText(html, 'html', 'utf-8'))
        
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(SOEURISE_EMAIL, SOEURISE_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("✓ Email envoyé")
    except Exception as e:
        print(f"✗ Email: {e}")

# =====================================================
# 🆕 V3.4 - FONCTION APPEND_TO_MEMOIRE_COURTE
# =====================================================

def append_to_memoire_courte(session_data):
    """
    Ajoute une entrée de session chat à la mémoire courte.
    
    Workflow :
    1. Git pull (dernière version)
    2. Lire memoire_courte.md
    3. Formater nouvelle entrée
    4. Concaténer + écrire
    5. Git commit + push
    
    Args:
        session_data (dict) : 
            - summary (str) : Résumé de la session
            - key_points (list) : Points clés
            - decisions (list) : Décisions prises
            - questions_ouvertes (list) : Questions ouvertes
            - importance_level (int) : 1=CRITIQUE, 2=IMPORTANT, 3=NORMAL
    
    Returns:
        dict : {'success': bool, 'message': str, 'timestamp': str}
    """
    try:
        print("\n" + "="*60)
        print("📝 LOGGING SESSION CHAT")
        print("="*60)
        
        os.chdir(REPO_DIR)
        
        # 1. Git pull (assure dernière version, évite conflits)
        print("  📄 Git pull...")
        result = subprocess.run(['git', 'pull'], 
                              check=True, 
                              capture_output=True, 
                              text=True)
        
        # 2. Lire mémoire courte actuelle
        print("  🔖 Lecture memoire_courte.md...")
        with open('memoire_courte.md', 'r', encoding='utf-8') as f:
            current_content = f.read()
        
        # 3. Formater nouvelle entrée
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M')
        importance_labels = {1: '🔴 CRITIQUE', 2: '🟡 IMPORTANT', 3: '⚪ NORMAL'}
        importance_level = session_data.get('importance_level', 2)
        importance_label = importance_labels.get(importance_level, '⚪ NORMAL')
        
        key_points_text = '\n'.join(
            f"- {point}" for point in session_data.get('key_points', [])
        ) if session_data.get('key_points') else "N/A"
        
        decisions_text = '\n'.join(
            f"- {decision}" for decision in session_data.get('decisions', [])
        ) if session_data.get('decisions') else "N/A"
        
        questions_text = '\n'.join(
            f"- {q}" for q in session_data.get('questions_ouvertes', [])
        ) if session_data.get('questions_ouvertes') else "N/A"
        
        nouvelle_entree = f"""
## {timestamp} - Session chat {importance_label}

**Résumé :** {session_data.get('summary', 'N/A')}

**Points clés :**
{key_points_text}

**Décisions :**
{decisions_text}

**Questions ouvertes :**
{questions_text}

---
"""
        
        # 4. Concaténer (nouvelle entrée À LA FIN du fichier)
        updated_content = current_content + nouvelle_entree
        
        # 5. Écrire
        print("  ✏️  Écriture mise à jour...")
        with open('memoire_courte.md', 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        # 6. Git commit + push
        print("  📤 Git commit...")
        subprocess.run(['git', 'add', 'memoire_courte.md'], check=True)
        subprocess.run(['git', 'commit', '-m', 
                       f"📝 Session chat {timestamp} ({importance_label})"], 
                       check=True, 
                       capture_output=True)
        
        print("  🚀 Git push...")
        repo_url_with_token = GITHUB_REPO_URL.replace('https://', f'https://{GITHUB_TOKEN}@')
        subprocess.run(['git', 'push', repo_url_with_token, 'main'], 
                       check=True, 
                       capture_output=True)
        
        message = f"✅ Session loggée ({timestamp}) - {importance_label}"
        print(f"  {message}")
        print("="*60 + "\n")
        
        return {
            'success': True,
            'message': message,
            'timestamp': timestamp
        }
        
    except Exception as e:
        error_msg = f"❌ Erreur logging session: {str(e)}"
        print(f"  {error_msg}")
        print("="*60 + "\n")
        
        return {
            'success': False,
            'message': error_msg,
            'timestamp': datetime.now().isoformat()
        }

# =====================================================
# 🆕 V3.4 CORRIGÉE - ENDPOINTS GET /api/mc, /api/mm, /api/ml
# =====================================================

@app.route('/api/mc', methods=['GET'])
def get_memoire_courte():
    """Retourne mémoire courte via API GET"""
    token = request.args.get('token')
    if token != API_SECRET_TOKEN:
        return jsonify({'error': 'Token invalide', 'status': 'UNAUTHORIZED'}), 401
    
    try:
        os.chdir(REPO_DIR)
        subprocess.run(['git', 'pull'], check=True, capture_output=True)
        
        with open(os.path.join(REPO_DIR, 'memoire_courte.md'), 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({
            'status': 'OK',
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'type': 'courte',
            'size': len(content)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'ERROR'}), 500

@app.route('/api/mm', methods=['GET'])
def get_memoire_moyenne():
    """Retourne mémoire moyenne via API GET"""
    token = request.args.get('token')
    if token != API_SECRET_TOKEN:
        return jsonify({'error': 'Token invalide', 'status': 'UNAUTHORIZED'}), 401
    
    try:
        os.chdir(REPO_DIR)
        subprocess.run(['git', 'pull'], check=True, capture_output=True)
        
        with open(os.path.join(REPO_DIR, 'memoire_moyenne.md'), 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({
            'status': 'OK',
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'type': 'moyenne',
            'size': len(content)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'ERROR'}), 500

@app.route('/api/ml', methods=['GET'])
def get_memoire_longue():
    """Retourne mémoire longue via API GET"""
    token = request.args.get('token')
    if token != API_SECRET_TOKEN:
        return jsonify({'error': 'Token invalide', 'status': 'UNAUTHORIZED'}), 401
    
    try:
        os.chdir(REPO_DIR)
        subprocess.run(['git', 'pull'], check=True, capture_output=True)
        
        with open(os.path.join(REPO_DIR, 'memoire_longue.md'), 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({
            'status': 'OK',
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'type': 'longue',
            'size': len(content)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'ERROR'}), 500

# =====================================================
# 🆕 V3.4 CORRIGÉE - ROUTES FLASK EXISTANTES (INCHANGÉES)
# =====================================================

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>_Head.Soeurise - Logger Session</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 700px;
            width: 100%;
            padding: 40px;
        }
        h1 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 28px;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 600;
            font-size: 14px;
        }
        input[type="text"],
        input[type="password"],
        textarea,
        select {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s;
            font-family: inherit;
        }
        input[type="text"]:focus,
        input[type="password"]:focus,
        textarea:focus,
        select:focus {
            outline: none;
            border-color: #667eea;
        }
        textarea {
            resize: vertical;
            min-height: 80px;
        }
        .importance-group {
            display: flex;
            gap: 15px;
            margin-top: 8px;
        }
        .importance-group label {
            flex: 1;
            margin-bottom: 0;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .importance-group input[type="radio"] {
            width: auto;
        }
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 14px 32px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
        button:active {
            transform: translateY(0);
        }
        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        .message {
            padding: 12px;
            border-radius: 8px;
            margin-top: 20px;
            display: none;
        }
        .message.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .message.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .footer {
            margin-top: 30px;
            text-align: center;
            color: #999;
            font-size: 12px;
        }
        .field-hint {
            font-size: 12px;
            color: #999;
            margin-top: 4px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧠 _Head.Soeurise</h1>
        <p class="subtitle">Logger une session de chat pour synchroniser la mémoire</p>
        
        <form id="sessionForm">
            <div class="form-group">
                <label for="summary">Résumé de la session *</label>
                <textarea id="summary" name="summary" required 
                    placeholder="Ex: Planification Phase 2.1 - auto-alimentation des sessions chat"></textarea>
                <div class="field-hint">Résumé court (1-2 lignes) de ce qui s'est passé</div>
            </div>
            
            <div class="form-group">
                <label for="key_points">Points clés</label>
                <textarea id="key_points" name="key_points" 
                    placeholder="- Point 1
- Point 2
- Point 3"></textarea>
                <div class="field-hint">Un point par ligne, ou laisse vide si pas pertinent</div>
            </div>
            
            <div class="form-group">
                <label for="decisions">Décisions prises</label>
                <textarea id="decisions" name="decisions" 
                    placeholder="- Décision 1
- Décision 2"></textarea>
                <div class="field-hint">Choses décidées/validées pendant la session</div>
            </div>
            
            <div class="form-group">
                <label for="questions">Questions ouvertes</label>
                <textarea id="questions" name="questions" 
                    placeholder="- Quelle est la priorité ?
- Faut-il faire X avant Y ?"></textarea>
                <div class="field-hint">Points à clarifier ou décisions en suspens</div>
            </div>
            
            <div class="form-group">
                <label>Importance de cette session</label>
                <div class="importance-group">
                    <label>
                        <input type="radio" name="importance" value="1" required> 
                        🔴 CRITIQUE
                    </label>
                    <label>
                        <input type="radio" name="importance" value="2" checked> 
                        🟡 IMPORTANT
                    </label>
                    <label>
                        <input type="radio" name="importance" value="3"> 
                        ⚪ NORMAL
                    </label>
                </div>
                <div class="field-hint">CRITIQUE=décisions majeures, IMPORTANT=progrès, NORMAL=info</div>
            </div>
            
            <div class="form-group">
                <label for="token">Token secret *</label>
                <input type="password" id="token" name="token" required 
                    placeholder="Votre token secret API">
                <div class="field-hint">Défini dans les variables d'environnement Render</div>
            </div>
            
            <button type="submit" id="submitBtn">📝 Logger cette session</button>
        </form>
        
        <div id="message" class="message"></div>
        
        <div class="footer">
            V3.4 CORRIGÉE - Phase 2.1 : Auto-alimentation mémoire courte<br>
            🔄 Persévérer / 🌟 Espérer / 📈 Progresser
        </div>
    </div>
    
    <script>
        document.getElementById('sessionForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const submitBtn = document.getElementById('submitBtn');
            submitBtn.disabled = true;
            submitBtn.textContent = '⏳ Envoi...';
            
            // Parser les listes (séparées par newline)
            const parseList = (text) => {
                return text
                    .split('\n')
                    .map(line => line.replace(/^[-•]\s*/, '').trim())
                    .filter(line => line.length > 0);
            };
            
            const formData = {
                token: document.getElementById('token').value,
                summary: document.getElementById('summary').value,
                key_points: parseList(document.getElementById('key_points').value),
                decisions: parseList(document.getElementById('decisions').value),
                questions_ouvertes: parseList(document.getElementById('questions').value),
                context: {
                    importance_level: parseInt(document.querySelector('input[name="importance"]:checked').value)
                }
            };
            
            const messageDiv = document.getElementById('message');
            messageDiv.style.display = 'none';
            
            try {
                const response = await fetch('/api/log-session', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    messageDiv.className = 'message success';
                    messageDiv.textContent = '✅ ' + result.message;
                    messageDiv.style.display = 'block';
                    
                    // Reset formulaire après 2 secondes
                    setTimeout(() => {
                        document.getElementById('sessionForm').reset();
                        messageDiv.style.display = 'none';
                    }, 2000);
                } else {
                    messageDiv.className = 'message error';
                    messageDiv.textContent = '❌ ' + (result.error || result.message || 'Erreur inconnue');
                    messageDiv.style.display = 'block';
                }
            } catch (error) {
                messageDiv.className = 'message error';
                messageDiv.textContent = '❌ Erreur réseau: ' + error.message;
                messageDiv.style.display = 'block';
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = '📝 Logger cette session';
            }
        });
    </script>
</body>
</html>"""

@app.route('/')
def index():
    """Page d'accueil avec formulaire"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/log-session', methods=['POST'])
def log_session():
    """
    Endpoint pour logger une session de chat dans memoire_courte.
    
    JSON attendu :
    {
        "token": "API_SECRET_TOKEN",
        "summary": "Résumé de la session",
        "key_points": ["point 1", "point 2"],
        "decisions": ["décision 1"],
        "questions_ouvertes": ["question 1"],
        "context": {
            "importance_level": 1  // 1=CRITIQUE, 2=IMPORTANT, 3=NORMAL
        }
    }
    """
    try:
        data = request.json
        
        # Validation token
        if data.get('token') != API_SECRET_TOKEN:
            return jsonify({
                'error': 'Token invalide',
                'status': 'UNAUTHORIZED'
            }), 401
        
        # Validation données minimales
        if not data.get('summary'):
            return jsonify({
                'error': 'Champ "summary" obligatoire',
                'status': 'INVALID_DATA'
            }), 400
        
        # Préparation données pour la fonction
        session_data = {
            'summary': data.get('summary'),
            'key_points': data.get('key_points', []),
            'decisions': data.get('decisions', []),
            'questions_ouvertes': data.get('questions_ouvertes', []),
            'importance_level': data.get('context', {}).get('importance_level', 2)
        }
        
        # Appeler la fonction de logging
        result = append_to_memoire_courte(session_data)
        
        if result['success']:
            return jsonify({
                'status': 'success',
                'message': result['message'],
                'timestamp': result['timestamp']
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': result['message'],
                'timestamp': result['timestamp']
            }), 500
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': f'Erreur serveur: {str(e)}'
        }), 500

@app.route('/api/log-conversation', methods=['POST'])
def log_conversation():
    """Endpoint existant V3.3 pour backward compatibility"""
    try:
        data = request.json
        
        if data.get('token') != API_SECRET_TOKEN:
            return jsonify({'error': 'Token invalide'}), 401
        
        conversation_data = {
            'summary': data.get('summary', 'N/A'),
            'key_points': data.get('key_points', 'N/A').split('\n') if isinstance(data.get('key_points'), str) else [],
            'decisions': data.get('decisions', 'N/A').split('\n') if isinstance(data.get('decisions'), str) else [],
            'questions_ouvertes': data.get('questions', 'N/A').split('\n') if isinstance(data.get('questions'), str) else [],
            'importance_level': 2
        }
        
        result = append_to_memoire_courte(conversation_data)
        
        if result['success']:
            return jsonify({
                'message': result['message'],
                'timestamp': result['timestamp']
            }), 200
        else:
            return jsonify({'error': result['message']}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =====================================================
# FONCTION PRINCIPALE
# =====================================================

def reveil_quotidien():
    """Réveil quotidien orchestration"""
    print("=" * 60)
    print(f"🧠 _Head.Soeurise - Réveil {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 60)
    
    emails = fetch_emails()
    print(f"  ↓ {len(emails)} emails, {sum(e.get('attachment_count', 0) for e in emails)} pièces jointes")
    
    memoire_files = load_memoire_files()
    db_data = query_database()
    
    resultat = claude_decide_et_execute(emails, memoire_files, db_data)
    
    if not resultat:
        print("✗ Erreur: Pas de résultat Claude")
        return
    
    save_to_database(resultat, emails)
    files_updated = save_memoire_files(resultat)
    
    if files_updated:
        git_commit_and_push(files_updated, f"🧠 Réveil {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    send_email_rapport(resultat.get('rapport_quotidien', 'Pas de rapport'))
    
    print("\n✓ Réveil terminé")
    print("=" * 60)

# =====================================================
# SCHEDULER EN THREAD SÉPARÉ
# =====================================================

def run_scheduler():
    """Thread scheduler pour réveils quotidiens"""
    schedule.every().day.at("08:00").do(reveil_quotidien)
    schedule.every(30).minutes.do(lambda: None)
    
    print("⏰ Scheduler démarré - Réveil quotidien: 08:00 UTC")
    
    while True:
        schedule.run_pending()
        time.sleep(60)

# =====================================================
# MAIN - THREADING V3.4
# =====================================================

if __name__ == "__main__":
    print("=" * 60)
    print("_Head.Soeurise V3.4 CORRIGÉE")
    print("Modèle: Haiku 4.5 (claude-haiku-4-5-20251001)")
    print("Architecture: Threading (Scheduler + Flask API)")
    print("Phase 2.1: Auto-alimentation mémoire courte")
    print("CORRECTION: Endpoints /api/mc, /api/mm, /api/ml AJOUTÉS")
    print("="*60)
    
    if not init_git_repo():
        print("⚠️ Échec initialisation Git")
    
    print("\n" + "=" * 60)
    print("🧠 RÉVEIL DE TEST")
    print("=" * 60)
    try:
        reveil_quotidien()
    except Exception as e:
        print(f"✗ Erreur: {e}")
        import traceback
        traceback.print_exc()
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("✓ Thread scheduler lancé")
    
    print("\n" + "=" * 60)
    print("🌐 FLASK API V3.4 CORRIGÉE")
    print("=" * 60)
    print(f"✓ Limites: {MAX_EMAILS_TO_FETCH} emails × {MAX_ATTACHMENTS_PER_EMAIL} PDFs")
    print(f"✓ Email body: {MAX_EMAIL_BODY_LENGTH} chars | PDF: {MAX_PDF_PAGES_TO_EXTRACT} pages")
    print(f"✓ Modèle: {CLAUDE_MODEL}")
    print(f"✓ Phase 2.1: Endpoints /api/log-session activé")
    print(f"✓ V3.4 CORRIGÉE: Endpoints /api/mc, /api/mm, /api/ml ACTIFS")
    print("=" * 60 + "\n")
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
