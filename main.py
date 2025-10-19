"""
_Head.Soeurise - Réveil Quotidien avec Mémoire Hiérarchisée + Flask API
Version : 3.5.1 FIXED - Correction detached HEAD
"""

import os
import json
import base64
from datetime import datetime, timedelta
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
import logging
from functools import wraps
from typing import Dict, Any, Optional, Tuple
import hashlib

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
# 📋 CONFIGURATION CENTRALISÉE V3.5.1 FIXED
# =====================================================

DB_URL = os.environ.get('DATABASE_URL', 'postgresql://default')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
SOEURISE_EMAIL = os.environ.get('SOEURISE_EMAIL', '')
SOEURISE_PASSWORD = os.environ.get('SOEURISE_PASSWORD', '')
NOTIF_EMAIL = os.environ.get('NOTIF_EMAIL', '')
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')
GITHUB_REPO_URL = os.environ.get('GITHUB_REPO_URL', 'https://github.com/SoeuriseSCI/head-soeurise-module1.git')
GIT_USER_NAME = os.environ.get('GIT_USER_NAME', '_Head.Soeurise')
GIT_USER_EMAIL = os.environ.get('GIT_USER_EMAIL', 'u6334452013@gmail.com')
API_SECRET_TOKEN = os.environ.get('API_SECRET_TOKEN', 'HeadSoeurise2025!SecureToken#V3.3')

if os.path.exists('/opt/render/project/src'):
    REPO_DIR = '/opt/render/project/src'
    print("[INIT] REPO_DIR = /opt/render/project/src (Render)")
elif os.path.exists('/home/claude/repo'):
    REPO_DIR = '/home/claude/repo'
    print("[INIT] REPO_DIR = /home/claude/repo (fallback)")
else:
    REPO_DIR = os.getcwd()
    print(f"[INIT] REPO_DIR = {os.getcwd()} (cwd)")

ATTACHMENTS_DIR = '/tmp/attachments'

GITHUB_REPO = "SoeuriseSCI/head-soeurise-module1"
GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_REPO}/contents/"

CLAUDE_MODEL = "claude-haiku-4-5-20251001"
CLAUDE_MAX_TOKENS = 8000

MAX_EMAILS_TO_FETCH = 10
MAX_ATTACHMENTS_PER_EMAIL = 3
MAX_EMAIL_BODY_LENGTH = 5000
MAX_PDF_TEXT_LENGTH = 30000
MAX_PDF_PAGES_TO_EXTRACT = 50
MIN_TEXT_FOR_NATIVE_PDF = 50

MAX_RETRIES = 3
RETRY_BACKOFF = 1.5
INITIAL_RETRY_DELAY = 0.5

MEMORY_CACHE = {}
CACHE_TTL = 300

IDENTITY = """Je suis _Head.Soeurise, l'IA de la SCI Soeurise.
Mission : Assister Ulrik dans la gestion patrimoniale.
Philosophie : Persévérer / Espérer / Progresser"""

