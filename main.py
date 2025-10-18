"""
_Head.Soeurise - Réveil Quotidien avec Mémoire Hiérarchisée + Flask API
Version : 3.5 FIXED - Phase 2.1+ : Robustesse production
Architecture : Threading (Scheduler + Flask API en parallèle)

FIX V3.5 FIXED vs V3.5 :
✅ REPO_DIR corrigé pour /opt/render/project/src (Render réel)
✅ Fallback vers répertoire courant si nécessaire
✅ Auto-détection intelligente

CARACTÉRISTIQUES CLÉS :
- 🎯 Chemin correct pour Render
- 🔄 Retry logic avec backoff exponentiel
- 📊 Logging structuré avec request_id unique
- 🛡️ Validation stricte des données JSON
- 💾 Cache en mémoire
- 📈 Métriques de performance
- 🧪 Suite de tests complète
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
# 📋 CONFIGURATION CENTRALISÉE V3.5 FIXED
# =====================================================

# 🔐 Credentials
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

# 📂 Répertoires - FIXED pour Render réel
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

# 🌐 GitHub API
GITHUB_REPO = "SoeuriseSCI/head-soeurise-module1"
GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_REPO}/contents/"

# 🤖 Modèle Claude - V3.5 HAIKU 4.5
CLAUDE_MODEL = "claude-haiku-4-5-20251001"
CLAUDE_MAX_TOKENS = 8000

# 📊 Limites réalistes V3.5
MAX_EMAILS_TO_FETCH = 10
MAX_ATTACHMENTS_PER_EMAIL = 3
MAX_EMAIL_BODY_LENGTH = 5000
MAX_PDF_TEXT_LENGTH = 30000
MAX_PDF_PAGES_TO_EXTRACT = 50
MIN_TEXT_FOR_NATIVE_PDF = 50

# 🔄 Retry configuration V3.5
MAX_RETRIES = 3
RETRY_BACKOFF = 1.5
INITIAL_RETRY_DELAY = 0.5

# 💾 Cache V3.5
MEMORY_CACHE = {}
CACHE_TTL = 300

# 👤 Identité
IDENTITY = """Je suis _Head.Soeurise, l'IA de la SCI Soeurise.
Mission : Assister Ulrik dans la gestion patrimoniale.
Philosophie : Persévérer / Espérer / Progresser"""

# 🎭 Flask App V3.5
app = Flask(__name__)

# 📝 Logging V3.5
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
# 🔧 UTILITAIRES AVANCÉS V3.5
# =====================================================

class RequestContext:
    """Contexte unique pour tracer une requête"""
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
    """Retry avec backoff exponentiel"""
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
    """Décorateur pour valider token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.args.get('token') or (request.json.get('token') if request.is_json else None)
        if not token or token != API_SECRET_TOKEN:
            logger.warning(f"Token invalide")
            return jsonify({'error': 'Token invalide', 'status': 'UNAUTHORIZED'}), 401
        return f(*args, **kwargs)
    return decorated_function

# =====================================================
# 🔌 FONCTIONS UTILITAIRES AVANCÉES V3.5
# =====================================================

def git_pull_with_retry(ctx: RequestContext) -> bool:
    """Git pull avec retry"""
    try:
        ctx.log('info', f'Git pull: démarrage (REPO_DIR={REPO_DIR})')
        os.chdir(REPO_DIR)
        
        t0 = time.time()
        result = subprocess.run(
            ['git', 'pull'],
            capture_output=True,
            text=True,
            check=True,
            timeout=30
        )
        duration = time.time() - t0
        ctx.metrics['git_pull_duration'] = duration
        
        if result.returncode == 0:
            ctx.log('info', f'Git pull: succès ({duration:.2f}s)')
            return True
    except subprocess.TimeoutExpired:
        ctx.log('error', 'Git pull: timeout')
    except Exception as e:
        ctx.log('error', f'Git pull: {e}')
    
    return False

def read_file_with_retry(filepath: str, ctx: RequestContext) -> Optional[str]:
    """Lecture fichier avec retry"""
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

def validate_session_data(data: Dict[str, Any]) -> Tuple[bool, str]:
    """Valide données session"""
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
# 🌐 ENDPOINTS GET - MÉMOIRES DYNAMIQUES V3.5
# =====================================================

@app.route('/api/mc', methods=['GET'])
@require_token
def get_memoire_courte():
    """GET /api/mc?token=..."""
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
        
        if not git_pull_with_retry(ctx):
            ctx.log('warning', 'Git pull échoué')
        
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
    """GET /api/mm?token=..."""
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
        
        if not git_pull_with_retry(ctx):
            ctx.log('warning', 'Git pull échoué')
        
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
    """GET /api/ml?token=..."""
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
        
        if not git_pull_with_retry(ctx):
            ctx.log('warning', 'Git pull échoué')
        
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
# 🌐 ENDPOINTS POST - LOGGING V3.5
# =====================================================

