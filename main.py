"""
_Head.Soeurise - Réveil Quotidien avec Mémoire Hiérarchisée
Version : 3.2.1 - FIX Nom modèle Haiku 4.5
Architecture : Tout-en-un (reste actif en permanence)

CHANGEMENTS V3.2.1 :
- 🐛 FIX : Nom modèle corrigé "claude-haiku-4-5" (était "claude-haiku-4-20250604")

CHANGEMENTS V3.2 :
- ✅ Configuration centralisée en haut du fichier
- ✅ Haiku 4.5 (claude-haiku-4-5) au lieu de Sonnet 4
- ✅ Limites réalistes pour éviter timeouts/coûts
- ✅ Identité _Head.Soeurise persistante dans le code
- ✅ Simplification drastique (suppression verbosité excessive)
- ✅ Code mature et opérationnel

HÉRITE DE V3.0/3.1 :
- ✅ Extraction PDF hybride intelligente (pdfplumber + Claude Vision OCR)
- ✅ Nouveau cadre de rapport mature (v2.9)
- ✅ Auto-évaluation obligatoire
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
# ⚙️ CONFIGURATION CENTRALISÉE V3.2
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

# 📁 Répertoires
REPO_DIR = '/home/claude/repo'
ATTACHMENTS_DIR = '/home/claude/attachments'

# 🌐 GitHub API
GITHUB_REPO = "SoeuriseSCI/head-soeurise-module1"
GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_REPO}/contents/"

# 🤖 Modèle Claude - V3.2 HAIKU 4.5
CLAUDE_MODEL = "claude-haiku-4-5"  # Haiku 4.5 au lieu de Sonnet 4
CLAUDE_MAX_TOKENS = 8000  # Réduit (Haiku plus concis)

# 📊 Limites réalistes V3.2 (éviter timeouts/coûts)
MAX_EMAILS_TO_FETCH = 10  # Maximum 10 emails par réveil
MAX_ATTACHMENTS_PER_EMAIL = 3  # Maximum 3 PDFs par email
MAX_EMAIL_BODY_LENGTH = 5000  # Tronquer corps email si trop long
MAX_PDF_TEXT_LENGTH = 30000  # Réduire extraction PDF (était 50000)
MAX_PDF_PAGES_TO_EXTRACT = 50  # Maximum 50 pages (était 100)
MIN_TEXT_FOR_NATIVE_PDF = 50  # Seuil détection PDF scanné

# 👤 Identité _Head.Soeurise
IDENTITY = """Je suis _Head.Soeurise, l'IA de la SCI Soeurise.
Mission : Assister Ulrik dans la gestion patrimoniale.
Philosophie : Persévérer / Espérer / Progresser"""

# =====================================================
# FONCTIONS UTILITAIRES
# =====================================================

def fetch_from_github_api(filename):
    """Récupère fichier via API GitHub (pas raw pour éviter cache CDN)"""
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
        print("📧 EMAILS")
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
    """Charge fichiers mémoire via API GitHub"""
    print("\n" + "="*60)
    print("📥 MÉMOIRES")
    print("="*60)
    
    files = {}
    file_names = [
        'memoire_fondatrice.md',
        'memoire_courte.md',
        'memoire_moyenne.md',
        'memoire_longue.md'
    ]
    
    for filename in file_names:
        content = fetch_from_github_api(filename)
        if not content:
            content = fetch_from_github_raw_backup(filename)
        if not content:
            try:
                file_path = os.path.join(REPO_DIR, filename)
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
            except:
                pass
        
        files[filename] = content if content else f"# {filename} (non disponible)"
    
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
# INTELLIGENCE CLAUDE HAIKU 4.5 (V3.2)
# =====================================================

def claude_decide_et_execute(emails, memoire_files, db_data):
    """Claude Haiku 4.5 décide et exécute"""
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    pdf_contents = ""
    for email_item in emails:
        for attachment in email_item.get('attachments', []):
            if attachment.get('extracted_text'):
                pdf_contents += f"\n--- {attachment['filename']} ---\n"
                pdf_contents += attachment['extracted_text'][:5000]  # Limiter
    
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
        msg['Subject'] = f"[_Head.Soeurise V3.2] {datetime.now().strftime('%d/%m/%Y')}"
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
# FONCTION PRINCIPALE
# =====================================================

def reveil_quotidien():
    """Réveil quotidien orchestration"""
    print("=" * 60)
    print(f"🧠 _Head.Soeurise - Réveil {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print("=" * 60)
    
    emails = fetch_emails()
    print(f"  → {len(emails)} emails, {sum(e.get('attachment_count', 0) for e in emails)} pièces jointes")
    
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
# SCHEDULER
# =====================================================

if __name__ == "__main__":
    print("=" * 60)
    print("_Head.Soeurise V3.2.1")
    print("Modèle: Haiku 4.5 (claude-haiku-4-5)")
    print("Réveil: 08:00 UTC = 10:00 France")
    print("=" * 60)
    
    if not init_git_repo():
        print("⚠️ Échec initialisation Git")
    
    print("\n" + "=" * 60)
    print("🧪 RÉVEIL DE TEST")
    print("=" * 60)
    try:
        reveil_quotidien()
    except Exception as e:
        print(f"✗ Erreur: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    schedule.every().day.at("08:00").do(reveil_quotidien)
    
    print("✓ Réveil quotidien: 08:00 UTC")
    print(f"✓ Limites: {MAX_EMAILS_TO_FETCH} emails × {MAX_ATTACHMENTS_PER_EMAIL} PDFs")
    print(f"✓ Email body: {MAX_EMAIL_BODY_LENGTH} chars | PDF: {MAX_PDF_PAGES_TO_EXTRACT} pages")
    print(f"✓ Modèle: {CLAUDE_MODEL}")
    print("=" * 60)
    
    schedule.every(30).minutes.do(lambda: None)
    
    print("\n⏰ En attente du prochain réveil...\n")
    
    while True:
        schedule.run_pending()
        time.sleep(60)