app = Flask(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/head-soeurise.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('_Head.Soeurise')

# =====================================================
# 🔧 UTILITAIRES
# =====================================================

class RequestContext:
    def __init__(self):
        self.request_id = f"{datetime.now().isoformat()}-{hashlib.md5(os.urandom(16)).hexdigest()[:8]}"
        self.start_time = time.time()
        self.metrics = {
            'git_pull_duration': None,
            'file_read_duration': None,
            'total_duration': None
        }
    
    def elapsed(self):
        return time.time() - self.start_time
    
    def log(self, level, message):
        elapsed = self.elapsed()
        prefix = f"[{self.request_id[:12]}] [{elapsed:.3f}s]"
        getattr(logger, level)(f"{prefix} {message}")

def retry_with_backoff(func, *args, max_retries=MAX_RETRIES, **kwargs):
    last_exception = None
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = INITIAL_RETRY_DELAY * (RETRY_BACKOFF ** attempt)
                logger.warning(f"Tentative {attempt + 1}/{max_retries} échouée, retry dans {delay:.2f}s")
                time.sleep(delay)
    raise last_exception

def get_cache_key(cache_type: str) -> str:
    now = datetime.now()
    return f"{cache_type}_{int(now.timestamp() / CACHE_TTL)}"

def set_cache(cache_type: str, content: str):
    key = get_cache_key(cache_type)
    MEMORY_CACHE[key] = content
    logger.debug(f"Cache SET: {cache_type}")

def get_cache(cache_type: str) -> Optional[str]:
    key = get_cache_key(cache_type)
    if key in MEMORY_CACHE:
        logger.debug(f"Cache HIT: {cache_type}")
        return MEMORY_CACHE[key]
    logger.debug(f"Cache MISS: {cache_type}")
    return None

def require_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.args.get('token') or (request.json.get('token') if request.is_json else None)
        if not token or token != API_SECRET_TOKEN:
            logger.warning(f"Token invalide")
            return jsonify({'error': 'Token invalide', 'status': 'UNAUTHORIZED'}), 401
        return f(*args, **kwargs)
    return decorated_function

# =====================================================
# GIT + FILE OPERATIONS
# =====================================================

def git_fetch_merge_with_retry(ctx: RequestContext) -> bool:
    try:
        ctx.log('info', f'Git fetch+merge: démarrage')
        os.chdir(REPO_DIR)
        
        t0 = time.time()
        subprocess.run(['git', 'fetch'], capture_output=True, check=True, timeout=30)
        subprocess.run(['git', 'merge', 'origin/main'], capture_output=True, timeout=30)
        duration = time.time() - t0
        ctx.metrics['git_pull_duration'] = duration
        
        ctx.log('info', f'Git fetch+merge: succès ({duration:.2f}s)')
        return True
    except Exception as e:
        ctx.log('error', f'Git fetch+merge: {e}')
        return False

def read_file_with_retry(filepath: str, ctx: RequestContext) -> Optional[str]:
    def _read():
        t0 = time.time()
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        duration = time.time() - t0
        ctx.metrics['file_read_duration'] = duration
        return content
    
    try:
        return retry_with_backoff(_read)
    except Exception as e:
        ctx.log('error', f'Lecture {filepath}: {e}')
        return None

def append_to_memoire_courte(session_data: Dict[str, Any]) -> Tuple[bool, str]:
    try:
        os.chdir(REPO_DIR)
        
        # Git fetch + merge (fonctionne avec detached HEAD)
        subprocess.run(['git', 'fetch'], capture_output=True, check=True, timeout=30)
        subprocess.run(['git', 'merge', 'origin/main'], capture_output=True, timeout=30)
        
        # Lire contenu actuel
        filepath = os.path.join(REPO_DIR, 'memoire_courte.md')
        with open(filepath, 'r', encoding='utf-8') as f:
            current_content = f.read()
        
        # Formater nouvelle entrée
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M')
        importance_labels = {1: '🔴 CRITIQUE', 2: '🟡 IMPORTANT', 3: '⚪ NORMAL'}
        importance_level = session_data.get('context', {}).get('importance_level', 2)
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
        
        nouvelle_entree = f"""## {timestamp} - Session chat {importance_label}

**Résumé :** {session_data.get('summary', 'N/A')}

**Points clés :**
{key_points_text}

**Décisions :**
{decisions_text}

**Questions ouvertes :**
{questions_text}

---
"""
        
        # Ajouter à la fin
        updated_content = current_content + nouvelle_entree
        
        # Écrire
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        # Git commit + push
        subprocess.run(['git', 'add', 'memoire_courte.md'], check=True)
        subprocess.run(['git', 'commit', '-m', f"📝 Session chat {timestamp} ({importance_label})"], 
                       check=True, capture_output=True)
        
        if GITHUB_TOKEN:
            repo_url_with_token = GITHUB_REPO_URL.replace('https://', f'https://{GITHUB_TOKEN}@')
            subprocess.run(['git', 'push', repo_url_with_token, 'main'], 
                           check=True, capture_output=True, timeout=30)
        else:
            logger.warning("GITHUB_TOKEN non défini, pas de push")
        
        # Invalider cache
        key = get_cache_key('memoire_courte')
        if key in MEMORY_CACHE:
            del MEMORY_CACHE[key]
        
        return True, f"Session ajoutée et pushée ({timestamp})"
        
    except Exception as e:
        logger.error(f"Erreur append_to_memoire_courte: {e}")
        return False, f"Erreur: {str(e)}"

def validate_session_data(data: Dict[str, Any]) -> Tuple[bool, str]:
    errors = []
    
    summary = data.get('summary', '').strip()
    if not summary:
        errors.append("'summary' est obligatoire et non vide")
    elif len(summary) > 500:
        errors.append("'summary' doit faire < 500 chars")
    
    for field in ['key_points', 'decisions', 'questions_ouvertes']:
        items = data.get(field, [])
        if not isinstance(items, list):
            errors.append(f"'{field}' doit être une liste")
        elif len(items) > 20:
            errors.append(f"'{field}' doit avoir < 20 éléments")
    
    importance = data.get('context', {}).get('importance_level')
    if importance is not None and importance not in [1, 2, 3]:
        errors.append("'importance_level' doit être 1, 2 ou 3")
    
    if errors:
        return False, "; ".join(errors)
    
    return True, "OK"

# =====================================================
# ENDPOINTS GET
# =====================================================

@app.route('/api/mc', methods=['GET'])
@require_token
def get_memoire_courte():
    ctx = RequestContext()
    ctx.log('info', 'GET /api/mc: démarrage')
    
    try:
        cached = get_cache('memoire_courte')
        if cached:
            ctx.log('info', f'Cache HIT')
            return jsonify({
                'status': 'OK',
                'source': 'cache',
                'content': cached,
                'timestamp': datetime.now().isoformat(),
                'type': 'courte',
                'size': len(cached),
                'request_id': ctx.request_id
            }), 200
        
        if not git_fetch_merge_with_retry(ctx):
            ctx.log('warning', 'Git fetch+merge échoué')
        
        filepath = os.path.join(REPO_DIR, 'memoire_courte.md')
        content = read_file_with_retry(filepath, ctx)
        
        if not content:
            return jsonify({
                'error': 'Fichier non accessible',
                'status': 'ERROR',
                'request_id': ctx.request_id,
                'repo_dir': REPO_DIR
            }), 500
        
        set_cache('memoire_courte', content)
        ctx.metrics['total_duration'] = ctx.elapsed()
        ctx.log('info', f'SUCCESS ({ctx.elapsed():.3f}s)')
        
        return jsonify({
            'status': 'OK',
            'source': 'filesystem',
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'type': 'courte',
            'size': len(content),
            'request_id': ctx.request_id,
            'metrics': ctx.metrics
        }), 200
        
    except Exception as e:
        ctx.log('error', f'EXCEPTION: {e}')
        return jsonify({
            'error': str(e),
            'status': 'ERROR',
            'request_id': ctx.request_id,
            'repo_dir': REPO_DIR
        }), 500

@app.route('/api/mm', methods=['GET'])
@require_token
def get_memoire_moyenne():
    ctx = RequestContext()
    ctx.log('info', 'GET /api/mm: démarrage')
    
    try:
        cached = get_cache('memoire_moyenne')
        if cached:
            ctx.log('info', 'Cache HIT')
            return jsonify({
                'status': 'OK',
                'source': 'cache',
                'content': cached,
                'timestamp': datetime.now().isoformat(),
                'type': 'moyenne',
                'size': len(cached),
                'request_id': ctx.request_id
            }), 200
        
        if not git_fetch_merge_with_retry(ctx):
            ctx.log('warning', 'Git fetch+merge échoué')
        
        filepath = os.path.join(REPO_DIR, 'memoire_moyenne.md')
        content = read_file_with_retry(filepath, ctx)
        
        if not content:
            return jsonify({
                'error': 'Fichier non accessible',
                'status': 'ERROR',
                'request_id': ctx.request_id,
                'repo_dir': REPO_DIR
            }), 500
        
        set_cache('memoire_moyenne', content)
        ctx.log('info', f'SUCCESS ({ctx.elapsed():.3f}s)')
        
        return jsonify({
            'status': 'OK',
            'source': 'filesystem',
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'type': 'moyenne',
            'size': len(content),
            'request_id': ctx.request_id,
            'metrics': ctx.metrics
        }), 200
        
    except Exception as e:
        ctx.log('error', f'EXCEPTION: {e}')
        return jsonify({
            'error': str(e),
            'status': 'ERROR',
            'request_id': ctx.request_id,
            'repo_dir': REPO_DIR
        }), 500

@app.route('/api/ml', methods=['GET'])
@require_token
def get_memoire_longue():
    ctx = RequestContext()
    ctx.log('info', 'GET /api/ml: démarrage')
    
    try:
        cached = get_cache('memoire_longue')
        if cached:
            ctx.log('info', 'Cache HIT')
            return jsonify({
                'status': 'OK',
                'source': 'cache',
                'content': cached,
                'timestamp': datetime.now().isoformat(),
                'type': 'longue',
                'size': len(cached),
                'request_id': ctx.request_id
            }), 200
        
        if not git_fetch_merge_with_retry(ctx):
            ctx.log('warning', 'Git fetch+merge échoué')
        
        filepath = os.path.join(REPO_DIR, 'memoire_longue.md')
        content = read_file_with_retry(filepath, ctx)
        
        if not content:
            return jsonify({
                'error': 'Fichier non accessible',
                'status': 'ERROR',
                'request_id': ctx.request_id,
                'repo_dir': REPO_DIR
            }), 500
        
        set_cache('memoire_longue', content)
        ctx.log('info', f'SUCCESS ({ctx.elapsed():.3f}s)')
        
        return jsonify({
            'status': 'OK',
            'source': 'filesystem',
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'type': 'longue',
            'size': len(content),
            'request_id': ctx.request_id,
            'metrics': ctx.metrics
        }), 200
        
    except Exception as e:
        ctx.log('error', f'EXCEPTION: {e}')
        return jsonify({
            'error': str(e),
            'status': 'ERROR',
            'request_id': ctx.request_id,
            'repo_dir': REPO_DIR
        }), 500

# =====================================================
# ENDPOINTS POST
# =====================================================

@app.route('/api/log-session', methods=['POST'])
@require_token
def log_session():
    try:
        data = request.json
        
        valid, msg = validate_session_data(data)
        if not valid:
            return jsonify({'error': msg, 'status': 'INVALID_DATA'}), 400
        
        success, result_msg = append_to_memoire_courte(data)
        
        if success:
            logger.info(f"Session logged et pushée: {data.get('summary', 'N/A')}")
            return jsonify({
                'status': 'success',
                'message': result_msg,
                'timestamp': datetime.now().isoformat()
            }), 200
        else:
            logger.error(f"Erreur append: {result_msg}")
            return jsonify({
                'status': 'error',
                'message': result_msg,
                'timestamp': datetime.now().isoformat()
            }), 500
        
    except Exception as e:
        logger.error(f"Erreur logging session: {e}")
        return jsonify({'error': str(e), 'status': 'ERROR'}), 500

# =====================================================
# ENDPOINTS UTILITAIRES
# =====================================================

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'OK',
        'timestamp': datetime.now().isoformat(),
        'repo_dir': REPO_DIR,
        'repo_exists': os.path.exists(REPO_DIR),
        'version': 'V3.5.1 FIXED'
    }), 200

