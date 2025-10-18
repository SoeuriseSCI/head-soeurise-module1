"""
_Head.Soeurise - V3.4 WITH LOGGING
Débogage des endpoints GET /api/mc, /api/mm, /api/ml
Chaque requête génère une trace complète pour diagnostiquer les problèmes de synchronisation.

CHANGEMENTS V3.4 WITH LOGGING:
- ✅ Logging structuré avec request_id unique par requête
- ✅ Traces Git (pull status, stdout, stderr)
- ✅ Traces fichier (chemin, existence, taille, modification)
- ✅ Analyses de contenu (lignes, dernières dates, timestamps)
- ✅ Payload JSON enrichie avec données de débogage
- ✅ Traceback complet en cas d'erreur
"""

import os
import json
import base64
from datetime import datetime
import anthropic
import psycopg2
from psycopg2.extras import RealDictCursor
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
import threading
import re
from flask import Flask, request, jsonify

# =====================================================
# CONFIGURATION
# =====================================================

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

REPO_DIR = '/home/claude/repo'
ATTACHMENTS_DIR = '/home/claude/attachments'

GITHUB_REPO = "SoeuriseSCI/head-soeurise-module1"
CLAUDE_MODEL = "claude-haiku-4-5-20251001"

app = Flask(__name__)

# =====================================================
# 🔧 ENDPOINTS AVEC LOGGING COMPLET
# =====================================================

def format_log_header(request_id, endpoint):
    """Crée un en-tête de log formaté"""
    return f"\n{'='*75}\n[{request_id}] {endpoint}\n{'='*75}"

def format_log_step(request_id, step_num, step_name, message=""):
    """Formate une étape de log"""
    return f"[{request_id}] {step_num}️⃣  {step_name}" + (f" → {message}" if message else "")

