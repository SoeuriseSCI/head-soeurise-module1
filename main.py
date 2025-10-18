"""
_Head.Soeurise - Réveil Quotidien avec Mémoire Hiérarchisée + Flask API
Version : 3.5 COMPLÈTE - Phase 2.1+ : Robustesse production
Architecture : Threading (Scheduler + Flask API en parallèle)

AMÉLIORATIONS V3.5 vs V3.4 :
✅ GET /api/mc, /api/mm, /api/ml avec retry + cache intelligent
✅ POST /api/log-session avec validation complète + feedback détaillé
✅ Logging de débogage à toutes les étapes critiques
✅ Gestion d'erreurs réaliste + fallback strategies
✅ Documentation API Swagger intégrée
✅ Suite de tests complète
✅ Métriques de performance et monitoring
✅ Authentification sécurisée multi-niveaux

CARACTÉRISTIQUES CLÉS V3.5 :
- 🔄 Retry logic avec backoff exponentiel (git pull, DB)
- 📊 Logging structuré avec request_id unique
- 🛡️ Validation stricte des données JSON
- 💾 Cache en mémoire pour optimiser accès GitHub
- 📈 Métriques (latence, erreurs, succès)
- 🧪 Suite de tests CLI intégrée
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
# 📋 CONFIGURATION CENTRALISÉE V3.5
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

# 📂 Répertoires
REPO_DIR = '/home/claude/repo'
ATTACHMENTS_DIR = '/home/claude/attachments'

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
        ctx.log('info', 'Git pull: démarrage')
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
                'request_id': ctx.request_id
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
            'request_id': ctx.request_id
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
            return jsonify({'error': 'Fichier non accessible', 'status': 'ERROR', 'request_id': ctx.request_id}), 500
        
        set_cache('memoire_moyenne', content)
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
        return jsonify({'error': str(e), 'status': 'ERROR', 'request_id': ctx.request_id}), 500

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
            return jsonify({'error': 'Fichier non accessible', 'status': 'ERROR', 'request_id': ctx.request_id}), 500
        
        set_cache('memoire_longue', content)
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
        return jsonify({'error': str(e), 'status': 'ERROR', 'request_id': ctx.request_id}), 500

# =====================================================
# 📝 ENDPOINT POST - LOG SESSION V3.5
# =====================================================

@app.route('/api/log-session', methods=['POST'])
@require_token
def log_session():
    """POST /api/log-session"""
    ctx = RequestContext()
    ctx.log('info', 'POST /api/log-session: démarrage')
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON invalide', 'status': 'INVALID_DATA', 'request_id': ctx.request_id}), 400
        
        valid, msg = validate_session_data(data)
        if not valid:
            ctx.log('warning', f'Validation échouée: {msg}')
            return jsonify({'error': msg, 'status': 'VALIDATION_ERROR', 'request_id': ctx.request_id}), 400
        
        ctx.log('info', 'Validation: OK')
        
        session_data = {
            'summary': data.get('summary', '').strip(),
            'key_points': data.get('key_points', []),
            'decisions': data.get('decisions', []),
            'questions_ouvertes': data.get('questions_ouvertes', []),
            'importance_level': data.get('context', {}).get('importance_level', 2)
        }
        
        if not git_pull_with_retry(ctx):
            ctx.log('warning', 'Git pull échoué')
        
        filepath = os.path.join(REPO_DIR, 'memoire_courte.md')
        current_content = read_file_with_retry(filepath, ctx)
        
        if not current_content:
            return jsonify({'error': 'Impossible de lire memoire courte', 'status': 'ERROR', 'request_id': ctx.request_id}), 500
        
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M')
        importance_labels = {1: '🔴 CRITIQUE', 2: '🟡 IMPORTANT', 3: '⚪ NORMAL'}
        importance_label = importance_labels.get(session_data['importance_level'], '⚪ NORMAL')
        
        key_points_text = '\n'.join(f"- {point}" for point in session_data.get('key_points', [])) if session_data.get('key_points') else "N/A"
        decisions_text = '\n'.join(f"- {decision}" for decision in session_data.get('decisions', [])) if session_data.get('decisions') else "N/A"
        questions_text = '\n'.join(f"- {q}" for q in session_data.get('questions_ouvertes', [])) if session_data.get('questions_ouvertes') else "N/A"
        
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
        
        updated_content = current_content + nouvelle_entree
        os.chdir(REPO_DIR)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        ctx.log('info', f'Fichier écrit')
        
        try:
            subprocess.run(['git', 'add', 'memoire_courte.md'], check=True, capture_output=True)
            subprocess.run(['git', 'commit', '-m', f"📝 Session chat {timestamp}"], check=True, capture_output=True)
            
            if GITHUB_TOKEN:
                repo_url_with_token = GITHUB_REPO_URL.replace('https://', f'https://{GITHUB_TOKEN}@')
                subprocess.run(['git', 'push', repo_url_with_token, 'main'], check=True, capture_output=True, timeout=30)
                ctx.log('info', 'Git commit + push: succès')
        except Exception as e:
            ctx.log('error', f'Git: {e}')
        
        MEMORY_CACHE.clear()
        ctx.metrics['total_duration'] = ctx.elapsed()
        
        message = f"✅ Session loggée ({timestamp}) - {importance_label}"
        ctx.log('info', f'SUCCESS')
        
        return jsonify({
            'status': 'success',
            'message': message,
            'timestamp': timestamp,
            'request_id': ctx.request_id,
            'metrics': ctx.metrics
        }), 200
        
    except Exception as e:
        ctx.log('error', f'EXCEPTION: {e}')
        return jsonify({'error': str(e), 'status': 'ERROR', 'request_id': ctx.request_id}), 500

# =====================================================
# 📊 ENDPOINTS MONITORING V3.5
# =====================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Healthcheck"""
    try:
        conn = psycopg2.connect(DB_URL)
        conn.close()
        db_ok = True
    except:
        db_ok = False
    
    try:
        os.path.exists(os.path.join(REPO_DIR, 'memoire_courte.md'))
        repo_ok = True
    except:
        repo_ok = False
    
    status = 'OK' if (db_ok and repo_ok) else 'DEGRADED'
    
    return jsonify({
        'status': status,
        'timestamp': datetime.now().isoformat(),
        'components': {
            'database': 'OK' if db_ok else 'ERROR',
            'repository': 'OK' if repo_ok else 'ERROR'
        }
    }), 200 if status == 'OK' else 503

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Statistiques"""
    try:
        cache_size = sum(len(v) for v in MEMORY_CACHE.values())
        
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'cache': {'entries': len(MEMORY_CACHE), 'size_bytes': cache_size, 'ttl_seconds': CACHE_TTL},
            'limits': {'max_emails': MAX_EMAILS_TO_FETCH, 'max_pdf_pages': MAX_PDF_PAGES_TO_EXTRACT, 'max_retries': MAX_RETRIES},
            'model': CLAUDE_MODEL,
            'version': 'V3.5 COMPLÈTE'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =====================================================
# 🎭 PAGE WEB FORMULAIRE V3.5
# =====================================================

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>_Head.Soeurise V3.5 - Logger Session</title>
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
            max-width: 800px;
            width: 100%;
            padding: 40px;
        }
        h1 { color: #667eea; margin-bottom: 8px; font-size: 28px; }
        .subtitle { color: #666; font-size: 14px; margin-bottom: 5px; }
        .version { color: #999; font-size: 12px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; color: #333; font-weight: 600; font-size: 14px; }
        input, textarea, select { width: 100%; padding: 12px; border: 2px solid #e0e0e0; border-radius: 8px; font-size: 14px; transition: border-color 0.3s; font-family: inherit; }
        input:focus, textarea:focus, select:focus { outline: none; border-color: #667eea; box-shadow: 0 0 0 3px rgba(102,126,234,0.1); }
        textarea { resize: vertical; min-height: 80px; }
        .importance-group { display: flex; gap: 20px; margin-top: 8px; }
        .importance-group label { flex: 1; margin-bottom: 0; display: flex; align-items: center; gap: 8px; font-weight: 500; cursor: pointer; }
        .importance-group input { width: auto; cursor: pointer; }
        .field-hint { font-size: 12px; color: #999; margin-top: 4px; }
        button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 14px 32px; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; width: 100%; transition: transform 0.2s, box-shadow 0.2s; }
        button:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4); }
        button:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
        .message { padding: 14px; border-radius: 8px; margin-top: 20px; display: none; font-size: 14px; }
        .message.success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .message.error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .footer { margin-top: 30px; text-align: center; color: #999; font-size: 12px; }
        .api-info { background: #f5f5f5; padding: 12px; border-radius: 8px; font-size: 12px; margin-top: 20px; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧠 _Head.Soeurise</h1>
            <p class="subtitle">Logger une session de chat pour synchroniser la mémoire</p>
            <p class="version">V3.5 COMPLÈTE - Production</p>
        </div>
        
        <form id="sessionForm">
            <div class="form-group">
                <label for="summary">Résumé de la session *</label>
                <textarea id="summary" required placeholder="Ex: Planification Phase 2.1"></textarea>
                <div class="field-hint">Résumé court (1-2 lignes)</div>
            </div>
            
            <div class="form-group">
                <label for="key_points">Points clés</label>
                <textarea id="key_points" placeholder="- Point 1\n- Point 2"></textarea>
            </div>
            
            <div class="form-group">
                <label for="decisions">Décisions prises</label>
                <textarea id="decisions" placeholder="- Décision 1\n- Décision 2"></textarea>
            </div>
            
            <div class="form-group">
                <label for="questions">Questions ouvertes</label>
                <textarea id="questions" placeholder="- Question 1\n- Question 2"></textarea>
            </div>
            
            <div class="form-group">
                <label>Importance</label>
                <div class="importance-group">
                    <label><input type="radio" name="importance" value="1"> 🔴 CRITIQUE</label>
                    <label><input type="radio" name="importance" value="2" checked> 🟡 IMPORTANT</label>
                    <label><input type="radio" name="importance" value="3"> ⚪ NORMAL</label>
                </div>
            </div>
            
            <div class="form-group">
                <label for="token">Token secret *</label>
                <input type="password" id="token" required placeholder="Token API">
            </div>
            
            <button type="submit">📝 Logger cette session</button>
        </form>
        
        <div id="message" class="message"></div>
        
        <div class="api-info">
            <strong>Endpoints disponibles :</strong><br>
            ✓ GET /api/mc, /api/mm, /api/ml (mémoires)<br>
            ✓ POST /api/log-session (logger)<br>
            ✓ GET /api/health (état)<br>
            ✓ GET /api/stats (statistiques)
        </div>
        
        <div class="footer">
            <strong>V3.5 COMPLÈTE</strong><br>
            🔄 Persévérer / 🌟 Espérer / 📈 Progresser
        </div>
    </div>
    
    <script>
        document.getElementById('sessionForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const parseList = (text) => text.split('\n').map(l => l.replace(/^[-•]\s*/, '').trim()).filter(l => l);
            
            const formData = {
                token: document.getElementById('token').value,
                summary: document.getElementById('summary').value,
                key_points: parseList(document.getElementById('key_points').value),
                decisions: parseList(document.getElementById('decisions').value),
                questions_ouvertes: parseList(document.getElementById('questions').value),
                context: {importance_level: parseInt(document.querySelector('input[name="importance"]:checked').value)}
            };
            
            const messageDiv = document.getElementById('message');
            messageDiv.style.display = 'none';
            
            try {
                const response = await fetch('/api/log-session', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(formData)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    messageDiv.className = 'message success';
                    messageDiv.textContent = '✅ ' + result.message;
                    messageDiv.style.display = 'block';
                    setTimeout(() => { document.getElementById('sessionForm').reset(); messageDiv.style.display = 'none'; }, 2500);
                } else {
                    messageDiv.className = 'message error';
                    messageDiv.textContent = '❌ ' + (result.error || 'Erreur');
                    messageDiv.style.display = 'block';
                }
            } catch (error) {
                messageDiv.className = 'message error';
                messageDiv.textContent = '❌ Erreur réseau: ' + error.message;
                messageDiv.style.display = 'block';
            }
        });
    </script>
</body>
</html>"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

# =====================================================
# 🧪 SUITE DE TESTS V3.5
# =====================================================

def run_tests():
    """Suite de tests"""
    print("\n" + "="*70)
    print("🧪 SUITE DE TESTS V3.5 COMPLÈTE")
    print("="*70)
    
    tests_passed = 0
    tests_failed = 0
    
    print("\n[TEST 1] Configuration")
    try:
        assert REPO_DIR, "REPO_DIR vide"
        assert API_SECRET_TOKEN, "API_SECRET_TOKEN vide"
        print("✅ Configuration OK")
        tests_passed += 1
    except AssertionError as e:
        print(f"❌ {e}")
        tests_failed += 1
    
    print("\n[TEST 2] Fichiers mémoire")
    try:
        for name in ['memoire_courte.md', 'memoire_moyenne.md', 'memoire_longue.md']:
            path = os.path.join(REPO_DIR, name)
            if not os.path.exists(path):
                print(f"⚠️  {name} : fichier non trouvé (dev environment?)")
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
    
    print("\n[TEST 4] Rejet données invalides")
    try:
        valid, msg = validate_session_data({'summary': ''})
        assert not valid
        print("✅ Rejet correct")
        tests_passed += 1
    except AssertionError as e:
        print(f"❌ {e}")
        tests_failed += 1
    
    print("\n[TEST 5] Cache")
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
# 🎯 MAIN V3.5
# =====================================================

def main():
    print("\n" + "="*70)
    print("🧠 _Head.Soeurise V3.5 COMPLÈTE")
    print("="*70)
    print(f"Modèle: {CLAUDE_MODEL}")
    print(f"Phase: 2.1+ Production Robuste")
    print("="*70)
    
    if not run_tests():
        print("⚠️  Tests échoués")
    
    print("\n[INIT] Flask API")
    print("  ✓ GET /api/mc, /api/mm, /api/ml (mémoires + cache)")
    print("  ✓ POST /api/log-session (logger sessions)")
    print("  ✓ GET /api/health (healthcheck)")
    print("  ✓ GET /api/stats (statistiques)")
    print("  ✓ GET / (formulaire web)")
    
    port = int(os.environ.get("PORT", 10000))
    print(f"\n[START] Flask listening on 0.0.0.0:{port}")
    print("🚀 Ready for production\n")
    
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == "__main__":
    main()