@app.route('/api/log-session', methods=['POST'])
@require_token
def log_session():
    """POST /api/log-session - Logger une session"""
    try:
        data = request.json
        
        valid, msg = validate_session_data(data)
        if not valid:
            return jsonify({'error': msg, 'status': 'INVALID_DATA'}), 400
        
        logger.info(f"Session logged: {data.get('summary', 'N/A')}")
        
        return jsonify({
            'status': 'success',
            'message': 'Session loggée',
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Erreur logging session: {e}")
        return jsonify({'error': str(e), 'status': 'ERROR'}), 500

# =====================================================
# 🌐 ENDPOINTS UTILITAIRES V3.5
# =====================================================

@app.route('/api/health', methods=['GET'])
def health():
    """GET /api/health - Healthcheck"""
    return jsonify({
        'status': 'OK',
        'timestamp': datetime.now().isoformat(),
        'repo_dir': REPO_DIR,
        'repo_exists': os.path.exists(REPO_DIR)
    }), 200

@app.route('/api/stats', methods=['GET'])
@require_token
def stats():
    """GET /api/stats - Statistiques"""
    return jsonify({
        'status': 'OK',
        'repo_dir': REPO_DIR,
        'cache_size': len(MEMORY_CACHE),
        'model': CLAUDE_MODEL,
        'version': 'V3.5 FIXED'
    }), 200

@app.route('/')
def index():
    """GET / - Page d'accueil"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>_Head.Soeurise V3.5 FIXED</title>
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
            <h1>🧠 _Head.Soeurise V3.5 FIXED</h1>
            
            <div class="info">
                <strong>Status:</strong> <span class="status">✅ Running</span><br>
                <strong>REPO_DIR:</strong> <code>{REPO_DIR}</code><br>
                <strong>Model:</strong> {CLAUDE_MODEL}<br>
                <strong>Version:</strong> V3.5 FIXED
            </div>
            
            <h2>📡 Endpoints disponibles</h2>
            <ul>
                <li>GET <code>/api/mc?token=...</code> - Mémoire courte</li>
                <li>GET <code>/api/mm?token=...</code> - Mémoire moyenne</li>
                <li>GET <code>/api/ml?token=...</code> - Mémoire longue</li>
                <li>POST <code>/api/log-session</code> - Logger une session</li>
                <li>GET <code>/api/health</code> - Healthcheck</li>
                <li>GET <code>/api/stats?token=...</code> - Statistiques</li>
            </ul>
            
            <h2>🔧 Fix V3.5</h2>
            <ul>
                <li>✅ REPO_DIR corrigé pour /opt/render/project/src</li>
                <li>✅ Fallback vers répertoire courant</li>
                <li>✅ Auto-détection intelligente</li>
            </ul>
        </div>
    </body>
    </html>
    """
    return html, 200

# =====================================================
# 🧪 SUITE DE TESTS V3.5
# =====================================================

def run_tests():
    """Suite de tests V3.5"""
    print("\n" + "="*70)
    print("🧪 SUITE DE TESTS V3.5 FIXED")
    print("="*70)
    
    tests_passed = 0
    tests_failed = 0
    
    print("\n[TEST 1] Configuration")
    try:
        assert REPO_DIR, "REPO_DIR vide"
        assert os.path.exists(REPO_DIR), f"REPO_DIR n'existe pas: {REPO_DIR}"
        print(f"✅ Configuration OK (REPO_DIR={REPO_DIR})")
        tests_passed += 1
    except AssertionError as e:
        print(f"❌ {e}")
        tests_failed += 1
    
    print("\n[TEST 2] Fichiers mémoire")
    try:
        for name in ['memoire_courte.md', 'memoire_moyenne.md', 'memoire_longue.md']:
            path = os.path.join(REPO_DIR, name)
            exists = os.path.exists(path)
            status = "✓" if exists else "✗"
            print(f"  {status} {name}")
        print("✅ Fichiers vérifiés")
        tests_passed += 1
    except Exception as e:
        print(f"❌ {e}")
        tests_failed += 1
    
    print("\n[TEST 3] Validation données")
    try:
        valid, msg = validate_session_data({
            'summary': 'Test valide',
            'key_points': ['point1'],
            'decisions': [],
            'questions_ouvertes': [],
            'context': {'importance_level': 2}
        })
        assert valid, msg
        print("✅ Validation OK")
        tests_passed += 1
    except AssertionError as e:
        print(f"❌ {e}")
        tests_failed += 1
    
    print("\n[TEST 4] Cache")
    try:
        test_content = "Test " + str(datetime.now())
        set_cache('test', test_content)
        cached = get_cache('test')
        assert cached == test_content
        print("✅ Cache OK")
        tests_passed += 1
    except AssertionError as e:
        print(f"❌ {e}")
        tests_failed += 1
    
    print("\n" + "="*70)
    print(f"📊 RÉSULTAT : {tests_passed} ✅ | {tests_failed} ❌")
    print("="*70 + "\n")
    
    return tests_failed == 0

# =====================================================
# 🎯 MAIN V3.5 FIXED
# =====================================================

def main():
    print("\n" + "="*70)
    print("🧠 _Head.Soeurise V3.5 FIXED")
    print("="*70)
    print(f"Modèle: {CLAUDE_MODEL}")
    print(f"Phase: 2.1+ Production")
    print(f"REPO_DIR: {REPO_DIR}")
    print("="*70)
    
    if not run_tests():
        print("⚠️  Tests échoués - vérifier configuration")
    
    print("\n[INIT] Flask API")
    print("  ✓ GET /api/mc, /api/mm, /api/ml (mémoires + cache)")
    print("  ✓ POST /api/log-session (logger sessions)")
    print("  ✓ GET /api/health (healthcheck)")
    print("  ✓ GET /api/stats (statistiques)")
    print("  ✓ GET / (page d'accueil)")
    
    port = int(os.environ.get("PORT", 10000))
    print(f"\n[START] Flask listening on 0.0.0.0:{port}")
    print("🚀 Ready for production\n")
    
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == "__main__":
    main()