@app.route('/api/mc', methods=['GET'])
def get_memoire_courte():
    """Retourne mémoire courte - Endpoint GET avec logging complet"""
    token = request.args.get('token')
    request_id = f"mc-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(format_log_header(request_id, "GET /api/mc"))
    print(f"[{request_id}] Token reçu: {token[:25] if token else 'NONE'}...")
    
    # Validation
    if token != API_SECRET_TOKEN:
        print(f"[{request_id}] ❌ TOKEN INVALIDE")
        print(f"{'='*75}\n")
        return jsonify({'error': 'Token invalide', 'status': 'UNAUTHORIZED'}), 401
    
    print(f"[{request_id}] ✓ Token validé")
    
    try:
        # STEP 1: Git pull
        print(format_log_step(request_id, "1", "Git Pull", REPO_DIR))
        result = subprocess.run(
            ['git', 'pull'],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            print(f"[{request_id}] ⚠️  Git stderr: {result.stderr[:200]}")
        else:
            git_status = result.stdout.split('\n')[0]
            print(f"[{request_id}]    Status: {git_status}")
        
        # STEP 2: Vérifier fichier
        filepath = os.path.join(REPO_DIR, 'memoire_courte.md')
        print(format_log_step(request_id, "2", "Vérification fichier", filepath))
        
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Fichier non trouvé: {filepath}")
        
        file_size = os.path.getsize(filepath)
        file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
        print(f"[{request_id}]    ✓ Existe: {file_size} bytes, modifié: {file_mtime.isoformat()}")
        
        # STEP 3: Lire contenu
        print(format_log_step(request_id, "3", "Lecture fichier"))
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        content_lines = content.split('\n')
        print(f"[{request_id}]    ✓ Contenu: {len(content)} chars, {len(content_lines)} lignes")
        
        # STEP 4: Analyser contenu
        print(format_log_step(request_id, "4", "Analyse contenu"))
        
        # Lignes non vides
        non_empty_lines = [l for l in content_lines if l.strip()]
        first_line = non_empty_lines[0][:100] if non_empty_lines else "[VIDE]"
        last_line = non_empty_lines[-1][:100] if non_empty_lines else "[VIDE]"
        
        print(f"[{request_id}]    Première ligne: {first_line}")
        print(f"[{request_id}]    Dernière ligne: {last_line}")
        
        # Dates (format JJ/MM/YYYY)
        date_pattern = r'\d{1,2}/\d{1,2}/\d{4}'
        dates_found = re.findall(date_pattern, content)
        if dates_found:
            unique_dates = sorted(set(dates_found))
            print(f"[{request_id}]    Dates trouvées: {len(unique_dates)} uniques")
            print(f"[{request_id}]    Plage: {unique_dates[0]} → {unique_dates[-1]}")
        
        # STEP 5: Préparer réponse
        print(format_log_step(request_id, "5", "Préparation réponse"))
        
        response_payload = {
            'status': 'OK',
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'type': 'courte',
            'meta': {
                'size_bytes': len(content),
                'line_count': len(content_lines),
                'non_empty_lines': len(non_empty_lines),
                'file_last_modified': file_mtime.isoformat(),
                'dates_found': len(dates_found),
                'date_range': {
                    'start': min(dates_found) if dates_found else None,
                    'end': max(dates_found) if dates_found else None
                }
            },
            'debug': {
                'request_id': request_id,
                'git_pull_status': result.returncode,
                'file_exists': True,
                'encoding': 'utf-8'
            }
        }
        
        print(f"[{request_id}] ✅ SUCCÈS - {len(content)} bytes à envoyer")
        print(f"{'='*75}\n")
        
        return jsonify(response_payload), 200
        
    except Exception as e:
        print(f"[{request_id}] ❌ ERREUR: {type(e).__name__}")
        print(f"[{request_id}]    {str(e)}")
        
        import traceback
        tb = traceback.format_exc()
        for line in tb.split('\n'):
            if line.strip():
                print(f"[{request_id}]    {line}")
        
        print(f"{'='*75}\n")
        
        return jsonify({
            'status': 'ERROR',
            'error': str(e),
            'error_type': type(e).__name__,
            'request_id': request_id
        }), 500


@app.route('/api/mm', methods=['GET'])
def get_memoire_moyenne():
    """Retourne mémoire moyenne - Endpoint GET avec logging complet"""
    token = request.args.get('token')
    request_id = f"mm-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(format_log_header(request_id, "GET /api/mm"))
    print(f"[{request_id}] Token: {token[:25] if token else 'NONE'}...")
    
    if token != API_SECRET_TOKEN:
        print(f"[{request_id}] ❌ TOKEN INVALIDE\n")
        return jsonify({'error': 'Token invalide', 'status': 'UNAUTHORIZED'}), 401
    
    try:
        print(format_log_step(request_id, "1", "Git pull"))
        subprocess.run(['git', 'pull'], cwd=REPO_DIR, capture_output=True, check=True)
        
        filepath = os.path.join(REPO_DIR, 'memoire_moyenne.md')
        print(format_log_step(request_id, "2", "Lecture fichier"))
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
        dates = re.findall(r'\d{1,2}/\d{1,2}/\d{4}', content)
        
        print(f"[{request_id}]    ✓ {len(content)} chars")
        print(f"[{request_id}] ✅ SUCCÈS\n")
        
        return jsonify({
            'status': 'OK',
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'type': 'moyenne',
            'meta': {
                'size_bytes': len(content),
                'file_last_modified': file_mtime.isoformat(),
                'dates_found': len(dates),
                'date_range': {'start': min(dates), 'end': max(dates)} if dates else None
            }
        }), 200
        
    except Exception as e:
        print(f"[{request_id}] ❌ {type(e).__name__}: {e}\n")
        return jsonify({'status': 'ERROR', 'error': str(e), 'request_id': request_id}), 500


@app.route('/api/ml', methods=['GET'])
def get_memoire_longue():
    """Retourne mémoire longue - Endpoint GET avec logging complet"""
    token = request.args.get('token')
    request_id = f"ml-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(format_log_header(request_id, "GET /api/ml"))
    print(f"[{request_id}] Token: {token[:25] if token else 'NONE'}...")
    
    if token != API_SECRET_TOKEN:
        print(f"[{request_id}] ❌ TOKEN INVALIDE\n")
        return jsonify({'error': 'Token invalide', 'status': 'UNAUTHORIZED'}), 401
    
    try:
        print(format_log_step(request_id, "1", "Git pull"))
        subprocess.run(['git', 'pull'], cwd=REPO_DIR, capture_output=True, check=True)
        
        filepath = os.path.join(REPO_DIR, 'memoire_longue.md')
        print(format_log_step(request_id, "2", "Lecture fichier"))
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
        dates = re.findall(r'\d{1,2}/\d{1,2}/\d{4}', content)
        
        print(f"[{request_id}]    ✓ {len(content)} chars")
        print(f"[{request_id}] ✅ SUCCÈS\n")
        
        return jsonify({
            'status': 'OK',
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'type': 'longue',
            'meta': {
                'size_bytes': len(content),
                'file_last_modified': file_mtime.isoformat(),
                'dates_found': len(dates),
                'date_range': {'start': min(dates), 'end': max(dates)} if dates else None
            }
        }), 200
        
    except Exception as e:
        print(f"[{request_id}] ❌ {type(e).__name__}: {e}\n")
        return jsonify({'status': 'ERROR', 'error': str(e), 'request_id': request_id}), 500


# =====================================================
# ENDPOINT DE DIAGNOSTIC
# =====================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Vérification rapide de la santé du système"""
    request_id = f"health-{datetime.now().strftime('%H%M%S')}"
    
    try:
        # Vérifier repo
        repo_ok = os.path.exists(os.path.join(REPO_DIR, '.git'))
        
        # Vérifier fichiers
        mc_ok = os.path.exists(os.path.join(REPO_DIR, 'memoire_courte.md'))
        mm_ok = os.path.exists(os.path.join(REPO_DIR, 'memoire_moyenne.md'))
        ml_ok = os.path.exists(os.path.join(REPO_DIR, 'memoire_longue.md'))
        
        status = 'HEALTHY' if all([repo_ok, mc_ok, mm_ok, ml_ok]) else 'DEGRADED'
        
        print(f"[{request_id}] Health Check: {status}")
        print(f"[{request_id}]    Repo: {'✓' if repo_ok else '❌'}, MC: {'✓' if mc_ok else '❌'}, MM: {'✓' if mm_ok else '❌'}, ML: {'✓' if ml_ok else '❌'}")
        
        return jsonify({
            'status': status,
            'repo': repo_ok,
            'memoire_courte': mc_ok,
            'memoire_moyenne': mm_ok,
            'memoire_longue': ml_ok,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'ERROR',
            'error': str(e)
        }), 500


# =====================================================
# MAIN
# =====================================================

if __name__ == "__main__":
    print("="*75)
    print("_Head.Soeurise V3.4 WITH LOGGING")
    print("Endpoints GET /api/mc, /api/mm, /api/ml avec traces complètes")
    print("="*75)
    
    port = int(os.environ.get("PORT", 10000))
    print(f"\n🚀 Serveur Flask démarré sur port {port}")
    print(f"📊 Logging complet activé pour débogage")
    print(f"🔐 Token validation: OUI")
    print(f"\nEndpoints disponibles:")
    print(f"  GET /api/mc?token=<token> → Mémoire Courte")
    print(f"  GET /api/mm?token=<token> → Mémoire Moyenne")
    print(f"  GET /api/ml?token=<token> → Mémoire Longue")
    print(f"  GET /api/health → Diagnostic santé système")
    print("="*75 + "\n")
    
    app.run(host='0.0.0.0', port=port)
