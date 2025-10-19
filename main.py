"""
_Head.Soeurise - Réveil Quotidien avec Mémoire Hiérarchisée + Flask API
Version : 3.5.3 - Auto-log via GET /api/mc?action=log&summary=...
Architecture : Threading (Scheduler + Flask API en parallèle)

CHANGEMENTS V3.5.3 :
- ✅ Endpoint GET /api/mc étendu : accepte action=log pour auto-persistence
- ✅ Paramètres : summary, key_points[], decisions[], questions_ouvertes[], importance_level
- ✅ Auto-ajoute une entrée à memoire_courte.md et git push
- ✅ Retourne le contenu mis à jour

HÉRITÉ DE V3.5.2 :
- ✅ GET /api/mc, /api/mm, /api/ml pour lire mémoires
- ✅ Flask API + Threading (Scheduler + Web en parallèle)
- ✅ Haiku 4.5 (claude-haiku-4-5-20251001)
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
# ⚙️ CONFIGURATION CENTRALISÉE V3.5.3
# =====================================================

# 🔓 Credentials
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

# 🌍 Répertoires
REPO_DIR = '/home/claude/repo'
ATTACHMENTS_DIR = '/home/claude/attachments'

# 🌐 GitHub API
GITHUB_REPO = "SoeuriseSCI/head-soeurise-module1"
GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_REPO}/contents/"

# 🤖 Modèle Claude - V3.5.3 HAIKU 4.5
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

# 🆕 Flask App V3.5.3
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
        subprocess.run(['git', 'push', repo_url_with_token, 'HEAD:main'], check=True)
        
        print("✓ Git push")
        return True
    except Exception as e:
        print(f"✗ Git push: {e}")
        return False

# =====================================================
# 🆕 V3.5.3 - ENDPOINTS GET CON AUTO-LOG SUPPORT
# =====================================================

@app.route('/api/mc', methods=['GET'])
def get_memoire_courte():
    """
    GET /api/mc - Lire mémoire courte
    Optionnel: action=log pour auto-persist session
    
    Usage lecture seule:
        GET /api/mc?token=XXX
    
    Usage auto-log:
        GET /api/mc?token=XXX&action=log&summary=Résumé&key_points=p1&key_points=p2&decisions=d1&importance_level=1
    """
    token = request.args.get('token')
    if token != API_SECRET_TOKEN:
        return jsonify({'error': 'Token invalide', 'status': 'UNAUTHORIZED'}), 401
    
    # ============================================
    # 🆕 ÉTAPE 1 : Vérifier si c'est un appel "log"
    # ============================================
    action = request.args.get('action')
    if action == 'log':
        print("\n" + "="*60)
        print("🧠 AUTO-LOG VIA GET /api/mc")
        print("="*60)
        
        try:
            # Récupérer les paramètres
            summary = request.args.get('summary', 'N/A')
            key_points = request.args.getlist('key_points')
            decisions = request.args.getlist('decisions')
            questions_ouvertes = request.args.getlist('questions_ouvertes')
            importance_level = int(request.args.get('importance_level', 2))
            
            print(f"  📝 Summary: {summary[:50]}...")
            print(f"  📍 Points: {len(key_points)}")
            print(f"  ✅ Décisions: {len(decisions)}")
            print(f"  ❓ Questions: {len(questions_ouvertes)}")
            print(f"  ⚡ Importance: {importance_level}")
            
            # ============================================
            # Git pull pour version la plus récente
            # ============================================
            os.chdir(REPO_DIR)
            subprocess.run(['git', 'pull'], check=True, capture_output=True)
            print("  ✓ Git pull")
            
            # ============================================
            # Formater la nouvelle entrée
            # ============================================
            timestamp = datetime.now().strftime('%d/%m/%Y %H:%M')
            importance_labels = {1: '🔴 CRITIQUE', 2: '🟡 IMPORTANT', 3: '⚪ NORMAL'}
            importance_label = importance_labels.get(importance_level, '⚪ NORMAL')
            
            key_points_text = '\n'.join([f"- {p}" for p in key_points]) if key_points else "N/A"
            decisions_text = '\n'.join([f"- {d}" for d in decisions]) if decisions else "N/A"
            questions_text = '\n'.join([f"- {q}" for q in questions_ouvertes]) if questions_ouvertes else "N/A"
            
            nouvelle_entree = f"""## {timestamp} - Session chat {importance_label}

**Résumé :** {summary}

**Points clés :**
{key_points_text}

**Décisions :**
{decisions_text}

**Questions ouvertes :**
{questions_text}

---
"""
            
            # ============================================
            # Lire, modifier, écrire memoire_courte.md
            # ============================================
            memoire_path = os.path.join(REPO_DIR, 'memoire_courte.md')
            with open(memoire_path, 'r', encoding='utf-8') as f:
                current_content = f.read()
            
            new_content = current_content + nouvelle_entree
            
            with open(memoire_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print("  ✓ Fichier modifié")
            
            # ============================================
            # Git commit + push
            # ============================================
            subprocess.run(['git', 'add', 'memoire_courte.md'], check=True)
            subprocess.run(['git', 'commit', '-m', f"🧠 Auto-log {timestamp} ({importance_label})"], 
                         check=True, capture_output=True)
            
            repo_url_with_token = GITHUB_REPO_URL.replace('https://', f'https://{GITHUB_TOKEN}@')
            subprocess.run(['git', 'push', repo_url_with_token, 'HEAD:main'], 
                         check=True, capture_output=True)
            
            print("  ✓ Git push")
            print("="*60 + "\n")
            
        except Exception as e:
            print(f"  ✗ Auto-log error: {e}")
            print("="*60 + "\n")
            # Continue quand même (retourner la lecture)
    
    # ============================================
    # ÉTAPE 2 : Toujours retourner le contenu
    # ============================================
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
# ROUTES FLASK BASIQUES
# =====================================================

@app.route('/')
def index():
    """Page d'accueil"""
    return jsonify({
        'service': '_Head.Soeurise',
        'version': 'V3.5.3',
        'status': 'running',
        'endpoints': {
            'GET /api/mc': 'Lire mémoire courte (optionnel: ?action=log&summary=...)',
            'GET /api/mm': 'Lire mémoire moyenne',
            'GET /api/ml': 'Lire mémoire longue'
        }
    }), 200


# =====================================================
# SCHEDULER EN THREAD SÉPARÉ
# =====================================================

def run_scheduler():
    """Thread scheduler pour monitoring"""
    schedule.every(30).minutes.do(lambda: None)
    
    print("⏰ Scheduler démarré")
    
    while True:
        schedule.run_pending()
        time.sleep(60)


# =====================================================
# MAIN - THREADING V3.5.3
# =====================================================

if __name__ == "__main__":
    print("=" * 60)
    print("_Head.Soeurise V3.5.3")
    print("Modèle: Haiku 4.5 (claude-haiku-4-5-20251001)")
    print("Architecture: Threading (Scheduler + Flask API)")
    print("🆕 NEW: Auto-log via GET /api/mc?action=log&...")
    print("="*60)
    
    if not init_git_repo():
        print("⚠️ Échec initialisation Git")
    
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    print("✓ Thread scheduler lancé")
    
    print("\n" + "=" * 60)
    print("🌐 FLASK API V3.5.3")
    print("=" * 60)
    print(f"✓ Modèle: {CLAUDE_MODEL}")
    print("✓ Endpoints: GET /api/mc (+ auto-log), /api/mm, /api/ml")
    print("🆕 V3.5.3: Auto-persistence via GET avec paramètres")
    print("=" * 60 + "\n")
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