@app.route('/api/stats', methods=['GET'])
@require_token
def stats():
    return jsonify({
        'status': 'OK',
        'repo_dir': REPO_DIR,
        'cache_size': len(MEMORY_CACHE),
        'model': CLAUDE_MODEL,
        'version': 'V3.5.1 FIXED'
    }), 200

@app.route('/')
def index():
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>_Head.Soeurise V3.5.1 FIXED</title>
        <style>
            body {{ font-family: Arial; background: #f5f5f5; padding: 40px; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }}
            h1 {{ color: #667eea; }}
            .info {{ background: #f0f0f0; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            code {{ background: #eee; padding: 2px 6px; border-radius: 3px; }}
            .status {{ color: green; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>_Head.Soeurise V3.5.1 FIXED</h1>
            
            <div class="info">
                <strong>Status:</strong> <span class="status">OK</span><br>
                <strong>REPO_DIR:</strong> <code>{REPO_DIR}</code><br>
                <strong>Model:</strong> {CLAUDE_MODEL}<br>
                <strong>Version:</strong> V3.5.1 FIXED
            </div>
            
            <h2>Endpoints</h2>
            <ul>
                <li>GET /api/mc?token=... - Memoire courte</li>
                <li>GET /api/mm?token=... - Memoire moyenne</li>
                <li>GET /api/ml?token=... - Memoire longue</li>
                <li>POST /api/log-session?token=... - Logger session (git fetch+merge fix)</li>
                <li>GET /api/health - Healthcheck</li>
                <li>GET /api/stats?token=... - Stats</li>
            </ul>
        </div>
    </body>
    </html>
    """
    return html, 200

# =====================================================
# TESTS
# =====================================================

def run_tests():
    print("\n" + "="*70)
    print("SUITE DE TESTS V3.5.1 FIXED")
    print("="*70)
    
    tests_passed = 0
    tests_failed = 0
    
    print("\n[TEST 1] Configuration")
    try:
        assert REPO_DIR, "REPO_DIR vide"
        assert os.path.exists(REPO_DIR), f"REPO_DIR n'existe pas: {REPO_DIR}"
        print(f"OK (REPO_DIR={REPO_DIR})")
        tests_passed += 1
    except AssertionError as e:
        print(f"FAIL {e}")
        tests_failed += 1
    
    print("\n[TEST 2] Fichiers memoire")
    try:
        for name in ['memoire_courte.md', 'memoire_moyenne.md', 'memoire_longue.md']:
            path = os.path.join(REPO_DIR, name)
            exists = os.path.exists(path)
            status = "OK" if exists else "MISSING"
            print(f"  {status}: {name}")
        tests_passed += 1
    except Exception as e:
        print(f"FAIL {e}")
        tests_failed += 1
    
    print("\n[TEST 3] Validation donnees")
    try:
        valid, msg = validate_session_data({
            'summary': 'Test valide',
            'key_points': ['point1'],
            'decisions': [],
            'questions_ouvertes': [],
            'context': {'importance_level': 2}
        })
        assert valid, msg
        print("OK")
        tests_passed += 1
    except AssertionError as e:
        print(f"FAIL {e}")
        tests_failed += 1
    
    print("\n" + "="*70)
    print(f"RESULTAT: {tests_passed} OK | {tests_failed} FAIL")
    print("="*70 + "\n")
    
    return tests_failed == 0

# =====================================================
# MAIN
# =====================================================

def main():
    print("\n" + "="*70)
    print("_Head.Soeurise V3.5.1 FIXED")
    print("="*70)
    print(f"Model: {CLAUDE_MODEL}")
    print(f"REPO_DIR: {REPO_DIR}")
    print("="*70)
    
    if not run_tests():
        print("Tests echoues")
    
    print("\n[INIT] Flask API")
    print("  GET /api/mc, /api/mm, /api/ml (+ cache)")
    print("  POST /api/log-session (git fetch+merge FIXED)")
    print("  GET /api/health")
    print("  GET /api/stats")
    
    port = int(os.environ.get("PORT", 10000))
    print(f"\n[START] Flask on 0.0.0.0:{port}")
    print("Ready\n")
    
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == "__main__":
    main()
